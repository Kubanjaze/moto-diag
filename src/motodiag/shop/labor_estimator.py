"""AI labor time estimation (Phase 167).

Composes against Phase 162.5 ``shop/ai_client.py`` — zero direct
``anthropic`` imports (enforced by anti-regression grep test).

Write-back to ``work_orders.estimated_hours`` routes ALWAYS through
Phase 161 :func:`update_work_order` whitelist — NEVER raw SQL.
Verified by :func:`test_labor_estimator_does_not_write_raw_sql`
(grep-test equivalent to Phase 165's cost-recompute audit guarantee).

System prompt seeded from Domain-Researcher pricing brief
(``_research/track_g_pricing_brief.md``):
- Labor-norms baseline table (oil change 0.5h, valve adjust 2-3h,
  brake pad per wheel 1-1.5h, etc.)
- Per-platform adjustments (HD pushrod vs Honda shim-under-bucket)
- Skill tier multipliers (apprentice +25%, journeyman 0%, master -15%)
- Mileage + environment adjustments (>50k +10%, coastal/salt +30-50%)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Callable, Literal, Optional

from motodiag.core.database import get_connection
from motodiag.shop.ai_client import (
    AIResponse, ShopAIClient, ShopAIClientError, extract_json_block,
)
from motodiag.shop.labor_models import (
    LaborEstimate, ReconcileBucket, ReconciliationReport, SkillTier,
)
from motodiag.shop.work_order_repo import (
    TERMINAL_STATUSES as WO_TERMINAL_STATUSES,
    WorkOrderNotFoundError, list_work_orders, require_work_order,
    update_work_order,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LaborEstimatorError(ValueError):
    """Base class for Phase 167 errors."""


class LaborEstimateMathError(LaborEstimatorError):
    """Raised when AI returns math inconsistent with the rubric formula."""


class ReconcileMissingDataError(LaborEstimatorError):
    """Raised when reconcile_with_actual lacks actual_hours or completed_at."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


VALID_SKILL_TIERS: tuple[str, ...] = ("apprentice", "journeyman", "master")

DEFAULT_SKILL_ADJUSTMENTS: dict[str, float] = {
    "apprentice": 0.25,
    "journeyman": 0.0,
    "master": -0.15,
}

MATH_TOLERANCE_HOURS = 0.01
RECONCILE_DELTA_THRESHOLD_PCT = 20.0


# ---------------------------------------------------------------------------
# System prompt (cached via ShopAIClient ephemeral cache)
# ---------------------------------------------------------------------------


