"""Automated triage queue — "what to fix first" (Phase 164).

Pure query-synthesis + deterministic-scoring layer over Phase 161
work_orders + Phase 162 issues + Phase 163 AI priority (consumed via
work_orders.priority) + Phase 165 parts availability (soft-guarded
since 165 hasn't shipped yet — `importlib.util.find_spec` returns None
→ treat all parts as ready).

Pure read in :func:`build_triage_queue`. Mutations confined to
:func:`flag_urgent` / :func:`clear_urgent` / :func:`skip_work_order` /
:func:`save_triage_weights` / :func:`reset_triage_weights`. Triage
markers ride on `work_orders.description` via prefix tokens
(``[TRIAGE_URGENT] `` / ``[TRIAGE_SKIP: reason] ``) — no new columns
beyond the per-shop triage_weights JSON added by migration 028.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from motodiag.core.database import get_connection
from motodiag.shop.work_order_repo import (
    list_work_orders, update_work_order, WorkOrderNotFoundError,
)


class ShopTriageError(ValueError):
    """Base error for Phase 164 triage operations."""


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ShopTriageWeights(BaseModel):
    """Per-shop tunable weights for the Phase 164 triage formula.

    Persisted as JSON in shops.triage_weights. NULL column → defaults.
    """
    model_config = ConfigDict(extra="forbid")

    priority_weight: float = Field(default=100.0, ge=0.0)
    wait_weight: float = Field(default=1.0, ge=0.0)
    parts_ready_weight: float = Field(default=10.0, ge=0.0)
    urgent_flag_bonus: float = Field(default=500.0, ge=0.0)
    skip_penalty: float = Field(default=50.0, ge=0.0)


class TriageItem(BaseModel):
    """One ranked work order + its triage-relevant context."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    work_order: dict
    issues: list[dict] = Field(default_factory=list)
    parts_ready: bool = True
    parts_missing_skus: list[str] = Field(default_factory=list)
    wait_hours: float = 0.0
    triage_flag: Optional[str] = None
    triage_skip_reason: Optional[str] = None
    triage_score: float = 0.0
    rank: int = 0  # 1-based


# ---------------------------------------------------------------------------
# Triage marker parser (markers stored in work_orders.description)
# ---------------------------------------------------------------------------


_URGENT_PREFIX = "[TRIAGE_URGENT] "
_SKIP_PREFIX_OPEN = "[TRIAGE_SKIP: "
_SKIP_PREFIX_CLOSE = "] "


def _parse_triage_markers(description: Optional[str]) -> dict:
    """Parse `[TRIAGE_URGENT] ` / `[TRIAGE_SKIP: reason] ` prefixes.

    Returns ``{flag, skip_reason, clean_description}``. Markers MUST
    appear at the very start of the description (parser anchors at ^).
    """
    if not description:
        return {"flag": None, "skip_reason": None, "clean_description": ""}
    flag: Optional[str] = None
    skip_reason: Optional[str] = None
    clean = description
    if clean.startswith(_URGENT_PREFIX):
        flag = "urgent"
        clean = clean[len(_URGENT_PREFIX):]
    if clean.startswith(_SKIP_PREFIX_OPEN):
        end = clean.find(_SKIP_PREFIX_CLOSE)
        if end > len(_SKIP_PREFIX_OPEN):
            skip_reason = clean[len(_SKIP_PREFIX_OPEN):end]
            clean = clean[end + len(_SKIP_PREFIX_CLOSE):]
    return {
        "flag": flag,
        "skip_reason": skip_reason,
        "clean_description": clean,
    }


def _build_marked_description(
    flag: Optional[str], skip_reason: Optional[str], clean: str,
) -> str:
    """Inverse of _parse_triage_markers — rebuilds the description."""
    out = clean or ""
    if skip_reason:
        out = f"{_SKIP_PREFIX_OPEN}{skip_reason}{_SKIP_PREFIX_CLOSE}{out}"
    if flag == "urgent":
        out = f"{_URGENT_PREFIX}{out}"
    return out


# ---------------------------------------------------------------------------
# Phase 165 parts availability (soft-guarded)
# ---------------------------------------------------------------------------


