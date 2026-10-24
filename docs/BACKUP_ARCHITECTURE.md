# Backup architecture — Step 19C

This is an **offline local recovery foundation**, not a production DR certification.
A repository on the same Mac protects against some logical errors; it does not protect
against loss of that Mac. Independent storage and independent key recovery remain gates.
Actual executed results are in PROJECT_STATUS.md.

## Reuse and technology

The supported `apps/api/scripts/backups.py` CLI reuses the ownership-checked local
PostgreSQL infrastructure, existing migrations, LocalFileStorage and the existing
synthetic workflow recovery drill. New focused modules live in `resolveflow/backups/`.
The older Step 19A/19B.1 private dumps remain untouched; they are not imported into
retention or replaced. No runtime API, business model or migration is changed.

PostgreSQL `pg_dump` custom format and `pg_restore` must match the server major version.
The installed PostgreSQL 18 tools are used by default. The service checks versions,
connectivity, database ownership, code migration head, free space and command results.
Credentials use a temporary private libpq password file, not command arguments.

Restic **0.19.1**, BSD-2-Clause, provides authenticated encryption, deduplication,
repository locks, checks and retention. The installer obtains the official release,
checks its SHA-256 against the official release checksums over certificate-verified
HTTPS, and retains its license. No custom cryptography, global package, paid service
or Python dependency was added. Existing TLS verification is never disabled.

References checked for this implementation:
- [PostgreSQL 18 pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html)
- [Restic design/encryption](https://restic.readthedocs.io/en/stable/100_references.html)
- [Restic key management](https://restic.readthedocs.io/en/stable/070_encryption.html)
- [Restic integrity checks](https://restic.readthedocs.io/en/stable/045_working_with_repos.html)
- [Restic restore](https://restic.readthedocs.io/en/stable/050_restore.html)
- [Restic retention](https://restic.readthedocs.io/en/stable/060_forget.html)
- [Restic license](https://github.com/restic/restic/blob/v0.19.1/LICENSE)

## Protected state

| Resource | Treatment |
| --- | --- |
| Users, workspace membership, sessions, tickets and activity | Full database dump; encrypted sensitive records, never log contents |
| Document metadata/chunks and pgvector embeddings | Full dump, foreign keys and extension metadata preserved |
| Uploaded document objects | Read only referenced workspace/key objects through LocalFileStorage; verify database size/SHA-256 before copying |
| LangGraph checkpoints, approvals/reviews, drafts and workflow jobs | Full dump, including non-public checkpoint schema; exact table fingerprints verified after restore |
| Account email outbox/audit and invitations | Database retained; no delivery/dispatcher started during restoration |
| Trained classifier versions | Only immutable `model.json` / `evaluation.json` artifacts under configured classifier root |
| Downloaded embedding weights | Excluded cache; available embedding manifest is included to reproduce exact dependencies separately |
| Valkey/RQ transport | Excluded: PostgreSQL outboxes are authoritative; transport identifiers are reconstructed only after recovery review |
| Local invitation mailbox / Mailpit | Excluded delivery sinks; old invitation/identity tokens require review/revocation before cutover, then fresh issuance |
| Source and environment configuration | Dependency-file hashes in manifest; source/Git and credential recovery are separate operator responsibilities |

No `.env`, API keys, PostgreSQL server credentials, backup password, virtualenv,
node_modules, build output, downloaded model cache or unrelated directory is backed up.
Database passwords/hashes, session hashes and private application content *are* sensitive
application data and exist inside the encrypted dump. The backup is not anonymized.
Local DB globals/role passwords are excluded by `--no-owner --no-privileges`; recreate
least-privilege roles deliberately for actual recovery. Preserve a matching source release
separately, including currently uncommitted work, before expecting recovery on another host.

## Consistency contract

1. Operator stops and drains this project's API, dispatcher, workers, document recovery
   commands and model training. PostgreSQL stays running. No unrelated service is stopped.
2. Manual creation requires `--quiesced`; configuring a scheduled window carries the
   same offline-writer requirement. Any other connection to the target database makes
   capture fail, even an idle pooled connection. The tool never kills clients.
3. A repeatable-read transaction takes bounded SHARE locks on all existing application/
   checkpoint tables, blocking row mutations while allowing pg_dump reads. One exported
   PostgreSQL snapshot is used by both the manifest and pg_dump.
4. Referenced documents are copied and compared with that snapshot's checksum/size.
   Pending, processing, deleting or indexing documents fail capture. A missing or corrupt
   object fails capture. Immutable classifier artifacts are copied within the window.
5. Archive listing and component checks finish before encryption. A UUID manifest ties
   the dump, file checksums, table counts/fingerprints, migration, extension versions,
   dependency hashes and model metadata to the same backup. No plaintext content is logged.
6. Database locks release in all normal failure paths. Restic stores the bundle; a complete
   repository data check is required before reporting backup success. A successful backup
   is still distinct from a successful isolated database restore.

This does not claim an online cross-system atomic snapshot. SHARE locks alone cannot
stop an independent process modifying files or creating new schema objects; stopping
all writers is a required operating contract. Existing filesystem write protection is
reused; symlinks and traversal paths are rejected. Read-only backup does not attempt to
repair incomplete journals or guess missing content. Run documented document recovery
before retrying, during a separate controlled operation.

## Encryption and boundaries

Default state `.local/backup-control/` and repository `.local/encrypted-backups/` are
separate, owner-only, Git-ignored directories. The key is outside the encrypted payload.
Private credential/config/state files are mode 0600; directories are 0700. Restic may
mark immutable pack files read-only. Repository identity is pinned in private config;
a password alone cannot silently select a replacement repository.

Subprocess environments contain only required tool settings; arbitrary inherited restic
backend/password options are not accepted. CLI output exposes operation categories,
timestamps, snapshot IDs, sizes and counts, not tool stderr or database URLs. Operations
share a nonblocking filesystem lock plus restic's own repository locks. Tool deadlines
bound hung operations; errors return nonzero. Local same-user compromise can still read
the key; encryption at rest is not protection against a fully compromised active host.

Plaintext staging exists briefly in a private control-directory child. Normal completion
or exceptions remove only that temporary child. Hard power loss/SIGKILL can leave it;
status reports incomplete stage counts. SSD deletion is not secure erasure. FileVault
and host security remain operator responsibilities. No generic cleanup command recursively
deletes configured roots or earlier backup folders.

## Destination and retention

The wrapper accepts explicit absolute filesystem destinations. An approved separately
mounted physical disk can use the same interface; remote URLs/providers are deliberately
not configured in this step. A directory on the same disk is still local. Off-host
verification needs an actual independent copy, key recovery and restore on another host.
Restic supports additional backends, but their credentials, network handling and approval
must be assessed before extending this local wrapper.

Defaults: retain 7 daily, 4 weekly, 3 monthly and at least the latest 2 snapshots.
Counts are configurable positive bounded values, not a guarantee of elapsed-day coverage.
Retention is tag-scoped to this initialized repository. It runs a full integrity check
and requires the latest snapshot to have passed this CLI's isolated restore test before
any forget/prune operation. Dry-run is the default; applying is explicit. Previous
Step 19A/19B.1 backups are outside this repository and never selected. Unattended pruning
is intentionally not enabled. Disk-space preflight, status size/age and deliberate
retention provide growth controls; an operator must monitor capacity.