LABOR_SYSTEM_PROMPT = """You are a veteran motorcycle shop foreman estimating wrench time. Return JSON only.

LABOR NORMS RUBRIC (journeyman mechanic, well-equipped shop, no seized fasteners):
- Oil + filter change: 0.5h
- Chain + sprocket set: 1.0-1.5h
- Brake pad replacement per wheel: 1.0-1.5h
- Brake fluid flush + bleed (both circuits): 0.75-1.25h
- Coolant flush: 0.75h
- Spark plug replacement (accessible): 0.5h per plug; (buried): +1.0h
- Battery replacement: 0.25h
- Tire R&R + mount + balance: 0.75h per tire + 0.25h per wheel
- Harley valve adjustment (air-cooled V-twin, pushrod): 2.0-3.0h
- Honda CBR / Yamaha R carb sync (4-cyl): 1.5-2.0h
- FI throttle-body sync: 0.75-1.25h
- Fork seal replacement (pair): 2.0-3.0h
- Clutch cable: 0.5-0.75h
- Clutch plate (Japanese wet): 2.0-3.5h; HD dry primary: 1.5h
- Timing chain/tensioner service: 3.0-5.0h
- Cam chain tensioner (Japanese twins): 1.5-2.5h
- Top-end rebuild: 8-14h
- Stator / R/R replacement: 1.0-2.0h
- Fuel pump replacement (in-tank): 1.25-2.0h
- Wheel bearing replacement per wheel: 1.0-1.5h

PER-PLATFORM ADJUSTMENTS:
- HD Twin Cam / M8: pushrod (no shim); valve check 1.5h
- Honda CBR / Yamaha R / Suzuki GSX-R / Kawasaki ZX (I4): shim-under-bucket valve adjust 5.0-6.0h
- Dual-sport (KLR/DR/XR): screw-adjust, 2.0h
- Mid-cruiser (Japanese twin): 3.5h

SKILL TIER ADJUSTMENTS (multiplicative on base_hours):
- apprentice (0-2yr): skill_adjustment = +0.25 (first-time jobs, tool-hunting)
- journeyman (3-8yr): skill_adjustment = 0.0 (baseline)
- master (8+yr): skill_adjustment = -0.15 (knows shortcuts, parallel diagnosis)

MILEAGE / ENVIRONMENT ADJUSTMENTS (additive on skill-adjusted hours):
- > 50,000 mi: mileage_adjustment = 0.10 (rust / seized fasteners risk)
- > 100,000 mi: mileage_adjustment = 0.20
- Coastal / Florida / salt-exposed: add "seized-fastener scenario" alternative_estimate +30-50%

RULES:
- adjusted_hours MUST equal base_hours * (1 + skill_adjustment) * (1 + mileage_adjustment),
  rounded to 2 decimals. Include the math explicitly in the rationale.
- Multi-job WO (e.g. "oil change + brake pads"): SUM the rubric lines; breakdown lists one entry per sub-job.
- Unknown/ambiguous job → confidence ≤ 0.5; explain uncertainty in rationale.
- Return JSON ONLY. No markdown. No prose outside JSON.

OUTPUT SCHEMA (strict):
{
  "base_hours": float,
  "adjusted_hours": float,
  "skill_adjustment": float,
  "mileage_adjustment": float,
  "confidence": float in [0,1],
  "rationale": string,
  "breakdown": [{"step_name": str, "step_hours": float, "tools_needed": [str]}],
  "alternative_estimates": [{"scenario_name": str, "hours": float, "notes": str}],
  "skill_tier": "apprentice"|"journeyman"|"master",
  "environment_notes": string|null
}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_skill_tier(skill_tier: str) -> str:
    if skill_tier not in VALID_SKILL_TIERS:
        raise LaborEstimatorError(
            f"skill_tier must be one of {VALID_SKILL_TIERS} "
            f"(got {skill_tier!r})"
        )
    return skill_tier


def _load_issues_safe(
    wo_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """Phase 162 issues enrichment; graceful degradation on missing table."""
    try:
        from motodiag.shop.issue_repo import list_issues
        return list_issues(work_order_id=wo_id, db_path=db_path)
    except Exception:
        return []


def _build_user_prompt(
    wo: dict, issues: list[dict], skill_tier: str,
    environment_hint: Optional[str],
) -> str:
    bike = " ".join(
        str(b) for b in (
            wo.get("vehicle_year"), wo.get("vehicle_make"),
            wo.get("vehicle_model"),
        ) if b
    ) or "unknown"
    shop_name = wo.get("shop_name") or str(wo.get("shop_id", "?"))
    vehicle_mileage = None
    vehicle_id = wo.get("vehicle_id")
    if vehicle_id is not None:
        try:
            with get_connection() as conn:
                vr = conn.execute(
                    "SELECT mileage FROM vehicles WHERE id = ?",
                    (vehicle_id,),
                ).fetchone()
                if vr is not None:
                    vehicle_mileage = vr["mileage"]
        except Exception:
            vehicle_mileage = None
    mileage_line = (
        f"  mileage: {vehicle_mileage}" if vehicle_mileage is not None
        else "  mileage: unknown"
    )
    if issues:
        issue_block = "\n".join(
            f"{i + 1}. [{iss.get('severity', '?')}] "
            f"{iss.get('title', '?')} — "
            f"{(iss.get('description') or '')[:200]}"
            for i, iss in enumerate(issues)
        )
    else:
        issue_block = "(none)"
    return (
        f"Work Order #{wo.get('id')}\n"
        f"Shop: {shop_name}\n"
        f"Vehicle: {bike}\n{mileage_line}\n"
        f"Skill tier requested: {skill_tier}\n\n"
        f"Title: {wo.get('title', '?')}\n"
        f"Description: {wo.get('description') or '(none)'}\n\n"
        f"Linked issues (Phase 162):\n{issue_block}\n\n"
        f"Environment hint (optional): {environment_hint or '(none)'}\n\n"
        f"Estimate the wrench time. Return JSON only."
    )


def _check_math(est: dict) -> bool:
    """Return True if AI math is consistent within MATH_TOLERANCE_HOURS."""
    base = float(est.get("base_hours", 0))
    skill = float(est.get("skill_adjustment", 0))
    mileage = float(est.get("mileage_adjustment", 0))
    expected = round(base * (1 + skill) * (1 + mileage), 2)
    actual = float(est.get("adjusted_hours", 0))
    return abs(expected - actual) <= MATH_TOLERANCE_HOURS


def _parse_estimate(
    ai_text: str, wo_id: int, skill_tier: str,
) -> dict:
    """Parse AI JSON response into a dict ready for LaborEstimate."""
    try:
        payload = json.loads(extract_json_block(ai_text))
    except Exception as e:
        raise LaborEstimatorError(
            f"failed to parse AI labor JSON: {e}\nraw: {ai_text[:200]!r}"
        ) from e
    payload["wo_id"] = wo_id
    payload.setdefault("skill_tier", skill_tier)
    return payload


def _persist_labor_estimate(
    est: LaborEstimate,
    user_prompt_snapshot: str,
    db_path: Optional[str] = None,
) -> int:
    """Append one row to labor_estimates. Returns row id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO labor_estimates
               (wo_id, skill_tier, base_hours, adjusted_hours,
                skill_adjustment, mileage_adjustment, confidence,
                rationale, breakdown_json, alternatives_json,
                environment_notes, ai_model, tokens_in, tokens_out,
                cost_cents, prompt_cache_hit, user_prompt_snapshot)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                est.wo_id, est.skill_tier, est.base_hours,
                est.adjusted_hours, est.skill_adjustment,
                est.mileage_adjustment, est.confidence, est.rationale,
                json.dumps([s.model_dump() for s in est.breakdown]),
                json.dumps([a.model_dump() for a in est.alternative_estimates]),
                est.environment_notes, est.ai_model, est.tokens_in,
                est.tokens_out, est.cost_cents,
                1 if est.prompt_cache_hit else 0,
                (user_prompt_snapshot or "")[:8000],
            ),
        )
        return int(cursor.lastrowid)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def estimate_labor(
    wo_id: int,
    skill_tier: str = "journeyman",
    model: str = "haiku",
    environment_hint: Optional[str] = None,
    write_back: bool = True,
    db_path: Optional[str] = None,
    client: Optional[ShopAIClient] = None,
    _default_scorer_fn: Optional[Callable] = None,
) -> LaborEstimate:
    """Estimate labor hours for one work order via AI.

    Write-back to ``work_orders.estimated_hours`` ALWAYS routes through
    Phase 161 :func:`update_work_order` — never raw SQL. Grep-test
    enforced.
    """
    _validate_skill_tier(skill_tier)
    wo = require_work_order(wo_id, db_path=db_path)
    if wo["status"] in WO_TERMINAL_STATUSES:
        raise LaborEstimatorError(
            f"work order id={wo_id} is terminal ({wo['status']!r}); cannot estimate"
        )
    issues = _load_issues_safe(wo_id, db_path=db_path)
    user_prompt = _build_user_prompt(wo, issues, skill_tier, environment_hint)

    if _default_scorer_fn is not None:
        payload, ai_resp = _default_scorer_fn(
            wo=wo, issues=issues, skill_tier=skill_tier, model=model,
        )
    else:
        client = client or ShopAIClient(
            model=model, max_tokens=2048, temperature=0.2,
        )
        cache_payload = {
            "wo_id": wo_id, "skill_tier": skill_tier,
            "ai_model": client.model,
            "title": wo.get("title"),
            "description": wo.get("description") or "",
            "vehicle_year": wo.get("vehicle_year"),
            "vehicle_make": wo.get("vehicle_make"),
            "vehicle_model": wo.get("vehicle_model"),
            "issues_count": len(issues),
        }
        ai_resp = client.ask(
            user_prompt=user_prompt, system_prompt=LABOR_SYSTEM_PROMPT,
            cache_kind="labor_estimate", cache_payload=cache_payload,
            db_path=db_path,
        )
        payload = _parse_estimate(ai_resp.text, wo_id, skill_tier)

    # Math consistency check; retry once at temp 0.1 if inconsistent
    if not _check_math(payload):
        if _default_scorer_fn is None and client is not None:
            retry_resp = client.ask(
                user_prompt=user_prompt + (
                    "\n\nYour previous response had inconsistent math. "
                    "Re-check: adjusted_hours MUST equal "
                    "base_hours * (1 + skill_adjustment) * "
                    "(1 + mileage_adjustment)."
                ),
                system_prompt=LABOR_SYSTEM_PROMPT,
                temperature=0.1,
                db_path=db_path,
            )
            payload = _parse_estimate(retry_resp.text, wo_id, skill_tier)
            ai_resp = retry_resp
        if not _check_math(payload):
            raise LaborEstimateMathError(
                f"AI math inconsistent after retry: "
                f"base={payload.get('base_hours')}, "
                f"skill={payload.get('skill_adjustment')}, "
                f"mileage={payload.get('mileage_adjustment')}, "
                f"adjusted={payload.get('adjusted_hours')}"
            )

    payload["wo_id"] = wo_id
    payload["ai_model"] = ai_resp.model
    payload["tokens_in"] = ai_resp.usage.input_tokens
    payload["tokens_out"] = ai_resp.usage.output_tokens
    payload["cost_cents"] = ai_resp.cost_cents
    payload["prompt_cache_hit"] = ai_resp.cache_hit
    payload["generated_at"] = datetime.now(timezone.utc)

    try:
        est = LaborEstimate(**payload)
    except Exception as e:
        raise LaborEstimatorError(
            f"LaborEstimate validation failed: {e}"
        ) from e

    _persist_labor_estimate(est, user_prompt, db_path=db_path)

    # Write-back via Phase 161 update_work_order whitelist — NEVER raw SQL.
    if write_back:
        update_work_order(
            wo_id, {"estimated_hours": float(est.adjusted_hours)},
            db_path=db_path,
        )

    return est


