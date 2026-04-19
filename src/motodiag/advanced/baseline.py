"""Phase 157 — Performance baselining.

Tenth Track F phase. Derive canonical "healthy baseline" profiles per
(make, model_pattern SQL LIKE, optional year range, canonical pid_hex,
operating_state) from sensor recordings that mechanics have flagged as
known-good.

The workflow is three-stage:

1. **Flag** (mechanic action) — :func:`flag_recording_as_healthy`
   inserts one row per (recording_id) into ``baseline_exemplars``.
   UNIQUE(recording_id) makes the flag idempotent via INSERT OR
   IGNORE. Auto-triggers a rebuild for the bike's (make, model,
   year→year) scope so every flag visibly moves the baseline.
2. **Rebuild** (aggregation) — :func:`rebuild_baseline` loads every
   exemplar recording via :class:`motodiag.hardware.recorder.
   RecordingManager`, runs :func:`_detect_operating_state` on its RPM
   (0x0C) trace, buckets every other PID's readings by the time spans
   those states cover, aggregates per (pid_hex, operating_state)
   across all exemplars using ``statistics.quantiles(n=20)`` for
   p5 / p50 / p95, and DELETEs-then-INSERTs the ``performance_baselines``
   rows for that scope atomically (within a single connection's
   implicit transaction). Confidence 1-5 is derived from distinct-
   exemplar-bike count via the thresholds 0 / 3 / 6 / 11 / 26 →
   1 / 2 / 3 / 4 / 5.
3. **Lookup** (consumer action) — :func:`get_baseline` returns the
   narrowest-year-band match for a (make, model, year, pid_hex,
   operating_state) tuple. Phase 156 comparative (future) can call
   this once instead of scanning the whole peer cohort.

Design notes
------------

- **Zero AI, zero tokens, zero network.** Everything runs on Phase 142
  recordings + the Phase 157 migration 024 tables + stdlib
  :mod:`statistics` + :mod:`bisect`.
- **RPM (0x0C) is the classifier.** :func:`_detect_operating_state`
  only looks at the RPM trace to decide whether a time window counts
  as idle / cruise / redline. Non-RPM PIDs (coolant, O2, MAP) get
  bucketed by whichever state span overlaps their timestamps.
- **Unclassified spans are dropped.** The bike may spend time
  transitioning (accelerating through 3500 RPM, downshifting past
  5000) where no state fits. Those readings never make it into the
  aggregates.
- **Electric bikes have no 0x0C.** :func:`_detect_operating_state`
  returns an empty span list; :func:`rebuild_baseline` returns zero
  baselines created. Phase 158+ introduces motor-kW operating states
  for electric powertrains.
- **Stdlib-only percentile math.** ``statistics.quantiles(n=20)``
  gives the 5th / 50th / 95th cut points when N >= 20; for smaller N
  we fall back to a :mod:`bisect`-based interpolation so the function
  stays sane at N=3 (the smallest cohort that confidence_1to5 >= 2
  allows).
"""

from __future__ import annotations

import statistics
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The canonical RPM PID. Phase 157 classifies operating states by
#: looking at this trace only — non-RPM PIDs are bucketed by time-span
#: overlap afterwards.
RPM_PID_HEX: str = "0x0C"

#: Minimum window duration (seconds) for idle / cruise classification.
#: Redline has its own lower bound (below) — real-world redline is
#: rarely sustained for 3 s.
_WINDOW_MIN_SECONDS_STABLE: float = 3.0

#: Minimum window duration (seconds) for redline classification. One
#: second is enough to separate a genuine dyno pull from noise.
_WINDOW_MIN_SECONDS_REDLINE: float = 1.0

#: Confidence 1-5 thresholds on distinct-exemplar-bike count. Read:
#: 0 exemplars → 1, >=3 → 2, >=6 → 3, >=11 → 4, >=26 → 5. Chosen so a
#: shop with a modest fleet (3-6 bikes) lands at 2-3 and a mature
#: dataset (26+) reaches the cap.
_CONFIDENCE_THRESHOLDS: list[tuple[int, int]] = [
    (26, 5),
    (11, 4),
    (6, 3),
    (3, 2),
    (0, 1),
]


