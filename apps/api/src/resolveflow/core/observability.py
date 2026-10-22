"""Content-free HTTP correlation and timings. Never log paths, queries or headers."""

import json
import logging
import time
import uuid
from contextvars import ContextVar

request_id: ContextVar[uuid.UUID | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("resolveflow.requests")
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)
logger.propagate = False
# Uvicorn access lines include raw paths/query strings; the safe events replace them.
logging.getLogger("uvicorn.access").disabled = True


class RequestDiagnostics:
    def __init__(self, app):
        self.app = app
        self.state = app.state

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        identity = uuid.uuid4()
        scope.setdefault("state", {})["request_id"] = identity
        token = request_id.set(identity)
        started = time.monotonic()
        status = 500

        async def observed_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"].append((b"x-request-id", str(identity).encode()))
            await send(message)

        try:
            await self.app(scope, receive, observed_send)
        finally:
            route = scope.get("route")
            # Framework route names are code-defined. Raw URLs may contain private input.
            logger.info(
                json.dumps(
                    dict(
                        event="http_request",
                        request_id=str(identity),
                        route=getattr(route, "name", "unmatched"),
                        status=status,
                        duration_ms=round((time.monotonic() - started) * 1000, 2),
                    )
                )
            )
            request_id.reset(token)
