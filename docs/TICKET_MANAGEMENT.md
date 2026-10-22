# Ticket management — Step 5

Implemented locally on 2026-10-19. The ticket inbox uses real authenticated
Next.js → FastAPI → PostgreSQL requests. No AI inference, customer messaging,
uploads, workers, or paid services are involved.

## Architecture and data

The existing Ticket model is extended by additive Alembic revision **0004**.
Original revisions are unchanged. Existing tickets retain their data, start at
version 1 and remain unassigned.

- `api/v1/tickets.py`: HTTP contracts and authentication/authorization boundaries.
- `schemas/tickets.py`: strict request, response and pagination schemas.
- `services/tickets.py`: assignment validation, transactional changes, notes and events.
- `db/ticket_queries.py`: scoped SQL search, filtering, pagination and history.
- `components/tickets/`: protected shell, inbox, forms, detail and history views.

Tickets retain UUID, workspace, title, description, status, priority, category,
created_at and updated_at. New fields are nullable assigned_user_id and positive
integer version. A composite FK links (workspace_id, assigned_user_id) to a
membership in that exact workspace. A composite unique key on (workspace_id,id)
allows notes and activity to reference the ticket's tenant consistently.

`ticket_notes` stores UUID, workspace_id, ticket_id, author_id, body and created_at.
`ticket_activities` stores UUID, workspace_id, ticket_id, actor_id, action,
structured JSON details and created_at. Composite ticket FKs reject mismatched
workspaces; author/actor FKs preserve identity references. Delete restrictions
protect referenced history. API routes never delete tickets, notes or events.

Indexes support existing workspace/created and workspace/status/created reads,
workspace/updated/id sorting, workspace/assignee lookups and each history's
workspace/ticket/created/id order. Category/priority do not each get speculative
indexes. Reassess plans with realistic workloads before adding more.

## Roles and lifecycle

All roles below must be current members of the requested workspace and active
authenticated users.

| Operation | Owner/Admin | Support agent | Viewer |
| --- | --- | --- | --- |
| Read tickets, notes, history and eligible assignees | Yes | Yes | Yes |
| Create ticket | Yes | Yes, medium priority and unassigned | No |
| Edit title, description, category or status | Any workspace ticket | Unassigned or assigned to that agent | No |
| Change priority or assignment | Yes | No | No |
| Add internal note | Any workspace ticket | Any workspace ticket | No |

Support agents cannot include priority/assignment fields in PATCH requests,
even if requesting the current value. They may supply default medium/unassigned
values on creation. Notes permit collaboration on teammates' tickets without
granting edit access. Viewers are trusted internal workspace members and can read
internal notes; no external/customer role or customer-facing endpoint exists.

Statuses are open, in_progress, waiting_for_approval, resolved and closed.
Any permitted editor may move between these values, including reopening a closed
ticket. Waiting for approval is currently a **manual organizational status**;
it does not create, approve or send an AI draft. Closed tickets remain searchable
with their complete history. No permanent delete or additional archive mechanism
is needed for this step.

Priorities are low, medium, high and urgent. Categories are manually entered,
case-sensitive exact-filter labels. No classification or recommendation is simulated.

## Assignment and transaction rules

Eligible assignees are active Owner, Admin or Support Agent members of the same
workspace. Viewers, inactive users and outsiders are rejected with generic 422.
Null means unassigned. The server rechecks targets during each assignment write;
a dropdown or supplied UUID is never trusted.

Removing a member or demoting them to Viewer unassigns their tickets in the same
transaction, bumps versions and records assignment_changed events with reason
membership_changed. Existing notes/activity retain the author. Account deactivation
has no UI in this phase; an assignment to an account deactivated directly in the
database remains visible as unavailable until an owner/admin reassigns it.

Every ticket and membership mutation first locks the workspace row and re-reads
the acting membership, so concurrent assignment, membership removal and demotion
cannot bypass policy. Ticket changes and their events commit atomically. Exceptions
roll back the request session. This deliberately simple workspace-level
serialization limits write concurrency; evaluate finer locks under production load.

PATCH requires expected_version. A mismatch yields 409 with no changes/events;
the UI preserves the form and offers Refresh ticket. Successful material edits,
notes and automatic unassignment increment version. No-op edits do not add events.
The UI prevents repeat submissions while requests/navigation are pending. This
is not a durable idempotency guarantee if a network response is lost after commit.

## API

All paths are relative to `/api/v1/workspaces/{workspace_id}/tickets`.
Read routes require authentication and membership. Writes also require the
existing exact Origin, JSON and synchronizer-CSRF checks.

