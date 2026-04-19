"""Phase 158 — Sensor degradation (drift) tracking.

Track slow-onset sensor drift across recordings of the same bike.
Fits a linear trend line (stdlib mean-of-products regression) per PID
across :class:`~motodiag.hardware.recorder.RecordingManager`
persistence written by Phase 142. Flags any PID whose signed drift per
30 days exceeds a user-chosen threshold (default ±5%).

Why this matters
----------------

Slow sensor aging looks "fine" on any single recording — an O2 sensor
drifting 6% richer per month will still read plausibly on a one-day
scan. It only becomes visible when you stack four or five recordings
over a quarter and notice the mean creeping in one direction. This
module does that stacking in SQL and hands the mechanic a three-bucket
verdict (stable / drifting-slow / drifting-fast) and an optional ASCII
sparkline or wide-format CSV for cross-session analysis.

Scope + non-goals
-----------------

- **No AI, no migration, no tokens.** Pure SQL on Phase 142
  ``sensor_samples`` + ``sensor_recordings`` + stdlib math.
- **No new tables.** Reads existing ``sensor_samples.value`` and
  ``sensor_samples.captured_at`` directly.
- **Sparse SQLite summary is OK** for the cross-recording trend.
  Spilled JSONL is only surfaced when
  :func:`compute_trend` is passed a single-recording filter (handled
  at the CLI layer via :class:`RecordingManager.load_recording`).

Public API
----------

- :class:`DriftBucket` — three-band enum surfaced in CLI + predictor.
- :class:`DriftResult` — frozen Pydantic row per PID.
- :func:`compute_trend` — regression for one ``(vehicle_id, pid_hex)``.
- :func:`detect_drifting_pids` — list of drifting results for a bike,
  sorted by urgency.
- :func:`summary_for_bike` — three-bucket dict, all keys always
  present.
"""

from __future__ import annotations

import csv
from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Optional

from pydantic import BaseModel, ConfigDict, Field

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Unicode 1/8 block sparkline palette (copied from Phase 143 dashboard)
# ---------------------------------------------------------------------------
#
# Eight vertical "block" glyphs at increasing heights. The
# :func:`_render_sparkline` helper maps normalized values onto this
# palette. A dedicated space glyph represents empty bins (no samples
# for that time slot).
_SPARK_CHARS: tuple[str, ...] = (
    "\u2581",  # ▁
    "\u2582",  # ▂
    "\u2583",  # ▃
    "\u2584",  # ▄
    "\u2585",  # ▅
    "\u2586",  # ▆
    "\u2587",  # ▇
    "\u2588",  # █
)
_SPARK_EMPTY: str = " "


# ---------------------------------------------------------------------------
# DriftBucket + DriftResult
# ---------------------------------------------------------------------------


class DriftBucket(str, Enum):
    """Three-band classification of per-PID drift magnitude.

    Applied via :func:`_classify_bucket` to
    ``abs(drift_pct_per_30_days)``:

    - :attr:`STABLE` — within ±threshold; sensor is behaving normally.
    - :attr:`DRIFTING_SLOW` — in ``[threshold, 2 × threshold)``; watch
      it, but no immediate action.
    - :attr:`DRIFTING_FAST` — ``≥ 2 × threshold``; mechanic action
      warranted. Phase 148 predictor surfaces these as a confidence
      bonus when the PID name overlaps an issue's symptoms.
    """

    STABLE = "stable"
    DRIFTING_SLOW = "drifting-slow"
    DRIFTING_FAST = "drifting-fast"


