"""Bound request bodies before JSON parsing and never cache identity/tenant responses."""

import re

from starlette.responses import JSONResponse


def is_document_upload(method: str, path: str) -> bool:
    return (
        method == "POST"
        and re.fullmatch(r"/api/v1/workspaces/[a-f0-9-]{36}/documents", path) is not None
    )


class SecurityMiddleware:
    def __init__(self, app, upload_limit=2 * 1024**2):
        self.app = app
        self.upload_limit = upload_limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        private = scope["path"].startswith(("/api/v1/auth", "/api/v1/workspaces"))

        async def secure_send(message):
            if message["type"] == "http.response.start" and private:
                message["headers"] += [
                    (b"cache-control", b"no-store"),
                    (b"vary", b"Cookie"),
                    (b"x-content-type-options", b"nosniff"),
                ]
            await send(message)

        if scope["method"] in {"POST", "PATCH", "PUT", "DELETE"}:
            limit = (
                self.upload_limit if is_document_upload(scope["method"], scope["path"]) else 16384
            )
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > limit:
                    response = JSONResponse(
                        {"error": {"code": "request_too_large", "message": "Request is too large"}},
                        status_code=413,
                    )
                    return await response(scope, receive, secure_send)
                body.extend(chunk)
                if not message.get("more_body", False):
                    break
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            return await self.app(scope, bounded_receive, secure_send)
        return await self.app(scope, receive, secure_send)
