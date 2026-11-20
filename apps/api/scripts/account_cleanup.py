"""List pending private cleanup receipts or retry one by its opaque UUID."""

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import func, select

from resolveflow.core.config import Settings
from resolveflow.db.models import AccountErasure
from resolveflow.db.session import Database
from resolveflow.services.erasure import cleanup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--pending", action="store_true")
    action.add_argument("--retry", type=uuid.UUID)
    args = parser.parse_args()
    settings = Settings()
    database = Database(settings)
    try:
        with database.sessions() as db:
            if args.pending:
                pending = select(AccountErasure.id).where(
                    func.json_array_length(AccountErasure.files) > 0
                )
                for identifier in db.scalars(pending):
                    print(identifier)
                return 0
            complete = cleanup(db, settings, args.retry)
            print(
                "Cleanup complete" if complete else "Receipt unavailable or manual review required"
            )
            return 0 if complete else 1
    finally:
        database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
