"""Deterministic contract checks plus an explicit real, offline local-model test."""

import os
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from resolveflow.core.config import API_ROOT
from resolveflow.retrieval.contracts import (
    EmbeddingUnavailable,
    SearchRequest,
    prepare,
    validate_vectors,
)
from resolveflow.retrieval.provider import LocalSentenceTransformerProvider


@pytest.fixture(scope="session")
def real_embeddings():
    root = Path(
        os.environ.get(
            "TEST_EMBEDDING_MODEL_ROOT", str(API_ROOT.parents[1] / ".local/embeddings/minilm-v1")
        )
    )
    if not root.exists():
        pytest.skip("Run scripts/download_embeddings.py for real local embedding tests")
    model = LocalSentenceTransformerProvider(root)
    assert model.health_check(), "Installed real model could not load"
    return model


@pytest.mark.parametrize("value", ["", "  ", "a" * 4001, "a\x00b", 123, None])
def test_invalid_text(value):
    with pytest.raises(ValueError):
        prepare(value)


@pytest.mark.parametrize(
    "values",
    [[[0.0] * 384], [[float("nan")] * 384], [[float("inf")] * 384], [[1.0] * 383], [[1.0] * 384]],
)
def test_invalid_vectors(values):
    with pytest.raises(ValueError):
        validate_vectors(values, 1)


def test_unavailable_and_query_validation(tmp_path):
    model = LocalSentenceTransformerProvider(tmp_path / "missing")
    assert not model.health_check()
    with pytest.raises(EmbeddingUnavailable):
        model.embed_query("What is the policy?")
    for body in [
        {"query": " "},
        {"query": "a" * 1001},
        {"query": "ok", "top_k": 21},
        {"query": "ok", "top_k": True},
        {"query": "ok", "min_similarity": float("nan")},
        {"query": "ok", "workspace_id": "bad"},
    ]:
        with pytest.raises(ValidationError):
            SearchRequest(**body)


def test_real_model_batch_dimensions_and_similarity(real_embeddings):
    model = real_embeddings
    texts = [
        "Reset your forgotten password using the recovery email.",
        "I forgot my password. How can I regain access?",
        "The office lunch menu includes soup.",
    ]
    vectors = np.array(model.embed_documents(texts))
    assert vectors.shape == (3, 384)
    assert np.isfinite(vectors).all() and np.allclose(np.linalg.norm(vectors, axis=1), 1)
    assert vectors[0] @ vectors[1] > vectors[0] @ vectors[2]
    assert np.allclose(vectors[1], model.embed_query(texts[1]), atol=1e-6)
    assert np.allclose(vectors, model.embed_documents(texts), atol=1e-6)
    assert len(model.embed_documents(["Account recovery help. " * 150])[0]) == 384
    for batch in [[], ["ok"] * 33, [""]]:
        with pytest.raises(ValueError):
            model.embed_documents(batch)
    assert model._slots.acquire(False)
    try:
        with pytest.raises(EmbeddingUnavailable):
            model.embed_query("Help")
    finally:
        model._slots.release()
