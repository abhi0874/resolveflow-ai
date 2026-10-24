"""Actual PostgreSQL tests; only randomly named, freshly created databases are removed."""

import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from resolveflow.core.config import Settings
from resolveflow.db.base import Base
from resolveflow.db.models import (
    AccountStatus,
    MembershipRole,
    Ticket,
    TicketPriority,
    TicketStatus,
    User,
    Workspace,
    WorkspaceMembership,
)
from resolveflow.db.session import get_session
from resolveflow.main import create_app

pytestmark = pytest.mark.integration
API = Path(__file__).resolve().parents[1]
# Synthetic encoded fixture only. This step has no password hashing or login feature.
HASH = "$argon2id$v=19$m=65536,t=3,p=4$c3ludGhldGljLXNhbHQ$aW50ZWdyYXRpb24tdGVzdC1oYXNo"


def migrate(engine, direction="upgrade", target="head"):
    config = Config(str(API / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        getattr(command, direction)(config, target)


@pytest.fixture(scope="session")
def engine(database_factory):
    engine = database_factory()
    migrate(engine)
    return engine


@pytest.fixture
def session(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def records(session):
    user = User(email=" Owner@Example.test ", password_hash=HASH)
    workspace = Workspace(name="Support", slug="support")
    session.add_all([user, workspace])
    session.flush()
    return user, workspace


def test_connection_extension_migration_and_schema(engine):
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT 1")) == 1
        assert conn.scalar(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))
        assert conn.scalar(text("SELECT '[1,2,3]'::vector <-> '[1,2,3]'::vector")) == 0
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "0012"
        context = MigrationContext.configure(
            conn, opts={"compare_type": True, "compare_server_default": True}
        )
        assert compare_metadata(context, Base.metadata) == []
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        "alembic_version",
        "workflow_executions",
        "workflow_jobs",
        "auth_sessions",
        "auth_rate_limits",
        "users",
        "workspaces",
        "workspace_memberships",
        "workspace_invitations",
        "identity_emails",
        "identity_audit",
        "tickets",
        "ticket_notes",
        "ticket_activities",
        "documents",
        "document_chunks",
        "chunk_embeddings",
        "response_drafts",
        "draft_citations",
        "draft_reviews",
    }
    assert {index["name"] for index in inspector.get_indexes("tickets")} == {
        "ix_tickets_workspace_created",
        "ix_tickets_workspace_updated",
        "uq_tickets_workspace_id",
        "ix_tickets_workspace_assignee",
        "ix_tickets_workspace_status_created",
    }
    for table in ["users", "workspaces", "workspace_memberships", "tickets"]:
        assert inspector.get_pk_constraint(table)["constrained_columns"] == ["id"]
        assert inspector.get_check_constraints(table)
    assert {fk["referred_table"] for fk in inspector.get_foreign_keys("workspace_memberships")} == {
        "users",
        "workspaces",
    }
    assert inspector.get_foreign_keys("tickets")[0]["options"]["ondelete"] == "RESTRICT"


def test_models_ticket_persistence_and_tenant_references(session, records):
    user, workspace = records
    member = WorkspaceMembership(
        user_id=user.id, workspace_id=workspace.id, role=MembershipRole.OWNER
    )
    ticket = Ticket(
        workspace_id=workspace.id, title="Cannot sign in", description="Synthetic ticket"
    )
    other = Workspace(name="Other", slug="other")
    session.add_all([member, ticket, other])
    session.commit()
    session.expire_all()
    saved = session.get(Ticket, ticket.id)
    assert isinstance(saved.id, uuid.UUID)
    assert saved.status == TicketStatus.OPEN and saved.priority == TicketPriority.MEDIUM
    assert saved.description == "Synthetic ticket" and saved.category is None
    assert saved.created_at.tzinfo is not None and saved.updated_at.tzinfo is not None
    assert user.email == "owner@example.test" and user.account_status == AccountStatus.ACTIVE
    assert session.scalar(select(Ticket).where(Ticket.workspace_id == other.id)) is None
    assert session.scalar(select(Ticket).where(Ticket.workspace_id == workspace.id)) == saved


def test_membership_unique_and_cross_workspace_allowed(session, records):
    user, workspace = records
    session.add(WorkspaceMembership(user_id=user.id, workspace_id=workspace.id))
    session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(WorkspaceMembership(user_id=user.id, workspace_id=workspace.id))
        session.flush()
    other = Workspace(name="Another", slug="another")
    session.add(other)
    session.flush()
    session.add(WorkspaceMembership(user_id=user.id, workspace_id=other.id))
    session.flush()


@pytest.mark.parametrize("column", ["user_id", "workspace_id"])
def test_membership_foreign_keys(session, records, column):
    user, workspace = records
    values = {"user_id": user.id, "workspace_id": workspace.id, column: uuid.uuid4()}
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(WorkspaceMembership(**values))
        session.flush()


def test_ticket_workspace_foreign_key_and_required(session):
    for workspace_id in [uuid.uuid4(), None]:
        with pytest.raises(IntegrityError), session.begin_nested():
            session.add(Ticket(workspace_id=workspace_id, title="Invalid"))
            session.flush()


def test_user_email_and_workspace_slug_unique(session, records):
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(User(email="OWNER@EXAMPLE.TEST", password_hash=HASH))
        session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(Workspace(name="Duplicate", slug="support"))
        session.flush()


@pytest.mark.parametrize(
    ("table", "column", "value"),
    [
        ("users", "password_hash", "plaintext-password"),
        ("users", "account_status", "invalid"),
        ("users", "email", "NONCANONICAL@example.test"),
        ("workspaces", "slug", "Bad Slug"),
        ("workspaces", "name", " "),
        ("workspace_memberships", "role", "superuser"),
        ("tickets", "status", "invalid"),
        ("tickets", "priority", "bogus"),
        ("tickets", "title", " "),
        ("tickets", "category", " "),
    ],
)
def test_database_constraints_on_raw_sql(session, records, table, column, value):
    user, workspace = records
    session.add_all(
        [
            WorkspaceMembership(user_id=user.id, workspace_id=workspace.id),
            Ticket(workspace_id=workspace.id, title="Valid"),
        ]
    )
    session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        # Identifiers are fixed test parameters, never request input.
        session.execute(text(f'UPDATE "{table}" SET "{column}" = :value'), {"value": value})


def test_delete_restrict(session, records):
    user, workspace = records
    session.add_all(
        [
            WorkspaceMembership(user_id=user.id, workspace_id=workspace.id),
            Ticket(workspace_id=workspace.id, title="Preserve"),
        ]
    )
    session.flush()
    for obj in [user, workspace]:
        with pytest.raises(IntegrityError), session.begin_nested():
            session.delete(obj)
            session.flush()


def test_migration_rollback_and_reapply(database_factory):
    isolated = database_factory()
    migrate(isolated)
    migrate(isolated, "downgrade", "base")
    assert set(inspect(isolated).get_table_names()) == {"alembic_version"}
    with isolated.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM alembic_version")) == 0
        assert conn.scalar(text("SELECT count(*) FROM pg_extension WHERE extname='vector'")) == 1
    migrate(isolated)
    assert "tickets" in inspect(isolated).get_table_names()


def test_ready_real_database(engine):
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=engine.url.render_as_string(hide_password=False),
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/ready")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ready",
            "service": "resolveflow-api",
            "database": "ok",
        }


def test_failed_request_rolls_back_and_session_can_recover(engine):
    settings = Settings(
        _env_file=None, database_url=engine.url.render_as_string(hide_password=False)
    )
    app = create_app(settings)
    from typing import Annotated

    from fastapi import Depends

    @app.post("/test-rollback")
    def broken(session: Annotated[Session, Depends(get_session)]):
        session.add(Workspace(name="Rolled back", slug="request-rollback"))
        session.flush()
        raise RuntimeError("synthetic error")

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.post("/test-rollback").status_code == 500
        assert client.get("/api/v1/ready").status_code == 200
    with Session(engine) as session:
        assert session.scalar(select(Workspace).where(Workspace.slug == "request-rollback")) is None


def test_orm_updated_timestamp_between_transactions(engine):
    identifier = None
    try:
        with Session(engine) as session:
            workspace = Workspace(name="Before", slug="timestamp-test")
            session.add(workspace)
            session.commit()
            identifier, before = workspace.id, workspace.updated_at
            workspace.name = "After"
            session.commit()
            assert workspace.updated_at > before
            assert workspace.created_at == before
    finally:
        if identifier is not None:
            with engine.begin() as connection:
                connection.execute(text("DELETE FROM workspaces WHERE id=:id"), {"id": identifier})
