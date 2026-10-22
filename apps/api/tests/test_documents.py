import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import pytest
from document_fixtures import pdf_bytes
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_auth_workspaces import mutate, register, workspace
from test_database import migrate

from resolveflow.core.config import Settings
from resolveflow.documents.extraction import ProcessingError
from resolveflow.documents.models import Document, DocumentChunk, DocumentStatus
from resolveflow.documents.service import recover
from resolveflow.main import create_asgi_app

pytestmark = pytest.mark.integration


@pytest.fixture
def env(database_factory, tmp_path):
    engine = database_factory()
    migrate(engine)
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=engine.url.render_as_string(hide_password=False),
        document_storage_root=tmp_path / "objects",
    )
    app = create_asgi_app(settings)
    with TestClient(app) as client:
        user = register(client)
        space = workspace(client)
        yield engine, app, client, user, space, f"/workspaces/{space['id']}/documents", settings


def upload(client, base, name="guide.txt", data=b"Support guide for account access."):
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    return client.post(
        "/api/v1" + base,
        content=data,
        headers={
            "origin": "http://127.0.0.1:3000",
            "x-csrf-token": csrf,
            "content-type": "application/octet-stream",
            "x-upload-filename": quote(name, safe=""),
        },
    )


@pytest.mark.parametrize(
    "name,data",
    [
        ("guide.pdf", pdf_bytes(("First page", "Second page"))),
        ("guide.txt", b"Text account guide. " * 200),
        ("guide.md", b"# Account guide\n\n<script>literal only</script>\n\nSteps to sign in."),
    ],
)
def test_upload_persistence_chunks_download_delete(env, name, data):
    engine, app, client, user, space, base, settings = env
    result = upload(client, base, name, data)
    assert result.status_code == 201, result.text
    doc = result.json()
    assert doc["processing_status"] == "completed" and doc["total_chunks"] > 0
    assert doc["uploaded_by_email"] == user["email"]
    assert "storage_key" not in doc and str(settings.document_storage_root) not in result.text
    path = base + "/" + doc["id"]
    chunks = client.get("/api/v1" + path + "/chunks").json()
    assert chunks["total"] == doc["total_chunks"]
    assert [c["chunk_index"] for c in chunks["items"]] == list(range(len(chunks["items"])))
    assert all(
        c["source_metadata"]["filename"] == name and c["workspace_id"] == space["id"]
        for c in chunks["items"]
    )
    if name.endswith(".pdf"):
        assert [c["page_number"] for c in chunks["items"]] == [1, 2]
    download = client.get("/api/v1" + path + "/download")
    assert download.content == data and download.headers["content-disposition"].startswith(
        "attachment;"
    )
    assert download.headers["x-content-type-options"] == "nosniff"
    assert "no-store" in download.headers["cache-control"]
    duplicate = upload(client, base, "renamed" + Path(name).suffix, data).json()
    assert duplicate["id"] == doc["id"]
    assert mutate(client, path + "/retry").json()["total_chunks"] == doc["total_chunks"]
    with Session(engine) as db:
        saved = db.get(Document, uuid.UUID(doc["id"]))
        key = saved.storage_key
        assert app.app.state.document_storage.exists(uuid.UUID(space["id"]), key)
        assert len(db.scalars(select(DocumentChunk)).all()) == doc["total_chunks"]
    assert mutate(client, path, method="DELETE").status_code == 204
    assert client.get("/api/v1" + path).status_code == 404
    assert not app.app.state.document_storage.exists(uuid.UUID(space["id"]), key)
    with Session(engine) as db:
        assert db.scalar(select(Document)) is None and db.scalar(select(DocumentChunk)) is None


def test_list_filters_pagination_and_validation(env):
    _, _, client, _, _, base, settings = env
    for i in range(3):
        assert (
            upload(client, base, f"handbook{i}.txt", f"Unique content {i}".encode()).status_code
            == 201
        )
    assert (
        upload(client, base, "broken.pdf", b"%PDF-1.7 broken").json()["processing_status"]
        == "failed"
    )
    first = client.get(
        "/api/v1" + base,
        params={"search": "handbook", "page_size": 1, "sort": "file_size", "direction": "asc"},
    ).json()
    second = client.get(
        "/api/v1" + base,
        params={
            "search": "handbook",
            "page_size": 1,
            "page": 2,
            "sort": "file_size",
            "direction": "asc",
        },
    ).json()
    assert (
        first["total"] == 3
        and first["pages"] == 3
        and first["items"][0]["id"] != second["items"][0]["id"]
    )
    assert client.get("/api/v1" + base, params={"status": "failed"}).json()["total"] == 1
    assert client.get("/api/v1" + base, params={"search": "absent"}).json()["items"] == []
    for params in (
        {"page": 0},
        {"page_size": 101},
        {"sort": "storage_key"},
        {"status": "invented"},
        {"unknown": "x"},
    ):
        assert client.get("/api/v1" + base, params=params).status_code == 422
    assert (
        upload(
            client, base, "huge.txt", b"x" * (settings.document_upload_max_bytes + 1)
        ).status_code
        == 413
    )
    assert upload(client, base, "empty.txt", b"").status_code == 422
    assert client.get("/api/v1/workspaces/bad/documents").status_code == 422
    assert client.get("/api/v1" + base + "/bad").status_code == 422
    assert (
        client.post(
            "/api/v1" + base,
            content=b"no csrf",
            headers={"content-type": "application/octet-stream", "x-upload-filename": "test.txt"},
        ).status_code
        == 403
    )
    assert client.post("/api/v1/auth/login", content=b"x" * 16385).status_code == 413


