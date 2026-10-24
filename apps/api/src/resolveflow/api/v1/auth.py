from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from resolveflow.db.models import AccountStatus, User
from resolveflow.schemas.auth import (
    AcceptInvitationInput,
    CsrfResponse,
    IdentityEmailInput,
    LoginInput,
    RegisterInput,
    ResetPasswordInput,
    UserResponse,
    VerifyEmailInput,
    WorkspaceResponse,
)
from resolveflow.services import identity, invitations
from resolveflow.services.auth import (
    CSRF,
    DB,
    DUMMY_HASH,
    HASHER,
    CurrentUser,
    current_session,
    issue_session,
    limited,
    valid_password,
    verification_allows,
)
from resolveflow.services.authorization import workspace_response

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/invitations/accept", response_model=WorkspaceResponse, status_code=201)
def accept_invitation(
    body: AcceptInvitationInput,
    request: Request,
    response: Response,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
):
    limited(db, request, "accept_invitation", user.email)
    config = request.app.state.settings
    if config.invitation_delivery != "local" or config.environment == "production":
        raise HTTPException(503)
    space, membership = invitations.accept(db, user, body.token.get_secret_value())
    issue_session(db, request, response, user)
    return workspace_response(space, membership)


@router.get("/csrf", response_model=CsrfResponse)
def csrf(request: Request, response: Response, db: DB):
    session = current_session(request, db)
    if session is None:
        limited(db, request, "csrf")
        session = issue_session(db, request, response, None)
    return CsrfResponse(csrf_token=session.csrf_token)


@router.post("/register", response_model=UserResponse | dict[str, str], status_code=201)
def register(body: RegisterInput, request: Request, response: Response, db: DB, csrf: CSRF):
    limited(db, request, "register", str(body.email))
    encoded = HASHER.hash(
        body.password.get_secret_value()
    )  # Equal expensive work for duplicate email.
    config = request.app.state.settings
    user = User(email=str(body.email), password_hash=encoded)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        if config.email_verification_required:
            response.status_code = 202
            return identity.GENERIC
        raise HTTPException(409) from None
    identity.queue_email(db, user, "verify", config)
    if config.email_verification_required:
        db.commit()
        response.status_code = 202
        return identity.GENERIC
    issue_session(db, request, response, user)
    return user


@router.post("/login", response_model=UserResponse)
def login(body: LoginInput, request: Request, response: Response, db: DB, csrf: CSRF):
    limited(db, request, "login", str(body.email))
    user = db.scalar(select(User).where(User.email == str(body.email)).with_for_update())
    verified = valid_password(
        user.password_hash if user else DUMMY_HASH, body.password.get_secret_value()
    )
    if not verified or user is None or user.account_status != AccountStatus.ACTIVE:
        raise HTTPException(401)
    config = request.app.state.settings
    if not verification_allows(config, user):
        raise HTTPException(403, detail="email_verification_required")
    if HASHER.check_needs_rehash(user.password_hash):
        user.password_hash = HASHER.hash(body.password.get_secret_value())
    issue_session(db, request, response, user)
    return user


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser):
    return user


@router.post("/verification/request", status_code=202)
def resend(body: IdentityEmailInput, request: Request, db: DB, csrf: CSRF):
    limited(db, request, "verification_request", str(body.email))
    identity.request_email(db, str(body.email), "verify", request.app.state.settings)
    return identity.GENERIC


@router.post("/password/request", status_code=202)
def forgot(body: IdentityEmailInput, request: Request, db: DB, csrf: CSRF):
    limited(db, request, "password_request", str(body.email))
    identity.request_email(db, str(body.email), "reset", request.app.state.settings)
    return identity.GENERIC


@router.post("/verification/confirm")
def verify(body: VerifyEmailInput, request: Request, db: DB, csrf: CSRF):
    limited(db, request, "verification_confirm")
    return identity.consume(
        db,
        body.token.get_secret_value(),
        "verify",
        csrf.user_id,
        body.password.get_secret_value(),
        settings=request.app.state.settings,
    )


@router.post("/password/confirm")
def reset(body: ResetPasswordInput, request: Request, db: DB, csrf: CSRF):
    limited(db, request, "password_confirm")
    return identity.consume(
        db,
        body.token.get_secret_value(),
        "reset",
        csrf.user_id,
        body.password.get_secret_value(),
        settings=request.app.state.settings,
    )


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DB, csrf: CSRF):
    db.delete(csrf)
    db.commit()
    config = request.app.state.settings
    response.delete_cookie(
        config.cookie_name,
        httponly=True,
        secure=config.environment == "production",
        samesite="lax",
        path="/",
    )