class DriftResult(BaseModel):
    """Per-PID drift trend snapshot emitted by :func:`compute_trend`.

    Frozen so downstream consumers (Rich table renderer, ``--json``
    serializer, predictor helper) can pass the row around without
    worrying about in-flight mutation. Every field is an unambiguous
    primitive — the enum serializes as its string value via
    ``model_dump(mode="json")``.
    """

    model_config = ConfigDict(frozen=True)

    vehicle_id: int
    pid_hex: str
    pid_name: str
    unit: str
    n_samples: int = Field(ge=0)
    n_recordings: int = Field(ge=0)
    first_captured_at: Optional[str]
    last_captured_at: Optional[str]
    span_days: float = Field(ge=0.0)
    slope_per_day: float
    intercept: float
    r_squared: float = Field(ge=0.0, le=1.0)
    mean_value: float
    # Signed — positive = value climbing over time; the sign is
    # physically meaningful (coolant creeping up = silting; battery
    # resting voltage dropping = aging). Consumers colorize by sign
    # + PID, not by abs-value alone.
    drift_pct_per_30_days: float
    bucket: DriftBucket


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_pid_hex(pid_hex: str) -> str:
    """Normalize a PID hex string to Phase 141/142 canonical ``0xNN`` form.

    Accepts ``"0C"``, ``"0x0c"``, ``"0X0C"``, etc., and returns the
    uppercase ``"0x0C"`` form used in ``sensor_samples.pid_hex`` by
    Phase 142's recorder. Pass-through for empty/None returns an empty
    string.
    """
    if pid_hex is None:
        return ""
    s = str(pid_hex).strip()
    if not s:
        return ""
    if s.lower().startswith("0x"):
        body = s[2:]
    else:
        body = s
    return "0x" + body.upper().zfill(2)


def _pid_catalog_entry(pid_hex: str) -> tuple[str, str]:
    """Look up a PID's ``(name, unit)`` via :data:`SENSOR_CATALOG`.

    Best-effort — unknown PIDs get a synthesized name (``"PID 0xNN"``)
    and empty unit so rendering stays stable. Import is lazy to avoid
    pulling the sensor module at module-import time (keeps the drift
    module import-cheap in predictor integration).
    """
    try:
        from motodiag.hardware.sensors import SENSOR_CATALOG

        normalized = _normalize_pid_hex(pid_hex)
        body = normalized[2:] if normalized.lower().startswith("0x") else normalized
        pid_int = int(body, 16)
        spec = SENSOR_CATALOG.get(pid_int)
        if spec is not None:
            return (spec.name, spec.unit)
        return (f"PID {normalized}", "")
    except Exception:
        return (pid_hex or "", "")


def _classify_bucket(abs_pct: float, threshold_pct: float) -> DriftBucket:
    """Classify an absolute drift percentage into a three-band bucket.

    Boundary convention (inclusive at the upper limit):
    ``abs < threshold`` → STABLE, ``threshold ≤ abs < 2×threshold`` →
    DRIFTING_SLOW, ``abs ≥ 2×threshold`` → DRIFTING_FAST. A threshold
    of 0 collapses everything above 0 into DRIFTING_FAST, which the
    tests lock in as the degenerate boundary behavior.
    """
    abs_pct = abs(float(abs_pct))
    threshold_pct = float(threshold_pct)
    if threshold_pct <= 0.0:
        return DriftBucket.STABLE if abs_pct == 0.0 else DriftBucket.DRIFTING_FAST
    if abs_pct < threshold_pct:
        return DriftBucket.STABLE
    if abs_pct < 2.0 * threshold_pct:
        return DriftBucket.DRIFTING_SLOW
    return DriftBucket.DRIFTING_FAST


def _parse_iso(captured_at: str) -> Optional[datetime]:
    """Best-effort :func:`datetime.fromisoformat` parse.

    Accepts the ISO 8601 strings Phase 142 writes. Returns ``None`` on
    unparseable input — the caller drops that sample rather than
    aborting the regression for one malformed row.
    """
    if not captured_at:
        return None
    try:
        return datetime.fromisoformat(captured_at)
    except (TypeError, ValueError):
        return None


