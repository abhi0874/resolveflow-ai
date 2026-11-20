from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from google_fixture import GoogleFixture
from pydantic import SecretStr
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from test_auth_workspaces import auth_env as base_auth_env
from test_auth_workspaces import mutate, register, workspace
from test_identity_email import local, send, token

from resolveflow.db.models import GoogleFlow, IdentityEmail, ProviderIdentity, User
from resolveflow.services import google_oidc

auth_env = base_auth_env
pytestmark = pytest.mark.integration
START = "/auth/google/start"
COMPLETE = "/api/v1/auth/google/complete"


@pytest.fixture
def google(auth_env, monkeypatch):
    engine, app, client = auth_env
    settings = app.app.state.settings
    settings.google_enabled = True
    settings.google_client_id = "local-fixture"
    settings.google_client_secret = SecretStr("local-fixture-only")
    settings.google_redirect_uri = "http://127.0.0.1:3000/auth/google/callback"
    provider = GoogleFixture()
    monkeypatch.setattr(google_oidc, "provider_client", provider.client)
    return engine, app, client, provider


def begin(client, provider, destination="/app"):
    started = mutate(client, START, {"destination": destination})
    assert started.status_code == 200
    return provider.authorize(started.json()["url"])


def test_disabled(auth_env):
    assert mutate(auth_env[2], START).status_code == 503


def test_google_sessions_workspace_and_recovery(google):
    engine, app, client, provider = google
    with closing(TestClient(app)) as owner:
        register(owner)
        other = workspace(owner)
    for destination in ["/app/analytics", "//example.invalid"]:
        callback = begin(client, provider, destination)
        response = client.post(COMPLETE, json=callback)
        assert response.status_code == 200
        assert response.json()["destination"] == (
            "/app" if destination.startswith("//") else destination
        )
        assert client.get("/api/v1/auth/me").json()["email"] == "fixture@example.com"
        assert client.get("/api/v1/workspaces").json() == []
        assert client.get("/api/v1/workspaces/" + other["id"]).status_code == 404
        old = client.cookies.get("resolveflow_session")
        assert mutate(client, "/auth/logout").status_code == 204
        with closing(TestClient(app)) as replay:
            replay.cookies.set("resolveflow_session", old)
            assert replay.get("/api/v1/auth/me").status_code == 401
    assert (
        mutate(client, "/auth/password/request", {"email": "fixture@example.com"}).status_code
        == 202
    )
    assert (
        mutate(
            client, "/auth/login", {"email": "fixture@example.com", "password": "anything"}
        ).status_code
        == 401
    )
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ProviderIdentity)) == 1
        assert (
            db.scalar(select(User).where(User.email == "fixture@example.com")).password_hash is None
        )
        assert not db.scalar(select(IdentityEmail).where(IdentityEmail.purpose == "reset"))


def test_password_collision(google):
    engine, _, client, provider = google
    original = register(client, "fixture@example.com")
    mutate(client, "/auth/logout")
    response = client.post(COMPLETE, json=begin(client, provider))
    assert response.status_code == 400
    assert client.get("/api/v1/auth/me").status_code == 401
    with Session(engine) as db:
        assert not db.scalar(select(ProviderIdentity))
        assert str(db.scalar(select(User)).id) == original["id"]


@pytest.mark.parametrize(
    ("claim", "value"),
    [
        ("iss", "other"),
        ("aud", "other"),
        ("azp", "other"),
        ("exp", 1),
        ("nonce", None),
        ("nonce", "wrong"),
        ("email_verified", False),
        ("email_verified", "true"),
        ("sub", ""),
        ("signature", None),
    ],
)
def test_reject_invalid_claims(google, claim, value):
    engine, _, client, provider = google
    if claim == "signature":
        provider.signing_key = GoogleFixture().key
    else:
        provider.claims[claim] = value
    body = begin(client, provider)
    assert client.post(COMPLETE, json=body).status_code == 400
    assert client.post(COMPLETE, json=body).status_code == 400
    assert provider.calls == 1
    with Session(engine) as db:
        assert not db.scalar(select(User))


@pytest.mark.parametrize(
    "case",
    ["wrong-state", "other-browser", "expired", "bad-verifier", "missing-verifier", "used-code"],
)
def test_reject_invalid_transaction(google, case):
    engine, app, client, provider = google
    body = begin(client, provider)
    if case == "wrong-state":
        body["state"] = "x" * 43
    if case == "other-browser":
        with closing(TestClient(app)) as other:
            other.get("/api/v1/auth/csrf")
            assert other.post(COMPLETE, json=body).status_code == 400
            assert provider.calls == 0
        return
    if case == "used-code":
        provider.grants.pop(body["code"])
    if case in {"bad-verifier", "missing-verifier", "expired"}:
        with Session(engine) as db:
            values = (
                {"expires_at": func.now()}
                if case == "expired"
                else {"verifier": "" if case == "missing-verifier" else "x" * 43}
            )
            db.execute(update(GoogleFlow).values(**values))
            db.commit()
    assert client.post(COMPLETE, json=body).status_code == 400
    assert client.get("/api/v1/auth/me").status_code == 401


def test_concurrent_replay(google):
    _, app, client, provider = google
    body = begin(client, provider)
    cookie = client.cookies.get("resolveflow_session")

    def submit(_):
        with closing(TestClient(app)) as browser:
            browser.cookies.set("resolveflow_session", cookie)
            return browser.post(COMPLETE, json=body).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, range(2))) == [200, 400]
    assert provider.calls == 1


def test_required_inbox_proof_is_bound_to_google_session(google):
    engine, app, client, provider = google
    local((engine, app, client), required=True)
    response = client.post(COMPLETE, json=begin(client, provider))
    assert response.json()["destination"] == "/verification-required"
    assert client.get("/api/v1/workspaces").status_code == 403
    _, capture = send((engine, app, client))
    proof = {"token": token(capture)}
    with closing(TestClient(app)) as stranger:
        assert mutate(stranger, "/auth/verification/confirm", proof).status_code == 400
    assert mutate(client, "/auth/verification/confirm", proof).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post(COMPLETE, json=begin(client, provider)).json()["destination"] == "/app"
    assert client.get("/api/v1/auth/me").json()["email_verified"]
    assert client.get("/api/v1/workspaces").status_code == 200


def test_two_browsers_register_one_identity(google):
    engine, app, first, provider = google
    with closing(TestClient(app)) as second:
        callbacks = [(browser, begin(browser, provider)) for browser in (first, second)]

        def submit(item):
            browser, body = item
            return browser.post(COMPLETE, json=body).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, callbacks))
        assert 200 in results
        assert set(results) <= {200, 400}
        successful = [
            browser.get("/api/v1/auth/me").json()["id"]
            for (browser, _), status in zip(callbacks, results, strict=True)
            if status == 200
        ]
        assert len(set(successful)) == 1
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(User)) == 1
            assert db.scalar(select(func.count()).select_from(ProviderIdentity)) == 1
