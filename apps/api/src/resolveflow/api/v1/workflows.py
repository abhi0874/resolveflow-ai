import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import select

from resolveflow.db.ticket_queries import paginate
from resolveflow.jobs import service as jobs
from resolveflow.rag.service import authorize
from resolveflow.schemas.tickets import Page, PageQuery
from resolveflow.services.auth import CSRF, DB, CurrentUser
from resolveflow.workflows import service
from resolveflow.workflows.contracts import ExecutionResponse, ResumeInput, StartInput
from resolveflow.workflows.models import WorkflowExecution

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["workflows"])


def dependencies(request):
    app = request.app.state
    return app.settings, app.classifier, app.embeddings, app.ai_provider


@router.post("/tickets/{ticket_id}/workflows", response_model=ExecutionResponse)
def start(
    workspace_id: uuid.UUID,
    ticket_id: uuid.UUID,
    body: StartInput,
    request: Request,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
    response: Response,
):
    inline = request.app.state.settings.workflow_inline_tests
    response.status_code = 200 if inline else 202
    return service.start(
        db, user, workspace_id, ticket_id, body, *dependencies(request), defer=not inline
    )


@router.get("/tickets/{ticket_id}/workflows", response_model=Page[ExecutionResponse])
def listing(
    workspace_id: uuid.UUID,
    ticket_id: uuid.UUID,
    query: Annotated[PageQuery, Query()],
    request: Request,
    db: DB,
    user: CurrentUser,
):
    authorize(db, user, workspace_id, ticket_id)
    rows, metadata = paginate(
        db,
        select(WorkflowExecution)
        .where(
            WorkflowExecution.workspace_id == workspace_id, WorkflowExecution.ticket_id == ticket_id
        )
        .order_by(WorkflowExecution.created_at.desc(), WorkflowExecution.id.desc()),
        query,
    )
    return Page[ExecutionResponse](
        items=[
            service.representation(db, user, row[0], request.app.state.settings) for row in rows
        ],
        **metadata,
    )


@router.get("/workflows/{execution_id}", response_model=ExecutionResponse)
def detail(
    workspace_id: uuid.UUID, execution_id: uuid.UUID, request: Request, db: DB, user: CurrentUser
):
    row = service.scoped(db, user, workspace_id, execution_id)
    return service.representation(db, user, row, request.app.state.settings)


@router.post("/workflows/{execution_id}/resume", response_model=ExecutionResponse)
def resume(
    workspace_id: uuid.UUID,
    execution_id: uuid.UUID,
    body: ResumeInput,
    request: Request,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
    response: Response,
):
    response.status_code = 200 if request.app.state.settings.workflow_inline_tests else 202
    row = service.scoped(db, user, workspace_id, execution_id, write=True)
    if request.app.state.settings.workflow_inline_tests:
        return service.drive(db, user, row, *dependencies(request))
    jobs.resume(db, user, row, request.app.state.settings)
    return service.representation(db, user, row, request.app.state.settings)


@router.post("/workflows/{execution_id}/cancel", response_model=ExecutionResponse)
def cancel(
    workspace_id: uuid.UUID,
    execution_id: uuid.UUID,
    body: ResumeInput,
    request: Request,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
    response: Response,
):
    response.status_code = 200 if request.app.state.settings.workflow_inline_tests else 202
    row = service.scoped(db, user, workspace_id, execution_id, write=True)
    if request.app.state.settings.workflow_inline_tests:
        return service.cancel(db, user, row, request.app.state.settings)
    jobs.cancel(db, user, row, request.app.state.settings)
    return service.representation(db, user, row, request.app.state.settings)
