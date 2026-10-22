import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from resolveflow.core.config import Settings
from resolveflow.main import create_asgi_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    settings = Settings(database_url=None, _env_file=None, environment="test")
    with TestClient(create_asgi_app(settings)) as test_client:
        yield test_client


def pytest_addoption(parser):
    parser.addoption(
        "--run-db", action="store_true", help="Run isolated PostgreSQL integration tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires real isolated PostgreSQL")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-db"):
        return
    skip = pytest.mark.skip(reason="Use --run-db with TEST_DATABASE_ADMIN_URL or local_db.py test")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def database_factory():
    raw = os.environ.get("TEST_DATABASE_ADMIN_URL")
    if not raw:
        pytest.fail("TEST_DATABASE_ADMIN_URL is required when --run-db is selected")
    admin_url = make_url(raw)
    if (
        admin_url.drivername != "postgresql+psycopg"
        or admin_url.database != "postgres"
        or admin_url.host not in {"127.0.0.1", "localhost", "::1"}
        or admin_url.query
    ):
        pytest.fail(
            "Test admin URL must target the local postgres maintenance DB, without query options"
        )
    admin = create_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
        hide_parameters=True,
        connect_args={"connect_timeout": 3},
    )
    created = []

    def create():
        name = f"resolveflow_test_{uuid.uuid4().hex}"
        marker = f"resolveflow-pytest-{uuid.uuid4().hex}"
        with admin.connect() as conn:
            cursor = conn.connection.driver_connection.cursor()
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            cursor.execute(
                sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                    sql.Identifier(name), sql.Literal(marker)
                )
            )
            cursor.close()
        engine = create_engine(
            admin_url.set(database=name), poolclass=NullPool, hide_parameters=True
        )
        created.append((name, marker, engine))
        return engine

    yield create
    for name, marker, engine in reversed(created):
        engine.dispose()
        with admin.connect() as conn:
            actual = conn.execute(
                text(
                    "SELECT shobj_description(oid, 'pg_database') "
                    "FROM pg_database WHERE datname=:name"
                ),
                {"name": name},
            ).scalar()
            if actual != marker or not name.startswith("resolveflow_test_"):
                raise RuntimeError("Test database ownership marker mismatch; refusing cleanup")
            cursor = conn.connection.driver_connection.cursor()
            cursor.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
            cursor.close()
    admin.dispose()


@pytest.fixture(autouse=True)
def isolate_model_configuration(tmp_path, monkeypatch):
    # Existing regressions must not load or depend on a developer's trained model.
    monkeypatch.setenv("RESOLVEFLOW_CLASSIFIER_ARTIFACT_ROOT", str(tmp_path / "models"))

    monkeypatch.setenv("RESOLVEFLOW_EMBEDDING_MODEL_ROOT", str(tmp_path / "embeddings"))