| Method and suffix | Contract |
| --- | --- |
| POST empty suffix | title, optional description/category/priority/assigned_user_id; 201 ticket |
| GET empty suffix | Search/filter query below; 200 paginated tickets |
| GET `/assignees` | Current active eligible members: user_id, email, role |
| GET `/{ticket_id}` | 200 ticket with version |
| PATCH `/{ticket_id}` | expected_version plus at least one editable field; 200 ticket |
| GET `/{ticket_id}/notes` | Paginated notes with author email and timestamp |
| POST `/{ticket_id}/notes` | body; 201 note and atomic activity event |
| GET `/{ticket_id}/activities` | Paginated events with actor email and timestamp |

Every ticket lookup includes workspace_id **and** ticket_id. Nonmembers,
nonexistent workspaces and foreign/missing tickets receive 404. Insufficient roles
receive 403; absent/expired sessions receive 401. Safe validation errors are 422;
stale edits are 409. No response contains password hashes or session credentials.
No-store and existing security middleware also cover nested ticket routes.

Title: 1–200 nonblank characters. Description: up to 8,000 characters.
Category: null or 1–100 nonblank characters. Note: 1–4,000 nonblank characters.
NUL characters, unexpected fields, invalid enums and invalid UUIDs are rejected.
Both servers retain the 16 KiB request-body cap: multibyte text can reach this
limit before the character limit and receive 413. React renders text literally;
no HTML/Markdown execution or customer delivery occurs.

### Search, sorting and pagination

- `search`: up to 200 characters, case-insensitive literal substring of title
  or description. SQL parameters bind values and escape LIKE wildcards.
- `status`, `priority`, `category`: exact filters.
- `assignee`: eligible/member UUID filter or `unassigned`. Results always remain
  tenant-scoped regardless of the supplied UUID.
- `sort`: created_at (default) or updated_at.
- `direction`: desc (default) or asc.
- `page`: 1–10,000; `page_size`: 1–100, default 25.

Notes/activity accept only page/page_size, newest first. Responses include items,
total, page, page_size and pages (zero for no results). SQL COUNT and LIMIT/OFFSET
avoid materializing the whole result set. UUID is the stable secondary ordering
key. Concurrent inserts/updates can shift offset pages; this is not snapshot
pagination. Substring search, count and deep offsets need workload measurement
and possibly indexed search/keyset pagination at larger scale.

The Next.js proxy only permits ticket query strings on GET collection/history
routes, bounds query length, rejects duplicate/unknown query keys, and continues
to use the fixed server-only backend origin. FastAPI validates query values and
rejects unexpected keys independently.

## Notes and activity

Internal notes are immutable through the current API. History records created,
updated, status_changed, priority_changed, assignment_changed and note_added.
Field edits record names of changed fields, not copies of customer content.
Status/priority/assignment changes record old/new values; note events reference
the note UUID without duplicating its body. No-op edits are omitted.

Events are appended by application commands. There are no ordinary event-edit,
event-delete, note-edit or note-delete endpoints. This is **application-level
append-only history**, not a tamper-proof store: the database owner can still use
SQL to modify records. Separate least-privilege runtime roles, database-enforced
immutability, retention/export and stronger audit guarantees are future hardening.
Historical events are not fabricated for tickets created before revision 0004.

## Frontend and verification

`/app/tickets?workspace=UUID` provides the inbox, creation form, title/description
search, all filters, stable sorting and pagination.
`/app/tickets/{ticketId}?workspace=UUID` provides details, edits, properties,
notes and paginated history. The existing workspace overview links to the inbox.
Workspace selection is resolved against the current user's authorized list before
rendering the shell; all client requests independently enforce backend permissions.

The interface reuses existing cream/green and system-dark tokens. Tables scroll
within their container on mobile; forms use explicit labels, native controls,
focus indicators, pending guards, loading placeholders, empty/error states and
read-only role views. All visible controls make real changes or navigate.

From repository root:

```bash
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/local_db.py start)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run alembic upgrade head)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/local_db.py test)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run ruff check .)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run ruff format --check .)
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run build
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/test_browser.py)
```

Database and browser suites use newly created marked databases and narrowly scoped
cleanup. Production build and installed Google Chrome are required for browser
checks. Never downgrade the development database to test rollback: downgrade 0004
removes this phase's notes/activity/assignment data. Migration rollback tests run
only on disposable databases.

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for actual final results.
Existing authentication and dependency limitations remain in
[AUTHENTICATION.md](AUTHENTICATION.md). AI, email delivery, notification workers,
bulk actions, analytics and public deployment remain unimplemented. Step 6 document
management is now described in [KNOWLEDGE_BASE.md](KNOWLEDGE_BASE.md).

## Step 7 category suggestions

Editable tickets now include a local ML classification section. Prediction reads
stored title/description and leaves category/history untouched. Only manual
acceptance calls the existing PATCH with the prediction's ticket_version, recording
an updated/category event. Dismissal and uncertain results do not write. Legacy
category text stays valid. See [ML_CLASSIFICATION.md](ML_CLASSIFICATION.md) for
permissions, confidence limits, training and actual evaluation evidence.
