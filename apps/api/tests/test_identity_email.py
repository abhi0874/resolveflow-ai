"""Real DB identity/security tests and actual SMTP delivery into an isolated Mailpit."""

import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from urllib.request import urlopen

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from test_auth_workspaces import PASSWORD, mutate, register, workspace
from test_auth_workspaces import auth_env as base_auth_env
from test_database import HASH, migrate

from resolveflow.core.config import Settings
from resolveflow.db.models import (
    AuthSession,
    IdentityAudit,
    IdentityEmail,
    User,
    WorkspaceMembership,
)
from resolveflow.db.session import Database
from resolveflow.jobs.email import process
from resolveflow.main import create_asgi_app
from resolveflow.services.auth import digest, valid_password
from resolveflow.services.email_delivery import DeliveryResult
from scripts.mailpit_fixture import isolated_mailpit

pytestmark = pytest.mark.integration
auth_env = base_auth_env
NEW_PASSWORD = "a replacement secure passphrase 87!"


class Capture:
    def __init__(self, result=None):
        self.result = result or DeliveryResult(True)
        self.links = []

    def send_verification(self, recipient, link, message_id):
        self.links.append(link)
        return self.result

    send_recovery = send_verification


def send(auth_env, purpose="verify", adapter=None):
    engine, app, _ = auth_env
    settings = app.app.state.settings
    with Session(engine) as db:
        row = db.scalar(
            select(IdentityEmail)
            .where(IdentityEmail.purpose == purpose)
            .order_by(IdentityEmail.created_at.desc())
        )
        identifier = row.id
    database = Database(settings)
    adapter = adapter or Capture()
    try:
        process(database, settings, identifier, adapter)
    finally:
        database.dispose()
    return identifier, adapter


def local(auth_env, required=False):
    settings = auth_env[1].app.state.settings
    settings.email_delivery = "local"
    settings.require_email_verification = required
    return settings


def token(capture):
    return capture.links[-1].split("#token=")[1]


def test_verification_lifecycle_policy_and_hash_only(auth_env):
    engine, _, client = auth_env
    settings = local(auth_env)
    user = register(client, "verify@example.com")
    old_cookie = client.cookies.get("resolveflow_session")
    settings.require_email_verification = True
    assert client.get("/api/v1/workspaces").status_code == 403
    assert (
        mutate(client, "/auth/login", {"email": user["email"], "password": PASSWORD}).status_code
        == 403
    )
    identifier, capture = send(auth_env)
    raw = token(capture)
    with Session(engine) as db:
        row = db.get(IdentityEmail, identifier)
        assert row.token_hash == digest(raw) and row.token_hash != raw
        assert row.status == "sent" and row.attempts == 1 and row.consumed_at is None
    assert (
        mutate(
            client, "/auth/verification/confirm", {"token": raw, "password": "wrong"}
        ).status_code
        == 400
    )
    assert (
        mutate(
            client, "/auth/verification/confirm", {"token": raw, "password": PASSWORD}
        ).status_code
        == 200
    )
    assert (
        mutate(
            client, "/auth/verification/confirm", {"token": raw, "password": PASSWORD}
        ).status_code
        == 400
    )
    with Session(engine) as db:
        saved = db.get(User, uuid.UUID(user["id"]))
        assert saved.email_verified and saved.email_verification_source == "local"
        assert (
            db.scalar(select(AuthSession).where(AuthSession.token_hash == digest(old_cookie)))
            is None
        )
        assert db.scalar(select(func.count()).select_from(IdentityAudit)) >= 2
    assert (
        mutate(client, "/auth/login", {"email": user["email"], "password": PASSWORD}).status_code
        == 200
    )


@pytest.mark.parametrize("purpose", ["verify", "reset"])
@pytest.mark.parametrize(
    "failure", ["invalid", "expired", "email_changed", "inactive", "wrong_account"]
)
def test_invalid_identity_links_fail_closed(auth_env, purpose, failure):
    engine, app, client = auth_env
    local(auth_env)
    user = register(client)
    if purpose == "reset":
        assert mutate(client, "/auth/password/request", {"email": user["email"]}).status_code == 202
    identifier, capture = send(auth_env, purpose)
    raw = token(capture)
    with Session(engine) as db:
        if failure == "expired":
            db.get(IdentityEmail, identifier).expires_at = datetime.now(UTC) - timedelta(seconds=1)
        if failure == "email_changed":
            target = db.get(User, uuid.UUID(user["id"]))
            target.email_verified_at = datetime.now(UTC)
            target.verified_email = target.email
            target.email = "changed@example.com"
            assert not target.email_verified
        if failure == "inactive":
            db.get(User, uuid.UUID(user["id"])).account_status = "inactive"
        db.commit()
    if failure == "invalid":
        raw = "x" * 43
    if failure == "wrong_account":
        mutate(client, "/auth/logout")
        register(client)
    path = "verification" if purpose == "verify" else "password"
    body = {"token": raw, "password": PASSWORD if purpose == "verify" else NEW_PASSWORD}
    if purpose == "reset":
        body["password_confirmation"] = NEW_PASSWORD
    assert mutate(client, f"/auth/{path}/confirm", body).status_code == 400
    with Session(engine) as db:
        assert db.get(IdentityEmail, identifier).consumed_at is None
        assert valid_password(db.get(User, uuid.UUID(user["id"])).password_hash, PASSWORD)


