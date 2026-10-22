"""Authorization, durable ownership and bounded invocation around the private graph."""

import uuid
from datetime import UTC, datetime

import psycopg
from fastapi import HTTPException
from langgraph.types import Command
from langsmith import tracing_context
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from resolveflow.db.session import DatabaseUnavailableError
from resolveflow.rag import service as rag
from resolveflow.workflows.contracts import TERMINAL, VERSION, ExecutionResponse
from resolveflow.workflows.graph import build_graph
from resolveflow.workflows.models import WorkflowExecution
from resolveflow.workflows.storage import (
    check_ownership,
    checkpoint_store,
    execution_lock,
    thread_id,
)
from resolveflow.workflows.workers import Workers, now


def scoped(db, user, workspace_id, execution_id, *, write=False):
    row = db.scalar(
        select(WorkflowExecution)
        .where(WorkflowExecution.workspace_id == workspace_id, WorkflowExecution.id == execution_id)
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise HTTPException(404)
    rag.authorize(db, user, workspace_id, row.ticket_id, write=write)
    return row


def representation(db, user, row, settings):
    ticket = rag.authorize(db, user, row.workspace_id, row.ticket_id)
    state = row.state
    draft = None
    if state.get("draft_id"):
        draft = rag.representation(
            db,
            rag.scoped_draft(db, row.workspace_id, row.ticket_id, uuid.UUID(state["draft_id"])),
            ticket,
        )
    evidence = []
    for ref in state.get("evidence", []):
        source = rag.current_source(
            db, row.workspace_id, uuid.UUID(ref["document_id"]), uuid.UUID(ref["chunk_id"])
        )
        if source:
            chunk, document = source
            evidence.append(
                dict(
                    document_id=document.id,
                    chunk_id=chunk.id,
                    document_name=document.original_filename,
                    chunk_index=chunk.chunk_index,
                    similarity_score=ref["similarity_score"],
                )
            )
    from resolveflow.jobs.service import job_view

    job = job_view(db, row)
    classification = state.get("classification", {})
    error = state.get("error") or {}
    return ExecutionResponse(
        job=job,
        cancel_requested=row.cancel_requested,
        id=row.id,
        workspace_id=row.workspace_id,
        ticket_id=row.ticket_id,
        requested_by=row.requested_by,
        workflow_version=row.workflow_version,
        status=row.status,
        current_stage=row.current_stage,
        completed_stages=state.get("completed_stages", []),
        classification=classification
        if classification and not classification.get("unavailable")
        else None,
        classification_unavailable=classification.get("unavailable", False),
        priority=state.get("priority"),
        evidence=evidence,
        context_summary=state.get("context_summary", {}),
        verification=state.get("verification", {}),
        approval_status=draft.review_status
        if draft
        else state.get("approval_status", "not_started"),
        draft=draft,
        error_code=error.get("code"),
        failed_stage=error.get("stage"),
        created_at=row.created_at,
        updated_at=row.updated_at,
        finished_at=row.finished_at,
        timings_ms=state.get("timings_ms", {}),
        attempts=row.attempts,
        can_resume=row.status in {"running", "paused"}
        and (
            (job is not None and job["status"] == "waiting_for_approval")
            or (job is None and row.attempts < settings.workflow_max_attempts)
        ),
    )


def start(
    db,
    user,
    workspace_id,
    ticket_id,
    body,
    settings,
    classifier,
    embeddings,
    provider,
    *,
    defer=False,
):
    ticket = rag.authorize(db, user, workspace_id, ticket_id, write=True)
    # Same lock order as RAG: workspace, then short global reservation lock.
    db.execute(text("SELECT pg_advisory_xact_lock(726374092)"))
    existing = db.scalar(
        select(WorkflowExecution).where(
            WorkflowExecution.workspace_id == workspace_id,
            WorkflowExecution.requested_by == user.id,
            WorkflowExecution.request_id == body.request_id,
        )
    )
    if existing:
        if (
            existing.ticket_id != ticket_id
            or existing.ticket_version != body.expected_ticket_version
            or existing.synthetic_confirmed != body.synthetic_confirmed
        ):
            raise HTTPException(409)
        return representation(db, user, existing, settings)
    if ticket.version != body.expected_ticket_version:
        raise HTTPException(409)
    if len(ticket.title) + len(ticket.description or "") > settings.ai_ticket_chars:
        raise HTTPException(422)
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    count = db.scalar(
        select(func.count())
        .select_from(WorkflowExecution)
        .where(WorkflowExecution.requested_by == user.id, WorkflowExecution.created_at >= today)
    )
    if count >= settings.workflow_daily_user:
        raise HTTPException(429, headers={"Retry-After": "86400"})
    row = WorkflowExecution(
        workspace_id=workspace_id,
        ticket_id=ticket_id,
        requested_by=user.id,
        request_id=body.request_id,
        ticket_version=ticket.version,
        synthetic_confirmed=body.synthetic_confirmed,
        workflow_version=VERSION,
    )
    db.add(row)
    if defer:
        from resolveflow.jobs.service import add_job

        db.flush()
        add_job(db, row, user, settings)
        db.commit()
        return representation(db, user, row, settings)
    db.commit()
    return drive(db, user, row, settings, classifier, embeddings, provider, resume=False)


def drive(
    db,
    user,
    row,
    settings,
    classifier,
    embeddings,
    provider,
    *,
    resume=True,
    background=False,
    guard=None,
):
    rag.authorize(db, user, row.workspace_id, row.ticket_id, write=True)
    if row.workflow_version != VERSION:
        raise HTTPException(409, detail="workflow_version_incompatible")
    db.commit()  # No application locks held while acquiring the exclusive checkpoint cursor.
    with (
        checkpoint_store(settings) as (saver, conn),
        execution_lock(conn, row, settings.workflow_concurrency),
    ):
        db.refresh(row)
        rag.authorize(db, user, row.workspace_id, row.ticket_id, write=True)
        if row.status in TERMINAL:
            if resume:
                raise HTTPException(409)
            return representation(db, user, row, settings)
        if not background and row.attempts >= settings.workflow_max_attempts:
            raise HTTPException(409, detail="workflow_recovery_limit")

        def verify_ownership():
            try:
                check_ownership(saver, conn)
                if guard:
                    guard()
            except psycopg.Error:
                raise DatabaseUnavailableError from None

        workers = Workers(
            db, user, row, settings, classifier, embeddings, provider, verify_ownership
        )
        graph = build_graph(workers, saver)
        config = {"configurable": {"thread_id": thread_id(row)}, "recursion_limit": 16}
        # Explicitly suppress environment-triggered tracing; no external telemetry service.
        with tracing_context(enabled=False):
            snapshot = graph.get_state(config)
            paused = any(task.interrupts for task in snapshot.tasks)
            if paused:
                draft = rag.scoped_draft(
                    db, row.workspace_id, row.ticket_id, uuid.UUID(snapshot.values["draft_id"])
                )
                if draft.review_status == "pending_review":
                    raise HTTPException(409, detail="workflow_review_required")
            row.attempts += 1
            row.status = "running"
            db.commit()
            initial = dict(
                execution_id=str(row.id),
                workspace_id=str(row.workspace_id),
                ticket_id=str(row.ticket_id),
                ticket_version=row.ticket_version,
                workflow_version=VERSION,
                current_stage="classification",
                completed_stages=[],
                evidence=[],
                status="running",
                approval_status="not_started",
                error=None,
                started_at=row.created_at.isoformat(),
                updated_at=now(),
                finished_at=None,
                timings_ms={},
            )
            try:
                if snapshot.values and not snapshot.next:
                    result = (
                        snapshot.values
                    )  # Recover a completed checkpoint whose row publication failed.
                else:
                    result = graph.invoke(
                        Command(resume=True) if paused else (None if snapshot.values else initial),
                        config,
                        durability="sync",
                    )
            except SQLAlchemyError:
                db.rollback()
                raise DatabaseUnavailableError from None
            # Only known state keys are published; interrupt metadata is never client state.
            result = {key: value for key, value in result.items() if key != "__interrupt__"}
            latest = graph.get_state(config)
            verify_ownership()
            row.state = result
            row.status = "paused" if any(t.interrupts for t in latest.tasks) else result["status"]
            row.current_stage = "approval" if row.status == "paused" else result["current_stage"]
            if result.get("finished_at"):
                row.finished_at = datetime.fromisoformat(result["finished_at"])
            db.commit()
    return representation(db, user, row, settings)


def cancel(db, user, row, settings):
    rag.authorize(db, user, row.workspace_id, row.ticket_id, write=True)
    db.commit()
    with (
        checkpoint_store(settings) as (saver, conn),
        execution_lock(conn, row, settings.workflow_concurrency),
    ):
        db.refresh(row)
        rag.authorize(db, user, row.workspace_id, row.ticket_id, write=True)
        if row.status in TERMINAL:
            raise HTTPException(409)
        row.status = "cancelled"
        row.finished_at = datetime.now(UTC)
        row.state = {**row.state, "status": "cancelled", "finished_at": row.finished_at.isoformat()}
        db.commit()
        saver.delete_thread(thread_id(row))
    return representation(db, user, row, settings)
