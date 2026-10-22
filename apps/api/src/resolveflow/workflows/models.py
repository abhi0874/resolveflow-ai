import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from resolveflow.db.base import Base, IdentityMixin, TimestampMixin


class WorkflowExecution(IdentityMixin, TimestampMixin, Base):
    __tablename__ = "workflow_executions"
    __table_args__ = (
        Index("ix_workflow_executions_analytics_created", "workspace_id", "created_at"),
        ForeignKeyConstraint(
            ["workspace_id", "ticket_id"],
            ["tickets.workspace_id", "tickets.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("workspace_id", "requested_by", "request_id", name="uq_workflow_request"),
        CheckConstraint(
            "status IN ('running','paused','completed','rejected',"
            "'needs_revision','failed','cancelled')",
            name="status",
        ),
        CheckConstraint("attempts >= 0 AND ticket_version > 0", name="bounds"),
        Index("ix_workflow_ticket_created", "workspace_id", "ticket_id", "created_at"),
    )
    workspace_id: Mapped[uuid.UUID]
    ticket_id: Mapped[uuid.UUID]
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    request_id: Mapped[uuid.UUID]
    ticket_version: Mapped[int]
    synthetic_confirmed: Mapped[bool]
    workflow_version: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="running")
    current_stage: Mapped[str] = mapped_column(String(30), default="classification")
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    attempts: Mapped[int] = mapped_column(default=0)
    cancel_requested: Mapped[bool] = mapped_column(default=False, server_default=false())
    cancel_requested_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
