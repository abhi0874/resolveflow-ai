"""Local mailbox reconciliation. Database IDs and content commitments are authoritative."""

import json
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from resolveflow.core.config import Settings
from resolveflow.db.models import (
    AccountStatus,
    InvitationDelivery,
    MembershipRole,
    User,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
)
from resolveflow.documents.storage import LocalFileStorage
from resolveflow.services.auth import digest
from resolveflow.services.authorization import Permission, access, check_member_change
from resolveflow.services.invitation_files import UnverifiedFile, checksum, read_private


def pending(workspace_id: uuid.UUID) -> tuple[ColumnElement[bool], ...]:
    return (
        WorkspaceInvitation.workspace_id == workspace_id,
        WorkspaceInvitation.consumed_at.is_(None),
        WorkspaceInvitation.revoked_at.is_(None),
        WorkspaceInvitation.expires_at > datetime.now(UTC),
    )


def mailbox_hash(settings: Settings) -> str:
    return digest(str(settings.invitation_delivery_root.resolve()))


def message(intent: InvitationDelivery, workspace: Workspace) -> bytes:
    return json.dumps(
        {
            "kind": "local_synthetic_invitation",
            "version": 2,
            "invitation_id": str(intent.id),
            "workspace_id": str(intent.workspace_id),
            "recipient_id": str(intent.recipient_id),
            "issued_by": str(intent.issuer_id),
            "recipient": intent.email,
            "workspace": workspace.name,
            "token": secrets.token_urlsafe(32),
            "expires_at": intent.expires_at.isoformat(),
        }
    ).encode()


def allowed(db: Session, workspace: Workspace, intent: InvitationDelivery) -> bool:
    target = db.scalar(
        select(User)
        .where(User.id == intent.recipient_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    issuer = db.get(User, intent.issuer_id, populate_existing=True)
    if (
        not target
        or target.email != intent.email
        or target.account_status != AccountStatus.ACTIVE
        or target.credential_version != intent.credential_version
        or not issuer
        or issuer.account_status != AccountStatus.ACTIVE
        or intent.expires_at <= datetime.now(UTC)
        or db.scalar(
            select(WorkspaceMembership.id).where(
                WorkspaceMembership.workspace_id == workspace.id,
                WorkspaceMembership.user_id == target.id,
            )
        )
    ):
        return False
    try:
        _, member = access(db, issuer, workspace.id, Permission.MEMBERS)
        check_member_change(db, member, None, MembershipRole(intent.role))
    except HTTPException:
        return False
    return True


def deliver(
    db: Session, settings: Settings, identifier: uuid.UUID, material: bytes | None = None
) -> WorkspaceInvitation | None:
    if settings.environment == "production" or settings.invitation_delivery != "local":
        raise HTTPException(503)
    storage = LocalFileStorage(settings.invitation_delivery_root, require_owner=True)
    # A replacement token must be committed by digest BEFORE writing its bytes.
    # A competing recovery can finish first; reacquire and inspect on every turn.
    while True:
        workspace_id = db.scalar(
            select(InvitationDelivery.workspace_id).where(InvitationDelivery.id == identifier)
        )
        if workspace_id is None:
            return None
        workspace = db.scalar(
            select(Workspace).where(Workspace.id == workspace_id).with_for_update()
        )
        intent = db.get(
            InvitationDelivery, identifier, with_for_update=True, populate_existing=True
        )
        if intent is None or intent.mailbox_hash != mailbox_hash(settings):
            db.rollback()
            return None
        if intent.status == "delivered":
            grant = db.get(WorkspaceInvitation, identifier)
            db.commit()
            return grant
        if intent.status != "pending":
            db.rollback()
            return None
        if not allowed(db, workspace, intent):
            intent.status = "cancelled"
            db.commit()
            return None
        expected = intent.attempts[-1]
        key = identifier.hex
        try:
            with storage.directory(workspace_id, key) as folder:
                final = read_private(folder, key)
                stage = read_private(folder, f"{key}.{expected}.part")
            if final is not None:
                if checksum(final) != expected:
                    raise UnverifiedFile
                material = final
            elif stage is not None and checksum(stage) == expected:
                material = stage
            elif material is not None and checksum(material) != expected:
                db.rollback()  # Another delivery attempt owns the current commitment.
                return None
            elif stage is not None or material is None:
                # An incomplete stage stays byte-for-byte intact and recorded. Recover
                # at a fresh committed name. Never unlink a mismatching or legacy file.
                if len(intent.attempts) >= 8:
                    raise UnverifiedFile
                material = message(intent, workspace)
                intent.attempts = [*intent.attempts, checksum(material)]
                db.commit()
                continue
            storage.save(workspace_id, key, material, True)
        except UnverifiedFile:
            intent.status = "held"
            db.commit()
            return None
        except OSError:
            db.rollback()
            raise HTTPException(503) from None

        db.execute(
            update(WorkspaceInvitation)
            .where(
                *pending(workspace_id),
                WorkspaceInvitation.user_id == intent.recipient_id,
            )
            .values(revoked_at=datetime.now(UTC))
        )
        grant = WorkspaceInvitation(
            id=identifier,
            workspace_id=workspace_id,
            user_id=intent.recipient_id,
            issued_by=intent.issuer_id,
            email=intent.email,
            role=MembershipRole(intent.role),
            token_hash=digest(json.loads(material)["token"]),
            expires_at=intent.expires_at,
        )
        db.add(grant)
        intent.status = "delivered"
        db.commit()
        return grant
