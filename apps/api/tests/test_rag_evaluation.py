"""Actual embeddings/pgvector; fixture generation is not a Gemini quality benchmark."""

import hashlib
import json
import os
import time
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_auth_workspaces import mutate
from test_documents import env as document_env
from test_documents import upload
from test_embeddings import real_embeddings as embedding_fixture

from resolveflow.ai.providers import DeterministicMockProvider
from resolveflow.core.config import API_ROOT
from resolveflow.rag.models import ResponseDraft
from resolveflow.rag.prompt import PROMPT_VERSION
from resolveflow.retrieval.evaluation import latency

env = document_env
real_embeddings = embedding_fixture
pytestmark = pytest.mark.integration


def test_evaluate_rag(env, real_embeddings):
    engine, app, client, _, space, base, settings = env
    app.app.state.embeddings = real_embeddings
    app.app.state.ai_provider = DeterministicMockProvider()
    settings.ai_daily_user, settings.ai_daily_workspace = 25, 30
    scenario_path = API_ROOT.parents[1] / "data/synthetic/rag-v1/scenarios.json"
    data = json.loads(scenario_path.read_text())
    corpus_path = (scenario_path.parent / data["corpus"]).resolve()
    corpus = json.loads(corpus_path.read_text())
    names, source_text = {}, {}
    for source in corpus["documents"]:
        response = upload(client, base, source["title"], source["text"].encode())
        assert response.status_code == 201
        doc = response.json()
        names[doc["id"]] = source["id"]
        source_text[doc["id"]] = source["text"]
        assert (
            mutate(client, base + "/" + doc["id"] + "/index").json()["indexing_status"] == "indexed"
        )
    predictions, times = [], []
    for case in data["scenarios"]:
        ticket = mutate(
            client,
            f"/workspaces/{space['id']}/tickets",
            {"title": case["title"], "description": case["description"]},
        ).json()
        start = time.perf_counter()
        result = mutate(
            client,
            f"/workspaces/{space['id']}/tickets/{ticket['id']}/generate-response",
            {"expected_ticket_version": 1, "request_id": str(uuid.uuid4())},
        )
        times.append((time.perf_counter() - start) * 1000)
        assert result.status_code == 200, result.text
        draft = result.json()
        with Session(engine) as db:
            manifest = db.scalar(
                select(ResponseDraft).where(ResponseDraft.id == uuid.UUID(draft["id"]))
            ).evidence_manifest
        citations = draft["citations"]
        retrieved = [names[e["document_id"]] for e in manifest]
        valid = all(c["supporting_quote"] in source_text[c["document_id"]] for c in citations)
        predictions.append(
            {
                "id": case["id"],
                "retrieved_sources": retrieved,
                "expected_sources": case["sources"],
                "cited_sources": [names[c["document_id"]] for c in citations],
                "retrieval_hit": bool(set(retrieved) & set(case["sources"]))
                if case["sources"]
                else None,
                "abstained": draft["insufficient_evidence"],
                "expected_abstention": case["abstain"],
                "citation_count": len(citations),
                "citations_valid": valid,
                "extractive_support_proxy": all(
                    c["supporting_quote"] in draft["response_text"] for c in citations
                )
                if citations
                else None,
                "required_terms_complete": all(
                    t in draft["response_text"].lower() for t in case["terms"]
                )
                if case["terms"]
                else None,
                "response_text": draft["response_text"],
                "generation_origin": draft["generation_origin"],
                "provider_duration_ms": draft["duration_ms"],
            }
        )
        assert valid and draft["fixture"] and draft["requires_human_review"]
    answerable = [p for p in predictions if p["expected_sources"]]
    abstentions = [p for p in predictions if p["expected_abstention"]]
    cited = [p for p in predictions if p["citation_count"]]
    report = {
        "version": data["version"],
        "mode": "deterministic_fixture_not_gemini_quality",
        "prompt_version": PROMPT_VERSION,
        "generation_provider": "fixture/deterministic-v1",
        "gemini_live_test": "pending_credentials_and_verified_free_tier",
        "dataset_sha256": hashlib.sha256(scenario_path.read_bytes()).hexdigest(),
        "corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "embedding_model": real_embeddings.get_model_info().model_dump(),
        "configuration": {
            "top_k": settings.ai_top_k,
            "min_similarity": settings.search_min_similarity,
            "context_chars": settings.ai_context_chars,
            "max_output_tokens": settings.ai_max_output_tokens,
        },
        "cases": len(predictions),
        "answerable": len(answerable),
        "retrieval_hit_rate": sum(p["retrieval_hit"] for p in answerable) / len(answerable),
        "citation_validity": sum(p["citations_valid"] for p in cited) / len(cited),
        "extractive_support_proxy": sum(p["extractive_support_proxy"] for p in cited) / len(cited),
        "required_terms_completeness": sum(p["required_terms_complete"] for p in answerable)
        / len(answerable),
        "expected_abstention_rate": sum(p["abstained"] for p in abstentions) / len(abstentions),
        "false_abstentions": sum(p["abstained"] for p in answerable),
        "in_process_http_csrf_retrieval_generation_persistence": latency(times),
        "predictions": predictions,
    }
    destination = os.environ.get("RAG_EVALUATION_OUTPUT")
    if destination:
        Path(destination).write_text(json.dumps(report, indent=2) + "\n")
