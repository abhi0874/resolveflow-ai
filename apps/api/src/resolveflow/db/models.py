import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, validates

from resolveflow.db.base import Base, CreatedMixin, IdentityMixin, TimestampMixin


class AccountStatus(enum.StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class MembershipRole(enum.StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    SUPPORT_AGENT = "support_agent"
    VIEWER = "viewer"


class TicketStatus(enum.StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


def enum_column(enum_type: type[enum.StrEnum], name: str) -> Enum:
    # CHECK constraints keep values portable and migrations straightforward.
    return Enum(
        enum_type,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )


class User(IdentityMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email"),
        CheckConstraint("email = lower(btrim(email)) AND position('@' in email) > 1", name="email"),
        # Accept encoded Argon2id or bcrypt hashes, never arbitrary/plaintext passwords.
        # This is a format guard, not a password hashing/authentication implementation.
        CheckConstraint(
            "password_hash ~ '^\\$argon2id\\$v=19\\$m=[0-9]+,t=[0-9]+,p=[0-9]+"
            "\\$[A-Za-z0-9+/]+\\$[A-Za-z0-9+/]+$' OR "
            "password_hash ~ '^\\$2[aby]\\$[0-9]{2}\\$[./A-Za-z0-9]{53}$'",
            name="password_hash_format",
        ),
    )

    email: Mapped[str] = mapped_column(String(320))
    password_hash: Mapped[str] = mapped_column(String(512))
    account_status: Mapped[AccountStatus] = mapped_column(
        enum_column(AccountStatus, "account_status"),
        default=AccountStatus.ACTIVE,
        server_default="active",
    )

    @validates("email")
    def normalize_email(self, _key: str, value: str) -> str:
        return value.strip().lower()


class Workspace(IdentityMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("slug"),
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
        CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="slug_format"),
    )

    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(80))


class WorkspaceMembership(IdentityMixin, CreatedMixin, Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_memberships_workspace_user"),
        Index("ix_workspace_memberships_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT")
    )
    role: Mapped[MembershipRole] = mapped_column(
        enum_column(MembershipRole, "membership_role"),
        default=MembershipRole.VIEWER,
        server_default="viewer",
    )


class Ticket(IdentityMixin, TimestampMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint("length(btrim(title)) > 0", name="title_not_blank"),
        CheckConstraint(
            "category IS NULL OR length(btrim(category)) > 0", name="category_not_blank"
        ),
        UniqueConstraint("workspace_id", "id", name="uq_tickets_workspace_id"),
        ForeignKeyConstraint(
            ["workspace_id", "assigned_user_id"],
            ["workspace_memberships.workspace_id", "workspace_memberships.user_id"],
            name="fk_tickets_workspace_assignee",
            ondelete="RESTRICT",
        ),
        CheckConstraint("version > 0", name="version_positive"),
        Index("ix_tickets_workspace_updated", "workspace_id", "updated_at", "id"),
        Index("ix_tickets_workspace_assignee", "workspace_id", "assigned_user_id"),
        Index("ix_tickets_workspace_created", "workspace_id", "created_at"),
        Index("ix_tickets_workspace_status_created", "workspace_id", "status", "created_at"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT")
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[TicketStatus] = mapped_column(
        enum_column(TicketStatus, "ticket_status"), default=TicketStatus.OPEN, server_default="open"
    )
    priority: Mapped[TicketPriority] = mapped_column(
        enum_column(TicketPriority, "ticket_priority"),
        default=TicketPriority.MEDIUM,
        server_default="medium",
    )
    category: Mapped[str | None] = mapped_column(String(100))
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column()
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class TicketNote(IdentityMixin, CreatedMixin, Base):
    __tablename__ = "ticket_notes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "ticket_id"],
            ["tickets.workspace_id", "tickets.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(btrim(body)) BETWEEN 1 AND 4000", name="body_length"),
        Index("ix_ticket_notes_history", "workspace_id", "ticket_id", "created_at", "id"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column()
    ticket_id: Mapped[uuid.UUID] = mapped_column()
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    body: Mapped[str] = mapped_column(Text)


class TicketActivity(IdentityMixin, CreatedMixin, Base):
    __tablename__ = "ticket_activities"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "ticket_id"],
            ["tickets.workspace_id", "tickets.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "action IN ('created','updated','status_changed','priority_changed',"
            "'assignment_changed','note_added')",
            name="action",
        ),
        Index("ix_ticket_activities_history", "workspace_id", "ticket_id", "created_at", "id"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column()
    ticket_id: Mapped[uuid.UUID] = mapped_column()
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(32))
    details: Mapped[dict] = mapped_column(JSON)


class AuthSession(CreatedMixin, Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="expiry"),
        Index("ix_auth_sessions_user_id", "user_id"),
        Index("ix_auth_sessions_expires_at", "expires_at"),
    )

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"
    __table_args__ = (Index("ix_auth_rate_limits_reset_at", "reset_at"),)

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
