"""Retry tracked deletion tombstones and mark interrupted uploads for explicit retry."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sqlalchemy.orm import Session

from resolveflow.core.config import Settings
from resolveflow.db.session import Database
from resolveflow.documents.service import recover
from resolveflow.documents.storage import LocalFileStorage


def main():
    settings = Settings()
    if settings.database_url is None:
        raise RuntimeError("Database configuration is required")
    database = Database(settings)
    try:
        with Session(database.engine) as db:
            count = recover(db, LocalFileStorage(settings.document_storage_root), settings)
            print(f"Recovered {count} tracked documents.")
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
