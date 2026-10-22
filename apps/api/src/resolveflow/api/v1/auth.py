from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from resolveflow.db.models import AccountStatus, User
from resolveflow.schemas.auth import CsrfResponse, LoginInput, RegisterInput, UserResponse
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
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/csrf", response_model=CsrfResponse)
def csrf(request: Request, response: Response, db: DB):
    session = current_session(request, db)
    if session is None:
        limited(db, request, "csrf")
        session = issue_session(db, request, response, None)
    return CsrfResponse(csrf_token=session.csrf_token)


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterInput, request: Request, response: Response, db: DB, csrf: CSRF):
    limited(db, request, "register", str(body.email))
    encoded = HASHER.hash(
        body.password.get_secret_value()
    )  # Equal expensive work for duplicate email.
    user = User(email=str(body.email), password_hash=encoded)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409) from None
    issue_session(db, request, response, user)
    return user


@router.post("/login", response_model=UserResponse)
def login(body: LoginInput, request: Request, response: Response, db: DB, csrf: CSRF):
    limited(db, request, "login", str(body.email))
    user = db.scalar(select(User).where(User.email == str(body.email)))
    verified = valid_password(
        user.password_hash if user else DUMMY_HASH, body.password.get_secret_value()
    )
    if not verified or user is None or user.account_status != AccountStatus.ACTIVE:
        raise HTTPException(401)
    if HASHER.check_needs_rehash(user.password_hash):
        user.password_hash = HASHER.hash(body.password.get_secret_value())
    issue_session(db, request, response, user)
    return user


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser):
    return user


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
