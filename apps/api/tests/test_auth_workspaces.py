import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from test_database import migrate

from resolveflow.core.config import Settings
from resolveflow.db.models import AccountStatus, AuthSession, User, Workspace, WorkspaceMembership
from resolveflow.main import create_asgi_app
from resolveflow.services.auth import HASHER, digest

pytestmark = pytest.mark.integration
ORIGIN = "http://127.0.0.1:3000"
PASSWORD = "a unique test passphrase 42!"


@pytest.fixture
def auth_env(database_factory):
    engine = database_factory()
    migrate(engine)
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=engine.url.render_as_string(hide_password=False),
    )
    app = create_asgi_app(settings)
    with TestClient(app) as client:
        yield engine, app, client


def mutate(client, path, body=None, method="POST", origin=ORIGIN):
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return client.request(
        method,
        "/api/v1" + path,
        json=body or {},
        headers={"origin": origin, "x-csrf-token": response.json()["csrf_token"]},
    )


def register(client, email=None):
    response = mutate(
        client,
        "/auth/register",
        {
            "email": email or f"user-{uuid.uuid4().hex}@example.com",
            "password": PASSWORD,
            "password_confirmation": PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def workspace(client, slug=None):
    response = mutate(
        client, "/workspaces", {"name": "Support", "slug": slug or f"support-{uuid.uuid4().hex}"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def invite_member(client, recipient, path, body):
    """Exercise the real invitation/acceptance flow using a private test mailbox."""
    for current in (client, recipient):
        assert current.app.app.state.settings.environment == "test"
        current.app.app.state.settings.invitation_delivery = "local"
    response = mutate(client, path.removesuffix("/members") + "/invitations", body)
    assert response.status_code == 202, response.text
    invitation = response.json()
    assert "token" not in invitation
    root = client.app.app.state.settings.invitation_delivery_root
    token = json.loads(
        (root / uuid.UUID(path.split("/")[2]).hex / uuid.UUID(invitation["id"]).hex).read_text()
    )["token"]
    return mutate(recipient, "/auth/invitations/accept", {"token": token})


def test_registration_hash_cookie_rotation_me_logout(auth_env):
    engine, _, client = auth_env
    csrf = client.get("/api/v1/auth/csrf")
    preauth = client.cookies.get("resolveflow_session")
    result = register(client, "Owner@Example.com")
    token = client.cookies.get("resolveflow_session")
    assert token != preauth
    assert set(result) == {"id", "email", "created_at", "email_verified"}
    assert result["email"] == "owner@example.com" and result["email_verified"] is False
    with Session(engine) as db:
        user = db.get(User, uuid.UUID(result["id"]))
        assert user.password_hash.startswith("$argon2id$") and HASHER.verify(
            user.password_hash, PASSWORD
        )
        assert db.get(AuthSession, digest(preauth)) is None
        assert db.get(AuthSession, digest(token)).user_id == user.id
        assert db.get(AuthSession, token) is None
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json() == result
    assert "no-store" in me.headers["cache-control"]
    assert "HttpOnly" in csrf.headers["set-cookie"] and "SameSite=lax" in csrf.headers["set-cookie"]
    assert "Domain=" not in csrf.headers["set-cookie"]
    assert mutate(client, "/auth/logout").status_code == 204
    client.cookies.set("resolveflow_session", token)
    assert client.get("/api/v1/auth/me").status_code == 401
    with Session(engine) as db:
        assert db.get(AuthSession, digest(token)) is None


def test_duplicates_invalid_login_inactive_and_persistence(auth_env):
    engine, _, client = auth_env
    user = register(client, "owner@example.com")
    duplicate = mutate(
        client,
        "/auth/register",
        {"email": " OWNER@EXAMPLE.COM ", "password": PASSWORD, "password_confirmation": PASSWORD},
    )
    assert duplicate.status_code == 409
    assert "email" not in duplicate.text and "hash" not in duplicate.text
    mutate(client, "/auth/logout")
    for email, password in [
        ("owner@example.com", "incorrect password"),
        ("missing@example.com", PASSWORD),
    ]:
        result = mutate(client, "/auth/login", {"email": email, "password": password})
        assert result.status_code == 401 and result.json() == {
            "error": {"code": "http_error", "message": "Unauthorized"}
        }
    result = mutate(client, "/auth/login", {"email": "OWNER@example.com", "password": PASSWORD})
    assert result.status_code == 200
    # Same persisted cookie works against a fresh app/pool.
    config = Settings(_env_file=None, database_url=engine.url.render_as_string(hide_password=False))
    with TestClient(create_asgi_app(config)) as second:
        second.cookies.set("resolveflow_session", client.cookies.get("resolveflow_session"))
        assert second.get("/api/v1/auth/me").json()["id"] == user["id"]
    with Session(engine) as db:
        db.get(User, uuid.UUID(user["id"])).account_status = AccountStatus.SUSPENDED
        db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        mutate(
            client, "/auth/login", {"email": "owner@example.com", "password": PASSWORD}
        ).status_code
        == 401
    )


def test_expired_and_anonymous_sessions(auth_env):
    engine, _, client = auth_env
    for path in ["/auth/me", "/workspaces", f"/workspaces/{uuid.uuid4()}"]:
        assert client.get("/api/v1" + path).status_code == 401
    register(client)
    token = client.cookies.get("resolveflow_session")
    with Session(engine) as db:
        session = db.get(AuthSession, digest(token))
        session.created_at = datetime.now(UTC) - timedelta(hours=13)
        session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401
    assert mutate(client, "/workspaces", {"name": "Blocked", "slug": "blocked"}).status_code == 401


def test_csrf_origin_token_and_content_type(auth_env):
    _, _, client = auth_env
    register(client)
    body = {"name": "Blocked", "slug": "blocked"}
    for headers in [
        {},
        {"origin": ORIGIN},
        {"origin": "https://evil.example", "x-csrf-token": "x"},
        {"origin": "null"},
    ]:
        assert client.post("/api/v1/workspaces", json=body, headers=headers).status_code == 403
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    assert (
        client.post(
            "/api/v1/workspaces",
            json=body,
            headers={"origin": ORIGIN, "x-csrf-token": token, "sec-fetch-site": "cross-site"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/workspaces",
            content="x",
            headers={"origin": ORIGIN, "x-csrf-token": token, "content-type": "text/plain"},
        ).status_code
        == 415
    )
    assert mutate(client, "/workspaces", body).status_code == 201
    other = client.cookies.get("resolveflow_session")
    mutate(client, "/auth/logout")
    client.get("/api/v1/auth/csrf")
    assert client.cookies.get("resolveflow_session") != other
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "x@example.com", "password": PASSWORD},
            headers={"origin": ORIGIN, "x-csrf-token": token},
        ).status_code
        == 403
    )


def test_invalid_registration_and_oversized_body(auth_env):
    _, _, client = auth_env
    cases = [
        dict(email="bad"),
        dict(password="short", password_confirmation="short"),
        dict(password_confirmation="does not match this password"),
        dict(unexpected="value"),
    ]
    for change in cases:
        data = {
            "email": "owner@example.com",
            "password": PASSWORD,
            "password_confirmation": PASSWORD,
            **change,
        }
        response = mutate(client, "/auth/register", data)
        assert response.status_code == 422
        assert PASSWORD not in response.text
    assert client.post("/api/v1/auth/register", content="x" * 16385).status_code == 413


def test_shared_login_rate_limit(auth_env):
    engine, _, client = auth_env
    for _ in range(10):
        assert (
            mutate(
                client, "/auth/login", {"email": "missing@example.com", "password": PASSWORD}
            ).status_code
            == 401
        )
    settings = Settings(
        _env_file=None, database_url=engine.url.render_as_string(hide_password=False)
    )
    with TestClient(create_asgi_app(settings)) as another:
        response = mutate(
            another, "/auth/login", {"email": "missing@example.com", "password": PASSWORD}
        )
        assert response.status_code == 429 and response.headers["retry-after"] == "900"


def test_workspace_atomic_owner_slug_and_tenant_boundaries(auth_env):
    engine, app, client = auth_env
    owner = register(client)
    first = workspace(client, "support")
    assert first["role"] == "owner"
    assert client.get("/api/v1/workspaces").json() == [first]
    assert (
        mutate(client, "/workspaces", {"name": "Duplicate", "slug": "support"}).status_code == 409
    )
    with Session(engine) as db:
        assert len(db.scalars(select(Workspace)).all()) == 1
        membership = db.scalar(select(WorkspaceMembership))
        assert (
            str(membership.user_id) == owner["id"] and str(membership.workspace_id) == first["id"]
        )
    with TestClient(create_asgi_app(app.app.state.settings)) as outsider:
        register(outsider)
        assert outsider.get("/api/v1/workspaces").json() == []
        for suffix in ["", "/members"]:
            assert outsider.get(f"/api/v1/workspaces/{first['id']}{suffix}").status_code == 404
        assert (
            mutate(
                outsider,
                f"/workspaces/{first['id']}",
                {"name": "Hijack", "slug": "hijack"},
                "PATCH",
            ).status_code
            == 404
        )
        assert (
            mutate(
                outsider, f"/workspaces/{first['id']}/members/{owner['id']}", method="DELETE"
            ).status_code
            == 404
        )


def test_roles_membership_uniqueness_and_owner_invariants(auth_env):
    _, app, client = auth_env
    owner = register(client)
    space = workspace(client)
    base = f"/workspaces/{space['id']}"
    with TestClient(create_asgi_app(app.app.state.settings)) as teammate:
        user = register(teammate)
        assert (
            invite_member(
                client, teammate, base + "/members", {"email": user["email"], "role": "viewer"}
            ).status_code
            == 201
        )
        assert mutate(client, base + "/members", {"email": user["email"]}).status_code == 409
        for role in ["viewer", "support_agent"]:
            assert (
                mutate(client, base + f"/members/{user['id']}", {"role": role}, "PATCH").status_code
                == 200
            )
            assert teammate.get("/api/v1" + base).status_code == 200
            assert mutate(teammate, base, {"name": "No", "slug": "no"}, "PATCH").status_code == 403
            assert mutate(teammate, base + "/members", {"email": owner["email"]}).status_code == 403
        assert (
            mutate(client, base + f"/members/{user['id']}", {"role": "admin"}, "PATCH").status_code
            == 200
        )
        assert (
            mutate(teammate, base, {"name": "Updated", "slug": space["slug"]}, "PATCH").status_code
            == 200
        )
        assert (
            mutate(
                teammate, base + f"/members/{user['id']}", {"role": "owner"}, "PATCH"
            ).status_code
            == 403
        )
        assert (
            mutate(teammate, base + f"/members/{owner['id']}", method="DELETE").status_code == 403
        )
        assert (
            mutate(
                teammate, base + "/members", {"email": "missing@example.com", "role": "owner"}
            ).status_code
            == 403
        )
        assert mutate(client, base + f"/members/{owner['id']}", method="DELETE").status_code == 409
        assert (
            mutate(client, base + f"/members/{owner['id']}", {"role": "admin"}, "PATCH").status_code
            == 409
        )
        # Only an owner can grant ownership; with two owners a removal is allowed.
        assert (
            mutate(client, base + f"/members/{user['id']}", {"role": "owner"}, "PATCH").status_code
            == 200
        )
        assert mutate(client, base + f"/members/{owner['id']}", method="DELETE").status_code == 204
        assert client.get("/api/v1" + base).status_code == 404
        assert mutate(teammate, base + f"/members/{user['id']}", method="DELETE").status_code == 409


def test_concurrent_owner_removal_preserves_one_owner(auth_env):
    engine, app, first = auth_env
    owner = register(first)
    space = workspace(first)
    base = f"/workspaces/{space['id']}/members"
    with TestClient(create_asgi_app(app.app.state.settings)) as second:
        other = register(second)
        assert (
            invite_member(
                first, second, base, {"email": other["email"], "role": "owner"}
            ).status_code
            == 201
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            a = executor.submit(mutate, first, base + "/" + owner["id"], None, "DELETE")
            b = executor.submit(mutate, second, base + "/" + other["id"], None, "DELETE")
            assert sorted([a.result().status_code, b.result().status_code]) == [204, 409]
    with Session(engine) as db:
        assert db.scalar(text("SELECT count(*) FROM workspace_memberships WHERE role='owner'")) == 1


def test_production_cookie_and_configuration(auth_env):
    engine, _, _ = auth_env
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production")
    config = Settings(
        _env_file=None,
        environment="production",
        trusted_origins=["https://app.example.com"],
        database_url=engine.url.render_as_string(hide_password=False),
    )
    with TestClient(create_asgi_app(config), base_url="https://app.example.com") as client:
        response = client.get("/api/v1/auth/csrf")
        cookie = response.headers["set-cookie"]
        assert (
            "__Host-resolveflow_session=" in cookie
            and "Secure" in cookie
            and "HttpOnly" in cookie
            and "Path=/" in cookie
        )
        assert "Domain=" not in cookie


def test_admin_can_manage_lower_roles_but_not_other_tenant_members(auth_env):
    _, app, owner_client = auth_env
    register(owner_client)
    first = workspace(owner_client)
    second = workspace(owner_client)
    base = f"/workspaces/{first['id']}"
    with (
        TestClient(create_asgi_app(app.app.state.settings)) as admin_client,
        TestClient(create_asgi_app(app.app.state.settings)) as agent_client,
    ):
        admin = register(admin_client)
        agent = register(agent_client)
        assert (
            invite_member(
                owner_client,
                admin_client,
                base + "/members",
                {"email": admin["email"], "role": "admin"},
            ).status_code
            == 201
        )
        assert (
            invite_member(
                admin_client,
                agent_client,
                base + "/members",
                {"email": agent["email"], "role": "support_agent"},
            ).status_code
            == 201
        )
        assert (
            mutate(
                admin_client, base + f"/members/{agent['id']}", {"role": "viewer"}, "PATCH"
            ).status_code
            == 200
        )
        assert (
            mutate(
                admin_client, base + f"/members/{agent['id']}", {"role": "admin"}, "PATCH"
            ).status_code
            == 403
        )
        assert (
            mutate(
                admin_client, f"/workspaces/{second['id']}/members/{agent['id']}", method="DELETE"
            ).status_code
            == 404
        )
        assert (
            mutate(admin_client, base + f"/members/{agent['id']}", method="DELETE").status_code
            == 204
        )
        assert agent_client.get("/api/v1" + base).status_code == 404


def test_additive_migration_preserves_existing_records(database_factory):
    engine = database_factory()
    migrate(engine, target="0002")
    identifier = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO workspaces (id, name, slug) VALUES (:id, 'Existing', 'existing')"),
            {"id": identifier},
        )
    migrate(engine)
    with engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT name FROM workspaces WHERE id=:id"), {"id": identifier})
            == "Existing"
        )
    migrate(engine, "downgrade", "0002")
    with engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT name FROM workspaces WHERE id=:id"), {"id": identifier})
            == "Existing"
        )
    migrate(engine)


def test_prune_only_expired_auth_rows(auth_env):
    engine, _, client = auth_env
    from resolveflow.db.models import AuthRateLimit
    from resolveflow.services.auth import clear_expired

    user = register(client)
    now = datetime.now(UTC)
    with Session(engine) as db:
        db.add(
            AuthSession(
                token_hash="0" * 64,
                csrf_token="0" * 43,
                created_at=now - timedelta(hours=2),
                expires_at=now - timedelta(hours=1),
            )
        )
        db.add(AuthRateLimit(key="0" * 64, count=1, reset_at=now - timedelta(hours=1)))
        db.commit()
        clear_expired(db)
        assert db.get(AuthSession, "0" * 64) is None
        assert db.get(AuthRateLimit, "0" * 64) is None
        assert db.get(User, uuid.UUID(user["id"])) is not None
    assert client.get("/api/v1/auth/me").status_code == 200
