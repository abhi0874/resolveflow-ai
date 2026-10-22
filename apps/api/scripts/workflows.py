"""Explicit checkpoint setup and terminal-history pruning; never executes a graph."""

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select

from resolveflow.core.config import Settings
from resolveflow.db.session import Database
from resolveflow.workflows.contracts import TERMINAL
from resolveflow.workflows.models import WorkflowExecution
from resolveflow.workflows.storage import checkpoint_store, execution_lock, thread_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["setup", "prune"])
    parser.add_argument("--older-than-days", type=int, default=30)
    args = parser.parse_args()
    if args.older_than_days < 1:
        parser.error("Retention must be at least one day")
    settings = Settings()
    with checkpoint_store(settings, setup=args.command == "setup") as (saver, conn):
        if args.command == "setup":
            print("Checkpoint schema initialized; no inference performed.")
            return
        database = Database(settings)
        count = 0
        try:
            with database.sessions() as db:
                rows = db.scalars(
                    select(WorkflowExecution).where(
                        WorkflowExecution.status.in_(TERMINAL),
                        WorkflowExecution.finished_at
                        < datetime.now(UTC) - timedelta(days=args.older_than_days),
                    )
                ).all()
                for row in rows:
                    with execution_lock(conn, row, settings.workflow_concurrency):
                        saver.delete_thread(thread_id(row))
                        count += 1
            print(
                f"Pruned checkpoints for {count} terminal executions; "
                "ownership/review records retained."
            )
        finally:
            database.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            "Workflow storage operation failed; check database availability and migrations.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
