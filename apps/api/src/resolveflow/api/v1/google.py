from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import Field, SecretStr

from resolveflow.schemas.auth import InputModel
from resolveflow.services import google_oidc
from resolveflow.services.auth import CSRF, DB, current_session, limited

router = APIRouter(prefix="/auth/google", tags=["authentication"])


class Start(InputModel):
    destination: str = Field(default="/app", max_length=2048)


class Callback(InputModel):
    state: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    code: SecretStr | None = Field(default=None, min_length=1, max_length=2048)


@router.post("/start")
def start(body: Start, request: Request, db: DB, csrf: CSRF):
    settings = request.app.state.settings
    if not settings.google_enabled:
        raise HTTPException(503)
    if csrf.user_id:
        raise HTTPException(409)
    limited(db, request, "google_start")
    return {"url": google_oidc.begin(db, csrf, settings, body.destination)}


@router.post("/complete")
def complete(body: Callback, request: Request, response: Response, db: DB):
    if not request.app.state.settings.google_enabled:
        raise HTTPException(503)
    session = current_session(request, db)
    if not session:
        raise HTTPException(400)
    return google_oidc.complete(db, request, response, session, body)
