"""Rehearse an actual encrypted pre-deletion snapshot with offline provider fixtures."""

import os
import uuid
from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_account_erasure import auth_env, base_auth, confirm, google, prove
from test_auth_workspaces import register
from test_backups import repo
from test_google_auth import COMPLETE, begin

from resolveflow.backups.erasure_recovery import reconcile
from resolveflow.backups.safety import BackupError
from resolveflow.backups.service import capture, quarantine_restore, restore_into
from resolveflow.db.models import AccountErasure, AuthSession, GoogleFlow, ProviderIdentity, User
from resolveflow.db.session import DatabaseUnavailableError
from resolveflow.main import create_asgi_app
from resolveflow.services import erasure_journal as journal
from resolveflow.workflows.storage import checkpoint_store

pytestmark = pytest.mark.integration
__all__ = ["auth_env", "base_auth", "google", "repo"]


def test_encrypted_snapshot_before_google_deletion(
    google, repo, database_factory, tmp_path, monkeypatch
):
    engine, app, client, provider = google
    settings = app.app.state.settings
    assert client.post(COMPLETE, json=begin(client, provider)).is_success
    uid = uuid.UUID(client.get("/api/v1/auth/me").json()["id"])
    cookie = client.cookies.get("resolveflow_session")
    with closing(TestClient(app)) as other:
        retained = uuid.UUID(register(other)["id"])
    with Session(engine) as db:
        db.get(User, uid).avatar_png = b"synthetic-private-avatar"
        db.commit()
        old_seal = journal.current_seal(db, settings)
    app.app.state.database.dispose()
    snapshot = capture(repo, engine, settings, quiesced=True)
    from test_account_erasure import PROOF
    from test_auth_workspaces import mutate

    provider.fresh_auth = True
    callback = provider.authorize(mutate(client, PROOF, {}).json()["url"])
    assert client.post(COMPLETE, json=callback).is_success and confirm(client).is_success
    with Session(engine) as db:
        seal = journal.current_seal(db, settings)
    assert seal != old_seal
    target = database_factory()
    with pytest.raises(BackupError, match="authoritative_seal_required"):
        restore_into(repo, snapshot["snapshot"], target, tmp_path / "isolated-restore")
    restored = settings.model_copy(
        update={"database_url": SecretStr(target.url.render_as_string(hide_password=False))}
    )
    with Session(target) as db:
        assert db.get(User, uid).avatar_png == b"synthetic-private-avatar"
        assert db.scalar(select(ProviderIdentity).where(ProviderIdentity.user_id == uid))
    with TestClient(create_asgi_app(restored)) as offline:
        assert (
            offline.get(
                "/api/v1/auth/me", headers={"cookie": "resolveflow_session=" + cookie}
            ).status_code
            == 503
        )
    with pytest.raises(DatabaseUnavailableError), checkpoint_store(restored, setup=True):
        pytest.fail("A quarantined checkpoint connection was granted")
    with pytest.raises(BackupError, match="authoritative_seal"):
        reconcile(target, restored, old_seal)
    witness = settings.erasure_witness_root / journal.NAME
    witness.rename(witness.with_suffix(".offline"))
    with pytest.raises(FileNotFoundError):
        reconcile(target, restored, seal)
    witness.with_suffix(".offline").rename(witness)
    # Simulate correlated storage rollback. Only a separately trusted current
    # seal distinguishes these matching, outdated copies from the complete history.
    primary = settings.erasure_journal_root / journal.NAME
    original = primary.read_bytes()
    try:
        for path in (primary, witness):
            path.write_bytes(original[:33])
        with pytest.raises(BackupError, match="authoritative_seal_mismatch"):
            reconcile(target, restored, seal)
    finally:
        for path in (primary, witness):
            path.write_bytes(original)
    from resolveflow.services import erasure

    original_erase = erasure.erase_rows

    def stop_after_scrub(db, user):
        original_erase(db, user)
        raise RuntimeError("synthetic interrupted reconciliation")

    with monkeypatch.context() as patch:
        patch.setattr(erasure, "erase_rows", stop_after_scrub)
        with pytest.raises(RuntimeError, match="interrupted reconciliation"):
            reconcile(target, restored, seal)
    with Session(target) as db:
        assert db.get(User, uid).avatar_png and db.get(AccountErasure, uid) is None
    with TestClient(create_asgi_app(restored)) as offline:
        assert (
            offline.get(
                "/api/v1/auth/me", headers={"cookie": "resolveflow_session=" + cookie}
            ).status_code
            == 503
        )
    assert reconcile(target, restored, seal) == {
        "verified_ids": 1,
        "replayed": 1,
        "private_file_holds": 0,
        "quarantined": True,
    }
    assert reconcile(target, restored, seal)["replayed"] == 0
    with Session(target) as db:
        assert db.get(User, uid) is None and db.get(User, retained)
        assert db.get(AccountErasure, uid) and db.scalar(select(GoogleFlow)) is None
        for model in (AuthSession, ProviderIdentity):
            assert db.scalar(select(model).where(model.user_id == uid)) is None
    fresh = restore_into(
        repo,
        snapshot["snapshot"],
        database_factory(),
        tmp_path / "complete-restore",
        settings=settings,
        expected_seal=seal,
    )
    assert fresh["erasure"]["replayed"] == 1 and fresh["erasure"]["quarantined"]
    with Session(engine) as db:
        assert journal.current_seal(db, settings) == seal and db.get(User, retained)


