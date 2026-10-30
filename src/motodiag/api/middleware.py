"""API middleware — request id + access log (Phase 175)."""

from __future__ import annotations

import json
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


# ---------------------------------------------------------------------------
# Phase 176 — rate limit middleware
# ---------------------------------------------------------------------------


_RATE_LIMIT_EXEMPT_PATHS = (
    "/healthz",
    "/v1/version",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/v1/billing/webhooks",  # Stripe retries shouldn't be throttled
    "/v1/live",  # Phase 181 — WebSocket streams don't fit req/min token buckets
)


def _request_db_path(request: Request, resolver=None) -> str:
    """The database in use for this request: the middleware's resolver if
    it has one, else the app's ``get_db_path`` override, else Settings."""
    if resolver is not None:
        return resolver(request)
    from motodiag.api.deps import get_db_path
    override = request.app.dependency_overrides.get(get_db_path)
    return override() if override else get_db_path()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket rate limiting per api-key (authed) or per IP
    (anonymous).

    Skip list: ``/healthz``, ``/v1/version``, OpenAPI endpoints, and
    ``/v1/billing/webhooks/*`` (Stripe retries shouldn't be
    throttled — signature verification handles abuse).

    Sets response headers: ``X-RateLimit-Limit``,
    ``X-RateLimit-Remaining``, ``X-RateLimit-Reset``,
    ``X-RateLimit-Tier``. On 429 block, raises
    :class:`RateLimitExceededError` which the custom handler in
    :mod:`motodiag.api.errors` translates to a ProblemDetail +
    ``Retry-After`` header.
    """

    def __init__(self, app, db_path_resolver=None):
        super().__init__(app)
        # Callable that returns the current db path; allows the
        # middleware to work across test-override seams.
        self._db_path_resolver = db_path_resolver

    def _is_exempt(self, path: str) -> bool:
        for prefix in _RATE_LIMIT_EXEMPT_PATHS:
            if path == prefix or path.startswith(prefix + "/"):
                return True
        return False

    async def _try_resolve_api_key(self, request: Request):
        """Best-effort API key or session resolution. Doesn't 401 here —
        that's the route's ``require_api_key`` dep's job."""
        from motodiag.auth.deps import (
            API_KEY_HEADER,
            _extract_key_from_headers,
            resolve_credential,
        )
        header = request.headers.get(API_KEY_HEADER)
        authz = request.headers.get("Authorization")
        plaintext = _extract_key_from_headers(header, authz)
        if plaintext is None:
            return None
        try:
            db_path = _request_db_path(request, self._db_path_resolver)
            return resolve_credential(plaintext, db_path=db_path)
        except Exception as e:
            logger.warning(
                "rate-limit api key resolve failed: %s", e,
            )
            return None

    async def _caller_tier(self, request: Request) -> tuple[str, str]:
        """Return (caller_key, tier). A credentialed caller whose
        :func:`~motodiag.auth.deps.resolve_tier` is None is
        ``'individual'``."""
        from motodiag.auth.deps import resolve_tier
        key = await self._try_resolve_api_key(request)
        if key is None:
            ip = request.client.host if request.client else "unknown"
            return f"ip:{ip}", "anonymous"
        # Stash key on state so deps can pick it up without re-hashing
        request.state.api_key = key
        # Look up subscription tier
        try:
            db_path = _request_db_path(request, self._db_path_resolver)
            tier = resolve_tier(key, db_path=db_path)
        except Exception:
            tier = None
        return f"key:{key.id}", tier or "individual"

    async def dispatch(self, request: Request, call_next):
        if self._is_exempt(request.url.path):
            return await call_next(request)

        from motodiag.auth.rate_limiter import get_rate_limiter

        caller_key, tier = await self._caller_tier(request)
        limiter = get_rate_limiter()
        state = limiter.check_and_consume(caller_key, tier)
        if not state.allowed:
            # Middleware-raised exceptions don't reach FastAPI's
            # exception handler registry cleanly (Starlette unwinds
            # through the BaseHTTPMiddleware stream layer), so we
            # build the 429 response inline here.
            from fastapi.responses import JSONResponse
            rid = getattr(request.state, "request_id", None)
            body = {
                "type": "https://motodiag.dev/problems/rate-limit-exceeded",
                "title": "Rate limit exceeded",
                "status": 429,
                "detail": (
                    f"rate limit exceeded ({state.tier} tier: "
                    f"{state.limit_per_minute}/min, "
                    f"{state.limit_per_day}/day)"
                ),
                "instance": str(request.url.path),
            }
            if rid:
                body["request_id"] = rid
            headers = {
                "Retry-After": str(max(state.retry_after_s, 1)),
                "X-RateLimit-Limit": str(state.limit_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(state.minute_reset_ts),
                "X-RateLimit-Tier": str(state.tier),
            }
            if rid:
                headers["X-Request-ID"] = rid
            return JSONResponse(
                status_code=429, content=body, headers=headers,
            )
        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(
            state.limit_per_minute,
        )
        response.headers["X-RateLimit-Remaining"] = str(
            state.remaining_minute,
        )
        response.headers["X-RateLimit-Reset"] = str(
            state.minute_reset_ts,
        )
        response.headers["X-RateLimit-Tier"] = str(state.tier)
        return response


# ---------------------------------------------------------------------------
# Phase 348 — the audit log
# ---------------------------------------------------------------------------


AUDITED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
audit_logger = logging.getLogger("motodiag.audit")


class AuditMiddleware(BaseHTTPMiddleware):
    """One ``audit_events`` row per write request, after the route answers.

    Registered inside ``RateLimitMiddleware``, so a refused request (429)
    is not recorded. Reads what the route left on the request's scope: the
    caller (Phase 303's ``request.state.caller``), the endpoint and the path
    ids. Never the body or the query string. A route that raises is
    recorded as 500 and the exception goes on. A failed audit write never
    fails the request (the operator, Phase 348): it is logged at ERROR on
    ``motodiag.audit`` with the request id, and the response goes out as is.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method not in AUDITED_METHODS:
            return await call_next(request)
        try:
            response: Response = await call_next(request)
        except Exception:
            self._record(request, 500)
            raise
        self._record(request, response.status_code)
        return response

    def _record(self, request: Request, status: int) -> None:
        from motodiag.audit import AuditEvent, append_event
        from motodiag.core.database import get_connection

        rid = getattr(request.state, "request_id", None)
        try:
            caller = getattr(request.state, "caller", None)
            params = dict(request.scope.get("path_params") or {})
            endpoint = request.scope.get("endpoint")
            shop_id = str(params.get("shop_id", ""))
            with get_connection(_request_db_path(request)) as conn:
                username = None
                if caller is not None:
                    row = conn.execute(
                        "SELECT username FROM users WHERE id = ?",
                        (caller.user_id,),
                    ).fetchone()
                    username = row[0] if row else None
                append_event(conn, AuditEvent(
                    method=request.method,
                    path=request.url.path,
                    status=status,
                    request_id=rid,
                    actor_user_id=caller.user_id if caller else None,
                    actor_username=username,
                    credential_kind=caller.credential_kind if caller else None,
                    credential_id=caller.credential_id if caller else None,
                    client_address=request.client.host if request.client else None,
                    forwarded_for=request.headers.get("X-Forwarded-For"),
                    endpoint=getattr(endpoint, "__name__", None),
                    path_params=(json.dumps(params, sort_keys=True, separators=(",", ":"),
                                            default=str) if params else None),
                    shop_id=int(shop_id) if shop_id.isdigit() else None,
                ))
        except Exception:
            audit_logger.exception(
                "audit write failed rid=%s %s %s", rid, request.method,
                request.url.path,
            )
