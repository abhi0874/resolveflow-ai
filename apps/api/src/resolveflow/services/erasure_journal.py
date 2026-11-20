"""Independent write-ahead erasure intents and a separately retained commit witness."""

import fcntl
import hashlib
import os
import stat
import uuid
from contextlib import ExitStack, contextmanager

from sqlalchemy import select, text

from resolveflow.backups.safety import private, require
from resolveflow.core.config import API_ROOT
from resolveflow.db.models import AccountErasure, ErasureJournalBinding

NAME = "erasure-ids.v1"
QUARANTINED = """SELECT EXISTS (SELECT 1 FROM pg_db_role_setting cfg
JOIN pg_database d ON cfg.setdatabase=d.oid WHERE d.datname=current_database()
AND cfg.setrole=0 AND 'resolveflow.restore_quarantined=on'=ANY(cfg.setconfig))"""


def roots(settings):
    a, b = settings.erasure_journal_root, settings.erasure_witness_root
    require(a and b, "erasure_journal_unconfigured")
    for path in (a, b):
        private(path, directory=True)
        for other in (
            API_ROOT.parent / "web" / "public",
            settings.document_storage_root,
            settings.invitation_delivery_root,
            settings.classifier_artifact_root,
            settings.embedding_model_root,
        ):
            other = other.resolve()
            require(
                not (path.is_relative_to(other) or other.is_relative_to(path)),
                "erasure_storage_overlap",
            )
    require(
        not a.is_relative_to(b) and not b.is_relative_to(a) and not a.samefile(b),
        "erasure_storage_overlap",
    )
    if settings.environment == "production":
        require(a.stat().st_dev != b.stat().st_dev, "independent_volumes_required")
    return a, b


def entry(identifier):
    return identifier.hex.encode("ascii") + b"\n"


def head(data):
    return hashlib.sha256(data).hexdigest()


def append(stream, data):
    stream.write(data)
    stream.flush()
    os.fsync(stream.fileno())


def records(data, epoch):
    rows = data.splitlines(keepends=True)
    require(rows and rows[0] == entry(epoch), "erasure_epoch_mismatch")
    items = []
    for row in rows[1:]:
        require(len(row) == 33 and row[-1:] == b"\n", "erasure_record_invalid")
        try:
            uid = uuid.UUID(hex=row[:-1].decode("ascii"))
        except ValueError:
            raise ValueError("invalid erasure record") from None
        require(row == entry(uid), "erasure_record_invalid")
        items.append(uid)
    require(len(items) == len(set(items)), "erasure_record_duplicate")
    return items


@contextmanager
def locked_files(settings, *, readonly=False):
    with ExitStack() as stack:
        files = []
        for root in roots(settings):
            path = root / NAME
            private(path)
            flags = os.O_RDONLY if readonly else os.O_RDWR | os.O_APPEND
            fd = os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK)
            f = stack.enter_context(os.fdopen(fd, "rb" if readonly else "a+b"))
            info = os.fstat(fd)
            require(
                stat.S_ISREG(info.st_mode)
                and info.st_uid == os.getuid()
                and not info.st_mode & 0o077
                and info.st_nlink == 1,
                "unsafe_erasure_file",
            )
            f.seek(0)
            files.append(f)
        fcntl.flock(files[0], fcntl.LOCK_SH if readonly else fcntl.LOCK_EX)
        yield files


def initialize(db, settings):
    """Exclusive first provisioning on an authoritative quiesced source only."""
    require(not db.scalar(text(QUARANTINED)), "source_only")
    db.execute(text("LOCK TABLE erasure_journal_binding, account_erasures IN EXCLUSIVE MODE"))
    require(db.get(ErasureJournalBinding, True) is None, "already_bound")
    locations = roots(settings)
    require(all(not any(path.iterdir()) for path in locations), "new_roots_required")
    epoch = uuid.uuid4()
    payload = entry(epoch) + b"".join(
        entry(i) for i in db.scalars(select(AccountErasure.id).order_by(AccountErasure.id))
    )
    for root in locations:
        fd = os.open(root / NAME, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            append(stream, payload)
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    db.add(ErasureJournalBinding(singleton=True, epoch=epoch, head=head(payload)))
    db.commit()


def binding(db):
    row = db.get(ErasureJournalBinding, True, with_for_update=True, populate_existing=True)
    require(row is not None, "erasure_binding_missing")
    return row


def commit_erasure(db, settings, uid, validate_proof):
    """Serialize with recovery; a lost acknowledgement leaves a visible pending tail."""
    row = binding(db)
    with locked_files(settings) as (journal, witness):
        pending, sealed = journal.read(), witness.read()
        ids = records(sealed, row.epoch)
        require(head(sealed) == row.head and uid not in ids, "erasure_source_diverged")
        tail = entry(uid)
        require(pending in (sealed, sealed + tail), "erasure_pending_reconciliation")
        validate_proof()  # Recheck after waiting for both database and journal locks.
        if pending == sealed:
            append(journal, tail)
        else:
            os.fsync(journal.fileno())  # A retry can follow a failed sync.
        row.head = head(sealed + tail)
        db.commit()
        append(witness, tail)


def seal_interrupted(db, settings):
    """Repair only the single final acknowledgement proven by the original live DB."""
    require(not db.scalar(text(QUARANTINED)), "source_only")
    row = binding(db)
    with locked_files(settings) as (journal, witness):
        pending, sealed = journal.read(), witness.read()
        ids = records(pending, row.epoch)
        require(head(pending) == row.head, "uncommitted_erasure")
        if pending != sealed:
            require(
                ids
                and pending == sealed + entry(ids[-1])
                and db.get(AccountErasure, ids[-1]) is not None,
                "unproven_erasure",
            )
            append(witness, entry(ids[-1]))


def current_seal(db, settings):
    """Called on the fenced authoritative source at the recovery cutover."""
    require(not db.scalar(text(QUARANTINED)), "source_only")
    row = binding(db)
    with locked_files(settings) as (journal, witness):
        sealed = witness.read()
        ids = records(sealed, row.epoch)
        require(
            journal.read() == sealed
            and head(sealed) == row.head
            and set(ids) == set(db.scalars(select(AccountErasure.id))),
            "erasure_source_diverged",
        )
        for stream in (journal, witness):
            os.fsync(stream.fileno())
        return row.head
