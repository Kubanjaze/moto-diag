"""Fleet-level analytics — rolls up per-bike predictions, wear, and sessions.

Phase 150. The only dynamic consumer of :mod:`motodiag.advanced.fleet_repo`
at ship time. Per-bike it calls Phase 148 :func:`predict_failures`, counts
open :class:`diagnostic_sessions`, and (when Phase 149 lands) averages
``wear_percent`` across the fleet.

Phase 149 soft-guard
--------------------

Phase 150 ships *before* Phase 149. The wear integration is built now so
that when 149's ``motodiag.advanced.wear`` module lands, it lights up
automatically without code churn:

1. At module load, :func:`importlib.util.find_spec` probes for the
   ``motodiag.advanced.wear`` package. The boolean result is cached in
   :data:`_HAS_WEAR`.
2. If True, the per-bike loop lazy-imports ``analyze_wear`` and
   populates ``wear_percent``. If False, ``wear_percent`` stays
   ``None`` and the CLI renderer prints a dim em-dash for the cell.

Tests monkeypatch :data:`_HAS_WEAR` to exercise both branches without
requiring Phase 149 to exist yet.

Return shape
------------

:func:`fleet_status_summary` returns a dict with four top-level keys:

.. code-block:: python

    {
      "fleet": {"id": 1, "name": "Summer rentals",
                "description": ..., "bike_count": 4},
      "bikes": [
        {"vehicle_id": 12, "make": "Harley-Davidson", "model": ...,
         "year": 2010, "role": "rental", "mileage": None,
         "prediction_count": 3, "critical_prediction_count": 1,
         "top_prediction": "Stator failure",
         "wear_percent": None, "open_sessions": 0},
        ...
      ],
      "totals": {"total_predictions": 7, "critical_predictions": 2,
                 "bikes_with_open_sessions": 1,
                 "bikes_with_critical": 2,
                 "average_wear_percent": None},
      "horizon_days": 180,
      "min_severity": None,
      "phase149_available": False,
    }
"""

from __future__ import annotations

import importlib.util
from typing import Any, Optional

from motodiag.advanced.fleet_repo import (
    FleetNotFoundError,
    get_fleet,
    list_bikes_in_fleet,
)
from motodiag.advanced.predictor import SEVERITY_WEIGHT, predict_failures
from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Phase 149 soft-guard
# ---------------------------------------------------------------------------


# Probed at module load so the per-call cost is zero. Tests monkeypatch
# this flag to exercise the True branch without requiring 149 to exist.
_HAS_WEAR: bool = (
    importlib.util.find_spec("motodiag.advanced.wear") is not None
)


def _wear_percent_for_vehicle(
    vehicle_row: dict,
    db_path: Optional[str] = None,
) -> Optional[float]:
    """Compute wear_percent for a vehicle when Phase 149 is present.

    Lazy-imports :func:`motodiag.advanced.wear.analyze_wear` only when
    the soft-guard passes. When 149 is absent (typical today), returns
    ``None`` so the cell renders as a dim em-dash.

    Phase 149's ``analyze_wear`` signature ranks wear patterns given a
    vehicle + symptoms list; Phase 150 doesn't carry per-bike symptoms
    in the fleet context, so the integration is intentionally
    conservative: we pass an empty symptoms list and only surface a
    numeric ``wear_percent`` if the integrator has explicitly added
    that field (future Phase 155+ shop-floor meters). Today the call
    returns no matches and we get ``None`` — which the CLI renders as
    a dim em-dash. Tests monkeypatch both :data:`_HAS_WEAR` and this
    helper to exercise the True branch deterministically.

    Any exception from :func:`analyze_wear` is swallowed and returns
    ``None`` — a best-effort analytic should never fail the whole
    status summary.
    """
    if not _HAS_WEAR:
        return None
    try:
        from motodiag.advanced.wear import analyze_wear  # type: ignore
    except Exception:
        return None
    try:
        result = analyze_wear(vehicle_row, symptoms=[], db_path=db_path)
    except Exception:
        return None
    if result is None:
        return None
    # Phase 149 contract (per roadmap draft): either a dict with a
    # `wear_percent` key, or a number, or a list of matches with
    # confidence_score. Be tolerant of multiple shapes so 149's final
    # API doesn't break 150 tests.
    if isinstance(result, (int, float)):
        return float(result)
    if isinstance(result, dict):
        val = result.get("wear_percent")
        if isinstance(val, (int, float)):
            return float(val)
    if isinstance(result, list) and result:
        first = result[0]
        if isinstance(first, (int, float)):
            return float(first)
        if isinstance(first, dict):
            val = first.get("wear_percent") or first.get("confidence_score")
            if isinstance(val, (int, float)):
                return float(val) * 100.0 if val <= 1.0 else float(val)
        # Pydantic model with confidence_score attribute
        score = getattr(first, "wear_percent", None)
        if isinstance(score, (int, float)):
            return float(score)
    return None


