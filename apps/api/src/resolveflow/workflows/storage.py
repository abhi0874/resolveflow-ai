"""Server-only checkpoint access and session locks. Never accept client thread IDs."""

import hashlib
from contextlib import contextmanager

import psycopg
from fastapi import HTTPException
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg.rows import dict_row
from sqlalchemy.engine import make_url

from resolveflow.db.session import DatabaseUnavailableError

SCHEMA = "workflow_checkpoints"


def thread_id(execution) -> str:
    return f"{execution.workspace_id}:{execution.id}"


def lock_key(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big", signed=True)


@contextmanager
def checkpoint_store(settings, *, setup=False):
    if settings.database_url is None:
        raise DatabaseUnavailableError
    url = make_url(settings.database_url.get_secret_value()).set(drivername="postgresql")
    try:
        with psycopg.connect(
            url.render_as_string(hide_password=False),
            autocommit=True,
            row_factory=dict_row,
            prepare_threshold=0,
            connect_timeout=settings.db_connect_timeout,
            options=(
                f"-c search_path={SCHEMA} -c statement_timeout={settings.db_statement_timeout_ms}"
            ),
        ) as conn:
            # Only primitive application state and LangGraph's built-in safe types are decoded.
            saver = PostgresSaver(
                conn, serde=JsonPlusSerializer(pickle_fallback=False, allowed_msgpack_modules=[])
            )
            if setup:
                conn.execute("SELECT pg_advisory_lock(%s)", (lock_key("workflow-schema"),))
                try:
                    saver.setup()
                finally:
                    conn.execute("SELECT pg_advisory_unlock(%s)", (lock_key("workflow-schema"),))
            else:
                version = conn.execute(
                    "SELECT max(v) AS version FROM checkpoint_migrations"
                ).fetchone()
                if version["version"] != len(saver.MIGRATIONS) - 1:
                    raise HTTPException(503, detail="workflow_schema_unavailable")
            yield saver, conn
    except psycopg.Error:
        raise DatabaseUnavailableError from None


@contextmanager
def execution_lock(conn, execution, concurrency: int):
    # Locks are released on connection loss, so a dead worker never leaves a durable mutex.
    key = lock_key("execution:" + thread_id(execution))
    if not conn.execute("SELECT pg_try_advisory_lock(%s) AS ok", (key,)).fetchone()["ok"]:
        raise HTTPException(409, detail="workflow_busy")
    slot = None
    try:
        for index in range(concurrency):
            candidate = lock_key(f"workflow-slot:{index}")
            if conn.execute("SELECT pg_try_advisory_lock(%s) AS ok", (candidate,)).fetchone()["ok"]:
                slot = candidate
                break
        if slot is None:
            raise HTTPException(429, detail="workflow_busy", headers={"Retry-After": "5"})
        yield
    finally:
        if slot is not None:
            conn.execute("SELECT pg_advisory_unlock(%s)", (slot,))
        conn.execute("SELECT pg_advisory_unlock(%s)", (key,))


def check_ownership(saver, conn):
    # PostgresSaver may persist writes in another graph thread. Serialize health
    # probes with its cursor lock so they cannot enter an active pipeline.
    with saver.lock:
        conn.execute("SELECT 1")
