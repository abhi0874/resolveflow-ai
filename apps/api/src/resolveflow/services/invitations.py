"""No membership grant without recipient-session and mailbox-token possession.

Only an opt-in private local delivery sink exists. It is not a production email
adapter or proof of a real mailbox; production issuance fails closed.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from resolveflow.core.config import Settings
from resolveflow.db.models import (
    AccountStatus,
    AuthSession,
    InvitationDelivery,
    User,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
)
from resolveflow.schemas.auth import MemberInput
from resolveflow.services import invitation_delivery
from resolveflow.services.auth import active_session, digest
from resolveflow.services.authorization import Permission, access, check_member_change

pending = invitation_delivery.pending


def issue(
    db: Session, actor: User, workspace_id: uuid.UUID, body: MemberInput, settings: Settings
) -> WorkspaceInvitation:
    space, member = access(db, actor, workspace_id, Permission.MEMBERS, lock=True)
    check_member_change(db, member, None, body.role)
    if settings.invitation_delivery != "local" or settings.environment == "production":
        raise HTTPException(503)
    target = db.scalar(select(User).where(User.email == str(body.email)).with_for_update())
    if target is None or target.account_status != AccountStatus.ACTIVE:
        raise HTTPException(422)
    if db.scalar(
        select(WorkspaceMembership.id).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == target.id,
        )
    ):
        raise HTTPException(409)
    now = datetime.now(UTC)
    # Supersede pending deliveries as well as checking outstanding grants.
    outstanding = (
        select(WorkspaceInvitation.user_id)
        .where(*pending(workspace_id), WorkspaceInvitation.user_id != target.id)
        .union(
            select(InvitationDelivery.recipient_id).where(
                InvitationDelivery.workspace_id == workspace_id,
                InvitationDelivery.status == "pending",
                InvitationDelivery.expires_at > now,
                InvitationDelivery.recipient_id != target.id,
            )
        )
    )
    if db.scalar(select(func.count()).select_from(outstanding.subquery())) >= 50:
        raise HTTPException(429)
    db.execute(
        update(InvitationDelivery)
        .where(
            InvitationDelivery.workspace_id == workspace_id,
            InvitationDelivery.recipient_id == target.id,
            InvitationDelivery.status == "pending",
        )
        .values(status="cancelled")
    )
    intent = InvitationDelivery(
        id=uuid.uuid4(),
        workspace_id=space.id,
        recipient_id=target.id,
        issuer_id=actor.id,
        email=target.email,
        role=body.role.value,
        credential_version=target.credential_version,
        expires_at=now + timedelta(hours=24),
        mailbox_hash=invitation_delivery.mailbox_hash(settings),
        status="pending",
    )
    material = invitation_delivery.message(intent, space)
    intent.attempts = [invitation_delivery.checksum(material)]
    db.add(intent)
    db.commit()  # No private file or usable grant exists before this commit.
    grant = invitation_delivery.deliver(db, settings, intent.id, material)
    if grant is None:
        raise HTTPException(503)
    return grant


def accept(
    db: Session, user: User, token: str, session_hash: str
) -> tuple[Workspace, WorkspaceMembership]:
    token_hash = digest(token)
    candidate = db.scalar(
        select(WorkspaceInvitation).where(
            WorkspaceInvitation.token_hash == token_hash,
            WorkspaceInvitation.user_id == user.id,
        )
    )
    if candidate is None:
        raise HTTPException(400)
    # Same workspace -> user -> invitation order as issuance; serialize competing
    # accepts, revocations and membership mutations before checking current state.
    space = db.scalar(
        select(Workspace).where(Workspace.id == candidate.workspace_id).with_for_update()
    )
    target = db.scalar(
        select(User)
        .where(User.id == user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    invitation = db.scalar(
        select(WorkspaceInvitation)
        .where(
            WorkspaceInvitation.id == candidate.id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if space is None or target is None or invitation is None:
        raise HTTPException(400)
    now = datetime.now(UTC)
    if (
        invitation.consumed_at
        or invitation.revoked_at
        or invitation.expires_at <= now
        or target.account_status != AccountStatus.ACTIVE
        or target.email != invitation.email
    ):
        raise HTTPException(400)
    active_session(db, session_hash, user.id)
    issuer = db.get(User, invitation.issued_by, populate_existing=True)
    if issuer is None or issuer.account_status != AccountStatus.ACTIVE:
        raise HTTPException(400)
    # Invitations cannot preserve permissions of an issuer who has since lost them.
    _, member = access(db, issuer, space.id, Permission.MEMBERS)
    check_member_change(db, member, None, invitation.role)
    existing = db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == space.id,
            WorkspaceMembership.user_id == user.id,
        )
    )
    if existing is not None:
        raise HTTPException(409)
    membership = WorkspaceMembership(workspace_id=space.id, user_id=user.id, role=invitation.role)
    target.email_verified_at = now
    target.verified_email = target.email
    target.email_verification_source = "local"
    invitation.consumed_at = now
    db.add(membership)
    # Establishing identity revokes pre-verification sessions; the route issues a
    # new current session in this same transaction. Never expose the token in URLs.
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.flush()
    return space, membership


def revoke(db: Session, actor: User, workspace_id: uuid.UUID, invitation_id: uuid.UUID) -> None:
    _, member = access(db, actor, workspace_id, Permission.MEMBERS, lock=True)
    invitation = db.scalar(
        select(WorkspaceInvitation)
        .where(
            WorkspaceInvitation.workspace_id == workspace_id,
            WorkspaceInvitation.id == invitation_id,
        )
        .with_for_update()
    )
    if invitation is None:
        raise HTTPException(404)
    check_member_change(db, member, None, invitation.role)
    invitation.revoked_at = datetime.now(UTC)
    db.commit()
