"""Crash boundaries in the real service, using disposable PostgreSQL and a private mailbox."""

import json
import multiprocessing
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from test_auth_workspaces import auth_env as auth_fixture
from test_auth_workspaces import mutate, register, workspace

from resolveflow.core.config import Settings
from resolveflow.db.models import InvitationDelivery, User, WorkspaceInvitation
from resolveflow.documents.storage import LocalFileStorage
from resolveflow.main import create_asgi_app
from resolveflow.schemas.auth import MemberInput
from resolveflow.services import invitations
from resolveflow.services.invitation_delivery import deliver
from resolveflow.services.invitation_files import checksum
from resolveflow.services.invitation_inventory import inventory

pytestmark = pytest.mark.integration
auth_env = auth_fixture


def interrupt(url, root, actor_id, workspace_id, email, phase):
    settings = Settings(
        _env_file=None,
        environment="test",
        invitation_delivery="local",
        invitation_delivery_root=root,
    )

    def crash(*args, **kwargs):
        os._exit(73)

    with Session(create_engine(url), expire_on_commit=False) as db:
        original = LocalFileStorage.save

        def write(storage, space, key, data, create_only):
            if phase == "after_intent":
                crash()
            if phase == "partial":
                with storage.directory(space, key) as folder:
                    fd = os.open(
                        f"{key}.{checksum(data)}.part",
                        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                        0o600,
                        dir_fd=folder,
                    )
                    os.write(fd, data[:23])
                    os.fsync(fd)
                    crash()
            original(storage, space, key, data, create_only)
            if phase == "after_file":
                crash()

        if phase == "before_intent":
            # Flush the INSERT into a real uncommitted PostgreSQL transaction.
            def rollback_on_disconnect():
                db.flush()
                crash()

            db.commit = rollback_on_disconnect
        LocalFileStorage.save = write
        if phase == "before_link":
            os.link = crash
        if phase == "after_link":
            os.unlink = crash
        invitations.issue(
            db, db.get(User, actor_id), workspace_id, MemberInput(email=email), settings
        )


@pytest.fixture
def mailbox(auth_env, tmp_path):
    engine, app, owner = auth_env
    settings = app.app.state.settings
    settings.invitation_delivery = "local"
    settings.invitation_delivery_root = tmp_path / "mail"
    actor = register(owner)
    space = workspace(owner)
    with TestClient(create_asgi_app(settings)) as recipient:
        target = register(recipient)
        yield (
            engine,
            settings,
            owner,
            recipient,
            uuid.UUID(actor["id"]),
            uuid.UUID(space["id"]),
            target,
        )


def crash_at(mailbox, phase):
    engine, settings, _, _, actor, space, target = mailbox
    child = multiprocessing.get_context("spawn").Process(
        target=interrupt,
        args=(
            engine.url.render_as_string(hide_password=False),
            settings.invitation_delivery_root,
            actor,
            space,
            target["email"],
            phase,
        ),
    )
    child.start()
    try:
        child.join(30)
        assert child.exitcode == 73
    finally:
        if child.is_alive():
            child.terminate()
            child.join(10)
        child.close()


