"""Real encrypted database/document recovery and fail-closed operational boundaries."""

import json
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text
from test_documents import env as document_env
from test_documents import upload

from resolveflow.backups.repository import Repository, initialize
from resolveflow.backups.safety import BackupError, exclusive, private, run, safe_path
from resolveflow.backups.service import capture, enough_space, owned, restore_into, validate_bundle
from resolveflow.core.config import API_ROOT
from scripts.backups import schedule
from scripts.local_db import BIN

ROOT = API_ROOT.parents[1]
RESTIC = ROOT / ".local/native/restic-0.19.1/restic"
env = document_env


@pytest.fixture
def repo(tmp_path):
    return initialize(tmp_path / "control", tmp_path / "repository", RESTIC, BIN)


def test_repository_credentials_encryption_and_identity(repo, tmp_path):
    assert repo.status()["stale"]
    key = repo.config.password_file
    private(key)
    secret = key.read_bytes()
    key.write_text("wrong-password-that-is-long-enough-to-check\n")
    with pytest.raises(BackupError, match="tool_failed"):
        Repository(repo.state)
    key.write_bytes(secret)
    config = repo.state / "config.json"
    values = json.loads(config.read_text())
    values["repository_id"] = "wrong"
    config.write_text(json.dumps(values))
    with pytest.raises(BackupError, match="repository_identity_mismatch"):
        Repository(repo.state)
    values["repository_id"] = repo.config.repository_id
    config.write_text(json.dumps(values))
    key.chmod(0o644)
    with pytest.raises(BackupError, match="private_permissions"):
        Repository(repo.state)
    key.chmod(0o600)
    key.unlink()
    with pytest.raises(FileNotFoundError):
        Repository(repo.state)
    assert not list(repo.state.glob("snapshot-*"))


