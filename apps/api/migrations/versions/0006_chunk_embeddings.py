"""Add local semantic indexing, preserving existing chunks and documents."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "documents",
        sa.Column("indexing_status", sa.String(20), nullable=False, server_default="not_indexed"),
    )
    op.add_column("documents", sa.Column("indexing_error", sa.String(40)))
    op.add_column("documents", sa.Column("indexing_token", sa.Uuid()))
    op.add_column("documents", sa.Column("indexed_model", sa.String(200)))
    op.create_check_constraint(
        "indexing_status",
        "documents",
        "indexing_status IN ('not_indexed','indexing','indexed','failed')",
    )
    op.create_unique_constraint(
        "uq_document_chunks_tenant_identity",
        "document_chunks",
        ["workspace_id", "document_id", "id"],
    )
    op.create_table(
        "chunk_embeddings",
        sa.Column("chunk_id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("model_space", sa.String(200), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "document_id", "chunk_id"],
            ["document_chunks.workspace_id", "document_chunks.document_id", "document_chunks.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("vector_norm(embedding) BETWEEN 0.999 AND 1.001", name="unit_vector"),
        sa.CheckConstraint("content_hash ~ '^[a-f0-9]{64}$'", name="content_hash"),
    )
    op.create_index(
        "ix_chunk_embeddings_workspace_model",
        "chunk_embeddings",
        ["workspace_id", "model_space", "document_id"],
    )


def downgrade():
    op.drop_table("chunk_embeddings")
    op.drop_constraint("uq_document_chunks_tenant_identity", "document_chunks", type_="unique")
    op.drop_constraint(op.f("ck_documents_indexing_status"), "documents", type_="check")
    for column in ["indexed_model", "indexing_token", "indexing_error", "indexing_status"]:
        op.drop_column("documents", column)
