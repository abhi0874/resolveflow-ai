"""private knowledge documents and chunks

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "processing_status",
            sa.Enum(
                "pending",
                "processing",
                "completed",
                "failed",
                "deleting",
                name="document_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("total_chunks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("processing_token", sa.Uuid(), nullable=True),
        sa.Column("processing_config", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name=op.f("ck_documents_checksum")),
        sa.CheckConstraint("file_size > 0 AND total_chunks >= 0", name=op.f("ck_documents_counts")),
        sa.CheckConstraint(
            "length(original_filename) BETWEEN 1 AND 255", name=op.f("ck_documents_filename")
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
            name=op.f("fk_documents_uploaded_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_documents_workspace_id_workspaces"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_documents_storage_key")),
        sa.UniqueConstraint("workspace_id", "checksum", name="uq_documents_workspace_checksum"),
        sa.UniqueConstraint("workspace_id", "id", name="uq_documents_workspace_id"),
    )
    op.create_index(
        "ix_documents_workspace_created",
        "documents",
        ["workspace_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_documents_workspace_size",
        "documents",
        ["workspace_id", "file_size", "id"],
        unique=False,
    )
    op.create_index(
        "ix_documents_workspace_status",
        "documents",
        ["workspace_id", "processing_status"],
        unique=False,
    )
    op.create_table(
        "document_chunks",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("source_metadata", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "chunk_index >= 0 AND character_count = length(content) AND character_count > 0",
            name=op.f("ck_document_chunks_content"),
        ),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0", name=op.f("ck_document_chunks_page")
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "document_id"],
            ["documents.workspace_id", "documents.id"],
            name=op.f("fk_document_chunks_workspace_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_position"),
    )
    op.create_index(
        "ix_document_chunks_workspace_document",
        "document_chunks",
        ["workspace_id", "document_id", "chunk_index"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_workspace_document", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_documents_workspace_status", table_name="documents")
    op.drop_index("ix_documents_workspace_size", table_name="documents")
    op.drop_index("ix_documents_workspace_created", table_name="documents")
    op.drop_table("documents")