def bulk_estimate_open_wos(
    shop_id: int,
    model: str = "haiku",
    skill_tier: str = "journeyman",
    force: bool = False,
    db_path: Optional[str] = None,
    client: Optional[ShopAIClient] = None,
    _default_scorer_fn: Optional[Callable] = None,
) -> list[LaborEstimate]:
    """Bulk-estimate open/in-progress WOs. Skips WOs with estimated_hours
    already set unless force=True."""
    _validate_skill_tier(skill_tier)
    wos = list_work_orders(
        shop_id=shop_id, status=["open", "in_progress"],
        limit=0, db_path=db_path,
    )
    results: list[LaborEstimate] = []
    for wo in wos:
        if wo.get("estimated_hours") is not None and not force:
            continue
        try:
            est = estimate_labor(
                wo["id"], skill_tier=skill_tier, model=model,
                db_path=db_path, client=client,
                _default_scorer_fn=_default_scorer_fn,
            )
            results.append(est)
        except LaborEstimatorError as e:
            logger.warning(
                "labor estimate skipped for wo_id=%d: %s", wo["id"], e,
            )
    return results


def reconcile_with_actual(
    wo_id: int, db_path: Optional[str] = None,
) -> ReconciliationReport:
    """Compare the most recent labor estimate against the completed WO's
    actual_hours. Pure arithmetic — no AI call.
    """
    wo = require_work_order(wo_id, db_path=db_path)
    if wo["status"] != "completed":
        raise ReconcileMissingDataError(
            f"work order id={wo_id} is not completed (status={wo['status']!r})"
        )
    if wo.get("actual_hours") is None:
        raise ReconcileMissingDataError(
            f"work order id={wo_id} has no actual_hours recorded"
        )
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT adjusted_hours FROM labor_estimates "
            "WHERE wo_id = ? ORDER BY generated_at DESC LIMIT 1",
            (wo_id,),
        ).fetchone()
    if row is None:
        raise ReconcileMissingDataError(
            f"no labor estimate exists for wo_id={wo_id}"
        )
    estimated = float(row["adjusted_hours"])
    actual = float(wo["actual_hours"])
    delta = actual - estimated
    pct: Optional[float] = None
    if estimated > 0:
        pct = (delta / estimated) * 100.0
    bucket: ReconcileBucket = "within"
    if pct is not None:
        if pct < -RECONCILE_DELTA_THRESHOLD_PCT:
            bucket = "over"  # over-estimated (actual < estimated by >20%)
        elif pct > RECONCILE_DELTA_THRESHOLD_PCT:
            bucket = "under"  # under-estimated (actual > estimated by >20%)
    notes = (
        f"estimated {estimated:.2f}h vs actual {actual:.2f}h "
        f"(delta {delta:+.2f}h"
        + (f" / {pct:+.1f}%" if pct is not None else "")
        + f"; {bucket})"
    )
    return ReconciliationReport(
        wo_id=wo_id, estimated_hours=estimated, actual_hours=actual,
        delta_hours=delta, delta_pct=pct, bucket=bucket, notes=notes,
    )


