"""FastAPI app factory (Phase 175).

``create_app()`` returns a fresh configured FastAPI instance each call.
Production uses ``uvicorn motodiag.api:create_app --factory``; tests
override dependencies via ``app.dependency_overrides[dep] = stub``.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from motodiag.api.deps import get_db_path, get_settings
from motodiag.api.errors import register_exception_handlers
from motodiag.api.middleware import (
    AccessLogMiddleware,
    AuditMiddleware,
    BodySizeLimitMiddleware,
    RateLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)
from motodiag.api.openapi import install_openapi
from motodiag.api.telemetry import install_telemetry
from motodiag.core.config import Environment, Settings

APP_VERSION = "v1"


def create_app(
    settings: Optional[Settings] = None,
    db_path_override: Optional[str] = None,
) -> FastAPI:
    """Build a configured FastAPI app.

    Args:
        settings: override Settings for the ``get_settings``
            dependency. If omitted, the global
            :func:`motodiag.core.config.get_settings` singleton is
            used.
        db_path_override: override the DB path for the
            ``get_db_path`` dependency. Handy for integration tests
            that want a temp DB without touching Settings.

    Returns:
        A fully wired FastAPI app with CORS + request-id +
        access-log middleware, domain exception handlers, and all
        v1 routers mounted.
    """
    app_settings = settings or get_settings()

    # --- Fail fast on a fake billing provider in production ---
    # `billing_provider` defaults to "fake", whose webhook signature
    # check is a comparison against a hardcoded literal, and whose
    # webhook route is both unauthenticated and rate-limit exempt.
    # A deploy that forgets MOTODIAG_BILLING_PROVIDER=stripe therefore
    # accepts a forged checkout.session.completed and grants any tier
    # to anyone who posts one. That is a config mistake, so it is
    # caught at startup where a config mistake is still cheap, rather
    # than trusted to a runbook (Phase 207).
    if (
        app_settings.env == Environment.PROD
        and app_settings.billing_provider != "stripe"
    ):
        raise RuntimeError(
            "Refusing to start in env=prod with "
            f"billing_provider={app_settings.billing_provider!r}: the "
            "fake provider accepts a hardcoded webhook signature, so "
            "anyone could grant themselves a paid tier. Set "
            "MOTODIAG_BILLING_PROVIDER=stripe (with "
            "MOTODIAG_STRIPE_WEBHOOK_SECRET), or run with "
            "MOTODIAG_ENV=dev if this is a local session."
        )
    # Phase 329 prebuild: a sign-up or a reset by email that would only
    # reach the stand-in sender's memory is a switch turned on too soon.
    if (
        app_settings.env == Environment.PROD
        and app_settings.email_provider == "fake"
        and (app_settings.self_serve_signup_enabled
             or app_settings.individual_signup_enabled
             or app_settings.password_reset_email_enabled)
    ):
        raise RuntimeError(
            "Refusing to start in env=prod with self-serve sign-up or the "
            "password reset by email on while email_provider='fake': no "
            "email would leave the server. Set the email service first, "
            "or turn MOTODIAG_SELF_SERVE_SIGNUP_ENABLED, "
            "MOTODIAG_INDIVIDUAL_SIGNUP_ENABLED and "
            "MOTODIAG_PASSWORD_RESET_EMAIL_ENABLED off."
        )
    # Phase 329: Resend chosen, and its key never typed in.
    if (
        app_settings.env == Environment.PROD
        and app_settings.email_provider == "resend"
        and not app_settings.resend_api_key
    ):
        raise RuntimeError(
            "Refusing to start in env=prod with email_provider='resend' and "
            "no MOTODIAG_RESEND_API_KEY: type the key into the settings "
            "file, or set MOTODIAG_EMAIL_PROVIDER=fake."
        )

    app = FastAPI(
        title="MotoDiag API",
        description=(
            "Motorcycle diagnostic + shop management API. "
            "Exposes the Track G shop console + Track A-F "
            "diagnostic substrate over HTTP."
        ),
        version=app_settings.version,
        # Phase 409 prebuild: the operator decides whether these stay open
        # on the public address (MOTODIAG_API_DOCS_ENABLED).
        openapi_url="/openapi.json" if app_settings.api_docs_enabled else None,
        docs_url="/docs" if app_settings.api_docs_enabled else None,
        redoc_url="/redoc" if app_settings.api_docs_enabled else None,
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.api_cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # --- Request-scoped middleware (innermost first in FastAPI order) ---
    telemetry = install_telemetry(app, app_settings)  # Phase 343 — innermost
    app.add_middleware(AuditMiddleware)  # Phase 348 — inside the rate limit
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RateLimitMiddleware)
    if app_settings.api_max_body_bytes > 0:  # Phase 409 prebuild
        app.add_middleware(
            BodySizeLimitMiddleware, limit=app_settings.api_max_body_bytes,
        )
    app.add_middleware(RequestIdMiddleware)
    # Phase 409 prebuild, outermost: the headers go on every answer the app
    # gives, a 429 included; the host check, when set, runs before all else.
    if app_settings.security_headers_enabled:
        app.add_middleware(SecurityHeadersMiddleware)
    if app_settings.api_allowed_hosts_list:
        from starlette.middleware.trustedhost import TrustedHostMiddleware
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=app_settings.api_allowed_hosts_list,
        )

    # Reset rate limiter so each app-instance has fresh state (tests).
    from motodiag.auth.rate_limiter import reset_rate_limiter
    reset_rate_limiter(settings=app_settings)
    from motodiag.auth.login_throttle import reset_login_throttle
    reset_login_throttle(settings=app_settings)

    # --- Exception → HTTP mapping ---
    register_exception_handlers(app)

    # --- Dependency overrides from kwargs ---
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings
    if db_path_override is not None:
        app.dependency_overrides[get_db_path] = (
            lambda p=db_path_override: p
        )

    # --- Routers (lazy import to keep module-import cheap) ---
    from motodiag.api.routes.audit import router as audit_router
    from motodiag.api.routes.auth import router as auth_router
    from motodiag.api.routes.billing import router as billing_router
    from motodiag.api.routes.diagnostics import router as diagnostics_router
    from motodiag.api.routes.kb import router as kb_router
    from motodiag.api.routes.live import router as live_router
    from motodiag.api.routes.manuals import review_router as manual_review_router
    from motodiag.api.routes.manuals import router as manuals_router
    from motodiag.api.routes.meta import router as meta_router
    from motodiag.api.routes.parts import router as parts_router
    from motodiag.api.routes.payments import router as payments_router
    from motodiag.api.routes.photos import router as photos_router
    from motodiag.api.routes.push import router as push_router
    from motodiag.api.routes.reports import router as reports_router
    from motodiag.api.routes.sessions import router as sessions_router
    from motodiag.api.routes.share import router as share_router
    from motodiag.api.routes.shop_mgmt import router as shop_mgmt_router
    from motodiag.api.routes.shops import router as shops_router
    from motodiag.api.routes.signup import router as signup_router
    from motodiag.api.routes.terms import router as terms_router
    from motodiag.api.routes.time_tracking import router as time_tracking_router
    from motodiag.api.routes.transcripts import router as transcripts_router
    from motodiag.api.routes.vehicles import router as vehicles_router
    from motodiag.api.routes.videos import router as videos_router

    app.include_router(meta_router)             # /healthz, /v1/version
    app.include_router(auth_router, prefix="/v1")  # Phase 303 — staff logins
    app.include_router(terms_router, prefix="/v1")  # Phase 334 — the terms
    app.include_router(shops_router, prefix="/v1")
    app.include_router(billing_router, prefix="/v1")
    app.include_router(vehicles_router, prefix="/v1")
    app.include_router(sessions_router, prefix="/v1")
    app.include_router(kb_router, prefix="/v1")
    app.include_router(shop_mgmt_router, prefix="/v1")
    app.include_router(payments_router, prefix="/v1")  # Phase 372 — card payments
    app.include_router(audit_router, prefix="/v1")  # Phase 348 — audit trail
    app.include_router(reports_router, prefix="/v1")
    app.include_router(videos_router, prefix="/v1")
    app.include_router(photos_router, prefix="/v1")  # Phase 194 — WO photos
    app.include_router(manuals_router, prefix="/v1")  # Phase 293 — shop manuals
    app.include_router(manual_review_router, prefix="/v1")  # Phase 293 — their review
    app.include_router(transcripts_router, prefix="/v1")  # Phase 195 — voice transcripts
    app.include_router(push_router, prefix="/v1")  # Phase 199 — push tokens
    app.include_router(share_router, prefix="/v1")  # Phase 200 — share links
    app.include_router(signup_router, prefix="/v1")  # Phase 329 — sign-up, off by default
    app.include_router(diagnostics_router, prefix="/v1")  # field telemetry
    app.include_router(parts_router, prefix="/v1")  # Phase 201 — parts ordering
    app.include_router(time_tracking_router, prefix="/v1")  # Phase 202 — labor timer
    app.include_router(live_router)             # WS route declares full /v1/live/... path

    # --- Phase 183: OpenAPI enrichment (after routers are mounted) ---
    install_openapi(app)

    # --- Startup log ---
    logger = logging.getLogger("motodiag.api")
    logger.info(
        "motodiag API ready — version=%s, cors=%s, db=%s, telemetry=%s",
        app_settings.version,
        app_settings.api_cors_origins_list,
        db_path_override or app_settings.db_path,
        telemetry,
    )

    return app