def test_failed_processing_and_retry_are_persistent_and_deduplicated(env, monkeypatch):
    engine, _, client, _, _, base, _ = env
    from resolveflow.documents import service

    real = service.extract

    def fail(*args):
        raise ProcessingError("resource_limit")

    monkeypatch.setattr(service, "extract", fail)
    doc = upload(client, base).json()
    assert doc["processing_status"] == "failed" and doc["total_chunks"] == 0
    assert "limits" in doc["processing_error"]
    with Session(engine) as db:
        assert db.scalar(select(DocumentChunk)) is None
    monkeypatch.setattr(service, "extract", real)
    result = mutate(client, base + "/" + doc["id"] + "/retry")
    assert result.status_code == 200 and result.json()["processing_status"] == "completed"
    first = client.get("/api/v1" + base + "/" + doc["id"] + "/chunks").json()
    assert mutate(client, base + "/" + doc["id"] + "/retry").status_code == 200
    assert client.get("/api/v1" + base + "/" + doc["id"] + "/chunks").json() == first


def test_roles_and_cross_tenant_document_content(env):
    _, app, client, _, space, base, _ = env
    doc = upload(client, base).json()
    path = base + "/" + doc["id"]
    with TestClient(create_asgi_app(app.app.state.settings)) as other:
        assert upload(other, base).status_code == 401
        member = register(other)
        other_space = workspace(other)
        for suffix in ("", "/chunks", "/download"):
            assert other.get("/api/v1" + path + suffix).status_code == 404
            assert (
                client.get(
                    f"/api/v1/workspaces/{space['id']}/documents/{uuid.uuid4()}" + suffix
                ).status_code
                == 404
            )
            assert (
                other.get(
                    f"/api/v1/workspaces/{other_space['id']}/documents/{doc['id']}" + suffix
                ).status_code
                == 404
            )
        assert mutate(other, path, method="DELETE").status_code == 404
        assert (
            mutate(
                client,
                f"/workspaces/{space['id']}/members",
                {"email": member["email"], "role": "viewer"},
            ).status_code
            == 201
        )
        assert other.get("/api/v1" + path).status_code == 200
        assert other.get("/api/v1" + path + "/chunks").status_code == 403
        assert other.get("/api/v1" + path + "/download").status_code == 403
        assert upload(other, base).status_code == 403
        assert mutate(other, path, method="DELETE").status_code == 403
        for role in ("support_agent", "admin"):
            assert (
                mutate(
                    client,
                    f"/workspaces/{space['id']}/members/{member['id']}",
                    {"role": role},
                    "PATCH",
                ).status_code
                == 200
            )
            assert other.get("/api/v1" + path + "/chunks").status_code == 200
            assert other.get("/api/v1" + path + "/download").status_code == 200
            assert upload(other, base, f"{role}.txt", role.encode()).status_code == 201
            if role == "support_agent":
                assert mutate(other, path, method="DELETE").status_code == 403
        assert mutate(other, path, method="DELETE").status_code == 204


def test_delete_failure_tombstone_recovery_and_upload_failure(env, monkeypatch):
    engine, app, client, _, space, base, settings = env
    storage = app.app.state.document_storage
    doc = upload(client, base).json()
    real_delete = storage.delete

    def fail(*args):
        raise OSError("Sensitive path must not escape")

    monkeypatch.setattr(storage, "delete", fail)
    assert mutate(client, base + "/" + doc["id"], method="DELETE").status_code == 503
    saved = client.get("/api/v1" + base + "/" + doc["id"]).json()
    assert saved["processing_status"] == "deleting" and saved["total_chunks"] == 0
    assert client.get("/api/v1" + base + "/" + doc["id"] + "/download").status_code == 409
    with Session(engine) as db:
        db.get(Document, uuid.UUID(doc["id"])).updated_at = datetime.now(UTC) - timedelta(minutes=5)
        db.commit()
    monkeypatch.setattr(storage, "delete", real_delete)
    with Session(engine) as db:
        assert recover(db, storage, settings) == 1
        assert db.scalar(select(Document)) is None and db.scalar(select(DocumentChunk)) is None
    monkeypatch.setattr(storage, "save", fail)
    failed = upload(client, base, "failed.txt", b"new text").json()
    assert failed["processing_status"] == "failed" and "Sensitive" not in str(failed)
    assert mutate(client, base + "/" + failed["id"], method="DELETE").status_code == 204