def _linear_regression(
    xs: list[float], ys: list[float],
) -> Optional[tuple[float, float, float]]:
    """Mean-of-products linear regression on equal-length series.

    Returns ``(slope, intercept, r_squared)`` or ``None`` when the
    x-series has zero variance (``sxx == 0`` — e.g. every sample has
    the exact same timestamp, degenerate). When ``syy == 0`` (flat
    y-series, a sensor pinned at one value) the series is treated as
    perfectly explained by a zero-slope line: ``r² = 1.0`` and
    ``slope = 0``.
    """
    n = len(xs)
    if n < 2 or len(ys) != n:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    syy = sum((y - mean_y) ** 2 for y in ys)
    if sxx == 0.0:
        return None
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    if syy == 0.0:
        # Flat y — zero-slope fit is exact. sxy will also be 0.
        r_squared = 1.0
    else:
        r_squared = (sxy * sxy) / (sxx * syy)
        # Clamp to [0, 1] to absorb any fp rounding at the boundary.
        r_squared = max(0.0, min(1.0, r_squared))
    return (slope, intercept, r_squared)


def _render_sparkline(values: Iterable[float], width: int = 60) -> str:
    """Render a sequence of floats as a Unicode 1/8-block sparkline.

    ``values`` is binned into ``width`` equal-count buckets; each
    bucket's mean value is normalized onto the 8-glyph palette. Empty
    buckets render as a single space so the absence of samples is
    visible. A flat series (zero range) renders as the mid-height
    glyph so the output is never blank.
    """
    vals = [float(v) for v in values]
    if not vals:
        return ""
    n = len(vals)
    width = max(1, int(width))

    # Bucket means.
    buckets: list[Optional[float]] = []
    if n <= width:
        # One value per bucket, empty trailing bins.
        for i in range(width):
            buckets.append(vals[i] if i < n else None)
    else:
        # Many values → equal-count bucketing.
        for i in range(width):
            lo = int(round(i * n / width))
            hi = int(round((i + 1) * n / width))
            hi = max(hi, lo + 1)
            slice_ = vals[lo:hi]
            buckets.append(sum(slice_) / len(slice_) if slice_ else None)

    present = [b for b in buckets if b is not None]
    if not present:
        return ""
    vmin = min(present)
    vmax = max(present)
    rng = vmax - vmin

    out: list[str] = []
    for b in buckets:
        if b is None:
            out.append(_SPARK_EMPTY)
            continue
        if rng == 0.0:
            # Flat series — pin to the mid-height glyph so the user
            # sees a line rather than an empty bar.
            out.append(_SPARK_CHARS[len(_SPARK_CHARS) // 2])
            continue
        frac = (b - vmin) / rng
        idx = int(frac * (len(_SPARK_CHARS) - 1))
        idx = max(0, min(len(_SPARK_CHARS) - 1, idx))
        out.append(_SPARK_CHARS[idx])
    return "".join(out)


def _render_csv(recordings_data: list[dict[str, Any]], writer: csv.DictWriter) -> None:
    """Write a wide-format CSV: one row per recording.

    Columns: ``recording_id, started_at, pid_hex, mean, min, max,
    n_samples``. The caller constructs the :class:`csv.DictWriter`
    (with ``newline=""`` to avoid Windows blank-row artifacts) and
    writes the header row; this helper only emits data rows.
    """
    for row in recordings_data:
        writer.writerow(
            {
                "recording_id": row["recording_id"],
                "started_at": row["started_at"],
                "pid_hex": row["pid_hex"],
                "mean": row["mean"],
                "min": row["min"],
                "max": row["max"],
                "n_samples": row["n_samples"],
            }
        )


# ---------------------------------------------------------------------------
# compute_trend — single (vehicle, pid) regression
# ---------------------------------------------------------------------------


def compute_trend(
    vehicle_id: int,
    pid_hex: str,
    since: Optional[str] = None,
    until: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[DriftResult]:
    """Fit a linear trend for one ``(vehicle_id, pid_hex)`` over time.

    Parameters
    ----------
    vehicle_id:
        Primary key of the bike in ``vehicles``.
    pid_hex:
        PID in any of ``"0C"``, ``"0x0c"``, ``"0X0C"`` — normalized
        internally to canonical ``"0x0C"`` for the SQL lookup.
    since, until:
        Optional ISO 8601 ``captured_at`` lower / upper bounds. Both
        default to ``None`` (all history).
    db_path:
        Override for the SQLite path (tests).

    Returns
    -------
    DriftResult | None
        ``None`` when fewer than 2 samples are in scope, or when the
        x-series has zero variance (every sample at the same
        timestamp — degenerate).
    """
    canonical_pid = _normalize_pid_hex(pid_hex)
    if not canonical_pid:
        return None

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT s.captured_at, s.value, s.unit, s.recording_id
              FROM sensor_samples s
              JOIN sensor_recordings r ON r.id = s.recording_id
             WHERE r.vehicle_id = ?
               AND s.pid_hex = ?
               AND s.value IS NOT NULL
               AND (? IS NULL OR s.captured_at >= ?)
               AND (? IS NULL OR s.captured_at <= ?)
             ORDER BY s.captured_at ASC
            """,
            (vehicle_id, canonical_pid, since, since, until, until),
        ).fetchall()

    if len(rows) < 2:
        return None

    # Parse timestamps → seconds-since-epoch → days-since-first-sample.
    parsed: list[tuple[datetime, float, str, int]] = []
    for r in rows:
        dt = _parse_iso(r["captured_at"])
        if dt is None:
            continue
        try:
            val = float(r["value"])
        except (TypeError, ValueError):
            continue
        parsed.append((dt, val, r["unit"] or "", int(r["recording_id"])))

    if len(parsed) < 2:
        return None

    t0 = parsed[0][0]
    xs = [(p[0].timestamp() - t0.timestamp()) / 86400.0 for p in parsed]
    ys = [p[1] for p in parsed]

    regression = _linear_regression(xs, ys)
    if regression is None:
        return None
    slope, intercept, r_squared = regression

    mean_y = sum(ys) / len(ys)
    # Signed percent-per-30-days. Guard against mean=0 (uncommon —
    # only when a sensor legitimately rests at zero, e.g. vehicle-
    # speed PID on a bike on a lift). We pick 0.0 as a safe signal;
    # the bucket classifier will then default to STABLE.
    if mean_y == 0.0:
        drift_pct_per_30_days = 0.0
    else:
        drift_pct_per_30_days = 100.0 * slope * 30.0 / mean_y

    bucket = _classify_bucket(abs(drift_pct_per_30_days), 5.0)

    first_dt = parsed[0][0]
    last_dt = parsed[-1][0]
    span_days = (last_dt.timestamp() - first_dt.timestamp()) / 86400.0
    span_days = max(0.0, span_days)

    # Unit: first non-empty unit wins (Phase 142 stores unit per-sample
    # because the decoder attaches it). Typically uniform for a given
    # PID so the pick is deterministic.
    unit = ""
    for _, _, u, _ in parsed:
        if u:
            unit = u
            break

    # PID name via catalog; fallback to "PID 0xNN".
    name, catalog_unit = _pid_catalog_entry(canonical_pid)
    if not unit and catalog_unit:
        unit = catalog_unit

    n_recordings = len({rid for _, _, _, rid in parsed})

    return DriftResult(
        vehicle_id=int(vehicle_id),
        pid_hex=canonical_pid,
        pid_name=name,
        unit=unit,
        n_samples=len(parsed),
        n_recordings=n_recordings,
        first_captured_at=first_dt.isoformat(),
        last_captured_at=last_dt.isoformat(),
        span_days=round(span_days, 6),
        slope_per_day=slope,
        intercept=intercept,
        r_squared=r_squared,
        mean_value=mean_y,
        drift_pct_per_30_days=drift_pct_per_30_days,
        bucket=bucket,
    )


# ---------------------------------------------------------------------------
# detect_drifting_pids — scan all recorded PIDs for one bike
# ---------------------------------------------------------------------------


def detect_drifting_pids(
    vehicle_id: int,
    threshold_pct: float = 5.0,
    since: Optional[str] = None,
    until: Optional[str] = None,
    db_path: Optional[str] = None,
) -> list[DriftResult]:
    """Return non-stable drift results for a bike, sorted by urgency.

    Scans every distinct ``pid_hex`` appearing in the bike's
    ``sensor_samples`` rows, runs :func:`compute_trend` on each, and
    returns only those whose ``abs(drift_pct_per_30_days) ≥
    threshold_pct``. Sort is deterministic: ``abs(pct) DESC``, then
    ``pid_hex ASC`` as tiebreaker.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT s.pid_hex
              FROM sensor_samples s
              JOIN sensor_recordings r ON r.id = s.recording_id
             WHERE r.vehicle_id = ?
               AND s.value IS NOT NULL
            """,
            (vehicle_id,),
        ).fetchall()
    pid_hexes = sorted({row["pid_hex"] for row in rows if row["pid_hex"]})
    if not pid_hexes:
        return []

    results: list[DriftResult] = []
    for pid in pid_hexes:
        res = compute_trend(
            vehicle_id=vehicle_id,
            pid_hex=pid,
            since=since,
            until=until,
            db_path=db_path,
        )
        if res is None:
            continue
        # Re-bucket per the caller's threshold (compute_trend uses 5.0
        # as its default; here we honor the explicit threshold_pct so
        # a mechanic passing --threshold-pct 3 actually sees a
        # different classification).
        bucket = _classify_bucket(
            abs(res.drift_pct_per_30_days), threshold_pct
        )
        rebucketed = res.model_copy(update={"bucket": bucket})
        if rebucketed.bucket == DriftBucket.STABLE:
            continue
        results.append(rebucketed)

    results.sort(
        key=lambda r: (-abs(r.drift_pct_per_30_days), r.pid_hex),
    )
    return results


# ---------------------------------------------------------------------------
# summary_for_bike — three-bucket dict
# ---------------------------------------------------------------------------


def summary_for_bike(
    vehicle_id: int,
    threshold_pct: float = 5.0,
    since: Optional[str] = None,
    until: Optional[str] = None,
    db_path: Optional[str] = None,
) -> dict[str, list[DriftResult]]:
    """Bucket every recorded PID into stable / slow / fast.

    Unlike :func:`detect_drifting_pids`, this function includes the
    ``stable`` bucket so the CLI can render a full inventory without
    a second scan. All three keys are always present (empty lists
    allowed) — callers can rely on the shape.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT s.pid_hex
              FROM sensor_samples s
              JOIN sensor_recordings r ON r.id = s.recording_id
             WHERE r.vehicle_id = ?
               AND s.value IS NOT NULL
            """,
            (vehicle_id,),
        ).fetchall()
    pid_hexes = sorted({row["pid_hex"] for row in rows if row["pid_hex"]})

    out: dict[str, list[DriftResult]] = {
        DriftBucket.STABLE.value: [],
        DriftBucket.DRIFTING_SLOW.value: [],
        DriftBucket.DRIFTING_FAST.value: [],
    }

    for pid in pid_hexes:
        res = compute_trend(
            vehicle_id=vehicle_id,
            pid_hex=pid,
            since=since,
            until=until,
            db_path=db_path,
        )
        if res is None:
            continue
        bucket = _classify_bucket(
            abs(res.drift_pct_per_30_days), threshold_pct
        )
        rebucketed = res.model_copy(update={"bucket": bucket})
        out[bucket.value].append(rebucketed)

    # Deterministic sort per bucket: most-drifted first, then
    # alphabetical pid_hex.
    for key in out:
        out[key].sort(
            key=lambda r: (-abs(r.drift_pct_per_30_days), r.pid_hex),
        )
    return out


__all__ = [
    "DriftBucket",
    "DriftResult",
    "compute_trend",
    "detect_drifting_pids",
    "summary_for_bike",
    "_normalize_pid_hex",
    "_classify_bucket",
    "_linear_regression",
    "_render_sparkline",
    "_render_csv",
]
