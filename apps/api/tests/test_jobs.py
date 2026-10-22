import os
import subprocess
import sys
import time
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from test_auth_workspaces import mutate, register
from test_documents import env as document_env
from test_embeddings import real_embeddings as embedding_fixture
from test_rag import setup

from resolveflow.db.session import Database
from resolveflow.jobs.dispatch import reconcile
from resolveflow.jobs.models import WorkflowJob
from resolveflow.jobs.service import now
from resolveflow.jobs.worker import process
from resolveflow.main import create_asgi_app
from resolveflow.rag.models import DraftReview, ResponseDraft
from resolveflow.workflows.storage import checkpoint_store
from scripts.broker_fixture import isolated_broker

pytestmark = pytest.mark.integration
env = document_env
real_embeddings = embedding_fixture


@pytest.fixture
def job_env(env):
    client, path, body, doc = setup(env)
    with checkpoint_store(env[6], setup=True):
        pass
    database = Database(env[6])
    try:
        yield env, client, path, body, database
    finally:
        database.dispose()


def start(fixture):
    _, client, path, body, _ = fixture
    result = mutate(client, path + "/workflows", body)
    assert result.status_code == 202, result.text
    run = result.json()
    assert run["job"]["status"] == "queued" and run["draft"] is None
    return run


def location(fixture, run):
    return f"/workspaces/{fixture[0][4]['id']}/workflows/{run['id']}"


def deliver(fixture, run):
    env, _, _, _, database = fixture
    with database.sessions() as db:
        job = db.get(WorkflowJob, uuid.UUID(run["job"]["id"]))
        identity, token = job.id, job.delivery_id
    process(
        database,
        env[6],
        identity,
        token,
        (env[1].app.state.classifier, env[1].app.state.embeddings, env[1].app.state.ai_provider),
    )
    return fixture[1].get("/api/v1" + location(fixture, run)).json()


def test_async_persistence_duplicate_delivery_approval(job_env):
    env, client, path, body, database = job_env
    run = start(job_env)
    assert mutate(client, path + "/workflows", body).json()["id"] == run["id"]
    paused = deliver(job_env, run)
    assert paused["status"] == "paused" and paused["job"]["status"] == "waiting_for_approval"
    assert deliver(job_env, run)["draft"]["id"] == paused["draft"]["id"]
    assert mutate(client, location(job_env, run) + "/resume", {}).status_code == 409
    review = mutate(
        client,
        path + f"/drafts/{paused['draft']['id']}/review",
        {"action": "approved", "expected_version": 1},
    )
    assert review.status_code == 200
    assert mutate(client, location(job_env, run) + "/resume", {}).status_code == 202
    assert mutate(client, location(job_env, run) + "/resume", {}).status_code == 202
    done = deliver(job_env, run)
    assert done["status"] == "completed" and done["job"]["status"] == "completed"
    with database.sessions() as db:
        assert db.scalar(select(func.count()).select_from(ResponseDraft)) == 1
        assert db.scalar(select(func.count()).select_from(DraftReview)) == 1
        assert db.scalar(select(func.count()).select_from(WorkflowJob)) == 1


def test_capacity_cancellation_and_authorization(job_env):
    env, client, path, body, database = job_env
    env[6].job_workspace_pending = 1
    run = start(job_env)
    assert (
        mutate(client, path + "/workflows", {**body, "request_id": str(uuid.uuid4())}).status_code
        == 429
    )
    with TestClient(create_asgi_app(env[6])) as other:
        assert other.get("/api/v1" + location(job_env, run)).status_code == 401
        register(other)
        assert other.get("/api/v1" + location(job_env, run)).status_code == 404
        assert mutate(other, location(job_env, run) + "/cancel", {}).status_code == 404
    assert mutate(client, location(job_env, run) + "/cancel", {}).status_code == 202
    assert mutate(client, location(job_env, run) + "/cancel", {}).status_code == 202
    done = deliver(job_env, run)
    assert done["status"] == "cancelled" and done["job"]["status"] == "cancelled"
    with database.sessions() as db:
        assert db.scalar(select(func.count()).select_from(ResponseDraft)) == 0


