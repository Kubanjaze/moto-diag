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
            # F52 — log successes, not just failures. Phase 199's device
            # smoke had to prove delivery by the ABSENCE of warnings plus
            # a hand-rolled sender call, because a working push left no
            # trace at all. One INFO line makes the happy path legible.
            logger.info(
                "push sent to user %s (%s)", user_id, title,
            )
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


def notify_parts_arrived(
    wo: dict,
    line: dict,
    acting_user_id: int,
    db_path: Optional[str] = None,
) -> None:
    """Phase 201 — push the assigned mechanic when a part line is
    marked received. The `parts_arrived` producer Phase 170's enum
    waited for; this is the mechanic half, the customer half is the
    170 queue row the route writes alongside."""
    try:
        assignee = wo.get("assigned_mechanic_user_id")
        if not assignee or assignee == acting_user_id:
            return
        qty = int(line.get("quantity") or 1)
        what = (
            str(line.get("description") or line.get("part_description")
                or line.get("slug") or line.get("part_slug") or "part")
        ).strip()
        title = f"Parts arrived for work order #{wo.get('id')}"
        body = f"{qty}× {what}" if qty > 1 else what
        _send_to_user(
            int(assignee), title, body,
            thread_id=f"wo-{wo.get('id')}", db_path=db_path,
        )
    except Exception:  # noqa: BLE001 — best-effort by design
        logger.exception("notify_parts_arrived failed (suppressed)")


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


def notify_obd_failure(
    report_id: int,
    error_kind: str,
    transport: Optional[str],
    device_id: Optional[str],
    message: Optional[str],
    db_path: Optional[str] = None,
) -> bool:
    """Alert the MAINTAINER that a mechanic could not connect an adapter.

    Deliberately not shop-scoped: the audience is whoever can fix the
    app, not the shop. Configured via ``MOTODIAG_ADMIN_USER_ID``; 0 (the
    default) disables alerts entirely, which is the right default for
    anyone running their own instance.

    Best-effort like every other push path — a telemetry alert must never
    propagate into the endpoint that recorded the failure. Returns True
    when an alert was actually sent.
    """
    try:
        from motodiag.core.config import get_settings
        from motodiag.obd_reports import (
            mark_notified, should_alert,
        )

        admin_id = int(getattr(get_settings(), "admin_user_id", 0) or 0)
        if admin_id <= 0:
            return False
        if not should_alert(error_kind, transport, db_path=db_path):
            # A dongle that will not connect gets retried, not tried once.
            # Twelve identical pushes would get the alerts muted, which
            # would hide the NEXT real signal.
            logger.info(
                "OBD failure %s suppressed (recent alert for %s/%s)",
                report_id, error_kind, transport,
            )
            return False

        where = f" on {device_id}" if device_id else ""
        detail = (message or "").strip()
        sent = _send_to_user(
            admin_id,
            f"OBD connect failed ({transport or 'unknown'})",
            f"{error_kind}{where}"
            + (f" — {detail[:120]}" if detail else "")
            + ". A mechanic could not connect an adapter.",
            thread_id="obd-failure",
            db_path=db_path,
        )
        if sent:
            mark_notified(report_id, db_path=db_path)
            return True
        return False
    except Exception:  # noqa: BLE001 — telemetry never breaks the caller
        logger.exception("notify_obd_failure failed (suppressed)")
        return False