# ---------------------------------------------------------------------------
# Enums + models
# ---------------------------------------------------------------------------


class OperatingState(str, Enum):
    """Canonical RPM-derived operating states for performance baselines.

    Three persisted values mirror the migration 024 CHECK constraint
    verbatim. ``UNCLASSIFIED`` is internal-only — it labels time
    windows that don't fit any band (accelerating, downshifting, idle-
    but-stalling) so :func:`rebuild_baseline` can skip those samples
    cleanly. UNCLASSIFIED is never written to ``performance_baselines``
    (the CHECK would reject it) and never returned by :func:`get_baseline`.
    """

    IDLE = "idle"
    CRUISE_2500 = "2500rpm"
    REDLINE = "redline"
    UNCLASSIFIED = "unclassified"


class BaselineProfile(BaseModel):
    """A single persisted performance_baselines row.

    Frozen — the profile flows through the Rich table renderer, the
    ``--json`` serializer, and test assertions. Mutating a profile
    mid-pipeline is always a bug.

    Attributes
    ----------
    id:
        Primary key. ``None`` on pre-INSERT instances.
    make:
        Lowercased manufacturer string (e.g. ``"harley-davidson"``).
    model_pattern:
        SQL LIKE pattern (``"Sportster%"``, ``"CBR600%"``). Stored as
        the mechanic typed it — casing preserved.
    year_min / year_max:
        Optional inclusive year band. ``None`` on both sides means the
        baseline applies to any year of this (make, model_pattern).
    pid_hex:
        Canonical ``"0x0C"`` uppercase form.
    operating_state:
        The string value of :class:`OperatingState` (``"idle"`` /
        ``"2500rpm"`` / ``"redline"``). UNCLASSIFIED never shows up
        here — the DB CHECK would reject it.
    expected_min / expected_max / expected_median:
        p5 / p95 / p50 across the exemplar cohort's per-state readings.
    sample_count:
        Total number of raw sensor_samples rows that contributed.
    last_rebuilt_at:
        ISO 8601 string; defaulted by the DB to CURRENT_TIMESTAMP on
        INSERT.
    confidence_1to5:
        Integer 1-5 derived from distinct-exemplar-bike count via
        :data:`_CONFIDENCE_THRESHOLDS`.
    """

    model_config = ConfigDict(frozen=True)

    id: Optional[int] = None
    make: str
    model_pattern: str
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    pid_hex: str
    operating_state: str
    expected_min: float
    expected_max: float
    expected_median: float
    sample_count: int = 0
    last_rebuilt_at: Optional[str] = None
    confidence_1to5: int = Field(ge=1, le=5, default=1)


# ---------------------------------------------------------------------------
# Operating-state detection
# ---------------------------------------------------------------------------


