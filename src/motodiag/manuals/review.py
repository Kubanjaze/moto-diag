"""The person at Mekno who reviews every upload before anyone opens it (K119).

A reviewer is a row of ``manual_reviewers``: the first kind of account that
can open any shop's files, held apart from ``shop_members`` because a
reviewer is a member of no shop, and granted only from the server's command
line. ``require_reviewer`` is the API's gate; no one else can open a file
waiting for review.

A decision records who and when (UTC). ``approved`` waits until every page
is rendered; ``rejected`` and ``taken_down`` carry a reason the shop sees. A
publisher's complaint arrives outside the API and is recorded as
``taken_down``. After approval any member of the shop may ``flag`` a page,
which sends the manual back to review until it is decided again.
"""

from __future__ import annotations

from typing import Callable, Optional

from fastapi import Depends

from motodiag.api.deps import get_db_path
from motodiag.auth.deps import AuthedUser, get_current_user
from motodiag.core.database import get_connection
from motodiag.core.timestamps import utc_now
from motodiag.manuals import (
    ManualConflictError,
    ManualNotFoundError,
    ManualReasonRequiredError,
)
from motodiag.reference import manual_repo
from motodiag.shop.rbac import PermissionDenied


def is_reviewer(user_id: int, db_path: Optional[str] = None) -> bool:
    with get_connection(db_path) as conn:
        return conn.execute("SELECT 1 FROM manual_reviewers WHERE user_id = ?",
                            (user_id,)).fetchone() is not None


def grant_reviewer(user_id: int, granted_by: Optional[int] = None,
                   db_path: Optional[str] = None) -> bool:
    """True when the grant is new; a second grant changes nothing."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO manual_reviewers (user_id, granted_at, granted_by_user_id) "
            "VALUES (?, ?, ?) ON CONFLICT (user_id) DO NOTHING",
            (user_id, utc_now(), granted_by),
        )
        return cur.rowcount > 0


def revoke_reviewer(user_id: int, db_path: Optional[str] = None) -> bool:
    with get_connection(db_path) as conn:
        return conn.execute("DELETE FROM manual_reviewers WHERE user_id = ?",
                            (user_id,)).rowcount > 0


def list_reviewers(db_path: Optional[str] = None) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT r.user_id, u.username, r.granted_at, r.granted_by_user_id "
            "FROM manual_reviewers r LEFT JOIN users u ON u.id = r.user_id "
            "ORDER BY r.granted_at, r.user_id").fetchall()
    return [dict(r) for r in rows]


def _not_ready(manual: dict) -> Optional[str]:
    if manual["render_error"] is not None:
        return f"its pages failed to render: {manual['render_error']}"
    if manual["rendered_pages"] < (manual["page_count"] or 0):
        return (f"its pages are still rendering ({manual['rendered_pages']} of "
                f"{manual['page_count']})")
    return None


def decide(manual_id: int, decision: str, reason: Optional[str], reviewer_id: int,
           tag_fixes: Optional[dict] = None, clock: Callable[[], str] = utc_now,
           db_path: Optional[str] = None) -> dict:
    """Record a decision, after fixing the tag fields given. Returns the row."""
    manual = manual_repo.get_manual(manual_id, db_path=db_path)
    if manual is None or manual.get("shop_id") is None:
        raise ManualNotFoundError(f"manual id={manual_id} not found")
    reason = (reason or "").strip() or None
    if decision in ("rejected", "taken_down") and reason is None:
        raise ManualReasonRequiredError(
            f"a {decision.replace('_', ' ')} decision needs a reason the shop can read")
    if decision == "approved":
        why = _not_ready(manual)
        if why is not None:
            raise ManualConflictError(f"manual id={manual_id} cannot be approved yet: {why}")
    if tag_fixes:
        manual_repo.update_tag(manual_id, db_path=db_path, **tag_fixes)
    manual_repo.set_status(manual_id, decision, reviewer_id, reason, clock, db_path=db_path)
    return manual_repo.get_manual(manual_id, db_path=db_path) or {}


def flag(manual_id: int, user_id: int, page_number: int, reason: str,
         db_path: Optional[str] = None) -> dict:
    """A member's flag on an approved manual sends it back to review."""
    manual = manual_repo.get_manual(manual_id, db_path=db_path)
    if manual is None:
        raise ManualNotFoundError(f"manual id={manual_id} not found")
    if manual["status"] != "approved":
        raise ManualConflictError(
            f"manual id={manual_id} is {manual['status']}, so it cannot be flagged")
    manual_repo.update_manual(
        manual_id, db_path=db_path, status="pending_review",
        review_reason=f"flagged on page {page_number} by user {user_id}: {reason}",
        reviewed_by_user_id=None, reviewed_at=None,
    )
    return manual_repo.get_manual(manual_id, db_path=db_path) or {}


async def require_reviewer(
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> AuthedUser:
    """403 for anyone not in ``manual_reviewers``, whatever their shop role."""
    if not is_reviewer(user.id, db_path):
        raise PermissionDenied(f"user id={user.id} does not review manuals")
    return user
