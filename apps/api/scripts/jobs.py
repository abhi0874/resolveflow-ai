"""Dedicated RQ workers, durable dispatch and content-free local diagnostics."""

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rq import Worker
from rq.serializers import JSONSerializer
from rq.worker_pool import WorkerPool
from sqlalchemy import func, select, text

from resolveflow.core.config import Settings
from resolveflow.db.session import Database
from resolveflow.jobs.dispatch import reconcile
from resolveflow.jobs.models import WorkflowJob
from resolveflow.jobs.transport import IdentifierJob, WorkflowWorker, connection, log_event, queue
from resolveflow.workflows.models import WorkflowExecution

API = Path(__file__).resolve().parents[1]


def main():
    os.environ["PYTHONPATH"] = str(API / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["worker", "dispatch", "reconcile", "health", "list"])
    parser.add_argument("--burst", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = Settings()
    if args.command == "worker":
        conn = connection(settings, worker=True)
        try:
            WorkerPool(
                [queue(settings, conn)],
                connection=conn,
                num_workers=settings.worker_concurrency,
                worker_class=WorkflowWorker,
                serializer=JSONSerializer,
                job_class=IdentifierJob,
            ).start(burst=args.burst, logging_level="WARNING")
        finally:
            conn.close()
        return
    database = Database(settings)
    try:
        if args.command in {"reconcile", "dispatch"}:
            stopping = False

            def stop(*_):
                nonlocal stopping
                stopping = True

            signal.signal(signal.SIGTERM, stop)
            signal.signal(signal.SIGINT, stop)
            while not stopping:
                try:
                    count = reconcile(database, settings)
                    with connection(settings) as heartbeat:
                        heartbeat.set(
                            "resolveflow:dispatcher:" + settings.job_queue,
                            "alive",
                            ex=max(30, settings.job_reconcile_seconds * 3),
                        )
                    if count:
                        log_event("jobs_published", code=str(count))
                except Exception:
                    log_event("dispatch_deferred", code="infrastructure_unavailable")
                    if args.command == "reconcile":
                        raise SystemExit(1) from None
                if args.command == "reconcile":
                    break
                for _ in range(settings.job_reconcile_seconds * 10):
                    if stopping:
                        break
                    time.sleep(0.1)
        elif args.command == "list":
            with database.sessions() as db:
                rows = db.execute(
                    select(WorkflowJob.status, func.count()).group_by(WorkflowJob.status)
                ).all()
                jobs = db.execute(
                    select(WorkflowJob, WorkflowExecution.workspace_id, WorkflowExecution.ticket_id)
                    .join(WorkflowExecution)
                    .order_by(WorkflowJob.updated_at.desc())
                    .limit(50)
                ).all()
                print(
                    json.dumps(
                        dict(
                            counts=dict(rows),
                            recent=[
                                dict(
                                    job_id=str(j.id),
                                    execution_id=str(j.execution_id),
                                    workspace_id=str(w),
                                    ticket_id=str(t),
                                    status=j.status,
                                    kind=j.kind,
                                    attempts=j.attempts,
                                    error_code=j.error_code,
                                )
                                for j, w, t in jobs
                            ],
                        )
                    )
                )
        else:
            with database.sessions() as db:
                db.execute(text("SELECT 1"))
                pending = db.scalar(
                    select(func.count())
                    .select_from(WorkflowJob)
                    .where(WorkflowJob.status == "queued")
                )
            conn = connection(settings)
            try:
                conn.ping()
                workers = Worker.all(queue=queue(settings, conn))
                alive = sum(
                    w.last_heartbeat is not None
                    and w.last_heartbeat > datetime.now(UTC) - timedelta(seconds=60)
                    for w in workers
                )
                dispatch_alive = bool(conn.get("resolveflow:dispatcher:" + settings.job_queue))
                queued_transport = queue(settings, conn).count
                print(
                    json.dumps(
                        dict(
                            database="ok",
                            broker="ok",
                            workers=alive,
                            dispatcher="ok" if dispatch_alive else "unavailable",
                            queued=pending,
                            transport_messages=queued_transport,
                        )
                    )
                )
                if not alive or not dispatch_alive:
                    raise SystemExit(1)
            finally:
                conn.close()
    finally:
        database.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            "Job command unavailable; inspect service health. Sensitive details withheld.",
            file=sys.stderr,
        )
        sys.exit(1)