def test_password_reset_sessions_replay_and_tenant_privileges(auth_env):
    engine, app, client = auth_env
    local(auth_env)
    user = register(client)
    space = workspace(client)
    with TestClient(create_asgi_app(app.app.state.settings)) as other:
        assert (
            mutate(other, "/auth/login", {"email": user["email"], "password": PASSWORD}).status_code
            == 200
        )
        assert mutate(client, "/auth/password/request", {"email": user["email"]}).status_code == 202
        _, capture = send(auth_env, "reset")
        body = {
            "token": token(capture),
            "password": NEW_PASSWORD,
            "password_confirmation": NEW_PASSWORD,
        }
        assert client.post("/api/v1/auth/password/confirm", json=body).status_code == 403
        assert (
            mutate(client, "/auth/password/confirm", {**body, "password": "short"}).status_code
            == 422
        )
        assert mutate(client, "/auth/password/confirm", body).status_code == 200
        assert other.get("/api/v1/auth/me").status_code == 401
        assert client.get("/api/v1/auth/me").status_code == 401
        assert mutate(client, "/auth/password/confirm", body).status_code == 400
    assert (
        mutate(client, "/auth/login", {"email": user["email"], "password": PASSWORD}).status_code
        == 401
    )
    assert (
        mutate(
            client, "/auth/login", {"email": user["email"], "password": NEW_PASSWORD}
        ).status_code
        == 200
    )
    with Session(engine) as db:
        saved = db.get(User, uuid.UUID(user["id"]))
        assert saved.password_hash.startswith("$argon2id$") and valid_password(
            saved.password_hash, NEW_PASSWORD
        )
        assert saved.credential_version == 2
        members = db.scalars(
            select(WorkspaceMembership).where(WorkspaceMembership.user_id == saved.id)
        ).all()
        assert (
            len(members) == 1
            and str(members[0].workspace_id) == space["id"]
            and members[0].role == "owner"
        )


def test_request_enumeration_cooldown_invalidation_and_limits(auth_env):
    engine, _, client = auth_env
    settings = local(auth_env)
    user = register(client)
    for path in ("verification", "password"):
        known = mutate(client, f"/auth/{path}/request", {"email": user["email"]})
        unknown = mutate(client, f"/auth/{path}/request", {"email": "absent@example.com"})
        assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(IdentityEmail)) == 2
    first, capture = send(auth_env)
    with Session(engine) as db:
        db.get(IdentityEmail, first).created_at = datetime.now(UTC) - timedelta(minutes=2)
        db.commit()
    mutate(client, "/auth/verification/request", {"email": user["email"]})
    assert (
        mutate(
            client, "/auth/verification/confirm", {"token": token(capture), "password": PASSWORD}
        ).status_code
        == 400
    )
    for _ in range(8):
        mutate(client, "/auth/verification/request", {"email": user["email"]})
    assert mutate(client, "/auth/verification/request", {"email": user["email"]}).status_code == 429
    settings.require_email_verification = True
    body = {"email": "new@example.com", "password": PASSWORD, "password_confirmation": PASSWORD}
    a = mutate(client, "/auth/register", body)
    b = mutate(client, "/auth/register", body)
    assert a.status_code == b.status_code == 202 and a.json() == b.json()


def test_bounded_failure_idempotency_and_redaction(auth_env, caplog):
    engine, app, client = auth_env
    settings = local(auth_env)
    register(client)
    capture = Capture(DeliveryResult(False, "smtp_unavailable", True))
    identifier, _ = send(auth_env, adapter=capture)
    database = Database(settings)
    try:
        for attempt in (2, 3):
            process(
                database, settings, identifier, capture
            )  # Backoff cannot be bypassed by duplicate message.
            assert len(capture.links) == attempt - 1
            with Session(engine) as db:
                db.get(IdentityEmail, identifier).available_at = datetime.now(UTC) - timedelta(
                    seconds=1
                )
                db.commit()
            process(database, settings, identifier, capture)
        process(database, settings, identifier, capture)
    finally:
        database.dispose()
    assert len(capture.links) == 3 and len(set(capture.links)) == 3
    with Session(engine) as db:
        row = db.get(IdentityEmail, identifier)
        assert row.status == "failed" and row.attempts == 3
    assert all(token(CaptureWithLink(link)) not in caplog.text for link in capture.links)


