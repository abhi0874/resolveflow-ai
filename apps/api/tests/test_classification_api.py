import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_auth_workspaces import auth_env as auth_fixture
from test_auth_workspaces import mutate, register, workspace
from test_ml import trained_model as trained_fixture
from test_tickets import create, patch, setup

from resolveflow.db.models import Ticket, TicketActivity
from resolveflow.main import create_asgi_app
from resolveflow.ml.classifier import LocalTicketClassifier
from resolveflow.ml.contracts import ModelUnavailable

auth_env = auth_fixture
trained_model = trained_fixture
pytestmark = pytest.mark.integration


def attach(app, root):
    app.app.state.classifier = LocalTicketClassifier(root, "test-v1", 0.45)


def test_real_classification_nonmutation_and_authorized_acceptance(auth_env, trained_model):
    engine, app, client = auth_env
    attach(app, trained_model)
    _, _, base = setup(client)
    ticket = create(
        client,
        base,
        title="Duplicate debit",
        description="My card shows two payments for one purchase. Please return the extra amount.",
        category="Legacy category",
    )
    detail = base + "/" + ticket["id"]
    result = mutate(client, detail + "/classify")
    assert result.status_code == 200
    prediction = result.json()
    assert prediction["predicted_category"] == "Billing"
    assert prediction["suggested_category"] == "Billing"
    assert prediction["model_version"] == "test-v1" and prediction["ticket_version"] == 1
    assert 0 <= prediction["score"] <= 1 and prediction["human_review_recommended"]
    assert "no-store" in result.headers["cache-control"]
    assert not {"description", "title", "path", "coefficients"} & prediction.keys()
    assert client.get("/api/v1" + detail).json() == ticket
    # Dismissal is deliberately no write. Classification itself adds no audit event.
    with Session(engine) as db:
        assert len(db.scalars(select(TicketActivity)).all()) == 1
        assert db.get(Ticket, uuid.UUID(ticket["id"])).category == "Legacy category"
    saved = patch(client, base, ticket, category=prediction["suggested_category"])
    assert saved.status_code == 200 and saved.json()["category"] == "Billing"
    events = client.get("/api/v1" + detail + "/activities").json()["items"]
    assert events[0]["action"] == "updated" and events[0]["details"] == {"fields": ["category"]}
    assert patch(client, base, ticket, category="Other").status_code == 409


def test_classification_tenant_roles_and_csrf(auth_env, trained_model):
    _, app, owner_client = auth_env
    attach(app, trained_model)
    owner, space, base = setup(owner_client)
    ticket = create(owner_client, base, assigned_user_id=owner["id"])
    detail = base + "/" + ticket["id"]
    assert owner_client.post("/api/v1" + detail + "/classify", json={}).status_code == 403
    assert mutate(owner_client, detail + "/classify", {"title": "injected"}).status_code == 422
    assert mutate(owner_client, base + "/invalid/classify").status_code == 422
    assert mutate(owner_client, base + f"/{uuid.uuid4()}/classify").status_code == 404
    with TestClient(create_asgi_app(app.app.state.settings)) as other:
        assert mutate(other, detail + "/classify").status_code == 401
        user = register(other)
        foreign = workspace(other)
        assert mutate(other, detail + "/classify").status_code == 404
        assert (
            mutate(
                other, f"/workspaces/{foreign['id']}/tickets/{ticket['id']}/classify"
            ).status_code
            == 404
        )
        members = f"/workspaces/{space['id']}/members"
        assert (
            mutate(owner_client, members, {"email": user["email"], "role": "viewer"}).status_code
            == 201
        )
        assert mutate(other, detail + "/classify").status_code == 403
        assert patch(other, base, ticket, category="Billing").status_code == 403
        assert (
            mutate(
                owner_client, members + "/" + user["id"], {"role": "support_agent"}, "PATCH"
            ).status_code
            == 200
        )
        assert mutate(other, detail + "/classify").status_code == 403
        saved = patch(owner_client, base, ticket, assigned_user_id=user["id"]).json()
        # Give this independent test app the same trusted synthetic test model.
        other.app.app.state.classifier = app.app.state.classifier
        assert mutate(other, detail + "/classify").status_code == 200
        assert patch(other, base, saved, category="Account Access").status_code == 200
        assert (
            mutate(
                owner_client, members + "/" + user["id"], {"role": "viewer"}, "PATCH"
            ).status_code
            == 200
        )
        assert mutate(other, detail + "/classify").status_code == 403


def test_classification_missing_and_failing_model_preserves_tickets(
    auth_env, tmp_path, trained_model, monkeypatch
):
    _, app, client = auth_env
    _, _, base = setup(client)
    ticket = create(client, base)
    detail = base + "/" + ticket["id"]
    app.app.state.classifier = LocalTicketClassifier(tmp_path, "missing", 0.45)
    response = mutate(client, detail + "/classify")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "classifier_unavailable"
    assert str(tmp_path) not in response.text
    attach(app, trained_model)

    def fail(_):
        raise ModelUnavailable("safe failure")

    monkeypatch.setattr(app.app.state.classifier, "predict", fail)
    assert mutate(client, detail + "/classify").status_code == 503
    assert client.get("/api/v1" + detail).json() == ticket
