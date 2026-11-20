"""Offline ASGI entry point used exclusively by the disposable browser runner."""

import os

from fastapi import Request
from google_fixture import GoogleFixture
from pydantic import SecretStr

from resolveflow.core.config import Settings
from resolveflow.main import create_asgi_app
from resolveflow.services import google_oidc

settings = Settings()
if (
    settings.environment != "test"
    or os.environ.get("RESOLVEFLOW_E2E_ISOLATED") != "1"
    or os.environ.get("RESOLVEFLOW_TEST_GOOGLE") != "1"
):
    raise RuntimeError("The browser fixture requires the isolated test runner")
settings.google_client_id = "isolated-browser"
settings.google_client_secret = SecretStr("synthetic-only")
settings.google_redirect_uri = "http://127.0.0.1:3100/auth/google/callback"
settings.google_enabled = True
provider = GoogleFixture()
provider.fresh_auth = True
google_oidc.provider_client = provider.client
app = create_asgi_app(settings)


@app.app.app.get("/_fixture/google/authorize")
def authorize(request: Request):
    return provider.authorize(google_oidc.AUTHORIZE + "?" + request.url.query)
