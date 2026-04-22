"""API middleware — request id + access log (Phase 175)."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


logger = logging.getLogger("motodiag.api.access")


REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request id to every request.

    Reads ``X-Request-ID`` from the inbound request if present
    (clients can provide one for tracing); otherwise generates a
    UUID4. Exposes via ``request.state.request_id`` and echoes on
    the response.

    The client-supplied id is *not* trusted for auth/audit — Phase
    176 will layer a server-derived session id on top for those
    uses. This middleware's id is correlation-only.
    """

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(REQUEST_ID_HEADER)
        if not rid:
            rid = uuid.uuid4().hex
        request.state.request_id = rid
        response: Response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = rid
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log one structured line per request.

    Format: ``<method> <path> <status> <duration_ms>ms rid=<id>``.
    Use the ``motodiag.api.access`` logger; tune verbosity via
    ``MOTODIAG_API_LOG_LEVEL``.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        dur_ms = (time.perf_counter() - start) * 1000
        rid = getattr(request.state, "request_id", "-")
        logger.info(
            "%s %s %d %.2fms rid=%s",
            request.method, request.url.path, response.status_code,
            dur_ms, rid,
        )
        return response
