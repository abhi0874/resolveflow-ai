"""Run real browser/API tests in a newly created local PostgreSQL database."""

import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import ExitStack
from pathlib import Path
from urllib.request import urlopen

from alembic import command
from alembic.config import Config
from broker_fixture import isolated_broker
from local_db import API, ROOT, admin_connect, load_state, url
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


def main() -> int:
    # Never attach test traffic to an unrelated server already using these ports.
    for port in (3100, 8100):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                raise RuntimeError(f"Test port {port} is occupied; no tests were run") from None
    state = load_state()
    name = f"resolveflow_test_{uuid.uuid4().hex}"
    marker = f"resolveflow-browser-{uuid.uuid4().hex}"
    resources = ExitStack()
    children = []
    logs = []
    with admin_connect(state) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        conn.execute(
            sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                sql.Identifier(name), sql.Literal(marker)
            )
        )
    storage = tempfile.TemporaryDirectory(prefix="resolveflow-browser-storage-")
    engine = create_engine(make_url(url(state, admin=True)).set(database=name))
    try:
        sys.path.insert(0, str(API / "src"))
        config = Config(str(API / "alembic.ini"))
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
        from resolveflow.core.config import Settings
        from resolveflow.ml.artifact import TrainingConfig
        from resolveflow.ml.training import train
        from resolveflow.workflows.storage import checkpoint_store

        with checkpoint_store(
            Settings(_env_file=None, database_url=engine.url.render_as_string(hide_password=False)),
            setup=True,
        ):
            pass

        model_root = Path(storage.name) / "models"
        train(model_root, "browser-v1", TrainingConfig())
        broker_url, _ = resources.enter_context(isolated_broker())
        env = {
            "RESOLVEFLOW_REDIS_URL": broker_url,
            "RESOLVEFLOW_JOB_QUEUE": "browser-" + uuid.uuid4().hex,
            "RESOLVEFLOW_JOB_RECONCILE_SECONDS": "1",
            **os.environ,
            "DATABASE_URL": engine.url.render_as_string(hide_password=False),
            "RESOLVEFLOW_ENVIRONMENT": "test",
            "RESOLVEFLOW_AI_PROVIDER": "fixture",
            "RESOLVEFLOW_AI_LIVE_ENABLED": "false",
            "RESOLVEFLOW_AI_FREE_TIER_VERIFIED": "false",
            "GEMINI_API_KEY": "synthetic-browser-test-key",
            "RESOLVEFLOW_AI_DAILY_GLOBAL": "100",
            "RESOLVEFLOW_AI_DAILY_WORKSPACE": "30",
            "RESOLVEFLOW_AI_DAILY_USER": "25",
            "RESOLVEFLOW_DOCUMENT_STORAGE_ROOT": str(Path(storage.name) / "documents"),
            "RESOLVEFLOW_CLASSIFIER_ARTIFACT_ROOT": str(model_root),
            "RESOLVEFLOW_CLASSIFIER_MODEL_VERSION": "browser-v1",
            "RESOLVEFLOW_CLASSIFIER_THRESHOLD": "0.45",
            "RESOLVEFLOW_TRUSTED_ORIGINS": '["http://127.0.0.1:3100"]',
            "API_INTERNAL_URL": "http://127.0.0.1:8100",
            "RESOLVEFLOW_E2E_ISOLATED": "1",
            "NEXT_TELEMETRY_DISABLED": "1",
        }
        output = ROOT / ".cache/e2e"
        output.mkdir(parents=True, exist_ok=True)
        for role in ("worker", "dispatch"):
            log = (output / f"{role}.log").open("w")
            logs.append(log)
            children.append(
                subprocess.Popen(
                    [sys.executable, "scripts/jobs.py", role],
                    cwd=API,
                    env=env,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
            )
        commands = [
            (
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "resolveflow.main:app",
                    "--app-dir",
                    "src",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8100",
                    "--no-proxy-headers",
                ],
                API,
                "/api/v1/ready",
                8100,
            ),
            (["npm", "run", "start", "--", "--port", "3100"], ROOT / "apps/web", "/login", 3100),
        ]
        for args, cwd, path, port in commands:
            log = (output / f"{port}.log").open("w")
            logs.append(log)
            process = subprocess.Popen(
                args, cwd=cwd, env=env, stdout=log, stderr=log, start_new_session=True
            )
            children.append(process)
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError(f"Server failed; see .cache/e2e/{port}.log")
                try:
                    with urlopen(f"http://127.0.0.1:{port}{path}", timeout=1) as response:
                        ready_marker = "Uvicorn running on" if port == 8100 else "Ready in"
                        own_log = (output / f"{port}.log").read_text()
                        if (
                            response.status == 200
                            and ready_marker in own_log
                            and process.poll() is None
                        ):
                            break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Test server startup timed out")
        print("Running browser tests against an isolated database on ports 3100/8100.", flush=True)
        return subprocess.run(
            ["npm", "run", "test:e2e", "--", *sys.argv[1:]], cwd=ROOT / "apps/web", env=env
        ).returncode
    finally:
        for process in reversed(children):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        for log in logs:
            log.close()
        resources.close()
        storage.cleanup()
        engine.dispose()
        with admin_connect(state) as conn:
            actual = conn.execute(
                "SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname=%s",
                (name,),
            ).fetchone()
            if actual != (marker,):
                raise RuntimeError("Database ownership marker mismatch; refusing cleanup")
            conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
        print(
            "Isolated browser database and storage removed; development data preserved.", flush=True
        )


if __name__ == "__main__":
    sys.exit(main())
