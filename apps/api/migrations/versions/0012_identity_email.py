"""Hash-only identity email outbox and account recovery audit; preserve existing users."""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = depends_on = None


def identity_columns():
    return [
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def upgrade():
    op.add_column("users", sa.Column("verified_email", sa.String(320)))
    op.add_column("users", sa.Column("email_verification_source", sa.String(16)))
    op.add_column(
        "users", sa.Column("credential_version", sa.Integer(), nullable=False, server_default="1")
    )
    # Old timestamps are retained, but are not elevated to externally verified identities.
    op.create_table(
        "identity_emails",
        *identity_columns(),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("credential_version", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_enqueued_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(32)),
        sa.Column("delivery_source", sa.String(16)),
        sa.UniqueConstraint("token_hash"),
        sa.CheckConstraint("purpose IN ('verify', 'reset')", name="purpose"),
        sa.CheckConstraint(
            "status IN ('pending','sending','sent','failed','cancelled')", name="status"
        ),
        sa.CheckConstraint("attempts BETWEEN 0 AND 3", name="attempts"),
    )
    op.create_index("ix_identity_emails_due", "identity_emails", ["status", "available_at"])
    op.create_index("ix_identity_emails_user", "identity_emails", ["user_id", "purpose"])
    op.create_table(
        "identity_audit",
        *identity_columns(),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("event", sa.String(40), nullable=False),
    )


def downgrade():
    op.drop_table("identity_audit")
    op.drop_table("identity_emails")
    op.drop_column("users", "credential_version")
    op.drop_column("users", "email_verification_source")
    op.drop_column("users", "verified_email")
