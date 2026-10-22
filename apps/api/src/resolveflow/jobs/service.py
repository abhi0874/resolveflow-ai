"""Transactional job/outbox ownership. No broker call participates in API transactions."""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select, text

from resolveflow.core.observability import request_id
from resolveflow.jobs.models import WorkflowJob
from resolveflow.rag import service as rag
from resolveflow.workflows.contracts import TERMINAL
from resolveflow.workflows.models import WorkflowExecution

ACTIVE = ("queued", "running")


def now():
    return datetime.now(UTC)


def get_job(db, execution_id, *, lock=False):
    query = select(WorkflowJob).where(WorkflowJob.execution_id == execution_id)
    if lock:
        query = query.with_for_update()
    return db.scalar(query.execution_options(populate_existing=True))


def capacity(db, workspace_id, settings):
    # All job acceptance uses the same short reservation lock as workflow creation.
    db.execute(text("SELECT pg_advisory_xact_lock(726374092)"))
    base = select(func.count()).select_from(WorkflowJob).where(WorkflowJob.status.in_(ACTIVE))
    total = db.scalar(base)
    own = db.scalar(
        base.join(WorkflowExecution).where(WorkflowExecution.workspace_id == workspace_id)
    )
    if total >= settings.job_max_pending or own >= settings.job_workspace_pending:
        raise HTTPException(429, headers={"Retry-After": "30"})


def add_job(db, row, user, settings):
    capacity(db, row.workspace_id, settings)
    job = WorkflowJob(
        execution_id=row.id, actor_id=user.id, available_at=now(), correlation_id=request_id.get()
    )
    db.add(job)
    db.flush()
    return job


def job_view(db, row):
    job = get_job(db, row.id)
    if job is None:
        return None
    return dict(
        id=str(job.id),
        kind=job.kind,
        status=job.status,
        attempts=job.attempts,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        next_attempt_at=job.available_at if job.status == "queued" else None,
        error_code=job.error_code,
    )


def requeue(job, actor_id, kind):
    job.correlation_id = request_id.get()
    job.kind, job.actor_id, job.status = kind, actor_id, "queued"
    job.delivery_id = uuid.uuid4()
    job.attempts, job.publications = 0, 0
    job.available_at = now()
    job.published_at = job.started_at = job.finished_at = job.error_code = None


def resume(db, user, row, settings):
    rag.authorize(db, user, row.workspace_id, row.ticket_id, write=True)
    db.execute(text("SELECT pg_advisory_xact_lock(726374092)"))
    job = get_job(db, row.id, lock=True)
    if job and job.status in ACTIVE:
        return  # Repeated request is the same queued/running operation.
    if row.status in TERMINAL or row.cancel_requested:
        raise HTTPException(409)
    if row.state.get("draft_id"):
        draft = rag.scoped_draft(
            db, row.workspace_id, row.ticket_id, uuid.UUID(row.state["draft_id"])
        )
        if row.status == "paused" and draft.review_status == "pending_review":
            raise HTTPException(409, detail="workflow_review_required")
    if job and job.status != "waiting_for_approval":
        raise HTTPException(409)
    if job is None:  # Existing Step 10 execution, same ID/checkpoints, no new graph.
        job = add_job(db, row, user, settings)
    else:
        capacity(db, row.workspace_id, settings)
    requeue(job, user.id, "resume")
    db.commit()


def cancel(db, user, row, settings):
    rag.authorize(db, user, row.workspace_id, row.ticket_id, write=True)
    db.execute(text("SELECT pg_advisory_xact_lock(726374092)"))
    job = get_job(db, row.id, lock=True)
    if row.cancel_requested:
        return
    if row.status in TERMINAL:
        raise HTTPException(409)
    row.cancel_requested = True
    row.cancel_requested_by = user.id
    row.cancel_requested_at = now()
    if job is None:
        job = WorkflowJob(
            execution_id=row.id,
            actor_id=user.id,
            available_at=now(),
            correlation_id=request_id.get(),
        )
        db.add(job)
    if job.status != "running":
        requeue(job, user.id, "cancel")
    db.commit()
