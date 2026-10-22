"""RQ transports UUIDs only. JSON serialization; no implicit queue retry policy."""

import logging
from contextlib import contextmanager

from redis import Redis
from rq import Queue, SpawnWorker
from rq.job import Job
from rq.serializers import JSONSerializer

from resolveflow.workflows.storage import lock_key


class IdentifierJob(Job):
    def perform(self):
        # Redis is private infrastructure, but a message still cannot choose arbitrary functions.
        if self.func_name != "resolveflow.jobs.worker.execute":
            raise ValueError("Unrecognized workflow task")
        return super().perform()


class WorkflowWorker(SpawnWorker):
    """WorkerPool does not forward arbitrary constructor kwargs in RQ 2.12."""

    def __init__(self, *args, **kwargs):
        kwargs.update(
            log_job_description=False,
            disable_default_exception_handler=True,
            worker_ttl=60,
            job_monitoring_interval=5,
        )
        super().__init__(*args, **kwargs)

    def work(self, *args, **kwargs):
        kwargs["with_scheduler"] = False  # PostgreSQL owns retry scheduling.
        return super().work(*args, **kwargs)


def connection(settings, *, worker=False):
    return Redis.from_url(
        settings.redis_url.get_secret_value(),
        socket_connect_timeout=3,
        socket_timeout=75 if worker else 3,
        retry_on_timeout=False,
    )


def queue(settings, conn):
    return Queue(
        settings.job_queue,
        connection=conn,
        serializer=JSONSerializer,
        job_class=IdentifierJob,
        default_timeout=settings.job_timeout_seconds,
    )


@contextmanager
def ownership(conn, name):
    key = lock_key(name)
    held = conn.execute("SELECT pg_try_advisory_lock(%s) AS ok", (key,)).fetchone()["ok"]
    try:
        yield held
    finally:
        if held:
            conn.execute("SELECT pg_advisory_unlock(%s)", (key,))


def log_event(event, job=None, code=None):
    import json

    logging.getLogger("resolveflow.jobs").info(
        json.dumps(
            dict(
                event=event,
                request_id=str(job.correlation_id) if job and job.correlation_id else None,
                duration_ms=max(0, (job.finished_at - job.started_at).total_seconds() * 1000)
                if job and job.finished_at and job.started_at
                else None,
                job_id=str(job.id) if job else None,
                execution_id=str(job.execution_id) if job else None,
                code=code,
                attempt=job.attempts if job else None,
                kind=job.kind if job else None,
            )
        )
    )
