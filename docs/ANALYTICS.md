# Workspace analytics — Step 12

The authenticated `/app/analytics?workspace=UUID` dashboard reads stored application
records. No provider or queue API is called to compute a metric. No artificial
business figures, growth estimates, AI summary or customer delivery is introduced.

## Architecture and permissions

`analytics/schemas.py` defines typed contracts/date validation; `queries.py` owns
SQLAlchemy aggregates; `resolution.py` validates status-event histories in PostgreSQL;
`service.py` starts a read-only repeatable-read snapshot and rechecks authorization.
The thin versioned route returns the combined overview in one request, avoiding
inconsistent independently fetched cards. Database statements have a 1.5-second
local timeout. Existing authenticated request sessions and safe error envelopes are reused.

`analytics:read` is an explicit central permission for **Owner/Admin only**.
Support Agent and Viewer receive 403; absent authentication is 401; a nonmember or
nonexistent workspace receives the same 404. The permission is checked inside the
report snapshot. Every aggregate and joined history is workspace-filtered in SQL.
No private ticket, document, job, user or checkpoint identifiers/content are returned.
Category labels are workspace data visible only to authorized analytics readers.
There is no RLS claim; application database credentials remain trusted infrastructure.

API:

```text
GET /api/v1/workspaces/{workspace_id}/analytics/overview?start=YYYY-MM-DD&end=YYYY-MM-DD
```

One typed response contains `tickets`, `workflows`, `jobs`, `reviews`, `knowledge_base`,
`range` and `generated_at`. Separate section endpoints are unnecessary for this
bounded dashboard. Unexpected/duplicate parameters, invalid dates, reversed ranges,
future end dates and ranges over 366 days are rejected. Next.js independently
allowlists the route and date parameters. Responses are private/no-store.

## Dates and cohort semantics

Defaults are today and the preceding 29 **UTC** dates, inclusive. SQL uses
`created_at >= start 00:00 UTC AND created_at < (end + 1 day) 00:00 UTC`.
Days are generated explicitly, including zero-count dates, with at most 366 buckets.
All distributions are **current states of records created in that range**, not
historical snapshots of those states. Changing a ticket today can change the current
outcome shown for an old creation cohort. Completion/review may happen after the
selected end; creation-cohort metrics reflect the observed current outcome.

The exception is `jobs.current_statuses`: current persisted job states for the whole
workspace regardless of creation date, explicitly labeled in the UI. Counts are
PostgreSQL job records, not Redis transport message counts or worker topology.

## Metric dictionary

| Metric | Exact measurement |
| --- | --- |
| Total tickets / creation trend | Count selected ticket creation cohort; daily UTC creation counts |
| Status | Current open, in_progress, waiting_for_approval, resolved, closed counts. Ticket waiting status is manual and distinct from graph pause |
| Priority | Current low/medium/high/urgent distribution |
| Category | Current case-sensitive labels; null is a distinct no-category bucket. Top 20 groups plus a remainder; explicit `Category:` prefix avoids collisions with missing/remainder labels |
| Resolution eligible count | Current resolved/closed cohort tickets with a complete, valid creation/status-event chain and a resolution after the latest reopen/nonterminal transition |
| Mean/median resolution seconds | Creation timestamp to **latest** valid transition to resolved, including all elapsed reopened periods. This is not agent working time or per-cycle resolution time |
| Resolution trend | Latest eligible resolution dates falling inside the range, once per eligible creation-cohort ticket. It is not all resolution events and not all resolutions of older tickets |
| Workflow total | Unique execution rows in creation cohort; attempts/retries never add executions |
| Workflow status/stage | Current execution status and last persisted stage, including paused separately |
| Workflow completion/failure rates | completed / terminal, failed / terminal. Terminal denominator includes completed, failed, cancelled, rejected and needs_revision. Running/paused excluded |
| Workflow elapsed seconds | Mean finished_at − created_at for eligible terminal rows; includes queue time and human review wait |
| Job counts | Current workspace job states plus creation-cohort total; one job per execution |
| Retained phase retries | Sum max(attempts − 1, 0) for selected jobs. Phase attempts reset on resume, so **not lifetime retries** |
| Initial queue wait | Mean started_at − created_at only when kind=start and attempts=1; resume/retry timestamps cannot reconstruct original wait |
| Latest attempt duration | Mean finished_at − started_at when both exist and interval is nonnegative; only last retained attempt, not cumulative compute time |
| Human review counts | Current outcomes of successfully generated drafts in creation cohort, one row per draft; generating/failed drafts excluded |
| Approval rate | Approved / (approved + rejected + needs_revision); pending excluded. A recorded decision does not mean current source validity or customer delivery |
| Request-to-review seconds | Mean unique review.created_at − draft.created_at; includes generation, since a generation-completed timestamp is unavailable |
| Documents / uploads | Surviving, non-deleting document rows created in range and their UTC creation trend. Deleted uploads cannot be reconstructed |
| Processed / failed documents | Current extraction processing status completed / failed |
| Indexed documents | Current indexing_status indexed, separate from extraction success; not a fresh revalidation of every vector |
| Chunks | Actual stored chunk count joined to the scoped document cohort, not a guessed count from file size |

