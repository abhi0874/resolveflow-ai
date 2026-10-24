import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_auth_workspaces import auth_env as auth_fixture
from test_auth_workspaces import invite_member, mutate, register, workspace
from test_database import migrate

from resolveflow.db.models import AccountStatus, Ticket, TicketActivity, TicketNote, User
from resolveflow.main import create_asgi_app

auth_env = auth_fixture
pytestmark = pytest.mark.integration


def setup(client):
    owner = register(client)
    space = workspace(client)
    return owner, space, f"/workspaces/{space['id']}/tickets"


def create(client, base, **values):
    result = mutate(client, base, {"title": "Cannot sign in", **values})
    assert result.status_code == 201, result.text
    return result.json()


def patch(client, base, ticket, **values):
    return mutate(
        client,
        base + "/" + ticket["id"],
        {"expected_version": ticket["version"], **values},
        "PATCH",
    )


def test_ticket_lifecycle_notes_history_persistence(auth_env):
    engine, _, client = auth_env
    owner, space, base = setup(client)
    ticket = create(
        client,
        base,
        description="Private customer text",
        category="Access",
        assigned_user_id=owner["id"],
        priority="high",
    )
    assert ticket["status"] == "open"
    result = patch(
        client,
        base,
        ticket,
        title="Sign in fixed",
        status="resolved",
        priority="low",
        assigned_user_id=None,
    )
    assert result.status_code == 200
    updated = result.json()
    assert updated["version"] == 2 and updated["updated_at"] >= ticket["updated_at"]
    assert patch(client, base, ticket, title="Stale overwrite").status_code == 409
    detail = base + "/" + ticket["id"]
    note = mutate(client, detail + "/notes", {"body": "<script>untrusted</script>"})
    assert note.status_code == 201 and note.json()["author_email"] == owner["email"]
    notes = client.get("/api/v1" + detail + "/notes").json()
    assert notes["total"] == 1 and notes["items"][0]["body"] == "<script>untrusted</script>"
    events = client.get("/api/v1" + detail + "/activities").json()
    assert events["total"] == 7
    assert {e["action"] for e in events["items"]} == {
        "created",
        "updated",
        "status_changed",
        "priority_changed",
        "assignment_changed",
        "note_added",
    }
    assert "Private customer text" not in str(events) and "<script>" not in str(events)
    assert client.get("/api/v1" + detail).json()["version"] == 3
    assert mutate(client, detail + "/activities", {"action": "forged"}).status_code == 405
    assert mutate(client, detail, method="DELETE").status_code == 405
    with Session(engine) as db:
        assert db.get(Ticket, uuid.UUID(ticket["id"])).title == "Sign in fixed"
        assert len(db.scalars(select(TicketActivity)).all()) == 7
        assert db.scalar(select(TicketNote)).workspace_id == uuid.UUID(space["id"])


def test_ticket_search_filters_and_stable_pagination(auth_env):
    _, _, client = auth_env
    owner, _, base = setup(client)
    first = create(
        client,
        base,
        title="Literal 100%_match",
        description="needle",
        category="Billing",
        assigned_user_id=owner["id"],
        priority="urgent",
    )
    create(client, base, title="Other", description="needle", category="Access")
    create(client, base, title="Third")

    def listing(**query):
        result = client.get("/api/v1" + base, params=query)
        assert result.status_code == 200, result.text
        return result.json()

    assert listing(search="needle")["total"] == 2
    assert listing(search="%_")["total"] == 1
    assert (
        listing(priority="urgent", category="Billing", assignee=owner["id"])["items"][0]["id"]
        == first["id"]
    )
    assert listing(assignee="unassigned")["total"] == 2
    assert listing(status="closed")["items"] == []
    pages = [listing(page=i, page_size=1, direction="asc") for i in (1, 2, 3)]
    assert len({p["items"][0]["id"] for p in pages}) == 3
    assert all(p["pages"] == 3 and p["total"] == 3 for p in pages)
    assert listing(page=4, page_size=1)["items"] == []
    assert patch(client, base, first, status="closed").status_code == 200
    assert listing(sort="updated_at")["items"][0]["id"] == first["id"]
    for query in (
        {"page": 0},
        {"page_size": 101},
        {"sort": "title; DROP TABLE tickets"},
        {"assignee": "bad"},
        {"unknown": "x"},
        {"status": "fake"},
        {"search": "x" * 201},
    ):
        assert client.get("/api/v1" + base, params=query).status_code == 422


