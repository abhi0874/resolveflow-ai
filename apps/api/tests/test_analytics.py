import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from test_auth_workspaces import mutate
from test_documents import env as document_env
from test_jobs import deliver, location, start
from test_jobs import job_env as job_fixture

from resolveflow.db.models import Ticket, TicketActivity, WorkspaceMembership

pytestmark = pytest.mark.integration
env = document_env
job_env = job_fixture


def report(env, query=""):
    return env[2].get(f"/api/v1/workspaces/{env[4]['id']}/analytics/overview" + query)


def test_empty_and_date_validation(env):
    result = report(env)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["tickets"]["total"] == 0
    assert data["tickets"]["resolution_average_seconds"]["value"] is None
    assert data["workflows"]["success_rate"]["value"] is None
    assert data["reviews"]["approval_rate"]["value"] is None
    assert data["knowledge_base"]["chunks"] == 0
    assert len(data["tickets"]["created_trend"]) == 30
    assert result.headers["cache-control"] == "no-store"
    assert uuid.UUID(result.headers["x-request-id"])
    for query in (
        "?start=wrong",
        "?start=2026-01-10&end=2026-01-01",
        "?start=2020-01-01&end=2026-01-01",
        "?end=2099-01-01",
        "?unexpected=yes",
    ):
        assert report(env, query).status_code == 422


def test_ticket_counts_resolution_reopens_and_legacy(env):
    from sqlalchemy.orm import Session

    engine, _, client, user, space, _, _ = env
    base = f"/workspaces/{space['id']}/tickets"
    ticket = mutate(
        client, base, dict(title="Synthetic case", priority="high", category="Billing")
    ).json()
    for version, status in enumerate(("resolved", "open", "resolved", "closed"), 1):
        assert (
            mutate(
                client,
                base + "/" + ticket["id"],
                dict(expected_version=version, status=status),
                method="PATCH",
            ).status_code
            == 200
        )
    with Session(engine) as db:
        row = db.get(Ticket, uuid.UUID(ticket["id"]))
        row.created_at = datetime(2026, 1, 1, tzinfo=UTC)
        events = db.scalars(
            select(TicketActivity)
            .where(TicketActivity.ticket_id == row.id)
            .order_by(TicketActivity.created_at, TicketActivity.id)
        ).all()
        for hour, event in enumerate(events):
            event.created_at = datetime(2026, 1, 1, hour, tzinfo=UTC)
        # Current resolved record without event history is intentionally not measurable.
        db.add(
            Ticket(
                workspace_id=row.workspace_id,
                title="Legacy",
                status="resolved",
                created_at=datetime(2026, 1, 2, tzinfo=UTC),
            )
        )
        db.add(
            Ticket(
                workspace_id=row.workspace_id,
                title="Outside cohort",
                created_at=datetime(2025, 12, 31, 23, 59, tzinfo=UTC),
            )
        )
        db.commit()
    data = report(env, "?start=2026-01-01&end=2026-01-02").json()["tickets"]
    assert data["total"] == 2
    assert dict((x["label"], x["count"]) for x in data["statuses"])["closed"] == 1
    assert data["resolution_average_seconds"]["value"] == 10800
    assert data["resolution_median_seconds"]["samples"] == 1
    assert data["resolution_history_excluded"] == 1
    assert [x["count"] for x in data["created_trend"]] == [1, 1]
    assert data["resolution_trend"][0]["count"] == 1
    assert {"label": "Category: Billing", "count": 1} in data["categories"]
    # Break the event chain; the result must become unavailable, not a guessed duration.
    with Session(engine) as db:
        event = db.scalar(
            select(TicketActivity)
            .where(
                TicketActivity.ticket_id == uuid.UUID(ticket["id"]),
                TicketActivity.action == "status_changed",
            )
            .order_by(TicketActivity.created_at)
        )
        event.details = {"from": "closed", "to": "resolved"}
        db.commit()
    assert (
        report(env, "?start=2026-01-01&end=2026-01-02").json()["tickets"][
            "resolution_average_seconds"
        ]["value"]
        is None
    )


