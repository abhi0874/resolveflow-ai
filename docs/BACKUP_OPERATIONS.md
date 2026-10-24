# Backup operations — local macOS

Run from the repository root unless a command says otherwise. Keep the project on
its existing database (55433); do not operate on another project's 55432 listener.
No external repository, billing, SMTP or AI call is needed.

## Step 19C.1 — credential recovery gate; scheduling remains inactive

Reviewed 2026-10-24. The user explicitly answered **“Not yet—keep scheduling
inactive”** to the independent-credential-recovery confirmation. No LaunchAgent was
installed, bootstrapped or triggered. This gate remains open; do not treat the
existing template or historical direct `scheduled` CLI execution as active automation.

The credential is currently `.local/backup-control/repository-password`, outside
the encrypted repository, owner-only (0600) in a private directory (0700). Its
contents were not displayed, printed or changed. To prepare an independent copy:

1. In your trusted password manager, manually import this file as a protected
   attachment/secure note using its local UI. Alternatively copy it to a separately
   encrypted external device through your own secure file workflow. Do not put it
   in an ordinary cloud folder, email, chat, Git, shell arguments or the plist.
2. Verify you can retrieve the saved item from another authorized device or decrypt
   the separate device without relying on this Mac. Make sure password-manager
   account recovery and any MFA recovery are themselves available independently.
3. Keep the current working credential intact. Confirm completion in chat **without
   sending the key**. A copy in another folder on this Mac is not independent recovery.

No password manager or external device was accessed by the agent. User confirmation
will be recorded as confirmation, not falsely described as an independently tested
key restore. Off-host backup data protection remains a separate unverified requirement.

The reviewed template runs once daily at **03:00 IST** (Mac timezone checked as
UTC+05:30), with exact project interpreter/CLI paths and private logs. Retention
remains 7 daily / 4 weekly / 3 monthly, with latest-two protection; no automatic
pruning is enabled. A readable launchd inventory contained no ResolveFlow/restic
job, the exact service was absent, and no user crontab was installed.

After a future affirmative confirmation, recheck conflicts, install only
`local.resolveflow.backup`, trigger one controlled launchd execution, verify its
snapshot and isolated restoration, then confirm the agent remains registered.
Actual launchd execution/access to this Documents-folder checkout is still untested;
macOS privacy permissions may need user action if launchd cannot access it. Do not
weaken filesystem/privacy settings or relocate unrelated files automatically.

Simple status commands, from the repository root:

```bash
launchctl print "gui/$(id -u)/local.resolveflow.backup"
(cd apps/api && .venv/bin/python scripts/backups.py status)
(cd apps/api && .venv/bin/python scripts/backups.py failures)
(cd apps/api && .venv/bin/python scripts/backups.py list)
(cd apps/api && .venv/bin/python scripts/backups.py verify)
```

The launchctl command currently reports the service absent. `status` distinguishes
last backup/integrity/restore timestamps; `list` identifies actual snapshots. A fresh
`verify` is an integrity check, not a new backup or restoration. Do not claim new
launchd execution/restore results until activation and testing actually occur.

SIGINT/ordinary SIGTERM interruption now records `backup_interrupted` and exits
nonzero after normal context cleanup. SIGKILL/power loss cannot be caught; inspect
incomplete staging and stale status as documented below. Eleven focused tests passed,
including encryption/isolated restoration, safe retention, missing documents,
corrupt metadata/packs, concurrency, interrupted capture cleanup, credential failures
and injected unavailable-service diagnostics. No real credential/repository was
modified for fault injection.

## Install and initialize once

```bash
(cd apps/api && .venv/bin/python scripts/install_restic.py)
(cd apps/api && .venv/bin/python scripts/backups.py init)
```

The pinned restic installer refuses replacement of an existing installation. `init`
refuses an existing state or repository directory; do not delete one to bypass that
safety check. The current checkout may already have both from Step 19C: use `status`.
Default locations:

- `.local/native/restic-0.19.1/restic`: binary, official checksums, license.
- `.local/backup-control/config.json`: private non-secret paths/identity/retention.
- `.local/backup-control/repository-password`: random private encryption credential.
- `.local/encrypted-backups/`: encrypted restic repository.

Never paste the credential into chat, logs, shell arguments or Git. Save a secure
recovery copy in your approved password manager or independent protected medium,
separate from the repository and the Mac. This independent key copy is a manual
prerequisite, **not performed or verified by Codex**. Losing all usable keys means the
backup cannot be decrypted. Do not store the only key copy inside encrypted snapshots.

`--state /absolute/private/control` selects another explicitly configured control
folder. `init --repository /absolute/approved/mounted-disk/repository` supports a
future approved independent filesystem destination. Do not run it on an unapproved
provider/mount; no independent destination was configured by this milestone.
Locations within this checkout must be Git-ignored. Paths must be absolute and
symlink-free, and source/state/repository directories must not overlap.

## Manual backup and checks

Gracefully stop this project's API, dispatcher, workers and any document/model
mutation commands first; leave PostgreSQL running. See WORKER_OPERATIONS.md. Do
not kill unrelated processes. There must be no other connection to resolveflow_dev.

From `apps/api`:

