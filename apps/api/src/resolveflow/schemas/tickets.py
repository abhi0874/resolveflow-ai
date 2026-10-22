import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from resolveflow.db.models import TicketPriority, TicketStatus
from resolveflow.schemas.auth import InputModel


class TextInput(InputModel):
    @field_validator("*", mode="before")
    @classmethod
    def reject_nul(cls, value):
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("NUL characters are not supported")
        return value


class TicketCreate(TextInput):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=8000)
    category: str | None = Field(default=None, max_length=100)
    priority: TicketPriority = TicketPriority.MEDIUM
    assigned_user_id: uuid.UUID | None = None

    @field_validator("title", "category")
    @classmethod
    def nonblank(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Cannot be blank")
        return value


class TicketPatch(TicketCreate):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=8000)
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    expected_version: int = Field(ge=1)

    @model_validator(mode="after")
    def valid_patch(self):
        fields = self.model_fields_set - {"expected_version"}
        if not fields or any(
            getattr(self, key) is None for key in fields - {"category", "assigned_user_id"}
        ):
            raise ValueError("Supply at least one non-null change")
        return self


class PageQuery(TextInput):
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=25, ge=1, le=100)


class TicketQuery(PageQuery):
    search: str = Field(default="", max_length=200)
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    category: str | None = Field(default=None, min_length=1, max_length=100)
    assignee: uuid.UUID | Literal["unassigned"] | None = None
    sort: Literal["created_at", "updated_at"] = "created_at"
    direction: Literal["asc", "desc"] = "desc"


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    description: str
    category: str | None
    status: TicketStatus
    priority: TicketPriority
    assigned_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    version: int


class NoteInput(TextInput):
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Cannot be blank")
        return value.strip()


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID
    author_email: str
    body: str
    created_at: datetime


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    ticket_id: uuid.UUID
    actor_id: uuid.UUID
    actor_email: str
    action: str
    details: dict[str, str | list[str] | None]
    created_at: datetime


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
