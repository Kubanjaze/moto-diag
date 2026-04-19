"""Comparative diagnostics — peer-cohort anomaly detection (Phase 156).

Ninth Track F phase. Given one bike's recorded sensor data (Phase 142
:mod:`motodiag.hardware.recorder`), find a cohort of similar bikes'
recordings, compute peer median / p25 / p75 / p95 on a chosen PID, and
bucket the target bike against those percentiles to flag anomalies.

Mechanic scenario
-----------------

Mechanic records a 2015 Road Glide idling at 112 °C coolant. Phase 156
pulls the 20 other 2015 Road Glide recordings from ``sensor_recordings``,
computes peer median 92 °C / p75 98 °C / p95 108 °C, and reports
"bike is ``>=p95`` — hotter than 95 % of peers, probably a cooling-
system issue".

Design rules
------------

- **Zero AI, zero migration, zero tokens.** Pure SQL on Phase 142
  tables + stdlib :mod:`statistics`.
- **Plain dataclasses, not Pydantic.** :class:`PeerStats` and
  :class:`PeerComparison` are frozen :func:`dataclasses.dataclass` so
  they serialize cheaply and carry no validation overhead — the data
  comes from our own SQL, not user input.
- **Two-stage reduction.** For each peer recording we compute a single
  per-PID summary (avg / max / p95) via :func:`_metric_reducer`; then
  percentiles across those per-recording summaries give the cohort
  distribution. This isolates within-recording noise from
  across-recording variance.
- **Cohort cap of 200 recordings** keeps the math cheap even on shops
  with thousands of logs.
- **Fleet cohort is Phase 150 territory.** We feature-detect
  ``fleet_memberships`` at runtime and short-circuit with a
  ``FLEET_UNAVAILABLE`` marker when the table is missing.

Public surface
--------------

- :class:`PeerStats` — cohort summary (size, distinct_bikes, p25/p50/
  p75/p95, unit, warning).
- :class:`PeerComparison` — target vs cohort (target_summary, bucket,
  anomaly_flag, pid_name, cohort stats).
- :func:`find_peer_recordings` — SQL cohort selection.
- :func:`compute_peer_stats` — per-recording summary + cross-cohort
  percentiles.
- :func:`compare_against_peers` — full pipeline for one (recording, pid).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Optional

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Upper bound on the number of peer recordings pulled per cohort. Keeps
#: percentile math O(200) even when a shop has thousands of logs.
COHORT_CAP: int = 200

#: Sentinel returned by :func:`find_peer_recordings` when ``fleet`` cohort
#: is requested but Phase 150's ``fleet_memberships`` table does not yet
#: exist. Callers render a yellow "Phase 150 required" panel and exit 0.
FLEET_UNAVAILABLE: str = "__fleet_unavailable__"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PeerStats:
    """Cross-cohort percentile summary for a single PID.

    Parameters
    ----------
    pid_hex:
        Canonical ``"0x05"`` PID identifier.
    cohort_size:
        Number of peer recordings that contributed (after
        :data:`COHORT_CAP` filtering and missing-PID elimination).
    distinct_bikes:
        Number of unique ``vehicle_id`` values across ``cohort_size``
        recordings. Mechanics often re-record the same bike on multiple
        visits; this count surfaces how many *bikes* (not recordings)
        the percentiles represent.
    p25 / p50 / p75 / p95:
        Percentile cut points across per-recording summaries. ``None``
        when the cohort is empty.
    unit:
        Free-text unit propagated from the first non-empty
        ``sensor_samples.unit`` encountered (``""`` when absent).
    metric:
        The per-recording metric (``"avg"`` / ``"max"`` / ``"p95"``)
        that the percentiles summarize. Kept on the struct so consumers
        don't need to plumb it separately.
    warning:
        Optional free-text note — ``None`` when the cohort is healthy;
        a short string (e.g. "Insufficient cohort — 3 peers found,
        minimum 5") when a downstream guard triggered.
    """

    pid_hex: str
    cohort_size: int
    distinct_bikes: int
    p25: Optional[float]
    p50: Optional[float]
    p75: Optional[float]
    p95: Optional[float]
    unit: str
    metric: str
    warning: Optional[str]


@dataclass(frozen=True)
class PeerComparison:
    """Target-vs-cohort comparison for a single ``(recording, pid)``.

    Parameters
    ----------
    vehicle_recording_id:
        The target recording's primary key (``sensor_recordings.id``).
    pid_hex:
        Canonical ``"0x05"`` PID identifier.
    pid_name:
        Human name from :data:`motodiag.hardware.sensors.SENSOR_CATALOG`
        (``"Engine coolant temperature"``) or the hex string as a fallback.
    target_summary:
        The target recording's own per-PID metric value. ``None`` when
        the target recording does not contain ``pid_hex``.
    cohort:
        Full :class:`PeerStats` — ``cohort_size == 0`` when below
        ``peers_min``; check ``cohort.warning`` for the reason.
    bucket:
        Percentile band the target lands in relative to the cohort:
        ``"<p25"`` / ``"p25-p50"`` / ``"p50-p75"`` / ``"p75-p95"`` /
        ``">=p95"``. ``None`` when the cohort is empty or the target
        has no value for this PID.
    anomaly_flag:
        ``True`` when the bucket is in the tails (``"<p25"`` or
        ``">=p95"``). Mechanic-facing "pay attention" signal.
    cohort_filter:
        Which cohort mode produced this comparison: ``"same-model"`` /
        ``"strict"`` / ``"fleet"``. Kept on the struct so a JSON
        consumer knows the provenance.
    """

    vehicle_recording_id: int
    pid_hex: str
    pid_name: str
    target_summary: Optional[float]
    cohort: PeerStats
    bucket: Optional[str]
    anomaly_flag: bool
    cohort_filter: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_pid_hex(pid: Any) -> str:
    """Return the canonical ``"0x05"`` form of a PID identifier.

    Accepts integers (``5``), plain hex strings (``"05"`` / ``"5"``),
    and ``0x``-prefixed strings (``"0x5"`` / ``"0X05"``). Always returns
    ``"0x{HH}"`` with an uppercase two-char hex body so SQLite string
    equality works against the ``sensor_samples.pid_hex`` rows that
    Phase 142's :func:`_reading_to_sample_row` writes.

    Raises :class:`ValueError` on malformed input (non-hex characters,
    negative ints, or ints outside 0-255).
    """
    if isinstance(pid, int):
        if pid < 0 or pid > 0xFF:
            raise ValueError(f"PID out of range (0-255): {pid}")
        return f"0x{pid:02X}"

    s = str(pid).strip()
    if not s:
        raise ValueError("PID string is empty")
    if s.lower().startswith("0x"):
        s = s[2:]
    # Reject whitespace or internal '0x' leftovers.
    if not s:
        raise ValueError("PID string has no hex body after '0x' prefix")
    try:
        value = int(s, 16)
    except ValueError as exc:
        raise ValueError(f"PID string is not valid hex: {pid!r}") from exc
    if value < 0 or value > 0xFF:
        raise ValueError(f"PID out of range (0-255): {pid!r}")
    return f"0x{value:02X}"


def _fleet_tables_available(db_path: Optional[str] = None) -> bool:
    """Return True iff Phase 150's ``fleet_memberships`` table exists.

    Feature-detection via ``sqlite_master`` keeps Phase 156 forward-
    compatible: when Phase 150 lands and adds the table, the same CLI
    subcommand starts resolving fleet cohorts without a code change.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='fleet_memberships'"
        ).fetchone()
    return row is not None


