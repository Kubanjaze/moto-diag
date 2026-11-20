"""Who accepted which version of the Terms of Service, and when (Phase 334, K84).

``TERMS_VERSION`` and ``TERMS_DATE`` are the one place the server knows the
current version; a test holds them equal to ``docs/legal/terms.md``'s header.
A row of ``terms_acceptances`` (migration 091) counts only for its own
version, so a new version must be accepted again.

``TERMS_EXEMPT_PATHS`` is the one record of what a signed-in user who has not
accepted may still call while ``MOTODIAG_TERMS_REQUIRED`` is on: read the
terms, accept them, see who they are, or sign out.
"""

from __future__ import annotations

from typing import Optional

from motodiag.core.database import get_connection
from motodiag.core.timestamps import utc_now

TERMS_VERSION = "1.0"
TERMS_DATE = "2026-11-19"

TERMS_EXEMPT_PATHS = (
    "/v1/terms",
    "/v1/terms/accept",
    "/v1/auth/me",
    "/v1/auth/logout",
)


class TermsNotAcceptedError(Exception):
    """403: the switch is on and the caller has not accepted the current version."""


class TermsVersionStaleError(ValueError):
    """422: the version sent is not the current one."""


def not_accepted_message(version: str) -> str:
    """The plain message a refused call carries."""
    return (
        f"Accept the current Terms of Service (version {version}) first: "
        "read GET /v1/terms, then POST /v1/terms/accept."
    )


def get_acceptance(user_id: int, version: str,
                   db_path: Optional[str] = None) -> Optional[dict]:
    """The user's row for exactly this version, or None."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, user_id, version, accepted_at FROM terms_acceptances "
            "WHERE user_id = ? AND version = ?",
            (user_id, version),
        ).fetchone()
    return dict(row) if row is not None else None


def has_accepted(user_id: int, version: str, db_path: Optional[str] = None) -> bool:
    """True only for a row of exactly this version: an older one does not count."""
    return get_acceptance(user_id, version, db_path) is not None


def record_acceptance(user_id: int, version: str,
                      db_path: Optional[str] = None) -> dict:
    """Record the acceptance with the UTC time and return its row.

    A second acceptance of the same version inserts nothing and returns the
    first row; the unique index on ``(user_id, version)`` holds it.
    """
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO terms_acceptances (user_id, version, accepted_at) "
            "VALUES (?, ?, ?) ON CONFLICT (user_id, version) DO NOTHING",
            (user_id, version, utc_now()),
        )
        row = conn.execute(
            "SELECT id, user_id, version, accepted_at FROM terms_acceptances "
            "WHERE user_id = ? AND version = ?",
            (user_id, version),
        ).fetchone()
    return dict(row)