```bash
.venv/bin/python scripts/local_db.py start
RESOLVEFLOW_AI_LIVE_ENABLED=false .venv/bin/python scripts/backups.py create --quiesced
.venv/bin/python scripts/backups.py list
.venv/bin/python scripts/backups.py verify
.venv/bin/python scripts/backups.py restore-test --snapshot latest
.venv/bin/python scripts/backups.py status
.venv/bin/python scripts/backups.py failures
```

Resume ordinary project services only after the backup window closes. The tool never
changes `.env`, starts inference, stops services, or resumes workflows. `verify` reads
all encrypted repository data. `restore-test` also decrypts the bundle, validates every
component, restores into a new marked temporary PostgreSQL database/document directory,
compares every table fingerprint, checks pgvector/head/schema, and removes only its
own temporary resources. It never accepts development as a restore target.

Status includes last successful backup, failure, integrity check, restore test, age,
repository bytes, free space and incomplete stages. It exits nonzero when the backup
is older than `max_age_hours` (default 26) or no backup exists. An unavailable/invalid
repository fails nonzero with a sanitized code; it is never reported healthy from a
cached success. There is no paid monitoring or automatic external alert. Check status
after waking the machine and after scheduled maintenance windows.

## Schedule template — activation is explicit

From `apps/api`:

```bash
.venv/bin/python scripts/backups.py schedule --hour 3 --minute 0
plutil -lint ../../.local/backup-control/local.resolveflow.backup.plist
```

This generates a per-user launchd plist with absolute interpreter/script paths,
private log paths, restrictive umask and `scheduled` command. It does **not install,
bootstrap or enable** an agent. It refuses overwriting a template; review/edit your
existing private template if changing the schedule. Default is 03:00 in the Mac's
local timezone; ensure that matches your intended Asia/Kolkata maintenance window.

After explicitly approving a recurring offline window, install only this project
agent manually. From repository root:

```bash
mkdir -p "$HOME/Library/LaunchAgents"
test ! -e "$HOME/Library/LaunchAgents/local.resolveflow.backup.plist" && \
  cp .local/backup-control/local.resolveflow.backup.plist "$HOME/Library/LaunchAgents/"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/local.resolveflow.backup.plist"
```

Do not overwrite another existing agent. To stop this exact approved agent:

```bash
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/local.resolveflow.backup.plist"
```

`scheduled` runs the same capture checks; it does not magically drain applications.
If writers are active or the DB is stopped, the scheduled run fails safely and records
a failure. Configure your working habits/maintenance window accordingly. No schedules
run while the Mac is powered off. Apple documents that StartCalendarInterval jobs
missed during sleep run on wake; powered-off occurrences wait for the next scheduled
time. This is platform behavior, not a completed wake/reboot test for this agent:
[Apple timed-job guidance](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html).
A wake-triggered backup can still fail if writers are active. Review status and run a
manual backup after a missed/failed window; no guaranteed RPO is claimed. Per-user launchd requires the
user's session; logs are private but still need operator rotation. The JSON status is
bounded latest-event metadata, not an unlimited event history.

## Retention

Edit only non-secret policy fields in the private `config.json`:
`keep_daily=7`, `keep_weekly=4`, `keep_monthly=3`, `max_age_hours=26`, and
`min_free_bytes=268435456`. Values are validated; zero-history policies are rejected.
Paths and repository ID are safety bindings, not arbitrary strings to casually change.

```bash
# Preview policy only, after restoring latest successfully:
.venv/bin/python scripts/backups.py retention
# Explicit destructive operation confined to this encrypted repository/tag:
.venv/bin/python scripts/backups.py retention --apply-retention
```

The latest tested restore point remains protected and the latest two snapshots are
retained when available. The tool will not touch the private `.local/backups/step19*`
archives. Do not run manual `forget --keep-last 0`, recursive removal or forced unlock
as a shortcut. Inspect capacity through `status`; arrange approved additional capacity
before disk exhaustion. Local encrypted storage is free software, not unlimited space.

## Diagnosing failures

- `database_clients_active_stop_writers`: drain/stop owned writers and pooled API clients.
- `document_mutation_incomplete` / `document_integrity_failed`: inspect the existing
  document journal and recover deliberately; never create a misleading partial success.
- `insufficient_disk_space`: add approved capacity or review tested retention; do not
  remove previous recovery points blindly.
- `tool_failed`: check installed versions, credentials and destination health without
  pasting tool output containing paths/content into logs. Wrong keys fail the same way.
- `backup_operation_busy`: another operation holds the lock; wait, do not forcibly unlock.
- `latest_restore_required`: restore-test the latest exact snapshot before retention.
- `repository_identity_mismatch`: stop and reconcile the expected repository; never
  edit the binding simply to bypass an unexpected destination.
- `backup_operation_failed`: safe generic category for lower-level exceptions. Inspect
  component availability/private file permissions locally without dumping credentials.

Hard interruption may leave private `snapshot-*` or `restore-test-*` children in the
control directory and a marked temporary DB. Confirm no owned process is running,
inspect exact ownership and completed snapshots, then clean only those abandoned
resources deliberately. Never use `rm -rf` on state/repository/development directories
or restic `unlock` while a process may still own the operation.
