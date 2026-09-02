"""Phase 199 — event → push glue (recipient resolution + copy).

The two LIVE producers (plan scope): work-order transitions/assignment
(Phase 193 endpoints) and video-analysis completion (Phase 191B/192
worker). Copy here is MECHANIC-voiced — deliberately NOT the Phase 170
customer templates (different audience; see plan audience decision).

Self-suppression rule (plan Risks): never push a user about an action
they themselves performed.

Everything is best-effort: failures log and never propagate into the
calling endpoint/worker.
"""

from __future__ import annotations

import logging
from typing import Optional

from motodiag.push.registry import delete_token, tokens_for_user
from motodiag.push.sender import get_sender

logger = logging.getLogger(__name__)

#: Mechanic-voiced copy per WO transition action.
_WO_ACTION_COPY: dict[str, str] = {
    "open": "was opened",
    "start": "was started",
    "pause": "was put on hold",
    "resume": "was resumed",
    "complete": "was completed",
    "cancel": "was cancelled",
    "reopen": "was reopened",
}


def _send_to_user(
    user_id: int,
    title: str,
    body: str,
    thread_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Send to all of a user's tokens; prune dead ones. Returns sends."""
    sender = get_sender()
    sent = 0
    for token in tokens_for_user(user_id, db_path=db_path):
        result = sender.send(token, title, body, thread_id=thread_id)
        if result.unregistered:
            delete_token(token, db_path=db_path)
            logger.info("pruned unregistered token for user %s", user_id)
        elif result.ok:
            sent += 1
    return sent


def notify_wo_transition(
    wo: dict,
    action: str,
    acting_user_id: int,
    db_path: Optional[str] = None,
) -> None:
    """Push the assigned mechanic about a WO state change."""
    try:
        assignee = wo.get("assigned_mechanic_user_id")
        if not assignee or assignee == acting_user_id:
            return  # nobody to tell, or they did it themselves
        verb = _WO_ACTION_COPY.get(action)
        if verb is None:
            return
        title = f"Work order #{wo.get('id')} {verb}"
        body = str(wo.get("title") or "").strip() or "Open the shop tab for details."
        _send_to_user(
            int(assignee), title, body,
            thread_id=f"wo-{wo.get('id')}", db_path=db_path,
        )
    except Exception:  # noqa: BLE001 — best-effort by design
        logger.exception("notify_wo_transition failed (suppressed)")


def notify_wo_assigned(
    wo: dict,
    assignee_user_id: Optional[int],
    acting_user_id: int,
    db_path: Optional[str] = None,
) -> None:
    """Push a mechanic when a WO lands on their plate."""
    try:
        if not assignee_user_id or assignee_user_id == acting_user_id:
            return
        title = f"Work order #{wo.get('id')} assigned to you"
        body = str(wo.get("title") or "").strip() or "Open the shop tab for details."
        _send_to_user(
            int(assignee_user_id), title, body,
            thread_id=f"wo-{wo.get('id')}", db_path=db_path,
        )
    except Exception:  # noqa: BLE001
        logger.exception("notify_wo_assigned failed (suppressed)")


def notify_analysis_complete(
    session_id: int,
    video_id: int,
    db_path: Optional[str] = None,
) -> None:
    """Push the session owner when a video analysis finishes."""
    try:
        from motodiag.core.database import get_connection

        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT user_id, vehicle_make, vehicle_model "
                "FROM diagnostic_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        if row is None or row[0] is None:
            return
        bike = " ".join(str(v) for v in (row[1], row[2]) if v) or "your bike"
        _send_to_user(
            int(row[0]),
            "Diagnostic analysis ready",
            f"Video analysis for {bike} finished — open the session to review findings.",
            thread_id=f"session-{session_id}",
            db_path=db_path,
        )
    except Exception:  # noqa: BLE001
        logger.exception("notify_analysis_complete failed (suppressed)")
