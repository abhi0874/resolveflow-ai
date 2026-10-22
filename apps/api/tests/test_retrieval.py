import uuid
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session
from test_auth_workspaces import mutate, register, workspace
from test_database import migrate
from test_documents import env as document_env
from test_documents import upload
from test_embeddings import real_embeddings as embedding_fixture

from resolveflow.db.models import MembershipRole, WorkspaceMembership
from resolveflow.documents.models import Document, DocumentChunk
from resolveflow.main import create_asgi_app
from resolveflow.retrieval.contracts import EmbeddingInfo, EmbeddingUnavailable
from resolveflow.retrieval.models import ChunkEmbedding

env = document_env
real_embeddings = embedding_fixture
pytestmark = pytest.mark.integration


class FixtureEmbeddings:
    """Only test wiring/failures use this fixture; never application/evaluation inference."""

    def __init__(self):
        self.info = EmbeddingInfo()
        self.calls = 0
        self.fail = False

    def get_dimensions(self):
        return 384

    def get_model_info(self):
        return self.info

    def embed_documents(self, texts):
        self.calls += 1
        if self.fail:
            raise EmbeddingUnavailable()
        return [[1.0] + [0.0] * 383 for _ in texts]

    def embed_query(self, query):
        return self.embed_documents([query])[0]

    def health_check(self):
        return True


def setup(env, provider=None):
    engine, app, client, _, space, base, settings = env
    provider = provider or FixtureEmbeddings()
    app.app.state.embeddings = provider
    doc = upload(
        client, base, "policy.txt", b"Refund requests are accepted within thirty days of purchase."
    ).json()
    path = base + "/" + doc["id"]
    search = f"/workspaces/{space['id']}/knowledge-base/search"
    return engine, app, client, space, doc, path, search, provider


def test_index_idempotence_replacement_missing_changed_and_interrupted(env):
    engine, app, client, space, doc, path, search, model = setup(env)
    assert mutate(client, search, {"query": "refund"}).json()["results"] == []
    result = mutate(client, path + "/index").json()
    assert result["indexing_status"] == "indexed"
    calls = model.calls
    assert mutate(client, path + "/index").json()["indexing_status"] == "indexed"
    assert model.calls == calls
    assert mutate(client, path + "/index", {"force": True}).json()["indexing_status"] == "indexed"
    assert model.calls == calls + 1
    with Session(engine) as db:
        embedding = db.scalar(select(ChunkEmbedding))
        saved = list(embedding.embedding)
        chunk_id = embedding.chunk_id
    model.fail = True
    assert mutate(client, path + "/index", {"force": True}).json()["indexing_status"] == "failed"
    with Session(engine) as db:
        assert list(db.get(ChunkEmbedding, chunk_id).embedding) == saved
    model.fail = False
    model.info = model.info.model_copy(update={"space": "test-new-space"})
    assert mutate(client, search, {"query": "refund"}).json()["results"] == []
    assert mutate(client, path + "/index").json()["indexing_status"] == "indexed"
    with Session(engine) as db:
        chunk = db.get(DocumentChunk, chunk_id)
        chunk.content = "Updated text for policy."
        chunk.character_count = len(chunk.content)
        db.commit()
    assert mutate(client, search, {"query": "refund"}).json()["results"] == []
    assert mutate(client, path + "/index").json()["indexing_status"] == "indexed"
    with Session(engine) as db:
        db.execute(delete(ChunkEmbedding))
        db.commit()
    assert mutate(client, path + "/index").json()["indexing_status"] == "indexed"
    with Session(engine) as db:
        stored = db.get(Document, uuid.UUID(doc["id"]))
        stored.indexing_status = "indexing"
        stored.indexing_token = uuid.uuid4()
        db.commit()
    assert mutate(client, path + "/index").status_code == 409
    with Session(engine) as db:
        db.execute(
            text("UPDATE documents SET updated_at=:old WHERE id=:id"),
            {"old": datetime.now(UTC) - timedelta(minutes=5), "id": doc["id"]},
        )
        db.commit()
    assert mutate(client, path + "/index").json()["indexing_status"] == "indexed"


