"""One current vector per chunk; replacements become visible atomically."""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from resolveflow.db.base import Base, TimestampMixin


class ChunkEmbedding(TimestampMixin, Base):
    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "document_id", "chunk_id"],
            ["document_chunks.workspace_id", "document_chunks.document_id", "document_chunks.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("vector_norm(embedding) BETWEEN 0.999 AND 1.001", name="unit_vector"),
        CheckConstraint("content_hash ~ '^[a-f0-9]{64}$'", name="content_hash"),
        Index("ix_chunk_embeddings_workspace_model", "workspace_id", "model_space", "document_id"),
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column()
    document_id: Mapped[uuid.UUID] = mapped_column()
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    model_space: Mapped[str] = mapped_column(String(200))
    content_hash: Mapped[str] = mapped_column(String(64))
