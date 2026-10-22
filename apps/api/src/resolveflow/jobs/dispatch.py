"""Persistent job rows double as a transactional outbox and recovery ledger."""

import uuid
from datetime import timedelta

from redis.exceptions import RedisError
from sqlalchemy import select

from resolveflow.jobs.models import WorkflowJob
from resolveflow.jobs.service import now
from resolveflow.jobs.transport import connection, log_event, ownership, queue
from resolveflow.workflows.storage import checkpoint_store


def reconcile(database, settings):
    published = 0
    broker = connection(settings)
    try:
        with checkpoint_store(settings) as (_, conn), database.sessions() as db:
            # One publisher across processes bounds the Redis queue capacity check + publication.
            with ownership(conn, "job-publisher:" + settings.job_queue) as held:
                if not held:
                    return 0
                candidates = db.scalars(
                    select(WorkflowJob)
                    .where(
                        WorkflowJob.status.in_(("queued", "running")),
                        WorkflowJob.available_at <= now(),
                    )
                    .order_by(WorkflowJob.available_at)
                    .limit(settings.job_max_pending)
                ).all()
                q = queue(settings, broker)
                for job in candidates:
                    with ownership(conn, "job:" + str(job.id)) as free:
                        if not free:
                            continue
                        db.refresh(job)
                        if job.status not in {"queued", "running"}:
                            continue
                        if job.status == "running":
                            # The old worker no longer owns its PG session lock. Redelivery
                            # reuses the checkpoint and draft reservation, never repeats inference.
                            job.status = "queued"
                            job.delivery_id = uuid.uuid4()
                            job.published_at = None
                            job.error_code = "worker_interrupted"
                        elif job.published_at and job.published_at > now() - timedelta(
                            seconds=settings.job_timeout_seconds + 30
                        ):
                            continue
                        else:
                            # Republish lost/stale deliveries under a fresh token. Old tokens no-op.
                            job.delivery_id = uuid.uuid4()
                        job.publications += 1
                        db.commit()  # Durable delivery identity before sending to Redis.
                        try:
                            if q.count >= settings.job_queue_capacity:
                                break
                            q.enqueue(
                                "resolveflow.jobs.worker.execute",
                                str(job.id),
                                str(job.delivery_id),
                                job_id=job.delivery_id.hex,
                                job_timeout=settings.job_timeout_seconds,
                                result_ttl=0,
                                failure_ttl=3600,
                                ttl=settings.job_timeout_seconds + 30,
                            )
                            job.published_at = now()
                            job.error_code = None if job.attempts == 0 else job.error_code
                            published += 1
                        except RedisError:
                            job.error_code = "broker_unavailable"
                            job.available_at = now() + timedelta(
                                seconds=min(60, 2 ** min(job.publications, 6))
                            )
                            log_event("publication_deferred", job, job.error_code)
                            db.commit()
                            break
                        db.commit()
                return published
    finally:
        broker.close()
