"""Durable workflow ownership; checkpointer setup is an explicit separate command.

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = depends_on = None


def upgrade():
    # Legacy drafts remain readable; every new draft preserves exact statement boundaries.
    op.add_column("draft_citations", sa.Column("statement_text", sa.Text(), nullable=True))
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column(
            "requested_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_version", sa.Integer(), nullable=False),
        sa.Column("synthetic_confirmed", sa.Boolean(), nullable=False),
        sa.Column("workflow_version", sa.String(60), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("current_stage", sa.String(30), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["workspace_id", "ticket_id"],
            ["tickets.workspace_id", "tickets.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "workspace_id", "requested_by", "request_id", name="uq_workflow_request"
        ),
        sa.CheckConstraint(
            "status IN ('running','paused','completed','rejected',"
            "'needs_revision','failed','cancelled')",
            name="status",
        ),
        sa.CheckConstraint("attempts >= 0 AND ticket_version > 0", name="bounds"),
    )
    op.create_index(
        "ix_workflow_ticket_created",
        "workflow_executions",
        ["workspace_id", "ticket_id", "created_at"],
    )
    op.execute("CREATE SCHEMA IF NOT EXISTS workflow_checkpoints")


def downgrade():
    # Retain checkpoint history; an operator must explicitly archive/drop it after backup.
    op.drop_table("workflow_executions")
    op.drop_column("draft_citations", "statement_text")