def test_workflow_job_review_knowledge_metrics(job_env):
    env, client, path, _, database = job_env
    run = start(job_env)
    queued = report(env).json()
    assert queued["jobs"]["current_statuses"] == [{"label": "queued", "count": 1}]
    paused = deliver(job_env, run)
    data = report(env).json()
    assert data["workflows"]["total"] == 1 and data["workflows"]["success_rate"]["value"] is None
    assert data["reviews"]["total_completed_drafts"] == 1
    assert data["knowledge_base"]["processed"] == 1 and data["knowledge_base"]["indexed"] == 1
    assert data["knowledge_base"]["chunks"] == 1
    assert (
        mutate(
            client,
            path + f"/drafts/{paused['draft']['id']}/review",
            dict(action="approved", expected_version=1),
        ).status_code
        == 200
    )
    assert mutate(client, location(job_env, run) + "/resume", {}).status_code == 202
    deliver(job_env, run)
    data = report(env).json()
    assert data["workflows"]["success_rate"]["value"] == 1
    assert data["workflows"]["failure_rate"]["value"] == 0
    assert data["reviews"]["approval_rate"]["value"] == 1
    assert data["reviews"]["request_to_review_average_seconds"]["samples"] == 1
    assert data["jobs"]["cohort_total"] == 1 and data["jobs"]["retained_phase_retries"] == 0
    assert data["jobs"]["initial_wait_average_seconds"]["value"] is None
    assert data["jobs"]["latest_attempt_average_seconds"]["samples"] == 1


def test_role_and_tenant_isolation(env):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from test_auth_workspaces import register, workspace

    from resolveflow.main import create_asgi_app

    with TestClient(create_asgi_app(env[6])) as other:
        path = f"/api/v1/workspaces/{env[4]['id']}/analytics/overview"
        assert other.get(path).status_code == 401
        register(other)
        own = workspace(other)
        mutate(other, f"/workspaces/{own['id']}/tickets", dict(title="Other tenant private"))
        assert other.get(path).status_code == 404
        assert report(env).json()["tickets"]["total"] == 0
    with Session(env[0]) as db:
        member = db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == uuid.UUID(env[4]["id"])
            )
        )
        for role, expected in [("viewer", 403), ("support_agent", 403), ("admin", 200)]:
            member.role = role
            db.commit()
            assert report(env).status_code == expected


@pytest.mark.parametrize(
    "terminal,expected", [("failed", (0, 1)), ("cancelled", (0, 0)), ("rejected", (0, 0))]
)
def test_terminal_denominators_and_retained_retries(job_env, terminal, expected):
    from resolveflow.jobs.models import WorkflowJob
    from resolveflow.workflows.models import WorkflowExecution

    env, _, _, _, database = job_env
    run = start(job_env)
    with database.sessions() as db:
        execution = db.get(WorkflowExecution, uuid.UUID(run["id"]))
        execution.status = terminal
        execution.finished_at = datetime.now(UTC)
        job = db.get(WorkflowJob, uuid.UUID(run["job"]["id"]))
        job.status = "failed"
        job.attempts = 3
        db.commit()
    data = report(env).json()
    assert data["workflows"]["total"] == 1
    assert data["workflows"]["success_rate"]["value"] == expected[0]
    assert data["workflows"]["failure_rate"]["value"] == expected[1]
    assert data["jobs"]["retained_phase_retries"] == 2
    assert data["jobs"]["latest_attempt_average_seconds"]["value"] is None


def test_correlation_propagation_and_safe_logs(job_env, caplog):
    import logging

    from resolveflow.core.observability import logger
    from resolveflow.jobs.models import WorkflowJob

    env, client, path, body, database = job_env
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.INFO):
            response = mutate(client, path + "/workflows", body)
        identifier = response.headers["x-request-id"]
        with database.sessions() as db:
            job = db.get(WorkflowJob, uuid.UUID(response.json()["job"]["id"]))
            assert str(job.correlation_id) == identifier
        assert identifier in caplog.text
        assert "Refund eligibility" not in caplog.text
        assert "csrf_token" not in caplog.text
        assert "password" not in caplog.text
    finally:
        logger.removeHandler(caplog.handler)


