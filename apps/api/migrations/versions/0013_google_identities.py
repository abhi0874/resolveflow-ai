"""Google identities and expiring, browser-bound authorization transactions."""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = depends_on = None


def upgrade():
    op.alter_column("users", "password_hash", nullable=True)
    op.create_table(
        "provider_identities",
        sa.Column("provider", sa.String(16), primary_key=True),
        sa.Column("subject", sa.String(255), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.UniqueConstraint("user_id", "provider"),
    )
    op.create_table(
        "google_flows",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column(
            "session_hash",
            sa.String(64),
            sa.ForeignKey("auth_sessions.token_hash", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("nonce_hash", sa.String(64), nullable=False),
        sa.Column("verifier", sa.String(86), nullable=False),
        sa.Column("destination", sa.String(2048), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    # Fail atomically before removing sign-in methods for existing accounts.
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM provider_identities)")):
        raise RuntimeError("Migrate provider identities before downgrading")
    op.alter_column("users", "password_hash", nullable=False)
    op.drop_table("google_flows")
    op.drop_table("provider_identities")
