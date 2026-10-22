"""Opaque PostgreSQL sessions and synchronizer CSRF tokens; no browser-held JWTs."""

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from resolveflow.core.security import is_document_upload
from resolveflow.db.models import AccountStatus, AuthRateLimit, AuthSession, User
from resolveflow.db.session import get_session

DB = Annotated[Session, Depends(get_session)]
# RFC 9106 low-memory profile: Argon2id, 64 MiB, 3 iterations, 4 lanes.
HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def limited(db: Session, request: Request, action: str, email: str | None = None) -> None:
    """Shared atomic counters. Never trust client-supplied forwarding headers."""
    now = datetime.now(UTC)
    address = request.client.host if request.client else "unknown"
    keys = [(f"{action}:ip:{address}", 120 if action == "csrf" else 60)]
    if email is not None:
        keys.append((f"{action}:email:{email}", 10))
    exceeded = False
    for value, maximum in keys:
        stmt = insert(AuthRateLimit).values(
            key=digest(value), count=1, reset_at=now + timedelta(minutes=15)
        )
        count = db.scalar(
            stmt.on_conflict_do_update(
                index_elements=[AuthRateLimit.key],
                set_={
                    "count": case(
                        (AuthRateLimit.reset_at <= now, 1), else_=AuthRateLimit.count + 1
                    ),
                    "reset_at": case(
                        (AuthRateLimit.reset_at <= now, now + timedelta(minutes=15)),
                        else_=AuthRateLimit.reset_at,
                    ),
                },
            ).returning(AuthRateLimit.count)
        )
        exceeded = exceeded or count > maximum
    db.commit()  # Failed logins must not roll back their rate-limit increments.
    if exceeded:
        raise HTTPException(429, headers={"Retry-After": "900"})


def current_session(request: Request, db: Session) -> AuthSession | None:
    token = request.cookies.get(request.app.state.settings.cookie_name, "")
    if len(token) != 43:
        return None
    return db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == digest(token), AuthSession.expires_at > datetime.now(UTC)
        )
    )


def require_csrf(request: Request, db: DB) -> AuthSession:
    config = request.app.state.settings
    origin = request.headers.get("origin")
    if origin not in config.trusted_origins:
        raise HTTPException(403)
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403)
    expected_type = (
        "application/octet-stream"
        if is_document_upload(request.method, request.url.path)
        else "application/json"
    )
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != expected_type:
        raise HTTPException(415)
    session = current_session(request, db)
    supplied = request.headers.get("x-csrf-token", "")
    if (
        session is None
        or not re.fullmatch(r"[A-Za-z0-9_-]{43}", supplied)
        or not secrets.compare_digest(supplied, session.csrf_token)
    ):
        raise HTTPException(403)
    return session


CSRF = Annotated[AuthSession, Depends(require_csrf)]


def authenticated(request: Request, db: DB) -> User:
    session = current_session(request, db)
    user = db.get(User, session.user_id) if session and session.user_id else None
    if user is None or user.account_status != AccountStatus.ACTIVE:
        raise HTTPException(401)
    return user


CurrentUser = Annotated[User, Depends(authenticated)]


def issue_session(
    db: Session, request: Request, response: Response, user: User | None
) -> AuthSession:
    config = request.app.state.settings
    previous = current_session(request, db)
    if previous:
        db.delete(previous)
    token = secrets.token_urlsafe(32)
    seconds = config.session_hours * 3600 if user else 600
    session = AuthSession(
        token_hash=digest(token),
        user_id=user.id if user else None,
        csrf_token=secrets.token_urlsafe(32),
        expires_at=datetime.now(UTC) + timedelta(seconds=seconds),
    )
    db.add(session)
    db.commit()
    response.set_cookie(
        config.cookie_name,
        token,
        max_age=seconds,
        httponly=True,
        secure=config.environment == "production",
        samesite="lax",
        path="/",
    )
    return session


def valid_password(encoded: str, password: str) -> bool:
    try:
        return HASHER.verify(encoded, password)
    except VerificationError, InvalidHashError:
        return False


def clear_expired(db: Session) -> None:
    """Explicit maintenance, never deletes active sessions or application records."""
    now = datetime.now(UTC)
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    db.execute(delete(AuthRateLimit).where(AuthRateLimit.reset_at <= now))
    db.commit()