@pytest.mark.parametrize(
    "phase", ["before_intent", "after_intent", "partial", "before_link", "after_link", "after_file"]
)
def test_restart_under_real_process_loss(mailbox, phase):
    engine, settings, owner, recipient, actor, space, target = mailbox
    crash_at(mailbox, phase)
    root = settings.invitation_delivery_root
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(WorkspaceInvitation)) == 0
        intent = db.scalar(select(InvitationDelivery))
        if phase == "before_intent":
            assert intent is None and not root.exists()
            return
        assert intent.status == "pending"
        assert (intent.workspace_id, intent.issuer_id, intent.recipient_id) == (
            space,
            actor,
            uuid.UUID(target["id"]),
        )
        identifier = intent.id
        first = intent.attempts[0]
    folder = root / space.hex
    final = folder / identifier.hex
    stage = folder / f"{identifier.hex}.{first}.part"
    assert final.exists() == (phase in {"after_link", "after_file"})
    assert stage.exists() == (phase in {"partial", "before_link", "after_link"})
    if final.exists():
        assert (
            mutate(
                recipient,
                "/auth/invitations/accept",
                {"token": json.loads(final.read_bytes())["token"]},
            ).status_code
            == 400
        )

    def retry(_):
        with Session(engine) as db:
            row = deliver(db, settings, identifier)
            return row.id if row else None

    if phase == "after_file":
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert list(pool.map(retry, range(2))) == [identifier, identifier]
    else:
        assert retry(0) == identifier
    content = final.read_bytes()
    assert retry(0) == identifier and final.read_bytes() == content
    assert final.stat().st_mode & 0o777 == 0o600
    with Session(engine) as db:
        intent = db.get(InvitationDelivery, identifier)
        assert intent.status == "delivered" and intent.attempts[-1] == checksum(content)
        assert len(intent.attempts) == (2 if phase in {"partial", "after_intent"} else 1)
        assert db.scalar(select(func.count()).select_from(WorkspaceInvitation)) == 1
        statuses = [status for _, status in inventory(db, root)]
        assert "verified_final" in statuses
        if phase == "partial":
            assert stage.stat().st_size == 23 and "hold_incomplete_or_altered_stage" in statuses
        else:
            assert not stage.exists()
    token = json.loads(content)["token"]
    assert mutate(owner, "/auth/invitations/accept", {"token": token}).status_code == 400
    assert mutate(recipient, "/auth/invitations/accept", {"token": token}).status_code == 201


def test_reused_address_cannot_inherit_pending_delivery(mailbox):
    engine, settings, _, _, _, _, target = mailbox
    crash_at(mailbox, "after_intent")
    with Session(engine) as db:
        user = db.get(User, uuid.UUID(target["id"]))
        user.email = "changed@example.com"
        db.commit()
    with TestClient(create_asgi_app(settings)) as other:
        replacement = register(other, target["email"])
        assert replacement["id"] != target["id"]
        with Session(engine) as db:
            intent = db.scalar(select(InvitationDelivery))
            assert deliver(db, settings, intent.id) is None
            assert intent.status == "cancelled" and intent.recipient_id == uuid.UUID(target["id"])
            assert not list(settings.invitation_delivery_root.rglob("*.*"))
            assert db.scalar(select(WorkspaceInvitation)) is None


def test_inventory_quarantines_foreign_and_unattributed_files_in_place(mailbox):
    engine, settings, owner, _, _, space, target = mailbox
    crash_at(mailbox, "after_file")
    other = uuid.UUID(workspace(owner)["id"])
    root = settings.invitation_delivery_root
    with Session(engine) as db:
        record = db.scalar(select(InvitationDelivery))
        final = root / space.hex / record.id.hex
        original = final.read_bytes()
        foreign = root / other.hex / final.name
        foreign.parent.mkdir(mode=0o700)
        foreign.write_bytes(original)
        foreign.chmod(0o600)
        ambiguous = final.with_name(uuid.uuid4().hex)
        ambiguous.write_text(json.dumps({"recipient": target["email"]}))
        ambiguous.chmod(0o600)
        altered = b'{"recipient":"unattributed@example.com"}'
        final.write_bytes(altered)
        (final.parent / "unsafe").symlink_to(foreign)
        findings = list(inventory(db, root))
        statuses = {status for _, status in findings}
        assert {
            "hold_location_mismatch",
            "hold_missing_ownership",
            "hold_unverified_content",
            "hold_unknown_name",
        } <= statuses
        assert target["email"] not in str(findings) and json.loads(original)["token"] not in str(
            findings
        )
        assert deliver(db, settings, record.id) is None and record.status == "held"
        assert db.scalar(select(WorkspaceInvitation)) is None
        assert final.read_bytes() == altered and foreign.read_bytes() == original
        assert json.loads(ambiguous.read_bytes())["recipient"] == target["email"]