def test_real_embeddings_pgvector_ranking_metadata_delete(env, real_embeddings):
    engine, app, client, space, doc, path, search, _ = setup(env, real_embeddings)
    other = upload(
        client,
        env[5],
        "access.txt",
        b"To recover a lost password, request an email reset link from the sign-in page.",
    ).json()
    for d in [doc, other]:
        result = mutate(client, env[5] + "/" + d["id"] + "/index")
        assert result.status_code == 200, result.text
        assert result.json()["indexing_status"] == "indexed"
    result = mutate(
        client, search, {"query": "I forgot my password, how do I get back in?", "top_k": 1}
    ).json()
    assert len(result["results"]) == 1
    hit = result["results"][0]
    assert hit["document_id"] == other["id"] and hit["document_name"] == "access.txt"
    assert hit["page_number"] is None and hit["chunk_index"] == 0
    with Session(engine) as db:
        vector = db.get(ChunkEmbedding, uuid.UUID(hit["chunk_id"])).embedding
        expected = float(np.dot(vector, real_embeddings.embed_query(result["query"])))
        assert hit["similarity_score"] == pytest.approx(expected, abs=1e-5)
        assert (
            db.scalar(
                select(DocumentChunk).where(DocumentChunk.id == uuid.UUID(hit["chunk_id"]))
            ).content
            == hit["content"]
        )
    assert (
        mutate(
            client,
            search,
            {"query": "Where do interstellar penguins buy spaceships?", "min_similarity": 0.95},
        ).json()["results"]
        == []
    )
    assert mutate(client, env[5] + "/" + other["id"], method="DELETE").status_code == 204
    assert all(
        h["document_id"] != other["id"]
        for h in mutate(client, search, {"query": "password", "min_similarity": 0.0}).json()[
            "results"
        ]
    )
    with Session(engine) as db:
        assert db.get(ChunkEmbedding, uuid.UUID(hit["chunk_id"])) is None


def test_security_tenants_roles_csrf_and_invalid_input(env):
    engine, app, client, space, doc, path, search, model = setup(env)
    assert mutate(client, path + "/index").status_code == 200
    second_app = create_asgi_app(env[-1])
    with TestClient(second_app) as stranger:
        assert stranger.post("/api/v1" + search, json={"query": "refund"}).status_code in (401, 403)
        user2 = register(stranger, "other@example.com")
        space2 = workspace(stranger, "other")
        second_app.app.state.embeddings = model
        base2 = f"/workspaces/{space2['id']}/documents"
        doc2 = upload(
            stranger,
            base2,
            "secret.txt",
            b"Refund requests are accepted within thirty days of purchase.",
        ).json()
        assert mutate(stranger, base2 + "/" + doc2["id"] + "/index").status_code == 200
        results = mutate(client, search, {"query": "refund", "min_similarity": 0.0}).json()[
            "results"
        ]
        assert [r["document_id"] for r in results] == [doc["id"]]
        assert "secret.txt" not in str(results)
        assert mutate(stranger, search, {"query": "refund"}).status_code == 404
        assert mutate(client, env[5] + "/" + doc2["id"] + "/index").status_code == 404
        with Session(engine) as db:
            db.add(
                WorkspaceMembership(
                    workspace_id=uuid.UUID(space["id"]),
                    user_id=uuid.UUID(user2["id"]),
                    role=MembershipRole.VIEWER,
                )
            )
            db.commit()
        assert mutate(stranger, search, {"query": "refund"}).status_code == 403
        assert mutate(stranger, path + "/index").status_code == 403
        with Session(engine) as db:
            member = db.scalar(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.user_id == uuid.UUID(user2["id"]),
                    WorkspaceMembership.workspace_id == uuid.UUID(space["id"]),
                )
            )
            member.role = MembershipRole.SUPPORT_AGENT
            db.commit()
        assert mutate(stranger, path + "/index").status_code == 200
        assert mutate(stranger, search, {"query": "refund"}).status_code == 200
    assert client.post("/api/v1" + search, json={"query": "refund"}).status_code == 403
    for body in [
        {"query": ""},
        {"query": "x" * 1001},
        {"query": "ok", "top_k": 21},
        {"query": "ok", "extra": True},
    ]:
        assert mutate(client, search, body).status_code == 422
    assert mutate(client, env[5] + "/" + str(uuid.uuid4()) + "/index").status_code == 404
    bad = upload(client, env[5], "empty.txt", b"   ").json()
    assert mutate(client, env[5] + "/" + bad["id"] + "/index").status_code == 409
    app.app.state.embeddings = __import__(
        "resolveflow.retrieval.provider", fromlist=["LocalSentenceTransformerProvider"]
    ).LocalSentenceTransformerProvider(env[-1].embedding_model_root)
    response = mutate(client, search, {"query": "refund"})
    assert (
        response.status_code == 503 and response.json()["error"]["code"] == "embedding_unavailable"
    )