def _parts_available_for(
    wo_id: int,
    assumed_available: bool = True,
    db_path: Optional[str] = None,
) -> tuple[bool, list[str]]:
    """Soft-guard pattern: Phase 165 may not be installed yet.

    Returns ``(parts_ready, missing_skus)``. When the
    ``motodiag.shop.parts_needs`` module isn't on the import path
    (Phase 165 hasn't shipped), returns ``(assumed_available, [])``.
    """
    spec = importlib.util.find_spec("motodiag.shop.parts_needs")
    if spec is None:
        return (assumed_available, [])
    try:
        from motodiag.shop import parts_needs
        # Phase 165 contract: list_parts_for_wo(wo_id, db_path=None)
        lines = parts_needs.list_parts_for_wo(wo_id, db_path=db_path)
    except Exception:
        return (assumed_available, [])
    if not lines:
        return (True, [])
    missing = [
        line.get("part_slug") or str(line.get("part_id", "?"))
        for line in lines
        if line.get("status") not in ("received", "installed")
    ]
    return (len(missing) == 0, missing)


# ---------------------------------------------------------------------------
# Wait-hour computation
# ---------------------------------------------------------------------------


def _compute_wait_hours(
    opened_at: Optional[str], now: Optional[datetime] = None,
) -> float:
    """Hours since opened_at; 0.0 when unknown."""
    if not opened_at:
        return 0.0
    try:
        t = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.0
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    delta = now - t
    return max(0.0, delta.total_seconds() / 3600.0)


# ---------------------------------------------------------------------------
# Triage score formula
# ---------------------------------------------------------------------------


def _compute_score(item: TriageItem, weights: ShopTriageWeights) -> float:
    """Deterministic triage score formula.

    score =
        priority_weight * (1 / max(1, priority))
      + wait_weight * (wait_hours / 24)
      + parts_ready_weight * (1 if parts_ready else 0)
      + urgent_flag_bonus * (1 if triage_flag == 'urgent' else 0)
      - skip_penalty * (1 if triage_skip_reason else 0)
    """
    priority = max(1, int(item.work_order.get("priority", 3) or 3))
    score = weights.priority_weight * (1.0 / priority)
    score += weights.wait_weight * (item.wait_hours / 24.0)
    if item.parts_ready:
        score += weights.parts_ready_weight
    if item.triage_flag == "urgent":
        score += weights.urgent_flag_bonus
    if item.triage_skip_reason is not None:
        score -= weights.skip_penalty
    return score


# ---------------------------------------------------------------------------
# Issue loader (graceful degradation when Phase 162 absent)
# ---------------------------------------------------------------------------


def _load_issues_safe(wo_id: int, db_path: Optional[str] = None) -> list[dict]:
    """Try Phase 162 list_issues; empty on missing import."""
    try:
        from motodiag.shop.issue_repo import list_issues
        return list_issues(work_order_id=wo_id, db_path=db_path)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Per-shop weights persistence
# ---------------------------------------------------------------------------


def load_triage_weights(
    shop_id: int, db_path: Optional[str] = None,
) -> ShopTriageWeights:
    """Load weights for shop_id; return defaults when column is NULL."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT triage_weights FROM shops WHERE id = ?", (shop_id,),
        ).fetchone()
    if row is None or row["triage_weights"] is None:
        return ShopTriageWeights()
    try:
        payload = json.loads(row["triage_weights"])
    except (TypeError, ValueError):
        return ShopTriageWeights()
    return ShopTriageWeights(**payload)


def save_triage_weights(
    shop_id: int, weights: ShopTriageWeights,
    db_path: Optional[str] = None,
) -> bool:
    """Persist weights JSON to shops.triage_weights for shop_id."""
    payload = json.dumps(weights.model_dump())
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE shops SET triage_weights = ?, updated_at = ? WHERE id = ?",
            (payload, datetime.now(timezone.utc).isoformat(), shop_id),
        )
        return cursor.rowcount > 0


def reset_triage_weights(
    shop_id: int, db_path: Optional[str] = None,
) -> bool:
    """Set triage_weights NULL → returns to ShopTriageWeights() defaults."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE shops SET triage_weights = NULL, updated_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), shop_id),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# flag-urgent / skip mutators (write through Phase 161 update_work_order)
