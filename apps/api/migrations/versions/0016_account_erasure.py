"""Action-bound deletion proof and private cleanup receipts."""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = depends_on = None


def upgrade():
    op.add_column("auth_sessions", sa.Column("deletion_digest", sa.String(64)))
    op.add_column("auth_sessions", sa.Column("deletion_until", sa.DateTime(timezone=True)))
    op.add_column("auth_sessions", sa.Column("deletion_version", sa.Integer()))
    op.add_column("google_flows", sa.Column("deletion_version", sa.Integer()))
    op.add_column("google_flows", sa.Column("started_at", sa.DateTime(timezone=True)))
    # The immutable issuer UUID stays available after its authentication record is erased.
    op.add_column("invitation_deliveries", sa.Column("retired_issuer_id", sa.Uuid()))
    op.alter_column("invitation_deliveries", "issuer_id", nullable=True)
    op.create_check_constraint(
        op.f("ck_invitation_deliveries_one_issuer"),
        "invitation_deliveries",
        "(issuer_id IS NULL) <> (retired_issuer_id IS NULL)",
    )
    op.create_table(
        "account_erasures",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("subject_digest", sa.String(64), index=True),
        sa.Column("files", sa.JSON(), nullable=False),
        sa.Column("review_required", sa.Boolean(), nullable=False),
    )


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM account_erasures)")):
        raise RuntimeError("Preserve account erasure receipts before downgrading")
    op.drop_table("account_erasures")
    op.drop_constraint(op.f("ck_invitation_deliveries_one_issuer"), "invitation_deliveries")
    op.alter_column("invitation_deliveries", "issuer_id", nullable=False)
    op.drop_column("invitation_deliveries", "retired_issuer_id")
    for table, name in (
        ("google_flows", "started_at"),
        ("google_flows", "deletion_version"),
        ("auth_sessions", "deletion_version"),
        ("auth_sessions", "deletion_until"),
        ("auth_sessions", "deletion_digest"),
    ):
        op.drop_column(table, name)
