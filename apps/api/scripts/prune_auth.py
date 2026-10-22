"""Explicitly remove expired authentication sessions and expired rate-limit counters."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from resolveflow.core.config import Settings  # noqa: E402
from resolveflow.db.session import Database  # noqa: E402
from resolveflow.services.auth import clear_expired  # noqa: E402


def main() -> None:
    database = Database(Settings())
    try:
        with database.sessions() as session:
            clear_expired(session)
        print(
            "Expired authentication rows pruned; active sessions and application records preserved."
        )
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