# ---------------------------------------------------------------------------


def flag_urgent(
    wo_id: int, db_path: Optional[str] = None,
) -> bool:
    """Force WO to top of triage. Sets priority=1 + adds [TRIAGE_URGENT] prefix.

    Idempotent — calling twice does not double-prefix the description.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT description FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        markers = _parse_triage_markers(row["description"])
    new_desc = _build_marked_description(
        flag="urgent",
        skip_reason=markers["skip_reason"],
        clean=markers["clean_description"],
    )
    update_work_order(
        wo_id, {"description": new_desc, "priority": 1}, db_path=db_path,
    )
    return True


def clear_urgent(wo_id: int, db_path: Optional[str] = None) -> bool:
    """Strip the [TRIAGE_URGENT] prefix; priority NOT auto-restored."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT description FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        markers = _parse_triage_markers(row["description"])
    if markers["flag"] != "urgent":
        return False
    new_desc = _build_marked_description(
        flag=None,
        skip_reason=markers["skip_reason"],
        clean=markers["clean_description"],
    )
    update_work_order(
        wo_id, {"description": new_desc}, db_path=db_path,
    )
    return True


def skip_work_order(
    wo_id: int, reason: str, db_path: Optional[str] = None,
) -> bool:
    """Soft-demote WO via [TRIAGE_SKIP: reason] prefix. Empty reason clears."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT description FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        markers = _parse_triage_markers(row["description"])
    new_skip = reason.strip() if reason and reason.strip() else None
    new_desc = _build_marked_description(
        flag=markers["flag"],
        skip_reason=new_skip,
        clean=markers["clean_description"],
    )
    update_work_order(
        wo_id, {"description": new_desc}, db_path=db_path,
    )
    return True


# ---------------------------------------------------------------------------
# Build triage queue
# ---------------------------------------------------------------------------


def build_triage_queue(
    shop_id: Optional[int] = None,
    assigned_mechanic_user_id: Optional[int] = None,
    include_terminal: bool = False,
    weights: Optional[ShopTriageWeights] = None,
    top: Optional[int] = None,
    assumed_parts_available: bool = True,
    now: Optional[datetime] = None,
    db_path: Optional[str] = None,
) -> list[TriageItem]:
    """Build the ranked triage queue for a shop (or all shops).

    Pure read — no DB mutation. Sort tiebreaker is
    ``(-triage_score, created_at ASC, wo_id ASC)`` — stable + deterministic.
    """
    if weights is None:
        if shop_id is not None:
            weights = load_triage_weights(shop_id, db_path=db_path)
        else:
            weights = ShopTriageWeights()

    rows = list_work_orders(
        shop_id=shop_id,
        assigned_mechanic_user_id=assigned_mechanic_user_id,
        include_terminal=include_terminal,
        limit=0,  # uncapped — caller may pass `top` to truncate
        db_path=db_path,
    )

    items: list[TriageItem] = []
    for wo in rows:
        markers = _parse_triage_markers(wo.get("description"))
        wait_hours = _compute_wait_hours(wo.get("opened_at"), now=now)
        parts_ready, missing_skus = _parts_available_for(
            wo["id"], assumed_available=assumed_parts_available,
            db_path=db_path,
        )
        item = TriageItem(
            work_order=wo,
            issues=_load_issues_safe(wo["id"], db_path=db_path),
            parts_ready=parts_ready,
            parts_missing_skus=missing_skus,
            wait_hours=wait_hours,
            triage_flag=markers["flag"],
            triage_skip_reason=markers["skip_reason"],
        )
        item = item.model_copy(update={
            "triage_score": _compute_score(item, weights),
        })
        items.append(item)

    # Sort: highest score first; tiebreak by created_at ASC then wo_id ASC
    items.sort(
        key=lambda x: (
            -x.triage_score,
            x.work_order.get("created_at") or "",
            int(x.work_order.get("id", 0)),
        )
    )

    # Assign 1-based rank
    items = [
        item.model_copy(update={"rank": i + 1})
        for i, item in enumerate(items)
    ]

    if top is not None and top > 0:
        items = items[:top]

    return items