def test_paths_concurrency_and_space(repo, tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "link"
    link.symlink_to(outside, target_is_directory=True)
    for path in (link / "file", Path("relative"), tmp_path / ".." / "escape"):
        with pytest.raises(BackupError):
            safe_path(path)
    with exclusive(repo.state), pytest.raises(BackupError, match="busy"), exclusive(repo.state):
        pass
    with exclusive(repo.state):
        pass
    with pytest.raises(BackupError, match="insufficient_disk"):
        enough_space(repo.state, 10**30)
    with pytest.raises(BackupError, match="destination_exists"):
        initialize(repo.state, repo.config.repository, RESTIC, BIN)


def test_schedule_and_redacted_tool_errors(tmp_path):
    config = schedule(tmp_path, 3, 15)
    assert config["StartCalendarInterval"] == {"Hour": 3, "Minute": 15}
    assert config["ProgramArguments"][-1] == "scheduled"
    assert "password" not in json.dumps(config).lower()
    with pytest.raises(BackupError, match="invalid_schedule"):
        schedule(tmp_path, 25, 0)
    with pytest.raises(BackupError) as caught:
        run(Path("/bin/sh"), ["-c", "echo synthetic-secret >&2; exit 1"], {})
    assert str(caught.value) == "tool_failed"
    assert (
        subprocess.run(
            ["git", "check-ignore", "-q", ".local/encrypted-backups/config"], cwd=ROOT
        ).returncode
        == 0
    )


@pytest.mark.integration
def test_real_encrypted_backup_restore_and_failures(
    env, database_factory, repo, tmp_path, monkeypatch
):
    engine, app, client, user, workspace, base, settings = env
    content = b"Unique synthetic encrypted backup document for workspace recovery."
    document = upload(client, base, "backup.txt", content).json()
    assert document["processing_status"] == "completed"
    app.app.state.database.dispose()
    with pytest.raises(BackupError, match="maintenance_confirmation"):
        capture(repo, engine, settings)
    with engine.connect() as active:
        active.execute(text("SELECT 1"))
        with pytest.raises(BackupError, match="clients_active"):
            capture(repo, engine, settings, quiesced=True)
    with pytest.raises(BackupError, match="unowned"):
        other = type("Engine", (), {"url": engine.url.set(database="unrelated")})()
        owned(other)
    backup = capture(repo, engine, settings, quiesced=True)
    assert backup["documents"] == 1 and len(backup["snapshot"]) == 64
    assert not list(repo.state.glob("snapshot-*"))
    assert all(
        content not in p.read_bytes() for p in repo.config.repository.rglob("*") if p.is_file()
    )
    with pytest.raises(BackupError, match="latest_restore_required"):
        repo.retention(True)
    with pytest.raises(BackupError, match="restore_target_not_empty"):
        restore_into(repo, "latest", engine, tmp_path / "unsafe")
    target = database_factory()
    restored = tmp_path / "restored"
    result = restore_into(repo, backup["snapshot"], target, restored)
    assert result["documents"] == 1 and not result["workers_started"]
    manifest = validate_bundle(restored / "bundle")
    assert manifest["tables"]["public.users"]["rows"] == 1
    assert manifest["tables"]["public.document_chunks"]["rows"] > 0
    file = next((restored / "bundle/documents").rglob("*/*"))
    assert file.read_bytes() == content
    file.write_bytes(b"corrupt")
    with pytest.raises(BackupError, match="integrity"):
        validate_bundle(restored / "bundle")
    file.write_bytes(content)
    manifest_path = restored / "bundle/manifest.json"
    original_manifest = manifest_path.read_bytes()
    damaged = json.loads(original_manifest)
    damaged["version"] = 999
    manifest_path.write_text(json.dumps(damaged))
    with pytest.raises(BackupError, match="integrity"):
        validate_bundle(restored / "bundle")
    manifest_path.write_bytes(original_manifest)
    assert repo.retention(False)["latest_preserved"]
    # Real repeated execution creates distinct snapshots, never overwriting prior history.
    second = capture(repo, engine, settings, quiesced=True)
    assert second["snapshot"] != backup["snapshot"]
    restore_into(repo, second["snapshot"], database_factory(), tmp_path / "second")
    assert repo.retention(True)["remaining"] == 2
    with engine.connect() as conn:
        key = conn.execute(text("SELECT storage_key FROM documents")).scalar_one()
    source = settings.document_storage_root / workspace["id"].replace("-", "") / key
    original = source.read_bytes()
    source.unlink()
    with pytest.raises(FileNotFoundError):
        capture(repo, engine, settings, quiesced=True)
    assert len(repo.snapshots()) == 2
    source.write_bytes(original)
    source.chmod(0o600)
    # Corrupt only this disposable encrypted repository; full data verification must fail.
    pack = next(p for p in (repo.config.repository / "data").rglob("*") if p.is_file())
    pack.chmod(0o600)  # Fault injection only in this test-created repository.
    pack.write_bytes(b"corrupt encrypted pack")
    with pytest.raises(BackupError, match="tool_failed"):
        repo.check()


@pytest.mark.parametrize(
    "failure", ["interrupted", "database_unavailable", "repository_unavailable"]
)
def test_cli_failure_is_reported_without_secrets(repo, monkeypatch, capsys, failure):
    import sys

    from scripts import backups

    class FailingRepository:
        def __init__(self, state):
            if failure == "repository_unavailable":
                raise FileNotFoundError("synthetic-secret-path")

        def status(self):
            if failure == "interrupted":
                raise KeyboardInterrupt
            raise ConnectionError("synthetic-database-password")

    monkeypatch.setattr(backups, "Repository", FailingRepository)
    monkeypatch.setattr(sys, "argv", ["backups.py", "--state", str(repo.state), "status"])
    assert backups.main() == 1
    output = capsys.readouterr()
    expected = "backup_interrupted" if failure == "interrupted" else "backup_operation_failed"
    assert json.loads(output.err) == {"ok": False, "code": expected}
    assert "synthetic" not in output.out + output.err
    assert json.loads((repo.state / "status.json").read_text())["failure"]["code"] == expected
    with exclusive(repo.state):
        pass


def test_actual_repository_unavailable_preserves_history(repo):
    saved = repo.config.repository.with_name("temporarily-unavailable")
    repo.config.repository.rename(saved)
    try:
        with pytest.raises(FileNotFoundError):
            Repository(repo.state)
    finally:
        saved.rename(repo.config.repository)
    assert Repository(repo.state).snapshots() == []


@pytest.mark.integration
def test_interrupted_capture_releases_database_and_staging(env, repo, monkeypatch):
    from resolveflow.backups import service

    engine, app, _, _, _, _, settings = env
    app.app.state.database.dispose()
    original = service.pg

    def interrupted_dump(engine, binary_directory, tool, *args):
        if tool == "pg_dump" and "--version" not in args:
            raise KeyboardInterrupt
        return original(engine, binary_directory, tool, *args)

    monkeypatch.setattr(service, "pg", interrupted_dump)
    with pytest.raises(KeyboardInterrupt):
        capture(repo, engine, settings, quiesced=True)
    assert not list(repo.state.glob("snapshot-*"))
    assert repo.snapshots() == []
    assert "backup" not in repo.status()
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL lock_timeout='500ms'"))
        conn.execute(text("LOCK TABLE users IN ACCESS EXCLUSIVE MODE"))
