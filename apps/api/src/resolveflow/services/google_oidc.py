"""Google authorization-code exchange. Only fixed Google HTTPS endpoints receive requests."""

import base64
import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from google.auth import exceptions
from google.oauth2 import id_token
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from resolveflow.db.models import (
    AccountErasure,
    AccountStatus,
    AuthSession,
    GoogleFlow,
    ProviderIdentity,
    User,
)
from resolveflow.services import identity
from resolveflow.services.auth import digest, issue_session, verification_allows
from resolveflow.workflows.storage import lock_key

AUTHORIZE = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
EMAIL = TypeAdapter(EmailStr)


def challenge(verifier):
    return (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )


def safe_destination(value):
    if re.fullmatch(r"/app(?:/[A-Za-z0-9-]+)*/?(?:\?[^\s#\\\x00-\x1f\x7f]*)?", value):
        return value
    return "/app"


def begin(db, session, settings, destination, *, deletion_version=None):
    state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
    if deletion_version is not None:
        session.deletion_digest = digest("google-deletion:" + state)
    values = dict(
        started_at=datetime.now(UTC),
        deletion_version=deletion_version,
        state_hash=digest(state),
        session_hash=session.token_hash,
        nonce_hash=digest(nonce),
        verifier=verifier,
        destination=safe_destination(destination),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    db.execute(
        insert(GoogleFlow)
        .values(**values)
        .on_conflict_do_update(index_elements=[GoogleFlow.session_hash], set_=values)
    )
    db.commit()
    return (
        AUTHORIZE
        + "?"
        + urlencode(
            dict(
                client_id=settings.google_client_id,
                redirect_uri=settings.google_redirect_uri,
                response_type="code",
                scope="openid email profile",
                **(
                    {"claims": '{"id_token":{"auth_time":{"essential":true}}}'}
                    if deletion_version is not None
                    else {}
                ),
                state=state,
                nonce=nonce,
                code_challenge=challenge(verifier),
                code_challenge_method="S256",
            )
        )
    )


def provider_client():
    return httpx.Client(timeout=5, follow_redirects=False, trust_env=False)


def exchange(settings, code, flow):
    with provider_client() as client:
        response = client.post(
            TOKEN,
            data=dict(
                grant_type="authorization_code",
                code=code,
                code_verifier=flow.verifier,
                client_id=settings.google_client_id,
                redirect_uri=settings.google_redirect_uri,
                client_secret=settings.google_client_secret.get_secret_value(),
            ),
        )
        response.raise_for_status()

        def fetch_certs(url, method="GET", **kwargs):
            # google-auth supplies its pinned Google certificate URL.
            result = client.get(url)
            return SimpleNamespace(status=result.status_code, data=result.content)

        claims = id_token.verify_oauth2_token(
            response.json()["id_token"], fetch_certs, audience=settings.google_client_id
        )
    if (
        claims.get("email_verified") is not True
        or claims.get("azp", settings.google_client_id) != settings.google_client_id
        or not isinstance(claims.get("nonce"), str)
        or not secrets.compare_digest(digest(claims["nonce"]), flow.nonce_hash)
        or not isinstance(claims.get("sub"), str)
        or not re.fullmatch(r"[!-~]{1,255}", claims["sub"])
    ):
        raise ValueError("Invalid identity claims")
    email = EMAIL.validate_python(claims["email"]).lower()
    if len(email) > 320:
        raise ValueError("Invalid email")
    if flow.deletion_version is not None:
        authenticated = claims.get("auth_time")
        # Require a signed Google authentication event during this particular ceremony.
        if (
            type(authenticated) is not int
            or not flow.started_at
            or type(claims.get("iat")) is not int
            or authenticated > claims["iat"]
            or not flow.started_at.timestamp()
            <= authenticated
            <= int(datetime.now(UTC).timestamp())
        ):
            raise ValueError("Fresh Google authentication required")
    return claims["sub"], email


def complete(db, request, response, session, body):
    settings = request.app.state.settings
    session_hash = session.token_hash
    flow = db.execute(
        delete(GoogleFlow)
        .where(
            GoogleFlow.state_hash == digest(body.state),
            GoogleFlow.session_hash == session_hash,
            GoogleFlow.expires_at > datetime.now(UTC),
        )
        .returning(GoogleFlow)
    ).scalar_one_or_none()
    db.commit()  # Replays must fail even after provider denial, timeouts or validation failure.
    if (
        flow is None
        or not body.code
        or (flow.deletion_version is None) != (session.user_id is None)
    ):
        raise HTTPException(400)
    try:
        subject, email = exchange(settings, body.code.get_secret_value(), flow)
    except (
        httpx.HTTPError,
        exceptions.GoogleAuthError,
        ValueError,
        KeyError,
        TypeError,
    ):
        raise HTTPException(400) from None
    if flow.deletion_version is not None:
        user = db.scalar(
            select(User)
            .join(ProviderIdentity)
            .where(
                User.id == session.user_id,
                ProviderIdentity.provider == "google",
                ProviderIdentity.subject == subject,
            )
            .with_for_update(of=User)
            .execution_options(populate_existing=True)
        )
        eligible = db.scalar(
            select(AuthSession)
            .where(
                AuthSession.token_hash == session_hash,
                AuthSession.user_id == session.user_id,
                AuthSession.expires_at > datetime.now(UTC),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            not eligible
            or not eligible.deletion_digest
            or not secrets.compare_digest(
                eligible.deletion_digest, digest("google-deletion:" + body.state)
            )
            or flow.expires_at <= datetime.now(UTC)
            or not user
            or user.account_status != AccountStatus.ACTIVE
            or user.password_hash
            or user.credential_version != flow.deletion_version
        ):
            raise HTTPException(400)
        eligible.deletion_digest = None
        eligible.deletion_version = user.credential_version
        eligible.deletion_until = min(flow.expires_at, datetime.now(UTC) + timedelta(minutes=3))
        db.commit()
        return {"destination": "/app/settings/account?delete=confirm"}
    # Logout, expiry or another sign-in during the exchange cancels this callback.
    eligible = db.scalar(
        select(AuthSession)
        .where(
            AuthSession.token_hash == session_hash,
            AuthSession.user_id.is_(None),
            AuthSession.expires_at > datetime.now(UTC),
        )
        .with_for_update()
    )
    if not eligible:
        raise HTTPException(400)
    db.execute(select(func.pg_advisory_xact_lock(lock_key("google-subject:" + subject))))
    previous = db.scalar(
        select(AccountErasure.deleted_at)
        .where(AccountErasure.subject_digest == digest("google:" + subject))
        .order_by(AccountErasure.deleted_at.desc())
        .limit(1)
    )
    if previous and (not flow.started_at or flow.started_at <= previous):
        raise HTTPException(400)
    match = db.execute(
        select(User, ProviderIdentity)
        .join(ProviderIdentity)
        .where(ProviderIdentity.provider == "google", ProviderIdentity.subject == subject)
        .with_for_update(of=User)
    ).one_or_none()
    bound_email = email
    if match is None:
        # Both the canonical email and the provider subject have database uniqueness.
        # A collision rolls back the new user; it never attaches a sign-in method.
        try:
            user = User(email=email)
            db.add(user)
            db.flush()
            db.add(ProviderIdentity(provider="google", subject=subject, user_id=user.id))
            db.flush()
            identity.queue_email(db, user, "verify", settings)
        except IntegrityError:
            db.rollback()
            raise HTTPException(400) from None
    else:
        user, provider = match
        bound_email = provider.original_email or user.email
    if user.account_status != AccountStatus.ACTIVE or bound_email != email:
        raise HTTPException(400)
    issue_session(db, request, response, user)
    return {
        "destination": flow.destination
        if verification_allows(settings, user)
        else "/verification-required"
    }