@pytest.mark.parametrize("after_commit", [False, True])
def test_interrupted_erasure_journal(auth_env, monkeypatch, after_commit):
    engine, app, client = auth_env
    settings = app.app.state.settings
    uid = uuid.UUID(register(client)["id"])
    prove(client)
    original = journal.append

    def inject(stream, data):
        witness = settings.erasure_witness_root / journal.NAME
        if after_commit and os.path.samestat(os.fstat(stream.fileno()), witness.stat()):
            raise OSError("interrupted before witness")
        original(stream, data)
        if not after_commit:
            raise OSError("interrupted after durable intent")

    with monkeypatch.context() as patch:
        patch.setattr(journal, "append", inject)
        assert confirm(client).status_code == 503
    with Session(engine) as db:
        with pytest.raises(BackupError):
            journal.current_seal(db, settings)
        if after_commit:
            assert db.get(User, uid) is None
            journal.seal_interrupted(db, settings)
        else:
            assert db.get(User, uid)
            with pytest.raises(BackupError, match="uncommitted"):
                journal.seal_interrupted(db, settings)
    if not after_commit:
        assert confirm(client).is_success
    with Session(engine) as db:
        assert len(journal.current_seal(db, settings)) == 64 and db.get(AccountErasure, uid)


def test_quarantined_or_unbound_source_cannot_initialize(auth_env, tmp_path):
    engine, app, _ = auth_env
    settings = app.app.state.settings
    with Session(engine) as db, pytest.raises(BackupError, match="already_bound"):
        journal.initialize(db, settings)
    quarantine_restore(engine)
    with Session(engine) as db, pytest.raises(BackupError, match="source_only"):
        journal.seal_interrupted(db, settings)


def test_snapshot_with_private_file_hold_stays_offline(auth_env, repo, database_factory, tmp_path):
    from test_auth_workspaces import workspace
    from test_invitations import issue

    engine, app, owner = auth_env
    settings = app.app.state.settings
    settings.invitation_delivery_root = tmp_path / "owned-mail"
    register(owner)
    space = workspace(owner)
    with closing(TestClient(app)) as guest:
        recipient = register(guest)
        invitation, _ = issue(owner, space, recipient)
        mailbox = settings.invitation_delivery_root / uuid.UUID(space["id"]).hex
        known = mailbox / uuid.UUID(invitation["id"]).hex
        ambiguous = mailbox / uuid.uuid4().hex
        ambiguous.write_bytes(b"fictional unassigned mailbox")
        ambiguous.chmod(0o600)
        app.app.state.database.dispose()
        snapshot = capture(repo, engine, settings, quiesced=True)
        prove(guest)
        assert confirm(guest).json() == {"cleanup": "complete"} and not known.exists()
    with Session(engine) as db:
        seal = journal.current_seal(db, settings)
    target = database_factory()
    with pytest.raises(BackupError, match="private_file_review"):
        restore_into(
            repo,
            snapshot["snapshot"],
            target,
            tmp_path / "held-restore",
            settings=settings,
            expected_seal=seal,
        )
    with Session(target) as db:
        uid = uuid.UUID(recipient["id"])
        assert db.get(User, uid) is None and db.get(AccountErasure, uid).files
    assert reconcile(target, settings, seal)["private_file_holds"] == 1
    assert ambiguous.read_bytes() == b"fictional unassigned mailbox" and not known.exists()


def test_unbound_snapshot_cannot_be_certified(
    base_auth, repo, database_factory, tmp_path, monkeypatch
):
    engine, app, client = base_auth
    register(client)
    settings = app.app.state.settings
    app.app.state.database.dispose()
    snapshot = capture(repo, engine, settings, quiesced=True)
    target = database_factory()
    from sqlalchemy import text

    from resolveflow.backups import service

    interrupted = database_factory()
    original_pg = service.pg

    def stop_after_import(engine, directory, program, *args):
        result = original_pg(engine, directory, program, *args)
        if program == "pg_restore" and "--dbname" in args:
            raise OSError("synthetic interrupted restore")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(service, "pg", stop_after_import)
        with pytest.raises(OSError, match="interrupted restore"):
            restore_into(
                repo, snapshot["snapshot"], interrupted, tmp_path / "interrupted", settings=settings
            )
    with Session(interrupted) as db:
        assert db.scalar(text(journal.QUARANTINED))
    assert repo.status().get("restore") is None
    with pytest.raises(BackupError, match="unbound_snapshot_quarantined"):
        restore_into(repo, snapshot["snapshot"], target, tmp_path / "legacy", settings=settings)
    with Session(target) as db:
        assert db.scalar(text(journal.QUARANTINED))
        with pytest.raises(BackupError, match="source_only"):
            journal.initialize(db, settings)


def test_journal_permissions_and_location_fail_closed(auth_env, tmp_path):
    engine, app, client = auth_env
    settings = app.app.state.settings
    uid = uuid.UUID(register(client)["id"])
    prove(client)
    witness = settings.erasure_witness_root
    witness.chmod(0o755)
    assert confirm(client).status_code == 503
    witness.chmod(0o700)
    settings.erasure_witness_root = settings.erasure_journal_root
    assert confirm(client).status_code == 503
    settings.erasure_witness_root = None
    assert confirm(client).status_code == 503
    with Session(engine) as db:
        assert db.get(User, uid) and not db.get(AccountErasure, uid)
    settings.erasure_witness_root = witness
    assert confirm(client).is_success
