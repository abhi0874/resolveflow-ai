import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from resolveflow.db.models import AccountStatus, MembershipRole, User, WorkspaceMembership
from resolveflow.db.ticket_queries import history, list_tickets
from resolveflow.ml.contracts import Prediction, TicketClassifier, TicketText
from resolveflow.schemas.auth import MemberResponse
from resolveflow.schemas.tickets import (
    ActivityResponse,
    NoteInput,
    NoteResponse,
    Page,
    PageQuery,
    TicketCreate,
    TicketPatch,
    TicketQuery,
    TicketResponse,
)
from resolveflow.services.auth import CSRF, DB, CurrentUser
from resolveflow.services.authorization import Permission, access
from resolveflow.services.tickets import (
    add_note,
    create_ticket,
    require_editor,
    scoped_ticket,
    update_ticket,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/tickets", tags=["tickets"])


@router.get("", response_model=Page[TicketResponse])
def index(
    workspace_id: uuid.UUID, query: Annotated[TicketQuery, Query()], db: DB, user: CurrentUser
):
    access(db, user, workspace_id)
    return list_tickets(db, workspace_id, query)


@router.post("", response_model=TicketResponse, status_code=201)
def create(workspace_id: uuid.UUID, body: TicketCreate, db: DB, user: CurrentUser, csrf: CSRF):
    _, actor = access(db, user, workspace_id, Permission.TICKET_WRITE, lock=True)
    return create_ticket(db, actor, body)


@router.get("/assignees", response_model=list[MemberResponse])
def assignees(workspace_id: uuid.UUID, db: DB, user: CurrentUser):
    access(db, user, workspace_id)
    return [
        MemberResponse(user_id=member.user_id, email=email, role=member.role)
        for member, email in db.execute(
            select(WorkspaceMembership, User.email)
            .join(User)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.role != MembershipRole.VIEWER,
                User.account_status == AccountStatus.ACTIVE,
            )
            .order_by(User.email)
        )
    ]


@router.get("/{ticket_id}", response_model=TicketResponse)
def detail(workspace_id: uuid.UUID, ticket_id: uuid.UUID, db: DB, user: CurrentUser):
    access(db, user, workspace_id)
    return scoped_ticket(db, workspace_id, ticket_id)


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update(
    workspace_id: uuid.UUID,
    ticket_id: uuid.UUID,
    body: TicketPatch,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
):
    _, actor = access(db, user, workspace_id, Permission.TICKET_WRITE, lock=True)
    return update_ticket(db, actor, scoped_ticket(db, workspace_id, ticket_id), body)


@router.get("/{ticket_id}/notes", response_model=Page[NoteResponse])
def notes(
    workspace_id: uuid.UUID,
    ticket_id: uuid.UUID,
    query: Annotated[PageQuery, Query()],
    db: DB,
    user: CurrentUser,
):
    access(db, user, workspace_id)
    return history(db, scoped_ticket(db, workspace_id, ticket_id), query, notes=True)


@router.post("/{ticket_id}/notes", response_model=NoteResponse, status_code=201)
def note(
    workspace_id: uuid.UUID,
    ticket_id: uuid.UUID,
    body: NoteInput,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
):
    _, actor = access(db, user, workspace_id, Permission.TICKET_WRITE, lock=True)
    saved = add_note(db, actor, scoped_ticket(db, workspace_id, ticket_id), body)
    return NoteResponse(
        id=saved.id,
        workspace_id=saved.workspace_id,
        ticket_id=saved.ticket_id,
        author_id=saved.author_id,
        author_email=user.email,
        body=saved.body,
        created_at=saved.created_at,
    )


@router.get("/{ticket_id}/activities", response_model=Page[ActivityResponse])
def activities(
    workspace_id: uuid.UUID,
    ticket_id: uuid.UUID,
    query: Annotated[PageQuery, Query()],
    db: DB,
    user: CurrentUser,
):
    access(db, user, workspace_id)
    return history(db, scoped_ticket(db, workspace_id, ticket_id), query, notes=False)


class ClassificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClassificationResponse(Prediction):
    ticket_id: uuid.UUID
    ticket_version: int


@router.post("/{ticket_id}/classify", response_model=ClassificationResponse)
def classify(
    workspace_id: uuid.UUID,
    ticket_id: uuid.UUID,
    body: ClassificationRequest,
    request: Request,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
):
    _, actor = access(db, user, workspace_id, Permission.TICKET_WRITE, lock=True)
    ticket = scoped_ticket(db, workspace_id, ticket_id)
    require_editor(ticket, actor)
    try:
        text = TicketText(title=ticket.title, description=ticket.description)
    except ValueError:
        raise HTTPException(422) from None
    classifier: TicketClassifier = request.app.state.classifier
    result = classifier.predict(text)
    # Recommendation only. The existing version-checked PATCH owns all category changes.
    return ClassificationResponse(
        **result.model_dump(), ticket_id=ticket.id, ticket_version=ticket.version
    )
