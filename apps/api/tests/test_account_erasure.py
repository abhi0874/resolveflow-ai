import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime, timedelta

import pytest
from erasure_fixture import provision
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from test_auth_workspaces import PASSWORD, invite_member, mutate, register, workspace
from test_auth_workspaces import auth_env as auth_fixture
from test_google_auth import COMPLETE, begin
from test_google_auth import google as google_fixture
from test_invitations import issue

from resolveflow.backups.service import quarantine_restore
from resolveflow.db.models import (
    AccountErasure,
    AuthSession,
    IdentityEmail,
    InvitationDelivery,
    ProviderIdentity,
    User,
    Workspace,
    WorkspaceMembership,
)
from resolveflow.main import create_asgi_app
from resolveflow.services import erasure

pytestmark = pytest.mark.integration


@pytest.fixture
def auth_env(base_auth, tmp_path):
    engine, app, _ = base_auth
    provision(engine, app.app.state.settings, tmp_path)
    return base_auth


base_auth = auth_fixture
google = google_fixture
PROOF = "/account/deletion/reauthenticate"
DELETE = "/account/deletion/confirm"


def prove(client):
    assert mutate(client, PROOF, {"current_password": PASSWORD}).status_code == 200


def confirm(client):
    challenge = mutate(client, "/account/deletion/challenge")
    value = challenge.json().get("challenge", "x" * 43)
    return mutate(client, DELETE, {"confirmation": "DELETE", "challenge": value})


def test_password_confirmation_and_revocation(auth_env):
    engine, app, client = auth_env
    account = register(client)
    uid = uuid.UUID(account["id"])
    space = workspace(client)
    with closing(TestClient(app)) as second:
        assert (
            mutate(
                second, "/auth/login", {"email": account["email"], "password": PASSWORD}
            ).status_code
            == 200
        )
        assert confirm(client).status_code == 403
        assert mutate(client, PROOF, {"current_password": "wrong"}).status_code == 403
        prove(client)
        assert confirm(second).status_code == 403
        assert client.post("/api/v1" + DELETE, json={"confirmation": "DELETE"}).status_code == 403
        assert mutate(client, DELETE, {"confirmation": "no"}).status_code == 422
        with Session(engine) as db:
            db.execute(
                update(AuthSession)
                .where(AuthSession.user_id == uid)
                .values(deletion_until=datetime.now(UTC) - timedelta(seconds=3))
            )
            db.commit()
        assert confirm(client).status_code == 403
        prove(client)
        assert (
            mutate(
                client, DELETE, {"confirmation": "DELETE", "user_id": str(uuid.uuid4())}
            ).status_code
            == 422
        )
        with Session(engine) as db:
            db.get(User, uid).avatar_png = b"synthetic avatar"
            db.commit()
        assert confirm(client).json() == {"cleanup": "complete"}
        assert confirm(client).status_code in {401, 403}
        assert second.get("/api/v1/auth/me").status_code == 401
        assert (
            mutate(
                second, "/auth/login", {"email": account["email"], "password": PASSWORD}
            ).status_code
            == 401
        )
        with Session(engine) as db:
            assert db.get(User, uid) is None and db.get(Workspace, uuid.UUID(space["id"])) is None
            assert (
                db.get(AccountErasure, uid)
                and db.scalar(select(AuthSession).where(AuthSession.user_id == uid)) is None
            )
            assert db.scalar(select(IdentityEmail).where(IdentityEmail.user_id == uid)) is None


def test_google_requires_recent_subject_and_rejects_predeletion_signin(google):
    engine, app, client, provider = google
    assert client.post(COMPLETE, json=begin(client, provider)).status_code == 200
    uid = uuid.UUID(client.get("/api/v1/auth/me").json()["id"])
    with closing(TestClient(app)) as other:
        earlier = begin(other, provider)
        for claims, expected in (
            ({}, 400),
            ({"auth_time": 1}, 400),
            ({"auth_time": True}, 400),
            ({"auth_time": int(time.time())}, 400),
            ({"auth_time": int(time.time()), "sub": "different"}, 400),
            ({"auth_time": int(time.time()) + 1000}, 400),
            ("fresh", 200),
        ):
            provider.claims = dict(claims) if claims != "fresh" else {}
            url = mutate(client, PROOF, {}).json()["url"]
            assert "max_age=" not in url and "claims=" in url
            provider.fresh_auth = claims == "fresh" or bool(provider.claims.get("sub"))
            if provider.claims.get("sub"):
                del provider.claims["auth_time"]
            callback = provider.authorize(url)
            response = client.post(COMPLETE, json=callback)
            assert response.status_code == expected
            assert client.post(COMPLETE, json=callback).status_code == 400
            if expected == 400:
                assert confirm(client).status_code == 403
        assert confirm(client).status_code == 200
        assert other.post(COMPLETE, json=earlier).status_code == 400
        with Session(engine) as db:
            assert db.scalar(select(ProviderIdentity)) is None and db.get(User, uid) is None
        provider.claims = {}
        assert other.post(COMPLETE, json=begin(other, provider)).status_code == 200
        assert other.get("/api/v1/auth/me").json()["id"] != str(uid)


