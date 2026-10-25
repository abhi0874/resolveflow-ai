# Portfolio evidence — Step 20

Verified locally on **2026-10-25 (Asia/Kolkata)**. This document distinguishes fresh
checks, historical experiment reports and unverified operating requirements. It is
not a security certification, commercial release or new deployment.

## Fresh checks executed in Step 20

| Check | Actual result | Reproduction / evidence |
| --- | --- | --- |
| Complete backend suite | **317 passed, 1 existing Google SDK deprecation warning, 152.89 seconds; no skips** | `apps/api`: `RESOLVEFLOW_AI_LIVE_ENABLED=false .venv/bin/python scripts/local_db.py test` |
| Full application browser suite | **29 passed, 2.2 minutes** | `apps/api`: `.venv/bin/python scripts/test_browser.py` after full build; real isolated API/DB/ML/embeddings/workers/Mailpit, fixture generation |
| Recruiter demo browser suite | **16 passed, 14.0 seconds** | `npm --prefix apps/web run test:demo` after demo build |
| Full production build | **Passed** | Node 24.22.1, `NEXT_PUBLIC_APP_MODE=full NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run build -- --webpack` |
| Demo production build | **Passed** | `npm --prefix apps/web run demo:build`; live AI false |
| TypeScript / ESLint | **Passed**, zero ESLint warnings | `npm --prefix apps/web run typecheck` / `run lint` |
| Ruff lint / format | **Passed**, 146 Python files formatted | `apps/api/.venv/bin/ruff check apps/api` / `format --check apps/api` |
| Owned development DB | **0012 = code head; no schema drift; checkpoint access passed** | Ownership checked against this checkout; read-only Alembic metadata comparison and checkpoint schema validation |
| Saved classifier re-evaluation | **Exact saved evaluation reproduced** | `classifier.py evaluate --version baseline-v1`; existing artifact unchanged |
| npm full / production-only audit | **0 / 0 reported findings** | `npm audit --json` / `npm audit --omit=dev --json` with existing lockfile; no dependency changes |

Private raw logs are retained under `.cache/verification/step20/`, excluded from Git.
The committed [verification summary](evaluation/step20-verification.json) retains
safe counts, scope and limitations. Full browser tests were deliberately launched
with an inherited broker URL on unreachable loopback port 1 and reconcile interval
60; the harness's owned broker/queue/interval correctly took precedence after the fix.
No real Gemini requests or external emails occurred.

Backend coverage includes authentication/recovery and invitations, workspaces/tickets,
documents, actual classifier/embedding inference, pgvector retrieval, deterministic
RAG, provider transport mocks, real LangGraph checkpoints, RQ crash/broker recovery,
analytics, migrations and encrypted/legacy restoration. Browser coverage includes
local SMTP verification/reset, session invalidation, permissions, tickets, knowledge,
classification, citations, review, workflow polling and analytics. Demo tests cover
navigation, local state/reset, review safeguards, layouts/keyboard/axe and CSP/API gates.
This is bounded test coverage, not proof of every failure interleaving or client platform.

## Technologies and features actually present

Next.js, React, TypeScript and Tailwind; FastAPI, Pydantic and SQLAlchemy; PostgreSQL,
Alembic and pgvector; scikit-learn and Sentence Transformers; Google Gen AI SDK
behind a typed provider contract; LangGraph with PostgreSQL checkpoints; RQ and
Valkey; restic; Mailpit; Pytest, Playwright, Ruff and ESLint.

The app implements real local inference/retrieval, persistent tickets/documents,
workspace authorization, structured generation validation, exact-draft review,
bounded background recovery, identity recovery and local encrypted backup/restore.
shadcn/ui, Vitest, PostgreSQL RLS, ANN search, OCR and customer message delivery are
not implemented features to list. Priority is rule-based, not another ML model.

## Dated AI/ML evaluation evidence

