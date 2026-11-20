"""Durable local mailbox provenance. Existing mailbox files are never adopted."""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "invitation_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        *[
            sa.Column(name, sa.Uuid(), sa.ForeignKey(table, ondelete="RESTRICT"), nullable=False)
            for name, table in (
                ("workspace_id", "workspaces.id"),
                ("recipient_id", "users.id"),
                ("issuer_id", "users.id"),
            )
        ],
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("credential_version", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mailbox_hash", sa.String(64), nullable=False),
        sa.Column("attempts", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.CheckConstraint("status IN ('pending','delivered','cancelled','held')", name="status"),
    )
    op.create_index(
        "ix_invitation_deliveries_pending",
        "invitation_deliveries",
        ["workspace_id", "status", "recipient_id"],
    )


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM invitation_deliveries)")):
        raise RuntimeError("Preserve mailbox ownership records before downgrading")
    op.drop_table("invitation_deliveries")