def test_tenant_and_unauthenticated_ticket_boundaries(auth_env):
    _, app, client = auth_env
    _, _, base = setup(client)
    ticket = create(client, base)
    with TestClient(create_asgi_app(app.app.state.settings)) as other:
        assert other.get("/api/v1" + base).status_code == 401
        register(other)
        other_space = workspace(other)
        for path in (
            base,
            base + "/" + ticket["id"],
            base + "/" + ticket["id"] + "/notes",
            base + "/" + ticket["id"] + "/activities",
        ):
            assert other.get("/api/v1" + path).status_code == 404
        wrong = f"/workspaces/{other_space['id']}/tickets/{ticket['id']}"
        assert other.get("/api/v1" + wrong).status_code == 404
        assert (
            mutate(other, wrong, {"expected_version": 1, "status": "closed"}, "PATCH").status_code
            == 404
        )
        assert mutate(other, wrong + "/notes", {"body": "blocked"}).status_code == 404
    for path in ("/workspaces/bad/tickets", base + "/bad"):
        assert client.get("/api/v1" + path).status_code == 422
    assert client.get("/api/v1" + base + "/" + str(uuid.uuid4())).status_code == 404
    assert client.post("/api/v1" + base, json={"title": "No CSRF"}).status_code == 403


def test_viewer_agent_admin_policy_and_assignment(auth_env):
    _, app, client = auth_env
    owner, space, base = setup(client)
    ticket = create(client, base)
    members = f"/workspaces/{space['id']}/members"
    with TestClient(create_asgi_app(app.app.state.settings)) as teammate:
        agent = register(teammate)
        assert patch(client, base, ticket, assigned_user_id=agent["id"]).status_code == 422
        assert (
            invite_member(
                client, teammate, members, {"email": agent["email"], "role": "viewer"}
            ).status_code
            == 201
        )
        assert patch(client, base, ticket, assigned_user_id=agent["id"]).status_code == 422
        assert teammate.get("/api/v1" + base).status_code == 200
        assert mutate(teammate, base, {"title": "No"}).status_code == 403
        assert patch(teammate, base, ticket, status="closed").status_code == 403
        assert (
            mutate(teammate, base + "/" + ticket["id"] + "/notes", {"body": "No"}).status_code
            == 403
        )
        assert (
            mutate(
                client, members + "/" + agent["id"], {"role": "support_agent"}, "PATCH"
            ).status_code
            == 200
        )
        assert patch(teammate, base, ticket, priority="high").status_code == 403
        assert patch(teammate, base, ticket, assigned_user_id=agent["id"]).status_code == 403
        assert mutate(teammate, base, {"title": "No", "priority": "high"}).status_code == 403
        own = create(teammate, base)
        assert patch(teammate, base, own, status="in_progress").status_code == 200
        assigned = patch(client, base, ticket, assigned_user_id=owner["id"]).json()
        assert patch(teammate, base, assigned, title="No").status_code == 403
        assert (
            mutate(
                teammate, base + "/" + ticket["id"] + "/notes", {"body": "Team context"}
            ).status_code
            == 201
        )
        assigned = client.get("/api/v1" + base + "/" + ticket["id"]).json()
        assigned = patch(client, base, assigned, assigned_user_id=agent["id"]).json()
        assert patch(teammate, base, assigned, status="waiting_for_approval").status_code == 200
        # Demotion clears assignment with an audit event and invalidates stale edits.
        assert (
            mutate(client, members + "/" + agent["id"], {"role": "viewer"}, "PATCH").status_code
            == 200
        )
        saved = client.get("/api/v1" + base + "/" + ticket["id"]).json()
        assert saved["assigned_user_id"] is None
        assert (
            mutate(client, members + "/" + agent["id"], {"role": "admin"}, "PATCH").status_code
            == 200
        )
        saved = patch(teammate, base, saved, assigned_user_id=agent["id"], priority="urgent").json()
        assert saved["priority"] == "urgent"
        assert mutate(client, members + "/" + agent["id"], method="DELETE").status_code == 204
        assert client.get("/api/v1" + base + "/" + ticket["id"]).json()["assigned_user_id"] is None
        assert teammate.get("/api/v1" + base).status_code == 404


def test_ticket_validation_and_atomic_failure(auth_env):
    engine, _, client = auth_env
    _, _, base = setup(client)
    for body in (
        {"title": " "},
        {"title": "bad\x00value"},
        {"title": "x" * 201},
        {"title": "x", "category": ""},
        {"title": "x", "description": "x" * 8001},
        {"title": "x", "workspace_id": str(uuid.uuid4())},
        {"title": "x", "priority": "invalid"},
        {"title": "x", "assigned_user_id": str(uuid.uuid4())},
    ):
        assert mutate(client, base, body).status_code == 422
    ticket = create(client, base)
    for fields in ({"status": None}, {"title": None}, {"description": None}, {"version": 100}, {}):
        assert patch(client, base, ticket, **fields).status_code == 422
    for body in (" ", "x" * 4001):
        assert (
            mutate(client, base + "/" + ticket["id"] + "/notes", {"body": body}).status_code == 422
        )
    assert (
        patch(
            client, base, ticket, title="Would change", assigned_user_id=str(uuid.uuid4())
        ).status_code
        == 422
    )
    with Session(engine) as db:
        assert db.get(Ticket, uuid.UUID(ticket["id"])).title == ticket["title"]
        assert len(db.scalars(select(TicketActivity)).all()) == 1


