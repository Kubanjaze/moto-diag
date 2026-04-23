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
        """Best-effort API key resolution. Doesn't 401 here — that's
        the route's ``require_api_key`` dep's job."""
        from motodiag.auth.api_key_repo import verify_api_key
        from motodiag.auth.deps import (
            _extract_key_from_headers, API_KEY_HEADER,
        )
        header = request.headers.get(API_KEY_HEADER)
        authz = request.headers.get("Authorization")
        plaintext = _extract_key_from_headers(header, authz)
        if plaintext is None:
            return None
        # Resolve db path via app override → Settings default
        try:
            if self._db_path_resolver is not None:
                db_path = self._db_path_resolver(request)
            else:
                from motodiag.api.deps import get_db_path
                app = request.app
                override = app.dependency_overrides.get(get_db_path)
                db_path = override() if override else get_db_path()
            return verify_api_key(plaintext, db_path=db_path)
        except Exception as e:
            logger.warning(
                "rate-limit api key resolve failed: %s", e,
            )
            return None

    async def _caller_tier(self, request: Request) -> tuple[str, str]:
        """Return (caller_key, tier)."""
        from motodiag.billing.subscription_repo import (
            get_active_subscription,
        )
        key = await self._try_resolve_api_key(request)
        if key is None:
            ip = request.client.host if request.client else "unknown"
            return f"ip:{ip}", "anonymous"
        # Stash key on state so deps can pick it up without re-hashing
        request.state.api_key = key
        # Look up subscription tier
        try:
            if self._db_path_resolver is not None:
                db_path = self._db_path_resolver(request)
            else:
                from motodiag.api.deps import get_db_path
                app = request.app
                override = app.dependency_overrides.get(get_db_path)
                db_path = override() if override else get_db_path()
            sub = get_active_subscription(
                key.user_id, db_path=db_path,
            )
        except Exception:
            sub = None
        tier = sub.tier if sub is not None else "individual"
        return f"key:{key.id}", tier

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
