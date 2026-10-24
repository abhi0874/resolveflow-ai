# Disaster recovery runbook — Step 19C

**Local backup verification is distinct from off-host and production DR verification.**
The current implementation restores only into isolated targets automatically. It
never overwrites development or starts workers after recovery. Keep the original
source available for comparison until an explicit cutover is approved.

## Step 19C.1 credential readiness

On 2026-10-24 the user confirmed that an independent credential recovery copy is
**not yet secured** and requested scheduling remain inactive. No automatic schedule
was installed or activated. The original private credential remains unchanged.
Follow the protected import/external-device checklist in
[BACKUP_OPERATIONS.md](BACKUP_OPERATIONS.md#step-19c1--credential-recovery-gate-scheduling-remains-inactive).
Do not send the credential to the agent or place it in logs, Git, plist values or argv.

A future user confirmation allows schedule activation under the approved task; it
does not establish off-host backup storage or prove recovery on a different machine.
The existing same-Mac snapshots and same-Mac working key cannot establish protection
against total machine loss. Key custody and independent snapshot custody are distinct
requirements, both needing usable recovery procedures.

## Before any recovery

1. Stop/drain the affected project's API, dispatcher and workers. Preserve evidence,
   old files, old database and failed migration logs privately. Do not reset anything.
2. Identify the correct encrypted repository, exact snapshot ID and matching code/
   dependency release. Obtain the credential independently. Do not paste it in commands.
3. Run backup `verify`, then `restore-test --snapshot <full-id>`. Treat any missing
   component, failed checksum, unknown schema or wrong repository as a stop condition.
4. Ensure PostgreSQL/pgvector tool compatibility, disk space and a **new empty** owned
   target database plus private file root. Restore no roles/passwords automatically.
5. For an actual cutover, separately approve a maintenance/cutover plan. The automated
   CLI is a rehearsal and cleans up its temporary target. It is not a restore-over-dev tool.

## Manual recovery to a retained isolated target

A trusted administrator can use the installed restic tool directly with its documented
password-file mechanism, under umask 077, to restore the chosen full snapshot into a
new private directory. For the default repository, from the root:

```bash
umask 077
export RESTIC_REPOSITORY="$PWD/.local/encrypted-backups"
export RESTIC_PASSWORD_FILE="$PWD/.local/backup-control/repository-password"
.local/native/restic-0.19.1/restic --no-cache snapshots --tag resolveflow-v1
# Replace FULL_SNAPSHOT_ID and NEW_PRIVATE_DIRECTORY after review:
.local/native/restic-0.19.1/restic --no-cache restore FULL_SNAPSHOT_ID \
  --target NEW_PRIVATE_DIRECTORY --verify
```

Never display the password-file contents. The restored `bundle/` contains the dump,
manifest, referenced documents, immutable classifier artifacts and optional embedding
manifest. Verify component hashes against the manifest before using it. Do not treat
unknown dumps as harmless: restoring trusted PostgreSQL dumps executes database DDL.

Provision a new ownership-marked empty database (not resolveflow_dev), and use matching
`pg_restore --no-owner --no-privileges --exit-on-error --single-transaction` with a private
libpq password file. No `--clean`, no restore over live tables. The automated
`restore-test` implementation in `scripts/backups.py` is the exact tested reference for
creation, ownership checks, manifest/table verification and scoped cleanup.

Validate all table counts/hashes, migration revision, metadata comparison and pgvector.
Point a test-only application at the new document/classifier roots; reprovision the
exact pinned embedding model from its manifest. No cache backup is claimed. Matching
source/dependencies must be available separately; uncommitted source is not contained
in the encrypted data bundle. Validate authenticated document downloads, tenant denial,
retrieval and checkpoint/approval continuity with synthetic data before cutover.

## Worker and identity quarantine

Do not restore old Valkey/AOF queues into the recovered environment. Create a separately
owned empty broker/queue namespace; keep dispatcher and workers stopped. PostgreSQL
contains authoritative workflow jobs, email intents, revisions and checkpoint state.

Review queued/running/cancelled jobs, attempt counters, leases and exact approvals.
Reconcile possible external effects before allowing retries. Never reset attempt
counters, synthesize approvals or re-generate a draft that already has a saved decision.
The existing dispatcher can republish eligible jobs with new delivery identifiers only
**after** recovery validation and an explicit operator decision. Normal worker duplicate
checks and exact-draft approval remain enforced; this is not exactly-once side effects.

Restored auth sessions and old verification/recovery/invitation tokens may no longer be
safe. Before real-user cutover, explicitly revoke old sessions and outstanding identity
links/invitations through an approved scoped operation, then issue fresh verification
or recovery. Keep email delivery disabled during rehearsal. Do not start the dispatcher
until old pending mail is reviewed/cancelled; otherwise an old snapshot can resend mail.
Do not reuse the local invitation sink or claim its historical tokens prove ownership.

## Failure scenarios

| Failure | Recovery procedure and limit |
| --- | --- |
| Accidental database deletion | Restore verified snapshot into a new DB; validate documents/checkpoints/permissions, then separately approve cutover. Changes after snapshot are lost without WAL/PITR. |
| Database corruption | Preserve original, run integrity checks and isolated restore of a known-good point. A successful dump does not prove prior business data was correct. |
| Lost uploaded documents | Restore the matching bundle, verify database keys/checksums and private workspace paths. Do not mix unrelated database/file snapshots or guessed files. |
| Failed migration | Preserve failed target; restore pre-migration snapshot with its matching code revision, rehearse intended migration on that copy. No automatic downgrade or overwrite. |
| Interrupted backup | Last successful snapshot remains; inspect full integrity and incomplete private staging. Do not count an interrupted run as success; retry only after ownership checks. |
| Worker failure/recovery | Restore authoritative DB/checkpoints first, then fresh broker and reviewed reconciliation. No automatic workflow/SMTP resume. |
| MacBook lost/destroyed | **Not protected by same-Mac storage.** Requires independently stored encrypted snapshots, an independent usable key and verified recovery hardware/software. Not verified here. |
| Missing encryption credential | Recover another authorized restic key/password from independent custody. If none exists, ciphertext is unrecoverable. No bypass or reset recovers the old repository. |
| Destination unavailable/full | Fail and report stale/failed backup; keep prior recovery points. Restore availability does not follow from an old cached status. Reconnect approved media/check capacity. |

## RPO and RTO

RPO is the age of the latest successful recoverable snapshot, not the configured
interval alone. The daily 03:00 template is an aspirational local cadence; it is not
activated by generation, cannot run while powered off, and fails if writers remain
active. No guaranteed RPO exists. Status reports actual age and defaults to stale at
26 hours. A quiesced snapshot has no loss of records committed at that captured point;
later writes are outside it.

RTO includes detection, key retrieval, hardware/dependency provisioning, restore,
validation and deliberate cutover. CLI timings measure local data restore/checks only.
The synthetic workflow drill additionally measures retrieval/approval/resume verification.
Actual values are recorded in PROJECT_STATUS.md and ignored verification reports;
small local measurements are not a production SLA. Existing synthetic tests target
under 120 seconds for their small dataset, not for an arbitrary customer database.

Production gates still include independent/off-host redundancy, tested key custody,
scheduled operations with alert ownership, retention/deletion/privacy policies, trusted
runtime roles, capacity tests, WAL archiving/PITR where required, monitored backup
freshness and periodic recovery on another host. No cloud storage or enterprise
infrastructure was purchased/configured to claim these complete.
