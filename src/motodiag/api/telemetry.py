"""Crash reports and request timings for the API (Phase 343).

``install_telemetry`` puts a sender at ``app.state.telemetry`` (a
``NullSender`` without ``MOTODIAG_SENTRY_DSN``) and adds
``TelemetryMiddleware``. ``capture_crash`` is the one call
``_unhandled_handler`` makes.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from motodiag.telemetry.events import error_event, transaction_event
from motodiag.telemetry.sender import make_sender

SKIPPED_PATHS = frozenset({"/healthz"})
UNMATCHED = "unmatched"


def route_template(request: Request) -> str:
    """The matched route's template (``/v1/shops/{shop_id}``), never the
    path with its ids; "unmatched" when no route matched."""
    route = request.scope.get("route")
    return getattr(route, "path_format", None) or UNMATCHED


def skipped(request: Request) -> bool:
    """``/healthz`` and every ``OPTIONS`` request are never timed."""
    return request.method == "OPTIONS" or request.url.path in SKIPPED_PATHS


def _sender(request: Request) -> Any:
    sender = getattr(request.app.state, "telemetry", None)
    return sender if sender is not None and sender.enabled else None


class TelemetryMiddleware(BaseHTTPMiddleware):
    """One transaction per sampled request.

    The stack as ``create_app`` builds it, outermost first:
    ``ServerErrorMiddleware`` (Starlette's, where ``_unhandled_handler``
    runs), ``RequestIdMiddleware``, ``RateLimitMiddleware``,
    ``AccessLogMiddleware``, ``AuditMiddleware``, this middleware,
    ``CORSMiddleware``, then Starlette's ``ExceptionMiddleware`` around the
    router. So:

    1. ``request.state.request_id`` is set before ``call_next``.
    2. A request the rate limit refuses (429) never reaches here, and sends
       no transaction.
    3. CORS answers a preflight below this layer without reaching the
       router, so it would arrive with no route; every ``OPTIONS`` request
       is skipped before ``call_next``, as ``/healthz`` is. The product
       registers no ``OPTIONS`` route.
    4. A mapped error (a 404, a 422, a domain error's status) is turned into
       a response by ``ExceptionMiddleware`` inside this layer, so it
       arrives as a response and is timed like any other. Only an exception
       no handler maps passes up through here; it is timed as a 500 and
       re-raised unchanged to ``_unhandled_handler``, which sends the crash.

    The sender is read from ``request.app.state`` on every request, never
    closed over at install. It never changes a response and never raises.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        sender = _sender(request)
        if sender is None or skipped(request):
            return await call_next(request)
        wall = time.time()
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            _time(request, sender, 500, wall, start)
            raise
        _time(request, sender, response.status_code, wall, start)
        return response


def _time(request: Request, sender: Any, status: int, wall: float,
          start: float) -> None:
    if not sender.sampled():
        return
    ended = wall + (time.perf_counter() - start)
    sender.capture(transaction_event(
        route=route_template(request), method=request.method, status=status,
        started=wall, ended=ended,
        request_id=getattr(request.state, "request_id", None),
        release=sender.release, environment=sender.environment,
        server_name=sender.server_name))


def capture_crash(request: Request, exc: BaseException) -> None:
    """Send one error event for an exception no handler mapped."""
    sender = _sender(request)
    if sender is None:
        return
    sender.capture(error_event(
        exc, request_id=getattr(request.state, "request_id", None),
        method=request.method, route=route_template(request), status=500,
        release=sender.release, environment=sender.environment,
        server_name=sender.server_name))


def install_telemetry(app: FastAPI, settings) -> str:
    """Build the sender, add the middleware; return the ready line's word."""
    sender = make_sender(settings)
    app.state.telemetry = sender
    app.add_middleware(TelemetryMiddleware)
    return f"on {sender.dsn}" if sender.enabled else "off"