def test_recovery_skips_live_locks_and_chunk_tenant_fk(env):
    engine, app, client, user, space, base, settings = env
    doc = upload(client, base).json()
    other = workspace(client)
    with Session(engine) as db:
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(
                DocumentChunk(
                    document_id=doc["id"],
                    workspace_id=other["id"],
                    chunk_index=10,
                    content="Mismatch",
                    character_count=8,
                    source_metadata={},
                )
            )
            db.flush()
        saved = db.get(Document, uuid.UUID(doc["id"]))
        saved.processing_status = DocumentStatus.PROCESSING
        saved.updated_at = datetime.now(UTC) - timedelta(minutes=5)
        db.commit()
    with Session(engine) as locked:
        locked.scalar(select(Document).where(Document.id == uuid.UUID(doc["id"])).with_for_update())
        with Session(engine) as db:
            assert recover(db, app.app.state.document_storage, settings) == 0
    with Session(engine) as db:
        assert recover(db, app.app.state.document_storage, settings) == 1
    assert client.get("/api/v1" + base + "/" + doc["id"]).json()["processing_status"] == "failed"
    assert (
        mutate(client, base + "/" + doc["id"] + "/retry").json()["processing_status"] == "completed"
    )


def test_document_migration_preserves_ticket(database_factory):
    engine = database_factory()
    migrate(engine, target="0004")
    wid, tid = uuid.uuid4(), uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO workspaces(id,name,slug) VALUES (:id,'Existing','existing')"),
            {"id": wid},
        )
        conn.execute(
            text("INSERT INTO tickets(id,workspace_id,title) VALUES (:id,:wid,'Preserved')"),
            {"id": tid, "wid": wid},
        )
    migrate(engine)
    migrate(engine, "downgrade", "0004")
    migrate(engine)
    with engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT title FROM tickets WHERE id=:id"), {"id": tid}) == "Preserved"
        )


def test_partial_file_is_tracked_and_delete_finishes_after_database_failure(env, monkeypatch):
    engine, app, client, _, space, base, _ = env
    storage = app.app.state.document_storage
    real_save = storage.save

    def partial(workspace_id, key, content):
        folder = storage.root / workspace_id.hex
        with storage.directory(workspace_id, key):
            (folder / (key + ".part")).write_bytes(content[:3])
        raise OSError("synthetic interrupted write")

    monkeypatch.setattr(storage, "save", partial)
    failed = upload(client, base).json()
    assert failed["processing_status"] == "failed"
    assert len(list(storage.root.rglob("*.part"))) == 1
    assert mutate(client, base + "/" + failed["id"], method="DELETE").status_code == 204
    assert not list(storage.root.rglob("*.part"))
    monkeypatch.setattr(storage, "save", real_save)
    doc = upload(client, base).json()
    from resolveflow.documents.service import finish_delete

    with Session(engine) as db:
        saved = db.get(Document, uuid.UUID(doc["id"]))
        saved.processing_status = DocumentStatus.DELETING
        key = saved.storage_key
        db.commit()
    with Session(engine) as db:

        def failed_commit():
            raise RuntimeError("synthetic DB failure")

        monkeypatch.setattr(db, "commit", failed_commit)
        with pytest.raises(RuntimeError, match="synthetic DB failure"):
            finish_delete(db, uuid.UUID(space["id"]), uuid.UUID(doc["id"]), storage)
        db.rollback()
    assert not storage.exists(uuid.UUID(space["id"]), key)
    assert client.get("/api/v1" + base + "/" + doc["id"]).json()["processing_status"] == "deleting"
    assert mutate(client, base + "/" + doc["id"], method="DELETE").status_code == 204


def test_download_detects_file_corruption(env, monkeypatch):
    _, app, client, _, _, base, _ = env
    doc = upload(client, base).json()
    monkeypatch.setattr(app.app.state.document_storage, "read", lambda *args: b"tampered")
    assert client.get("/api/v1" + base + "/" + doc["id"] + "/download").status_code == 503
