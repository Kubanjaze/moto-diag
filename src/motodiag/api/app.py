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
    RateLimitMiddleware,
    RequestIdMiddleware,
)
from motodiag.core.config import Settings


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
    app = FastAPI(
        title="MotoDiag API",
        description=(
            "Motorcycle diagnostic + shop management API. "
            "Exposes the Track G shop console + Track A-F "
            "diagnostic substrate over HTTP."
        ),
        version=app_settings.version,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
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
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # Reset rate limiter so each app-instance has fresh state (tests).
    from motodiag.auth.rate_limiter import reset_rate_limiter
    reset_rate_limiter(settings=app_settings)

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
    from motodiag.api.routes.billing import router as billing_router
    from motodiag.api.routes.kb import router as kb_router
    from motodiag.api.routes.meta import router as meta_router
    from motodiag.api.routes.sessions import router as sessions_router
    from motodiag.api.routes.shops import router as shops_router
    from motodiag.api.routes.vehicles import router as vehicles_router

    app.include_router(meta_router)             # /healthz, /v1/version
    app.include_router(shops_router, prefix="/v1")
    app.include_router(billing_router, prefix="/v1")
    app.include_router(vehicles_router, prefix="/v1")
    app.include_router(sessions_router, prefix="/v1")
    app.include_router(kb_router, prefix="/v1")

    # --- Startup log ---
    logger = logging.getLogger("motodiag.api")
    logger.info(
        "motodiag API ready — version=%s, cors=%s, db=%s",
        app_settings.version,
        app_settings.api_cors_origins_list,
        db_path_override or app_settings.db_path,
    )

    return app
