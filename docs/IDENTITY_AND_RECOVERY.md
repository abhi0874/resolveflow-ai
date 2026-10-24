# Local identity and recovery hardening

**Step 19B supplement:** account verification and password recovery now use an
SMTP-capable hash-only outbox, independently of the local workspace-invitation
sink described below. See [EMAIL_DELIVERY.md](EMAIL_DELIVERY.md). Migration 0012
was safely applied to development in Step 19B.1 after a verified private backup and
isolated restore rehearsal. Actual local Mailpit verification/recovery passed.
No external mail provider or commercial delivery has been activated or verified.

2026-10-23. This is the local follow-up to the Step 18 audit, authorized by the
instruction to continue. It addresses the invitation protocol and a synthetic
restoration exercise. No external email service, deployment, real-data processing,
paid infrastructure or live Gemini request is enabled.

## Identity-bound invitations

The old `POST /workspaces/{id}/members` no longer grants membership. Authorized
legacy clients receive 409; unauthorized callers retain permission checks. Existing
member role changes and removal retain their original owner/admin protections.

| Route, under `/api/v1` | Result |
| --- | --- |
| `POST /workspaces/{id}/invitations` | Authorized owner/admin creates a pending invitation for an existing active account; 202 with safe ID/email/role/expiry, never the token |
| `GET /workspaces/{id}/invitations` | Owner/admin sees at most 50 unexpired pending invitations |
| `DELETE /workspaces/{id}/invitations/{invitation_id}` | Revoke an invitation subject to tenant and role checks; does not remove an already accepted membership |
| `POST /auth/invitations/accept` | Signed-in recipient submits `{token}` with CSRF; atomically confirms the account's address in this local delivery flow and creates membership; 201 with workspace information |

Tokens contain 32 cryptographically random bytes, are stored as SHA-256 hashes in
PostgreSQL, expire after 24 hours and can be consumed only once. They bind the
workspace, recipient user ID, exact normalized email, role and issuer. Neither a
claimed signup email nor a pending invitation grants access. Tokens travel in a
POST body, not a URL, log, invitation-list response or browser storage.

Acceptance locks the workspace, recipient and invitation, checks expiry/revocation,
current recipient email/account status and the issuer's current membership/role.
An issuer who loses the authority to grant the role cannot leave a usable grant
behind. A replacement invitation revokes previous pending tokens for that recipient
in that workspace. Concurrent acceptance produces one membership. Acceptance
revokes that recipient's previous sessions and issues a new current session in
the same transaction; other users' sessions are unaffected.

Issuance and acceptance use the existing persistent per-action auth limits (60/IP
and 10/account per 15 minutes), with at most 50 pending invitations per workspace.
This does not resolve the separately tracked shared-proxy rate-limit fairness issue.
Pending rows/local delivery files require an eventual retention policy; no scheduled
mailbox cleanup or real email delivery is introduced here.

Migration **0011** adds `users.email_verified_at` and `workspace_invitations`.
It does not delete or reset users, existing memberships, passwords, sessions, tickets
or checkpoints, and does not mark historical accounts verified. Tests explicitly
exercise upgrading legacy identity/session records and downgrading in disposable
databases. Existing membership identities must still be reviewed before a real-user
launch; grandfathering rows for data preservation is not retrospective verification.

## Delivery boundary and local usage

**Only a private local synthetic mailbox is implemented.** It lets the developer
exercise the delivery/acceptance protocol; it is not evidence of actual mailbox
ownership. The local operator can inspect every synthetic invitation. Do not use
this sink for real users or describe its `email_verified` value as an external
email-provider attestation.

`RESOLVEFLOW_INVITATION_DELIVERY` defaults to **disabled**. Opt-in `local` is allowed
only in development/test; production configuration rejects it. Both issuance and
acceptance fail closed when delivery is disabled or the runtime is production.
A future production delivery adapter, verified real-mailbox flow and associated
privacy/abuse review require separate authorization. Commercial P0-1 is therefore
only partially addressed, even though the direct-grant bypass is removed.

The local sink reuses private file storage: generated UUID paths, mode-700
directories, mode-600 files, no-follow checks and atomic file publication. Its root
must be absolute, outside public assets and separate from uploads/model roots.
Default: repository `.local/invitation-mailbox`, already ignored by Git. The API
does not expose a mailbox/token-reading endpoint. Write failure yields a safe 503
and no active invitation; a crash before DB commit can leave only an unusable
message. This is a local sink, not a durable external delivery outbox.