def test_representative_query_measurements(env):
    import json
    import statistics
    import time
    from pathlib import Path

    from sqlalchemy import text

    from resolveflow.analytics.resolution import RESOLUTION_SQL

    engine, _, client, user, space, _, _ = env
    foreign = mutate(
        client,
        "/workspaces",
        dict(name="Synthetic benchmark tenant", slug="bench-" + uuid.uuid4().hex),
    ).json()
    with engine.begin() as db:
        for workspace in (space["id"], foreign["id"]):
            db.execute(
                text("""INSERT INTO tickets
                (id,workspace_id,title,description,status,priority,category,version,created_at,updated_at)
                SELECT gen_random_uuid(),:workspace,'Synthetic benchmark','', 'resolved','medium',
                'Benchmark',1, '2026-01-05'::timestamptz + i*interval '1 second',now()
                FROM generate_series(1,10000) i"""),
                dict(workspace=workspace),
            )
            db.execute(
                text("""INSERT INTO ticket_activities
                (id,workspace_id,ticket_id,actor_id,action,details,created_at)
                SELECT gen_random_uuid(),workspace_id,id,:actor,'created','{}'::json,created_at
                FROM tickets WHERE workspace_id=:workspace"""),
                dict(workspace=workspace, actor=user["id"]),
            )
            db.execute(
                text("""INSERT INTO ticket_activities
                (id,workspace_id,ticket_id,actor_id,action,details,created_at)
                SELECT gen_random_uuid(),workspace_id,id,:actor,'status_changed',
                '{"from":"open","to":"resolved"}'::json,created_at+interval '2 hours'
                FROM tickets WHERE workspace_id=:workspace"""),
                dict(workspace=workspace, actor=user["id"]),
            )
        db.execute(text("ANALYZE tickets"))
        db.execute(text("ANALYZE ticket_activities"))
    samples = []
    for _ in range(5):
        begin = time.perf_counter()
        result = report(env, "?start=2026-01-01&end=2026-01-31")
        samples.append((time.perf_counter() - begin) * 1000)
        assert result.status_code == 200, result.text
        assert result.json()["tickets"]["total"] == 10000
        assert result.json()["tickets"]["resolution_average_seconds"]["value"] == 7200
    with engine.connect() as db:
        plan = db.execute(
            text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + RESOLUTION_SQL),
            dict(
                workspace=space["id"],
                start=datetime(2026, 1, 1, tzinfo=UTC),
                end=datetime(2026, 2, 1, tzinfo=UTC),
                observed=datetime.now(UTC),
            ),
        ).scalar()[0]
    output = Path(__file__).resolve().parents[3] / ".cache/verification/analytics-performance.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            dict(
                tickets=20000,
                status_events=20000,
                creation_events=20000,
                scoped_tickets=10000,
                request_ms=samples,
                median_ms=statistics.median(samples),
                resolution_query_ms=plan["Execution Time"],
                planning_ms=plan["Planning Time"],
                shared_hit_blocks=plan["Plan"].get("Shared Hit Blocks"),
                note="Local synthetic in-process HTTP, warm database; not a production SLA.",
            ),
            indent=2,
        )
        + "\n"
    )


@pytest.mark.parametrize(
    "issue", ["tie", "duplicate_creation", "missing_creation", "reopened_then_closed"]
)
def test_incomplete_resolution_sequences_are_not_estimated(env, issue):
    from sqlalchemy.orm import Session

    engine, _, client, user, space, _, _ = env
    base = f"/workspaces/{space['id']}/tickets"
    ticket = mutate(client, base, dict(title="Synthetic history integrity")).json()
    with Session(engine) as db:
        row = db.get(Ticket, uuid.UUID(ticket["id"]))
        row.created_at = datetime(2026, 1, 1, tzinfo=UTC)
        row.status = "resolved"
        creation = db.scalar(select(TicketActivity).where(TicketActivity.ticket_id == row.id))
        creation.created_at = row.created_at
        event = TicketActivity(
            workspace_id=row.workspace_id,
            ticket_id=row.id,
            actor_id=uuid.UUID(user["id"]),
            action="status_changed",
            details={"from": "open", "to": "resolved"},
            created_at=datetime(2026, 1, 1, 1, tzinfo=UTC),
        )
        db.add(event)
        if issue == "missing_creation":
            db.delete(creation)
        if issue == "duplicate_creation":
            db.add(
                TicketActivity(
                    workspace_id=row.workspace_id,
                    ticket_id=row.id,
                    actor_id=uuid.UUID(user["id"]),
                    action="created",
                    details={},
                    created_at=row.created_at,
                )
            )
        if issue in ("tie", "reopened_then_closed"):
            for hour, old, new in [(2, "resolved", "open"), (3, "open", "closed")]:
                db.add(
                    TicketActivity(
                        workspace_id=row.workspace_id,
                        ticket_id=row.id,
                        actor_id=uuid.UUID(user["id"]),
                        action="status_changed",
                        details={"from": old, "to": new},
                        created_at=datetime(2026, 1, 1, 1 if issue == "tie" else hour, tzinfo=UTC),
                    )
                )
            row.status = "closed"
        db.commit()
    metrics = report(env, "?start=2026-01-01&end=2026-01-02").json()["tickets"]
    assert metrics["resolution_average_seconds"]["value"] is None
    assert metrics["resolution_average_seconds"]["samples"] == 0
    assert metrics["resolution_history_excluded"] == 1
