import enum
import uuid

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from resolveflow.db.base import Base, CreatedMixin, IdentityMixin, TimestampMixin
from resolveflow.db.models import enum_column


class DocumentStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETING = "deleting"


class Document(IdentityMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_documents_workspace_id"),
        UniqueConstraint("workspace_id", "checksum", name="uq_documents_workspace_checksum"),
        UniqueConstraint("storage_key"),
        CheckConstraint(
            "indexing_status IN ('not_indexed','indexing','indexed','failed')",
            name="indexing_status",
        ),
        CheckConstraint("file_size > 0 AND total_chunks >= 0", name="counts"),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="checksum"),
        CheckConstraint("length(original_filename) BETWEEN 1 AND 255", name="filename"),
        Index("ix_documents_workspace_created", "workspace_id", "created_at", "id"),
        Index("ix_documents_workspace_size", "workspace_id", "file_size", "id"),
        Index("ix_documents_workspace_status", "workspace_id", "processing_status"),
    )
    indexing_status: Mapped[str] = mapped_column(
        String(20), default="not_indexed", server_default="not_indexed"
    )
    indexing_error: Mapped[str | None] = mapped_column(String(40))
    indexing_token: Mapped[uuid.UUID | None] = mapped_column()
    indexed_model: Mapped[str | None] = mapped_column(String(200))
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT")
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(32))
    content_type: Mapped[str] = mapped_column(String(64))
    file_size: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64))
    processing_status: Mapped[DocumentStatus] = mapped_column(
        enum_column(DocumentStatus, "document_status"),
        default=DocumentStatus.PENDING,
        server_default="pending",
    )
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(40))
    processing_token: Mapped[uuid.UUID | None] = mapped_column()
    processing_config: Mapped[dict] = mapped_column(JSON)


class DocumentChunk(IdentityMixin, CreatedMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "document_id"],
            ["documents.workspace_id", "documents.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "workspace_id", "document_id", "id", name="uq_document_chunks_tenant_identity"
        ),
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_position"),
        CheckConstraint(
            "chunk_index >= 0 AND character_count = length(content) AND character_count > 0",
            name="content",
        ),
        CheckConstraint("page_number IS NULL OR page_number > 0", name="page"),
        Index(
            "ix_document_chunks_workspace_document", "workspace_id", "document_id", "chunk_index"
        ),
    )
    document_id: Mapped[uuid.UUID] = mapped_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column()
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    character_count: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer)
    source_metadata: Mapped[dict] = mapped_column(JSON)
