"""Phase 209D — which shop a piece of work, and its AI spend, belongs to.

Every ``cost_events`` row written before this phase had ``shop_id = NULL``
for vision and text: voice attributed because its route is shop-scoped, and
nothing else had a shop to point at. A monthly cap read through
``shop_cost_this_month`` would have seen $0 for every shop and never fired.

The chain is short and always the same: a video belongs to a session, and
since migration 061 a session belongs to a shop. These lookups are the only
place that chain is spelled out, so a caller that needs the shop of a paid
call asks here rather than writing the join again.

All of them return ``None`` rather than raising. No shop is a legitimate
state -- a walk-in diagnosis, a CLI session on a machine that runs no shop --
and a lookup failing must never take down the work it was annotating.
"""

from __future__ import annotations

import logging
from typing import Optional

from motodiag.core.database import get_connection

log = logging.getLogger(__name__)


def _one(sql: str, params: tuple, db_path: Optional[str]) -> Optional[int]:
    try:
        with get_connection(db_path) as conn:
            row = conn.execute(sql, params).fetchone()
    except Exception:
        log.warning("shop lookup failed: %s", sql.split("FROM")[0].strip(),
                    exc_info=True)
        return None
    if row is None or row[0] is None:
        return None
    return int(row[0])


def shop_for_user(user_id: int, db_path: Optional[str] = None) -> Optional[int]:
    """The user's shop, when they have exactly one active membership.

    Two memberships mean the work could belong to either, and guessing would
    put one shop's spend on another's ledger. That case stays unattributed
    until the client says which -- see the F-ticket on the app sending its
    active shop.
    """
    return _one(
        "SELECT shop_id FROM shop_members "
        "WHERE user_id = ? AND is_active = 1 "
        "GROUP BY user_id HAVING COUNT(*) = 1",
        (user_id,), db_path,
    )


def only_shop(db_path: Optional[str] = None) -> Optional[int]:
    """The shop this database runs, when it runs exactly one.

    For the CLI, which has no authenticated user. One shop per deployment is
    the shape the operator chose on 2026-09-17 (each shop runs its own
    server); a database with two shops gets no guess.
    """
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute("SELECT id FROM shops LIMIT 2").fetchall()
    except Exception:
        log.warning("shop lookup failed: only_shop", exc_info=True)
        return None
    return int(rows[0][0]) if len(rows) == 1 else None


def shop_for_session(
    session_id: int, db_path: Optional[str] = None,
) -> Optional[int]:
    """The shop stamped on a session when it was created (migration 061)."""
    return _one(
        "SELECT shop_id FROM diagnostic_sessions WHERE id = ?",
        (session_id,), db_path,
    )


def shop_for_video(video_id: int, db_path: Optional[str] = None) -> Optional[int]:
    """The shop paying for a video's sweep and its questions."""
    return _one(
        "SELECT s.shop_id FROM videos v "
        "JOIN diagnostic_sessions s ON s.id = v.session_id "
        "WHERE v.id = ?",
        (video_id,), db_path,
    )
