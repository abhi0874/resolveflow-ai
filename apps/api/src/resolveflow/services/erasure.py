"""Erase one authenticated identity. Workspace objects have a separate lifetime."""

import os
import re
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from resolveflow.backups.safety import BackupError
from resolveflow.db.models import (
    AccountErasure,
    AccountStatus,
    IdentityEmail,
    InvitationDelivery,
    MembershipRole,
    ProviderIdentity,
    Ticket,
    TicketActivity,
    TicketNote,
    User,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
)
from resolveflow.documents.models import Document
from resolveflow.jobs.models import WorkflowJob
from resolveflow.rag.models import DraftReview, ResponseDraft
from resolveflow.services import erasure_journal
from resolveflow.services.auth import digest
from resolveflow.services.invitation_delivery import mailbox_hash
from resolveflow.services.invitation_files import UnverifiedFile, checksum, read_private
from resolveflow.services.invitation_inventory import private_directory
from resolveflow.workflows.contracts import TERMINAL
from resolveflow.workflows.models import WorkflowExecution
from resolveflow.workflows.storage import lock_key, thread_id


def workspace_plan(db, user_id, *, lock=False):
    query = (
        select(Workspace)
        .join(WorkspaceMembership)
        .where(WorkspaceMembership.user_id == user_id)
        .order_by(Workspace.id)
    )
    spaces = db.scalars(query.with_for_update(of=Workspace) if lock else query).all()
    empty = []
    blocked = []
    for space in spaces:
        members = db.execute(
            select(WorkspaceMembership.user_id, WorkspaceMembership.role, User.account_status)
            .join(User)
            .where(WorkspaceMembership.workspace_id == space.id)
        ).all()
        if not any(uid == user_id and role == MembershipRole.OWNER for uid, role, _ in members):
            continue
        if any(
            uid != user_id and role == MembershipRole.OWNER and state == AccountStatus.ACTIVE
            for uid, role, state in members
        ):
            continue
        if len(members) > 1 or any(
            db.scalar(select(model.id).where(model.workspace_id == space.id).limit(1))
            for model in (Ticket, Document, InvitationDelivery, WorkspaceInvitation)
        ):
            blocked.append(space.name)
        else:
            empty.append(space)
    return empty, blocked


def fence_work(db, user_id):
    # Use the same connection-level keys as RQ and the checkpoint runner. A busy
    # worker retains its lock across database commits and external calls.
    jobs = db.scalars(
        select(WorkflowJob)
        .join(WorkflowExecution)
        .where(
            or_(WorkflowExecution.requested_by == user_id, WorkflowJob.actor_id == user_id),
            WorkflowJob.status.in_(["queued", "running", "waiting_for_approval"]),
        )
        .with_for_update(of=WorkflowJob)
    ).all()
    owned = {job.execution_id: job for job in jobs}
    executions = db.scalars(
        select(WorkflowExecution)
        .where(
            or_(WorkflowExecution.requested_by == user_id, WorkflowExecution.id.in_(owned)),
            WorkflowExecution.status.not_in(TERMINAL),
        )
        .with_for_update()
    ).all()
    for job in jobs:
        if not db.scalar(select(func.pg_try_advisory_xact_lock(lock_key("job:" + str(job.id))))):
            raise HTTPException(409, detail="account_busy")
    for row in executions:
        if not db.scalar(
            select(func.pg_try_advisory_xact_lock(lock_key("execution:" + thread_id(row))))
        ):
            raise HTTPException(409, detail="account_busy")
        if row.requested_by != user_id or row.id not in owned or owned[row.id].actor_id != user_id:
            raise HTTPException(409, detail="account_busy")
        row.status = "cancelled"
        row.finished_at = datetime.now(UTC)
        row.state = {**row.state, "status": "cancelled"}
    for job in jobs:
        job.delivery_id = uuid.uuid4()
        job.status = "cancelled"
        job.finished_at = datetime.now(UTC)
    sending = db.scalars(
        select(IdentityEmail).where(IdentityEmail.user_id == user_id).with_for_update()
    ).all()
    if any(row.status == "sending" for row in sending):
        raise HTTPException(409, detail="account_busy")
    if db.scalar(
        select(ResponseDraft.id)
        .where(
            ResponseDraft.requested_by == user_id, ResponseDraft.generation_status == "generating"
        )
        .limit(1)
    ):
        raise HTTPException(409, detail="account_busy")


def detach_invitations(db, user_id):
    files = []
    review = False
    records = db.scalars(
        select(InvitationDelivery)
        .where(
            or_(InvitationDelivery.recipient_id == user_id, InvitationDelivery.issuer_id == user_id)
        )
        .order_by(InvitationDelivery.id)
        .with_for_update()
    ).all()
    known = {record.id for record in records}
    for record in records:
        if record.recipient_id == user_id:
            files.append(
                dict(
                    root=record.mailbox_hash,
                    workspace=record.workspace_id.hex,
                    invitation=record.id.hex,
                    attempts=list(record.attempts),
                )
            )
            db.delete(record)
        else:
            record.retired_issuer_id = user_id
            record.issuer_id = None
            if record.status == "pending":
                record.status = "cancelled"
    grants = db.scalars(
        select(WorkspaceInvitation)
        .where(
            or_(WorkspaceInvitation.user_id == user_id, WorkspaceInvitation.issued_by == user_id)
        )
        .with_for_update()
    ).all()
    for grant in grants:
        if grant.id not in known:
            # A legacy filename is not ownership proof. Retain the reference for review.
            files.append(
                dict(
                    legacy=True,
                    workspace=grant.workspace_id.hex,
                    invitation=grant.id.hex,
                    recipient=grant.user_id.hex,
                    issuer=grant.issued_by.hex,
                    token_digest=grant.token_hash,
                )
            )
            review = True
        db.delete(grant)
    return files, review


