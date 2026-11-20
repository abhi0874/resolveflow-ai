"""Bind one installation to its independent erasure journal."""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "erasure_journal_binding",
        sa.Column("singleton", sa.Boolean(), primary_key=True),
        sa.Column("epoch", sa.Uuid(), nullable=False),
        sa.Column("head", sa.String(64), nullable=False),
        sa.CheckConstraint("singleton", name="one_binding"),
    )


def downgrade():
    op.drop_table("erasure_journal_binding")
