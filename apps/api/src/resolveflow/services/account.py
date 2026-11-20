"""Personal settings and credential changes scoped to the locked session owner."""

import base64
import binascii
import secrets
import struct
import zlib
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from resolveflow.db.models import (
    AuthSession,
    IdentityAudit,
    IdentityEmail,
    ProviderIdentity,
    User,
    WorkspaceInvitation,
)
from resolveflow.services.auth import digest, email_proven, valid_password

AVATAR_SIZE = 56
ACCEPTED = {"status": "accepted"}


def profile(db, user: User):
    return {
        "display_name": user.display_name,
        "avatar": (
            "data:image/png;base64," + base64.b64encode(user.avatar_png).decode()
            if user.avatar_png
            else None
        ),
        "email": user.email,
        "email_verified": user.email_verified,
        "password_enabled": user.password_hash is not None,
        "google_linked": bool(google_identity(db, user)),
    }


def avatar_png(pixels: str) -> bytes:
    # Accept exactly 56x56 RGB pixels, never an uploaded file or URL. Generate
    # a fresh PNG with no metadata, active content or supplied image headers.
    try:
        raw = base64.b64decode(pixels, validate=True)
    except binascii.Error, ValueError:
        raise HTTPException(422) from None
    width = AVATAR_SIZE * 3
    if len(raw) != AVATAR_SIZE * width:
        raise HTTPException(422)

    def chunk(kind, data):
        payload = kind + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload))

    header = struct.pack(">IIBBBBB", AVATAR_SIZE, AVATAR_SIZE, 8, 2, 0, 0, 0)
    rows = b"".join(b"\0" + raw[i : i + width] for i in range(0, len(raw), width))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def google_identity(db, user):
    return db.scalar(
        select(ProviderIdentity).where(
            ProviderIdentity.user_id == user.id, ProviderIdentity.provider == "google"
        )
    )


def require_password(user, password):
    if not user.password_hash or not password or not valid_password(user.password_hash, password):
        raise HTTPException(403, detail="current_password_required")


def enqueue(db, user, email, purpose, session_hash=None):
    now = datetime.now(UTC)
    db.add(
        IdentityEmail(
            user_id=user.id,
            email=email,
            purpose=purpose,
            session_hash=session_hash,
            credential_version=user.credential_version,
            token_hash=digest(secrets.token_urlsafe(32)),
            expires_at=now + timedelta(minutes=30),
            available_at=now,
        )
    )


def start_email_change(db, user, session_hash, email, password, settings):
    if user.password_hash:
        require_password(user, password)
        purpose = "email_change"
    else:
        if not email_proven(settings, user) or google_identity(db, user) is None:
            raise HTTPException(403, detail="email_verification_required")
        purpose = "email_approve"
    if settings.email_delivery == "disabled":
        raise HTTPException(503)
    if email == user.email:
        return ACCEPTED
    now = datetime.now(UTC)
    db.execute(
        update(IdentityEmail)
        .where(
            IdentityEmail.user_id == user.id,
            IdentityEmail.purpose.in_(["email_approve", "email_change"]),
            IdentityEmail.consumed_at.is_(None),
            IdentityEmail.invalidated_at.is_(None),
        )
        .values(invalidated_at=now, status="cancelled")
    )
    # The address is deliberately not looked up here. Only a caller who proves
    # access to its inbox can reach the uniqueness check at final confirmation.
    enqueue(db, user, email, purpose, session_hash)
    db.add(IdentityAudit(user_id=user.id, event="email_change_requested"))
    db.commit()
    return ACCEPTED


def change_credentials(db, user, event):
    now = datetime.now(UTC)
    user.credential_version += 1
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.execute(
        update(WorkspaceInvitation)
        .where(
            WorkspaceInvitation.user_id == user.id,
            WorkspaceInvitation.consumed_at.is_(None),
            WorkspaceInvitation.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.execute(
        update(IdentityEmail)
        .where(
            IdentityEmail.user_id == user.id,
            IdentityEmail.consumed_at.is_(None),
            IdentityEmail.purpose != "email_notice",
        )
        .values(invalidated_at=now, status="cancelled")
    )
    db.add(IdentityAudit(user_id=user.id, event=event))


def prove_email(db, user, session_hash, raw, action, settings):
    purpose = "email_approve" if action == "approve" else "email_change"
    row = db.scalar(
        select(IdentityEmail)
        .where(
            IdentityEmail.token_hash == digest(raw),
            IdentityEmail.user_id == user.id,
            IdentityEmail.session_hash == session_hash,
            IdentityEmail.purpose == purpose,
        )
        .with_for_update()
    )
    now = datetime.now(UTC)
    if (
        not row
        or row.expires_at <= now
        or row.invalidated_at
        or row.consumed_at
        or row.credential_version != user.credential_version
        or row.status not in {"sending", "sent"}
        or (settings.environment == "production" and row.delivery_source != "smtp")
    ):
        raise HTTPException(400, detail="identity_link_invalid")
    row.consumed_at = now
    if action == "approve":
        if not email_proven(settings, user):
            raise HTTPException(400, detail="identity_link_invalid")
        enqueue(db, user, row.email, "email_change", session_hash)
        db.commit()
        return

    previous = user.email
    provider = google_identity(db, user)
    if provider is not None and provider.original_email is None:
        provider.original_email = previous
    user.email = row.email
    user.verified_email = row.email
    user.email_verified_at = now
    user.email_verification_source = row.delivery_source
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, detail="identity_link_invalid") from None
    change_credentials(db, user, "email_changed")
    enqueue(db, user, previous, "email_notice")
    db.commit()
