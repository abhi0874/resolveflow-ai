import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError, TimeoutError
from starlette.exceptions import HTTPException

from resolveflow.ai.contracts import AIError
from resolveflow.db.session import DatabaseUnavailableError
from resolveflow.ml.contracts import ModelUnavailable
from resolveflow.retrieval.contracts import EmbeddingUnavailable
from resolveflow.schemas.system import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def error_response(status: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(
        status_code=status, content=body.model_dump(), headers={"Cache-Control": "no-store"}
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AIError)
    async def ai_error(_request: Request, exc: AIError) -> JSONResponse:
        status = 429 if exc.code in {"ai_daily_budget", "ai_quota_exhausted", "ai_busy"} else 503
        if exc.code in {"ticket_too_long", "sensitive_input", "synthetic_only"}:
            status = 422
        if exc.code in {"ticket_changed", "sources_changed", "generation_interrupted"}:
            status = 409
        response = error_response(status, exc.code, "Draft generation could not complete safely")
        if exc.retry_after is not None:
            response.headers["Retry-After"] = str(exc.retry_after)
        return response

    @app.exception_handler(EmbeddingUnavailable)
    async def embedding_unavailable(_request: Request, _exc: EmbeddingUnavailable) -> JSONResponse:
        return error_response(
            503, "embedding_unavailable", "Local embedding model is unavailable or busy"
        )

    @app.exception_handler(ModelUnavailable)
    async def classifier_unavailable(_request: Request, _exc: ModelUnavailable) -> JSONResponse:
        return error_response(503, "classifier_unavailable", "Ticket classifier is unavailable")

    @app.exception_handler(DatabaseUnavailableError)
    @app.exception_handler(OperationalError)
    @app.exception_handler(TimeoutError)
    async def database_unavailable_handler(_request: Request, _exc: Exception) -> JSONResponse:
        return error_response(503, "database_unavailable", "Database is unavailable")

    @app.exception_handler(IntegrityError)
    async def database_conflict_handler(_request: Request, _exc: Exception) -> JSONResponse:
        return error_response(409, "database_conflict", "Database constraint conflict")

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("Database operation failed: %s", type(exc).__name__)
        return error_response(500, "database_error", "Database operation failed")

    @app.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        # Do not expose arbitrary exception details or submitted values.
        try:
            message = HTTPStatus(exc.status_code).phrase
        except ValueError:
            message = "Request failed"
        code = (
            exc.detail
            if exc.detail in ("email_verification_required", "identity_link_invalid")
            else "http_error"
        )
        response = error_response(exc.status_code, code, message)
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(422, "validation_error", "Request validation failed")

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        # Log the exception type without credentials, request content, or exception values.
        logger.error("Unhandled API error: %s", type(exc).__name__)
        return error_response(500, "internal_error", "An unexpected error occurred")
