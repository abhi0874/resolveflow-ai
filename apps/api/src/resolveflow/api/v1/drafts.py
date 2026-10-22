import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from resolveflow.db.ticket_queries import paginate
from resolveflow.rag import service
from resolveflow.rag.models import ResponseDraft
from resolveflow.rag.schemas import DraftConfig, DraftResponse, GenerateInput, ReviewInput
from resolveflow.schemas.tickets import Page, PageQuery
from resolveflow.services.auth import CSRF, DB, CurrentUser

router = APIRouter(
    prefix="/workspaces/{workspace_id}/tickets/{ticket_id}", tags=["response drafts"]
)


@router.get("/response-config", response_model=DraftConfig)
def config(
    workspace_id: uuid.UUID, ticket_id: uuid.UUID, request: Request, db: DB, user: CurrentUser
):
    service.authorize(db, user, workspace_id, ticket_id)
    provider, settings = request.app.state.ai_provider, request.app.state.settings
    info = provider.get_model_info()
    return DraftConfig(
        **info.model_dump(),
        available=provider.health_check()
        and (info.fixture or workspace_id in settings.ai_synthetic_workspaces),
        synthetic_confirmation_required=not info.fixture,
        max_ticket_chars=settings.ai_ticket_chars,
    )


@router.post("/generate-response", response_model=DraftResponse)
def generate(
    workspace_id: uuid.UUID,
    ticket_id: uuid.UUID,
    body: GenerateInput,
    request: Request,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
):
    return service.generate(
        db,
        user,
        workspace_id,
        ticket_id,
        body,
        request.app.state.ai_provider,
        request.app.state.embeddings,
        request.app.state.settings,
    )


@router.get("/drafts", response_model=Page[DraftResponse])
def drafts(
    workspace_id: uuid.UUID,
    ticket_id: uuid.UUID,
    query: Annotated[PageQuery, Query()],
    db: DB,
    user: CurrentUser,
):
    ticket = service.authorize(db, user, workspace_id, ticket_id)
    rows, metadata = paginate(
        db,
        select(ResponseDraft)
        .where(ResponseDraft.workspace_id == workspace_id, ResponseDraft.ticket_id == ticket_id)
        .order_by(ResponseDraft.created_at.desc(), ResponseDraft.id.desc()),
        query,
    )
    return Page[DraftResponse](
        items=[service.representation(db, row[0], ticket) for row in rows], **metadata
    )


@router.get("/drafts/{draft_id}", response_model=DraftResponse)
def detail(
    workspace_id: uuid.UUID, ticket_id: uuid.UUID, draft_id: uuid.UUID, db: DB, user: CurrentUser
):
    ticket = service.authorize(db, user, workspace_id, ticket_id)
    return service.representation(
        db, service.scoped_draft(db, workspace_id, ticket_id, draft_id), ticket
    )


@router.post("/drafts/{draft_id}/review", response_model=DraftResponse)
def review(
    workspace_id: uuid.UUID,
    ticket_id: uuid.UUID,
    draft_id: uuid.UUID,
    body: ReviewInput,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
):
    return service.review(db, user, workspace_id, ticket_id, draft_id, body)
