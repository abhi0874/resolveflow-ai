"""RQ entry point delegates to the existing application orchestrator."""

import logging
import uuid
from contextlib import ExitStack
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from resolveflow.core.config import Settings
from resolveflow.db.models import User
from resolveflow.db.session import Database, DatabaseUnavailableError
from resolveflow.jobs.models import WorkflowJob
from resolveflow.jobs.service import now
from resolveflow.jobs.transport import log_event, ownership
from resolveflow.retrieval.contracts import EmbeddingUnavailable
from resolveflow.workflows import service as workflow
from resolveflow.workflows.contracts import TERMINAL
from resolveflow.workflows.models import WorkflowExecution
from resolveflow.workflows.storage import checkpoint_store


def finish(job, row):
    job.status = {
        "paused": "waiting_for_approval",
        "rejected": "completed",
        "needs_revision": "completed",
    }.get(row.status, row.status)
    job.error_code = (row.state.get("error") or {}).get("code")
    if job.status != "waiting_for_approval":
        job.finished_at = now()


def defer(job, code, delay):
    job.status, job.error_code = "queued", code
    job.available_at = now() + timedelta(seconds=delay)
    job.published_at = None
    job.delivery_id = uuid.uuid4()


def fail(job, row, code):
    job.status, job.error_code, job.finished_at = "failed", code, now()
    if row.status not in TERMINAL:
        row.status, row.finished_at = "failed", now()
        row.state = {
            **row.state,
            "status": "failed",
            "error": {"code": code, "stage": row.current_stage},
        }


def process(database, settings, job_id, delivery_id, dependencies=None):
    with checkpoint_store(settings) as (_, conn), ExitStack() as stack:
        held = stack.enter_context(ownership(conn, "job:" + str(job_id)))
        if not held:
            return
        with database.sessions() as db:
            job = db.get(WorkflowJob, job_id)
            if job is None or job.delivery_id != delivery_id or job.status != "queued":
                return
            row = db.get(WorkflowExecution, job.execution_id)
            if row.status in TERMINAL:
                finish(job, row)
                db.commit()
                return
            # A committed pause can outlive a crash before publishing job status.
            if row.status == "paused" and job.kind == "start" and not row.cancel_requested:
                finish(job, row)
                db.commit()
                return
            workspace_slot = False
            for index in range(settings.job_workspace_concurrency):
                if stack.enter_context(
                    ownership(conn, f"job-workspace:{row.workspace_id}:{index}")
                ):
                    workspace_slot = True
                    break
            if not workspace_slot:
                defer(job, "workspace_busy", 5)
                db.commit()
                return
            if job.attempts >= settings.job_max_attempts and not row.cancel_requested:
                fail(job, row, "job_attempts_exhausted")
                db.commit()
                return
            job.status, job.started_at = "running", now()
            job.attempts += 1
            job.available_at = now() + timedelta(seconds=settings.job_timeout_seconds + 30)
            db.commit()
            log_event("job_started", job)
            provider = None
            try:
                user = db.get(User, job.actor_id)
                if user is None:
                    raise HTTPException(403)
                # Current user, workspace, ticket and assignment authorization; never message scope.
                workflow.scoped(db, user, row.workspace_id, row.id, write=True)
                if row.cancel_requested:
                    workflow.cancel(db, user, row, settings)
                else:
                    if dependencies is None:
                        from resolveflow.ai.providers import select_provider
                        from resolveflow.ml.classifier import LocalTicketClassifier
                        from resolveflow.retrieval.provider import LocalSentenceTransformerProvider

                        provider = select_provider(settings)
                        classifier = LocalTicketClassifier(
                            settings.classifier_artifact_root,
                            settings.classifier_model_version,
                            settings.classifier_threshold,
                        )
                        embeddings = LocalSentenceTransformerProvider(
                            settings.embedding_model_root,
                            settings.embedding_device,
                            settings.embedding_batch_size,
                        )
                    else:
                        classifier, embeddings, provider = dependencies
                    workflow.drive(
                        db,
                        user,
                        row,
                        settings,
                        classifier,
                        embeddings,
                        provider,
                        resume=False,
                        background=True,
                        guard=lambda: conn.execute("SELECT 1"),
                    )
                    db.refresh(row)
                    if row.cancel_requested and row.status not in TERMINAL:
                        workflow.cancel(db, user, row, settings)
                db.refresh(row)
                finish(job, row)
                db.commit()
                log_event("job_finished", job, job.error_code)
            except (SQLAlchemyError, DatabaseUnavailableError, EmbeddingUnavailable) as exc:
                db.rollback()
                db.refresh(job)
                db.refresh(row)
                if job.delivery_id != delivery_id or job.status != "running":
                    return
                code = (
                    "retrieval_unavailable"
                    if isinstance(exc, EmbeddingUnavailable)
                    else "database_unavailable"
                )
                if job.attempts < settings.job_max_attempts:
                    defer(job, code, 2**job.attempts)
                else:
                    fail(job, row, code)
                db.commit()
                log_event("job_retry" if job.status == "queued" else "job_failed", job, code)
            except HTTPException as exc:
                db.rollback()
                db.refresh(job)
                db.refresh(row)
                if job.delivery_id != delivery_id or job.status != "running":
                    return
                if exc.status_code == 429 or exc.detail == "workflow_busy":
                    job.attempts -= 1  # Capacity contention is not a processing attempt.
                    defer(job, "workflow_busy", 5)
                else:
                    fail(
                        job,
                        row,
                        "authorization_changed"
                        if exc.status_code in {401, 403, 404}
                        else "workflow_conflict",
                    )
                db.commit()
                log_event(
                    "job_deferred" if job.status == "queued" else "job_failed", job, job.error_code
                )
            except Exception:
                db.rollback()
                db.refresh(job)
                db.refresh(row)
                if job.delivery_id != delivery_id or job.status != "running":
                    return
                fail(job, row, "job_execution_failed")
                db.commit()
                log_event("job_failed", job, job.error_code)
            finally:
                if dependencies is None and provider is not None:
                    provider.close()


def execute(job_id: str, delivery_id: str):
    logger = logging.getLogger("resolveflow.jobs")
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        identity, delivery = uuid.UUID(job_id), uuid.UUID(delivery_id)
    except ValueError, TypeError, AttributeError:
        return
    database = None
    try:
        settings = Settings()
        database = Database(settings)
        process(database, settings, identity, delivery)
    except Exception:
        # RQ must never store raw exception values/tracebacks from database or provider code.
        # The durable row remains available for bounded reconciliation after process failure.
        log_event("job_deferred", code="infrastructure_unavailable")
    finally:
        if database:
            database.dispose()
