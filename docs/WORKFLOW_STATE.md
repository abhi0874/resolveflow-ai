# Workflow state and recovery contract

Step 10 version: `ticket-workflow-v1`. Code lives in
`apps/api/src/resolveflow/workflows/{contracts,graph,workers,service,storage}.py`.
HTTP inputs/outputs use Pydantic; the graph uses a typed `WorkflowState`.

## Persisted fields

| Field | Purpose |
| --- | --- |
| `execution_id`, `workspace_id`, `ticket_id`, `ticket_version` | Server-derived identity and input revision; validated at every node |
| `workflow_version` | Reject incompatible graph definitions instead of replaying them silently |
| `current_stage`, `completed_stages` | Actual node progress; completed names are deduplicated |
| `classification` | Existing bounded model recommendation/uncertainty/version, or unavailable marker |
| `priority` | Deterministic suggested priority, rule IDs/version and human-review requirement |
| `evidence` | Authorized document/chunk UUIDs, content hashes and similarity scores; no passage bodies |
| `context_summary` | Selected counts/characters, abstention flag and trusted reason |
| `draft_id` | Reference to the existing private response draft; text stays in that service's tables |
| `verification` | Passed/abstained, citation count, review requirement; explicit false factual-proof claim |
| `approval_status` | Not started, pending review, or saved decision; refreshed from the draft on reads |
| `status` | Running, paused, completed, rejected, needs_revision, failed or cancelled |
| `started_at`, `updated_at`, `finished_at`, `timings_ms` | Execution timestamps and actual per-stage elapsed milliseconds |
| `error` | Safe code and stage only; no exception body or provider response |

The SQL ownership record additionally stores original requester, idempotency request
UUID, synthetic confirmation, invocation count and timestamps. A composite foreign
key ensures the ticket belongs to the workspace. Request identity is unique within
workspace/requester. The UI receives a Pydantic projection, not arbitrary checkpoint
metadata or resume commands. Credentials, raw ticket text, passages, output text,
provider objects, sessions, clients and hidden reasoning are absent from graph state.
Checkpoint data still contains private business identifiers and must remain private.

## Sources of truth

PostgreSQL LangGraph checkpoint tables in `workflow_checkpoints` are authoritative
for graph transitions and interrupts. `workflow_executions` owns authorization,
version, request identity, cancellation and safe observable progress. Existing
`response_drafts`, `draft_citations` and `draft_reviews` remain authoritative for
text, source relationships and exact-revision decisions. Approval is never inferred
from an arbitrary resume payload. There is no independent second review system.

Progress publication and LangGraph checkpoint writes are separate transactions.
A crash can leave the progress projection ahead of the checkpoint. Recovery uses
the checkpoint and repeats only safe node operations. Generation specifically
checks its stable draft reservation before doing work. A completed checkpoint can
repair a stale execution projection. This is not a distributed transaction or a
claim of exactly-once remote-provider delivery. At most one provider attempt is
allowed by the stable reservation, sacrificing automatic retry after uncertainty.

## State transitions

| Condition | Result and recovery behavior |
| --- | --- |
| New valid request | `running`; start at classification |
| Duplicate same request | Return existing execution; never invoke graph automatically again |
| Classification unavailable | Record unavailable; continue with manual classification required |
| Empty/unsafe evidence or account-status question | Persist trusted abstaining draft, zero provider calls; pause for review; approval disabled |
| Embedding/retrieval failure | `failed` at retrieval; no downstream generation |
| Provider unavailable, quota, timeout, malformed output or invalid citation | `failed` at generation; no automatic retry; preserved safe code |
| Source/ticket changes | Fail closed before generation/publication or during verification/review |
| Verification passes | Real human interrupt; `paused` |
| Resume without a saved review | 409; remains paused |
| Saved valid approval | Recheck authorization, exact hash/revision, ticket and sources; `completed` |
| Rejection / revision request | `rejected` / `needs_revision`; terminal, no generation |
| Process lost after committed draft but before checkpoint | Explicit resume reuses draft and reaches review without generation |
| Process lost after generation reservation with unknown outcome | Explicit resume fails with `generation_interrupted`; never resends |
| Concurrent run/resume | Per-execution advisory lock rejects competing invocation (409) |
| Global execution slots exhausted | 429; committed execution can be recovered deliberately later |
| Attempt budget exhausted | 409; inspect history; no automatic retry or state override |
| Unknown graph/checkpointer schema version | 409 / 503; operator must resolve compatibility before replay |
| Database unavailable | Safe 503 or persisted node failure if safely recordable; no raw database details |
| Stop while idle/paused | `cancelled`; checkpoint deleted, review/draft history retained |

Terminal states reject resume. A new revision uses a new workflow/request UUID and
must pass all quotas and human approval again. Attempt bounds cover graph invocations,
including the initial run and human-decision resume. With a deliberately small cap,
a workflow can require a new execution rather than further recovery. The default is 3.

All reads, starts, resumes, cancellations and reviews enforce current tenant/RBAC
rules. Each worker rechecks authorization, and the generation service rechecks
permissions/ticket/source hashes after provider completion. Application database
roles are still trusted; PostgreSQL RLS and protection against privileged SQL writers
are separate future hardening.

See [AGENT_ORCHESTRATION.md](AGENT_ORCHESTRATION.md) for setup, API, bounds, cleanup,
worker rules and limitations. See [PROJECT_STATUS.md](PROJECT_STATUS.md) for measured
test evidence. No live inference or customer delivery is implied by graph completion.


## Step 11 dispatch amendment

The transition table above describes the original Step 10 inline invocation.
Normal HTTP start/resume/cancel now return 202 and expose a typed `job` alongside
execution state. PostgreSQL job rows own delivery, current-phase attempts and status;
checkpoints still own graph position. The dispatcher recovers interrupted work
automatically, subject to a three-attempt phase cap. Global/workspace contention
requeues rather than failing an accepted request. Database/retrieval errors can retry
before generation; ambiguous provider reservations never repeat inference. Queued,
running and paused executions accept cooperative cancellation with saved actor/time.
See BACKGROUND_JOBS.md for the authoritative asynchronous transition semantics.
