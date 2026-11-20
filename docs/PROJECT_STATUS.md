# Project status

Updated **2026-11-20 (Asia/Kolkata)** for the public portfolio evidence package.

## Current portfolio status

Public GitHub main and the Vercel production showcase resolve to commit
`d2af3ec4ab99cba381ef30e91c2274284733f8ab`. The GitHub repository is public, the
showcase returned HTTPS 200, and the retired rosy address returned 404. The
showcase replays synthetic examples with live generation disabled. Full
application and research evidence describes local execution. [Repository](https://github.com/abhi0874/resolveflow-ai) · [Showcase](https://resolveflow-ai-showcase.vercel.app/)

- The configured local classifier is `baseline-v1`. It scored **44/56 (78.57%) / 0.7846 macro-F1** on the original held-out split. On a separate paired 210-ticket synthetic challenge, frozen V1 scored **142/210 (67.62%) / 0.6585** and inactive V2 scored **183/210 (87.14%) / 0.8701**. This was a comparison of frozen research artifacts. V2 remains inactive. [Original evaluation](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/docs/evaluation/classifier-v1-evaluation.json) · [Paired results](evaluation/PUBLIC_EVIDENCE.md#classifier-evaluation)
- Recomputed MiniLM vs TF-IDF results on the same corpus and labels: **Hit@1 19/21 vs 11/21**, **Hit@5 20/21 vs 19/21**, **Recall@5 0.9286 vs 0.8492**, and **MRR@5 0.9286 vs 0.6762**. The 14-document corpus has 24 queries, including three unsupported queries reported separately. The MiniLM floor was 0.30 and the TF-IDF baseline kept positive scores. [Retrieval results](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/docs/evaluation/retrieval-v1.json)
- Deterministic RAG recorded **7/7 citation-valid answerable cases**, **5/5 expected abstentions** and **3/7 required-term completeness**. The separate authorized Gemini smoke verified the adapter for one synthetic request. Saved local live mode is disabled. [Fixture results](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/docs/evaluation/rag-v1.json) · [Live smoke record](evaluation/PUBLIC_EVIDENCE.md#rag-fixture-evaluation)

## Verification scope

The local full application implements FastAPI, PostgreSQL/pgvector retrieval and
a seven-stage LangGraph with durable human review. Historical tests exercised
checkpoint resume after a broker restart and recovery after worker interruption.
The hosted showcase is a separate Next.js build that exercises the same user
journey with synthetic data and precomputed results. Neither evaluation scope
establishes independent customer accuracy or commercial readiness.

The public evidence summary records benchmark denominators and provenance. The
full development history and detailed research records are retained separately.
The historical temporary Step 30A rerun reports were unavailable at their
recorded paths, and their absence does not change the original benchmark records.
[Public evidence summary](evaluation/PUBLIC_EVIDENCE.md) · [Project profile](AI_PORTFOLIO_PROFILE.md)
