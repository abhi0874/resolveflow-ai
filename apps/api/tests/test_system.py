import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.middleware.cors import CORSMiddleware

from resolveflow.core.config import Settings
from resolveflow.main import create_app, create_asgi_app


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "resolveflow-api"}


def test_info(client: TestClient) -> None:
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    assert response.json() == {
        "name": "ResolveFlow AI",
        "version": "0.1.0",
        "description": "AI-powered customer support platform",
    }


def test_openapi_and_docs(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert set(schema["paths"]) == {
        "/api/v1/health",
        "/api/v1/info",
        "/api/v1/ready",
        "/api/v1/auth/csrf",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
        "/api/v1/workspaces/{workspace_id}/tickets",
        "/api/v1/workspaces/{workspace_id}/tickets/assignees",
        "/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}",
        "/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/notes",
        "/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/classify",
        "/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/generate-response",
        "/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/response-config",
        "/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/drafts",
        "/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/drafts/{draft_id}",
        "/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/drafts/{draft_id}/review",
        "/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/activities",
        "/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/workflows",
        "/api/v1/workspaces/{workspace_id}/workflows/{execution_id}",
        "/api/v1/workspaces/{workspace_id}/workflows/{execution_id}/resume",
        "/api/v1/workspaces/{workspace_id}/workflows/{execution_id}/cancel",
        "/api/v1/workspaces/{workspace_id}/documents",
        "/api/v1/workspaces/{workspace_id}/documents/config",
        "/api/v1/workspaces/{workspace_id}/documents/{document_id}",
        "/api/v1/workspaces/{workspace_id}/documents/{document_id}/chunks",
        "/api/v1/workspaces/{workspace_id}/documents/{document_id}/download",
        "/api/v1/workspaces/{workspace_id}/documents/{document_id}/retry",
        "/api/v1/workspaces/{workspace_id}/documents/{document_id}/index",
        "/api/v1/workspaces/{workspace_id}/knowledge-base/search",
        "/api/v1/workspaces/{workspace_id}/analytics/overview",
        "/api/v1/workspaces",
        "/api/v1/workspaces/{workspace_id}",
        "/api/v1/workspaces/{workspace_id}/members",
        "/api/v1/workspaces/{workspace_id}/members/{user_id}",
    }
    assert schema["paths"]["/api/v1/health"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"].endswith("/HealthResponse")
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200


def test_not_found_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/missing")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "http_error", "message": "Not Found"}}


def test_disallowed_method(client: TestClient) -> None:
    response = client.post("/api/v1/health")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "http_error"
    assert "GET" in response.headers["allow"]


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://127.0.0.1:3000"])
def test_local_cors(client: TestClient, origin: str) -> None:
    response = client.get("/api/v1/health", headers={"Origin": origin})
    assert response.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in response.headers


def test_cors_rejects_unknown_origin(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "https://untrusted.example"})
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-methods"] == "GET"


def test_errors_do_not_expose_internal_values() -> None:
    application = create_app(Settings(database_url=None, _env_file=None, environment="test"))

    @application.get("/test-error")
    async def broken_route() -> None:
        raise RuntimeError("sensitive-internal-value")

    @application.get("/test-validation")
    async def validated_route(count: int) -> dict[str, int]:
        return {"count": count}

    wrapped = CORSMiddleware(application, allow_origins=["http://localhost:3000"])
    with TestClient(wrapped, raise_server_exceptions=False) as client:
        response = client.get("/test-error", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 500
        assert response.json() == {
            "error": {"code": "internal_error", "message": "An unexpected error occurred"}
        }
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        invalid = client.get("/test-validation?count=sensitive-internal-value")
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "validation_error"
        assert "sensitive-internal-value" not in invalid.text


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESOLVEFLOW_ENVIRONMENT", "production")
    monkeypatch.setenv("RESOLVEFLOW_TRUSTED_ORIGINS", '["https://example.com"]')
    monkeypatch.setenv("RESOLVEFLOW_CORS_ORIGINS", '["https://example.com"]')
    monkeypatch.setenv("RESOLVEFLOW_DOCS_ENABLED", "false")
    settings = Settings(database_url=None, _env_file=None)
    assert settings.environment == "production"
    assert settings.cors_origins == ["https://example.com"]
    with TestClient(create_asgi_app(settings)) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


@pytest.mark.parametrize("origin", ["*", "https://example.com/path", "ftp://example.com"])
def test_invalid_cors_settings(origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(database_url=None, _env_file=None, cors_origins=[origin])
