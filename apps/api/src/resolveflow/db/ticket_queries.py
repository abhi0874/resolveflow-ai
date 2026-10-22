"""Bounded, tenant-scoped reads with stable ordering and parameterized search."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from resolveflow.db.models import Ticket, TicketActivity, TicketNote, User
from resolveflow.schemas.tickets import (
    ActivityResponse,
    NoteResponse,
    Page,
    PageQuery,
    TicketQuery,
    TicketResponse,
)


def paginate(db: Session, statement, query: PageQuery):
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    rows = db.execute(
        statement.offset((query.page - 1) * query.page_size).limit(query.page_size)
    ).all()
    return rows, dict(
        total=total,
        page=query.page,
        page_size=query.page_size,
        pages=(total + query.page_size - 1) // query.page_size,
    )


def list_tickets(db: Session, workspace_id, query: TicketQuery):
    statement = select(Ticket).where(Ticket.workspace_id == workspace_id)
    for field in ("status", "priority", "category"):
        value = getattr(query, field)
        if value is not None:
            statement = statement.where(getattr(Ticket, field) == value)
    if query.assignee is not None:
        statement = statement.where(
            Ticket.assigned_user_id == (None if query.assignee == "unassigned" else query.assignee)
        )
    if query.search:
        escaped = query.search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        statement = statement.where(
            or_(
                Ticket.title.ilike(pattern, escape="\\"),
                Ticket.description.ilike(pattern, escape="\\"),
            )
        )
    column = getattr(Ticket, query.sort)  # Literal-validated, never a SQL string.
    ordering = (
        (column.asc(), Ticket.id.asc())
        if query.direction == "asc"
        else (column.desc(), Ticket.id.desc())
    )
    rows, metadata = paginate(db, statement.order_by(*ordering), query)
    return Page[TicketResponse](
        items=[TicketResponse.model_validate(row[0]) for row in rows], **metadata
    )


def history(db: Session, ticket: Ticket, query: PageQuery, *, notes: bool):
    model = TicketNote if notes else TicketActivity
    author = model.author_id if notes else model.actor_id
    statement = (
        select(model, User.email)
        .join(User, User.id == author)
        .where(model.workspace_id == ticket.workspace_id, model.ticket_id == ticket.id)
        .order_by(model.created_at.desc(), model.id.desc())
    )
    rows, metadata = paginate(db, statement, query)
    schema = NoteResponse if notes else ActivityResponse
    email_key = "author_email" if notes else "actor_email"
    items = [
        schema.model_validate(
            {
                **{key: getattr(row, key) for key in schema.model_fields if key != email_key},
                email_key: email,
            }
        )
        for row, email in rows
    ]
    return Page(items=items, **metadata)
