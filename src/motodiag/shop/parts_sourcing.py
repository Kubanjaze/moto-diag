"""AI parts sourcing + cost optimization (Phase 166).

Composes against Phase 162.5 ``shop/ai_client.py`` substrate — zero
direct ``anthropic`` imports (enforced by anti-regression grep test).
Reads Phase 153 parts catalog (`parts` + `parts_xref`) + Phase 165
parts requisitions (`parts_requisitions` + `parts_requisition_items`).
Persists every recommendation to migration-030 `sourcing_recommendations`
table for Phase 169 invoicing + Phase 171 analytics.

System prompt seeded from Domain-Researcher pricing brief
(`docs/phases/in_progress/_research/track_g_pricing_brief.md`):
- Decision tree (safety-critical path-of-force → OEM only;
  consumables → aftermarket first; etc.)
- 6-tier vendor taxonomy (T1 OEM dealer → T6 AliExpress-avoid)
- Concrete examples (Ricks Motorsports stators > OEM on 80s-00s
  Japanese; EBC HH > OEM on most sport bikes; etc.)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from motodiag.advanced.parts_repo import get_part as get_part_by_slug
from motodiag.core.database import get_connection
from motodiag.shop.ai_client import (
    AIResponse, ShopAIClient, ShopAIClientError, extract_json_block,
)
from motodiag.shop.sourcing_models import (
    SourcingRecommendation, TierPreference, VendorSuggestion,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PartNotFoundError(ValueError):
    """Raised when part_id does not resolve in the Phase 153 catalog."""


class InvalidTierPreferenceError(ValueError):
    """Raised when tier_preference is not in the allowed set."""


class SourcingParseError(ValueError):
    """Wraps JSON-parse / Pydantic-validation failures from the AI response."""


class BatchTimeoutError(ValueError):
    """Raised when optimize_requisition exceeds wait_seconds."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


VALID_TIER_PREFERENCES: tuple[str, ...] = (
    "oem", "aftermarket", "used", "balanced",
)


# ---------------------------------------------------------------------------
# System prompt (cached via shop.ai_client.ShopAIClient ephemeral cache)
# ---------------------------------------------------------------------------


SOURCING_SYSTEM_PROMPT = """You are a motorcycle parts sourcing assistant for a working shop.

Pick the best source tier for a part and justify it in 2-4 sentences a mechanic would actually read.

DECISION TREE
- Safety-critical path-of-force (brake hydraulics, steering bearings, wheel bearings, control cables, fuel lines, throttle cables, hydraulic clutch lines):
    OEM or tier-1 aftermarket (EBC/Galfer/HEL/Goodridge) ONLY — never used, never AliExpress.
- Safety-adjacent friction (brake pads, brake rotors, tires, chain+sprockets):
    Reputable aftermarket EQUAL or BETTER than OEM on most applications.
    EBC HH > OEM on most sport bikes. Vesrah RJL > OEM on sport-touring.
    DID 520VX3 / EK ZVX3 > stock OEM chains.
- Engine internals (pistons/rings/valves/cams/bearings):
    Bike >= 2005 with OEM in production -> OEM.
    Bike 1990-2004 or OEM discontinued -> Wiseco/JE/Wossner pistons, Kibblewhite valves.
    Pre-1990 Japanese -> aftermarket often ONLY path.
- Electrical charging system (stator, regulator/rectifier, CDI, ignition coils):
    AFTERMARKET WINS on older Japanese bikes — counter-intuitive but standard mechanic knowledge.
    Ricks Motorsports MOSFET R/R > OEM shunt R/R on 80s-00s Honda/Yamaha/Kawasaki.
    Ricks stators run cooler than OEM on CBR/VFR/FZR.
- Consumables (oil filter, air filter, spark plugs, levers, mirrors, grips):
    Quality aftermarket always fine (K&N, HiFlo, NGK, Denso, Pro Taper).
    OEM oil filter is waste on 99% of applications.
- Body/cosmetic (fairings, tank, seat, fender, mirrors):
    Insurance/color-match -> OEM.
    Budget customer -> used-OEM (Boneyard / eBay Motors).
- Discontinued OEM:
    Used-OEM (eBay/Boneyard/MotoProz/CMSNL) -> aftermarket reproduction -> last resort China-direct.

VENDOR TIERS (rank cheapest within acceptable availability):
T1: OEM dealer (HD, Honda Powerhouse, Yamaha/Kaw/Suz authorized) — same-day to 3 days, full MSRP.
T2: OEM wholesale online (Partzilla, BikeBandit, CheapCycleParts, Tucker, Parts Unlimited, Drag Specialties, WPS) — 20-35% off MSRP, 2-5 days. **DEFAULT.**
T3: Aftermarket brand direct/reseller (EBC, Galfer, Vesrah, K&N, HiFlo, Ricks Motorsports, Wiseco, JE, Barnett, DID, EK, Pro Taper, Renthal, Shindengen, ElectroSport, Dynojet, S&S, Andrews, Screamin' Eagle) — 15-50% off equivalent OEM, 2-7 days.
T4: Online mega-retailers (RevZilla, J&P Cycles, Dennis Kirk, ChapMoto, MotoSport) — mixed orders, often next-day.
T5: Used-OEM (eBay Motors, Boneyard Cycle Parts, MotoProz, CMSNL, Facebook Marketplace, salvage) — 40-80% off new, variable lead.
T6 (avoid for safety-critical): AliExpress, Temu, generic Amazon — cosmetic-only, never brakes/tires/bearings/fasteners/charging.

DO NOT INVENT VENDOR URLs. If unsure, return null.

OUTPUT JSON (strict; no prose, no markdown fences):
{
  "source_tier": "oem"|"aftermarket"|"used"|"superseded",
  "confidence": 0.0-1.0,
  "rationale": "2-4 sentences explaining tier pick",
  "estimated_cost_cents": int >= 0 (unit_cost * quantity),
  "risk_notes": string | null,
  "alternative_parts": [int parts.id],
  "vendor_suggestions": [
    {"name": str, "url": str | null, "rough_price_cents": int >= 0,
     "availability": "in_stock"|"3-5_days"|"backorder"|"discontinued",
     "notes": str | null}
  ]
}

If input incomplete (no vehicle, no xref data), confidence <= 0.6 and explain in rationale.
Never refuse — always return best-effort."""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_tier(tier_preference: str) -> str:
    if tier_preference not in VALID_TIER_PREFERENCES:
        raise InvalidTierPreferenceError(
            f"tier_preference must be one of {VALID_TIER_PREFERENCES} "
            f"(got {tier_preference!r})"
        )
    return tier_preference


