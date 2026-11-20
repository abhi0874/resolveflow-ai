"""Audit an offline private mailbox, or retry one journaled delivery by invitation ID."""

import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select, text

from resolveflow.core.config import Settings
from resolveflow.db.models import InvitationDelivery
from resolveflow.db.session import Database
from resolveflow.services.invitation_delivery import deliver, mailbox_hash
from resolveflow.services.invitation_files import UnverifiedFile
from resolveflow.services.invitation_inventory import inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--audit", action="store_true")
    options.add_argument("--pending", action="store_true")
    options.add_argument("--retry", type=uuid.UUID)
    args = parser.parse_args()
    settings = Settings()
    if settings.environment == "production":
        parser.error("This tool is for the local mailbox only")
    database = Database(settings)
    try:
        with database.sessions() as db:
            if args.audit or args.pending:
                db.execute(text("SET TRANSACTION READ ONLY"))
            if args.pending:
                pending = select(InvitationDelivery.id).where(
                    InvitationDelivery.status == "pending",
                    InvitationDelivery.mailbox_hash == mailbox_hash(settings),
                )
                for identifier in db.scalars(pending):
                    print(identifier)
            elif args.audit:
                if not settings.invitation_delivery_root.is_dir():
                    print("Mailbox unavailable. Inventory incomplete.", file=sys.stderr)
                    return 2
                needs_review = False
                try:
                    for ref, status in inventory(db, settings.invitation_delivery_root):
                        print(json.dumps({"object_ref": ref, "classification": status}))
                        needs_review |= status.startswith("hold_") or status == "legacy_correlated"
                except UnverifiedFile, OSError:
                    print("Private mailbox could not be inspected safely.", file=sys.stderr)
                    return 2
                return 2 if needs_review else 0
            else:
                result = deliver(db, settings, args.retry)
                print(
                    "Grant committed; use --audit to check files"
                    if result
                    else "Inactive or requires review"
                )
                return 0 if result else 1
    finally:
        database.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
