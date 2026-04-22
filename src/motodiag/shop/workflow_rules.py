"""Workflow rule engine (Phase 173).

If-this-then-that rule engine composing Track G primitives. Rules are
JSON data in ``workflow_rules.conditions_json`` + ``actions_json``; the
engine is a fixed dispatcher.

Fire modes:
- Event-driven: :func:`trigger_rules_for_event` finds all active rules
  for a shop + event, fires in ``priority ASC`` order.
- Manual: :func:`fire_rule_for_wo` runs one specific rule.

Every firing writes a :class:`WorkflowRuleRun` row whether matched or
not. Action failures don't block sibling actions; the first error is
captured in the run row's ``error`` column.
"""

from __future__ import annotations

import json as _json
import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from motodiag.core.database import get_connection
from motodiag.shop.workflow_actions import (
    ACTION_TYPES, InvalidActionError,
    execute_action, validate_actions,
)
from motodiag.shop.workflow_conditions import (
    CONDITION_TYPES, InvalidConditionError,
    evaluate_conditions, validate_conditions,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


EVENT_TRIGGERS: tuple[str, ...] = (
    "wo_opened", "wo_in_progress", "wo_completed", "wo_cancelled",
    "parts_arrived", "invoice_issued", "invoice_paid",
    "issue_added", "manual",
)

EventTrigger = Literal[
    "wo_opened", "wo_in_progress", "wo_completed", "wo_cancelled",
    "parts_arrived", "invoice_issued", "invoice_paid",
    "issue_added", "manual",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InvalidEventError(ValueError):
    """Raised when event_trigger is not in EVENT_TRIGGERS."""


class RuleNotFoundError(ValueError):
    """Raised when a rule_id does not resolve."""


class DuplicateRuleNameError(ValueError):
    """Raised when trying to create a rule with a name already used
    at that shop (UNIQUE(shop_id, name))."""


# ---------------------------------------------------------------------------
# Pydantic
# ---------------------------------------------------------------------------


class WorkflowRule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    shop_id: int
    name: str
    description: Optional[str]
    event_trigger: str
    conditions: list[dict] = Field(default_factory=list)
    actions: list[dict] = Field(default_factory=list)
    priority: int = 100
    is_active: bool = True
    created_by_user_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WorkflowRuleRun(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    rule_id: int
    work_order_id: Optional[int]
    triggered_event: Optional[str]
    matched: bool
    actions_log: list[dict] = Field(default_factory=list)
    error: Optional[str] = None
    actor_user_id: Optional[int] = None
    fired_at: str


class RuleRunResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rule_id: int
    rule_name: str
    work_order_id: Optional[int]
    matched: bool
    actions_log: list[dict] = Field(default_factory=list)
    error: Optional[str] = None
    run_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_event(event: str) -> None:
    if event not in EVENT_TRIGGERS:
        raise InvalidEventError(
            f"event_trigger {event!r} not in {EVENT_TRIGGERS}"
        )


def _row_to_rule(row) -> WorkflowRule:
    d = dict(row)
    return WorkflowRule(
        id=int(d["id"]),
        shop_id=int(d["shop_id"]),
        name=str(d["name"]),
        description=d.get("description"),
        event_trigger=str(d["event_trigger"]),
        conditions=_json.loads(d.get("conditions_json") or "[]"),
        actions=_json.loads(d.get("actions_json") or "[]"),
        priority=int(d.get("priority") or 100),
        is_active=bool(d.get("is_active", 1)),
        created_by_user_id=d.get("created_by_user_id"),
        created_at=d.get("created_at"),
        updated_at=d.get("updated_at"),
    )


def _row_to_run(row) -> WorkflowRuleRun:
    d = dict(row)
    return WorkflowRuleRun(
        id=int(d["id"]),
        rule_id=int(d["rule_id"]),
        work_order_id=d.get("work_order_id"),
        triggered_event=d.get("triggered_event"),
        matched=bool(d.get("matched", 0)),
        actions_log=_json.loads(d.get("actions_log") or "[]"),
        error=d.get("error"),
        actor_user_id=d.get("actor_user_id"),
        fired_at=str(d["fired_at"]),
    )


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------


def build_wo_context(
    wo_id: int, db_path: Optional[str] = None,
) -> dict:
    """Fetch WO + issues + parts + invoice + shop into one dict.

    Missing entities return as None / empty list; condition evaluators
    handle gracefully. This is called once per rule firing so a rule
    with 5 conditions doesn't re-query.
    """
    from motodiag.shop.work_order_repo import get_work_order
    wo = get_work_order(wo_id, db_path=db_path)
    if wo is None:
        return {"wo": None, "issues": [], "parts": [], "invoice": None, "shop": None}
    issues: list[dict] = []
    parts: list[dict] = []
    invoice: Optional[dict] = None
    shop: Optional[dict] = None
    with get_connection(db_path) as conn:
        issues = [
            dict(r) for r in conn.execute(
                "SELECT * FROM issues WHERE work_order_id = ? "
                "ORDER BY id", (wo_id,),
            ).fetchall()
        ]
        parts = [
            dict(r) for r in conn.execute(
                """SELECT wop.*,
                          p.slug, p.description AS part_description,
                          p.typical_cost_cents
                   FROM work_order_parts wop
                   JOIN parts p ON p.id = wop.part_id
                   WHERE wop.work_order_id = ?
                     AND wop.status != 'cancelled'
                   ORDER BY wop.id""",
                (wo_id,),
            ).fetchall()
        ]
        inv_row = conn.execute(
            "SELECT * FROM invoices WHERE work_order_id = ? "
            "AND status != 'cancelled' ORDER BY id DESC LIMIT 1",
            (wo_id,),
        ).fetchone()
        if inv_row is not None:
            invoice = dict(inv_row)
        shop_row = conn.execute(
            "SELECT * FROM shops WHERE id = ?", (wo["shop_id"],),
        ).fetchone()
        if shop_row is not None:
            shop = dict(shop_row)
    return {
        "wo": dict(wo),
        "issues": issues,
        "parts": parts,
        "invoice": invoice,
        "shop": shop,
    }


# ---------------------------------------------------------------------------
# Rule CRUD
# ---------------------------------------------------------------------------


def create_rule(
    shop_id: int,
    name: str,
    event_trigger: str,
    conditions: list[dict],
    actions: list[dict],
    priority: int = 100,
    description: Optional[str] = None,
    created_by_user_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> int:
    """Validate + persist a new rule. Returns rule_id."""
    _validate_event(event_trigger)
    validate_conditions(conditions)
    validate_actions(actions)
    import sqlite3
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        try:
            cursor = conn.execute(
                """INSERT INTO workflow_rules
                   (shop_id, name, description, event_trigger,
                    conditions_json, actions_json, priority,
                    is_active, created_by_user_id, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                (
                    shop_id, name, description, event_trigger,
                    _json.dumps(conditions), _json.dumps(actions),
                    priority, created_by_user_id, now,
                ),
            )
            return int(cursor.lastrowid)
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise DuplicateRuleNameError(
                    f"rule name {name!r} already exists at shop_id={shop_id}"
                ) from e
            raise


def get_rule(
    rule_id: int, db_path: Optional[str] = None,
) -> Optional[WorkflowRule]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM workflow_rules WHERE id = ?", (rule_id,),
        ).fetchone()
    return _row_to_rule(row) if row else None


def require_rule(rule_id: int, db_path: Optional[str] = None) -> WorkflowRule:
    rule = get_rule(rule_id, db_path=db_path)
    if rule is None:
        raise RuleNotFoundError(f"rule not found: id={rule_id}")
    return rule


def list_rules(
    shop_id: Optional[int] = None,
    event_trigger: Optional[str] = None,
    active_only: bool = True,
    db_path: Optional[str] = None,
) -> list[WorkflowRule]:
    if event_trigger is not None:
        _validate_event(event_trigger)
    query = "SELECT * FROM workflow_rules WHERE 1=1"
    params: list = []
    if shop_id is not None:
        query += " AND shop_id = ?"
        params.append(shop_id)
    if event_trigger is not None:
        query += " AND event_trigger = ?"
        params.append(event_trigger)
    if active_only:
        query += " AND is_active = 1"
    query += " ORDER BY priority ASC, id ASC"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_rule(r) for r in rows]


_UPDATABLE_FIELDS = frozenset({
    "name", "description", "conditions_json", "actions_json",
    "priority",
})


def update_rule(
    rule_id: int, db_path: Optional[str] = None,
    **fields,
) -> bool:
    """Update allowed fields on a rule. `conditions` / `actions`
    kwargs are JSON-encoded + validated before persisting."""
    changes: dict = {}
    if "conditions" in fields:
        validate_conditions(fields["conditions"])
        changes["conditions_json"] = _json.dumps(fields.pop("conditions"))
    if "actions" in fields:
        validate_actions(fields["actions"])
        changes["actions_json"] = _json.dumps(fields.pop("actions"))
    for k, v in fields.items():
        if k not in _UPDATABLE_FIELDS:
            raise ValueError(
                f"field {k!r} is not updatable; use enable/disable "
                "helpers for is_active"
            )
        changes[k] = v
    if not changes:
        return False
    changes["updated_at"] = datetime.now(timezone.utc).isoformat()
    keys = ", ".join(f"{k} = ?" for k in changes)
    params = list(changes.values()) + [rule_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE workflow_rules SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def _set_active(
    rule_id: int, active: int, db_path: Optional[str],
) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE workflow_rules SET is_active = ?, updated_at = ? "
            "WHERE id = ?",
            (active, now, rule_id),
        )
        return cursor.rowcount > 0


def enable_rule(rule_id: int, db_path: Optional[str] = None) -> bool:
    return _set_active(rule_id, 1, db_path)


def disable_rule(rule_id: int, db_path: Optional[str] = None) -> bool:
    return _set_active(rule_id, 0, db_path)


def delete_rule(rule_id: int, db_path: Optional[str] = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM workflow_rules WHERE id = ?", (rule_id,),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_rule(
    rule: WorkflowRule, ctx: dict,
) -> bool:
    """AND-compose all conditions. Empty list → always True."""
    return evaluate_conditions(rule.conditions, ctx)


# ---------------------------------------------------------------------------
# Firing
# ---------------------------------------------------------------------------


def _log_run(
    rule_id: int, wo_id: Optional[int], triggered_event: Optional[str],
    matched: bool, actions_log: list[dict], error: Optional[str],
    actor_user_id: Optional[int], db_path: Optional[str],
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO workflow_rule_runs
               (rule_id, work_order_id, triggered_event, matched,
                actions_log, error, actor_user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                rule_id, wo_id, triggered_event, 1 if matched else 0,
                _json.dumps(actions_log), error, actor_user_id,
            ),
        )
        return int(cursor.lastrowid)


def fire_rule_for_wo(
    rule_id: int, wo_id: int,
    actor_user_id: Optional[int] = None,
    triggered_event: Optional[str] = None,
    db_path: Optional[str] = None,
    _context: Optional[dict] = None,
) -> RuleRunResult:
    """Evaluate + execute. Always writes a workflow_rule_runs row.

    ``_context`` is a cache hook — :func:`trigger_rules_for_event`
    reuses one context across all rules for the same WO.
    """
    rule = require_rule(rule_id, db_path=db_path)
    ctx = _context if _context is not None else build_wo_context(
        wo_id, db_path=db_path,
    )
    matched = evaluate_rule(rule, ctx)
    actions_log: list[dict] = []
    error: Optional[str] = None
    if matched:
        for action in rule.actions:
            try:
                result = execute_action(action, ctx, db_path)
                actions_log.append(result)
            except Exception as e:
                detail = f"{type(e).__name__}: {e}"
                logger.warning(
                    "rule_id=%d wo_id=%s action=%s failed: %s",
                    rule_id, wo_id, action.get("type"), detail,
                )
                actions_log.append({
                    "type": action.get("type"),
                    "ok": False, "error": detail,
                })
                if error is None:
                    error = detail
                # fail-one, continue-rest — keep going
    run_id = _log_run(
        rule_id, wo_id, triggered_event, matched, actions_log,
        error, actor_user_id, db_path,
    )
    return RuleRunResult(
        rule_id=rule_id, rule_name=rule.name,
        work_order_id=wo_id, matched=matched,
        actions_log=actions_log, error=error, run_id=run_id,
    )


def trigger_rules_for_event(
    event: str, wo_id: int,
    actor_user_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> list[RuleRunResult]:
    """Fire all active rules matching ``event`` for WO's shop, in
    priority order. Returns per-rule results.

    ``event='manual'`` rules never fire here — only via
    :func:`fire_rule_for_wo`.
    """
    _validate_event(event)
    if event == "manual":
        raise InvalidEventError(
            "'manual' rules cannot be fired by event trigger; use "
            "fire_rule_for_wo instead"
        )
    ctx = build_wo_context(wo_id, db_path=db_path)
    wo = ctx.get("wo")
    if wo is None:
        return []
    rules = list_rules(
        shop_id=wo["shop_id"], event_trigger=event,
        active_only=True, db_path=db_path,
    )
    results: list[RuleRunResult] = []
    for rule in rules:
        results.append(fire_rule_for_wo(
            rule.id, wo_id,
            actor_user_id=actor_user_id,
            triggered_event=event,
            db_path=db_path, _context=ctx,
        ))
    return results


def list_rule_runs(
    rule_id: Optional[int] = None,
    wo_id: Optional[int] = None,
    shop_id: Optional[int] = None,
    matched_only: bool = False,
    since: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[str] = None,
) -> list[WorkflowRuleRun]:
    query = (
        "SELECT wrr.* FROM workflow_rule_runs wrr "
        "JOIN workflow_rules wr ON wr.id = wrr.rule_id "
        "WHERE 1=1"
    )
    params: list = []
    if rule_id is not None:
        query += " AND wrr.rule_id = ?"
        params.append(rule_id)
    if wo_id is not None:
        query += " AND wrr.work_order_id = ?"
        params.append(wo_id)
    if shop_id is not None:
        query += " AND wr.shop_id = ?"
        params.append(shop_id)
    if matched_only:
        query += " AND wrr.matched = 1"
    if since:
        query += " AND wrr.fired_at >= ?"
        params.append(since)
    query += " ORDER BY wrr.fired_at DESC, wrr.id DESC"
    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(int(limit))
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_run(r) for r in rows]
