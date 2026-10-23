# ResolveFlow AI

ResolveFlow AI is a planned customer-support SaaS platform that helps support
teams classify tickets, retrieve relevant knowledge, draft grounded responses,
and review those responses before taking action. The long-term goal is a secure,
maintainable, deployable product with a polished, responsive interface.

**Current state: the standalone recruiter demo is live on Vercel Hobby and passed Step 15D hosted verification. Step 16 UI polish is local and not deployed.**

[Explore the recruiter demo](https://resolveflow-ai-rosy.vercel.app/demo). Start with a citation-linked workflow, review the example draft, then open **Under the hood** for the implemented architecture. The public demo uses synthetic data and precomputed examples; it does not run live Gemini or the full backend.
The interactive recruiter demo runs alongside the complete local application and workspace analytics.
Registration, login/logout, server-side sessions, workspace selection/settings,
and role-controlled membership management now work with the local PostgreSQL API.
The ticket inbox adds creation/editing, assignment, search/filtering, notes and
persistent activity history. The knowledge base adds private PDF/TXT/Markdown uploads,
real text extraction, deterministic stored chunks, authorized downloads and recoverable
deletion. A trained TF-IDF/logistic-regression classifier now suggests ticket
categories, with explicit manual acceptance and activity history. Local Sentence Transformer
embeddings and pgvector now retrieve authorized source passages, with indexing/reindexing
and semantic search in the knowledge base. The public homepage is preserved. Docker, paid identity services and AI credentials are not required for local tests.
Background integration tests use the installed private Valkey broker binary. The response assistant
adds bounded RAG drafts, citations and persistent internal approval. The real Gemini
adapter passed one explicitly approved synthetic smoke test on 2026-10-20; live
inference remains disabled for routine use. Step 10 adds a seven-stage workflow,
durable approval pauses, authorized recovery and real workflow progress on tickets.
Step 11 moves execution into dedicated Python workers with a PostgreSQL outbox,
bounded retries, cooperative cancellation and asynchronous status polling.
Production readiness is a future acceptance gate, not a current claim.

## Planned capabilities

- Ticket inbox, classification, prioritization, and workflow automation.
- Document ingestion and semantic retrieval with source citations.
- AI-generated drafts using genuine LangGraph orchestration.
- Human review, editing, approval, and an auditable action history.
- Support analytics and model-quality evaluation.
- A premium SaaS interface with responsive layouts, accessible controls, and
  clear loading, empty, error, and quota-exhaustion states.

## Required technology stack

| Area | Planned technology | Status |
| --- | --- | --- |
| Frontend | Next.js, TypeScript, Tailwind CSS | Installed; homepage implemented; shadcn/ui remains planned |
| API | Python, FastAPI, Pydantic | System, authentication, authorized workspace, ticket, document and classification routes implemented |
| Persistent storage and search | PostgreSQL with pgvector | Local core tables and extension verified; exact tenant-scoped vector search implemented |
| AI workflow | LangGraph | Real seven-node graph; PostgreSQL checkpoints, interrupt/resume and ticket UI |
| Classification and embeddings | scikit-learn, sentence-transformers | scikit-learn baseline trained and evaluated; local sentence-transformers embeddings implemented |
| Background jobs | RQ, Valkey and Python workers | Durable PostgreSQL outbox, dedicated workers and recovery implemented |
| Initial inference | Google Gemini API, `gemini-3.6-flash` | Official SDK adapter verified in one approved synthetic test; live calls remain disabled |
| Checks | Pytest, Ruff, TypeScript, ESLint, Next.js build, Playwright | Backend and real browser auth/workspace/ticket/document/classification suites implemented; Vitest remains planned |
| Frontend hosting | Vercel Hobby, personal recruiter demonstration | Standalone demo deployed; full backend remains local |

## Intended architecture

The monorepo contains a Next.js client in `apps/web/` and a FastAPI backend in
`apps/api/`. Dedicated Python workers share backend application services.
PostgreSQL stores business records, internal notes, ticket activities, document chunks and
384-dimensional embeddings and durable LangGraph checkpoints. LangGraph coordinates
classification, retrieval, drafting and a persistent human-review pause through
asynchronous jobs executed by dedicated RQ workers. PostgreSQL owns durable job state.

Application services depend on provider-neutral generation and embedding
interfaces. The initial generation adapter uses Gemini. Replacing it will
require adapter/configuration changes and evaluation, without rewriting ticket
or approval business logic. Local tests will run without API credentials.

The recruiter demo uses a separate synthetic data adapter and requires only Next.js
and the visitor's browser. It is hosted on Vercel Hobby without an API, database,
worker or Gemini key. Hosted browser verification found no local-service requests;
a physical MacBook-off test on a separate device has not been performed. Hosting the full application still requires
a separate API/storage/worker/ML arrangement.

## Development boundaries

- No additional paid services, APIs, or cloud subscriptions are required or
  authorized. Local open-source services and synthetic fixtures are the baseline.
- Live Gemini use must remain within a verified free tier, with server-side
  quotas, strict resource limits, and a kill switch. No automatic paid fallback.
- No external deployment or service activation without explicit approval.
- GPT-6 Astra is the requested primary development agent; this repository does
  not configure or attest to the active chat model. Multi-agent development is
  optional future work.
- The personal demo and eventual commercial production deployment have distinct
  operational requirements. The demo is not a claim of production availability.

## Repository contents

```text
ResolveFlow AI/
├── .gitignore
├── .nvmrc
├── AGENTS.md
├── README.md
├── apps/
│   ├── web/
│   │   ├── .env.example
│   │   ├── AGENTS.md                 # Version-specific Next.js guidance
│   │   ├── package.json / package-lock.json
│   │   ├── next.config.ts / tsconfig.json
│   │   ├── eslint.config.mjs / postcss.config.mjs
│   │   └── src/
│   │       ├── app/                  # App Router, root layout, tokens/styles
│   │       ├── components/           # layout/, home/, ui/
│   │       └── lib/api.ts            # Typed, bounded health request
│   └── api/
│       ├── .env.example / .python-version
│       ├── pyproject.toml / uv.lock
│       ├── alembic.ini / migrations/ # Versioned PostgreSQL schema
│       ├── scripts/local_db.py       # Project-local PostgreSQL lifecycle
│       ├── src/resolveflow/
│       │   ├── main.py              # Application factory + outer CORS wrapper
│       │   ├── api/                 # Versioned routes
│       │   ├── services/            # Session security and central authorization
│       │   ├── core/                # Settings + error handling
│       │   ├── db/                  # ORM models and session management
│       │   └── schemas/             # Response contracts
│       └── tests/                   # Endpoint, error, settings and CORS tests
└── docs/
    ├── ARCHITECTURE.md
    ├── DATABASE.md
    ├── AUTHENTICATION.md
    ├── AUTHORIZATION.md
    ├── TICKET_MANAGEMENT.md
    ├── KNOWLEDGE_BASE.md
    ├── ML_CLASSIFICATION.md
    ├── ML_EVALUATION.md
    ├── PROJECT_PLAN.md
    └── PROJECT_STATUS.md
```

Read [the architecture](docs/ARCHITECTURE.md) for component responsibilities and
security requirements, [the plan](docs/PROJECT_PLAN.md) for phases and dependency
gates, and [the status](docs/PROJECT_STATUS.md) for environment findings and
completed work. Follow [the development instructions](AGENTS.md).

## Local setup

Verified on Apple Silicon macOS with Node.js **26.5.0**, npm **11.17.0**, Python
**3.14.6**, and uv **0.11.26**. `.nvmrc` and `apps/api/.python-version` record the
verified runtimes. If you already use nvm, run `nvm use` from the repository root.
The API currently targets Python 3.14; compatibility with future ML dependencies
and the eventual Vercel runtime must be reassessed before those phases.

Run these commands from the repository root to install the locked dependencies:

```bash
(cd apps/web && npm ci --cache ../../.cache/npm)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv sync --locked)
```

Only free registry packages are required. The API environment is isolated at
`apps/api/.venv/`; no global Python packages are installed. No Docker,
cloud account or AI key is needed. Queue integration tests require the private Valkey binary. PostgreSQL is needed for readiness
and integration checks; liveness and unit tests work without it. `uv` must already be available; use
[uv's official installation instructions](https://docs.astral.sh/uv/getting-started/installation/)
if setting up another machine.

For the database, follow [DATABASE.md](docs/DATABASE.md): `local_db.py setup`
generates a private API `.env` without overwriting existing values. Do not copy
the placeholder database URL over it. For optional web overrides:

```bash
cp -n apps/web/.env.example apps/web/.env.local
```

- Web: `NEXT_PUBLIC_API_BASE_URL` is a **public** API origin, defaulting to
  `http://127.0.0.1:8000`. Never put credentials in a `NEXT_PUBLIC_` variable.
  Next.js embeds public values into client bundles; restart dev or rebuild after
  changes. This origin must be reachable by the browser.
- API: `RESOLVEFLOW_ENVIRONMENT`, `RESOLVEFLOW_CORS_ORIGINS` (a JSON array of exact
  HTTP(S) origins), `RESOLVEFLOW_DOCS_ENABLED`, `DATABASE_URL`, and the database
  pool/timeout settings are validated server-side.
  Process environment overrides `apps/api/.env`, whose path is resolved independently
  of the working directory. Unknown dotenv settings fail validation.
- `DATABASE_URL` uses PostgreSQL with psycopg. Missing configuration leaves health
  usable and readiness at HTTP 503. Server-only Gemini settings and privacy gates
  are described in [GEMINI_INTEGRATION.md](docs/GEMINI_INTEGRATION.md).
- Authentication uses same-origin `/api/v1` routes. Server-only `API_INTERNAL_URL`
  points Next.js to FastAPI (required for `next start`; dev defaults to port 8000).
  `RESOLVEFLOW_TRUSTED_ORIGINS` controls exact mutation origins; production requires
  HTTPS. `RESOLVEFLOW_SESSION_HOURS` defaults to 12. See
  [authentication](docs/AUTHENTICATION.md) for cookie/CSRF and production behavior.
- Real `.env` files are ignored; sanitized `.env.example` templates are versioned.

## Train the local classifier

A fresh checkout needs an explicit training run; application startup never trains.
This checkout already contains the ignored, trained `baseline-v1` artifact.
From the repository root:

```bash
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/classifier.py train --version baseline-v1)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/classifier.py evaluate --version baseline-v1)
```

Existing model versions cannot be overwritten. See the ML runbook for creating a
new version and selecting it with `RESOLVEFLOW_CLASSIFIER_MODEL_VERSION` before an
API restart. `RESOLVEFLOW_CLASSIFIER_THRESHOLD` defaults to 0.45. A missing model
shows an unavailable state while ordinary ticket editing continues to work.

The 280-example synthetic corpus yields **78.6% held-out accuracy and 0.785 macro F1**
(56 records in 28 held-out scenarios). These are synthetic evaluation results,
not production accuracy. At threshold 0.45, only 13/56 test records receive a
suggestion; the remainder require manual categorization. Scores are uncalibrated.

## Run locally

ResolveFlow's native PostgreSQL uses **127.0.0.1:55433**. Port 55432 belongs to
another local project and must be left alone. The existing data directory is
`data/local/postgresql18`; the ignored cluster marker and private API database URL
agree with the helper and PostgreSQL configuration. Existing data and Gemini
credentials are preserved. Never copy the template's placeholder database URL over
the working private `.env`.

Start the configured project-local database and apply migrations first:

```bash
cd apps/api
export UV_CACHE_DIR=../../.cache/uv
uv run python scripts/local_db.py start
uv run --locked python scripts/local_broker.py start
uv run alembic upgrade head
uv run --locked python scripts/workflows.py setup
```

For a fresh checkout, use the installation and one-time `setup` commands in
[the database runbook](docs/DATABASE.md). Stop the database with
`uv run python scripts/local_db.py stop` from `apps/api`; this preserves data.

Install/setup the private broker once with `scripts/install_broker.py` and
`scripts/local_broker.py setup` from `apps/api`; the existing checkout is already set
up. See [worker operations](docs/WORKER_OPERATIONS.md) for safe private configuration.

Start the backend in terminal 1, from the repository root:

```bash
cd apps/api
UV_CACHE_DIR=../../.cache/uv uv run --locked uvicorn resolveflow.main:app --app-dir src --host 127.0.0.1 --port 8000 --no-proxy-headers --reload
```

Start the dispatcher and worker in two more terminals, each from `apps/api`:

```bash
UV_CACHE_DIR=../../.cache/uv RESOLVEFLOW_AI_LIVE_ENABLED=false uv run --locked python scripts/jobs.py dispatch
```

```bash
UV_CACHE_DIR=../../.cache/uv RESOLVEFLOW_AI_LIVE_ENABLED=false uv run --locked python scripts/jobs.py worker
```

Check them with `uv run --locked python scripts/jobs.py health` and inspect safe job
metadata with `uv run --locked python scripts/jobs.py list`. Accepted requests remain
saved if the broker/worker is unavailable; the dispatcher is required for recovery.

Start the frontend in terminal 4, from the repository root:

```bash
API_INTERNAL_URL=http://127.0.0.1:8000 NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run dev -- --webpack
```

Open [the homepage](http://127.0.0.1:3000). The development-only connection panel
under **Project status** makes a real browser request to the API. It shows
checking, connected, or unavailable, with a **Check again** button. Requests time
out after four seconds. The rest of the page remains usable when the API is down.
This public indicator performs no authentication or provider calls.

Open [registration](http://127.0.0.1:3000/register) or
[login](http://127.0.0.1:3000/login), then enter the protected
[workspace area](http://127.0.0.1:3000/app). Create a workspace, select among your
workspaces, manage permitted settings/members, and sign out. Open **Ticket inbox**
to create, triage, assign and discuss tickets; its detail view shows persistent history. Open **Knowledge base** to upload, inspect,
download and manage private reference documents. Open an editable ticket and choose
**Classify with ML** for a real local suggestion; review it before accepting. Use registered
development accounts; email ownership is not verified and recovery is deferred.

The API, web and broker listeners bind to loopback. The web command uses Next.js's supported webpack
option to avoid the local Turbopack socket issue. The backend keeps the saved Gemini
provider with live inference disabled; normal startup makes no Gemini requests.
For an explicitly labeled deterministic workflow smoke test, use the isolated
`scripts/test_browser.py` command below rather than enabling live inference or
changing the saved provider. It creates and removes its own test databases on 55433.

Stop each process with **Ctrl+C in its own terminal**; let the worker finish its current
bounded job. Then stop the owned broker with `scripts/local_broker.py stop` and database
with `scripts/local_db.py stop`. No data is reset.
Stopping the API and clicking **Check again** demonstrates the unavailable state;
restart it and check again to verify recovery. CORS permits only
`http://localhost:3000` and `http://127.0.0.1:3000` by default, with no credentials.
If you change the web port, update the allowed origins and restart the API.

## API endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/health` | `{ "status": "ok", "service": "resolveflow-api" }` |
| `GET /api/v1/ready` | PostgreSQL connectivity; HTTP 200 ready or safe HTTP 503 unavailable |
| `GET /api/v1/info` | Product name, version `0.1.0`, and description |
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/openapi.json` | Generated OpenAPI contracts |

[Interactive API docs](http://127.0.0.1:8000/docs) are enabled by default and can
be disabled with `RESOLVEFLOW_DOCS_ENABLED=false`. The documentation UI uses
FastAPI's default CDN assets, while the JSON schema and API itself require no
external network. Health is process liveness only, not database/AI readiness.
Errors use `{ "error": { "code": "…", "message": "…" } }` without leaking
exception details or submitted values. CORS is not authentication.

Authentication and workspace endpoint contracts are in
[AUTHENTICATION.md](docs/AUTHENTICATION.md) and
[AUTHORIZATION.md](docs/AUTHORIZATION.md). Ticket routes and policy are in
[TICKET_MANAGEMENT.md](docs/TICKET_MANAGEMENT.md). Document contracts, storage limits
and recovery are in [KNOWLEDGE_BASE.md](docs/KNOWLEDGE_BASE.md). ML contracts, training and observed evaluation results are in
[ML_CLASSIFICATION.md](docs/ML_CLASSIFICATION.md) and
[ML_EVALUATION.md](docs/ML_EVALUATION.md). All mutations require a valid session
CSRF token and trusted Origin; UI hiding is not the authorization boundary.

## Run checks

From the repository root:

```bash
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run build
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run --locked ruff check .)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run --locked ruff format --check .)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run --locked pytest)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/local_db.py test)
```

Default Pytest skips explicitly marked PostgreSQL cases. The database helper runs
the full suite using disposable databases; start the project database first.
See the latest measured counts in PROJECT_STATUS.md. See [DATABASE.md](docs/DATABASE.md) for isolation and migration details.

The build does not need a running backend. Preview the production build with:

```bash
API_INTERNAL_URL=http://127.0.0.1:8000 npm --prefix apps/web run start
```

Stop the dev server first because both use port 3000. The development connection
panel is intentionally absent from production output. See
[the status record](docs/PROJECT_STATUS.md) for actual verification results,
resolved failures, and current dependency warnings.

The browser scenarios use installed Google Chrome, the production build,
and a fresh isolated PostgreSQL database, private temporary storage and its own
real synthetic-data-trained classifier and local embeddings. Response generation uses
an explicitly labeled deterministic fixture. With PostgreSQL running, run:

```bash
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/test_browser.py)
```

The helper owns test servers on 3100/8100 and cleans up its marked test database and temporary storage.
See the authentication runbook for prerequisites and maintenance commands.

## Deployment preparation and limitations

The web app uses standard Next.js scripts and configuration. For a future Vercel
project, select `apps/web` as its root directory, select a supported compatible
Node runtime, and set any public configuration before building. No Vercel project,
credentials or hosting resources have been created.

The homepage links to the working synthetic recruiter demo at `/demo`.
Theme tokens follow the system light/dark preference; a user theme switch is not
implemented. shadcn/ui and Vitest remain future work. Workspace analytics are implemented. Background workers are implemented.
LangGraph orchestration is implemented. Gemini passed one approved synthetic test;
unrestricted live inference remains disabled. Email verification, password
recovery, MFA, authentication audit events and public-production hardening are deferred.
The previously recorded frontend runtime dependency audit was clean; a development-only ESLint/glob advisory remains
open and is documented in the authentication runbook. Local application startup does not establish hosted-demo or
production readiness. Step 14 local release verification is complete; subsequent
work requires a defined next-step scope. Document extraction is bounded
and synchronous; production storage and operational hardening remain
future work. See the knowledge-base runbook for recovery and residual risks.


## Local semantic retrieval

Download the free pinned model once; application inference then runs offline:

```bash
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/download_embeddings.py)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run alembic upgrade head)
```

Open a completed document and choose **Index document**. Existing uploads are eligible
without uploading again. Search from **Search by meaning** in the knowledge base;
results link to actual source passages and preserve workspace permissions. Viewer
access remains metadata-only. Reindex replaces vectors atomically; deleted content
is excluded even when file cleanup fails.

See [SEMANTIC_SEARCH.md](docs/SEMANTIC_SEARCH.md) for setup, APIs, indexing/recovery,
model replacement, limits and CLI commands. [RETRIEVAL_EVALUATION.md](docs/RETRIEVAL_EVALUATION.md)
records actual synthetic results: Recall@5 0.9286, MRR@5 0.9286, Hit Rate@5 0.9524.
These 24 questions over 14 documents do not establish production accuracy. No generated
answers, Gemini, LangGraph or deployment are included in Step 8.

## Response drafts and internal review

After applying migration `0007`, open a ticket to use **Response assistant**.
Authorized editors can generate a draft, inspect source quotations, approve the
exact draft, reject it or request revision. History persists; changed tickets or
sources invalidate approvability. Viewer cannot read document-derived drafts.
Approval never sends a message or performs a customer action.

Default cloud inference is disabled. Missing evidence can produce an explicit
local abstention; a missing Gemini configuration never produces a fake answer.
The provider uses `gemini-3.6-flash` through the official Python SDK, with
strict call/input/context/output budgets and synthetic-data gates.

See [GEMINI_INTEGRATION.md](docs/GEMINI_INTEGRATION.md) for secure configuration,
free-tier/privacy requirements and the opt-in single-call smoke command;
[AI_PROVIDERS.md](docs/AI_PROVIDERS.md) for the provider boundary;
[RAG_PIPELINE.md](docs/RAG_PIPELINE.md) for APIs, persistence and review; and
[RAG_EVALUATION.md](docs/RAG_EVALUATION.md) for measured synthetic results.
The 12-case fixture evaluation achieved 7/7 expected-source retrieval hits and
5/5 expected abstentions, but only 3/7 required-term completeness. These are
structural pipeline checks, not Gemini quality or production accuracy.

## Ticket AI workflows

After migrations and explicit checkpoint setup, open an editable ticket's **AI
workflow** section. Start an execution, inspect real stage summaries and citations,
and approve/reject/request revision on its exact draft. Review is saved privately;
approval sends nothing. Paused work survives API restart and can be resumed by a
currently authorized editor. Start uses the same provider configuration and quotas
as the response assistant. Live Gemini remains disabled unless separately enabled
under the existing free-tier/synthetic-data gates.

[AGENT_ORCHESTRATION.md](docs/AGENT_ORCHESTRATION.md) describes the graph, setup,
limits, API and recovery. [WORKFLOW_STATE.md](docs/WORKFLOW_STATE.md) documents
state ownership, privacy and failure semantics. Step 10 introduced no Redis service,
customer delivery or deployment. A future hosted backend must run independently
of this machine.

On machines where Turbopack cannot open its local build socket, the supported
production-build alternative is `npm --prefix apps/web run build -- --webpack`.
The Step 10 production build and browser suite use that option.


## Background workflow processing

Step 11 uses RQ **2.12.0**, redis-py **8.1.0** and private Valkey **9.1.2** on port
**56379**. Workflow start/resume/cancel return **202 Accepted** with persistent job
metadata. Review pauses release worker capacity. PostgreSQL is authoritative; broker
replacement and worker restart recover accepted work without creating another draft.
This is at-least-once delivery with application idempotency, not an exactly-once claim.

Read [BACKGROUND_JOBS.md](docs/BACKGROUND_JOBS.md) for settings, bounds and recovery
semantics, and [WORKER_OPERATIONS.md](docs/WORKER_OPERATIONS.md) for exact start/stop,
health, test and optional Docker commands. Automated verification uses deterministic
mock AI and isolated database/broker processes. No live Gemini requests are made.
Step 12 analytics and Step 13 local recruiter demo preparation are implemented; public hosting remains future work.


## Analytics and operational visibility

Workspace owners/admins can open **Workspace analytics** from team/settings or
**Analytics** in the app sidebar. `/app/analytics?workspace=UUID` displays real
creation-cohort ticket, workflow, review, job and knowledge-base measurements, with
validated UTC date ranges and current queue counts clearly separated. Missing
history/zero denominators display unavailable values rather than invented numbers.
All aggregation is workspace-scoped PostgreSQL SQL; no AI calls are involved.

Apply additive migration **0010** using the normal `alembic upgrade head` command,
then restart the API, dispatcher and workers. Existing data and credentials are
preserved. No additional service setup is needed. See [ANALYTICS.md](docs/ANALYTICS.md)
for metric definitions, permissions, query limits and measured performance, and
[OBSERVABILITY.md](docs/OBSERVABILITY.md) for safe request/job correlation and diagnostics.
Step 13 adds a separate synthetic demo; public deployment remains unapproved.


## Recruiter demo — no backend required

The landing page’s **Explore Live Demo** opens `/demo`: a separate synthetic workspace
with editable tickets, keyword document search, source-linked workflow replays,
human review examples and analytics calculated from the same local records.
The real authenticated application and Python services remain unchanged.

From the repository root:

```bash
npm --prefix apps/web run demo:build
npm --prefix apps/web run demo:start
```

Open http://127.0.0.1:3200/demo. These commands set `NEXT_PUBLIC_APP_MODE=demo`
and `DEMO_LIVE_AI_ENABLED=false` without changing private environment files.
No API, database, worker or key is needed. Temporary changes use tab-local session
storage; Reset demo restores the authored examples. Workflow replay is explicitly
not live AI. The demo blocks the real API proxy and cannot enable public inference.
Node 24 LTS is the prepared Vercel target. Rebuild when switching modes; both use `.next`.

See [RECRUITER_DEMO.md](docs/RECRUITER_DEMO.md),
[DEMO_SECURITY.md](docs/DEMO_SECURITY.md) and
[VERCEL_DEPLOYMENT.md](docs/VERCEL_DEPLOYMENT.md) for architecture, exact verification
commands, environment settings and hosting limits. Nothing is publicly deployed.
A later approved hosted deployment will be independent of the developer’s MacBook;
that hosted acceptance check is still pending. Stop after Step 14; Step 15 is not authorized.

The [release readiness report](docs/VERCEL_RELEASE_READINESS.md) records the final
13 passing demo checks, production build, type/lint checks, secret and bundle audit,
zero runtime dependency advisories, and the unresolved development-only lint advisory.
Vercel settings: **Next.js · root `apps/web` · Node 24.x · install `npm ci` · build
`npm run demo:build` · default output**. Set `NEXT_PUBLIC_APP_MODE=demo` and
`DEMO_LIVE_AI_ENABLED=false`; optionally `NEXT_TELEMETRY_DISABLED=1`. No secret or
backend URL is required. Step 15A adds the reviewed initial local commit; no remote is configured. Private
GitHub publication still needs explicit approval. No deployment has been attempted.
