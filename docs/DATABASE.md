# Database foundation — Steps 3 and 4

## Step 19C — supported encrypted backup operations

The existing 0012 development schema is unchanged. `apps/api/scripts/backups.py`
now performs ownership-validated offline backups with matching PostgreSQL tools,
exported snapshots, referenced private document objects, manifests and encrypted
restic storage. Local development capture/restoration was verified without changing
source record fingerprints. Earlier private Step 19A/19B.1 dumps remain intact.

Default encrypted repository: `.local/encrypted-backups/`; private control/credential
files: `.local/backup-control/`. These are separate and Git-ignored. Do not copy the
credential into a snapshot; arrange independent secure key custody manually.
Restore tests create and remove only marked disposable databases, verify pgvector,
revision/head, schema and every table fingerprint. They never overwrite development
or resume queued work. Full workflow/document recovery has synthetic coverage.

Use [BACKUP_OPERATIONS.md](BACKUP_OPERATIONS.md) for the manual/scheduled commands,
status, integrity, restore-test and retention preview. The schedule template is not
active; off-host storage/PITR are not implemented or verified. Recovery scenarios and
operator-controlled cutover are in [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md).
The older sections below preserve historical evidence, not today's backup command.

## Step 19B.1 — current development revision 0012

On 2026-10-24, confirmed the owned development database `resolveflow_dev` on
`127.0.0.1:55433` and its project data directory, then safely upgraded **0011 → 0012**.
The code has one head, 0012. The new user verification/address/source/credential
metadata and `identity_emails` / `identity_audit` schema match SQLAlchemy metadata;
Alembic reported no pending upgrade operations. No existing migration was rewritten.

Fresh private backup: **`.local/backups/step19b1-20261024T111834Z/resolveflow_dev.dump`**.
The directory includes private table/file manifests, configured file/model copies,
restore verification and migration verification markers. Archive SHA-256 and Git
exclusion passed; directories are 0700 and files 0600. Restore to an owned empty
disposable database, fingerprint comparison and migration rehearsal all passed
before changing development. The backup is local, not encrypted/off-host/scheduled.

All **22 original tables / 14 rows** retained their original-column fingerprints
through migration, except the intentional revision update. The upgrade only adds
columns/tables/constraints/indexes; no original record reset/deletion occurred.
There were no pre-existing users. Subsequent actual frontend verification/recovery
created and retained one synthetic account and owner workspace plus expected
identity/audit/session/rate-limit records. Password reset preserved membership.
This does not imply populated production-data rollout has been tested.