def test_legacy_inventory_requires_database_scope_and_token_proof(mailbox):
    from datetime import UTC, datetime, timedelta

    from resolveflow.db.models import MembershipRole
    from resolveflow.services.auth import digest

    engine, settings, _, _, actor, space, target = mailbox
    root = settings.invitation_delivery_root
    folder = root / space.hex
    root.mkdir(mode=0o700)
    folder.mkdir(mode=0o700)
    expires = datetime.now(UTC) + timedelta(hours=1)
    with Session(engine) as db:
        invitation = WorkspaceInvitation(
            id=uuid.uuid4(),
            workspace_id=space,
            issued_by=actor,
            user_id=uuid.UUID(target["id"]),
            email=target["email"],
            role=MembershipRole.VIEWER,
            expires_at=expires,
            token_hash=digest("a" * 43),
        )
        db.add(invitation)
        db.commit()
        final = folder / invitation.id.hex
        legacy = {
            "kind": "local_synthetic_invitation",
            "workspace": "Support",
            "recipient": target["email"],
            "expires_at": expires.isoformat(),
            "token": "a" * 43,
        }
        final.write_text(json.dumps(legacy))
        final.chmod(0o600)
        assert [s for _, s in inventory(db, root)] == ["legacy_correlated"]
        final.write_text(json.dumps({**legacy, "token": "b" * 43}))
        assert [s for _, s in inventory(db, root)] == ["hold_unverified_legacy"]
        partial = final.with_suffix(".part")
        partial.write_text(json.dumps(legacy))
        partial.chmod(0o600)
        assert {s for _, s in inventory(db, root)} == {
            "hold_unverified_legacy",
            "hold_missing_ownership",
        }
        assert db.scalar(select(InvitationDelivery)) is None
        assert json.loads(partial.read_text()) == legacy


def test_retry_cannot_deliver_to_different_mailbox_root(mailbox, tmp_path):
    engine, settings, _, _, _, _, _ = mailbox
    crash_at(mailbox, "after_intent")
    different_root = tmp_path / "unrelated"
    with Session(engine) as db:
        record = db.scalar(select(InvitationDelivery))
        redirected = settings.model_copy(update={"invitation_delivery_root": different_root})
        assert deliver(db, redirected, record.id) is None
        assert record.status == "pending" and not different_root.exists()
        assert deliver(db, settings, record.id).id == record.id
        assert deliver(db, redirected, record.id) is None
        assert not different_root.exists()


def test_operator_inventory_signals_holds_without_exposing_contents(mailbox, monkeypatch, capsys):
    import sys

    from scripts import invitation_mailbox

    engine, settings, _, _, _, _, target = mailbox
    crash_at(mailbox, "after_file")
    monkeypatch.setattr(invitation_mailbox, "Settings", lambda: settings)
    with Session(engine) as db:
        record = db.scalar(select(InvitationDelivery))
        identifier = record.id
        final = settings.invitation_delivery_root / record.workspace_id.hex / identifier.hex
    token = json.loads(final.read_bytes())["token"]

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["invitation_mailbox.py", *args])
        code = invitation_mailbox.main()
        output = capsys.readouterr()
        assert (
            target["email"] not in output.out + output.err and token not in output.out + output.err
        )
        return code, output.out

    assert run("--pending") == (0, str(identifier) + "\n")
    assert run("--retry", str(identifier))[0] == 0
    assert run("--audit")[0] == 0
    legacy = final.with_name(uuid.uuid4().hex)
    legacy.write_bytes(final.read_bytes())
    legacy.chmod(0o600)
    assert run("--audit")[0] == 2 and legacy.exists()
    final.unlink()  # Only this disposable fixture's already-committed final.
    code, summary = run("--audit")
    assert code == 2 and "hold_missing_or_inaccessible_final" in summary