def _detect_operating_state(
    pid_readings: list[tuple[datetime, str, float]],
) -> list[tuple[datetime, datetime, OperatingState]]:
    """Classify consecutive RPM windows into idle / cruise / redline spans.

    Parameters
    ----------
    pid_readings:
        All (timestamp, pid_hex, value) triples from a single recording.
        Only rows with ``pid_hex == RPM_PID_HEX`` (``"0x0C"``) are
        consulted; non-RPM rows are silently ignored so callers can
        hand the function the whole recording without filtering first.

    Returns
    -------
    list of ``(start, end, state)`` tuples covering the parts of the
    recording where a state was confidently identified. UNCLASSIFIED
    windows (transitioning / unstable RPM / sub-window-length) are
    represented as gaps — they simply don't appear in the returned
    list. Consumers iterate the returned spans and drop any readings
    whose timestamps fall in the gaps.

    Algorithm
    ---------

    1. Filter and sort RPM readings by timestamp.
    2. Walk forward, greedily extending the current span as long as the
       next reading fits the same state's RPM band AND stddev across
       the current span stays below the state's stability threshold.
    3. When a reading breaks the band or the stddev limit, close out
       the current span (if it met the state's minimum duration) and
       start a new candidate span from that reading.

    State bands (empirically chosen, documented in Phase 157
    implementation.md):

    =====================  ============  =================  ===============
    state                  rpm band      stddev ceiling     min duration
    =====================  ============  =================  ===============
    idle                   rpm < 1200    stddev < 150       3 s
    2500rpm (cruise)       2000-4000     stddev < 300       3 s
    redline                rpm > 7000    stddev < 500       1 s
    =====================  ============  =================  ===============

    Anything outside those bands, or any window whose stddev exceeds
    the ceiling, stays UNCLASSIFIED and is not emitted. Windows that
    meet the band + stddev test but are shorter than the minimum
    duration are also dropped.
    """
    # Filter to the RPM PID only, and preserve the caller's time order
    # by sorting (sensor_samples may return interleaved rows).
    rpm_rows: list[tuple[datetime, float]] = []
    for ts, pid_hex, value in pid_readings:
        if pid_hex == RPM_PID_HEX and value is not None:
            rpm_rows.append((ts, float(value)))
    rpm_rows.sort(key=lambda pair: pair[0])

    if len(rpm_rows) < 2:
        return []

    def _state_for_value(v: float) -> OperatingState:
        if v < 1200:
            return OperatingState.IDLE
        if 2000 <= v <= 4000:
            return OperatingState.CRUISE_2500
        if v > 7000:
            return OperatingState.REDLINE
        return OperatingState.UNCLASSIFIED

    def _stddev_ceiling(state: OperatingState) -> float:
        if state is OperatingState.IDLE:
            return 150.0
        if state is OperatingState.CRUISE_2500:
            return 300.0
        if state is OperatingState.REDLINE:
            return 500.0
        return 0.0  # UNCLASSIFIED — never accepted

    def _min_duration(state: OperatingState) -> float:
        if state is OperatingState.REDLINE:
            return _WINDOW_MIN_SECONDS_REDLINE
        return _WINDOW_MIN_SECONDS_STABLE

    def _finalize(
        state: OperatingState,
        window: list[tuple[datetime, float]],
        out: list[tuple[datetime, datetime, OperatingState]],
    ) -> None:
        if state is OperatingState.UNCLASSIFIED or len(window) < 2:
            return
        duration = (window[-1][0] - window[0][0]).total_seconds()
        if duration < _min_duration(state):
            return
        # Recompute stddev one last time so a window grown past the
        # stability threshold at the last step doesn't slip through.
        values = [v for _, v in window]
        if statistics.stdev(values) >= _stddev_ceiling(state):
            return
        out.append((window[0][0], window[-1][0], state))

    spans: list[tuple[datetime, datetime, OperatingState]] = []
    current_state: Optional[OperatingState] = None
    current_window: list[tuple[datetime, float]] = []

    for ts, value in rpm_rows:
        candidate_state = _state_for_value(value)
        if candidate_state is OperatingState.UNCLASSIFIED:
            # Break the current span (if any) and skip.
            if current_state is not None:
                _finalize(current_state, current_window, spans)
            current_state = None
            current_window = []
            continue

        if current_state is None:
            current_state = candidate_state
            current_window = [(ts, value)]
            continue

        if candidate_state is current_state:
            # Tentatively extend and re-check stddev.
            tentative = current_window + [(ts, value)]
            vals = [v for _, v in tentative]
            if (
                len(vals) >= 2
                and statistics.stdev(vals) < _stddev_ceiling(current_state)
            ):
                current_window = tentative
                continue
            # Stddev exceeded — close the existing span and start fresh.
            _finalize(current_state, current_window, spans)
            current_state = candidate_state
            current_window = [(ts, value)]
        else:
            # State changed (e.g. idle → cruise). Close out and start new.
            _finalize(current_state, current_window, spans)
            current_state = candidate_state
            current_window = [(ts, value)]

    # Close the trailing span, if any.
    if current_state is not None:
        _finalize(current_state, current_window, spans)

    return spans