def list_labor_estimates(
    wo_id: Optional[int] = None,
    since: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List labor_estimates rows with optional filters."""
    query = "SELECT * FROM labor_estimates"
    conditions: list[str] = []
    params: list = []
    if wo_id is not None:
        conditions.append("wo_id = ?")
        params.append(wo_id)
    if since:
        conditions.append("generated_at >= ?")
        params.append(since)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY generated_at DESC, id DESC"
    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(int(limit))
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def labor_budget(
    shop_id: Optional[int] = None,
    since: Optional[str] = None,
    db_path: Optional[str] = None,
) -> dict:
    """Aggregate labor-AI spend + cache-hit rate + per-model breakdown."""
    query = (
        "SELECT COUNT(*) AS n, "
        "  COALESCE(SUM(tokens_in), 0) AS tokens_in, "
        "  COALESCE(SUM(tokens_out), 0) AS tokens_out, "
        "  COALESCE(SUM(cost_cents), 0) AS cost_cents, "
        "  COALESCE(SUM(prompt_cache_hit), 0) AS cache_hits "
        "FROM labor_estimates le"
    )
    params: list = []
    conditions: list[str] = []
    if shop_id is not None:
        query += " JOIN work_orders wo ON wo.id = le.wo_id"
        conditions.append("wo.shop_id = ?")
        params.append(shop_id)
    if since:
        conditions.append("le.generated_at >= ?")
        params.append(since)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    with get_connection(db_path) as conn:
        row = conn.execute(query, params).fetchone()
    total_calls = int(row["n"]) if row else 0
    cache_hits = int(row["cache_hits"]) if row else 0
    return {
        "calls": total_calls,
        "tokens_in": int(row["tokens_in"]) if row else 0,
        "tokens_out": int(row["tokens_out"]) if row else 0,
        "cost_cents": int(row["cost_cents"]) if row else 0,
        "cache_hit_count": cache_hits,
        "cache_hit_rate": (
            cache_hits / total_calls if total_calls > 0 else 0.0
        ),
    }
