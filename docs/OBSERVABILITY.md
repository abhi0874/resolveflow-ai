# Foundational operational observability — Step 12

This is a local, content-free logging and diagnostics foundation. It introduces no
paid monitoring, external telemetry, analytics vendor or additional AI request.

## HTTP correlation

The outer `RequestDiagnostics` ASGI middleware generates a new UUID for every API
HTTP request. It returns `X-Request-ID`; the Next.js proxy passes that response header
back to the browser. Untrusted inbound IDs are ignored. FastAPI error responses also
pass through this wrapper. CORS preflight handled outside the wrapper is not an
application request and does not have an application correlation ID.

Each completed request emits a JSON event with `event=http_request`, `request_id`,
code-defined route name, HTTP status and monotonic `duration_ms`. It records no raw
URL/path, query, cookies, authorization headers, body, email, ticket text, document
content or model reasoning. Unknown paths use `unmatched`. Standard Uvicorn access
logging is disabled for this application because it includes raw query strings;
these safe events replace it. Deployment proxies must independently follow the same
privacy policy. Existing error handlers retain safe exception categories without
exception values or tracebacks.

## Jobs and workflows

New jobs store the originating API correlation UUID in nullable
`workflow_jobs.correlation_id`. A new queued phase captures that phase's request ID;
legacy/direct-internal jobs may have null. This is diagnostic metadata, not an
idempotency key, authorization credential or client-supplied routing identifier.
RQ messages still contain only validated job/delivery identifiers.

Existing safe job events include request/job/execution IDs, phase, attempt and trusted
error category. Completed attempt events add duration from retained start/finish
timestamps when both exist. IDs link API acceptance to worker processing; logs never
contain prompts, provider responses, credentials or complete exception objects.
Workflow stage timings and creation/finish timestamps remain authoritative stored
measurements. Analytics reports elapsed durations with explicit queue/review caveats.
Missing measurements remain null; no historical duration backfill is fabricated.

A full-suite regression exposed an existing connection race: graph checkpoint writes
may run on a background thread while the ownership health probe used the same
psycopg connection. The probe now acquires the PostgresSaver cursor lock before
querying. A real PostgreSQL pipeline test verifies it waits for an active checkpoint
pipeline, preserving ownership checks and durable graph behavior.

## Operations and readiness

From `apps/api`:

```bash
uv run --locked python scripts/local_db.py status
uv run --locked python scripts/local_broker.py status
uv run --locked python scripts/jobs.py health
uv run --locked python scripts/jobs.py list
```

`health` measures database/broker connectivity, worker and dispatcher heartbeats,
database pending jobs and transport message count. `list` shows safe job metadata.
These are **operator CLI diagnostics**, not public analytics API fields. Public
`/api/v1/health` is liveness and `/api/v1/ready` tests database connectivity; neither
reveals broker URLs, topology, secrets or checkpoints. Run `alembic current`/`check`
for schema verification; readiness does not automatically run migrations.

Start/stop and recovery commands remain in WORKER_OPERATIONS.md. Restart the API,
dispatcher and workers after applying migration 0010 so processes use the new model
and diagnostics. Keep live inference disabled. No new credentials are needed.

## Verification and boundaries

Tests verify generated response IDs, persistence into accepted job records, safe log
fields and actual workflow/worker regressions. Measured query times use synthetic
isolated data, not customer payloads. Production log collection, retention, dashboards,
alerting, tracing between external services, SLOs and restore/load exercises remain
future work. Console logs are not durable audit storage. Ticket activity and exact
review records retain their existing application-level history guarantees.
