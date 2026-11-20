import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import Field, SecretStr
from sqlalchemy import select, update

from resolveflow.db.models import AccountStatus, AuthSession, ProviderIdentity, User
from resolveflow.schemas.account import (
    EmailChange,
    EmailProof,
    PasswordChange,
    ProfileResponse,
    ProfileUpdate,
)
from resolveflow.schemas.auth import InputModel
from resolveflow.services import account, erasure, google_oidc
from resolveflow.services.auth import (
    CSRF,
    DB,
    HASHER,
    CurrentUser,
    active_session,
    clear_cookie,
    digest,
    limited,
)

router = APIRouter(prefix="/account", tags=["personal settings"])


def lock_actor(db, request, actor, csrf, action):
    if csrf.user_id != actor.id:
        raise HTTPException(403)
    limited(db, request, action, str(actor.id))
    user = db.scalar(
        select(User)
        .where(User.id == actor.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None or user.account_status != AccountStatus.ACTIVE:
        raise HTTPException(401)
    active_session(db, csrf.token_hash, user.id)
    return user


@router.get("/profile", response_model=ProfileResponse)
def read_profile(response: Response, db: DB, actor: CurrentUser):
    response.headers["Cache-Control"] = "private, no-store"
    return account.profile(db, actor)


@router.patch("/profile", response_model=ProfileResponse)
def edit_profile(
    body: ProfileUpdate,
    request: Request,
    response: Response,
    db: DB,
    actor: CurrentUser,
    csrf: CSRF,
):
    user = lock_actor(db, request, actor, csrf, "profile_edit")
    user.display_name = body.display_name or None
    if "avatar_pixels" in body.model_fields_set:
        user.avatar_png = account.avatar_png(body.avatar_pixels) if body.avatar_pixels else None
    view = account.profile(db, user)
    db.commit()
    response.headers["Cache-Control"] = "private, no-store"
    return view


@router.post("/email/request", status_code=202)
def request_email(body: EmailChange, request: Request, db: DB, actor: CurrentUser, csrf: CSRF):
    user = lock_actor(db, request, actor, csrf, "email_change_request")
    return account.start_email_change(
        db,
        user,
        csrf.token_hash,
        str(body.email),
        body.current_password.get_secret_value() if body.current_password else None,
        request.app.state.settings,
    )


@router.post("/email/confirm", status_code=204)
def verify_new_email(
    body: EmailProof, request: Request, response: Response, db: DB, actor: CurrentUser, csrf: CSRF
):
    user = lock_actor(db, request, actor, csrf, "email_change_confirm")
    account.prove_email(
        db,
        user,
        csrf.token_hash,
        body.token.get_secret_value(),
        body.action,
        request.app.state.settings,
    )
    if body.action == "confirm":
        clear_cookie(request, response)


@router.post("/password", status_code=204)
def change_password(
    body: PasswordChange,
    request: Request,
    response: Response,
    db: DB,
    actor: CurrentUser,
    csrf: CSRF,
):
    user = lock_actor(db, request, actor, csrf, "password_change")
    account.require_password(user, body.current_password.get_secret_value())
    user.password_hash = HASHER.hash(body.password.get_secret_value())
    account.change_credentials(db, user, "password_changed")
    db.commit()
    clear_cookie(request, response)


class DeletionProof(InputModel):
    current_password: SecretStr | None = Field(default=None, min_length=1, max_length=128)


class DeleteConfirmation(InputModel):
    confirmation: Literal["DELETE"]
    challenge: SecretStr = Field(min_length=43, max_length=43)


@router.get("/deletion/impact")
def deletion_impact(response: Response, db: DB, actor: CurrentUser):
    response.headers["Cache-Control"] = "private, no-store"
    empty, blocked = erasure.workspace_plan(db, actor.id)
    return {"empty_workspaces": [s.name for s in empty], "blocked_workspaces": blocked}


@router.post("/deletion/reauthenticate")
def deletion_proof(body: DeletionProof, request: Request, db: DB, actor: CurrentUser, csrf: CSRF):
    user = lock_actor(db, request, actor, csrf, "account_deletion_proof")
    settings = request.app.state.settings
    csrf.deletion_digest = None
    csrf.deletion_until = None
    if user.password_hash:
        account.require_password(
            user, body.current_password.get_secret_value() if body.current_password else None
        )
        csrf.deletion_until = datetime.now(UTC) + timedelta(minutes=3)
        csrf.deletion_version = user.credential_version
        db.commit()
        return {"verified": True}
    if not settings.google_enabled or not db.scalar(
        select(ProviderIdentity.subject).where(
            ProviderIdentity.user_id == user.id, ProviderIdentity.provider == "google"
        )
    ):
        raise HTTPException(403)
    return {
        "url": google_oidc.begin(
            db, csrf, settings, "/app/settings/account", deletion_version=user.credential_version
        )
    }


@router.post("/deletion/challenge")
def deletion_challenge(
    request: Request, response: Response, db: DB, actor: CurrentUser, csrf: CSRF
):
    user = lock_actor(db, request, actor, csrf, "account_deletion_challenge")
    erasure.require_proof(user, csrf)
    challenge = secrets.token_urlsafe(32)
    csrf.deletion_digest = digest(challenge)
    db.commit()
    response.headers["Cache-Control"] = "private, no-store"
    return {"challenge": challenge}


@router.post("/deletion/confirm")
def delete_account(
    body: DeleteConfirmation,
    request: Request,
    response: Response,
    db: DB,
    actor: CurrentUser,
    csrf: CSRF,
):
    user = lock_actor(db, request, actor, csrf, "account_deletion_confirm")
    if not csrf.deletion_digest or not secrets.compare_digest(
        csrf.deletion_digest, digest(body.challenge.get_secret_value())
    ):
        raise HTTPException(403, detail="deletion_proof_required")
    session_hash, presented = csrf.token_hash, csrf.deletion_digest
    try:
        done = erasure.erase(db, user, csrf, request.app.state.settings)
    except HTTPException:
        db.rollback()
        # Consume this specific confirmation even when ownership or busy work blocks it.
        db.execute(
            update(AuthSession)
            .where(AuthSession.token_hash == session_hash, AuthSession.deletion_digest == presented)
            .values(deletion_digest=None)
        )
        db.commit()
        raise
    clear_cookie(request, response)
    response.headers["Cache-Control"] = "private, no-store"
    return {"cleanup": "complete" if done else "under_review"}