# ---------------------------------------------------------------------------
# Internal helpers — percentile math + confidence
# ---------------------------------------------------------------------------


def _percentiles(values: list[float]) -> Optional[tuple[float, float, float]]:
    """Return (p5, p50, p95) or None when values is empty.

    Uses ``statistics.quantiles(n=20)`` when ``len(values) >= 20`` so we
    get true 5th / 50th / 95th percentiles. For smaller N we fall back
    to a :mod:`bisect`-based interpolation — sort once, look up the
    target quantile's fractional index, linearly interpolate between
    the two nearest samples. Identical to ``quantiles`` at N=20 and
    reasonable at N as low as 3.
    """
    if not values:
        return None
    if len(values) == 1:
        v = float(values[0])
        return v, v, v

    if len(values) >= 20:
        # quantiles(n=20) gives us 19 cut points: q[0] is the 5th
        # percentile, q[9] the 50th, q[18] the 95th.
        q = statistics.quantiles(values, n=20)
        return float(q[0]), float(q[9]), float(q[18])

    def _interp(sorted_vals: list[float], p: float) -> float:
        if len(sorted_vals) == 1:
            return sorted_vals[0]
        # p in [0, 1]; position on a 0..(N-1) axis.
        target = p * (len(sorted_vals) - 1)
        lo = int(target)
        if lo >= len(sorted_vals) - 1:
            return sorted_vals[-1]
        frac = target - lo
        return sorted_vals[lo] + frac * (sorted_vals[lo + 1] - sorted_vals[lo])

    sorted_vals = sorted(float(v) for v in values)
    p5 = _interp(sorted_vals, 0.05)
    p50 = _interp(sorted_vals, 0.50)
    p95 = _interp(sorted_vals, 0.95)
    # Guard: band must be monotone non-decreasing (interpolation is
    # exact, but we future-proof against a float rounding flip).
    lo, mid, hi = sorted([p5, p50, p95])
    return lo, mid, hi


def _confidence_for_bikes(n_distinct_bikes: int) -> int:
    """Map distinct-exemplar-bike count → 1-5 confidence band."""
    for threshold, level in _CONFIDENCE_THRESHOLDS:
        if n_distinct_bikes >= threshold:
            return level
    return 1


def _state_for_timestamp(
    ts: datetime,
    spans: list[tuple[datetime, datetime, OperatingState]],
) -> Optional[OperatingState]:
    """Return the state whose span contains ``ts``, or None for gap windows."""
    for start, end, state in spans:
        if start <= ts <= end:
            return state
    return None


# ---------------------------------------------------------------------------
# flag_recording_as_healthy
# ---------------------------------------------------------------------------