def _require_part(part_id: int, db_path: Optional[str] = None) -> dict:
    """Load Phase 153 parts row by id; raise PartNotFoundError on miss."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM parts WHERE id = ?", (part_id,),
        ).fetchone()
    if row is None:
        raise PartNotFoundError(f"part not found in catalog: id={part_id}")
    return dict(row)


def _load_vehicle(
    vehicle_id: Optional[int], db_path: Optional[str] = None,
) -> Optional[dict]:
    if vehicle_id is None:
        return None
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, make, model, year, mileage, engine_type "
            "FROM vehicles WHERE id = ?", (vehicle_id,),
        ).fetchone()
    return dict(row) if row else None


def _load_xrefs(
    part_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """Load up to 10 cross-reference rows ranked by equivalence DESC."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT pxref.equivalence_rating, pxref.notes,
                      p.id AS aftermarket_part_id, p.slug AS slug,
                      p.brand AS brand,
                      p.oem_part_number AS oem_part_number,
                      p.typical_cost_cents AS typical_cost_cents
               FROM parts_xref pxref
               JOIN parts p ON p.id = pxref.aftermarket_part_id
               WHERE pxref.oem_part_id = ?
               ORDER BY pxref.equivalence_rating DESC, p.id ASC
               LIMIT 10""",
            (part_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def _build_user_prompt(
    part: dict, quantity: int, vehicle: Optional[dict],
    xrefs: list[dict], tier_preference: str,
    mechanic_notes: Optional[str] = None,
) -> str:
    aftermarket_cost = (
        xrefs[0]["typical_cost_cents"] if xrefs else None
    )
    parts_block = (
        f"PART (from catalog)\n"
        f"  part_id: {part['id']}\n"
        f"  slug: {part.get('slug', '?')}\n"
        f"  oem_part_number: {part.get('oem_part_number', '?')}\n"
        f"  brand: {part.get('brand', '?')}\n"
        f"  description: {part.get('description', '?')}\n"
        f"  category: {part.get('category', '?')}\n"
        f"  make: {part.get('make', '?')}\n"
        f"  model_pattern: {part.get('model_pattern', '?')}\n"
        f"  oem_typical_cost_cents: {part.get('typical_cost_cents', '?')}\n"
        f"  aftermarket_typical_cost_cents: "
        f"{aftermarket_cost if aftermarket_cost else '(none on file)'}\n"
        f"  quantity_needed: {quantity}\n"
    )
    if vehicle:
        vehicle_block = (
            f"\nVEHICLE\n"
            f"  make: {vehicle.get('make', '?')}\n"
            f"  model: {vehicle.get('model', '?')}\n"
            f"  year: {vehicle.get('year', '?')}\n"
            f"  mileage: {vehicle.get('mileage') or 'unknown'}\n"
            f"  engine_type: {vehicle.get('engine_type', '?')}\n"
        )
    else:
        vehicle_block = ""
    if xrefs:
        xref_lines = "\n".join(
            f"  [{xr['aftermarket_part_id']}] {xr.get('brand', '?')} "
            f"{xr.get('oem_part_number') or xr.get('slug', '?')} — "
            f"equivalence {xr['equivalence_rating']}/5 — "
            f"{xr.get('typical_cost_cents', '?')}¢ "
            f"notes: {xr.get('notes') or '—'}"
            for xr in xrefs
        )
        xref_block = (
            f"\nCROSS-REFERENCE OPTIONS (from parts_xref; up to 10, ranked)\n"
            f"{xref_lines}\n"
        )
    else:
        xref_block = "\nCROSS-REFERENCE OPTIONS\n  (none on file)\n"
    notes_block = (
        f"\nMECHANIC PREFERENCE\n"
        f"  tier_preference: {tier_preference}\n"
        f"  notes: {mechanic_notes or '—'}\n"
    )
    return (
        parts_block + vehicle_block + xref_block + notes_block
        + "\nReturn the JSON object described in the system prompt. Nothing else."
    )


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_recommendation(
    ai_text: str, part_id: int, quantity: int,
) -> dict:
    """Parse AI JSON response into a dict ready for SourcingRecommendation."""
    try:
        payload = json.loads(extract_json_block(ai_text))
    except Exception as e:
        raise SourcingParseError(
            f"failed to parse AI sourcing JSON: {e}\nraw: {ai_text[:200]!r}"
        ) from e
    payload["part_id"] = part_id
    payload["quantity"] = quantity
    # Coerce alternative_parts entries to int + drop garbage
    alts = payload.get("alternative_parts") or []
    cleaned: list[int] = []
    for item in alts:
        try:
            n = int(item)
            if n > 0:
                cleaned.append(n)
        except (TypeError, ValueError):
            continue
    payload["alternative_parts"] = cleaned
    return payload


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _persist_recommendation(
    rec: SourcingRecommendation,
    vehicle_id: Optional[int],
    requisition_id: Optional[int],
    requisition_line_id: Optional[int],
    tier_preference: str,
    db_path: Optional[str] = None,
) -> int:
    """Append one row to sourcing_recommendations. Returns row id."""
    payload = json.dumps(rec.model_dump(mode="json"), default=str)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO sourcing_recommendations
               (part_id, vehicle_id, requisition_id, requisition_line_id,
                quantity, tier_preference, source_tier, confidence,
                estimated_cost_cents, recommendation_json,
                ai_model, tokens_in, tokens_out, cache_hit, cost_cents,
                batch_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rec.part_id, vehicle_id, requisition_id,
                requisition_line_id, rec.quantity, tier_preference,
                rec.source_tier, rec.confidence,
                rec.estimated_cost_cents, payload, rec.ai_model,
                rec.tokens_in, rec.tokens_out,
                1 if rec.cache_hit else 0,
                rec.cost_cents, rec.batch_id,
            ),
        )
        return int(cursor.lastrowid)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def recommend_source(
    part_id: int,
    quantity: int = 1,
    vehicle_id: Optional[int] = None,
    tier_preference: str = "balanced",
    mechanic_notes: Optional[str] = None,
    model: str = "haiku",
    use_cache: bool = True,
    db_path: Optional[str] = None,
    _default_scorer_fn: Optional[Callable] = None,
) -> SourcingRecommendation:
    """Synchronous single-part sourcing recommendation.

    Persists every result to sourcing_recommendations (cache_hit=1 rows
    persist alongside cache_miss=0 rows so budget reports separate paid
    impressions from free).

    Parameters
    ----------
    _default_scorer_fn : test injection seam — function (part: dict,
        vehicle: Optional[dict], xrefs: list[dict], quantity: int,
        tier_preference: str, model: str) -> tuple[dict, AIResponse]
    """
    if quantity is None or int(quantity) <= 0:
        raise ValueError(f"quantity must be > 0 (got {quantity!r})")
    _validate_tier(tier_preference)
    part = _require_part(part_id, db_path=db_path)
    vehicle = _load_vehicle(vehicle_id, db_path=db_path)
    xrefs = _load_xrefs(part_id, db_path=db_path)

    if _default_scorer_fn is not None:
        payload_dict, ai_resp = _default_scorer_fn(
            part=part, vehicle=vehicle, xrefs=xrefs,
            quantity=quantity, tier_preference=tier_preference,
            model=model,
        )
    else:
        client = ShopAIClient(model=model, max_tokens=1024, temperature=0.2)
        cache_payload = {
            "part_id": part_id, "quantity": quantity,
            "vehicle_id": vehicle_id,
            "tier_preference": tier_preference,
            "mechanic_notes": mechanic_notes or "",
            "ai_model": client.model,
        }
        ai_resp = client.ask(
            user_prompt=_build_user_prompt(
                part, quantity, vehicle, xrefs,
                tier_preference, mechanic_notes,
            ),
            system_prompt=SOURCING_SYSTEM_PROMPT,
            cache_kind="sourcing" if use_cache else None,
            cache_payload=cache_payload if use_cache else None,
            db_path=db_path,
        )
        payload_dict = _parse_recommendation(ai_resp.text, part_id, quantity)

    payload_dict["part_id"] = part_id
    payload_dict["quantity"] = quantity
    payload_dict["ai_model"] = ai_resp.model
    payload_dict["tokens_in"] = ai_resp.usage.input_tokens
    payload_dict["tokens_out"] = ai_resp.usage.output_tokens
    payload_dict["cost_cents"] = ai_resp.cost_cents
    payload_dict["cache_hit"] = ai_resp.cache_hit
    payload_dict["generated_at"] = datetime.now(timezone.utc)

    try:
        rec = SourcingRecommendation(**payload_dict)
    except Exception as e:
        raise SourcingParseError(
            f"SourcingRecommendation validation failed: {e}"
        ) from e
    _persist_recommendation(
        rec, vehicle_id=vehicle_id,
        requisition_id=None, requisition_line_id=None,
        tier_preference=tier_preference, db_path=db_path,
    )
    return rec


def get_recommendation(
    rec_id: int, db_path: Optional[str] = None,
) -> Optional[dict]:
    """Load one persisted sourcing_recommendations row."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM sourcing_recommendations WHERE id = ?", (rec_id,),
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        try:
            d["recommendation"] = json.loads(d.get("recommendation_json") or "{}")
        except Exception:
            d["recommendation"] = {}
        return d


