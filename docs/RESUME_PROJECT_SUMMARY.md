# ResolveFlow AI — resume and portfolio copy

Personal engineering project. Suitable for Junior AI/ML Engineer, Junior AI Automation
Engineer, Software Engineer, Backend Engineer and AI Application Engineer applications.
Choose relevant bullets; do not present this as professional employment or commercial
customer delivery. Source remains private; the live link is a synthetic demonstration.

## Project description

Built a multi-tenant customer-support application combining trained ticket
classification, semantic document retrieval, Gemini-powered RAG and checkpointed
LangGraph workflows with exact-draft human approval.

## Technical stack

Python, FastAPI, SQLAlchemy, PostgreSQL, pgvector, scikit-learn, Sentence Transformers,
Google Gen AI through `AIProvider`, LangGraph, Redis-compatible Valkey, RQ,
Next.js, TypeScript, React, Tailwind CSS, Pytest, Playwright, Alembic and restic.
Gemini model selection is configurable; the implemented default is `gemini-3.6-flash`.
Routine tests use deterministic generation; public live inference is disabled.

## ATS-friendly resume bullet options

- Built a multi-tenant support platform with FastAPI, Next.js and PostgreSQL,
  enforcing session authentication, role-based access and tenant-scoped ticket,
  document and analytics operations.
- Implemented scikit-learn TF-IDF/logistic-regression ticket classification and
  Sentence Transformers embeddings with pgvector retrieval; evaluated the classifier
  on 280 synthetic examples across seven categories using grouped train/validation/test splits.
- Developed structured RAG generation through a provider-neutral Gemini adapter,
  with bounded context, source-quotation validation, insufficient-evidence handling
  and human review of the exact response draft.
- Engineered seven-stage LangGraph workflows with PostgreSQL checkpoints and
  RQ/Valkey background processing, using a durable outbox, stable draft identities
  and authorization rechecks to support tested interruption and duplicate-delivery cases.

For AI/ML roles, lead with the second and third bullets. For backend/software roles,
lead with the first and fourth. For automation roles, emphasize explicit review and
recovery rather than autonomous customer actions. These are implementation claims,
not measured productivity gains.

## LinkedIn project description

ResolveFlow AI is my personal AI/ML and software engineering project for support
triage, evidence retrieval and accountable response drafting. The local application
combines traditional ML classification, Sentence Transformers/pgvector retrieval,
Gemini RAG and LangGraph orchestration with PostgreSQL checkpoints, RQ workers and
multi-tenant authorization. I focused on exact-draft human approval and recovery
across interrupted background work. Evaluation is synthetic. The hosted recruiter
demo uses precomputed examples and browser-local interactions, with live AI disabled;
commercial hosting and operating requirements remain open.

## Portfolio card

**ResolveFlow AI · AI/ML support engineering**

Ticket classification, semantic retrieval and human-reviewed RAG, coordinated through
durable LangGraph workflows. Explore a synthetic interactive demo; the complete
Python/PostgreSQL AI stack is implemented locally.

[Explore the live recruiter demo](https://resolveflow-ai-rosy.vercel.app/demo)

## Evidence behind the wording

| Claim | Source / qualification |
| --- | --- |
| Classification and grouped evaluation | `apps/api/src/resolveflow/ml/`; [ML report](ML_EVALUATION.md). Frozen baseline-v1 test macro F1 0.784580 on 56 synthetic test records; 13/56 suggestions at threshold 0.45. Not real-world accuracy. |
| Embeddings and retrieval | `retrieval/`; [retrieval report](RETRIEVAL_EVALUATION.md). 384-dimensional local embeddings; Recall@5 0.928571 on 21 answerable synthetic queries. Similarity is not correctness. |
| RAG and exact-draft review | `rag/`, `ai/`, `workflows/workers.py`; [case study](AI_ENGINEERING_CASE_STUDY.md). No claim of hallucination elimination or automatic customer delivery. |
| Durable background processing | `jobs/`, `workflows/`; [portfolio evidence](PORTFOLIO_EVIDENCE.md). At-least-once transport with tested idempotency, not universal exactly-once execution. |
| Local verification | Step 20 recorded 317 backend, 29 full browser and 16 demo tests; these were not rerun in Step 23. |

Backend module paths in this table are relative to `apps/api/src/resolveflow/`.
No latency reduction, cost saving, adoption, uptime or customer outcome was measured.
External SMTP, off-host disaster recovery, backup scheduling and commercial operating
controls remain outstanding. No existing resume was edited.
