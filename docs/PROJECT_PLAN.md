# Project plan

Status date: 2026-10-22 (Asia/Kolkata).

Steps 1–14 and Step 15A are completed locally; public demo deployment remains a separate approval gate. Step 9's separately approved single synthetic
Gemini test passed; Step 10 uses offline deterministic generation only. Later phases
remain proposals, not authorization. Each step ends with evidence and updated status.

## Phases and dependencies

| Phase | Scope | Depends on | Exit evidence |
| --- | --- | --- | --- |
| 1 — Initialization | Inspect workspace/tools; preserve or initialize Git; add ignore rules, instructions, vision, architecture, plan, and status | User's Step 1 request | Six requested files present; environment and Git inspected; no application implementation |
| 2 — Compatibility and foundation | Pin verified foundation runtimes/dependencies; establish apps/web and apps/api, homepage, health/info routes, configuration and checks; worker choice deferred | 1 + explicit next-step instruction | Reproducible setup; frontend/backend smoke checks; no paid-service dependency; initial no-cost hosting feasibility assessment |
| 3 — Database foundation | Native local PostgreSQL/pgvector, SQLAlchemy models, Alembic, sessions/settings, readiness and isolated database tests | 2 + explicit Step 3 request | 44 backend tests pass; migration/rollback/reapply and live outage/recovery verified |
| 4 — Authentication and workspaces | Argon2id, server sessions/cookies/CSRF, auth forms, protected shell, workspace management, central RBAC and membership invariants | 3 + explicit Step 4 request | 57 backend tests; four real browser scenarios; lint/type/build; tenant and concurrent last-owner checks |
| 5 — Ticket management | Ticket creation/editing, assignment/status/priority, inbox/detail UI, notes, activity, search/filter/pagination; no background dispatch | 4 + explicit Step 5 request | Real browser-to-API-to-database ticket journey; role/tenant isolation; stale-edit and migration tests |
| 6 — Knowledge base and documents | Private uploads, real PDF/TXT/Markdown extraction, deterministic chunks, document lifecycle and UI; embeddings/retrieval deferred | 5 + explicit Step 6 request | Tenant/RBAC isolation, resource limits, recovery, migration and real browser journeys |
| 7 — ML classification | Synthetic dataset, TF-IDF/logistic regression, grouped splits, immutable artifacts, scores/abstention, authorized suggestions and manual acceptance | 6 + explicit Step 7 request | 119 backend tests, 13 browser scenarios; reproducible 0.785 test macro F1, threshold coverage and measured local latency |
| 8 — Semantic retrieval | Local Sentence Transformers, atomic indexing/reindexing, tenant-scoped pgvector search and source UI | 6–7 + explicit Step 8 request | 139 backend tests; 15 browser scenarios; real model/pgvector evaluation and deletion/tenant checks |
| 9 — RAG drafts and human review | Official Gemini adapter, provider boundary, bounded retrieval/generation, citations, immutable drafts and internal review | 8 + explicit Step 9 request | 168 backend tests; 18 browser scenarios; 12-case fixture RAG evaluation; one separately approved synthetic live test verified |
| 10 — Durable AI workflow | Genuine LangGraph, PostgreSQL checkpoints, authorized resume and ticket workflow UI | 9 + explicit Step 10 request | Real PostgreSQL execution, process recovery, tenant isolation and browser review tests; see current status |
| 11 — Background execution | PostgreSQL outbox, Valkey/RQ, bounded recovery and cancellation | 10 + explicit authorization | Worker and browser regressions; see PROJECT_STATUS |
| 12 — Analytics and diagnostics | Tenant-scoped aggregates, dashboard, safe correlation logs | 11 + explicit authorization | 269 backend and 26 browser tests at completion |
| 13 — Recruiter demo preparation | Synthetic browser-local data, workflow examples, shared analytics, Vercel-compatible build | 12 + explicit authorization | Backend-independent demo browser tests; deployment not authorized |
| 14 — Demo release preparation | Official Vercel settings, focused security/dependency audit, production-like demo verification and release runbook | 13 + explicit Step 14 authorization | 13 demo checks, build/type/lint checks and readiness report; no deployment |
| 15A — Local Git publication preparation | File/index/history and ignore review, saved dependency audit review, initial local commit | 14 + explicit authorization | Reviewed local commit only; no remote, publication or deployment |
| Future — Full-application hardening and release preparation | Threat review, production abuse controls, backup/restore, load tests and deployment runbooks | 4–9 | Full regression suites; recovery/security evidence; no-cost hosting plan reviewed |
| Future — Approved hosted recruiter demo | Explicitly approved free hosting and bounded synthetic demo | Hardening + deployment approval | Complete journey with MacBook offline; inference quotas and recovery verified |
| Future — Production readiness | Commercial hosting reassessment, operations, capacity, compliance and support | Hosted demo + agreed scope | Measured objectives, restore/incident exercises and explicit launch approval |

## Early decisions and gates

1. **Runtime compatibility:** Step 2 verifies Node 26.5.0 and Python 3.14.6 for
   the foundation and pins dependency lockfiles. Compatibility with the future
   ML dependency set, particularly sentence-transformers and native wheels,
   remains a separate gate before those dependencies are introduced.
2. **Local services:** Choose a free container runtime with Compose-compatible
   tooling, or documented native PostgreSQL/pgvector and Redis installation.
   Docker itself is optional; functioning service equivalents are required.
3. **AI access:** Preserve `gemini-3.6-flash`. Verify account/region access,
   free-tier quotas, and supported structured-output behavior before integration.
   Default tests use fixtures; live requests are a separately gated path.
4. **Hosting feasibility:** Assess no-cost API execution, persistent PostgreSQL
   with pgvector, Redis, storage, embeddings, and workers early in Phase 2.
   Recheck current limits before deployment. Do not defer discovery of a major
   hosting constraint until all application code is complete.
5. **Demo scope:** Prefer the same application core with bounded synthetic data.
   A demo may pre-ingest a knowledge corpus or disable heavy uploads if explicitly
   agreed, but live query embedding/retrieval, real LangGraph execution, and
   limited live generation still need an approved hosted execution path.
6. **No-cost feasibility failure:** Record the exact limitation and ask the user
   to resolve scope or hosting choices at that phase. Do not add billing, silently
   remove requirements, or represent fixture output as live AI inference.

## Quality gates across phases

- Unit tests for domain decisions; integration tests for database, retrieval,
  queue recovery, tenant isolation, and workflow checkpoints.
- Vitest for UI/component behavior; Playwright for ticket creation, draft review,
  approval, tenant boundaries, and the hosted demo's complete journey.
- Provider-independent contract tests and recorded synthetic fixtures; no live
  AI calls in routine CI. Optional live checks need explicit enablement and caps.
- ML and RAG evaluations with versioned datasets, train/evaluation separation,
  groundedness, citation accuracy, latency, and resource measurements. Agree on
  numerical acceptance thresholds when representative datasets exist.
- Typed contracts, lint/type checks, dependency and secret review, reproducible
  builds, migration safety, and restore verification before release.
- Define measurable performance and availability objectives before claiming
  production readiness. Free hosting does not imply an availability guarantee.

## Next step

Step 15A stops after the reviewed initial local Git commit.
GitHub publication, Vercel connection/deployment and live Gemini execution require separate explicit scope
and approval. The Step 13 user-approved fixture-based demo supersedes the earlier
live-backend hosting assumption for the recruiter demonstration only; the full system
is preserved. No hosted service is provisioned by these steps.