def flag_recording_as_healthy(
    recording_id: int,
    flagged_by_user_id: int = 1,
    db_path: Optional[str] = None,
) -> dict:
    """Mark a sensor recording as a known-healthy exemplar and rebuild.

    Validations (raise :class:`ValueError`):

    - Recording exists with non-NULL ``stopped_at`` — a recording that
      is still in-progress cannot be flagged.
    - Recording has non-NULL ``vehicle_id`` — a dealer-lot recording
      with no associated bike has no (make, model, year) to scope
      the baseline against.

    Side effects (idempotent):

    - INSERT OR IGNORE into ``baseline_exemplars`` (UNIQUE(recording_id)
      dedupes silently — a second flag is a no-op).
    - Auto-call :func:`rebuild_baseline` for the bike's (make, model as
      exact-model model_pattern, year_min=year_max=vehicle.year) scope.
      Mechanics flagging one exemplar expect to see the baseline move;
      the auto-rebuild makes that visible without a separate command.

    Returns
    -------
    dict
        ``{"exemplar_id": int, "baselines_updated": int,
        "baselines_created": int}``. ``exemplar_id`` is the row ID of
        the existing or newly-inserted exemplar row. The ``baselines_*``
        counts come from the piggybacked rebuild.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT r.id, r.vehicle_id, r.stopped_at,
                   v.make, v.model, v.year
              FROM sensor_recordings r
              LEFT JOIN vehicles v ON v.id = r.vehicle_id
             WHERE r.id = ?
            """,
            (int(recording_id),),
        )
        row = cursor.fetchone()

    if row is None:
        raise ValueError(f"Recording {recording_id} not found")
    if row["stopped_at"] is None:
        raise ValueError(
            f"Recording {recording_id} is still in-progress "
            "(stopped_at IS NULL) — stop the recording first."
        )
    if row["vehicle_id"] is None:
        raise ValueError(
            f"Recording {recording_id} has no vehicle_id "
            "(dealer-lot scenario) — associate it with a garage bike first."
        )

    make = row["make"]
    model = row["model"]
    year = row["year"]

    # Idempotent INSERT OR IGNORE via UNIQUE(recording_id).
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO baseline_exemplars
                (vehicle_id, recording_id, flagged_by_user_id)
            VALUES (?, ?, ?)
            """,
            (int(row["vehicle_id"]), int(recording_id), int(flagged_by_user_id)),
        )
        # Resolve exemplar_id whether we just inserted or ignored.
        exemplar_row = conn.execute(
            "SELECT id FROM baseline_exemplars WHERE recording_id = ?",
            (int(recording_id),),
        ).fetchone()
        exemplar_id = int(exemplar_row["id"])

    # Auto-rebuild for this bike's scope. Exact-model pattern (no SQL
    # wildcards) keeps the flag focused — a mechanic flagging a 2015
    # Road Glide expects only 2015 Road Glide baselines to move.
    rebuild_result = rebuild_baseline(
        make=make or "",
        model_pattern=model or "",
        year_min=int(year) if year is not None else None,
        year_max=int(year) if year is not None else None,
        db_path=db_path,
    )

    return {
        "exemplar_id": exemplar_id,
        "baselines_updated": int(rebuild_result.get("baselines_updated", 0)),
        "baselines_created": int(rebuild_result.get("baselines_created", 0)),
    }


# ---------------------------------------------------------------------------
# rebuild_baseline
# ---------------------------------------------------------------------------


def rebuild_baseline(
    make: str,
    model_pattern: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    db_path: Optional[str] = None,
) -> dict:
    """Re-aggregate performance_baselines for one (make, model, years) scope.

    Parameters
    ----------
    make:
        Make string. Normalized to lowercase for the vehicles.make
        lookup (the Phase 110 registry stores make case-insensitively).
    model_pattern:
        SQL LIKE pattern for model matching (``"Sportster%"``,
        ``"CBR%"``). Stored verbatim — callers who want exact-match
        should pass the bare model string (SQLite LIKE with no
        wildcards == equality, case-insensitive by default).
    year_min / year_max:
        Optional inclusive year window on the exemplar's vehicle.year.
        Both None → all years.

    Algorithm
    ---------

    1. Pull every exemplar whose vehicle (make, model LIKE pattern,
       year in range) matches. Skip exemplars whose recording is
       missing (CASCADE on recording_id should make this impossible
       in practice, but the defensive check keeps the test suite
       deterministic).
    2. For each exemplar: import-delayed :class:`RecordingManager` to
       avoid circular imports. Load the recording, run
       :func:`_detect_operating_state` on the RPM trace, bucket every
       PID's readings by the state spans they fall within, accumulate
       per (pid_hex, operating_state).
    3. Aggregate across exemplars: compute p5 / p50 / p95 per
       (pid_hex, operating_state) via :func:`_percentiles`.
    4. Derive confidence from the count of distinct
       ``vehicle_id``s that contributed to each (pid, state) bucket.
    5. DELETE existing rows matching the same (make, model_pattern,
       year_min, year_max) scope then batch INSERT the new aggregates.
       Both inside a single connection's implicit transaction so a
       mid-rebuild crash leaves the previous aggregate intact.

    Returns
    -------
    dict
        ``{"baselines_updated": N, "baselines_created": N,
        "exemplar_count": N}``. For a clean rebuild ``updated == 0``
        and ``created`` equals the row count inserted. If any rows
        existed before the rebuild, ``updated`` is the count deleted
        and ``created`` the count reinserted — they are typically
        equal for a simple re-flag.
    """
    # Import-delayed — RecordingManager's module imports from us
    # (eventually), and we use it only here.
    from motodiag.hardware.recorder import RecordingManager

    normalized_make = (make or "").strip().lower()
    model_like = (model_pattern or "").strip()

    where_clauses = ["LOWER(v.make) = ?", "v.model LIKE ?"]
    params: list = [normalized_make, model_like]
    if year_min is not None and year_max is not None:
        where_clauses.append("v.year BETWEEN ? AND ?")
        params.extend([int(year_min), int(year_max)])
    elif year_min is not None:
        where_clauses.append("v.year >= ?")
        params.append(int(year_min))
    elif year_max is not None:
        where_clauses.append("v.year <= ?")
        params.append(int(year_max))

    sql = (
        "SELECT be.recording_id, be.vehicle_id, v.year "
        "  FROM baseline_exemplars be "
        "  JOIN sensor_recordings sr ON sr.id = be.recording_id "
        "  JOIN vehicles v ON v.id = be.vehicle_id "
        " WHERE " + " AND ".join(where_clauses)
    )

    with get_connection(db_path) as conn:
        exemplar_rows = [
            dict(r) for r in conn.execute(sql, tuple(params)).fetchall()
        ]

    # Map (pid_hex, state) → {"values": [...], "bikes": set(vehicle_id)}.
    buckets: dict[tuple[str, OperatingState], dict] = {}

    mgr = RecordingManager(db_path=db_path)
    for exemplar in exemplar_rows:
        recording_id = int(exemplar["recording_id"])
        vehicle_id = exemplar.get("vehicle_id")
        try:
            _meta, samples_iter = mgr.load_recording(recording_id)
        except KeyError:
            # Defensive — CASCADE should prevent this.
            continue

        # Materialize into (datetime, pid_hex, value) for state detection.
        triples: list[tuple[datetime, str, float]] = []
        for s in samples_iter:
            raw_ts = s.get("captured_at")
            if raw_ts is None:
                continue
            try:
                ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                continue
            value = s.get("value")
            if value is None:
                continue
            try:
                v = float(value)
            except (TypeError, ValueError):
                continue
            triples.append((ts, str(s.get("pid_hex") or "").strip(), v))

        spans = _detect_operating_state(triples)
        if not spans:
            continue

        for ts, pid_hex, value in triples:
            state = _state_for_timestamp(ts, spans)
            if state is None or state is OperatingState.UNCLASSIFIED:
                continue
            key = (pid_hex, state)
            bucket = buckets.setdefault(key, {"values": [], "bikes": set()})
            bucket["values"].append(value)
            if vehicle_id is not None:
                bucket["bikes"].add(int(vehicle_id))

    # Build the INSERT rows from the buckets.
    insert_rows: list[tuple] = []
    last_rebuilt_at = datetime.now().isoformat(timespec="seconds")
    for (pid_hex, state), data in buckets.items():
        values = data["values"]
        pcts = _percentiles(values)
        if pcts is None:
            continue
        p5, p50, p95 = pcts
        # Guard against float rounding breaking the CHECK constraint.
        lo, mid, hi = sorted([p5, p50, p95])
        insert_rows.append(
            (
                normalized_make,
                model_like,
                int(year_min) if year_min is not None else None,
                int(year_max) if year_max is not None else None,
                pid_hex,
                state.value,
                float(lo),
                float(hi),
                float(mid),
                int(len(values)),
                last_rebuilt_at,
                _confidence_for_bikes(len(data["bikes"])),
            )
        )

    # Atomic DELETE-then-INSERT for the target scope.
    with get_connection(db_path) as conn:
        delete_sql = (
            "DELETE FROM performance_baselines "
            "WHERE LOWER(make) = ? AND model_pattern = ? "
            "  AND ((? IS NULL AND year_min IS NULL) OR year_min = ?) "
            "  AND ((? IS NULL AND year_max IS NULL) OR year_max = ?)"
        )
        y_min_p = int(year_min) if year_min is not None else None
        y_max_p = int(year_max) if year_max is not None else None
        del_cur = conn.execute(
            delete_sql,
            (
                normalized_make,
                model_like,
                y_min_p,
                y_min_p,
                y_max_p,
                y_max_p,
            ),
        )
        deleted = int(del_cur.rowcount or 0)

        if insert_rows:
            conn.executemany(
                """
                INSERT INTO performance_baselines
                    (make, model_pattern, year_min, year_max,
                     pid_hex, operating_state,
                     expected_min, expected_max, expected_median,
                     sample_count, last_rebuilt_at, confidence_1to5)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                insert_rows,
            )

    return {
        "baselines_updated": deleted,
        "baselines_created": len(insert_rows),
        "exemplar_count": len(exemplar_rows),
    }


