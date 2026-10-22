import importlib

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from resolveflow.core.config import Settings
from resolveflow.main import create_app


def test_missing_database_ready_503_health_still_ok(client):
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "database_unavailable", "message": "Database is unavailable"}
    }
    assert client.get("/api/v1/health").status_code == 200


@pytest.mark.parametrize(
    "url",
    [
        "",
        "sqlite:///test.db",
        "postgresql://host/db",
        "postgresql://user@host",
        "postgresql://user@host:99999/db",
    ],
)
def test_invalid_database_configuration(url):
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, database_url=url)
    assert "DATABASE_URL must be a PostgreSQL URL" in str(error.value)
    assert "input_value=" not in str(error.value)


def test_database_url_normalization_and_secret_repr(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:secret-value@host:5432/db?sslmode=require")
    settings = Settings(_env_file=None)
    assert settings.database_url.get_secret_value().startswith("postgresql+psycopg://")
    assert "secret-value" not in repr(settings)
    assert "sslmode=require" in settings.database_url.get_secret_value()


def test_import_and_lifespan_do_not_connect_and_query_failure_is_safe(monkeypatch):
    attempts = []

    def fail(_self, *args, **kwargs):
        attempts.append(True)
        raise OperationalError("SELECT secret", {}, Exception("sensitive-password-host"))

    monkeypatch.setattr(Engine, "connect", fail)
    import resolveflow.main

    importlib.reload(resolveflow.main)
    settings = Settings(_env_file=None, database_url="postgresql://user:secret@localhost/db")
    with TestClient(create_app(settings)) as client:
        assert attempts == []
        assert client.get("/api/v1/health").status_code == 200
        assert attempts == []
        response = client.get("/api/v1/ready")
        assert response.status_code == 503
        assert "secret" not in response.text and "host" not in response.text
        assert attempts == [True]
