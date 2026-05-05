"""OpenAPI schema enrichment (Phase 183).

FastAPI's auto-generated OpenAPI spec captures route signatures +
types + summaries, but nothing about the *product* — no tag
descriptions, no server URLs, no security schemes, no documented
error envelopes. Phase 183 fixes all of that by overriding
``FastAPI.openapi()`` with :func:`build_openapi` which:

1. Enriches ``info`` with contact, license, terms-of-service.
2. Adds a ``servers`` list from Settings.
3. Adds a ``tags`` catalog with descriptions.
4. Adds ``components.securitySchemes`` (apiKey + bearerAuth).
5. Adds ``components.responses.*`` — reusable RFC 7807 error
   envelopes for 401 / 402 / 403 / 404 / 422 / 429 / 500.
6. Walks every ``/v1/*`` operation and attaches the right
   ``security`` + ``responses`` references based on tags / path
   params / request bodies.
7. Caches the result on ``app.openapi_schema`` so repeated spec
   requests don't re-enrich.

The override is idempotent: second call returns the cached dict.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


# ---------------------------------------------------------------------------
# Static metadata
# ---------------------------------------------------------------------------


INFO_CONTACT = {
    "name": "MotoDiag Support",
    "email": "support@motodiag.dev",
    "url": "https://motodiag.dev/support",
}

INFO_LICENSE = {
    "name": "MIT",
    "identifier": "MIT",
    "url": "https://opensource.org/license/mit",
}

INFO_TERMS = "https://motodiag.dev/terms"


# Tag catalog — descriptions shown in Swagger UI under each group.
TAG_CATALOG: list[dict[str, Any]] = [
    {
        "name": "meta",
        "description": (
            "Health checks and version metadata. No authentication "
            "required; used by load balancers and client startup "
            "probes."
        ),
    },
    {
        "name": "auth",
        "description": (
            "API keys, subscriptions, and Stripe webhooks. This is "
            "the entry point for the paywall — every non-meta "
            "endpoint requires an active API key."
        ),
    },
    {
        "name": "shops",
        "description": (
            "Global shop registry. Read-only at this tier; see "
            "`shop-management` for writes."
        ),
    },
    {
        "name": "billing",
        "description": (
            "Stripe checkout sessions + customer portals + webhook "
            "intake. Prices are set per subscription tier."
        ),
    },
    {
        "name": "vehicles",
        "description": (
            "Caller's garage — add, list, update, or remove bikes "
            "you own. Tier-quota gated (individual=5, shop=50, "
            "company=unlimited)."
        ),
    },
    {
        "name": "sessions",
        "description": (
            "Diagnostic session lifecycle: open a session, record "
            "symptoms + fault codes, save the AI diagnosis, close "
            "the session. Monthly-quota gated."
        ),
    },
    {
        "name": "knowledge-base",
        "description": (
            "Read-only lookups: DTC codes, symptoms, known issues, "
            "and a unified search across all three. Available to "
            "any authenticated caller (no tier required)."
        ),
    },
    {
        "name": "shop-management",
        "description": (
            "The full shop-operator console: members, customers, "
            "work orders, issues, parts, invoices, analytics. "
            "Shop-tier required + per-shop membership enforced."
        ),
    },
    {
        "name": "reports",
        "description": (
            "Downloadable reports in JSON or PDF — diagnostic "
            "session reports (session owner), work-order receipts "
            "(shop-tier), invoice PDFs (shop-tier)."
        ),
    },
    {
        "name": "live",
        "description": (
            "WebSocket live sensor-data streams keyed to a "
            "diagnostic session. Paid-tier required."
        ),
    },
    {
        "name": "videos",
        "description": (
            "Video diagnostic uploads + Claude Vision AI analysis "
            "nested under a session. POST upload (shop-tier + "
            "multipart) / GET list / GET single / DELETE soft-delete "
            "/ GET binary file-stream. Per-session caps: 10 videos / "
            "1 GB. Per-tier monthly: 0/200/unlimited for individual/"
            "shop/company. ffmpeg subprocess + Vision pipeline drive "
            "the analysis worker through pending → analyzing → "
            "analyzed | analysis_failed | unsupported. Phase 191B."
        ),
    },
]


# Tags whose endpoints are *public* — no security requirement.
PUBLIC_TAGS = {"meta"}


# Paths that are explicitly public even if their tag isn't in PUBLIC_TAGS.
PUBLIC_PATH_PREFIXES = (
    "/v1/billing/webhooks",
)


# ---------------------------------------------------------------------------
# Security schemes
# ---------------------------------------------------------------------------


SECURITY_SCHEMES: dict[str, dict] = {
    "apiKey": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": (
            "API key issued via `POST /v1/billing/checkout-session` "
            "or the `motodiag apikey create` CLI. Prefix "
            "`mdk_live_...` for production or `mdk_test_...` for "
            "dev/test. Plaintext is shown ONCE at creation time; "
            "keep it safe."
        ),
    },
    "bearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "description": (
            "Same key as `apiKey`, supplied as `Authorization: "
            "Bearer <key>` instead of the dedicated header. Useful "
            "for OpenAPI clients that only support HTTP Bearer."
        ),
    },
}


# ---------------------------------------------------------------------------
# Reusable error responses (RFC 7807 envelope)
# ---------------------------------------------------------------------------


_PROBLEM_REF = {"$ref": "#/components/schemas/ProblemDetail"}


ERROR_RESPONSES: dict[str, dict] = {
    "Unauthorized": {
        "description": (
            "Missing, malformed, or revoked API key. Supply a valid "
            "`X-API-Key` header or `Authorization: Bearer <key>`."
        ),
        "content": {"application/json": {"schema": _PROBLEM_REF}},
    },
    "SubscriptionRequired": {
        "description": (
            "Caller is authenticated but lacks the required "
            "subscription tier. Upgrade via `POST "
            "/v1/billing/checkout-session` or the Stripe customer "
            "portal."
        ),
        "content": {"application/json": {"schema": _PROBLEM_REF}},
    },
    "Forbidden": {
        "description": (
            "Caller is authenticated and has the right tier, but "
            "lacks access to this specific resource (e.g. "
            "cross-shop request)."
        ),
        "content": {"application/json": {"schema": _PROBLEM_REF}},
    },
    "NotFound": {
        "description": (
            "Resource does not exist OR belongs to another owner — "
            "both cases return 404 to avoid enumeration attacks."
        ),
        "content": {"application/json": {"schema": _PROBLEM_REF}},
    },
    "ValidationError": {
        "description": (
            "Request body failed Pydantic validation. Response "
            "body's `detail` lists the invalid fields."
        ),
        "content": {"application/json": {"schema": _PROBLEM_REF}},
    },
    "RateLimitExceeded": {
        "description": (
            "Per-minute or per-day rate limit for the caller's "
            "tier has been exceeded. `Retry-After` header indicates "
            "wait-time in seconds."
        ),
        "content": {"application/json": {"schema": _PROBLEM_REF}},
        "headers": {
            "Retry-After": {
                "description": "Seconds until next request allowed.",
                "schema": {"type": "integer"},
            },
            "X-RateLimit-Limit": {
                "description": (
                    "Current tier's per-minute request budget."
                ),
                "schema": {"type": "integer"},
            },
            "X-RateLimit-Tier": {
                "description": (
                    "Tier bucket used for this request "
                    "(anonymous / individual / shop / company)."
                ),
                "schema": {"type": "string"},
            },
        },
    },
    "InternalError": {
        "description": (
            "Unexpected server error. `detail` is intentionally "
            "omitted on 5xx responses — check the correlation "
            "`request_id` and server logs."
        ),
        "content": {"application/json": {"schema": _PROBLEM_REF}},
    },
}


# Default ProblemDetail schema — FastAPI emits it from the Pydantic
# model in motodiag.api.errors, but we fall back to an explicit
# definition if the model isn't discovered (e.g. when no route
# currently types its return as ProblemDetail).
PROBLEM_DETAIL_SCHEMA: dict = {
    "title": "ProblemDetail",
    "type": "object",
    "description": (
        "RFC 7807 Problem Details body. All error responses use "
        "this shape."
    ),
    "properties": {
        "type": {
            "type": "string",
            "description": (
                "URI reference identifying the problem type."
            ),
            "default": "about:blank",
        },
        "title": {
            "type": "string",
            "description": "Short, human-readable summary.",
        },
        "status": {
            "type": "integer",
            "description": "HTTP status code.",
        },
        "detail": {
            "type": "string",
            "description": "Human-readable explanation, optional.",
            "nullable": True,
        },
        "instance": {
            "type": "string",
            "description": "URI reference for the specific problem.",
            "nullable": True,
        },
        "request_id": {
            "type": "string",
            "description": (
                "Server-issued correlation id; matches the "
                "`X-Request-ID` response header."
            ),
            "nullable": True,
        },
    },
    "required": ["title", "status"],
}


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------


def build_openapi(app: FastAPI) -> dict[str, Any]:
    """Return the enriched OpenAPI dict, caching on the app.

    Idempotent: on the second call returns ``app.openapi_schema``
    directly without re-walking the routes.
    """
    if app.openapi_schema is not None:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=TAG_CATALOG,
    )

    info = schema.setdefault("info", {})
    info["contact"] = INFO_CONTACT
    info["license"] = INFO_LICENSE
    info["termsOfService"] = INFO_TERMS

    # Servers from Settings (local dev by default; deployments
    # override via MOTODIAG_API_SERVERS).
    try:
        from motodiag.core.config import get_settings
        servers = get_settings().api_servers_list
    except Exception:  # pragma: no cover — config must exist in prod
        servers = [{"url": "http://localhost:8080",
                    "description": "Local dev"}]
    if servers:
        schema["servers"] = servers

    components = schema.setdefault("components", {})
    components.setdefault("schemas", {}).setdefault(
        "ProblemDetail", PROBLEM_DETAIL_SCHEMA,
    )
    components["securitySchemes"] = dict(SECURITY_SCHEMES)
    components_responses = components.setdefault("responses", {})
    for name, response in ERROR_RESPONSES.items():
        components_responses[name] = response

    _walk_operations(schema)

    app.openapi_schema = schema
    return schema


def _walk_operations(schema: dict) -> None:
    """For every path + method, attach security + error responses."""
    for path, path_item in schema.get("paths", {}).items():
        for method_name, operation in path_item.items():
            if method_name.lower() not in _HTTP_METHODS:
                continue
            _enrich_operation(path, operation)


_HTTP_METHODS = {"get", "post", "put", "patch", "delete",
                 "head", "options", "trace"}


def _is_public(path: str, operation: dict) -> bool:
    if any(path.startswith(p) for p in PUBLIC_PATH_PREFIXES):
        return True
    tags = set(operation.get("tags") or [])
    return bool(tags & PUBLIC_TAGS)


def _enrich_operation(path: str, operation: dict) -> None:
    is_public = _is_public(path, operation)

    if not is_public:
        operation.setdefault(
            "security", [{"apiKey": []}, {"bearerAuth": []}],
        )
        responses = operation.setdefault("responses", {})
        responses.setdefault(
            "401",
            {"$ref": "#/components/responses/Unauthorized"},
        )
        responses.setdefault(
            "429",
            {"$ref": "#/components/responses/RateLimitExceeded"},
        )
        responses.setdefault(
            "500",
            {"$ref": "#/components/responses/InternalError"},
        )
        # Tier-gated paths get 402 (conservative: attach to any
        # non-public /v1/* operation that requires more than the
        # anonymous tier — includes most of them; `meta` + billing
        # webhooks are excluded above).
        if _needs_tier(path, operation):
            responses.setdefault(
                "402",
                {
                    "$ref": "#/components/responses/SubscriptionRequired",
                },
            )
        # Path params → 404 possible.
        if _has_path_params(operation):
            responses.setdefault(
                "404",
                {"$ref": "#/components/responses/NotFound"},
            )
        # Request bodies → 422 possible.
        if operation.get("requestBody"):
            responses.setdefault(
                "422",
                {"$ref": "#/components/responses/ValidationError"},
            )


_ALWAYS_TIER_GATED_TAGS = {
    "shop-management", "reports", "live",
    "vehicles", "sessions",
}
# `vehicles` + `sessions` aren't strictly tier-gated (individual
# tier users can use them) but they enforce *quotas* that map to
# 402 with detail "monthly quota exceeded" — so 402 is still a
# possible response and should be documented.


def _needs_tier(path: str, operation: dict) -> bool:
    tags = set(operation.get("tags") or [])
    return bool(tags & _ALWAYS_TIER_GATED_TAGS)


def _has_path_params(operation: dict) -> bool:
    params = operation.get("parameters") or []
    return any(p.get("in") == "path" for p in params)


# ---------------------------------------------------------------------------
# Installer
# ---------------------------------------------------------------------------


def install_openapi(app: FastAPI) -> None:
    """Wire :func:`build_openapi` as ``app.openapi``.

    Call once during ``create_app``. Safe to call multiple times —
    each re-install starts from a clean cache.
    """
    app.openapi_schema = None
    app.openapi = lambda: build_openapi(app)