A measurement returns `{value, samples, unavailable_reason}`. Zero counts and actual
zero durations/rates stay **zero**. No eligible observations/zero denominators produce
**null** with a reason, never zero or an invented timestamp. Future/negative duration
endpoints are excluded. The UI distinguishes loading, no activity, unavailable
measurements and failed requests.

Resolution validation requires one valid creation event, no tied status timestamps,
known non-no-op status transitions, a continuous `from → to` chain beginning at open,
chronological timestamps after ticket creation and before observation, and a final
state matching the current ticket. Currently reopened/never-resolved tickets are not
samples. Resolved/closed rows lacking adequate history are counted in
`resolution_history_excluded`. No backfill modifies legacy tickets. Closing after a
reopen without a new resolution is excluded. Raw database writers can still corrupt
history; this validation does not make activity records tamper-proof.

## UI and accessibility

The page reuses AppShell, workspace permissions and existing cream/green/dark tokens.
Workspace settings links to detailed analytics; unrelated pages are retained.
[Recharts 3.10.1](https://github.com/recharts/recharts) supplies responsive, keyboard
accessible trend charts. Native labeled bar distributions include counts as text;
trend charts provide expandable daily data tables. Date fields/buttons are keyboard
operable; cards explain units and denominators. There is no polling or Redis cache.
An obsolete request cannot overwrite the selected range. Refresh is explicit through
Apply range or Retry analytics.

## Query performance and verification

Queries aggregate in PostgreSQL rather than fetching tickets/events into Python.
Responses contain bounded groups and date buckets. Existing ticket/document/history
indexes support tenant and event joins. Migration **0010** adds workspace/created_at
indexes for workflow executions and response drafts: their prior workspace/ticket/date
indexes cannot directly use the date suffix without a ticket predicate. It also adds
nullable job correlation IDs without rewriting historical records. No materialized
view, separate database, infrastructure service or caching layer was introduced.

`tests/test_analytics.py::test_representative_query_measurements` seeds **20,000 tickets
and 40,000 activity rows across two isolated tenants**, measures five real in-process
HTTP overview requests for 10,000 tickets and runs `EXPLAIN (ANALYZE, BUFFERS)` on the
resolution query. `.cache/verification/analytics-performance.json` records the exact
latest values. See PROJECT_STATUS for measured timings. This is a warm local synthetic
workload, not a public production SLA or a before/after performance improvement claim.

Run the full backend and isolated browser commands in WORKER_OPERATIONS.md. Focused
browser verification uses `python scripts/test_browser.py tests/analytics.spec.ts`
after a production build. Tests use disposable marked PostgreSQL databases and
synthetic fixtures; benchmark rows never enter the development database. Existing
workflow/job/provider regression coverage remains required. Live Gemini remains off.

Known limits: no historical state snapshots, deleted-upload history, lifetime job
attempt ledger, agent productivity, working-hour/SLA calendars, percentile latency
service, long-term log storage, export, analytics cache or AI narrative. Step 13 and
the future recruiter demo are not implemented.
