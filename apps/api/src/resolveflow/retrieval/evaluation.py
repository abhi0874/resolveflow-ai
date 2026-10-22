"""Metrics for frozen relevance labels; empty-ground-truth cases are reported separately."""

import numpy as np


def ranking_metrics(rankings: list[list[str]], relevance: list[list[str]], k: int):
    answered = [(r[:k], set(g)) for r, g in zip(rankings, relevance, strict=True) if g]
    recall, reciprocal, hits = [], [], []
    for result, gold in answered:
        found = set(result) & gold
        recall.append(len(found) / len(gold))
        positions = [i + 1 for i, item in enumerate(result) if item in gold]
        reciprocal.append(1 / min(positions) if positions else 0)
        hits.append(int(bool(found)))
    no_answer = [r[:k] for r, g in zip(rankings, relevance, strict=True) if not g]
    return {
        "k": k,
        "answerable_queries": len(answered),
        "recall_at_k": float(np.mean(recall)),
        "mrr_at_k": float(np.mean(reciprocal)),
        "hit_rate_at_k": float(np.mean(hits)),
        "no_answer_queries": len(no_answer),
        "no_answer_with_results": sum(bool(r) for r in no_answer),
    }


def latency(values):
    return {
        "count": len(values),
        "median_ms": float(np.median(values)),
        "p95_ms": float(np.percentile(values, 95)),
        "max_ms": float(max(values)),
    }
