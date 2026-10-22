# Background workflow jobs — Step 11

The API accepts work with HTTP **202**; a dedicated Python process runs the existing
LangGraph graph. PostgreSQL owns accepted requests, jobs, drafts, reviews and
checkpoints. Redis-compatible Valkey transports identifiers only. This is an
at-least-once system, **not an exactly-once guarantee**.

## Selection and architecture

Pinned **RQ 2.12.0 / redis-py 8.1.0**, with **Valkey 9.1.2**, use maintained,
established queue implementations. RQ's process isolation, JSON serializer and
`SpawnWorker` suit this small Python application and Apple Silicon's ML libraries.
Dramatiq is viable but its actors, thread concurrency and default retry middleware
would add a second retry policy. PostgreSQL owns retry decisions here; RQ automatic
retries are disabled. No custom broker or orchestration engine was built.

References: [RQ workers](https://python-rq.org/docs/workers/),
[RQ jobs](https://python-rq.org/docs/jobs/),
[Dramatiq guide](https://dramatiq.io/guide.html),
[Valkey installation](https://valkey.io/topics/installation/).

```text
Authorized POST → execution + job transaction → HTTP 202
                          ↓
             dispatcher reconciles PostgreSQL outbox
                          ↓
          Valkey/RQ UUID message → dedicated SpawnWorker
                          ↓
      current authorization → existing LangGraph services
                          ↓
       PostgreSQL progress/checkpoints/draft → frontend GET
```

The new `workflow_jobs` table has one row per execution. Workspace and ticket IDs
are resolved through its immutable execution foreign key, avoiding duplicate scope
columns. Jobs track type, status, current-phase attempts, publication count, delivery
UUID, timestamps, next availability and a safe error category. Alembic **0009** is
additive; existing Step 10 executions and checkpoint threads remain recoverable.

## Lifecycle and durable publication

| Job status | Meaning |
| --- | --- |
| queued | Accepted or waiting for bounded processing retry; may not yet be in Valkey |
| running | Worker owns PostgreSQL session locks and has started this attempt |
| waiting_for_approval | Graph interrupted durably; worker capacity released |
| completed | Graph completed, rejected, or requested revision; graph retains precise outcome |
| failed | Processing cannot safely continue or retry budget exhausted |
| cancelled | Cooperative cancellation observed and persisted |

Execution state owns graph progress and exact review outcome; the job owns delivery
and attempt status. An execution's historical `running` value can coexist with a
queued job. Clients use the typed `job` field for queue status and the execution for
stages, evidence and review. Current-phase timestamps reset on authorized resume;
execution creation/completion timestamps and review history remain permanent.

Execution creation and its job row commit together. A separate dispatcher publishes
a durable delivery token, then enqueues it, then records publication. There is **no
cross-system atomic transaction**. A crash in any gap leaves a recoverable database
row. Reconciliation rotates stale delivery tokens; old messages no-op. Broker loss
cannot erase an accepted request. AOF is helpful but is not the durability authority.

The dispatcher scans bounded batches every five seconds. A queued published message
or interrupted running attempt is eligible for recovery after the 120-second job
limit plus 30 seconds. PostgreSQL ownership must also be free. Broker publication
uses exponential backoff capped at 60 seconds. Accepted outbox records remain pending
during infrastructure downtime rather than being discarded; this ongoing reconciliation
is distinct from bounded attempts to execute application logic.

## Ownership, bounds and idempotency

All workers use PostgreSQL session advisory locks for job, execution, global slots
and workspace slots. The OS/process/connection lifetime releases ownership on crash;
no permanent database mutex or expiring Redis lease allows an overlapping worker.
RQ enforces a hard job timeout. Ownership connections are checked at graph safe points
and before publishing generated output. The delivery UUID and state reject stale or
duplicate messages. Private authenticated broker access remains a trust boundary.

| Environment variable | Default |
| --- | --- |
| `RESOLVEFLOW_REDIS_URL` | Private authenticated loopback URL set by local setup |
| `RESOLVEFLOW_JOB_QUEUE` | `resolveflow-workflows` |
| `RESOLVEFLOW_WORKER_CONCURRENCY` | 1 process per worker pool, configurable 1–4 |
| `RESOLVEFLOW_WORKFLOW_CONCURRENCY` | 2 simultaneous graph invocations across processes |
| `RESOLVEFLOW_JOB_WORKSPACE_CONCURRENCY` | 1 per workspace |
| `RESOLVEFLOW_JOB_TIMEOUT_SECONDS` | 120 seconds per job attempt |
| `RESOLVEFLOW_JOB_MAX_ATTEMPTS` | 3 total attempts per start/resume phase |
| `RESOLVEFLOW_JOB_QUEUE_CAPACITY` | 50 waiting transport messages |
| `RESOLVEFLOW_JOB_MAX_PENDING` | 100 queued/running database jobs globally |
| `RESOLVEFLOW_JOB_WORKSPACE_PENDING` | 10 queued/running per workspace |
| `RESOLVEFLOW_JOB_RECONCILE_SECONDS` | 5 seconds |

Existing daily execution/generation quotas, 60-second graph deadline, provider caps,
and generation concurrency remain. Capacity is checked within a short global
reservation transaction. Waiting human review does not occupy active worker slots.
Set matching global/workspace limits on every worker deployment.

A repeated request UUID returns the same execution; mismatched payloads conflict.
One job per execution and the existing stable draft reservation prevent duplicate
persisted drafts. Repeated resume while queued/running returns the existing operation.
Exact-draft reviews remain immutable and unique. Graph stages update saved summaries,
not duplicate append-only ticket events. An ambiguous provider reservation fails
closed; retry never assumes a provider request did not run. External side effects
are not implemented, and distributed network partitions are not a claim of exactly-once
execution or comprehensive chaos certification.

## Failures and cancellation

Temporary database errors and local retrieval failures retry at 2, 4 seconds, then
fail on attempt 3. Crashed attempts count toward the same bound. Capacity contention
waits without consuming a processing attempt. Authorization failures, missing or
changed resources, invalid transitions/output/citations, provider timeout, Gemini
quota exhaustion and ambiguous generation are terminal. Provider calls never
implicitly retry and never switch to a paid fallback. Safe log events contain only
job/execution IDs, phase, attempt and trusted categories; no prompt or exception body.

Cancellation records requesting user/time and a durable flag. Queued/paused work is
scheduled for cleanup; running work observes the flag before/after nodes and around
provider generation. An already running external request cannot necessarily be
interrupted immediately; its returned output is discarded if cancellation is observed
before publication. Completed drafts remain history; no customer communication occurs.

Approval still records the exact current draft revision through the existing review
endpoint. The UI then requests asynchronous resume. If that request fails, review is
still saved and the user can resume it later. Workers recheck current authorization,
review hash/version, ticket and sources. Legacy Step 10 executions can acquire a job
without replacing their checkpoint. Background job attempt bounds replace the legacy
three-invocation recovery cap so transient retries do not consume the approval phase.

## UI, tests and limits

History/status endpoints enforce existing tenant/ticket access. No public queue,
worker or raw checkpoint endpoint is exposed. The UI displays queued/processing,
actual stages/timings, attempts, cancellation and terminal outcomes. It polls every
two seconds while active, pauses reads in hidden tabs, stops at review/terminal state,
and caps automatic reads at 60 per polling session; refresh restarts the bounded session.
No progress percentage is invented. Old synchronous graph regressions use an explicit
**test-environment-only** seam; normal HTTP execution is always queued.

Real tests use disposable authenticated Valkey processes, isolated marked PostgreSQL
databases and dedicated RQ SpawnWorkers. They cover broker replacement, worker kill
mid-graph and restart, checkpoint/review resumption, duplicate suppression and safe
cleanup. Database transient errors also have focused injected-failure coverage.
See PROJECT_STATUS for the actual executed results and WORKER_OPERATIONS for commands.

API, dispatcher and workers can deploy independently with configured PostgreSQL,
Redis/Valkey and provider adapters. Shared document storage and identical local model
artifacts must be provisioned for workers. The optional Docker configuration supplies
a broker, not a production deployment. Hosted TLS, least-privilege broker ACLs, service
supervision, backups/restore and operational load testing remain deployment work.
Long-lived workers do not belong inside Vercel request functions. The future Vercel
recruiter demo needs a separate lightweight execution strategy; it is not built here.
