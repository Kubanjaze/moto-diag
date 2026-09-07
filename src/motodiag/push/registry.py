"""Phase 199 — device-token registry (CRUD over ``device_tokens``).

Invariant (decided at Step 0, per the 198 data-invariant lesson):
one row per TOKEN (UNIQUE) — a token re-registered by a different user
REBINDS to that user (shared-device reality) rather than duplicating.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from motodiag.core.database import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_token(
    user_id: int,
    token: str,
    platform: str = "ios",
    db_path: Optional[str] = None,
) -> None:
    """Insert or rebind a device token to ``user_id``."""
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO device_tokens
                 (user_id, token, platform, created_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(token) DO UPDATE SET
                 user_id = excluded.user_id,
                 platform = excluded.platform,
                 last_seen_at = excluded.last_seen_at""",
            (user_id, token, platform, _now(), _now()),
        )


def delete_token(
    token: str,
    db_path: Optional[str] = None,
    user_id: Optional[int] = None,
) -> bool:
    """Remove a token (sign-out hygiene or APNs 410 prune).

    Pass `user_id` when a request is deregistering its OWN device, so
    one authenticated user cannot silence another's notifications by
    posting a token they happened to learn. The APNs 410 prune path
    has no caller identity and deliberately omits it (Phase 207).
    """
    sql = "DELETE FROM device_tokens WHERE token = ?"
    params: list = [token]
    if user_id is not None:
        sql += " AND user_id = ?"
        params.append(user_id)
    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return cursor.rowcount > 0


def tokens_for_user(
    user_id: int, db_path: Optional[str] = None,
) -> list[str]:
    """All live tokens for a user (usually 1; multi-device legal)."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT token FROM device_tokens WHERE user_id = ? "
            "ORDER BY last_seen_at DESC",
            (user_id,),
        )
        return [row[0] for row in cursor.fetchall()]
