import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_auth_workspaces import ORIGIN, invite_member, mutate, register, workspace
from test_auth_workspaces import auth_env as auth_fixture
from test_database import HASH, migrate

from resolveflow.core.config import Settings
from resolveflow.db.models import AccountStatus, User, WorkspaceInvitation, WorkspaceMembership
from resolveflow.main import create_asgi_app
from resolveflow.services.auth import digest

pytestmark = pytest.mark.integration
auth_env = auth_fixture


def issue(client, space, user, role="viewer"):
    settings = client.app.app.state.settings
    settings.invitation_delivery = "local"
    response = mutate(
        client, f"/workspaces/{space['id']}/invitations", {"email": user["email"], "role": role}
    )
    assert response.status_code == 202
    row = response.json()
    file = settings.invitation_delivery_root / uuid.UUID(space["id"]).hex / uuid.UUID(row["id"]).hex
    assert file.stat().st_mode & 0o777 == 0o600
    token = json.loads(file.read_text())["token"]
    assert token not in response.text
    return row, token


def test_invitation_requires_recipient_and_secret_and_rotates_sessions(auth_env):
    engine, app, owner = auth_env
    register(owner)
    space = workspace(owner)
    with TestClient(create_asgi_app(app.app.state.settings)) as target:
        victim_claim = register(target, "unverified-claimed@example.com")
        old_session = target.cookies.get("resolveflow_session")
        assert (
            mutate(
                owner, f"/workspaces/{space['id']}/members", {"email": victim_claim["email"]}
            ).status_code
            == 409
        )
        row, token = issue(owner, space, victim_claim)
        assert target.get(f"/api/v1/workspaces/{space['id']}").status_code == 404
        assert mutate(target, "/auth/invitations/accept", {"token": "x" * 43}).status_code == 400
        assert mutate(owner, "/auth/invitations/accept", {"token": token}).status_code == 400
        assert (
            target.post("/api/v1/auth/invitations/accept", json={"token": token}).status_code == 403
        )
        with Session(engine) as db:
            invitation = db.get(WorkspaceInvitation, uuid.UUID(row["id"]))
            assert invitation.token_hash == digest(token) and invitation.token_hash != token
            assert db.scalar(select(func.count()).select_from(WorkspaceMembership)) == 1
        accepted = mutate(target, "/auth/invitations/accept", {"token": token})
        assert accepted.status_code == 201 and accepted.json()["id"] == space["id"]
        assert target.get("/api/v1/auth/me").json()["email_verified"] is True
        assert target.cookies.get("resolveflow_session") != old_session
        assert owner.get("/api/v1/auth/me").status_code == 200
        assert (
            target.get(
                "/api/v1/auth/me", headers={"cookie": f"resolveflow_session={old_session}"}
            ).status_code
            == 401
        )
        assert mutate(target, "/auth/invitations/accept", {"token": token}).status_code == 400
        assert target.get(f"/api/v1/workspaces/{space['id']}").json()["role"] == "viewer"


@pytest.mark.parametrize(
    "change",
    [
        "expired",
        "revoked",
        "reissued",
        "issuer_removed",
        "issuer_demoted",
        "issuer_inactive",
        "target_email",
        "target_inactive",
    ],
)
def test_invitation_fails_closed_after_changes(auth_env, change):
    engine, app, owner = auth_env
    actor = register(owner)
    space = workspace(owner)
    with TestClient(create_asgi_app(app.app.state.settings)) as target:
        user = register(target)
        row, token = issue(owner, space, user, "admin")
        if change == "revoked":
            assert (
                mutate(
                    owner, f"/workspaces/{space['id']}/invitations/{row['id']}", method="DELETE"
                ).status_code
                == 204
            )
        elif change == "reissued":
            _, replacement = issue(owner, space, user)
            assert replacement != token
        else:
            with Session(engine) as db:
                invitation = db.get(WorkspaceInvitation, uuid.UUID(row["id"]))
                if change == "expired":
                    invitation.created_at = datetime.now(UTC) - timedelta(days=2)
                    invitation.expires_at = datetime.now(UTC) - timedelta(days=1)
                elif change.startswith("issuer_"):
                    member = db.scalar(
                        select(WorkspaceMembership).where(
                            WorkspaceMembership.workspace_id == uuid.UUID(space["id"])
                        )
                    )
                    if change == "issuer_removed":
                        db.delete(member)
                    elif change == "issuer_demoted":
                        member.role = "admin"  # Admin cannot grant the saved admin role.
                    else:
                        db.get(User, uuid.UUID(actor["id"])).account_status = AccountStatus.INACTIVE
                elif change == "target_email":
                    db.get(User, uuid.UUID(user["id"])).email = "changed@example.com"
                else:
                    db.get(User, uuid.UUID(user["id"])).account_status = AccountStatus.INACTIVE
                db.commit()
        response = mutate(target, "/auth/invitations/accept", {"token": token})
        assert response.status_code in {400, 401, 403, 404}
        with Session(engine) as db:
            assert (
                db.scalar(
                    select(WorkspaceMembership).where(
                        WorkspaceMembership.user_id == uuid.UUID(user["id"])
                    )
                )
                is None
            )
            assert db.get(User, uuid.UUID(user["id"])).email_verified_at is None


