import base64
from contextlib import closing
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_auth_workspaces import PASSWORD, mutate, register, workspace
from test_google_auth import COMPLETE, auth_env, begin, google  # noqa: F401
from test_identity_email import NEW_PASSWORD, Capture, local, send, token

from resolveflow.db.models import IdentityEmail

pytestmark = pytest.mark.integration
PROFILE = "/account/profile"
REQUEST = "/account/email/request"
CONFIRM = "/account/email/confirm"
CHANGE = "/account/password"


class AccountMail(Capture):
    def __init__(self):
        super().__init__()
        self.recipients = []

    def send_email_change(self, recipient, link, message_id):
        self.recipients.append(recipient)
        return self.send_verification(recipient, link, message_id)

    send_email_approval = send_email_change

    def send_email_notice(self, recipient, message_id):
        self.recipients.append(recipient)
        return self.result


def sign_in(client, email, password=PASSWORD):
    return mutate(client, "/auth/login", {"email": email, "password": password})


def proof(client, raw, action="confirm"):
    return mutate(client, CONFIRM, {"token": raw, "action": action})


def request(client, email, password=PASSWORD):
    return mutate(client, REQUEST, {"email": email, "current_password": password})


def change(client, current=PASSWORD):
    return mutate(
        client,
        CHANGE,
        {
            "current_password": current,
            "password": NEW_PASSWORD,
            "password_confirmation": NEW_PASSWORD,
        },
    )


def test_private_profile_csrf_cross_user_and_image(auth_env):  # noqa: F811
    _, app, client = auth_env
    assert client.get("/api/v1" + PROFILE).status_code == 401
    assert mutate(client, PROFILE, {"display_name": "Denied"}, method="PATCH").status_code == 401
    for path in (REQUEST, CONFIRM, CHANGE):
        assert mutate(client, path).status_code == 401
    owner = register(client)
    assert client.patch("/api/v1" + PROFILE, json={"display_name": "Denied"}).status_code == 403
    assert (
        mutate(
            client,
            PROFILE,
            {"display_name": "Denied"},
            method="PATCH",
            origin="https://untrusted.example",
        ).status_code
        == 403
    )
    assert (
        mutate(
            client, PROFILE, {"display_name": "Denied", "user_id": owner["id"]}, method="PATCH"
        ).status_code
        == 422
    )
    for invalid in ("data:image/svg+xml;base64,eA==", "!" * 12544):
        assert (
            mutate(
                client,
                PROFILE,
                {"display_name": "Denied", "avatar_pixels": invalid},
                method="PATCH",
            ).status_code
            == 422
        )
    pixels = base64.b64encode(bytes([53, 100, 120]) * (56 * 56)).decode()
    result = mutate(
        client, PROFILE, {"display_name": " <Alice> ", "avatar_pixels": pixels}, method="PATCH"
    )
    assert result.status_code == 200
    data = result.json()
    assert data["display_name"] == "<Alice>"
    assert data["password_enabled"] and not data["google_linked"]
    assert base64.b64decode(data["avatar"].split(",")[1]).startswith(b"\x89PNG\r\n\x1a\n")
    with closing(TestClient(app)) as other:
        register(other)
        assert other.get("/api/v1" + PROFILE).json()["display_name"] is None
        assert other.get("/api/v1" + PROFILE).json()["avatar"] is None
    fresh = client.get("/api/v1" + PROFILE)
    assert fresh.json() == data and "no-store" in fresh.headers["cache-control"]
    assert mutate(client, PROFILE, {"display_name": "Alice"}, method="PATCH").json()["avatar"]
    assert (
        mutate(
            client, PROFILE, {"display_name": "Alice", "avatar_pixels": None}, method="PATCH"
        ).json()["avatar"]
        is None
    )


def test_password_reauth_revokes_every_session_and_stale_reset(auth_env):  # noqa: F811
    _, app, client = auth_env
    local(auth_env)
    user = register(client)
    email = user["email"]
    assert mutate(client, "/auth/password/request", {"email": email}).status_code == 202
    _, reset = send(auth_env, "reset")
    with closing(TestClient(app)) as other:
        assert sign_in(other, email).status_code == 200
        assert change(client, "wrong").status_code == 403
        assert other.get("/api/v1" + PROFILE).status_code == 200
        assert change(client).status_code == 204
        for context in (client, other):
            assert context.get("/api/v1" + PROFILE).status_code == 401
        assert (
            mutate(
                other,
                "/auth/password/confirm",
                {"token": token(reset), "password": PASSWORD, "password_confirmation": PASSWORD},
            ).status_code
            == 400
        )
    assert sign_in(client, email).status_code == 401
    assert sign_in(client, email, NEW_PASSWORD).status_code == 200


