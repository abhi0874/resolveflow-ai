"""Offline simulated Google transport. Production never imports this module."""

import secrets
import time
from urllib.parse import parse_qs, urlsplit

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.auth import crypt, jwt

from resolveflow.services import google_oidc


class GoogleFixture:
    def __init__(self):
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.signing_key = self.key
        self.grants = {}
        self.claims = {}
        self.fresh_auth = False
        self.calls = 0

    def authorize(self, url):
        params = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        assert params["scope"] == "openid email profile"
        assert params["code_challenge_method"] == "S256"
        assert params["response_type"] == "code"
        code = secrets.token_urlsafe(24)
        if self.fresh_auth and "claims" in params:
            # Simulate an actual new sign-in at authorization time. ID tokens carry
            # whole seconds, so wait until its ordering is unambiguous.
            time.sleep(int(time.time()) + 1.01 - time.time())
            params["fixture_auth_time"] = int(time.time())
        self.grants[code] = params
        return {"state": params["state"], "code": code}

    def client(self):
        return httpx.Client(transport=httpx.MockTransport(self.handle))

    def handle(self, request):
        if str(request.url) == "https://www.googleapis.com/oauth2/v1/certs":
            pem = self.key.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
            return httpx.Response(200, json={"fixture": pem.decode()})
        assert str(request.url) == google_oidc.TOKEN
        self.calls += 1
        data = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        grant = self.grants.pop(data["code"], None)
        if (
            not grant
            or not data.get("code_verifier")
            or grant["code_challenge"] != google_oidc.challenge(data["code_verifier"])
            or data["client_id"] != grant["client_id"]
            or data["redirect_uri"] != grant["redirect_uri"]
        ):
            return httpx.Response(400, json={"error": "invalid_grant"})
        now = int(time.time())
        claims = dict(
            iss="https://accounts.google.com",
            aud=grant["client_id"],
            iat=now,
            exp=now + 120,
            nonce=grant["nonce"],
            sub="123456789",
            email="fixture@example.com",
            email_verified=True,
        )
        if (
            self.fresh_auth
            and grant.get("claims") == '{"id_token":{"auth_time":{"essential":true}}}'
        ):
            claims["auth_time"] = grant["fixture_auth_time"]
        claims.update(self.claims)
        pem = self.signing_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        signed = jwt.encode(crypt.RSASigner.from_string(pem, key_id="fixture"), claims)
        return httpx.Response(200, json={"id_token": signed.decode()})
