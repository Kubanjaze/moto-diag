"""Workflow rule actions (Phase 173).

Action dicts look like ``{"type": "set_priority", "value": 1}``.
Each executor routes through the canonical Track G repo for its
mutation — never raw SQL. Anti-regression grep test enforces.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional


logger = logging.getLogger(__name__)


ACTION_TYPES: tuple[str, ...] = (
    "set_priority", "flag_urgent", "skip_triage",
    "reassign_to_user", "unassign",
    "trigger_notification", "add_issue_note", "change_status",
)


class InvalidActionError(ValueError):
    """Raised when an action dict is malformed or references an
    unknown type."""


# ---------------------------------------------------------------------------
# Executors
# ---------------------------------------------------------------------------


def _require_wo(ctx: dict) -> dict:
    wo = ctx.get("wo")
    if wo is None:
        raise InvalidActionError(
            "action requires a work_order context (ctx['wo'] is None)"
        )
    return wo


def _a_set_priority(action: dict, ctx: dict, db_path) -> dict:
    """Set WO priority via Phase 161 `update_work_order` whitelist."""
    from motodiag.shop.work_order_repo import update_work_order
    wo = _require_wo(ctx)
    value = int(action["value"])
    update_work_order(
        wo["id"], {"priority": value}, db_path=db_path,
    )
    return {"type": "set_priority", "ok": True, "value": value}


def _a_flag_urgent(action: dict, ctx: dict, db_path) -> dict:
    """Apply Phase 164 urgent marker."""
    from motodiag.shop.triage_queue import flag_urgent
    wo = _require_wo(ctx)
    flag_urgent(wo["id"], db_path=db_path)
    return {"type": "flag_urgent", "ok": True}


def _a_skip_triage(action: dict, ctx: dict, db_path) -> dict:
    """Apply Phase 164 skip marker."""
    from motodiag.shop.triage_queue import skip_work_order
    wo = _require_wo(ctx)
    reason = action.get("reason", "rule skip")
    skip_work_order(wo["id"], reason=reason, db_path=db_path)
    return {"type": "skip_triage", "ok": True, "reason": reason}


def _a_reassign_to_user(action: dict, ctx: dict, db_path) -> dict:
    """Reassign via Phase 172 (which routes back through Phase 161
    whitelist internally)."""
    from motodiag.shop.rbac import reassign_work_order
    wo = _require_wo(ctx)
    mech_id = int(action["value"])
    reason = action.get("reason", "rule reassignment")
    assignment_id = reassign_work_order(
        wo["id"],
        new_mechanic_user_id=mech_id,
        reason=reason,
        db_path=db_path,
    )
    return {
        "type": "reassign_to_user", "ok": True,
        "assignment_id": assignment_id, "mechanic_user_id": mech_id,
    }


def _a_unassign(action: dict, ctx: dict, db_path) -> dict:
    from motodiag.shop.rbac import reassign_work_order
    wo = _require_wo(ctx)
    reason = action.get("reason", "rule unassignment")
    aid = reassign_work_order(
        wo["id"], new_mechanic_user_id=None,
        reason=reason, db_path=db_path,
    )
    return {"type": "unassign", "ok": True, "assignment_id": aid}


def _a_trigger_notification(action: dict, ctx: dict, db_path) -> dict:
    """Fire a Phase 170 notification."""
    from motodiag.shop.notifications import trigger_notification
    wo = _require_wo(ctx)
    event = action["event"]
    channel = action.get("channel", "email")
    extra = action.get("extra_context") or None
    nid = trigger_notification(
        event, wo_id=wo["id"], channel=channel,
        extra_context=extra, db_path=db_path,
    )
    return {
        "type": "trigger_notification", "ok": True,
        "notification_id": nid, "event": event, "channel": channel,
    }


def _a_add_issue_note(action: dict, ctx: dict, db_path) -> dict:
    """Append a note to the WO's most-recent open issue via Phase 162
    `update_issue` whitelist."""
    from motodiag.shop.issue_repo import update_issue
    issues = ctx.get("issues") or []
    open_issues = [i for i in issues if i.get("status") == "open"]
    if not open_issues:
        return {
            "type": "add_issue_note", "ok": False,
            "detail": "no open issues on WO",
        }
    target = open_issues[0]
    note = action.get("note") or action.get("value") or ""
    existing = (target.get("description") or "").rstrip()
    appended = (existing + "\n" + note).strip() if existing else note
    update_issue(
        target["id"], {"description": appended}, db_path=db_path,
    )
    return {
        "type": "add_issue_note", "ok": True,
        "issue_id": target["id"],
    }


def _a_change_status(action: dict, ctx: dict, db_path) -> dict:
    """Route through Phase 161 lifecycle transition functions
    (never generic `update_work_order`)."""
    from motodiag.shop.work_order_repo import (
        cancel_work_order, complete_work_order, open_work_order,
        pause_work, reopen_work_order, resume_work, start_work,
    )
    wo = _require_wo(ctx)
    target = action["value"]
    dispatch = {
        "open": lambda: open_work_order(wo["id"], db_path=db_path),
        "in_progress": lambda: start_work(wo["id"], db_path=db_path),
        "on_hold": lambda: pause_work(
            wo["id"], reason=action.get("reason"), db_path=db_path,
        ),
        "resume": lambda: resume_work(wo["id"], db_path=db_path),
        "completed": lambda: complete_work_order(
            wo["id"],
            actual_hours=action.get("actual_hours"),
            db_path=db_path,
        ),
        "cancelled": lambda: cancel_work_order(
            wo["id"], reason=action.get("reason") or "rule cancellation",
            db_path=db_path,
        ),
        "reopen": lambda: reopen_work_order(wo["id"], db_path=db_path),
    }
    if target not in dispatch:
        raise InvalidActionError(
            f"change_status value {target!r} not in "
            f"{sorted(dispatch.keys())}"
        )
    dispatch[target]()
    return {"type": "change_status", "ok": True, "target": target}


_REGISTRY: dict[str, Callable[[dict, dict, Optional[str]], dict]] = {
    "set_priority": _a_set_priority,
    "flag_urgent": _a_flag_urgent,
    "skip_triage": _a_skip_triage,
    "reassign_to_user": _a_reassign_to_user,
    "unassign": _a_unassign,
    "trigger_notification": _a_trigger_notification,
    "add_issue_note": _a_add_issue_note,
    "change_status": _a_change_status,
}


# ---------------------------------------------------------------------------
# Validation + dispatch
# ---------------------------------------------------------------------------


def validate_action(action: dict) -> None:
    if not isinstance(action, dict):
        raise InvalidActionError(
            f"action must be a dict, got {type(action).__name__}"
        )
    atype = action.get("type")
    if atype not in ACTION_TYPES:
        raise InvalidActionError(
            f"unknown action type {atype!r}; expected one of {ACTION_TYPES}"
        )
    if atype in {"set_priority", "reassign_to_user"}:
        if "value" not in action:
            raise InvalidActionError(
                f"action type {atype!r} requires 'value' field"
            )
    if atype == "trigger_notification":
        if "event" not in action:
            raise InvalidActionError(
                "trigger_notification action requires 'event' field"
            )
    if atype == "change_status":
        if "value" not in action:
            raise InvalidActionError(
                "change_status action requires 'value' field"
            )


def validate_actions(actions: list[dict]) -> None:
    if not isinstance(actions, list):
        raise InvalidActionError("actions must be a list")
    for a in actions:
        validate_action(a)


def execute_action(action: dict, ctx: dict, db_path) -> dict:
    """Dispatch + execute. Returns the per-action result dict."""
    fn = _REGISTRY[action["type"]]
    return fn(action, ctx, db_path)