def test_broker_failure_and_reconciliation(job_env):
    env, client, _, _, database = job_env
    run = start(job_env)
    env[6].redis_url = SecretStr("redis://127.0.0.1:1/0")
    assert reconcile(database, env[6]) == 0
    with database.sessions() as db:
        job = db.get(WorkflowJob, uuid.UUID(run["job"]["id"]))
        assert job.status == "queued" and job.error_code == "broker_unavailable"
        job.available_at = now() - timedelta(seconds=1)
        db.commit()
    with isolated_broker() as (url, _):
        env[6].redis_url = SecretStr(url)
        assert reconcile(database, env[6]) == 1
        assert reconcile(database, env[6]) == 0
    assert client.get("/api/v1" + location(job_env, run)).json()["job"]["status"] == "queued"


def test_retry_bounds_and_stale_delivery(job_env):
    from resolveflow.retrieval.contracts import EmbeddingUnavailable

    env, _, _, _, database = job_env
    run = start(job_env)

    def fail(_):
        raise EmbeddingUnavailable("private failure detail")

    env[1].app.state.embeddings.embed_query = fail
    for attempt in range(1, 4):
        result = deliver(job_env, run)
        assert result["job"]["attempts"] == attempt
        assert "private failure detail" not in str(result)
    assert result["job"]["status"] == "failed"
    assert result["job"]["error_code"] == "retrieval_unavailable"
    with database.sessions() as db:
        assert db.scalar(select(func.count()).select_from(ResponseDraft)) == 0
    process(database, env[6], uuid.uuid4(), uuid.uuid4())


def test_cancel_during_provider_discards_output(job_env):
    env, client, _, _, database = job_env
    run = start(job_env)
    original = env[1].app.state.ai_provider.generate_structured

    def cancel_then_return(request):
        assert mutate(client, location(job_env, run) + "/cancel", {}).status_code == 202
        return original(request)

    env[1].app.state.ai_provider.generate_structured = cancel_then_return
    result = deliver(job_env, run)
    assert result["status"] == "cancelled" and result["job"]["status"] == "cancelled"
    with database.sessions() as db:
        draft = db.scalar(select(ResponseDraft))
        assert draft.response_text is None and draft.generation_status == "failed"


def worker_env(env, url):
    return {
        **os.environ,
        "DATABASE_URL": env[0].url.render_as_string(hide_password=False),
        "PYTHONPATH": str(Path.cwd() / "src"),
        "RESOLVEFLOW_EMBEDDING_MODEL_ROOT": str(
            Path.cwd().parents[1] / ".local/embeddings/minilm-v1"
        ),
        "RESOLVEFLOW_ENVIRONMENT": "test",
        "RESOLVEFLOW_AI_PROVIDER": "fixture",
        "RESOLVEFLOW_AI_LIVE_ENABLED": "false",
        "RESOLVEFLOW_AI_FREE_TIER_VERIFIED": "false",
        "GEMINI_API_KEY": "synthetic-test-key",
        "RESOLVEFLOW_REDIS_URL": url,
        "RESOLVEFLOW_JOB_QUEUE": env[6].job_queue,
        "RESOLVEFLOW_DOCUMENT_STORAGE_ROOT": str(env[6].document_storage_root),
    }


