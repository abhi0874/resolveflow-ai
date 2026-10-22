import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from resolveflow.db.base import Base, IdentityMixin, TimestampMixin


class WorkflowJob(IdentityMixin, TimestampMixin, Base):
    __tablename__ = "workflow_jobs"
    __table_args__ = (
        UniqueConstraint("execution_id", name="uq_workflow_job_execution"),
        CheckConstraint(
            "status IN ('queued','running','waiting_for_approval',"
            "'completed','failed','cancelled')",
            name="status",
        ),
        CheckConstraint("attempts >= 0 AND publications >= 0", name="bounds"),
        Index("ix_workflow_jobs_dispatch", "status", "available_at"),
    )
    correlation_id: Mapped[uuid.UUID | None] = mapped_column()
    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_executions.id", ondelete="RESTRICT")
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(16), default="start")
    status: Mapped[str] = mapped_column(String(24), default="queued")
    attempts: Mapped[int] = mapped_column(default=0)
    publications: Mapped[int] = mapped_column(default=0)
    delivery_id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(48))