# ---------------------------------------------------------------------------
# get_baseline
# ---------------------------------------------------------------------------


def get_baseline(
    make: str,
    model: str,
    year: int,
    pid_hex: str,
    operating_state: str,
    db_path: Optional[str] = None,
) -> Optional[BaselineProfile]:
    """Fetch the best-matching baseline for one (bike, pid, state) tuple.

    Selection rules (``ORDER BY``):

    1. ``confidence_1to5 DESC`` — higher-confidence baselines beat
       lower-confidence ones.
    2. Narrowest year band wins — a baseline with ``year_min == year_max``
       (single model year) beats a ten-year-band row. Implemented as
       ``(year_max - year_min) ASC``, treating NULLs as an effectively-
       infinite band (COALESCE to a large number in the ORDER BY).
    3. ``id ASC`` as a final deterministic tiebreak.

    Parameters
    ----------
    make, model, year, pid_hex, operating_state:
        The target bike + lookup coordinates. ``make`` is lowercased
        before comparison so the stored (lowercased) and queried
        (any-case) values match. ``pid_hex`` is passed verbatim —
        callers are responsible for canonicalizing to the ``"0x0C"``
        uppercase form. ``operating_state`` must be one of the three
        persisted values (``"idle"``, ``"2500rpm"``, ``"redline"``).

    Returns
    -------
    BaselineProfile or None
        None when no baseline matches. The narrowest-year-band winner
        when multiple rows match — e.g. a query for a 2015 Sportster
        hits both the 2014-2016 row and the 2010-2020 row; the 3-year
        band wins.
    """
    normalized_make = (make or "").strip().lower()

    with get_connection(db_path) as conn:
        # Use COALESCE to push NULL year bands to the back of the
        # narrowness sort — a NULL/NULL band is "all years" and is the
        # broadest possible match, so it should tie-break LAST.
        row = conn.execute(
            """
            SELECT *,
                   COALESCE(year_max, 9999) - COALESCE(year_min, -9999)
                       AS band_width
              FROM performance_baselines
             WHERE LOWER(make) = ?
               AND ? LIKE model_pattern
               AND (
                   (year_min IS NULL AND year_max IS NULL)
                   OR (? BETWEEN COALESCE(year_min, -9999)
                                 AND COALESCE(year_max, 9999))
               )
               AND pid_hex = ?
               AND operating_state = ?
             ORDER BY confidence_1to5 DESC,
                      band_width ASC,
                      id ASC
             LIMIT 1
            """,
            (
                normalized_make,
                model or "",
                int(year),
                pid_hex,
                operating_state,
            ),
        ).fetchone()

    if row is None:
        return None

    return BaselineProfile(
        id=int(row["id"]),
        make=row["make"],
        model_pattern=row["model_pattern"],
        year_min=row["year_min"],
        year_max=row["year_max"],
        pid_hex=row["pid_hex"],
        operating_state=row["operating_state"],
        expected_min=float(row["expected_min"]),
        expected_max=float(row["expected_max"]),
        expected_median=float(row["expected_median"]),
        sample_count=int(row["sample_count"] or 0),
        last_rebuilt_at=row["last_rebuilt_at"],
        confidence_1to5=int(row["confidence_1to5"] or 1),
    )