def _pid_display_name(pid_hex: str) -> str:
    """Best-effort lookup of a human PID name from the Phase 141 catalog.

    Lazy import keeps Phase 156 from pulling the sensors module (and
    its pydantic + click surface) on package import. Falls back to the
    canonical hex string when the catalog has no entry — safe for custom
    PIDs that never went through the J1979 decoder.
    """
    try:
        from motodiag.hardware.sensors import SENSOR_CATALOG

        pid_int = int(pid_hex, 16)
        spec = SENSOR_CATALOG.get(pid_int)
        if spec is not None:
            return spec.name
    except Exception:
        # Import or lookup failure — fall through to the hex fallback.
        pass
    return pid_hex


def _bucket(target: float, p25: float, p50: float, p75: float, p95: float) -> str:
    """Return the percentile band ``target`` lands in.

    Bucket boundaries are inclusive on the upper edge for the ">=p95"
    tail (the spec's explicit rule: "target == p95 → ``>=p95``") and
    half-open elsewhere. A target below p25 sits in ``"<p25"``.
    """
    if target >= p95:
        return ">=p95"
    if target >= p75:
        return "p75-p95"
    if target >= p50:
        return "p50-p75"
    if target >= p25:
        return "p25-p50"
    return "<p25"


def _metric_reducer(values: list[float], metric: str) -> Optional[float]:
    """Compute the per-recording summary on a list of float values.

    ``metric`` is one of ``"avg"`` / ``"max"`` / ``"p95"``:

    - ``avg`` — arithmetic mean via :func:`statistics.fmean`.
    - ``max`` — ``max(values)``.
    - ``p95`` — 95th-percentile cut point. Delegates to
      ``statistics.quantiles(values, n=20)[18]`` when we have enough
      samples for a meaningful split; falls back to ``max(values)`` on
      very short series (``n < 2``).

    Returns ``None`` when ``values`` is empty (no signal to summarize).
    """
    if not values:
        return None
    if metric == "avg":
        return float(statistics.fmean(values))
    if metric == "max":
        return float(max(values))
    if metric == "p95":
        if len(values) < 2:
            return float(values[0])
        # statistics.quantiles(n=20) returns 19 cut points; index 18 is
        # the 95th percentile boundary.
        cuts = statistics.quantiles(values, n=20)
        return float(cuts[18])
    raise ValueError(
        f"metric must be one of 'avg', 'max', 'p95' (got {metric!r})"
    )


