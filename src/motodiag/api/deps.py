"""FastAPI dependency providers (Phase 175).

All external resources (DB path, Settings, request metadata) flow
through ``Depends(...)`` so tests can override cleanly via
``app.dependency_overrides``.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Request

from motodiag.core.config import Settings, get_settings as _get_settings


def get_settings() -> Settings:
    """Return the process-level Settings singleton.

    Tests override via ``app.dependency_overrides[get_settings] =
    lambda: Settings(db_path="...")``.
    """
    return _get_settings()


def get_db_path() -> str:
    """Return the SQLite DB path from Settings.

    Tests override via ``app.dependency_overrides[get_db_path] =
    lambda: str(tmp_path / "test.db")`` — the preferred seam for
    route-level integration tests that don't want to mutate the
    global Settings.
    """
    return get_settings().db_path


def get_request_id(request: Request) -> Optional[str]:
    """Return the request-scoped request id set by
    :class:`RequestIdMiddleware`, or ``None`` if the middleware
    hasn't run (shouldn't happen in production)."""
    return getattr(request.state, "request_id", None)
