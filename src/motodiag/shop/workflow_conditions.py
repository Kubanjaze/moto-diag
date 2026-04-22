"""Workflow rule conditions (Phase 173).

Condition dicts look like ``{"type": "priority_lte", "value": 2}``.
Evaluators read a pre-built context dict (WO + issues + parts +
invoice + shop) assembled by :func:`build_wo_context` in
``workflow_rules.py``.

Adding a new condition: define the evaluator, add to ``_REGISTRY``,
extend ``CONDITION_TYPES``, and document the dict shape. No schema
change needed.
"""

from __future__ import annotations

from typing import Callable


CONDITION_TYPES: tuple[str, ...] = (
    "always",
    "priority_gte", "priority_lte", "priority_eq",
    "status_eq", "status_in",
    "severity_eq", "severity_in",
    "category_in",
    "parts_cost_gt_cents", "invoice_total_gt_cents",
    "has_unresolved_issue",
)


class InvalidConditionError(ValueError):
    """Raised when a condition dict is malformed or references an
    unknown type."""


# ---------------------------------------------------------------------------
# Individual evaluators
# ---------------------------------------------------------------------------


def _c_always(cond: dict, ctx: dict) -> bool:
    return True


def _c_priority_gte(cond: dict, ctx: dict) -> bool:
    return int((ctx.get("wo") or {}).get("priority") or 0) >= int(cond["value"])


def _c_priority_lte(cond: dict, ctx: dict) -> bool:
    return int((ctx.get("wo") or {}).get("priority") or 0) <= int(cond["value"])


def _c_priority_eq(cond: dict, ctx: dict) -> bool:
    return int((ctx.get("wo") or {}).get("priority") or 0) == int(cond["value"])


def _c_status_eq(cond: dict, ctx: dict) -> bool:
    return (ctx.get("wo") or {}).get("status") == cond["value"]


def _c_status_in(cond: dict, ctx: dict) -> bool:
    values = cond.get("values") or []
    return (ctx.get("wo") or {}).get("status") in values


def _c_severity_eq(cond: dict, ctx: dict) -> bool:
    target = cond["value"]
    for issue in ctx.get("issues") or []:
        if issue.get("severity") == target and issue.get("status") == "open":
            return True
    return False


def _c_severity_in(cond: dict, ctx: dict) -> bool:
    targets = set(cond.get("values") or [])
    for issue in ctx.get("issues") or []:
        if issue.get("severity") in targets and issue.get("status") == "open":
            return True
    return False


def _c_category_in(cond: dict, ctx: dict) -> bool:
    targets = set(cond.get("values") or [])
    for issue in ctx.get("issues") or []:
        if issue.get("category") in targets and issue.get("status") == "open":
            return True
    return False


def _c_parts_cost_gt_cents(cond: dict, ctx: dict) -> bool:
    threshold = int(cond["value"])
    total = 0
    for p in ctx.get("parts") or []:
        qty = int(p.get("quantity") or 0)
        unit = int(
            p.get("unit_cost_cents_override")
            or p.get("typical_cost_cents")
            or 0
        )
        total += qty * unit
    return total > threshold


def _c_invoice_total_gt_cents(cond: dict, ctx: dict) -> bool:
    inv = ctx.get("invoice") or {}
    # Phase 169 stores invoice.total as dollar float; convert to cents.
    total_cents = int(round(float(inv.get("total") or 0.0) * 100))
    return total_cents > int(cond["value"])


def _c_has_unresolved_issue(cond: dict, ctx: dict) -> bool:
    for issue in ctx.get("issues") or []:
        if issue.get("status") == "open":
            return True
    return False


_REGISTRY: dict[str, Callable[[dict, dict], bool]] = {
    "always": _c_always,
    "priority_gte": _c_priority_gte,
    "priority_lte": _c_priority_lte,
    "priority_eq": _c_priority_eq,
    "status_eq": _c_status_eq,
    "status_in": _c_status_in,
    "severity_eq": _c_severity_eq,
    "severity_in": _c_severity_in,
    "category_in": _c_category_in,
    "parts_cost_gt_cents": _c_parts_cost_gt_cents,
    "invoice_total_gt_cents": _c_invoice_total_gt_cents,
    "has_unresolved_issue": _c_has_unresolved_issue,
}


# ---------------------------------------------------------------------------
# Validation + dispatch
# ---------------------------------------------------------------------------


def validate_condition(cond: dict) -> None:
    """Raises :class:`InvalidConditionError` on malformed input."""
    if not isinstance(cond, dict):
        raise InvalidConditionError(
            f"condition must be a dict, got {type(cond).__name__}"
        )
    ctype = cond.get("type")
    if ctype not in CONDITION_TYPES:
        raise InvalidConditionError(
            f"unknown condition type {ctype!r}; expected one of "
            f"{CONDITION_TYPES}"
        )
    # Lightweight shape checks for the common types.
    if ctype in {
        "priority_gte", "priority_lte", "priority_eq",
        "parts_cost_gt_cents", "invoice_total_gt_cents",
    }:
        if "value" not in cond:
            raise InvalidConditionError(
                f"condition type {ctype!r} requires 'value' field"
            )
    if ctype in {"status_in", "severity_in", "category_in"}:
        if "values" not in cond or not isinstance(cond["values"], list):
            raise InvalidConditionError(
                f"condition type {ctype!r} requires list 'values' field"
            )


def validate_conditions(conditions: list[dict]) -> None:
    if not isinstance(conditions, list):
        raise InvalidConditionError("conditions must be a list")
    for c in conditions:
        validate_condition(c)


def evaluate_condition(cond: dict, ctx: dict) -> bool:
    """Dispatch + evaluate. Assumes cond already validated."""
    fn = _REGISTRY[cond["type"]]
    return bool(fn(cond, ctx))


def evaluate_conditions(conditions: list[dict], ctx: dict) -> bool:
    """AND-compose all conditions. Empty list → True (always-match)."""
    return all(evaluate_condition(c, ctx) for c in conditions)
