"""response_drafts

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "response_drafts",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_version", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("generation_status", sa.String(length=20), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("fixture", sa.Boolean(), nullable=False),
        sa.Column("prompt_version", sa.String(length=60), nullable=False),
        sa.Column("generation_origin", sa.String(length=20), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("insufficient_evidence", sa.Boolean(), nullable=False),
        sa.Column("uncertainty_notes", sa.Text(), nullable=True),
        sa.Column("suggested_next_steps", sa.JSON(), nullable=False),
        sa.Column("evidence_manifest", sa.JSON(), nullable=False),
        sa.Column("citation_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "generation_status IN ('generating','completed','failed')",
            name=op.f("ck_response_drafts_generation_status"),
        ),
        sa.CheckConstraint(
            "review_status IN ('pending_review','approved','rejected','needs_revision')",
            name=op.f("ck_response_drafts_review_status"),
        ),
        sa.CheckConstraint(
            "version > 0 AND ticket_version > 0 AND citation_count >= 0",
            name=op.f("ck_response_drafts_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name=op.f("fk_response_drafts_requested_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "ticket_id"],
            ["tickets.workspace_id", "tickets.id"],
            name=op.f("fk_response_drafts_workspace_id_tickets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_response_drafts")),
        sa.UniqueConstraint("workspace_id", "id", name="uq_response_drafts_tenant_identity"),
        sa.UniqueConstraint(
            "workspace_id", "requested_by", "request_id", name="uq_response_drafts_request"
        ),
    )
    op.create_index("ix_response_drafts_created", "response_drafts", ["created_at"], unique=False)
    op.create_index(
        "ix_response_drafts_ticket_created",
        "response_drafts",
        ["workspace_id", "ticket_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "draft_citations",
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("supporting_quote", sa.Text(), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id", "document_id", "chunk_id"],
            ["document_chunks.workspace_id", "document_chunks.document_id", "document_chunks.id"],
            name=op.f("fk_draft_citations_workspace_id_document_chunks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "draft_id"],
            ["response_drafts.workspace_id", "response_drafts.id"],
            name=op.f("fk_draft_citations_workspace_id_response_drafts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("draft_id", "position", name=op.f("pk_draft_citations")),
    )
    op.create_table(
        "draft_reviews",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("draft_version", sa.Integer(), nullable=False),
        sa.Column("response_hash", sa.String(length=64), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision IN ('approved','rejected','needs_revision')",
            name=op.f("ck_draft_reviews_decision"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_draft_reviews_actor_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "draft_id"],
            ["response_drafts.workspace_id", "response_drafts.id"],
            name=op.f("fk_draft_reviews_workspace_id_response_drafts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_draft_reviews")),
        sa.UniqueConstraint("draft_id", name="uq_draft_reviews_decision"),
    )


def downgrade() -> None:
    op.drop_table("draft_reviews")
    op.drop_table("draft_citations")
    op.drop_index("ix_response_drafts_ticket_created", table_name="response_drafts")
    op.drop_index("ix_response_drafts_created", table_name="response_drafts")
    op.drop_table("response_drafts")