def test_vector_constraints_and_upgrade_preserves_chunks(env):
    engine, app, client, space, doc, path, search, model = setup(env)
    assert mutate(client, path + "/index").status_code == 200
    with Session(engine) as db:
        chunk = db.scalar(select(DocumentChunk))
        chunk_id = chunk.id
        for vector in [[0.0] * 384, [1.0] * 383, [float("inf")] * 384]:
            with pytest.raises((IntegrityError, StatementError)):
                with db.begin_nested():
                    db.get(ChunkEmbedding, chunk_id).embedding = vector
                    db.flush()
    migrate(engine, "downgrade", "0005")
    migrate(engine)
    with Session(engine) as db:
        assert db.get(DocumentChunk, chunk_id).content.startswith("Refund")
        assert db.get(Document, uuid.UUID(doc["id"])).indexing_status == "not_indexed"
        assert db.scalar(select(ChunkEmbedding)) is None


def test_partial_reindex_rollback_and_delete_tombstone(env, monkeypatch):
    engine, app, client, space, doc, path, search, model = setup(env)
    large = upload(client, env[5], "long.txt", b"Account recovery. " * 200).json()
    path = env[5] + "/" + large["id"]
    env[-1].embedding_batch_size = 1
    assert mutate(client, path + "/index").json()["indexing_status"] == "indexed"
    with Session(engine) as db:
        before = {e.chunk_id: list(e.embedding) for e in db.scalars(select(ChunkEmbedding))}
    calls = 0

    def fail_later(texts):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise EmbeddingUnavailable()
        return [[0.0, 1.0] + [0.0] * 382 for _ in texts]

    monkeypatch.setattr(model, "embed_documents", fail_later)
    assert mutate(client, path + "/index", {"force": True}).json()["indexing_status"] == "failed"
    assert calls == 2
    with Session(engine) as db:
        assert {e.chunk_id: list(e.embedding) for e in db.scalars(select(ChunkEmbedding))} == before
    storage = app.app.state.document_storage
    original = storage.delete

    def fail_delete(*args):
        raise OSError("private path must not leak")

    monkeypatch.setattr(storage, "delete", fail_delete)
    assert mutate(client, path, method="DELETE").status_code == 503
    with Session(engine) as db:
        assert (
            db.scalar(
                select(ChunkEmbedding).where(ChunkEmbedding.document_id == uuid.UUID(large["id"]))
            )
            is None
        )
        assert db.get(Document, uuid.UUID(large["id"])).processing_status.value == "deleting"
    monkeypatch.setattr(storage, "delete", original)
    assert mutate(client, path, method="DELETE").status_code == 204


def test_cross_tenant_embedding_foreign_key_and_duplicates(env):
    engine, app, client, space, doc, path, search, model = setup(env)
    assert mutate(client, path + "/index").status_code == 200
    with Session(engine) as db:
        saved = db.scalar(select(ChunkEmbedding))
        with pytest.raises(IntegrityError):
            with db.begin_nested():
                saved.workspace_id = uuid.uuid4()
                db.flush()
    duplicate = upload(client, env[5], "repeated.txt", b"Repeated phrase. " * 200).json()
    assert mutate(client, env[5] + "/" + duplicate["id"] + "/index").status_code == 200
    hits = mutate(client, search, {"query": "anything", "top_k": 20, "min_similarity": 0.0}).json()[
        "results"
    ]
    assert len({h["content"] for h in hits}) == len(hits)
    again = mutate(
        client, search, {"query": "anything", "top_k": 20, "min_similarity": 0.0}
    ).json()["results"]
    assert [h["chunk_id"] for h in hits] == [h["chunk_id"] for h in again]
