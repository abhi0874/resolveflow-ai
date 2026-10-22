# Local worker operations

Run these commands in the ResolveFlow checkout. Use its own PostgreSQL **55433**
and Valkey **56379**. Never stop the unrelated PostgreSQL service on **55432**.
Do not print `.env`, broker configuration, ownership markers, or credential URLs.

## One-time broker installation

The existing checkout already has a verified Apple Silicon Valkey binary. For a
fresh installation, Apple command-line build tools, `make`, and network access to
the official Valkey source are required. No Homebrew/global service or Docker is needed.

```bash
cd apps/api
export UV_CACHE_DIR=../../.cache/uv
uv sync --locked
uv run --locked python scripts/install_broker.py
uv run --locked python scripts/local_broker.py setup
```

The installer verifies the pinned 9.1.2 source SHA-256 against the published checksum,
builds in a temporary directory without spaces (the upstream Lua linker cannot handle
this checkout's spaced path), and copies the server/client binaries into ignored
`.local/native/valkey-9.1.2/src`. Setup creates an owned loopback-only broker with a
random password, AOF persistence, 128MB memory cap and `noeviction`. It appends only
`RESOLVEFLOW_REDIS_URL` to `apps/api/.env`, retaining Gemini/database settings.
Private marker/config/password files are mode 600 inside a mode-700 directory and
excluded by `.gitignore`. Do not copy `.env.example` over an existing `.env`.

## Start the existing local application

From repository root, prepare services/migrations:

```bash
cd apps/api
export UV_CACHE_DIR=../../.cache/uv
uv run --locked python scripts/local_db.py start
uv run --locked python scripts/local_broker.py start
uv run --locked alembic upgrade head
uv run --locked python scripts/workflows.py setup
```

In separate terminals (first three commands from `apps/api`):

```bash
# Terminal 1 — HTTP API
UV_CACHE_DIR=../../.cache/uv RESOLVEFLOW_AI_LIVE_ENABLED=false uv run --locked uvicorn resolveflow.main:app --app-dir src --host 127.0.0.1 --port 8000 --no-proxy-headers --reload

# Terminal 2 — PostgreSQL outbox dispatcher, required even when broker is healthy
UV_CACHE_DIR=../../.cache/uv RESOLVEFLOW_AI_LIVE_ENABLED=false uv run --locked python scripts/jobs.py dispatch

# Terminal 3 — dedicated RQ worker pool
UV_CACHE_DIR=../../.cache/uv RESOLVEFLOW_AI_LIVE_ENABLED=false uv run --locked python scripts/jobs.py worker

# Terminal 4 — from the repository root
API_INTERNAL_URL=http://127.0.0.1:8000 NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run dev -- --webpack
```

Open http://127.0.0.1:3000. The configured provider remains Gemini, with live generation
disabled. Normal workflows may reach `ai_not_configured` if generation is needed;
this is intentional and is not a silent fixture fallback. Use the isolated browser
harness below for a complete deterministic smoke test. API and worker must use the
same database, model artifacts, private document storage, queue and safety settings.
No new API key is required and no Gemini test is authorized by these commands.

## Diagnose and recover

From `apps/api`:

```bash
uv run --locked python scripts/local_db.py status
uv run --locked python scripts/local_broker.py status
uv run --locked python scripts/jobs.py health
uv run --locked python scripts/jobs.py list
uv run --locked python scripts/jobs.py reconcile
curl --fail http://127.0.0.1:8000/api/v1/ready
curl --fail http://127.0.0.1:8000/api/v1/health
```

`health` checks PostgreSQL, broker ping, recent RQ worker heartbeats, dispatcher
heartbeat, database pending count and actual transport queue count. It exits nonzero
if a required process is missing. Public `/ready` remains a content-free database
readiness check; private worker topology is not exposed. `list` prints status counts
and the latest 50 job/execution/workspace/ticket IDs, phase, attempt and safe category.
It never prints payloads or credentials. Worker/dispatcher console events are JSON
with correlation IDs and categories. Service startup and dependency libraries may
also emit their ordinary non-content startup messages.

- Broker down: accepted jobs remain in PostgreSQL. Start the owned broker; dispatch
  republishes automatically. Do not flush Redis or delete accepted job rows.
- Worker absent/crashed: restart `jobs.py worker`. After the recovery deadline,
  dispatch uses persisted checkpoints and the same draft identity. Normal default
  recovery eligibility is within 150 seconds plus dispatcher cadence after claim.
- Database down: restart only the owned cluster if appropriate. Keep workers and
  dispatcher running or restart them after readiness returns. No job can be accepted
  without its database transaction. Existing committed jobs remain authoritative.
- Retrieval failure: restore the exact configured local embedding snapshot. Attempts
  are bounded; failed executions do not silently regenerate. After resolving the cause,
  a user can deliberately start a new execution subject to normal quotas.
- Review pending: no worker should be occupied. Review the exact draft in the UI,
  then resume. Do not edit checkpoint payloads or fake review records.
- Long queue: inspect health and limits. Capacity contention is not a reason to kill
  unrelated processes or raise concurrency blindly on a laptop.
- Cancel: use **Stop workflow**. A flag is durable immediately; completion waits for
  a safe worker point. Do not use process termination as the user cancellation flow.

## Verification

With the private database running and installed local embedding artifacts:

```bash
# From apps/api; all tests use synthetic data and isolated databases/brokers.
PYTEST_ADDOPTS=--tb=short RESOLVEFLOW_AI_LIVE_ENABLED=false RESOLVEFLOW_AI_FREE_TIER_VERIFIED=false GEMINI_API_KEY=synthetic-test-key UV_CACHE_DIR=../../.cache/uv uv run --locked python scripts/local_db.py test
uv run --locked ruff check .
uv run --locked ruff format --check .

# From repository root
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run build -- --webpack

# From apps/api after the production build
UV_CACHE_DIR=../../.cache/uv uv run --locked python scripts/test_browser.py
```

The browser harness owns temporary ports 3100/8100 and a random broker port. It
starts actual API, dispatcher and RQ worker processes with deterministic mock AI,
uses synthetic test classifier artifacts, and cleans up only its marked test database,
processes and files. It refuses occupied test ports. Do not run these browser tests
against the development database. The API key environment override above is a literal
synthetic test value, not the configured key.

## Stop safely

Press **Ctrl+C once in each worker/API/frontend/dispatcher terminal**. Let the RQ
worker finish its current bounded task before closing that terminal. Then, from
`apps/api`:

```bash
uv run --locked python scripts/local_broker.py stop
uv run --locked python scripts/local_db.py stop
```

These helpers validate project ownership and preserve data. Do not use global
`killall`, `pkill`, `redis-cli flushall`, `docker compose down -v`, or database resets.
Unexpected worker loss is recoverable; deliberate cleanup still uses graceful stops.

## Optional Docker broker and hosted portability

Docker is **optional and was not installed or executed for this milestone**.
`compose.broker.yaml` is a portable broker-only configuration with a named persistent
volume and password secret generated by native `setup`. Stop the native broker first,
then, if Docker is installed and intentionally selected:

```bash
# Repository root
 docker compose -f compose.broker.yaml up -d
 docker compose -f compose.broker.yaml ps
 docker compose -f compose.broker.yaml down
```

Do not use `-v` on shutdown. Native and Docker broker data are separate; switching
brokers relies on the PostgreSQL outbox, not a Redis data migration. If also
containerizing workers later, use the broker's internal hostname/6379 and appropriate
PostgreSQL address rather than host loopback. Run the existing dispatcher and worker
commands as independent supervised services with shared model/document access.
Do not put permanent workers in Vercel serverless request handlers. No hosting or
recruiter-demo adaptation has been provisioned in Step 11.