def test_invitation_race_and_tenant_scoping(auth_env):
    engine, app, owner = auth_env
    register(owner)
    space, second = workspace(owner), workspace(owner)
    with TestClient(create_asgi_app(app.app.state.settings)) as target:
        user = register(target)
        row, token = issue(owner, space, user)
        assert target.get(f"/api/v1/workspaces/{space['id']}/invitations").status_code == 404
        assert (
            mutate(
                owner, f"/workspaces/{second['id']}/invitations/{row['id']}", method="DELETE"
            ).status_code
            == 404
        )
        assert len(owner.get(f"/api/v1/workspaces/{space['id']}/invitations").json()) == 1
        csrf = target.get("/api/v1/auth/csrf").json()["csrf_token"]
        cookie = target.cookies.get("resolveflow_session")

        def attempt():
            with TestClient(create_asgi_app(app.app.state.settings)) as client:
                return client.post(
                    "/api/v1/auth/invitations/accept",
                    json={"token": token},
                    headers={
                        "origin": ORIGIN,
                        "x-csrf-token": csrf,
                        "cookie": f"resolveflow_session={cookie}",
                    },
                ).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        assert results.count(201) == 1
        assert all(status in {201, 400, 401, 403} for status in results)
        with Session(engine) as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(WorkspaceMembership)
                    .where(WorkspaceMembership.user_id == uuid.UUID(user["id"]))
                )
                == 1
            )


def test_delivery_disabled_and_production_rejected(auth_env):
    _, app, owner = auth_env
    register(owner)
    space = workspace(owner)
    with TestClient(create_asgi_app(app.app.state.settings)) as target:
        user = register(target)
        response = mutate(owner, f"/workspaces/{space['id']}/invitations", {"email": user["email"]})
        assert response.status_code == 503
        assert not app.app.state.settings.invitation_delivery_root.exists()
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            trusted_origins=["https://example.com"],
            invitation_delivery="local",
        )


def test_delivery_failure_does_not_activate_invitation(auth_env, monkeypatch):
    from resolveflow.documents.storage import LocalFileStorage

    engine, app, owner = auth_env
    register(owner)
    space = workspace(owner)
    app.app.state.settings.invitation_delivery = "local"
    with TestClient(create_asgi_app(app.app.state.settings)) as target:
        user = register(target)

        def fail(*args):
            raise OSError("untrusted content must not be logged")

        monkeypatch.setattr(LocalFileStorage, "save", fail)
        response = mutate(owner, f"/workspaces/{space['id']}/invitations", {"email": user["email"]})
        assert response.status_code == 503 and "untrusted" not in response.text
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(WorkspaceInvitation)) == 0


def test_invitation_permission_boundaries(auth_env):
    _, app, owner = auth_env
    register(owner)
    space = workspace(owner)
    base = f"/workspaces/{space['id']}"
    with (
        TestClient(create_asgi_app(app.app.state.settings)) as admin,
        TestClient(create_asgi_app(app.app.state.settings)) as target,
    ):
        manager, recipient = register(admin), register(target)
        assert (
            invite_member(
                owner, admin, base + "/members", {"email": manager["email"], "role": "admin"}
            ).status_code
            == 201
        )
        for role in ("owner", "admin"):
            assert (
                mutate(
                    admin, base + "/invitations", {"email": recipient["email"], "role": role}
                ).status_code
                == 403
            )
        row, _ = issue(owner, space, recipient, "owner")
        assert mutate(admin, base + "/invitations/" + row["id"], method="DELETE").status_code == 403
        assert mutate(target, base + "/invitations", {"email": manager["email"]}).status_code == 404
        assert (
            mutate(target, base + "/invitations/" + row["id"], method="DELETE").status_code == 404
        )


def test_identity_migration_preserves_legacy_users_memberships_and_sessions(database_factory):
    from sqlalchemy import text

    engine = database_factory()
    migrate(engine, target="0010")
    user, space = uuid.uuid4(), uuid.uuid4()
    old_hash = digest("synthetic-old-session")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash) "
                "VALUES (:id, 'legacy@example.com', :hash)"
            ),
            {"id": user, "hash": HASH},
        )
        conn.execute(
            text("INSERT INTO workspaces (id, name, slug) VALUES (:id, 'Legacy', 'legacy')"),
            {"id": space},
        )
        conn.execute(
            text(
                "INSERT INTO workspace_memberships (user_id, workspace_id, role) "
                "VALUES (:user, :space, 'owner')"
            ),
            {"user": user, "space": space},
        )
        conn.execute(
            text(
                "INSERT INTO auth_sessions (token_hash, user_id, csrf_token, expires_at) "
                "VALUES (:hash, :user, 'synthetic-csrf', now() + interval '1 hour')"
            ),
            {"hash": old_hash, "user": user},
        )
    migrate(engine)
    with Session(engine) as db:
        saved = db.get(User, user)
        assert saved.email == "legacy@example.com" and saved.password_hash == HASH
        assert saved.email_verified_at is None  # Never silently certify legacy accounts.
        assert (
            db.scalar(select(WorkspaceMembership.role).where(WorkspaceMembership.user_id == user))
            == "owner"
        )
        assert (
            db.scalar(
                text("SELECT user_id FROM auth_sessions WHERE token_hash=:hash"), {"hash": old_hash}
            )
            == user
        )
    migrate(engine, "downgrade", "0010")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM users")) == 1
        assert conn.scalar(text("SELECT count(*) FROM workspace_memberships")) == 1
        assert conn.scalar(text("SELECT count(*) FROM auth_sessions")) == 1