def require_proof(user, session):
    now = datetime.now(UTC)
    if (
        not session.deletion_until
        or session.deletion_until <= now
        or session.deletion_version != user.credential_version
    ):
        raise HTTPException(403, detail="deletion_proof_required")


def erase(db: Session, user: User, session, settings):
    require_proof(user, session)
    identifier = user.id
    erase_rows(db, user)
    try:
        erasure_journal.commit_erasure(
            db, settings, identifier, lambda: require_proof(user, session)
        )
    except BackupError, OSError, ValueError:
        db.rollback()
        raise HTTPException(503, detail="erasure_journal_unavailable") from None
    return cleanup(db, settings, identifier)


def erase_rows(db, user):
    now = datetime.now(UTC)
    empty, blocked = workspace_plan(db, user.id, lock=True)
    if blocked:
        raise HTTPException(409, detail="workspace_transfer_required")
    fence_work(db, user.id)
    files, review = detach_invitations(db, user.id)
    provider = db.scalar(
        select(ProviderIdentity.subject).where(
            ProviderIdentity.user_id == user.id, ProviderIdentity.provider == "google"
        )
    )
    if provider and not db.scalar(
        select(func.pg_try_advisory_xact_lock(lock_key("google-subject:" + provider)))
    ):
        raise HTTPException(409, detail="account_busy")
    receipt = AccountErasure(
        id=user.id,
        deleted_at=now,
        subject_digest=digest("google:" + provider) if provider else None,
        files=files,
        review_required=bool(files) or review,
    )
    db.add(receipt)
    db.execute(
        update(Ticket)
        .where(Ticket.assigned_user_id == user.id)
        .values(assigned_user_id=None, version=Ticket.version + 1)
    )
    db.execute(delete(WorkspaceMembership).where(WorkspaceMembership.user_id == user.id))
    # Preserve joins, audit history and uniqueness of request IDs. The historical
    # actor gets a fresh UUID, no credentials, no membership and no sessions.
    historical = None
    for column in (
        TicketNote.author_id,
        TicketActivity.actor_id,
        Document.uploaded_by,
        ResponseDraft.requested_by,
        DraftReview.actor_id,
        WorkflowExecution.requested_by,
        WorkflowExecution.cancel_requested_by,
        WorkflowJob.actor_id,
    ):
        if db.scalar(select(column).where(column == user.id).limit(1)):
            if historical is None:
                historical = User(
                    email=f"deleted-{uuid.uuid4().hex}@accounts.invalid",
                    account_status=AccountStatus.INACTIVE,
                )
                db.add(historical)
                db.flush()
            db.execute(
                update(column.class_).where(column == user.id).values({column: historical.id})
            )
    # Assignment history also holds structured identifiers when a different user
    # made the change. Never rewrite free-form notes or shared customer text.
    old_id = str(user.id)
    for event in db.scalars(
        select(TicketActivity)
        .where(
            TicketActivity.action == "assignment_changed",
            or_(
                TicketActivity.details["from"].as_string() == old_id,
                TicketActivity.details["to"].as_string() == old_id,
            ),
        )
        .with_for_update()
    ):
        event.details = {
            **event.details,
            **{key: None for key in ("from", "to") if event.details.get(key) == old_id},
        }
    for space in empty:
        db.delete(space)
    db.flush()
    # FK cascades remove provider identities, sessions, OAuth and email grants.
    db.delete(user)
    receipt.deleted_at = datetime.now(UTC)
    db.flush()


def remove_verified(root, item):
    # Directories and links are never followed. Only committed bytes under the
    # recorded mailbox/workspace/invitation can be removed by this worker.
    key = uuid.UUID(hex=item["invitation"]).hex
    workspace = uuid.UUID(hex=item["workspace"]).hex
    attempts = item["attempts"]
    if not 1 <= len(attempts) <= 8 or not all(re.fullmatch(r"[0-9a-f]{64}", h) for h in attempts):
        raise UnverifiedFile
    names = [(key, attempts[-1]), *((f"{key}.{h}.part", h) for h in attempts)]
    try:
        with private_directory(root) as root_fd, private_directory(workspace, root_fd) as folder:
            for name, expected in names:
                data = read_private(folder, name)
                if data is not None:
                    if checksum(data) != expected:
                        raise UnverifiedFile
                    try:
                        os.unlink(name, dir_fd=folder)
                    except FileNotFoundError:
                        continue
            os.fsync(folder)
    except FileNotFoundError:
        # A missing workspace folder contains no objects at these exact paths.
        if not root.is_dir():
            raise UnverifiedFile from None


def cleanup(db, settings, identifier):
    receipt = db.get(AccountErasure, identifier, with_for_update=True, populate_existing=True)
    if not receipt:
        return False
    remaining = []
    for item in receipt.files:
        try:
            if item.get("legacy") or item["root"] != mailbox_hash(settings):
                raise UnverifiedFile
            remove_verified(settings.invitation_delivery_root, item)
        except UnverifiedFile, OSError:
            remaining.append(item)
    receipt.files = remaining
    receipt.review_required = bool(remaining)
    db.commit()
    return not remaining
