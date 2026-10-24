"""Quiesced synthetic snapshot/restore into a second owned, initially empty DB.

Never accepts a database name/path from CLI input. No developer records are
backed up or restored. Credentials go to child environment, never argv/logs.
"""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from test_auth_workspaces import mutate, register
from test_documents import env as document_env
from test_embeddings import real_embeddings as embedding_fixture
from test_jobs import deliver, location, start
from test_ml import trained_model as trained_fixture
from test_rag import POLICY, setup

from resolveflow.backups.repository import initialize
from resolveflow.backups.service import capture, restore_into
from resolveflow.core.config import API_ROOT
from resolveflow.db.session import Database
from resolveflow.documents.models import Document
from resolveflow.jobs.models import WorkflowJob
from resolveflow.main import create_asgi_app
from resolveflow.ml.classifier import LocalTicketClassifier
from resolveflow.rag.models import DraftReview, ResponseDraft
from resolveflow.workflows.storage import checkpoint_store
from scripts.local_db import BIN

pytestmark = pytest.mark.integration
env = document_env
real_embeddings = embedding_fixture
trained_model = trained_fixture


def owned(engine, *, empty=False):
    name = engine.url.database
    assert name and name.startswith("resolveflow_test_")
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    with engine.connect() as conn:
        marker = conn.scalar(
            text(
                "SELECT shobj_description(oid, 'pg_database') FROM pg_database "
                "WHERE datname=current_database()"
            )
        )
        assert marker and marker.startswith("resolveflow-pytest-")
        if empty:
            assert (
                conn.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema NOT IN ('pg_catalog', 'information_schema')"
                    )
                )
                == 0
            )
    return marker


def pg_tool(engine, tool, *arguments):
    owned(engine)
    url = engine.url
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PGHOST": url.host,
        "PGPORT": str(url.port),
        "PGUSER": url.username,
        "PGPASSWORD": url.password or "",
        "PGDATABASE": url.database,
        "PGCONNECT_TIMEOUT": "5",
    }
    result = subprocess.run(
        [str(BIN / tool), *map(str, arguments)], env=env, capture_output=True, timeout=60
    )
    assert result.returncode == 0, f"Isolated {tool} failed (details suppressed)"