def test_email_requires_bound_session_new_inbox_and_generic_duplicate_response(auth_env):  # noqa: F811
    _, app, client = auth_env
    local(auth_env)
    user = register(client)
    space = workspace(client)
    current = user["email"]
    new = "new-profile-address@example.com"
    assert request(client, new, "wrong").status_code == 403
    with closing(TestClient(app)) as other, closing(TestClient(app)) as second_session:
        independent = register(other)
        assert sign_in(second_session, current).status_code == 200
        collision = request(client, independent["email"])
        assert collision.status_code == 202
        _, inbox = send(auth_env, "email_change", AccountMail())
        assert proof(client, token(inbox)).status_code == 400
        assert other.get("/api/v1" + PROFILE).json()["email"] == independent["email"]
        accepted = request(client, new)
        assert accepted.status_code == 202 and accepted.json() == collision.json()
        _, inbox = send(auth_env, "email_change", AccountMail())
        assert inbox.recipients == [new]
        raw = token(inbox)
        assert client.get("/api/v1" + PROFILE).json()["email"] == current
        assert proof(other, raw).status_code == 400
        assert proof(second_session, raw).status_code == 400
        assert proof(client, raw).status_code == 204
        assert second_session.get("/api/v1" + PROFILE).status_code == 401
    _, notice = send(auth_env, "email_notice", AccountMail())
    assert notice.recipients == [current] and not notice.links
    assert sign_in(client, current).status_code == 401
    assert sign_in(client, new).status_code == 200
    assert proof(client, raw).status_code == 400
    assert client.get("/api/v1/auth/me").json()["id"] == user["id"]
    assert client.get("/api/v1" + PROFILE).json()["email_verified"]
    assert client.get("/api/v1/workspaces/" + space["id"]).status_code == 200


@pytest.mark.parametrize("reason", ["expired", "superseded", "logged_out"])
def test_inactive_email_proofs(auth_env, reason):  # noqa: F811
    engine, _, client = auth_env
    local(auth_env)
    user = register(client)
    assert request(client, "initial@example.com").status_code == 202
    key, inbox = send(auth_env, "email_change", AccountMail())
    if reason == "expired":
        with Session(engine) as db:
            db.get(IdentityEmail, key).expires_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()
    if reason == "superseded":
        assert request(client, "replacement@example.com").status_code == 202
    if reason == "logged_out":
        mutate(client, "/auth/logout")
        assert sign_in(client, user["email"]).status_code == 200
    assert proof(client, token(inbox)).status_code == 400
    assert client.get("/api/v1" + PROFILE).json()["email"] == user["email"]


def test_google_only_email_step_up_and_sign_in_after_change(google):  # noqa: F811
    engine, app, client, provider = google
    local((engine, app, client))
    assert client.post(COMPLETE, json=begin(client, provider)).status_code == 200
    user = client.get("/api/v1/auth/me").json()
    profile = client.get("/api/v1" + PROFILE).json()
    assert profile["google_linked"] and not profile["password_enabled"]
    assert change(client).status_code == 403
    new = "google-new@example.com"
    assert request(client, new, None).status_code == 403
    _, signed = send((engine, app, client), "verify")
    assert mutate(client, "/auth/verification/confirm", {"token": token(signed)}).status_code == 200
    assert client.post(COMPLETE, json=begin(client, provider)).status_code == 200
    assert request(client, new, None).status_code == 202
    with Session(engine) as db:
        assert (
            db.scalar(select(IdentityEmail).where(IdentityEmail.purpose == "email_change")) is None
        )
    _, approval = send((engine, app, client), "email_approve", AccountMail())
    assert approval.recipients == [user["email"]]
    assert proof(client, token(approval)).status_code == 400
    assert proof(client, token(approval), "approve").status_code == 204
    assert proof(client, token(approval), "approve").status_code == 400
    _, new_proof = send((engine, app, client), "email_change", AccountMail())
    assert new_proof.recipients == [new]
    assert proof(client, token(new_proof)).status_code == 204
    assert client.post(COMPLETE, json=begin(client, provider)).status_code == 200
    after = client.get("/api/v1/auth/me").json()
    assert after["id"] == user["id"] and after["email"] == new
    assert not client.get("/api/v1" + PROFILE).json()["password_enabled"]