def _count_open_sessions(
    vehicle_id: int,
    db_path: Optional[str] = None,
) -> int:
    """Count open diagnostic_sessions for a vehicle.

    Status `'open'` is the Phase 80+ convention; closed sessions have
    either `'closed'` or `'resolved'` per later tracks. We only count
    `'open'` so the mechanic sees "bikes with work outstanding".
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM diagnostic_sessions "
            "WHERE vehicle_id = ? AND status = 'open'",
            (vehicle_id,),
        ).fetchone()
    return int(row[0]) if row else 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fleet_status_summary(
    fleet_id: int,
    horizon_days: int = 180,
    min_severity: Optional[str] = None,
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """Roll up per-bike analytics for every bike in a fleet.

    Parameters
    ----------
    fleet_id : int
        Target fleet. Raises :class:`FleetNotFoundError` on miss.
    horizon_days : int, optional
        Passed through to :func:`predict_failures`. Defaults to 180
        days (Phase 148 convention — one service interval).
    min_severity : str, optional
        Passed through to :func:`predict_failures`.
    db_path : str, optional
        Override for tests.

    Returns
    -------
    dict
        See module docstring for the exact shape.
    """
    fleet_row = get_fleet(fleet_id, db_path=db_path)
    if fleet_row is None:
        raise FleetNotFoundError(f"fleet not found: id={fleet_id}")

    bikes = list_bikes_in_fleet(fleet_id, db_path=db_path)

    bike_summaries: list[dict[str, Any]] = []
    total_predictions = 0
    critical_predictions = 0
    bikes_with_open_sessions = 0
    bikes_with_critical = 0
    wear_values: list[float] = []

    critical_weight = SEVERITY_WEIGHT.get("critical", 4)

    for bike in bikes:
        vehicle_dict = {
            "make": bike.get("make"),
            "model": bike.get("model"),
            "year": bike.get("year"),
            # Phase 148 convention: `mileage` is optional. vehicles
            # table doesn't carry mileage today (Phase 149 adds it),
            # so we just read whatever is present and let predictor
            # fall back to age-only scoring when absent.
            "mileage": bike.get("mileage"),
        }
        try:
            predictions = predict_failures(
                vehicle_dict,
                horizon_days=horizon_days,
                min_severity=min_severity,
                db_path=db_path,
            )
        except Exception:
            predictions = []

        pred_count = len(predictions)
        crit_count = sum(
            1 for p in predictions
            if SEVERITY_WEIGHT.get((p.severity or "").lower(), 0)
            >= critical_weight
        )
        top_title = predictions[0].issue_title if predictions else None

        open_sessions = _count_open_sessions(
            int(bike["id"]), db_path=db_path,
        )

        wear_pct = _wear_percent_for_vehicle(
            dict(bike), db_path=db_path,
        )
        if wear_pct is not None:
            wear_values.append(wear_pct)

        total_predictions += pred_count
        critical_predictions += crit_count
        if open_sessions > 0:
            bikes_with_open_sessions += 1
        if crit_count > 0:
            bikes_with_critical += 1

        bike_summaries.append({
            "vehicle_id": int(bike["id"]),
            "make": bike.get("make"),
            "model": bike.get("model"),
            "year": bike.get("year"),
            "role": bike.get("role"),
            "mileage": bike.get("mileage"),
            "prediction_count": pred_count,
            "critical_prediction_count": crit_count,
            "top_prediction": top_title,
            "wear_percent": wear_pct,
            "open_sessions": open_sessions,
        })

    average_wear_percent: Optional[float] = None
    if wear_values:
        average_wear_percent = round(
            sum(wear_values) / len(wear_values), 2,
        )

    return {
        "fleet": {
            "id": int(fleet_row["id"]),
            "name": fleet_row.get("name"),
            "description": fleet_row.get("description"),
            "bike_count": len(bikes),
        },
        "bikes": bike_summaries,
        "totals": {
            "total_predictions": total_predictions,
            "critical_predictions": critical_predictions,
            "bikes_with_open_sessions": bikes_with_open_sessions,
            "bikes_with_critical": bikes_with_critical,
            "average_wear_percent": average_wear_percent,
        },
        "horizon_days": horizon_days,
        "min_severity": min_severity,
        "phase149_available": bool(_HAS_WEAR),
    }