def test_real_rq_process_checkpoint_resume_and_broker_restart(env, real_embeddings, tmp_path):
    client, path, body, _ = setup(env, real_embeddings)
    with checkpoint_store(env[6], setup=True):
        pass
    database = Database(env[6])
    fixture = (env, client, path, body, database)
    try:
        with isolated_broker() as (url, broker):
            env[6].redis_url = SecretStr(url)
            run = start(fixture)
            assert reconcile(database, env[6]) == 1
            # A real dedicated RQ SpawnWorker; all graph/ML/retrieval work runs outside the API.
            with (tmp_path / "worker.log").open("w") as log:
                result = subprocess.run(
                    [sys.executable, "scripts/jobs.py", "worker", "--burst"],
                    env=worker_env(env, url),
                    stdout=log,
                    stderr=log,
                    timeout=60,
                )
            assert result.returncode == 0, "Worker process failed; inspect isolated worker log"
            paused = client.get("/api/v1" + location(fixture, run)).json()
            assert paused["status"] == "paused", paused["job"]
            assert paused["draft"]["can_approve"]
            assert (
                mutate(
                    client,
                    path + f"/drafts/{paused['draft']['id']}/review",
                    {"expected_version": 1, "action": "approved"},
                ).status_code
                == 200
            )
            assert mutate(client, location(fixture, run) + "/resume", {}).status_code == 202
            broker.terminate()
            broker.wait(timeout=5)
            assert reconcile(database, env[6]) == 0
        # New real broker with no Redis state; PostgreSQL still owns the accepted resume.
        with isolated_broker() as (url, _):
            env[6].redis_url = SecretStr(url)
            with database.sessions() as db:
                job = db.get(WorkflowJob, uuid.UUID(run["job"]["id"]))
                job.available_at = now() - timedelta(seconds=1)
                db.commit()
            assert reconcile(database, env[6]) == 1
            with (tmp_path / "resume.log").open("w") as log:
                result = subprocess.run(
                    [sys.executable, "scripts/jobs.py", "worker", "--burst"],
                    env=worker_env(env, url),
                    stdout=log,
                    stderr=log,
                    timeout=60,
                )
            assert result.returncode == 0
            done = client.get("/api/v1" + location(fixture, run)).json()
            assert done["status"] == "completed" and done["draft"]["id"] == paused["draft"]["id"]
    finally:
        database.dispose()


def test_workspace_slots_and_revoked_authorization(job_env):
    from resolveflow.db.models import WorkspaceMembership
    from resolveflow.jobs.transport import ownership

    env, _, _, _, database = job_env
    run = start(job_env)
    with checkpoint_store(env[6]) as (_, conn):
        with ownership(conn, f"job-workspace:{env[4]['id']}:0") as held:
            assert held
            result = deliver(job_env, run)
            assert result["job"]["status"] == "queued"
            assert result["job"]["attempts"] == 0
            assert result["job"]["error_code"] == "workspace_busy"
    with database.sessions() as db:
        membership = db.scalar(select(WorkspaceMembership))
        membership.role = "viewer"
        db.commit()
    deliver(job_env, run)
    with database.sessions() as db:
        job = db.get(WorkflowJob, uuid.UUID(run["job"]["id"]))
        assert job.status == "failed"
        assert job.error_code == "authorization_changed"
        assert db.scalar(select(func.count()).select_from(ResponseDraft)) == 0


def test_temporary_database_failure_and_retry(job_env, monkeypatch):
    from resolveflow.db.session import DatabaseUnavailableError
    from resolveflow.workflows import service

    run = start(job_env)
    original = service.drive

    def unavailable(*args, **kwargs):
        raise DatabaseUnavailableError

    monkeypatch.setattr(service, "drive", unavailable)
    pending = deliver(job_env, run)
    assert pending["job"]["attempts"] == 1
    assert pending["job"]["status"] == "queued"
    assert pending["job"]["error_code"] == "database_unavailable"
    monkeypatch.setattr(service, "drive", original)
    assert deliver(job_env, run)["job"]["status"] == "waiting_for_approval"