The initial implementation was verified in isolated resources. **Step 19A has now
applied migration 0011 to this checkout's owned development database**, after a
verified private backup and isolated restore/migration rehearsal. Private `.env`
remains unchanged. See [DATABASE.md](DATABASE.md#step-19a--development-migration-and-recovery-verification)
for backup scope and recovery precautions. On another checkout, or to confirm
the intended owned database is current, use the additive migration command:

```bash
# From apps/api, with the existing owned PostgreSQL on 55433 running.
.venv/bin/alembic upgrade head

# Opt in for this API process only; no .env overwrite and no external email.
RESOLVEFLOW_INVITATION_DELIVERY=local RESOLVEFLOW_AI_LIVE_ENABLED=false \
  .venv/bin/uvicorn resolveflow.main:app --app-dir src \
  --host 127.0.0.1 --port 8000 --no-proxy-headers

# In another terminal, from repository root, with the supported Node runtime.
NEXT_PUBLIC_APP_MODE=full API_INTERNAL_URL=http://127.0.0.1:8000 \
  NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run dev -- --webpack
```

Keep the existing dispatcher/worker startup from [WORKER_OPERATIONS.md](WORKER_OPERATIONS.md)
for workflows. They do not deliver invitations. The public demo remains separate.

For a local synthetic invitation:

1. Register separate synthetic owner and recipient accounts in separate browser
   sessions; create a workspace as owner.
2. In Team & settings, choose **Invite a registered teammate** and **Send invitation**.
   The recipient has no access yet. Owners/admins can inspect/revoke pending grants.
3. Open the generated private local mailbox file in your editor:
   `.local/invitation-mailbox/<workspace UUID without hyphens>/<invitation UUID without hyphens>`.
   Inspect the recipient field to select the intended synthetic message. Do not
   publish the mailbox, paste codes into chat, or print them in logs.
4. As the matching recipient, paste the code into **Invitation code** and choose
   **Accept invitation**. The workspace becomes available after the server checks
   and commits acceptance. A wrong account, expired/revoked/used code fails.

Disabling local delivery again prevents further issuance/acceptance; existing
accepted memberships remain governed by the regular role/removal controls.

## Synthetic restoration exercise

`apps/api/tests/test_restore.py` provisions its source and destination using the
existing ownership-marked database fixture. It refuses nonlocal/unmarked databases
and requires an empty destination. It never accepts a development database name
or restores over existing records, and never uses `pg_restore --clean`.

The drill:

1. Creates synthetic source data with real document extraction, local classifier,
   real MiniLM embeddings/pgvector, a durable job and actual LangGraph checkpoint.
2. Pauses for approval, saves the exact-draft review and quiesces all source writes.
3. Uses the installed PostgreSQL 18 `pg_dump` custom format for the entire source DB,
   including business records, outbox and checkpoint schema. Credentials are child
   environment values, not command arguments or output.
4. Copies private documents, the generated test classifier and pinned embedding
   snapshot, rejecting symlinks and comparing file hashes. Copies and dump remain
   inside an owned private temporary directory; no developer model is changed.
5. Restores to the second empty DB in one transaction and independently copies
   backed-up files/models to new restore paths. A fresh application loads the
   restored artifacts and accesses the restored checkpoint/schema without setup DDL.
6. Confirms the same saved review/draft is current, downloads the original file,
   runs real semantic search and resumes through the actual worker service.
   The generation method is replaced with an assertion failure: another call
   would fail the test. Duplicate delivery retains one job, draft and review.
7. Tests outsider tenant denial and missing/corrupted file download returning 503,
   then confirms source DB/file state is unchanged. Only owned temporary resources
   are removed. A content-free measurement report remains in ignored
   `.cache/verification/restore-drill.json`.

The local gate is **zero committed records lost at the quiesced snapshot** and
**restore plus validation under 120 seconds** for this tiny synthetic fixture.
Measured times are reported in PROJECT_STATUS; these are not business-approved
production RPO/RTO values, network recovery measurements or performance promises.

The drill invokes the real worker service after restoration; separate existing
tests cover dedicated RQ subprocesses and broker replacement. It does not certify
an off-host restore, live-write consistent file snapshots, database failover,
encrypted backup management, a production supervisor or external delivery.

## Backup ownership and commercial prerequisites

The local developer owns this drill and its ephemeral artifacts. No scheduled
backup of development or customer data is installed. For a later commercial
release, designate an operations owner and approve recovery objectives before
choosing frequency/storage. A database dump alone is insufficient: document blobs,
checkpoint/schema versions, model manifests and application revision must agree.

Keep real backups encrypted and access-restricted off the application host; include
session/password material in the sensitivity inventory. Define key custody,
retention/deletion, monitoring of backup age and periodic isolated restore drills.
Never restore over the active database as a test. Validate a new isolated target,
reconcile sessions and source integrity, then use an explicitly approved cutover;
retain the previous target for a defined rollback window. Those operational policies
and systems are requirements, not capabilities implemented by this synthetic test.

## Reproduce verification

```bash
# From apps/api; only disposable databases, private test mailboxes and fixture AI.
RESOLVEFLOW_AI_LIVE_ENABLED=false RESOLVEFLOW_AI_FREE_TIER_VERIFIED=false \
  GEMINI_API_KEY=synthetic-test-key .venv/bin/python scripts/local_db.py test

# Focused invitation and restore checks (same safe database factory).
PYTEST_ADDOPTS='tests/test_invitations.py tests/test_restore.py --tb=short' \
  RESOLVEFLOW_AI_LIVE_ENABLED=false .venv/bin/python scripts/local_db.py test
```

The browser harness configures its own private mailbox and exercises real UI
invitation acceptance. It does not require developer mailbox files. See the newest
[PROJECT_STATUS.md](PROJECT_STATUS.md) entry for final test counts. No application
assertion is replaced with direct database membership insertion in these updated
browser/authentication journeys.