def _fetch_recording(recording_id: int, db_path: Optional[str]) -> Optional[dict[str, Any]]:
    """Return the ``sensor_recordings`` row as a dict (or None if absent)."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM sensor_recordings WHERE id = ?",
            (recording_id,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def _fetch_vehicle(vehicle_id: int, db_path: Optional[str]) -> Optional[dict[str, Any]]:
    """Return the ``vehicles`` row as a dict (or None if absent)."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM vehicles WHERE id = ?",
            (vehicle_id,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def _recording_values(
    recording_id: int, pid_hex: str, db_path: Optional[str]
) -> tuple[list[float], str]:
    """Fetch non-null sample values + first-seen unit for one recording/PID.

    Returns ``(values, unit)`` where ``unit`` is the first non-empty
    ``sensor_samples.unit`` encountered (empty string otherwise). Null
    values are filtered out — they represent timeout / unsupported cells
    from Phase 141's streamer and would poison any percentile.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT value, unit FROM sensor_samples "
            "WHERE recording_id = ? AND pid_hex = ? COLLATE NOCASE "
            "AND value IS NOT NULL",
            (recording_id, pid_hex),
        ).fetchall()
    values = [float(r["value"]) for r in rows]
    unit = ""
    for r in rows:
        u = r["unit"]
        if u:
            unit = str(u)
            break
    return values, unit


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_peer_recordings(
    vehicle: dict[str, Any],
    cohort_filter: str,
    db_path: Optional[str] = None,
    *,
    target_recording_id: Optional[int] = None,
    target_protocol_name: Optional[str] = None,
    fleet_id: Optional[int] = None,
) -> list[int]:
    """Return the IDs of peer recordings matching ``cohort_filter``.

    Parameters
    ----------
    vehicle:
        Target bike row (make / model / year). Only the keys we care
        about are consulted, so a synthetic dict from the CLI's
        direct-args mode works the same as a ``vehicles`` row.
    cohort_filter:
        One of ``"same-model"`` / ``"strict"`` / ``"fleet"``.
    db_path:
        Optional override; defaults to the project DB.
    target_recording_id:
        If given, excluded from the result so a recording never
        compares against itself.
    target_protocol_name:
        Required when ``cohort_filter == "strict"`` — used to keep
        K-line recordings from polluting a CAN cohort.
    fleet_id:
        Reserved for Phase 150 (fleet cohort scoping). Currently
        unused; present on the signature so the CLI call site is
        stable across phases.

    Returns
    -------
    list[int]
        Up to :data:`COHORT_CAP` recording IDs. Returns
        ``[FLEET_UNAVAILABLE]`` sentinel list when
        ``cohort_filter == "fleet"`` and Phase 150's table is absent.
    """
    if cohort_filter not in ("same-model", "strict", "fleet"):
        raise ValueError(
            f"cohort_filter must be same-model/strict/fleet "
            f"(got {cohort_filter!r})"
        )

    if cohort_filter == "fleet" and not _fleet_tables_available(db_path):
        # Sentinel result so the CLI can render a yellow panel without
        # having to re-run the feature-detect itself.
        return [FLEET_UNAVAILABLE]  # type: ignore[list-item]

    make = (vehicle.get("make") or "").strip()
    model = (vehicle.get("model") or "").strip()
    year = vehicle.get("year")

    if not make or not model or year is None:
        # Degenerate vehicle — nothing we can match against.
        return []

    clauses: list[str] = [
        "r.stopped_at IS NOT NULL",
        "v.make = ? COLLATE NOCASE",
        "v.model = ? COLLATE NOCASE",
    ]
    params: list[Any] = [make, model]

    if cohort_filter == "same-model":
        # ±1 year window keeps "my 2015 Road Glide" compatible with
        # 2014/2016 recordings — same platform, indistinguishable wear.
        clauses.append("v.year BETWEEN ? AND ?")
        params.extend([int(year) - 1, int(year) + 1])
    elif cohort_filter == "strict":
        clauses.append("v.year = ?")
        params.append(int(year))
        if target_protocol_name:
            clauses.append("r.protocol_name = ? COLLATE NOCASE")
            params.append(target_protocol_name)
    elif cohort_filter == "fleet":
        # Phase 150 will add: INNER JOIN fleet_memberships fm ON ...
        # For now, behave like same-model with strict year (safer default
        # than opening the cohort wide) so the caller gets a usable peer
        # set even without fleet tagging. Tests exercise the sentinel
        # path above.
        clauses.append("v.year = ?")
        params.append(int(year))

    if target_recording_id is not None:
        clauses.append("r.id != ?")
        params.append(int(target_recording_id))

    sql = (
        "SELECT r.id FROM sensor_recordings r "
        "JOIN vehicles v ON v.id = r.vehicle_id "
        f"WHERE {' AND '.join(clauses)} "
        "ORDER BY r.started_at DESC "
        f"LIMIT {COHORT_CAP}"
    )
    with get_connection(db_path) as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [int(r["id"]) for r in rows]


def compute_peer_stats(
    peer_ids: list[int],
    pid_hex: Any,
    metric: str = "avg",
    db_path: Optional[str] = None,
) -> PeerStats:
    """Compute cross-cohort percentiles for one PID.

    Flow:

    1. Canonicalize ``pid_hex``.
    2. For each peer recording, pull non-null sample values for this
       PID (:func:`_recording_values`) and reduce to a single metric
       value via :func:`_metric_reducer`.
    3. Collect the surviving per-recording summaries + the set of
       distinct ``vehicle_id`` values (fetched alongside so we can
       report ``distinct_bikes``).
    4. Compute p25 / p50 / p75 / p95 across per-recording summaries
       using :func:`statistics.median` and :func:`statistics.quantiles`.
       Very short cohorts (``n == 1``) collapse all percentiles to the
       single value; empty cohorts yield all-``None`` percentiles.
    5. Propagate the first non-empty unit seen.

    Returns a :class:`PeerStats` even for empty / degenerate cohorts —
    check :attr:`PeerStats.cohort_size` before trusting the percentile
    fields.
    """
    canonical_pid = _normalize_pid_hex(pid_hex)

    if metric not in ("avg", "max", "p95"):
        raise ValueError(
            f"metric must be one of avg/max/p95 (got {metric!r})"
        )

    per_recording: list[float] = []
    distinct_vehicle_ids: set[int] = set()
    unit: str = ""

    for rid in peer_ids:
        values, rec_unit = _recording_values(rid, canonical_pid, db_path)
        if not values:
            continue
        summary = _metric_reducer(values, metric)
        if summary is None:
            continue
        per_recording.append(summary)
        if not unit and rec_unit:
            unit = rec_unit
        # Pull vehicle_id so we can report distinct-bike count.
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT vehicle_id FROM sensor_recordings WHERE id = ?",
                (rid,),
            ).fetchone()
        if row is not None and row["vehicle_id"] is not None:
            distinct_vehicle_ids.add(int(row["vehicle_id"]))

    cohort_size = len(per_recording)
    if cohort_size == 0:
        return PeerStats(
            pid_hex=canonical_pid,
            cohort_size=0,
            distinct_bikes=0,
            p25=None,
            p50=None,
            p75=None,
            p95=None,
            unit=unit,
            metric=metric,
            warning=None,
        )

    if cohort_size == 1:
        only = float(per_recording[0])
        return PeerStats(
            pid_hex=canonical_pid,
            cohort_size=1,
            distinct_bikes=len(distinct_vehicle_ids),
            p25=only,
            p50=only,
            p75=only,
            p95=only,
            unit=unit,
            metric=metric,
            warning=None,
        )

    p50 = float(statistics.median(per_recording))
    quartiles = statistics.quantiles(per_recording, n=4, method="inclusive")
    p25 = float(quartiles[0])
    p75 = float(quartiles[2])
    # n=20 needs ≥ 2 data points; guaranteed by the cohort_size==1 guard
    # above. For n=2/3 the 95th cut point still falls between the two
    # largest values under the default exclusive method.
    vingts = statistics.quantiles(per_recording, n=20)
    p95 = float(vingts[18])

    return PeerStats(
        pid_hex=canonical_pid,
        cohort_size=cohort_size,
        distinct_bikes=len(distinct_vehicle_ids),
        p25=p25,
        p50=p50,
        p75=p75,
        p95=p95,
        unit=unit,
        metric=metric,
        warning=None,
    )


def compare_against_peers(
    vehicle_recording_id: int,
    pid_hex: Any,
    *,
    cohort_filter: str = "same-model",
    metric: str = "avg",
    peers_min: int = 5,
    db_path: Optional[str] = None,
) -> PeerComparison:
    """Full pipeline: target → cohort → peer stats → bucket.

    Raises
    ------
    ValueError
        When the target recording does not exist, or has no
        ``vehicle_id`` (orphaned / dealer-lot recording).

    Returns
    -------
    PeerComparison
        ``cohort.warning`` carries the reason when ``cohort_size <
        peers_min``. ``bucket`` / ``anomaly_flag`` are meaningful only
        when ``cohort.cohort_size >= peers_min`` AND ``target_summary``
        is non-``None``.
    """
    canonical_pid = _normalize_pid_hex(pid_hex)

    recording = _fetch_recording(vehicle_recording_id, db_path)
    if recording is None:
        raise ValueError(
            f"Recording #{vehicle_recording_id} not found"
        )
    vehicle_id = recording.get("vehicle_id")
    if vehicle_id is None:
        raise ValueError(
            f"Recording #{vehicle_recording_id} is orphaned "
            "(vehicle_id is NULL — dealer-lot scenario). "
            "Link it to a garage bike first via the garage tools."
        )

    vehicle = _fetch_vehicle(int(vehicle_id), db_path)
    if vehicle is None:
        raise ValueError(
            f"Recording #{vehicle_recording_id} references missing "
            f"vehicle #{vehicle_id}"
        )

    # --- Target summary ---
    target_values, _target_unit = _recording_values(
        vehicle_recording_id, canonical_pid, db_path,
    )
    target_summary = _metric_reducer(target_values, metric)

    # --- Cohort discovery ---
    target_protocol = recording.get("protocol_name")
    peer_ids = find_peer_recordings(
        vehicle,
        cohort_filter=cohort_filter,
        db_path=db_path,
        target_recording_id=vehicle_recording_id,
        target_protocol_name=target_protocol,
    )

    # Fleet-cohort sentinel — surface via an explicit warning so the CLI
    # can branch on it without re-feature-detecting.
    if peer_ids == [FLEET_UNAVAILABLE]:
        cohort = PeerStats(
            pid_hex=canonical_pid,
            cohort_size=0,
            distinct_bikes=0,
            p25=None, p50=None, p75=None, p95=None,
            unit="",
            metric=metric,
            warning="Phase 150 required: fleet_memberships table is missing.",
        )
        return PeerComparison(
            vehicle_recording_id=vehicle_recording_id,
            pid_hex=canonical_pid,
            pid_name=_pid_display_name(canonical_pid),
            target_summary=target_summary,
            cohort=cohort,
            bucket=None,
            anomaly_flag=False,
            cohort_filter=cohort_filter,
        )

    cohort = compute_peer_stats(peer_ids, canonical_pid, metric, db_path)

    # --- Guard: below peers_min ---
    if cohort.cohort_size < peers_min:
        warned = PeerStats(
            pid_hex=cohort.pid_hex,
            cohort_size=cohort.cohort_size,
            distinct_bikes=cohort.distinct_bikes,
            p25=cohort.p25, p50=cohort.p50,
            p75=cohort.p75, p95=cohort.p95,
            unit=cohort.unit,
            metric=cohort.metric,
            warning=(
                f"Insufficient cohort — {cohort.cohort_size} peer "
                f"recording(s) found, minimum {peers_min}. Widen "
                "--cohort or add more recordings before trusting "
                "the percentiles."
            ),
        )
        return PeerComparison(
            vehicle_recording_id=vehicle_recording_id,
            pid_hex=canonical_pid,
            pid_name=_pid_display_name(canonical_pid),
            target_summary=target_summary,
            cohort=warned,
            bucket=None,
            anomaly_flag=False,
            cohort_filter=cohort_filter,
        )

    # --- Bucket + anomaly flag ---
    bucket: Optional[str] = None
    anomaly: bool = False
    if (
        target_summary is not None
        and cohort.p25 is not None
        and cohort.p50 is not None
        and cohort.p75 is not None
        and cohort.p95 is not None
    ):
        bucket = _bucket(
            target_summary, cohort.p25, cohort.p50, cohort.p75, cohort.p95,
        )
        anomaly = bucket in ("<p25", ">=p95")

    return PeerComparison(
        vehicle_recording_id=vehicle_recording_id,
        pid_hex=canonical_pid,
        pid_name=_pid_display_name(canonical_pid),
        target_summary=target_summary,
        cohort=cohort,
        bucket=bucket,
        anomaly_flag=anomaly,
        cohort_filter=cohort_filter,
    )


__all__ = [
    "PeerStats",
    "PeerComparison",
    "COHORT_CAP",
    "FLEET_UNAVAILABLE",
    "find_peer_recordings",
    "compute_peer_stats",
    "compare_against_peers",
]
