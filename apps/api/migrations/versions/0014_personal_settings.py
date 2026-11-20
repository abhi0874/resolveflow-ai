"""Personal profile fields and browser-bound verified email changes."""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = depends_on = None


def set_purposes(values):
    op.drop_constraint(op.f("ck_identity_emails_purpose"), "identity_emails", type_="check")
    op.create_check_constraint(
        op.f("ck_identity_emails_purpose"), "identity_emails", f"purpose IN ({values})"
    )


def upgrade():
    op.add_column("users", sa.Column("display_name", sa.String(80)))
    op.add_column("users", sa.Column("avatar_png", sa.LargeBinary()))
    op.add_column("provider_identities", sa.Column("original_email", sa.String(320)))
    op.add_column("identity_emails", sa.Column("session_hash", sa.String(64)))
    set_purposes("'verify', 'reset', 'email_approve', 'email_change', 'email_notice'")


def downgrade():
    bind = op.get_bind()
    for query in (
        "SELECT EXISTS (SELECT 1 FROM users "
        "WHERE display_name IS NOT NULL OR avatar_png IS NOT NULL)",
        "SELECT EXISTS (SELECT 1 FROM provider_identities WHERE original_email IS NOT NULL)",
        "SELECT EXISTS (SELECT 1 FROM identity_emails WHERE purpose LIKE 'email_%')",
    ):
        if bind.scalar(sa.text(query)):
            raise RuntimeError("Preserve personal settings and email history before downgrading")
    set_purposes("'verify', 'reset'")
    op.drop_column("identity_emails", "session_hash")
    op.drop_column("provider_identities", "original_email")
    op.drop_column("users", "avatar_png")
    op.drop_column("users", "display_name")
