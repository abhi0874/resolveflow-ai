from fastapi import APIRouter

from resolveflow.api.v1.analytics import router as analytics_router
from resolveflow.api.v1.auth import router as auth_router
from resolveflow.api.v1.documents import router as document_router
from resolveflow.api.v1.drafts import router as draft_router
from resolveflow.api.v1.retrieval import router as retrieval_router
from resolveflow.api.v1.system import router as system_router
from resolveflow.api.v1.tickets import router as ticket_router
from resolveflow.api.v1.workflows import router as workflow_router
from resolveflow.api.v1.workspaces import router as workspace_router
from resolveflow.schemas.system import ErrorResponse

api_router = APIRouter(
    prefix="/api/v1",
    responses={
        422: {"model": ErrorResponse, "description": "Request validation failed"},
        500: {"model": ErrorResponse, "description": "Unexpected server error"},
    },
)
api_router.include_router(system_router)


api_router.include_router(auth_router)
api_router.include_router(workspace_router)

api_router.include_router(ticket_router)

api_router.include_router(document_router)

api_router.include_router(retrieval_router)
api_router.include_router(draft_router)
api_router.include_router(workflow_router)

api_router.include_router(analytics_router)
