"""Enable pgvector; provision as an administrator if the migration role cannot install it."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")


def downgrade() -> None:
    # Keep the extension: later/non-application objects may depend on it.
    # Never DROP EXTENSION ... CASCADE during an application rollback.
    pass
