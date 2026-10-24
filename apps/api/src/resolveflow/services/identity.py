"""Single-use identity actions. All operations lock user before token rows."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, select, update

from resolveflow.db.models import (
    AccountStatus,
    AuthSession,
    IdentityAudit,
    IdentityEmail,
    User,
    WorkspaceInvitation,
)
from resolveflow.services.auth import HASHER, digest, email_proven, valid_password

GENERIC = {
    "status": "accepted",
    "message": (
        "If the account is eligible, an email will arrive. Check your inbox and spam folder."
    ),
}


def queue_email(db, user, purpose, settings):
    now = datetime.now(UTC)
    # The caller holds the user lock (or owns its uncommitted registration).
    recent = db.scalar(
        select(IdentityEmail).where(
            IdentityEmail.user_id == user.id,
            IdentityEmail.purpose == purpose,
            IdentityEmail.created_at > now - timedelta(seconds=60),
        )
    )
    if recent is not None:
        return
    db.execute(
        update(IdentityEmail)
        .where(
            IdentityEmail.user_id == user.id,
            IdentityEmail.purpose == purpose,
            IdentityEmail.consumed_at.is_(None),
            IdentityEmail.invalidated_at.is_(None),
        )
        .values(invalidated_at=now, status="cancelled")
    )
    # Generate a hash now; delivery rotates it immediately before sending. No raw secret at rest.
    row = IdentityEmail(
        user_id=user.id,
        email=user.email,
        purpose=purpose,
        credential_version=user.credential_version or 1,
        token_hash=digest(secrets.token_urlsafe(32)),
        expires_at=now + timedelta(minutes=30 if purpose == "reset" else 1440),
        available_at=now,
        status="pending" if settings.email_delivery != "disabled" else "failed",
        error_code="delivery_disabled" if settings.email_delivery == "disabled" else None,
    )
    db.add(row)
    db.add(IdentityAudit(user_id=user.id, event=f"{purpose}_requested"))


def request_email(db, email, purpose, settings):
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    if (
        user
        and user.account_status == AccountStatus.ACTIVE
        and (purpose == "reset" or not email_proven(settings, user))
    ):
        queue_email(db, user, purpose, settings)
    db.commit()


def consume(db, raw, purpose, actor_id=None, new_password=None, *, settings):
    hashed = digest(raw)
    candidate = db.scalar(
        select(IdentityEmail).where(
            IdentityEmail.token_hash == hashed, IdentityEmail.purpose == purpose
        )
    )
    if candidate is None:
        raise HTTPException(400, detail="identity_link_invalid")
    user = db.scalar(
        select(User)
        .where(User.id == candidate.user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    row = db.scalar(
        select(IdentityEmail)
        .where(IdentityEmail.id == candidate.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    now = datetime.now(UTC)
    if (
        not user
        or user.account_status != AccountStatus.ACTIVE
        or not row
        or not secrets.compare_digest(row.token_hash, hashed)
        or row.consumed_at
        or row.invalidated_at
        or row.expires_at <= now
        or row.status not in {"sending", "sent"}
        or row.email != user.email
        or row.credential_version != user.credential_version
        or (settings.environment == "production" and row.delivery_source != "smtp")
        or (actor_id is not None and actor_id != user.id)
    ):
        raise HTTPException(400, detail="identity_link_invalid")
    row.consumed_at = now
    if purpose == "verify":
        # Prevent activating an attacker's pre-registration with an attacker-known password.
        if not new_password or not valid_password(user.password_hash, new_password):
            raise HTTPException(400, detail="identity_link_invalid")
        user.email_verified_at = now
        user.verified_email = user.email
        user.email_verification_source = row.delivery_source
    else:
        user.password_hash = HASHER.hash(new_password)
        user.credential_version += 1
        # Recovery proves control of this address, and invalidates every outstanding grant.
        user.email_verified_at = now
        user.verified_email = user.email
        user.email_verification_source = row.delivery_source
        db.execute(
            update(WorkspaceInvitation)
            .where(
                WorkspaceInvitation.user_id == user.id, WorkspaceInvitation.consumed_at.is_(None)
            )
            .values(revoked_at=now)
        )
    db.execute(
        update(IdentityEmail)
        .where(
            IdentityEmail.user_id == user.id,
            IdentityEmail.id != row.id,
            IdentityEmail.consumed_at.is_(None),
        )
        .values(invalidated_at=now, status="cancelled")
    )
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.add(
        IdentityAudit(
            user_id=user.id, event="email_verified" if purpose == "verify" else "password_reset"
        )
    )
    db.commit()
    return {"status": "complete"}