def test_shared_owner_file_and_membership_safety(auth_env):
    engine, app, owner = auth_env
    account = register(owner)
    uid = uuid.UUID(account["id"])
    space = workspace(owner)
    wid = uuid.UUID(space["id"])
    with closing(TestClient(app)) as member, closing(TestClient(app)) as guest:
        recipient = register(member)
        outsider = register(guest)
        path = f"/workspaces/{wid}/members"
        assert (
            invite_member(
                owner, member, path, {"email": recipient["email"], "role": "viewer"}
            ).status_code
            == 201
        )
        grant, _ = issue(owner, space, outsider)
        settings = app.app.state.settings
        folder = settings.invitation_delivery_root / wid.hex
        foreign = folder / uuid.UUID(grant["id"]).hex
        contents = foreign.read_bytes()
        prove(owner)
        assert confirm(owner).status_code == 409
        assert owner.get("/api/v1/auth/me").status_code == 200
        assert (
            mutate(
                owner, path + "/" + recipient["id"], {"role": "owner"}, method="PATCH"
            ).status_code
            == 200
        )
        assert confirm(owner).status_code == 200
        assert member.get(f"/api/v1/workspaces/{wid}").status_code == 200
        assert foreign.read_bytes() == contents
        with Session(engine) as db:
            assert db.get(User, uid) is None
            record = db.get(InvitationDelivery, uuid.UUID(grant["id"]))
            assert record.issuer_id is None and record.retired_issuer_id == uid
            assert db.scalar(select(func.count()).select_from(WorkspaceMembership)) == 1


def test_interrupted_private_cleanup_is_retryable_and_preserves_unknown(auth_env, monkeypatch):
    engine, app, owner = auth_env
    register(owner)
    space = workspace(owner)
    with closing(TestClient(app)) as recipient:
        user = register(recipient)
        uid = uuid.UUID(user["id"])
        row, _ = issue(owner, space, user)
        settings = app.app.state.settings
        final = (
            settings.invitation_delivery_root
            / uuid.UUID(space["id"]).hex
            / uuid.UUID(row["id"]).hex
        )
        legacy = final.with_name(uuid.uuid4().hex)
        legacy.write_text(user["email"])
        legacy.chmod(0o600)
        prove(recipient)
        with monkeypatch.context() as patch:

            def fail(*args):
                raise OSError("synthetic interruption")

            patch.setattr(erasure, "remove_verified", fail)
            assert confirm(recipient).json() == {"cleanup": "under_review"}
        with Session(engine) as db:
            assert db.get(User, uid) is None and len(db.get(AccountErasure, uid).files) == 1
            known = final.read_bytes()
            final.write_bytes(b"synthetic unrelated file")
            assert not erasure.cleanup(db, settings, uid)
            assert final.read_bytes() == b"synthetic unrelated file"
            final.write_bytes(known)

            def crash_before_ack():
                raise RuntimeError("simulated interruption after unlink")

            with monkeypatch.context() as patch:
                patch.setattr(db, "commit", crash_before_ack)
                with pytest.raises(RuntimeError, match="simulated interruption"):
                    erasure.cleanup(db, settings, uid)
            db.rollback()
            assert not final.exists() and db.get(AccountErasure, uid).files
            assert erasure.cleanup(db, settings, uid) and erasure.cleanup(db, settings, uid)
        from resolveflow.services.invitation_inventory import inventory

        with Session(engine) as db:
            assert "hold_missing_ownership" in [
                status for _, status in inventory(db, settings.invitation_delivery_root)
            ]
        assert not final.exists() and legacy.read_text() == user["email"]


def test_concurrent_confirmation_commits_once(auth_env):
    engine, app, client = auth_env
    uid = uuid.UUID(register(client)["id"])
    prove(client)
    nonce = mutate(client, "/account/deletion/challenge").json()["challenge"]
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    cookie = client.cookies.get("resolveflow_session")

    def post(_):
        with closing(TestClient(app)) as tab:
            return tab.post(
                "/api/v1" + DELETE,
                json={"confirmation": "DELETE", "challenge": nonce},
                headers={
                    "cookie": "resolveflow_session=" + cookie,
                    "origin": "http://127.0.0.1:3000",
                    "x-csrf-token": csrf,
                },
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(post, range(2)))
    assert outcomes.count(200) == 1 and set(outcomes) <= {200, 401, 403}
    with Session(engine) as db:
        assert db.get(User, uid) is None and db.get(AccountErasure, uid)


def test_restored_snapshot_cannot_serve_stale_session(auth_env):
    engine, app, client = auth_env
    register(client)
    cookie = client.cookies.get("resolveflow_session")
    quarantine_restore(engine)
    assert client.get("/api/v1/auth/me").status_code == 503
    with TestClient(create_asgi_app(app.app.state.settings)) as restored:
        assert (
            restored.get(
                "/api/v1/auth/me", headers={"cookie": "resolveflow_session=" + cookie}
            ).status_code
            == 503
        )