class CaptureWithLink:
    def __init__(self, link):
        self.links = [link]


def test_concurrent_delivery_and_reset_consumption(auth_env):
    engine, app, client = auth_env
    settings = local(auth_env)
    user = register(client)
    mutate(client, "/auth/password/request", {"email": user["email"]})
    with Session(engine) as db:
        identifier = db.scalar(select(IdentityEmail.id).where(IdentityEmail.purpose == "reset"))
    capture = Capture()
    database = Database(settings)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: process(database, settings, identifier, capture), range(2)))
    finally:
        database.dispose()
    assert len(capture.links) == 1

    def consume(_):
        with TestClient(create_asgi_app(settings)) as independent:
            return mutate(
                independent,
                "/auth/password/confirm",
                {
                    "token": token(capture),
                    "password": NEW_PASSWORD,
                    "password_confirmation": NEW_PASSWORD,
                },
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(consume, range(2)))
    assert sorted(results) == [200, 400]


def test_actual_smtp_verification_and_reset_mail(auth_env):
    engine, app, client = auth_env
    settings = local(auth_env)
    with isolated_mailpit() as (port, inbox):
        settings.smtp_port = port
        user = register(client, "inbox@example.com")
        with Session(engine) as db:
            identifier = db.scalar(select(IdentityEmail.id))
        database = Database(settings)
        try:
            process(database, settings, identifier)
        finally:
            database.dispose()
        with urlopen(inbox + "/api/v1/messages") as response:
            listing = json.load(response)
        assert len(listing["messages"]) == 1
        mid = listing["messages"][0]["ID"]
        with urlopen(inbox + "/api/v1/message/" + mid) as response:
            message = json.load(response)
        match = re.search(
            r"http://127\.0\.0\.1:3000/verify-email#token=([A-Za-z0-9_-]{43})", message["Text"]
        )
        assert match is not None
        assert (
            mutate(
                client, "/auth/verification/confirm", {"token": match[1], "password": PASSWORD}
            ).status_code
            == 200
        )
        assert mutate(client, "/auth/password/request", {"email": user["email"]}).status_code == 202
        with Session(engine) as db:
            identifier = db.scalar(select(IdentityEmail.id).where(IdentityEmail.purpose == "reset"))
        database = Database(settings)
        try:
            process(database, settings, identifier)
        finally:
            database.dispose()
        with urlopen(inbox + "/api/v1/messages") as response:
            listing = json.load(response)
        assert len(listing["messages"]) == 2
        with urlopen(inbox + "/api/v1/message/" + listing["messages"][0]["ID"]) as response:
            message = json.load(response)
        match = re.search(r"/reset-password#token=([A-Za-z0-9_-]{43})", message["Text"])
        assert match is not None
        assert (
            mutate(
                client,
                "/auth/password/confirm",
                {
                    "token": match[1],
                    "password": NEW_PASSWORD,
                    "password_confirmation": NEW_PASSWORD,
                },
            ).status_code
            == 200
        )


def test_safe_settings_and_legacy_migration(database_factory):
    for override in (
        {"environment": "production", "require_email_verification": False},
        {"email_delivery": "smtp"},
        {"email_delivery": "local", "smtp_host": "smtp.example.com"},
    ):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **override)
    engine = database_factory()
    migrate(engine, target="0011")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (email,password_hash,email_verified_at) "
                "VALUES ('legacy@example.com',:hash,now())"
            ),
            {"hash": HASH},
        )
    migrate(engine)
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user.password_hash == HASH and user.email_verified_at and not user.email_verified
        assert user.credential_version == 1
    migrate(engine, "downgrade", "0011")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM users")) == 1


