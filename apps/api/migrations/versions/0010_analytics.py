"""Workspace/date aggregation indexes and safe HTTP-to-job correlation.
Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = depends_on = None


def upgrade():
    op.add_column("workflow_jobs", sa.Column("correlation_id", sa.Uuid(), nullable=True))
    for table in ("workflow_executions", "response_drafts"):
        op.create_index(f"ix_{table}_analytics_created", table, ["workspace_id", "created_at"])


def downgrade():
    for table in ("workflow_executions", "response_drafts"):
        op.drop_index(f"ix_{table}_analytics_created", table_name=table)
    op.drop_column("workflow_jobs", "correlation_id")