def sourcing_budget(
    since: Optional[str] = None, db_path: Optional[str] = None,
) -> dict:
    """Aggregate sourcing AI spend + tier distribution + cache-hit rate."""
    base_query = "FROM sourcing_recommendations"
    params: list = []
    if since:
        base_query += " WHERE generated_at >= ?"
        params.append(since)
    with get_connection(db_path) as conn:
        head = conn.execute(
            f"SELECT COUNT(*) AS n, "
            f"  COALESCE(SUM(tokens_in), 0) AS tokens_in, "
            f"  COALESCE(SUM(tokens_out), 0) AS tokens_out, "
            f"  COALESCE(SUM(cost_cents), 0) AS cost_cents, "
            f"  COALESCE(SUM(cache_hit), 0) AS cache_hits "
            f"{base_query}",
            params,
        ).fetchone()
        tier_rows = conn.execute(
            f"SELECT source_tier, COUNT(*) AS n {base_query} "
            f"GROUP BY source_tier",
            params,
        ).fetchall()
    cache_hits = int(head["cache_hits"]) if head else 0
    total_calls = int(head["n"]) if head else 0
    return {
        "calls": total_calls,
        "tokens_in": int(head["tokens_in"]) if head else 0,
        "tokens_out": int(head["tokens_out"]) if head else 0,
        "cost_cents": int(head["cost_cents"]) if head else 0,
        "cache_hit_count": cache_hits,
        "cache_hit_rate": (
            cache_hits / total_calls if total_calls > 0 else 0.0
        ),
        "tier_distribution": {
            r["source_tier"]: int(r["n"]) for r in tier_rows
        },
    }
