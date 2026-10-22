"""Persistent job/outbox and cooperative cancellation.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "workflow_executions",
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "workflow_executions",
        sa.Column(
            "cancel_requested_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", name="fk_workflow_cancel_actor", ondelete="RESTRICT"),
        ),
    )
    op.add_column(
        "workflow_executions", sa.Column("cancel_requested_at", sa.DateTime(timezone=True))
    )
    op.create_table(
        "workflow_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "execution_id",
            sa.Uuid(),
            sa.ForeignKey("workflow_executions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("publications", sa.Integer(), nullable=False),
        sa.Column("delivery_id", sa.Uuid(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(48)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("execution_id", name="uq_workflow_job_execution"),
        sa.CheckConstraint(
            "status IN ('queued','running','waiting_for_approval',"
            "'completed','failed','cancelled')",
            name="status",
        ),
        sa.CheckConstraint("attempts >= 0 AND publications >= 0", name="bounds"),
    )
    op.create_index("ix_workflow_jobs_dispatch", "workflow_jobs", ["status", "available_at"])


def downgrade():
    op.drop_table("workflow_jobs")
    op.drop_column("workflow_executions", "cancel_requested_at")
    op.drop_column("workflow_executions", "cancel_requested_by")
    op.drop_column("workflow_executions", "cancel_requested")