def manifest(root):
    assert root.is_dir() and not root.is_symlink()
    values = {}
    for path in sorted(root.rglob("*")):
        assert not path.is_symlink(), "Snapshot sources cannot contain symlinks"
        if path.is_file():
            values[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def checked_copy(source, destination):
    expected = manifest(source)
    shutil.copytree(source, destination)
    assert manifest(destination) == expected
    return len(expected)


@pytest.mark.parametrize("encrypted", [False, True])
def test_quiesced_backup_restore_checkpoint_and_private_files(
    env, real_embeddings, trained_model, database_factory, tmp_path, encrypted
):
    source_engine, source_app, source, _, space, document_base, settings = env
    assert settings.environment == "test" and not settings.ai_live_enabled
    settings.ai_provider = "fixture"
    settings.classifier_artifact_root = trained_model
    settings.classifier_model_version = "test-v1"
    source_app.app.state.classifier = LocalTicketClassifier(trained_model, "test-v1", 0.45)
    client, ticket_path, body, doc = setup(env, real_embeddings)
    with checkpoint_store(settings, setup=True):
        pass
    database = Database(settings)
    try:
        fixture = env, client, ticket_path, body, database
        run = start(fixture)
        paused = deliver(fixture, run)
        assert paused["status"] == "paused" and paused["draft"]["can_approve"]
        assert (
            mutate(
                source,
                ticket_path + f"/drafts/{paused['draft']['id']}/review",
                {
                    "action": "approved",
                    "expected_version": 1,
                },
            ).status_code
            == 200
        )
        # Quiesced point: no workers/dispatchers or concurrent writes in these owned DBs.
        target_engine = database_factory()
        source_marker, target_marker = owned(source_engine), owned(target_engine, empty=True)
        assert source_engine.url.database != target_engine.url.database
        snapshot_start = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="resolveflow-restore-", dir=tmp_path) as directory:
            root = Path(directory)
            if encrypted:
                source_app.app.state.database.dispose()
                database.dispose()
                repo = initialize(
                    root / "control",
                    root / "repository",
                    API_ROOT.parents[1] / ".local/native/restic-0.19.1/restic",
                    BIN,
                )
                saved = capture(repo, source_engine, settings, quiesced=True)
                backup_seconds = time.perf_counter() - snapshot_start
                recovery_start = time.perf_counter()
                restored_result = restore_into(
                    repo, saved["snapshot"], target_engine, root / "recovered"
                )
                assert restored_result["documents"] == 1
                files = checked_copy(
                    root / "recovered/bundle/documents", root / "restored-documents"
                )
                checked_copy(root / "recovered/bundle/classifier", root / "restored-classifier")
                # Reprovision the pinned downloadable model, intentionally absent from backup.
                embedding_root = Path(
                    os.environ.get(
                        "TEST_EMBEDDING_MODEL_ROOT",
                        API_ROOT.parents[1] / ".local/embeddings/minilm-v1",
                    )
                )
                checked_copy(embedding_root, root / "restored-embeddings")
            else:
                archive = root / "database.dump"
                archive.touch(mode=0o600)
                pg_tool(
                    source_engine,
                    "pg_dump",
                    "--format=custom",
                    "--no-owner",
                    "--no-privileges",
                    "--file",
                    archive,
                )
                digest = hashlib.sha256(archive.read_bytes()).hexdigest()
                files = checked_copy(settings.document_storage_root, root / "backup-documents")
                checked_copy(trained_model, root / "backup-classifier")
                embedding_root = Path(
                    os.environ.get(
                        "TEST_EMBEDDING_MODEL_ROOT",
                        API_ROOT.parents[1] / ".local/embeddings/minilm-v1",
                    )
                )
                checked_copy(embedding_root, root / "backup-embeddings")
                backup_seconds = time.perf_counter() - snapshot_start
                recovery_start = time.perf_counter()
                # Check both file integrity and destination ownership before any restoration.
                assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest
                assert owned(target_engine, empty=True) == target_marker
                pg_tool(
                    target_engine,
                    "pg_restore",
                    "--no-owner",
                    "--no-privileges",
                    "--exit-on-error",
                    "--single-transaction",
                    "--dbname",
                    target_engine.url.database,
                    archive,
                )
                checked_copy(root / "backup-documents", root / "restored-documents")
                checked_copy(root / "backup-classifier", root / "restored-classifier")
                checked_copy(root / "backup-embeddings", root / "restored-embeddings")
            restored_settings = settings.model_copy(
                update={
                    "database_url": SecretStr(
                        target_engine.url.render_as_string(hide_password=False)
                    ),
                    "document_storage_root": root / "restored-documents",
                    "classifier_artifact_root": root / "restored-classifier",
                    "embedding_model_root": root / "restored-embeddings",
                }
            )
            restored_database = Database(restored_settings)
            try:
                with TestClient(create_asgi_app(restored_settings)) as restored:
                    restored.cookies.update(source.cookies)
                    state = restored.app.app.state
                    assert state.classifier.health_check() and state.embeddings.health_check()
                    assert state.ai_provider.get_model_info().fixture

                    # No inference may occur while recovering an already generated draft.
                    def forbidden(_):
                        pytest.fail("Restoring an approved pause must not regenerate")

                    state.ai_provider.generate_structured = forbidden
                    run_path = location(fixture, run)
                    recovered = restored.get("/api/v1" + run_path)
                    assert recovered.status_code == 200
                    assert recovered.json()["status"] == "paused"
                    assert recovered.json()["draft"]["approval_current"]
                    assert recovered.json()["draft"]["id"] == paused["draft"]["id"]
                    download = document_base + f"/{doc['id']}/download"
                    assert restored.get("/api/v1" + download).content == POLICY
                    result = mutate(
                        restored,
                        f"/workspaces/{space['id']}/knowledge-base/search",
                        {"query": "refund policy"},
                    )
                    assert result.status_code == 200 and result.json()["results"]
                    assert mutate(restored, run_path + "/resume", {}).status_code == 202
                    target_env = (
                        target_engine,
                        restored.app,
                        restored,
                        *env[3:6],
                        restored_settings,
                    )
                    target_fixture = target_env, restored, ticket_path, body, restored_database
                    completed = deliver(target_fixture, run)
                    assert (
                        completed["status"] == "completed"
                        and completed["draft"]["approval_current"]
                    )
                    assert deliver(target_fixture, run)["draft"]["id"] == paused["draft"]["id"]
                    with Session(target_engine) as db:
                        for model in (ResponseDraft, DraftReview, WorkflowJob):
                            assert db.scalar(select(func.count()).select_from(model)) == 1
                        saved_doc = db.get(Document, uuid.UUID(doc["id"]))
                        # Corruption/missing file must fail safely, never serve guessed content.
                        object_file = (
                            root
                            / "restored-documents"
                            / uuid.UUID(space["id"]).hex
                            / saved_doc.storage_key
                        )
                        original = object_file.read_bytes()
                        object_file.write_bytes(b"corrupted synthetic file")
                        assert restored.get("/api/v1" + download).status_code == 503
                        object_file.unlink()
                        assert restored.get("/api/v1" + download).status_code == 503
                        object_file.write_bytes(original)
                        object_file.chmod(0o600)
                    assert restored.get("/api/v1" + download).content == POLICY
                    with TestClient(create_asgi_app(restored_settings)) as outsider:
                        register(outsider)
                        assert outsider.get("/api/v1" + run_path).status_code == 404
                        assert outsider.get("/api/v1" + download).status_code == 404
                    recovery_seconds = time.perf_counter() - recovery_start
                    assert (
                        recovery_seconds < 120
                    )  # Local synthetic drill target, not a production SLA.
            finally:
                restored_database.dispose()
            assert owned(source_engine) == source_marker and owned(target_engine) == target_marker
            # Source pause and document remain unchanged after all target mutations.
            assert source.get("/api/v1" + location(fixture, run)).json()["status"] == "paused"
            assert (
                source.get("/api/v1" + document_base + f"/{doc['id']}/download").content == POLICY
            )
            report = {
                "scope": "quiesced synthetic local restore; not off-host disaster recovery",
                "encrypted_restic": encrypted,
                "backup_seconds": round(backup_seconds, 3),
                "restore_and_validation_seconds": round(recovery_seconds, 3),
                "local_rto_target_seconds": 120,
                "snapshot_rpo": "zero committed records lost at the quiesced snapshot",
                "private_document_files": files,
                "checkpoint_resumed": True,
                "duplicate_drafts": 0,
                "source_unchanged": True,
                "missing_corrupt_file_fail_closed": True,
                "tenant_denial_verified": True,
                "live_ai_calls": 0,
            }
            destination = API_ROOT.parents[1] / (
                ".cache/verification/encrypted-restore-drill.json"
                if encrypted
                else ".cache/verification/restore-drill.json"
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(report, indent=2) + "\n")
    finally:
        database.dispose()
