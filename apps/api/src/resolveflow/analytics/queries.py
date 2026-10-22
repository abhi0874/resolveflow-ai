"""SQL aggregates return bounded buckets, never complete domain rows."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Date, cast, func, select

from resolveflow.analytics.resolution import resolution
from resolveflow.analytics.schemas import Measurement, Overview
from resolveflow.db.models import Ticket, TicketPriority, TicketStatus
from resolveflow.documents.models import Document, DocumentChunk
from resolveflow.jobs.models import WorkflowJob
from resolveflow.rag.models import DraftReview, ResponseDraft
from resolveflow.workflows.contracts import TERMINAL
from resolveflow.workflows.models import WorkflowExecution


def measure(value, samples, reason="No eligible records in this creation-date cohort"):
    return Measurement(
        value=float(value) if value is not None else None,
        samples=samples,
        unavailable_reason=reason if value is None else None,
    )


def distribution(db, model, column, filters, labels=()):
    rows = dict(
        db.execute(
            select(column, func.count()).select_from(model).where(*filters).group_by(column)
        ).all()
    )
    return [dict(label=str(key), count=rows.pop(key, 0)) for key in labels] + [
        dict(label=str(key), count=value)
        for key, value in sorted(rows.items(), key=lambda x: str(x[0]))
    ]


def trend(db, model, filters, dates):
    day = cast(func.timezone("UTC", model.created_at), Date)
    rows = db.execute(select(day, func.count()).where(*filters).group_by(day)).all()
    return fill_trend(dict(rows), dates)


def fill_trend(rows, dates):
    return [
        dict(
            day=dates.start + timedelta(days=i), count=rows.get(dates.start + timedelta(days=i), 0)
        )
        for i in range((dates.end - dates.start).days + 1)
    ]


def duration(db, statement, expression):
    count, average = db.execute(
        statement.with_only_columns(func.count(), func.avg(expression)).where(expression >= 0)
    ).one()
    return measure(average, count)


def overview(db, workspace, dates):
    start, end = dates.timestamps()
    observed = datetime.now(UTC)

    def scope(model):
        return (
            model.workspace_id == workspace,
            model.created_at >= start,
            model.created_at < end,
            model.created_at <= observed,
        )

    tf = scope(Ticket)
    statuses = distribution(db, Ticket, Ticket.status, tf, tuple(TicketStatus))
    # Top 20 labels plus an explicit remainder keep arbitrary category cardinality bounded.
    category = Ticket.category
    categories = [
        dict(label=f"Category: {k}" if k is not None else "No category", count=v)
        for k, v in db.execute(
            select(category, func.count())
            .where(*tf)
            .group_by(category)
            .order_by(func.count().desc(), category)
            .limit(20)
        )
    ]
    total = sum(item["count"] for item in statuses)
    remainder = total - sum(item["count"] for item in categories)
    if remainder:
        categories.append(dict(label="Other categories (remainder)", count=remainder))
    resolved = resolution(db, workspace, start, end, observed)
    wf = scope(WorkflowExecution)
    ws = distribution(
        db,
        WorkflowExecution,
        WorkflowExecution.status,
        wf,
        ("running", "paused", "completed", "failed", "cancelled", "rejected", "needs_revision"),
    )
    counts = {item["label"]: item["count"] for item in ws}
    terminal = sum(counts.get(key, 0) for key in TERMINAL)
    elapsed = func.extract("epoch", WorkflowExecution.finished_at - WorkflowExecution.created_at)
    jf = (
        WorkflowExecution.workspace_id == workspace,
        WorkflowJob.created_at >= start,
        WorkflowJob.created_at < end,
        WorkflowJob.created_at <= observed,
    )
    job_query = select(WorkflowJob).join(WorkflowExecution).where(*jf)
    jobs_total, retries = db.execute(
        job_query.with_only_columns(
            func.count(), func.coalesce(func.sum(func.greatest(WorkflowJob.attempts - 1, 0)), 0)
        )
    ).one()
    current_jobs = [
        dict(label=k, count=v)
        for k, v in db.execute(
            select(WorkflowJob.status, func.count())
            .join(WorkflowExecution)
            .where(WorkflowExecution.workspace_id == workspace)
            .group_by(WorkflowJob.status)
        )
    ]
    job_elapsed = func.extract("epoch", WorkflowJob.finished_at - WorkflowJob.started_at)
    wait = func.extract("epoch", WorkflowJob.started_at - WorkflowJob.created_at)
    df = (*scope(ResponseDraft), ResponseDraft.generation_status == "completed")
    outcomes = distribution(
        db,
        ResponseDraft,
        ResponseDraft.review_status,
        df,
        ("pending_review", "approved", "rejected", "needs_revision"),
    )
    decisions = {item["label"]: item["count"] for item in outcomes}
    reviewed = sum(decisions.get(k, 0) for k in ("approved", "rejected", "needs_revision"))
    review_elapsed = func.extract("epoch", DraftReview.created_at - ResponseDraft.created_at)
    review_query = (
        select(ResponseDraft)
        .join(
            DraftReview,
            (DraftReview.draft_id == ResponseDraft.id) & (DraftReview.workspace_id == workspace),
        )
        .where(*df, DraftReview.created_at <= observed)
    )
    kf = (*scope(Document), Document.processing_status != "deleting")
    kt, processed, failed, indexed = db.execute(
        select(
            func.count(),
            func.count().filter(Document.processing_status == "completed"),
            func.count().filter(Document.processing_status == "failed"),
            func.count().filter(Document.indexing_status == "indexed"),
        ).where(*kf)
    ).one()
    chunks = db.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .join(
            Document,
            (Document.id == DocumentChunk.document_id)
            & (Document.workspace_id == DocumentChunk.workspace_id),
        )
        .where(*kf, DocumentChunk.workspace_id == workspace)
    )
    return Overview(
        range=dates,
        generated_at=observed,
        tickets=dict(
            total=total,
            statuses=statuses,
            priorities=distribution(db, Ticket, Ticket.priority, tf, tuple(TicketPriority)),
            categories=categories,
            created_trend=trend(db, Ticket, tf, dates),
            resolution_trend=fill_trend(
                {datetime.fromisoformat(r["day"]).date(): r["count"] for r in resolved["trend"]},
                dates,
            ),
            resolution_average_seconds=measure(resolved["average"], resolved["samples"]),
            resolution_median_seconds=measure(resolved["median"], resolved["samples"]),
            resolution_history_excluded=resolved["excluded"],
        ),
        workflows=dict(
            total=sum(counts.values()),
            statuses=ws,
            stages=distribution(db, WorkflowExecution, WorkflowExecution.current_stage, wf),
            success_rate=measure(
                counts.get("completed", 0) / terminal if terminal else None, terminal
            ),
            failure_rate=measure(
                counts.get("failed", 0) / terminal if terminal else None, terminal
            ),
            elapsed_average_seconds=duration(
                db,
                select(WorkflowExecution).where(
                    *wf,
                    WorkflowExecution.status.in_(TERMINAL),
                    WorkflowExecution.finished_at <= observed,
                ),
                elapsed,
            ),
        ),
        jobs=dict(
            current_statuses=current_jobs,
            cohort_total=jobs_total,
            retained_phase_retries=retries,
            latest_attempt_average_seconds=duration(
                db, job_query.where(WorkflowJob.finished_at <= observed), job_elapsed
            ),
            initial_wait_average_seconds=duration(
                db,
                job_query.where(
                    WorkflowJob.kind == "start",
                    WorkflowJob.attempts == 1,
                    WorkflowJob.started_at <= observed,
                ),
                wait,
            ),
        ),
        reviews=dict(
            total_completed_drafts=sum(decisions.values()),
            outcomes=outcomes,
            approval_rate=measure(
                decisions.get("approved", 0) / reviewed if reviewed else None, reviewed
            ),
            request_to_review_average_seconds=duration(db, review_query, review_elapsed),
        ),
        knowledge_base=dict(
            total=kt,
            processed=processed,
            failed=failed,
            indexed=indexed,
            chunks=chunks,
            upload_trend=trend(db, Document, kf, dates),
        ),
    )
