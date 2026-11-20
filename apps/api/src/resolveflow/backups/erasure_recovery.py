"""Offline replay on an already quarantined, owned target. Never mounts serving storage."""

from datetime import UTC, datetime

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from resolveflow.backups.safety import require
from resolveflow.backups.service import owned
from resolveflow.db.models import AccountErasure, GoogleFlow, User
from resolveflow.services import erasure
from resolveflow.services import erasure_journal as journal


def reconcile(engine, settings, expected_seal):
    owned(engine, empty=False)
    with Session(engine) as db:
        require(db.scalar(text(journal.QUARANTINED)), "quarantined_target_required")
        binding = journal.binding(db)
        with journal.locked_files(settings, readonly=True) as (intent, witness):
            sealed = witness.read()
            require(intent.read() == sealed, "erasure_witness_incomplete")
            require(journal.head(sealed) == expected_seal, "authoritative_seal_mismatch")
            ids = journal.records(sealed, binding.epoch)
            receipts = set(db.scalars(select(AccountErasure.id)))
            prefix = len(receipts)
            require(
                set(ids[:prefix]) == receipts
                and journal.head(sealed[: 33 * (1 + prefix)]) == binding.head,
                "snapshot_erasure_history_diverged",
            )
            # In-flight anonymous callbacks may predate a deleted identity that did
            # not even exist at snapshot time.
            db.execute(delete(GoogleFlow))
            replayed = 0
            for uid in ids:
                user = db.get(User, uid, with_for_update=True)
                if uid in receipts:
                    require(user is None, "erased_identity_present")
                    continue
                if user is None:
                    db.add(
                        AccountErasure(
                            id=uid, deleted_at=datetime.now(UTC), files=[], review_required=False
                        )
                    )
                else:
                    erasure.erase_rows(db, user)
                    replayed += 1
                db.flush()
            binding.head = journal.head(sealed)
            db.commit()
            holds = len(
                db.scalars(
                    select(AccountErasure.id).where(AccountErasure.review_required.is_(True))
                ).all()
            )
            return {
                "verified_ids": len(ids),
                "replayed": replayed,
                "private_file_holds": holds,
                "quarantined": True,
            }
