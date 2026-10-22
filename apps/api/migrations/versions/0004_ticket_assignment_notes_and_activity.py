"""ticket assignment notes and activity

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_tickets_workspace_id", "tickets", ["workspace_id", "id"])
    op.create_table(
        "ticket_activities",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('created','updated','status_changed','priority_changed',"
            "'assignment_changed','note_added')",
            name=op.f("ck_ticket_activities_action"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_ticket_activities_actor_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "ticket_id"],
            ["tickets.workspace_id", "tickets.id"],
            name=op.f("fk_ticket_activities_workspace_id_tickets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ticket_activities")),
    )
    op.create_index(
        "ix_ticket_activities_history",
        "ticket_activities",
        ["workspace_id", "ticket_id", "created_at", "id"],
        unique=False,
    )
    op.create_table(
        "ticket_notes",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(body)) BETWEEN 1 AND 4000", name=op.f("ck_ticket_notes_body_length")
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_ticket_notes_author_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "ticket_id"],
            ["tickets.workspace_id", "tickets.id"],
            name=op.f("fk_ticket_notes_workspace_id_tickets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ticket_notes")),
    )
    op.create_index(
        "ix_ticket_notes_history",
        "ticket_notes",
        ["workspace_id", "ticket_id", "created_at", "id"],
        unique=False,
    )
    op.add_column("tickets", sa.Column("assigned_user_id", sa.Uuid(), nullable=True))
    op.add_column("tickets", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.create_check_constraint(op.f("ck_tickets_version_positive"), "tickets", "version > 0")
    op.create_index(
        "ix_tickets_workspace_assignee",
        "tickets",
        ["workspace_id", "assigned_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_tickets_workspace_updated",
        "tickets",
        ["workspace_id", "updated_at", "id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_tickets_workspace_assignee",
        "tickets",
        "workspace_memberships",
        ["workspace_id", "assigned_user_id"],
        ["workspace_id", "user_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_tickets_workspace_assignee", "tickets", type_="foreignkey")
    op.drop_index("ix_tickets_workspace_updated", table_name="tickets")
    op.drop_index("ix_tickets_workspace_assignee", table_name="tickets")
    op.drop_constraint(op.f("ck_tickets_version_positive"), "tickets", type_="check")
    op.drop_column("tickets", "version")
    op.drop_column("tickets", "assigned_user_id")
    op.drop_index("ix_ticket_notes_history", table_name="ticket_notes")
    op.drop_table("ticket_notes")
    op.drop_index("ix_ticket_activities_history", table_name="ticket_activities")
    op.drop_table("ticket_activities")
    op.drop_constraint("uq_tickets_workspace_id", "tickets", type_="unique")