def test_job_lock_blocks_then_stale_delivery_cannot_run(auth_env, tmp_path):
    from test_documents import upload

    from resolveflow.db.models import AccountStatus, Ticket
    from resolveflow.documents.storage import LocalFileStorage
    from resolveflow.jobs.models import WorkflowJob
    from resolveflow.jobs.worker import process
    from resolveflow.workflows.models import WorkflowExecution
    from resolveflow.workflows.storage import checkpoint_store, lock_key

    engine, app, owner = auth_env
    owner_id = uuid.UUID(register(owner)["id"])
    wid = uuid.UUID(workspace(owner)["id"])
    with closing(TestClient(app)) as actor:
        user = register(actor)
        uid = uuid.UUID(user["id"])
        assert (
            invite_member(
                owner,
                actor,
                f"/workspaces/{wid}/members",
                {"email": user["email"], "role": "admin"},
            ).status_code
            == 201
        )
        app.app.state.document_storage = LocalFileStorage(tmp_path / "docs")
        doc = upload(
            actor, f"/workspaces/{wid}/documents", "team.txt", b"Shared synthetic workspace file"
        )
        assert doc.status_code == 201
        download = f"/api/v1/workspaces/{wid}/documents/{doc.json()['id']}/download"
        with Session(engine) as db:
            ticket = Ticket(
                workspace_id=wid,
                title="Synthetic",
                description="Retained workspace ticket",
                assigned_user_id=uid,
            )
            db.add(ticket)
            db.flush()
            run = WorkflowExecution(
                workspace_id=wid,
                ticket_id=ticket.id,
                requested_by=uid,
                workflow_version="ticket-workflow-v1",
                request_id=uuid.uuid4(),
                ticket_version=1,
                synthetic_confirmed=True,
            )
            db.add(run)
            db.flush()
            job = WorkflowJob(
                execution_id=run.id,
                actor_id=uid,
                kind="start",
                status="queued",
                available_at=datetime.now(UTC),
            )
            db.add(job)
            db.commit()
            jid, rid, tid, delivery = job.id, run.id, ticket.id, job.delivery_id
        prove(actor)
        with engine.begin() as worker:
            worker.execute(select(func.pg_advisory_xact_lock(lock_key("job:" + str(jid)))))
            assert confirm(actor).status_code == 409
        with Session(engine) as db:
            db.get(WorkflowJob, jid).actor_id = owner_id
            db.commit()
        assert confirm(actor).status_code == 409
        with Session(engine) as db:
            job = db.get(WorkflowJob, jid)
            assert job.status == "queued" and job.delivery_id == delivery
            job.actor_id = uid
            db.commit()
        assert confirm(actor).json() == {"cleanup": "complete"}
        settings = app.app.state.settings
        with checkpoint_store(settings, setup=True):
            pass
        process(app.app.state.database, settings, jid, delivery)
        assert owner.get(download).content == b"Shared synthetic workspace file"
        with Session(engine) as db:
            assert db.get(User, uid) is None
            assert db.get(Ticket, tid).assigned_user_id is None
            assert db.get(WorkflowJob, jid).delivery_id != delivery
            assert db.get(WorkflowExecution, rid).status == "cancelled"
            archived = db.get(User, db.get(WorkflowJob, jid).actor_id)
            assert (
                archived.account_status == AccountStatus.INACTIVE and archived.password_hash is None
            )
            assert (
                db.scalar(
                    select(WorkspaceMembership).where(WorkspaceMembership.user_id == archived.id)
                )
                is None
            )


def test_challenge_supersession_and_cross_user(auth_env):
    _, app, alice = auth_env
    register(alice)
    prove(alice)
    old = mutate(alice, "/account/deletion/challenge").json()["challenge"]
    new = mutate(alice, "/account/deletion/challenge").json()["challenge"]
    assert old != new
    with closing(TestClient(app)) as bob:
        register(bob)
        prove(bob)
        assert mutate(bob, DELETE, {"confirmation": "DELETE", "challenge": new}).status_code == 403
    assert mutate(alice, DELETE, {"confirmation": "DELETE", "challenge": old}).status_code == 403
    assert mutate(alice, DELETE, {"confirmation": "DELETE", "challenge": new}).status_code == 200


def test_superseded_google_exchange_cannot_issue_proof(google, monkeypatch):
    from resolveflow.services import google_oidc

    _, _, client, provider = google
    assert client.post(COMPLETE, json=begin(client, provider)).is_success
    provider.fresh_auth = True
    initial = provider.authorize(mutate(client, PROOF, {}).json()["url"])
    original = google_oidc.exchange
    newer = []

    def supersede(*args):
        claims = original(*args)
        newer.append(mutate(client, PROOF, {}).json()["url"])
        return claims

    with monkeypatch.context() as patch:
        patch.setattr(google_oidc, "exchange", supersede)
        assert client.post(COMPLETE, json=initial).status_code == 400
    assert confirm(client).status_code == 403
    assert client.post(COMPLETE, json=provider.authorize(newer[0])).is_success
    assert confirm(client).is_success