| Experiment | Supported claim | Limit |
| --- | --- | --- |
| Classifier v1, recorded 2026-10-19; re-evaluated Step 20 | 280 synthetic examples, seven classes, group-preserving 168/56/56 split; held-out accuracy 44/56 = 0.785714, macro F1 0.784580 | Only 28 held-out scenario groups; not real-world accuracy |
| Suggestion threshold 0.45 | 13/56 test examples suggested, 43 abstained | Low coverage; zero observed errors in 13 is not perfect production precision; scores uncalibrated |
| Retrieval v1, recorded 2026-10-20 | 14 synthetic docs, 24 queries; 21 answerable: Recall@5/MRR@5 0.928571, hits 20/21; three no-answer cases abstained | Small English corpus, exact search, no large-scale or real-data generalization claim |
| Deterministic RAG v1, recorded Step 9 | 7/7 source hits and valid cited drafts, 5/5 expected abstentions, **3/7 required-term completeness** | Fixture pipeline evidence, not Gemini quality; valid citations can be incomplete |
| Historical approved Gemini smoke, 2026-10-20 | One request, zero retries, `gemini-3.6-flash`, minimal thinking, 1,024 output cap, 25-second timeout; STOP, JSON/schema/citations passed | No fresh call in Step 20; no broad quality/current availability/billing guarantee |

Sources: [ML evaluation](ML_EVALUATION.md),
[classifier JSON](evaluation/classifier-v1-evaluation.json),
[retrieval JSON](evaluation/retrieval-v1.json), [RAG JSON](evaluation/rag-v1.json),
and the controlled-live-test section in [project status](PROJECT_STATUS.md).
Recorded historical timings are workload-specific observations, not production SLAs
or measured improvements. Step 20 ran retrieval regression tests but did not replace
the frozen retrieval report or claim that a nonzero-hit test proves metric equality.

## Deployment and source access

[Live recruiter demo](https://resolveflow-ai-rosy.vercel.app/demo): standalone Next.js
with synthetic tickets/passages, authored stage/draft examples, keyword search,
browser-local edits and local analytics. It requires no FastAPI, PostgreSQL, worker,
model cache or Gemini key. The full backend remains local.

Recorded Step 17B deployed revision: `759e5f87751cb49c1dd117755dcbdc08b14e31af`.
Step 20 did not make a new deployment. Steps 21–22 subsequently verified private
source preservation on `hardening/step20` and the unchanged production revision on
`main`. Step 23 inspected the hosted overview, billing workflow, cited source, inbox,
analytics and architecture pages without publishing changes. The
[GitHub repository](https://github.com/abhi0874/resolveflow-ai) remains private.
A recruiter needs separately authorized
access to inspect private source and these documents.

## Reliability and security mechanisms

- Accepted work and a PostgreSQL outbox commit before queue publication; delivery
  identities/ownership locks and stable draft reservations suppress tested duplicates.
- Checkpoints survive process interruption; human resume checks a saved exact draft
  decision and current authorization/evidence. At-least-once, not exactly-once, semantics.
- Passwords use Argon2id; opaque server sessions and CSRF/Origin checks protect actions.
  Recovery rotates credential state and revokes sessions while preserving workspace roles.
- Workspace-scoped queries and composite relationships protect tenant resources;
  model output and documents remain untrusted; no arbitrary tools or HTML execution.
- Backup manifests bind database/file evidence, restic encrypts locally, and isolated
  populated restore tests retain checkpoints/approvals and tenant denial behavior.

## Limits that belong in a technical discussion

Automatic backups are intentionally inactive. Independent key custody, off-host
storage and production disaster recovery remain unverified. External account SMTP
is unconfigured/unverified; production invitation delivery is absent. Production
hosting, supervision, least-privilege runtime roles, aggregate quotas, trusted-ingress
fairness, data lifecycle and representative quality/load studies remain open.
Prompt/citation checks are heuristics. Chrome/axe tests are not complete accessibility
certification, and the review is not an external penetration test.

Historical npm findings involved a development-only lint chain; current registry
audits report zero without a lockfile change. This does not establish a particular
upstream patch or absence of all vulnerabilities. No comprehensive fresh Python
vulnerability audit was performed. No adoption, revenue, uptime or real-user benefit
has been measured.

## Claim reuse and Step 23 presentation review

Use [RESUME_PROJECT_SUMMARY.md](RESUME_PROJECT_SUMMARY.md) for resume, LinkedIn and
portfolio-card copy. Its claims map to the source and frozen reports above. Step 23
inspected existing evaluation JSON; it did not retrain models or rerun the Step 20
application suites. The counts above remain Step 20 evidence.

Steps 21–22 verified private source preservation on `hardening/step20`, production
unchanged on `main`, and corrected future repository-local attribution. The branch
preview was blocked by old commit metadata, not presented as a successful deployment.
Step 23's presentation work is included in the Step 24A local documentation
checkpoint; it has not been pushed. Commercial readiness and backup/email limits
above are unchanged.
