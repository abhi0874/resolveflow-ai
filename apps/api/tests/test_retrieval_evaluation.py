"""Reproducible real model → extraction → indexing → pgvector evaluation in an owned test DB."""

import hashlib
import json
import os
import platform
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import psutil
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy import text
from test_auth_workspaces import mutate, workspace
from test_documents import env as document_env
from test_documents import upload
from test_embeddings import real_embeddings as embedding_fixture

from resolveflow.core.config import API_ROOT
from resolveflow.retrieval.evaluation import latency, ranking_metrics

env = document_env
real_embeddings = embedding_fixture
pytestmark = pytest.mark.integration


def test_evaluate_retrieval(env, real_embeddings):
    engine, app, client, _, space, base, _ = env
    app.app.state.embeddings = real_embeddings
    corpus_path = API_ROOT.parents[1] / "data/synthetic/retrieval-v1/corpus.json"
    corpus = json.loads(corpus_path.read_text())
    identifiers = {}
    indexing_ms = []
    chunks = 0
    rss_before = psutil.Process().memory_info().rss
    embedding_start = time.perf_counter()
    real_embeddings.embed_documents([d["text"] for d in corpus["documents"]])
    embedding_ms = (time.perf_counter() - embedding_start) * 1000
    for source in corpus["documents"]:
        response = upload(client, base, source["title"], source["text"].encode())
        assert response.status_code == 201, response.text
        doc = response.json()
        identifiers[doc["id"]] = source["id"]
        chunks += doc["total_chunks"]
        start = time.perf_counter()
        response = mutate(client, base + "/" + doc["id"] + "/index")
        indexing_ms.append((time.perf_counter() - start) * 1000)
        assert response.status_code == 200 and response.json()["indexing_status"] == "indexed"
    rankings, times, predictions = [], [], []
    route = f"/workspaces/{space['id']}/knowledge-base/search"
    for query in corpus["queries"]:
        start = time.perf_counter()
        response = mutate(
            client, route, {"query": query["query"], "top_k": 5, "min_similarity": 0.30}
        )
        times.append((time.perf_counter() - start) * 1000)
        assert response.status_code == 200, response.text
        hits = response.json()["results"]
        rank = [identifiers[h["document_id"]] for h in hits]
        rankings.append(rank)
        predictions.append(
            {
                "id": query["id"],
                "ranked_sources": rank,
                "scores": [h["similarity_score"] for h in hits],
            }
        )
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform([d["text"] for d in corpus["documents"]])
    baseline = []
    for q in corpus["queries"]:
        scores = (matrix @ vectorizer.transform([q["query"]]).T).toarray().ravel()
        order = np.argsort(-scores, kind="stable")
        baseline.append([corpus["documents"][i]["id"] for i in order if scores[i] > 0][:5])
    gold = [q["relevant"] for q in corpus["queries"]]
    with engine.connect() as conn:
        vector_version = conn.scalar(
            text("SELECT extversion FROM pg_extension WHERE extname='vector'")
        )
    report = {
        "dataset_version": corpus["version"],
        "dataset_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "model": real_embeddings.get_model_info().model_dump(),
        "documents": len(corpus["documents"]),
        "chunks": chunks,
        "queries": len(gold),
        "configuration": {
            "top_k": 5,
            "minimum_similarity": 0.30,
            "index_strategy": "exact cosine",
            "threads": 2,
            "batch_size": 16,
            "threshold_selected_before_evaluation": True,
        },
        "semantic": [ranking_metrics(rankings, gold, k) for k in [1, 3, 5]],
        "keyword_tfidf": [ranking_metrics(baseline, gold, k) for k in [1, 3, 5]],
        "search_in_process_http_csrf_auth_db": latency(times),
        "index_in_process_http_csrf_auth_db": latency(indexing_ms),
        "embedding_corpus_batch_ms": embedding_ms,
        "rss_before_evaluation_bytes": rss_before,
        "rss_after_evaluation_bytes": psutil.Process().memory_info().rss,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pgvector": vector_version,
        "dependencies": {
            n: version(n) for n in ["sentence-transformers", "torch", "transformers", "pgvector"]
        },
        "predictions": predictions,
    }
    # A longer document lives in a separate workspace, never in the scored corpus.
    bench_space = workspace(client)
    bench_base = f"/workspaces/{bench_space['id']}/documents"
    long_text = "\n\n".join(
        f"Section {i}. " + source["text"] for i in range(6) for source in corpus["documents"]
    )
    long_doc = upload(client, bench_base, "representative-handbook.txt", long_text.encode()).json()
    start = time.perf_counter()
    indexed = mutate(client, bench_base + "/" + long_doc["id"] + "/index")
    elapsed = (time.perf_counter() - start) * 1000
    assert indexed.status_code == 200 and indexed.json()["indexing_status"] == "indexed"
    report["representative_document"] = {
        "characters": len(long_text),
        "chunks": long_doc["total_chunks"],
        "indexing_ms": elapsed,
        "rss_after_bytes": psutil.Process().memory_info().rss,
    }
    # This is a functionality gate, not a tuned accuracy target.
    assert report["semantic"][2]["hit_rate_at_k"] > 0
    destination = os.environ.get("RETRIEVAL_EVALUATION_OUTPUT")
    if destination:
        Path(destination).write_text(json.dumps(report, indent=2) + "\n")
