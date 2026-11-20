# Local invitation mailbox ownership and recovery

An invitation belongs to its workspace. Its immutable invitation ID, issuing account ID and
intended recipient account ID have distinct meanings. A workspace owner can change over time.
An invitation email is a delivery snapshot and may later belong to someone else.

## Delivery and interruption

Migration 0015 adds a delivery journal without importing historical files. Issuance commits the
IDs, mailbox location digest, expiry, role, recipient credential version and a SHA-256 commitment
to the exact message bytes before creating an object. The journal stores no usable token. A
second transaction rechecks authorization under the workspace lock, publishes a private
create-only file, then activates the grant. Accepting it still requires the intended recipient's
session and the token. The local mailbox is disabled in production.

A crash before the journal commit leaves no file. A crash after it leaves a discoverable intent.
A complete staged or final file can finish delivery with its original token. A partial write
remains in place under its recorded attempt name. Recovery commits a fresh attempt before writing
another file. An unexpected final file or exhausted attempt limit holds delivery for review.
A retry cannot replace foreign contents, transfer a grant to a reassigned address, or duplicate
an active grant. Parent references restrict removal of provenance while journal records exist.

## Operator procedure

Use the local API environment with the verified matching database and absolute private mailbox
root. Run from the repository root. Keep the mailbox, database and audit output accessible only
to authorized operators. Pause invitation writes for a consistent inventory.

1. Run `python apps/api/scripts/invitation_mailbox.py --audit`. It reads private directories
   without following symlink entries. Output contains a SHA-256 reference to each relative path
   and a classification. Exit 2 indicates a hold, a legacy correlation, or incomplete access.
   A successful inventory alone grants no deletion authority. Check every configured root,
   including any independently retained copies or restores, before an erasure decision.
2. Run `python apps/api/scripts/invitation_mailbox.py --pending` to list pending invitation IDs
   for this root. Use `--retry INVITATION_UUID` for one pending delivery. Retry only against the
   matching workspace database and mailbox. Rerun the read-only audit afterward.
3. Quarantine ambiguous entries **in place**. Keep them private and outside automated delivery,
   account cleanup, and user-facing downloads. Never move, overwrite, reassign or erase based
   on an email, a matching filename, expiry, or a workspace owner's request alone.
4. In a restricted case record, record the opaque object reference, classification, date, reviewer,
   evidence considered, decision authority and next review date. Keep tokens, message bodies and
   addresses out of ordinary logs. A legacy final can be correlated only by workspace and
   invitation IDs, the recipient snapshot and the database token commitment. Content without
   trustworthy attribution stays on hold. A matching legacy row still requires manual review.
5. The responsible privacy owner must determine the retention basis, review deadline and any
   separately authorized disposition for each hold. Record that decision before changing any
   historical file. Future deletion must account for both issuer and recipient references,
   shared workspace records, partial files, pending deliveries and backups. It must stop affected
   cleanup if provenance is incomplete. Do not promise erasure of retained or unreviewed copies.

## Scope of the investigation

The earlier Step 5 reproduction left one known **synthetic** orphan in its disposable test
evidence. Its name identifies the invitation and its parent identifies the workspace. It has no
durable recipient record. It remains untouched. Neither checkout had a default local mailbox
directory at the Step 5A inspection. This does not establish the contents of unexamined backups or
custom roots. The adjacent document store already commits a journal before writing and uses a
deletion tombstone. Identity email uses a database outbox. Account deletion is a separate step.

## Account deletion after migration 0016

Account deletion cancels grants issued by or addressed to the account. A delivery to another
account keeps its workspace, recipient and original issuer UUID. Its file stays private.
For recipient-owned cleanup, an erasure receipt retains the workspace, invitation, mailbox
location digest and expected content hashes until cleanup succeeds. The cleaner uses these
values under a database lock. Unsafe, altered and legacy objects require manual review.
Discarding the account login does not authorize deleting an unassigned legacy object.

Use `python apps/api/scripts/account_cleanup.py --pending` to find interrupted cleanups and
`--retry RECEIPT_UUID` to retry a single authorized receipt. The operation can resume after
a file was removed but before PostgreSQL acknowledged it. Use the separate mailbox inventory
for unassigned historical objects. Preserve those objects as unattributed. Do not attach them
to an erasure receipt merely because they share an address.