def test_authenticated_tls_adapter_and_safe_failure(monkeypatch):
    import smtplib
    import ssl

    from resolveflow.services.email_delivery import SmtpEmailDelivery

    events = []

    class SMTP:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("smtp.example.com", 587, 5)

        def starttls(self, *, context):
            assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
            events.append("tls")

        def login(self, user, password):
            assert events == ["tls"] and user == "synthetic-user" and password == "synthetic-secret"
            events.append("auth")

        def send_message(self, message):
            assert events == ["tls", "auth"]
            assert message["Subject"] == "Verify your ResolveFlow email"
            events.append("send")
            return {}

        def close(self):
            events.append("close")

    monkeypatch.setattr(smtplib, "SMTP", SMTP)
    settings = Settings(
        _env_file=None,
        email_delivery="smtp",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_tls="starttls",
        smtp_username="synthetic-user",
        smtp_password="synthetic-secret",
        email_public_origin="https://app.example.com",
    )
    result = SmtpEmailDelivery(settings).send_verification(
        "synthetic@example.com", "https://app.example.com/verify-email#token=synthetic", "test-id"
    )
    assert result.accepted and events == ["tls", "auth", "send", "close"]

    def denied(self, user, password):
        raise smtplib.SMTPAuthenticationError(535, b"private error content")

    monkeypatch.setattr(SMTP, "login", denied)
    result = SmtpEmailDelivery(settings).send_recovery(
        "synthetic@example.com", "https://app.example.com/reset-password#token=synthetic", "test-id"
    )
    assert not result.accepted and not result.retryable and result.code == "smtp_authentication"


def test_production_policy_does_not_trust_local_verification():
    from resolveflow.services.auth import verification_allows

    config = Settings(
        _env_file=None, environment="production", trusted_origins=["https://app.example.com"]
    )
    user = User(
        email="synthetic@example.com",
        password_hash=HASH,
        verified_email="synthetic@example.com",
        email_verified_at=datetime.now(UTC),
        email_verification_source="local",
    )
    assert not verification_allows(config, user)
    user.email_verification_source = "smtp"
    assert verification_allows(config, user)
    user.email = "other@example.com"
    assert not verification_allows(config, user)


def test_outbox_publishes_identifiers_and_survives_broker_outage(auth_env):
    from pydantic import SecretStr
    from redis.exceptions import ConnectionError

    from resolveflow.jobs.email import publish
    from resolveflow.jobs.transport import connection, queue
    from scripts.broker_fixture import isolated_broker

    engine, app, client = auth_env
    settings = local(auth_env)
    register(client)
    database = Database(settings)
    try:
        settings.redis_url = SecretStr("redis://127.0.0.1:1/0")
        with pytest.raises(ConnectionError):
            publish(database, settings)
        with Session(engine) as db:
            row = db.scalar(select(IdentityEmail))
            identifier = row.id
            assert row.status == "pending" and row.attempts == 0 and row.last_enqueued_at is None
        with isolated_broker() as (broker_url, _):
            settings.redis_url = SecretStr(broker_url)
            assert publish(database, settings) == 1
            assert publish(database, settings) == 0
            with connection(settings) as broker:
                jobs = queue(settings, broker).get_jobs()
                assert len(jobs) == 1 and jobs[0].args == [str(identifier)]
                assert jobs[0].func_name == "resolveflow.jobs.email.execute"
    finally:
        database.dispose()


@pytest.mark.parametrize("purpose", ["verify", "reset"])
def test_production_rejects_old_local_mail_tokens(auth_env, purpose):
    from fastapi import HTTPException

    from resolveflow.services.identity import consume

    engine, _, client = auth_env
    local(auth_env)
    user = register(client)
    if purpose == "reset":
        mutate(client, "/auth/password/request", {"email": user["email"]})
    _, capture = send(auth_env, purpose)
    production = Settings(
        _env_file=None, environment="production", trusted_origins=["https://app.example.com"]
    )
    with Session(engine) as db, pytest.raises(HTTPException) as error:
        consume(db, token(capture), purpose, new_password=PASSWORD, settings=production)
    assert error.value.status_code == 400


def test_crashed_email_attempt_is_recovered_once_with_new_token(auth_env):
    engine, app, client = auth_env
    settings = local(auth_env)
    register(client)
    identifier, first = send(auth_env)
    with Session(engine) as db:
        row = db.get(IdentityEmail, identifier)
        row.status = "sending"  # SMTP accepted, process died before its completion commit.
        row.available_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    database = Database(settings)
    second = Capture()
    try:
        process(database, settings, identifier, second)
        process(database, settings, identifier, second)
    finally:
        database.dispose()
    assert len(second.links) == 1 and token(first) != token(second)
    assert (
        mutate(
            client, "/auth/verification/confirm", {"token": token(first), "password": PASSWORD}
        ).status_code
        == 400
    )
    assert (
        mutate(
            client, "/auth/verification/confirm", {"token": token(second), "password": PASSWORD}
        ).status_code
        == 200
    )
