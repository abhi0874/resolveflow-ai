"""Immutable generated text, current source references, and append-only review decisions."""

import uuid

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from resolveflow.db.base import Base, CreatedMixin, IdentityMixin


class ResponseDraft(IdentityMixin, CreatedMixin, Base):
    __tablename__ = "response_drafts"
    __table_args__ = (
        Index("ix_response_drafts_analytics_created", "workspace_id", "created_at"),
        ForeignKeyConstraint(
            ["workspace_id", "ticket_id"],
            ["tickets.workspace_id", "tickets.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("workspace_id", "id", name="uq_response_drafts_tenant_identity"),
        UniqueConstraint(
            "workspace_id", "requested_by", "request_id", name="uq_response_drafts_request"
        ),
        CheckConstraint(
            "generation_status IN ('generating','completed','failed')", name="generation_status"
        ),
        CheckConstraint(
            "review_status IN ('pending_review','approved','rejected','needs_revision')",
            name="review_status",
        ),
        CheckConstraint(
            "version > 0 AND ticket_version > 0 AND citation_count >= 0", name="versions"
        ),
        Index("ix_response_drafts_ticket_created", "workspace_id", "ticket_id", "created_at"),
        Index("ix_response_drafts_created", "created_at"),
    )
    workspace_id: Mapped[uuid.UUID]
    ticket_id: Mapped[uuid.UUID]
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    request_id: Mapped[uuid.UUID]
    ticket_version: Mapped[int]
    version: Mapped[int] = mapped_column(default=1)
    generation_status: Mapped[str] = mapped_column(String(20), default="generating")
    review_status: Mapped[str] = mapped_column(String(20), default="pending_review")
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(100))
    fixture: Mapped[bool]
    prompt_version: Mapped[str] = mapped_column(String(60))
    generation_origin: Mapped[str] = mapped_column(String(20), default="provider")
    response_text: Mapped[str | None] = mapped_column(Text)
    insufficient_evidence: Mapped[bool] = mapped_column(default=True)
    uncertainty_notes: Mapped[str | None] = mapped_column(Text)
    suggested_next_steps: Mapped[list] = mapped_column(JSON, default=list)
    evidence_manifest: Mapped[list] = mapped_column(JSON, default=list)
    citation_count: Mapped[int] = mapped_column(default=0)
    error_code: Mapped[str | None] = mapped_column(String(40))
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    duration_ms: Mapped[float | None]


class DraftCitation(Base):
    __tablename__ = "draft_citations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "draft_id"],
            ["response_drafts.workspace_id", "response_drafts.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "document_id", "chunk_id"],
            ["document_chunks.workspace_id", "document_chunks.document_id", "document_chunks.id"],
            ondelete="CASCADE",
        ),
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[uuid.UUID]
    document_id: Mapped[uuid.UUID]
    chunk_id: Mapped[uuid.UUID]
    content_hash: Mapped[str] = mapped_column(String(64))
    supporting_quote: Mapped[str] = mapped_column(Text)
    statement_text: Mapped[str | None] = mapped_column(Text)
    similarity_score: Mapped[float]


class DraftReview(IdentityMixin, CreatedMixin, Base):
    __tablename__ = "draft_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "draft_id"],
            ["response_drafts.workspace_id", "response_drafts.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("draft_id", name="uq_draft_reviews_decision"),
        CheckConstraint("decision IN ('approved','rejected','needs_revision')", name="decision"),
    )
    workspace_id: Mapped[uuid.UUID]
    draft_id: Mapped[uuid.UUID]
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    decision: Mapped[str] = mapped_column(String(20))
    draft_version: Mapped[int]
    response_hash: Mapped[str] = mapped_column(String(64))