def test_ticket_concurrent_edit_conflict(auth_env):
    _, app, client = auth_env
    _, _, base = setup(client)
    ticket = create(client, base)
    cookie = client.cookies.get("resolveflow_session")

    def edit(title):
        with TestClient(create_asgi_app(app.app.state.settings)) as other:
            other.cookies.set("resolveflow_session", cookie)
            return patch(other, base, ticket, title=title).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(edit, ["One", "Two"])) == [200, 409]


def test_ticket_database_tenant_constraints(auth_env):
    engine, _, client = auth_env
    owner, _, base = setup(client)
    ticket = create(client, base)
    other = workspace(client)
    with Session(engine) as db:
        for model, extra in (
            (TicketNote, {"author_id": owner["id"], "body": "wrong"}),
            (TicketActivity, {"actor_id": owner["id"], "action": "created", "details": {}}),
        ):
            with pytest.raises(IntegrityError), db.begin_nested():
                db.add(model(workspace_id=other["id"], ticket_id=ticket["id"], **extra))
                db.flush()
        with pytest.raises(IntegrityError), db.begin_nested():
            db.get(Ticket, uuid.UUID(ticket["id"])).assigned_user_id = uuid.uuid4()
            db.flush()


def test_ticket_migration_preserves_existing_records(database_factory):
    engine = database_factory()
    migrate(engine, target="0003")
    wid, tid = uuid.uuid4(), uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO workspaces(id,name,slug) VALUES (:id,'Existing','existing')"),
            {"id": wid},
        )
        conn.execute(
            text("INSERT INTO tickets(id,workspace_id,title) VALUES (:id,:wid,'Existing ticket')"),
            {"id": tid, "wid": wid},
        )
    migrate(engine)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT version FROM tickets WHERE id=:id"), {"id": tid}) == 1
        assert (
            conn.scalar(text("SELECT title FROM tickets WHERE id=:id"), {"id": tid})
            == "Existing ticket"
        )
    migrate(engine, "downgrade", "0003")
    migrate(engine)
    with engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT title FROM tickets WHERE id=:id"), {"id": tid})
            == "Existing ticket"
        )


def test_inactive_assignee_history_pages_and_noop(auth_env):
    engine, _, client = auth_env
    owner, _, base = setup(client)
    ticket = create(client, base)
    detail = base + "/" + ticket["id"]
    assert patch(client, base, ticket, title=ticket["title"]).json()["version"] == 1
    for i in range(3):
        assert mutate(client, detail + "/notes", {"body": f"Context {i}"}).status_code == 201
    for suffix, total in (("/notes", 3), ("/activities", 4)):
        pages = [
            client.get("/api/v1" + detail + suffix, params={"page": i, "page_size": 1}).json()
            for i in range(1, total + 1)
        ]
        assert all(p["total"] == total for p in pages)
        assert len({p["items"][0]["id"] for p in pages}) == total
    # A second active owner can inspect the now-inactive account without authenticating as it.
    from test_database import HASH

    from resolveflow.db.models import MembershipRole, WorkspaceMembership

    with Session(engine) as db:
        inactive = User(
            email="inactive@example.com", password_hash=HASH, account_status=AccountStatus.INACTIVE
        )
        db.add(inactive)
        db.flush()
        db.add(
            WorkspaceMembership(
                user_id=inactive.id,
                workspace_id=ticket["workspace_id"],
                role=MembershipRole.SUPPORT_AGENT,
            )
        )
        db.commit()
        inactive_id = str(inactive.id)
    assert inactive_id not in str(client.get("/api/v1" + base + "/assignees").json())
    latest = client.get("/api/v1" + detail).json()
    assert patch(client, base, latest, assigned_user_id=inactive_id).status_code == 422
    assert owner["id"] in str(client.get("/api/v1" + base + "/assignees").json())


def test_ticket_audit_failure_rolls_back_changes(auth_env, monkeypatch):
    _, _, client = auth_env
    _, _, base = setup(client)
    ticket = create(client, base)

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr("resolveflow.services.tickets.record", fail)
    with pytest.raises(RuntimeError, match="synthetic audit"):
        patch(client, base, ticket, title="Must roll back")
    saved = client.get("/api/v1" + base + "/" + ticket["id"]).json()
    assert saved["title"] == ticket["title"] and saved["version"] == 1
