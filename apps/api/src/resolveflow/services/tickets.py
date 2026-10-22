"""Transactional ticket commands. Callers hold the workspace lock for every write."""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from resolveflow.db.models import (
    AccountStatus,
    MembershipRole,
    Ticket,
    TicketActivity,
    TicketNote,
    User,
    WorkspaceMembership,
)
from resolveflow.schemas.tickets import NoteInput, TicketCreate, TicketPatch
from resolveflow.services.authorization import PERMISSIONS, Permission


def scoped_ticket(db: Session, workspace_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket:
    ticket = db.scalar(
        select(Ticket).where(Ticket.workspace_id == workspace_id, Ticket.id == ticket_id)
    )
    if ticket is None:
        raise HTTPException(404)
    return ticket


def record(db: Session, ticket: Ticket, actor_id: uuid.UUID, action: str, details: dict):
    db.add(
        TicketActivity(
            workspace_id=ticket.workspace_id,
            ticket_id=ticket.id,
            actor_id=actor_id,
            action=action,
            details=details,
            created_at=datetime.now(UTC),
        )
    )


def validate_assignee(db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID | None):
    if user_id is None:
        return
    member = db.scalar(
        select(WorkspaceMembership)
        .join(User)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.role != MembershipRole.VIEWER,
            User.account_status == AccountStatus.ACTIVE,
        )
    )
    if member is None:
        raise HTTPException(422)


def require_editor(ticket: Ticket, actor: WorkspaceMembership):
    if actor.role == MembershipRole.SUPPORT_AGENT and ticket.assigned_user_id not in (
        None,
        actor.user_id,
    ):
        raise HTTPException(403)


def create_ticket(db: Session, actor: WorkspaceMembership, body: TicketCreate) -> Ticket:
    if Permission.TICKET_MANAGE not in PERMISSIONS[actor.role] and (
        body.assigned_user_id is not None or body.priority != "medium"
    ):
        raise HTTPException(403)
    validate_assignee(db, actor.workspace_id, body.assigned_user_id)
    ticket = Ticket(workspace_id=actor.workspace_id, **body.model_dump())
    db.add(ticket)
    db.flush()
    record(db, ticket, actor.user_id, "created", {})
    if ticket.assigned_user_id:
        record(
            db,
            ticket,
            actor.user_id,
            "assignment_changed",
            {"from": None, "to": str(ticket.assigned_user_id)},
        )
    db.commit()
    return ticket


def update_ticket(db: Session, actor: WorkspaceMembership, ticket: Ticket, body: TicketPatch):
    require_editor(ticket, actor)
    values = body.model_dump(exclude_unset=True, exclude={"expected_version"})
    if Permission.TICKET_MANAGE not in PERMISSIONS[actor.role] and (
        {"assigned_user_id", "priority"} & values.keys()
    ):
        raise HTTPException(403)
    if ticket.version != body.expected_version:
        raise HTTPException(409)
    if "assigned_user_id" in values:
        validate_assignee(db, actor.workspace_id, values["assigned_user_id"])
    changed = []
    actions = {
        "status": "status_changed",
        "priority": "priority_changed",
        "assigned_user_id": "assignment_changed",
    }
    for key, value in values.items():
        old = getattr(ticket, key)
        if old == value:
            continue
        setattr(ticket, key, value)
        if key in actions:
            record(
                db,
                ticket,
                actor.user_id,
                actions[key],
                {
                    "from": str(old) if old is not None else None,
                    "to": str(value) if value is not None else None,
                },
            )
        else:
            changed.append(key)
    if changed:
        # Do not duplicate customer content in audit metadata.
        record(db, ticket, actor.user_id, "updated", {"fields": sorted(changed)})
    if db.is_modified(ticket):
        ticket.version += 1
    db.commit()
    return ticket


def add_note(db: Session, actor: WorkspaceMembership, ticket: Ticket, body: NoteInput):
    note = TicketNote(
        workspace_id=ticket.workspace_id,
        ticket_id=ticket.id,
        author_id=actor.user_id,
        body=body.body,
    )
    db.add(note)
    db.flush()
    ticket.version += 1
    record(db, ticket, actor.user_id, "note_added", {"note_id": str(note.id)})
    db.commit()
    return note


def unassign_member(db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID, actor_id: uuid.UUID):
    # Membership changes use the same workspace lock as ticket writes.
    for ticket in db.scalars(
        select(Ticket).where(
            Ticket.workspace_id == workspace_id, Ticket.assigned_user_id == user_id
        )
    ).yield_per(100):
        ticket.assigned_user_id = None
        ticket.version += 1
        record(
            db,
            ticket,
            actor_id,
            "assignment_changed",
            {"from": str(user_id), "to": None, "reason": "membership_changed"},
        )
    db.flush()  # Satisfy the membership FK before deleting the member.
