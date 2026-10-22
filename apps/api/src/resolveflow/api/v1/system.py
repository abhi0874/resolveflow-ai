from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from resolveflow import __version__
from resolveflow.db.session import DatabaseUnavailableError, get_session
from resolveflow.schemas.system import (
    ErrorResponse,
    HealthResponse,
    InfoResponse,
    ReadinessResponse,
)

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Process liveness only; no database or AI readiness is implied."""
    return HealthResponse()


@router.get("/info", response_model=InfoResponse)
async def info() -> InfoResponse:
    return InfoResponse(
        name="ResolveFlow AI",
        version=__version__,
        description="AI-powered customer support platform",
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ErrorResponse, "description": "Database unavailable"}},
)
def ready(session: Annotated[Session, Depends(get_session)]) -> ReadinessResponse:
    """Connectivity only; migration and extension state are checked separately."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError from exc
    return ReadinessResponse()