Migration ran as the application database owner in a transaction with bounded lock
and statement timeouts. Development readiness and real checkpoint access passed.
Fresh backend migration/security regressions passed; results and service checks
are recorded in [PROJECT_STATUS.md](PROJECT_STATUS.md#step-19b1--protected-development-migration-and-real-local-email-flows).
The private helpers `.cache/verification/step19b1_database.py` and
`step19b1_startup.py` are one-off audit evidence, not new supported infrastructure.
Do not rerun the migration helper: it intentionally requires source revision 0011.

For recovery, verify the archive hash and restore into a **new owned empty database**
using the existing restoration precautions below. Never restore over development
or use downgrade as an automatic rollback: 0012 downgrade deletes new identity,
audit and proof data. The retained pre-migration backup predates the synthetic
verification account and is not a backup of later writes.

## Step 19A — development migration and recovery verification

Verification started 2026-10-23 (Asia/Kolkata). The historical foundation sections
below retain their original counts; current test evidence is in
[PROJECT_STATUS.md](PROJECT_STATUS.md).

- Confirmed `DATABASE_URL` exactly matched the private project marker, database
  `resolveflow_dev` on `127.0.0.1:55433`, and PostgreSQL's actual data directory
  matched this checkout's `data/local/postgresql18`. No other development DB
  sessions were present before backup or migration. No unrelated service changed.
- Alembic had one linear history from 0001 through 0010, with one expected head,
  **0011**. Reviewed 0011's operations: nullable `users.email_verified_at`, new
  `workspace_invitations`, role/expiry checks, three foreign keys, unique token
  hash, UUID primary key and workspace/expiry index. No existing-record update,
  table drop or data reset occurs in the upgrade.
- Created a custom-format full database dump, including the checkpoint schema,
  at `.local/backups/step19a-20261023T182455Z/resolveflow_dev.dump`. The backup
  folder also contains copies of existing configured private document/model/mailbox
  roots, a private file/table hash manifest and verification markers. Missing roots
  are recorded as absent. No `.env` or Gemini credential was copied or changed.
- Verified Git exclusion, directory mode **0700**, file mode **0600**, archive
  SHA-256 and copied-file hashes. The archive contains sensitive database state;
  keep it local/private and do not attach it to issues or commit it. It is not an
  encrypted off-host or scheduled backup.
- Restored the archive into a freshly created ownership-marked disposable database,
  compared every original table's row count and SHA-256 fingerprint, rehearsed
  upgrade to 0011 and ran Alembic's metadata comparison. All passed. Removed only
  that verified owned restore database afterward. The retained backup was not deleted.
- Applied 0011 transactionally as the configured development owner, with a 5-second
  lock timeout and 60-second statement timeout. `alembic current` reports
  **0011 (head)** and `alembic check` reports **No new upgrade operations detected**.
  Verified the new constraints/indexes and empty invitation table; no legacy account
  was marked verified. Downgrade removes the new table/column and therefore loses
  invitation/verification state; it was not run on development data.
- All original data fingerprints still match after migration and startup checks,
  excluding the intentionally changed Alembic revision. The source had **21 tables
  and 14 rows**, consisting of revision/checkpoint metadata, two anonymous sessions
  and one rate-limit row. It had **no users, tickets, documents, embeddings or
  workflow executions**. Preservation of populated business records is demonstrated
  by the fresh isolated migration/restore tests, not by claiming populated local data.
- The real development checkpoint schema is accessible and version-compatible.
  API readiness, local broker, worker and dispatcher health passed. Tests use owned
  disposable databases and deterministic AI; they do not populate development data.

The one-off audit helpers and logs are ignored local artifacts under
`.cache/verification/step19a_database.py`, `.cache/verification/step19a_startup.py`
and `.cache/verification/step19a/`. They are evidence for this checkout, not new
supported infrastructure. Do not rerun the pre-0011 helper against an upgraded
database; it intentionally requires revision 0010.

For recovery, preserve the archive and manifest; verify the archive hash first.
Restore into a **new empty, ownership-verified local database**, never over
`resolveflow_dev`, using the matching PostgreSQL binaries and credentials in a
child environment (not command arguments or logs). The verified rehearsal used
`pg_restore --no-owner --no-privileges --exit-on-error --single-transaction
--dbname <owned-empty-target> <archive>`. Compare original table/file fingerprints,
apply the desired migration to the restored copy, verify model/document references
and checkpoint access, then review any cutover separately. The original dump
contains ownership/ACL metadata; the rehearsal intentionally did not apply it.
No restore-over-development, downgrade or automatic cutover is authorized here.

Operational backup scheduling, encryption/key management, independent retention,
off-host recovery and business-approved RPO/RTO remain commercial release gates.

## Historical foundation

Verified 2026-10-19 on Apple Silicon macOS. PostgreSQL **18.6**, pgvector **0.8.6**,
SQLAlchemy **2.0.55**, Alembic **1.20.0**, psycopg **3.3.6**, Python **3.14.6**.
No Docker, cloud database, Redis, billing, or AI provider is required.

## Installation on this Mac

PostgreSQL, Postgres.app, and Homebrew were absent from the inspected PATH and
standard installation locations. The official [Postgres.app download](https://postgresapp.com/downloads.html)
(version 2.9.6, PostgreSQL 18 bundle) supplies native arm64 binaries and pgvector.
The bundle is installed **inside this checkout**, not in `/Applications`:

```text
.local/native/Postgres.app/Contents/Versions/18/bin/
.local/database.json                 # generated admin/dev passwords, mode 0600
apps/api/.env                        # server-only development URL, mode 0600
data/local/postgresql18/             # dedicated cluster, mode 0700
```

All these paths are ignored by Git. The downloaded installer is under `.cache/`.
The final copied bundle passed `codesign --verify --deep --strict`; the original
installer app passed Apple's notarization assessment. No quarantine or signature
checks were disabled. No administrator privileges or system service installation
were needed. The agent environment required permission to mount the image and
bind/connect to local sockets; normal local terminal use does not require sudo.

For another Mac without PostgreSQL, these reproduce the verified bundle install
from the repository root. First check for an existing usable installation; do not
overwrite a functioning bundle. The copy destination must not already exist.

```bash
mkdir -p .cache/postgres-download .local/native
curl --fail --location --retry 2 \
  https://github.com/PostgresApp/PostgresApp/releases/download/v2.9.6/Postgres-2.9.6-18.dmg \
  -o .cache/postgres-download/Postgres-2.9.6-18.dmg
hdiutil attach -readonly -nobrowse \
  -mountpoint /private/tmp/resolveflow-postgres-installer \
  .cache/postgres-download/Postgres-2.9.6-18.dmg
codesign --verify --deep --strict /private/tmp/resolveflow-postgres-installer/Postgres.app
cp -R /private/tmp/resolveflow-postgres-installer/Postgres.app .local/native/
codesign --verify --deep --strict .local/native/Postgres.app
hdiutil detach /private/tmp/resolveflow-postgres-installer
```

macOS reports these hdiutil mount/eject commands deprecated, but they worked on
this machine. Prefer its recommended `diskutil image attach` / `diskutil eject`
equivalents when adapting to a newer macOS. The helper below targets this verified
project-local bundle. Other native installations can run the same application
and migrations using `DATABASE_URL` and their own service manager; the helper is
not a general-purpose system PostgreSQL manager.

## Start, migrate, inspect, stop

Run from `apps/api` (the first command assumes the repository root):

```bash
cd apps/api
export UV_CACHE_DIR=../../.cache/uv
uv sync --locked
uv run python scripts/local_db.py setup
uv run alembic upgrade head
uv run alembic current
uv run alembic check
uv run python scripts/local_db.py status
```

`setup` initializes only a new project cluster, generates random credentials,
creates `resolveflow_dev`, enables vector, and writes `DATABASE_URL` only when
absent. It refuses an existing unmarked data directory. Existing environment
values and database contents are preserved. Re-running setup is supported;
migrations are always an explicit separate command. Do not copy the placeholder
URL from `.env.example` over the generated `.env`.

For subsequent sessions:

```bash
uv run python scripts/local_db.py start
uv run alembic upgrade head
uv run --locked uvicorn resolveflow.main:app --app-dir src --host 127.0.0.1 --port 8000 --no-proxy-headers --reload
```

Stop the API with Ctrl+C. These commands inspect or stop only this project cluster:

```bash
uv run python scripts/local_db.py status
uv run python scripts/local_db.py psql
uv run python scripts/local_db.py stop
```

The cluster listens on **127.0.0.1:55433** (moved from 55432 on 2026-10-21 to
avoid the unrelated DocRAG PostgreSQL service), has no Unix socket listener, and uses
SCRAM password authentication. No login launch agent is installed; restart it
explicitly after reboot. `stop` preserves all data. Never delete the data directory
to fix a startup or migration failure. Keep `.local/database.json` with this local
cluster; it contains credentials, not a data backup. Moving the checkout requires
manual review of the stored absolute cluster path; the helper refuses a mismatch.

## Configuration and session lifecycle

`DATABASE_URL` is a server-only PostgreSQL URL, normalized to the psycopg dialect:

```dotenv
DATABASE_URL=postgresql+psycopg://resolveflow_dev:CHANGE_ME@127.0.0.1:55433/resolveflow_dev
RESOLVEFLOW_DB_POOL_SIZE=5
RESOLVEFLOW_DB_MAX_OVERFLOW=5
RESOLVEFLOW_DB_POOL_TIMEOUT=3
RESOLVEFLOW_DB_CONNECT_TIMEOUT=3
RESOLVEFLOW_DB_STATEMENT_TIMEOUT_MS=5000
```

Use URL-encoded username/password components when configuring your own URL.
Process environment overrides `apps/api/.env`. Pydantic validates driver, username,
host, database and port, hides the URL in settings representations, and reports
invalid configuration without echoing the submitted value. Missing configuration
is allowed so isolated unit tests and process liveness work; `/ready` returns 503.
Pool/time-limit values are bounded positive integers (overflow may be zero).

The engine is created during FastAPI lifespan; neither import nor engine creation
opens a network connection. Each synchronous database request gets its own session.
Callers explicitly commit; exceptions roll back, and closing discards uncommitted
work. Shutdown disposes the pool. Pool pre-ping detects stale connections, recycle
is 1800 seconds, and configured connect/checkout/statement timeouts bound common
failure paths. These are not an absolute HTTP deadline across DNS/TLS failures.
SQLAlchemy parameter logging is hidden. Public errors expose only safe codes:
`database_unavailable` (503), `database_conflict` (409), or `database_error` (500).

## Models and integrity

| Table | Fields and rules |
| --- | --- |
| `users` | UUID PK, normalized unique email, encoded password hash, active/inactive/suspended account status, created/updated timestamps |
| `workspaces` | UUID PK, nonblank name, unique lowercase hyphenated slug, created/updated timestamps |
| `workspace_memberships` | UUID PK, required user/workspace FKs, unique `(workspace_id,user_id)`, owner/admin/support_agent/viewer role, created timestamp |
| `tickets` | UUID PK, required workspace FK, nonblank title, text description, status, priority, optional nonblank category, created/updated timestamps |

All timestamps are PostgreSQL `TIMESTAMP WITH TIME ZONE`. UUIDs have Python and
server defaults; creation timestamps have server defaults. ORM updates set
`updated_at` using PostgreSQL `now()`; raw SQL writers must update it explicitly.
`now()` is transaction time, so several writes in one transaction may share it.

Statuses are `open`, `in_progress`, `waiting_for_approval`, `resolved`, `closed`.
Priorities are `low`, `medium`, `high`, `urgent`. Named database CHECK constraints
protect allowed values even when writes bypass the ORM. Hash storage accepts
Argon2id/bcrypt encoded formats and rejects ordinary plaintext. This format check
is not a hashing/verification service; proper hashing and account security belong
to the implemented authentication service; see [AUTHENTICATION.md](AUTHENTICATION.md).
No accounts are seeded in development.

Foreign keys use `RESTRICT` to prevent accidental cascaded deletion. Unique email
and slug constraints create lookup indexes. The membership unique index supports
workspace membership lookups; a separate user index supports a user's memberships.
Ticket indexes `(workspace_id,created_at)` and `(workspace_id,status,created_at)`
support future workspace inbox ordering/filtering and workspace FK checks.

Workspace references establish tenant-aware storage. Step 4 enforces application
permissions on every workspace/membership route; see [AUTHORIZATION.md](AUTHORIZATION.md).
There is no database row-level security. Future resource APIs must reuse the central
access checks and scope resource queries by workspace.

## Migrations and pgvector

Alembic revision `0001` executes `CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA
public`. Revision `0002` creates exactly four core tables and their constraints and
indexes. Step 4 adds revision `0003`: `auth_sessions` (hashed credential, optional
user FK, CSRF token, creation/expiry) and `auth_rate_limits` (hashed key, count, reset
time), with expiry/user indexes. The user FK cascades sessions if an administrator
deletes a user; there is no user deletion endpoint. `alembic_version` records migration state. Static migrations contain no
imports of mutable application models. There is no startup `create_all`, automatic
migration, vector column/table, embedding pipeline, or vector index.

pgvector is not a trusted extension: initial installation requires an administrator
(or an appropriate provider mechanism). The helper uses its generated cluster-admin
role to enable vector in the dedicated dev database. Application migrations then
run as `resolveflow_dev`, which owns this database but is not a superuser and cannot
create roles/databases. The admin credential is not used by the API.
Fresh integration databases exercise extension creation through revision `0001`.
See the [official pgvector installation guidance](https://github.com/pgvector/pgvector).

The downgrade of `0002` drops the four application tables. The downgrade of `0001`
intentionally leaves the extension installed, because other objects could depend
on it. It never executes `DROP EXTENSION ... CASCADE`. Downgrades destroy application
records: automated rollback verification runs **only in a freshly created test
database**, never in development. No development reset command is provided.

For a new change, edit models, generate and review a new migration, then apply it:

```bash
uv run alembic revision --autogenerate -m 'Describe the schema change'
uv run alembic upgrade head
uv run alembic check
```

Autogeneration is not a substitute for review, especially for data changes and
CHECK constraints. Do not edit applied migration semantics or run downgrades on
valuable databases without a reviewed backup/recovery plan.

## Checks

From `apps/api`, with `UV_CACHE_DIR` set as above:

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv run python scripts/local_db.py start
uv run python scripts/local_db.py test
```

Default Pytest runs **84 tests** with the real model installed, skipping **85 PostgreSQL cases**.
The helper runs all **169 tests** using the local admin credential through a child
environment variable, never a command-line argument. An explicit `--run-db` without
`TEST_DATABASE_ADMIN_URL` fails. For another local test cluster, supply a secret
`TEST_DATABASE_ADMIN_URL` targeting its `postgres` maintenance database and run
`uv run pytest --run-db`. Only loopback URLs without query overrides are accepted.
The test role needs permission to create databases and install vector. Do not use
production credentials; no hosted test database is accepted.

The fixture creates random `resolveflow_test_<uuid>` databases, marks each with a
unique ownership comment, and cleans up only names it created whose marker still
matches. Tests use transactions/savepoints, with a second disposable database for
upgrade/downgrade/reapply. No SQLite substitution, development database downgrade,
forced session termination, or wildcard database cleanup is used. An interrupted
process can leave a test database; inspect its name and ownership comment before
any manual cleanup.

Integration coverage includes connectivity, vector extension and operator, schema
and migration revision, ORM defaults/persistence/timestamps, foreign keys, required
workspace reference, memberships and email/slug uniqueness, raw-SQL CHECK
constraints, restricted deletes, explicit tenant filtering, session rollback, and
real database readiness. Metadata comparison and `alembic check` verify no drift.

With the API running:

```bash
curl -i http://127.0.0.1:8000/api/v1/health
curl -i http://127.0.0.1:8000/api/v1/ready
```

Health remains HTTP 200 independently of PostgreSQL. Ready executes `SELECT 1` and
returns HTTP 200 with `{"status":"ready","service":"resolveflow-api","database":"ok"}`
or HTTP 503 with `{"error":{"code":"database_unavailable","message":"Database is unavailable"}}`.
Readiness tests connectivity, not migration/version/extension correctness; check
those explicitly using Alembic and `status`. Live outage and pool recovery were
verified by stopping and restarting only this project's database.

## Troubleshooting and portability

- **Startup failed / port occupied:** inspect `data/local/postgresql18/server.log`
  and `lsof -nP -iTCP:55433 -sTCP:LISTEN`. Do not stop an unrelated server. The helper
  checks the connected cluster's data directory before setup changes. The port must
  agree in `scripts/local_db.py`, the ignored `.local/database.json` marker, the
  owned cluster's `postgresql.conf`, and `apps/api/.env`'s `DATABASE_URL`. Do not
  reset data or overwrite passwords to resolve a port conflict.
- **Missing bundle:** check the verified installation path above. Do not disable
  macOS signature checks to make a damaged copy work; obtain a fresh official copy.
- **Password authentication failed:** check which `DATABASE_URL` source is active.
  Setup preserves existing values, including template placeholders; reconcile your
  private `.env` locally. Do not paste credentials into logs, commits, or issues.
- **Extension unavailable:** confirm `vector.control` exists under the installation's
  `share/postgresql/extension`; install a compatible pgvector package. For permission
  failures, have the database administrator enable vector before ordinary migrations.
- **Readiness 503:** confirm URL, cluster status, credentials and pool capacity.
  Health can still be 200 by design. Malformed URLs fail settings validation at startup.
- **Migration failure:** inspect the revision and schema; do not stamp head or reset
  data to conceal divergence. Fix with a reviewed migration.
- **Helper failure:** it suppresses raw connection details to avoid credential
  leakage. Check the prerequisites, ownership marker, filesystem access, service log
  and intended command above; never remove data to bypass its guard.

The app and migrations use standard PostgreSQL/psycopg SQLAlchemy URLs. A future
hosted database can use the same code with provider-appropriate TLS settings such
as `sslmode=verify-full`, CA configuration and separately provisioned vector. Review
pool sizes per worker against server limits; use separate least-privilege runtime
and migration roles, secrets management, backup/restore and tenant authorization
before production. The local helper and privileged integration fixture are strictly
development tools. No hosted portability claim has been tested against a provider,
and nothing is deployed. Step 8 is the current completed scope.


## Step 5 schema extension

Revision 0004 adds ticket assignment/version and ticket_notes/ticket_activities.
The current schema has eight application tables plus alembic_version. Composite
FKs enforce same-workspace assignment and note/activity ownership; version checks,
history indexes and transactional application commands are described in
[TICKET_MANAGEMENT.md](TICKET_MANAGEMENT.md). Earlier counts/revisions above
describe the historical foundation. Run upgrade head; never reset development.
Downgrade 0004 discards the new feature data and is tested only on disposable DBs.
See project status for the current suite totals.

## Step 6 schema extension

Revision 0005 creates documents and document_chunks. Composite document/workspace
foreign keys, checksum uniqueness and indexed tenant queries protect consistency;
private files live outside PostgreSQL. Prior revisions and data are preserved.
The migration regression downgrades/reapplies only on disposable databases and
checks existing ticket data. Downgrading 0005 discards document metadata/chunks and
does not delete private objects: do not downgrade a populated development/production
library without an explicit backup and coordinated storage cleanup plan.

Backend document tests use fresh temporary storage; the browser harness sets its
own temporary storage root and cleans it only after stopping its servers. No test
cleanup targets development documents. See [KNOWLEDGE_BASE.md](KNOWLEDGE_BASE.md)
for the file/DB journal, tombstones and operator recovery command. Current schema
head is 0005; schema consistency is verified with `alembic check`.

## Step 7 classifier integration

No schema migration is needed: existing nullable free-text ticket.category stores
accepted canonical labels while preserving legacy/custom values. Classification
itself does not write. Acceptance uses the existing version-checked update and
category activity event. Current schema head remains 0005. Training artifacts
are local files containing synthetic-trained parameters, separate from PostgreSQL
and private documents. Test fixtures train temporary models and never train from
or modify development ticket data. See [ML_CLASSIFICATION.md](ML_CLASSIFICATION.md).


## Step 8 schema extension

Step 8 introduced schema revision 0006. Additive document indexing metadata and chunk_embeddings
preserve existing extracted content. Composite workspace/document/chunk FKs cascade
vectors on chunk deletion; vector(384), norm and content-hash checks protect stored
values. Exact pgvector search uses tenant/model B-tree filtering; no approximate index
is introduced for the measured small corpus. Upgrade/downgrade preservation and vector
constraints are tested only in disposable databases. Downgrading 0006 discards vectors
and indexing metadata, preserves documents/chunks, and requires reindexing after reapply.
See SEMANTIC_SEARCH.md for schema/query/lifecycle details. Current full suite: 169 tests.

## Step 9 response drafts

Current schema head is **0007**. The additive migration creates response_drafts,
draft_citations and draft_reviews. Composite workspace/ticket and workspace/source
foreign keys prevent invalid tenant references. Draft requests have a scoped
idempotency key and indexed budget timestamps. Review records preserve the exact
response hash, revision, actor and decision. Source deletion cascades citation
references; response/review history remains and is marked stale. No existing
business tables are reset. Downgrading 0007 removes this new history and is tested
only in disposable databases, not recommended as a development recovery command.
See RAG_PIPELINE.md for transaction, budget, authorization and freshness rules.