# ---------------------------------------------------------------------------
# Listing helper (used by `motodiag advanced baseline list`)
# ---------------------------------------------------------------------------


def list_baselines(
    make: Optional[str] = None,
    min_confidence: Optional[int] = None,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Return one row per distinct (make, model_pattern, year_min, year_max)
    scope with aggregate counts for the ``list`` CLI.

    Each row includes:

    - ``make`` / ``model_pattern`` / ``year_min`` / ``year_max`` — the
      scope keys.
    - ``pid_count`` — DISTINCT count of ``pid_hex`` across persisted
      rows for this scope.
    - ``exemplar_count`` — DISTINCT count of ``baseline_exemplars``
      bound to bikes whose vehicle (make, model LIKE model_pattern,
      year within band) falls inside this scope.
    - ``confidence_1to5`` — the MAX across the scope's rows (a scope's
      best-case confidence is the most-informative signal to surface
      in a top-level listing).
    - ``last_rebuilt_at`` — the MAX across the scope's rows.
    """
    clauses: list[str] = []
    params: list = []
    if make:
        clauses.append("LOWER(pb.make) = ?")
        params.append(make.strip().lower())
    if min_confidence is not None:
        clauses.append("pb.confidence_1to5 >= ?")
        params.append(int(min_confidence))

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT pb.make,
               pb.model_pattern,
               pb.year_min,
               pb.year_max,
               COUNT(DISTINCT pb.pid_hex) AS pid_count,
               MAX(pb.confidence_1to5) AS confidence_1to5,
               MAX(pb.last_rebuilt_at) AS last_rebuilt_at
          FROM performance_baselines pb
          {where}
         GROUP BY pb.make, pb.model_pattern, pb.year_min, pb.year_max
         ORDER BY pb.make ASC, pb.model_pattern ASC,
                  pb.year_min ASC, pb.year_max ASC
    """

    with get_connection(db_path) as conn:
        rows = [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]
        # Attach exemplar count per scope via a second query — JOINing
        # vehicles into the main GROUP BY would force cross-joins on the
        # baseline table and inflate counts.
        for row in rows:
            exemplar_sql_clauses = ["LOWER(v.make) = ?", "v.model LIKE ?"]
            exemplar_params: list = [
                row["make"].lower() if row.get("make") else "",
                row.get("model_pattern") or "",
            ]
            if row.get("year_min") is not None and row.get("year_max") is not None:
                exemplar_sql_clauses.append("v.year BETWEEN ? AND ?")
                exemplar_params.extend([row["year_min"], row["year_max"]])
            exemplar_sql = (
                "SELECT COUNT(DISTINCT be.id) AS n "
                "  FROM baseline_exemplars be "
                "  JOIN vehicles v ON v.id = be.vehicle_id "
                " WHERE " + " AND ".join(exemplar_sql_clauses)
            )
            ex_row = conn.execute(
                exemplar_sql, tuple(exemplar_params),
            ).fetchone()
            row["exemplar_count"] = int(ex_row["n"]) if ex_row else 0

    return rows