def test_real_worker_interruption_and_checkpoint_recovery(env, real_embeddings, tmp_path):
    import psutil
    from sqlalchemy import text

    from resolveflow.db.models import TicketActivity
    from resolveflow.workflows.models import WorkflowExecution

    client, path, body, _ = setup(env, real_embeddings)
    with checkpoint_store(env[6], setup=True):
        pass
    database = Database(env[6])
    fixture = (env, client, path, body, database)
    try:
        with isolated_broker() as (url, _):
            env[6].redis_url = SecretStr(url)
            run = start(fixture)
            assert reconcile(database, env[6]) == 1
            # Block retrieval in this disposable test DB after the first graph checkpoints.
            with env[0].connect() as blocked:
                blocked.execute(text("LOCK TABLE chunk_embeddings IN ACCESS EXCLUSIVE MODE"))
                with (tmp_path / "interrupted.log").open("w") as log:
                    worker = subprocess.Popen(
                        [sys.executable, "scripts/jobs.py", "worker", "--burst"],
                        env=worker_env(env, url),
                        stdout=log,
                        stderr=log,
                    )
                    try:
                        for _ in range(400):
                            with database.sessions() as db:
                                execution = db.get(WorkflowExecution, uuid.UUID(run["id"]))
                                if execution.current_stage == "retrieval":
                                    assert execution.state["completed_stages"] == [
                                        "classification",
                                        "priority",
                                    ]
                                    break
                            assert worker.poll() is None
                            time.sleep(0.025)
                        else:
                            pytest.fail("Dedicated worker did not reach the real retrieval node")
                    finally:
                        # Kill only this test's descendants to simulate abrupt process loss.
                        children = (
                            psutil.Process(worker.pid).children(recursive=True)
                            if worker.poll() is None
                            else []
                        )
                        for child in reversed(children):
                            try:
                                child.kill()
                            except psutil.NoSuchProcess:
                                pass
                        if worker.poll() is None:
                            worker.kill()
                        worker.wait(timeout=5)
                        psutil.wait_procs(children, timeout=5)
                blocked.rollback()
            with database.sessions() as db:
                job = db.get(WorkflowJob, uuid.UUID(run["job"]["id"]))
                assert job.status == "running"
                # Advance only the durable recovery deadline in the isolated fixture.
                job.available_at = now() - timedelta(seconds=1)
                db.commit()
            assert reconcile(database, env[6]) == 1
            with (tmp_path / "recovered.log").open("w") as log:
                result = subprocess.run(
                    [sys.executable, "scripts/jobs.py", "worker", "--burst"],
                    env=worker_env(env, url),
                    stdout=log,
                    stderr=log,
                    timeout=60,
                )
            assert result.returncode == 0
            paused = client.get("/api/v1" + location(fixture, run)).json()
            assert paused["status"] == "paused"
            assert paused["job"]["attempts"] == 2
            assert len(paused["completed_stages"]) == 6
            with database.sessions() as db:
                assert db.scalar(select(func.count()).select_from(ResponseDraft)) == 1
                assert db.scalar(select(func.count()).select_from(TicketActivity)) == 1
    finally:
        database.dispose()


def test_worker_pool_configuration_and_transport_allowlist(job_env):
    from rq.serializers import JSONSerializer

    from resolveflow.jobs.transport import IdentifierJob, WorkflowWorker, connection, queue

    settings = job_env[0][6]
    with isolated_broker() as (url, _):
        settings.redis_url = SecretStr(url)
        with connection(settings) as conn:
            worker = WorkflowWorker(
                [queue(settings, conn)],
                connection=conn,
                serializer=JSONSerializer,
                job_class=IdentifierJob,
            )
            assert worker.worker_ttl == 60 and worker.dequeue_timeout == 45
            assert worker.disable_default_exception_handler
            assert not worker.log_job_description
            bad = IdentifierJob.create(
                "builtins.print",
                args=["untrusted payload"],
                connection=conn,
                serializer=JSONSerializer,
            )
            with pytest.raises(ValueError, match="Unrecognized workflow task"):
                bad.perform()
