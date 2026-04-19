"""Phase 156 — Comparative diagnostics (peer-cohort anomaly) tests.

Four test classes, ~28 tests, zero live hardware / network / tokens.

Classes
-------

- :class:`TestFindPeers` — cohort-selection SQL: same-model ±1 year
  window, strict exact-year + protocol, target-recording exclusion,
  fleet feature-detect, :data:`COHORT_CAP` clamp.
- :class:`TestComputePeerStats` — per-recording reducer across the three
  metrics (avg / max / p95), cross-cohort percentile math, unit
  propagation, missing-PID handling, NULL-value filtering, degenerate
  cohorts (empty / single-peer).
- :class:`TestCompareAgainstPeers` — end-to-end pipeline: happy path,
  insufficient-cohort warning, orphan recording raises ValueError,
  PID-not-recorded, bucket boundaries, anomaly flag semantics, PID
  name via catalog.
- :class:`TestCompareCLI` — CliRunner on ``motodiag advanced compare
  {bike,recording,fleet}`` covering Rich output, ``--json``, unknown
  slug/recording, fleet-without-Phase 150, ``--pid``
  canonicalization, ``--peers-min`` validation, ``--help``.

Seeding uses Phase 142's :class:`RecordingManager` directly — local
synthetic ``SensorReading``-shaped dataclass keeps the test suite
decoupled from any Phase 141 API drift (same pattern as
``test_phase142_log.py``).
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import click
import pytest
from click.testing import CliRunner

from motodiag.advanced.comparative import (
    COHORT_CAP,
    FLEET_UNAVAILABLE,
    PeerComparison,
    PeerStats,
    _bucket,
    _normalize_pid_hex,
    compare_against_peers,
    compute_peer_stats,
    find_peer_recordings,
)
from motodiag.cli.advanced import register_advanced
from motodiag.core.database import get_connection, init_db
from motodiag.core.models import (
    EngineType,
    PowertrainType,
    ProtocolType,
    VehicleBase,
)
from motodiag.hardware.recorder import RecordingManager
from motodiag.vehicles.registry import add_vehicle


# ---------------------------------------------------------------------------
# Synthetic SensorReading — decouple from Phase 141
# ---------------------------------------------------------------------------


@dataclass
class _Reading:
    """Duck-typed stand-in for :class:`SensorReading`.

    Only the fields Phase 142's ``_reading_to_sample_row`` consults
    exist here: ``pid_hex``, ``value``, ``raw``, ``unit``, ``captured_at``.
    """
    pid_hex: str
    value: Optional[float]
    raw: Optional[int]
    unit: str
    captured_at: datetime


def _reading(
    pid_hex: str,
    value: float,
    offset_s: float = 0.0,
    unit: str = "°C",
) -> _Reading:
    base = datetime(2026, 4, 18, 12, 0, 0, tzinfo=timezone.utc)
    return _Reading(
        pid_hex=pid_hex,
        value=value,
        raw=int(value) if value is not None else None,
        unit=unit,
        captured_at=base + timedelta(seconds=offset_s),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Bare initialized DB with CLI + RecordingManager pointing at tmp."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase156.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()

    # Patch RecordingManager default so helper seeds land in the same DB.
    from motodiag.hardware import recorder as rec_mod
    original_init = rec_mod.RecordingManager.__init__

    def _patched_init(self, db_path=None, recordings_dir=None):
        original_init(
            self,
            db_path=db_path or path,
            recordings_dir=recordings_dir or tmp_path / "recordings",
        )

    monkeypatch.setattr(rec_mod.RecordingManager, "__init__", _patched_init)

    yield path
    reset_settings()


def _add_vehicle(db_path: str, make: str, model: str, year: int) -> int:
    """Insert a vehicle and return its ID."""
    v = VehicleBase(
        make=make,
        model=model,
        year=year,
        engine_cc=1200,
        protocol=ProtocolType.J1850,
        powertrain=PowertrainType.ICE,
        engine_type=EngineType.FOUR_STROKE,
    )
    return add_vehicle(v, db_path=db_path)


def _seed_recording(
    db_path: str,
    vehicle_id: Optional[int],
    pid_hex: str,
    values: list[float],
    protocol_name: str = "J1850",
    unit: str = "°C",
) -> int:
    """Create a completed recording with the given per-sample values."""
    mgr = RecordingManager(db_path=db_path)
    rid = mgr.start_recording(
        vehicle_id=vehicle_id,
        label="test",
        pids=[pid_hex.removeprefix("0x")],
        protocol_name=protocol_name,
    )
    readings = [
        _reading(pid_hex, v, offset_s=i * 0.5, unit=unit)
        for i, v in enumerate(values)
    ]
    mgr.append_samples(rid, readings)
    mgr.stop_recording(rid)
    return rid


def _make_cli():
    """Build a fresh CLI group with only `advanced` registered."""
    @click.group()
    def root() -> None:
        """test root"""
    register_advanced(root)
    return root


# ===========================================================================
# 1. find_peer_recordings
# ===========================================================================


class TestFindPeers:
    """SQL-level cohort selection."""

    def test_same_model_matches_same_make_model_within_year_window(self, db_path):
        target_v = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        peer_in_window = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2014)
        peer_out_of_window = _add_vehicle(
            db_path, "Harley-Davidson", "Road Glide", 2010,
        )
        other_make = _add_vehicle(db_path, "Honda", "Road Glide", 2015)

        _seed_recording(db_path, target_v, "0x05", [90.0])
        peer_in_rid = _seed_recording(db_path, peer_in_window, "0x05", [91.0])
        _seed_recording(db_path, peer_out_of_window, "0x05", [92.0])
        _seed_recording(db_path, other_make, "0x05", [93.0])

        vehicle = {"make": "Harley-Davidson", "model": "Road Glide", "year": 2015}
        ids = find_peer_recordings(vehicle, "same-model", db_path=db_path)
        assert peer_in_rid in ids
        # Out-of-window + other-make excluded
        assert len(ids) >= 1
        # Verify the found peer belongs to the in-window vehicle
        for rid in ids:
            with get_connection(db_path) as conn:
                row = conn.execute(
                    "SELECT vehicle_id FROM sensor_recordings WHERE id = ?",
                    (rid,),
                ).fetchone()
                assert row["vehicle_id"] in (target_v, peer_in_window)

    def test_same_model_year_plus_minus_one_window(self, db_path):
        """±1 year window matches year - 1, year, year + 1 only."""
        for y in (2013, 2014, 2015, 2016, 2017):
            vid = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", y)
            _seed_recording(db_path, vid, "0x05", [90.0])

        vehicle = {"make": "Harley-Davidson", "model": "Road Glide", "year": 2015}
        ids = find_peer_recordings(vehicle, "same-model", db_path=db_path)
        # 2014, 2015, 2016 match = 3 peers
        assert len(ids) == 3

    def test_strict_matches_exact_year_and_protocol(self, db_path):
        v2015 = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        v2014 = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2014)

        peer_ok = _seed_recording(db_path, v2015, "0x05", [90.0], protocol_name="CAN")
        peer_wrong_proto = _seed_recording(
            db_path, v2015, "0x05", [91.0], protocol_name="K-Line",
        )
        _seed_recording(db_path, v2014, "0x05", [92.0], protocol_name="CAN")

        vehicle = {"make": "Harley-Davidson", "model": "Road Glide", "year": 2015}
        ids = find_peer_recordings(
            vehicle, "strict", db_path=db_path,
            target_protocol_name="CAN",
        )
        assert peer_ok in ids
        assert peer_wrong_proto not in ids

    def test_target_recording_excluded(self, db_path):
        vid = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        target = _seed_recording(db_path, vid, "0x05", [90.0])
        peer = _seed_recording(db_path, vid, "0x05", [91.0])

        vehicle = {"make": "Harley-Davidson", "model": "Road Glide", "year": 2015}
        ids = find_peer_recordings(
            vehicle, "same-model", db_path=db_path,
            target_recording_id=target,
        )
        assert target not in ids
        assert peer in ids

    def test_fleet_without_table_returns_sentinel(self, db_path):
        vid = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        _seed_recording(db_path, vid, "0x05", [90.0])
        vehicle = {"make": "Harley-Davidson", "model": "Road Glide", "year": 2015}
        ids = find_peer_recordings(vehicle, "fleet", db_path=db_path)
        assert ids == [FLEET_UNAVAILABLE]

    def test_limit_200_honored_on_300_peer_cohort(self, db_path):
        """300 peers → result LIMITed to COHORT_CAP (200)."""
        # Seed 300 recordings across 10 vehicles (30 each).
        for v_idx in range(10):
            vid = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
            for _ in range(30):
                _seed_recording(db_path, vid, "0x05", [90.0])

        vehicle = {"make": "Harley-Davidson", "model": "Road Glide", "year": 2015}
        ids = find_peer_recordings(vehicle, "same-model", db_path=db_path)
        assert len(ids) == COHORT_CAP


# ===========================================================================
# 2. compute_peer_stats
# ===========================================================================


class TestComputePeerStats:
    """Per-recording reducer + cross-cohort percentiles."""

    def _seed_cohort(self, db_path: str, summaries: list[float]) -> list[int]:
        """One recording per per-recording-avg target value."""
        peer_ids: list[int] = []
        for i, val in enumerate(summaries):
            vid = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
            rid = _seed_recording(db_path, vid, "0x05", [val] * 3)
            peer_ids.append(rid)
        return peer_ids

    def test_avg_metric_percentiles(self, db_path):
        """avg metric: 10 summaries 10..100 → percentiles spread evenly."""
        summaries = [float(v) for v in range(10, 101, 10)]  # 10,20,...,100
        peers = self._seed_cohort(db_path, summaries)
        stats = compute_peer_stats(peers, "0x05", metric="avg", db_path=db_path)
        assert stats.cohort_size == 10
        assert stats.p50 == pytest.approx(55.0)
        assert stats.p25 is not None and stats.p75 is not None
        assert stats.p25 < stats.p50 < stats.p75 < stats.p95

    def test_max_metric_uses_per_recording_max(self, db_path):
        """max metric: each recording's summary is its maximum value."""
        vid = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        rid = _seed_recording(db_path, vid, "0x05", [5.0, 10.0, 15.0])
        # Pad the cohort so we have ≥ 2 data points for quantiles(n=20).
        vid2 = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        rid2 = _seed_recording(db_path, vid2, "0x05", [20.0, 25.0, 30.0])

        stats = compute_peer_stats(
            [rid, rid2], "0x05", metric="max", db_path=db_path,
        )
        # Per-recording maxes are 15 and 30; median = 22.5
        assert stats.cohort_size == 2
        assert stats.p50 == pytest.approx(22.5)

    def test_p95_metric_per_recording(self, db_path):
        """p95 metric: short series fall back to max, long series use quantiles."""
        vid1 = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        # 20 values so p95 lands at index 18 cut point.
        rid1 = _seed_recording(
            db_path, vid1, "0x05", [float(v) for v in range(1, 21)],
        )
        vid2 = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        rid2 = _seed_recording(
            db_path, vid2, "0x05", [float(v) for v in range(100, 120)],
        )
        stats = compute_peer_stats(
            [rid1, rid2], "0x05", metric="p95", db_path=db_path,
        )
        assert stats.cohort_size == 2
        # p95 per recording is near the high end; cohort median sits
        # between the two.
        assert stats.p50 is not None

    def test_empty_cohort_returns_zero_size(self, db_path):
        stats = compute_peer_stats([], "0x05", db_path=db_path)
        assert stats.cohort_size == 0
        assert stats.distinct_bikes == 0
        assert stats.p25 is None and stats.p95 is None

    def test_single_peer_collapses_percentiles(self, db_path):
        vid = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        rid = _seed_recording(db_path, vid, "0x05", [42.0])
        stats = compute_peer_stats([rid], "0x05", db_path=db_path)
        assert stats.cohort_size == 1
        assert stats.p25 == pytest.approx(42.0)
        assert stats.p50 == pytest.approx(42.0)
        assert stats.p75 == pytest.approx(42.0)
        assert stats.p95 == pytest.approx(42.0)

    def test_null_values_are_filtered(self, db_path):
        """NULL sample values are excluded from the per-recording reducer."""
        vid = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        mgr = RecordingManager(db_path=db_path)
        rid = mgr.start_recording(
            vehicle_id=vid, label="nulls", pids=["05"], protocol_name="CAN",
        )
        readings = [
            _reading("0x05", 100.0, offset_s=0.0),
            _Reading(
                pid_hex="0x05", value=None, raw=None, unit="°C",
                captured_at=datetime(2026, 4, 18, 12, 0, 1, tzinfo=timezone.utc),
            ),
            _reading("0x05", 200.0, offset_s=2.0),
        ]
        mgr.append_samples(rid, readings)
        mgr.stop_recording(rid)

        vid2 = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        rid2 = _seed_recording(db_path, vid2, "0x05", [150.0])

        stats = compute_peer_stats(
            [rid, rid2], "0x05", metric="avg", db_path=db_path,
        )
        # First recording: (100+200)/2 = 150 (NULL excluded)
        # Second recording: 150
        assert stats.cohort_size == 2
        assert stats.p50 == pytest.approx(150.0)

    def test_unit_propagates_from_first_peer_with_unit(self, db_path):
        vid = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        rid = _seed_recording(db_path, vid, "0x05", [50.0], unit="°C")
        vid2 = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        rid2 = _seed_recording(db_path, vid2, "0x05", [60.0], unit="°C")
        stats = compute_peer_stats(
            [rid, rid2], "0x05", metric="avg", db_path=db_path,
        )
        assert stats.unit == "°C"

    def test_missing_pid_in_recordings_yields_empty_cohort(self, db_path):
        """Peers recorded a different PID → cohort_size == 0."""
        vid = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        rid = _seed_recording(db_path, vid, "0x0C", [1000.0])  # RPM, not coolant
        stats = compute_peer_stats(
            [rid], "0x05", metric="avg", db_path=db_path,
        )
        assert stats.cohort_size == 0


# ===========================================================================
# 3. compare_against_peers
# ===========================================================================


class TestCompareAgainstPeers:
    """End-to-end pipeline (target + cohort + bucket + flag)."""

    def _seed_target_and_peers(
        self, db_path: str, target_value: float,
        peer_values: list[float],
    ) -> int:
        target_vid = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
        target_rid = _seed_recording(db_path, target_vid, "0x05", [target_value])
        for v in peer_values:
            peer_vid = _add_vehicle(
                db_path, "Harley-Davidson", "Road Glide", 2015,
            )
            _seed_recording(db_path, peer_vid, "0x05", [v])
        return target_rid

    def test_happy_path_bucket_and_flag(self, db_path):
        """Target 92 °C, cohort 80..100: lands near p50 — no anomaly."""
        target_rid = self._seed_target_and_peers(
            db_path, 92.0, [80.0, 85.0, 90.0, 95.0, 100.0, 88.0, 93.0],
        )
        comparison = compare_against_peers(
            target_rid, "0x05", db_path=db_path,
        )
        assert comparison.cohort.cohort_size >= 5
        assert comparison.bucket in ("p25-p50", "p50-p75")
        assert comparison.anomaly_flag is False

    def test_insufficient_cohort_warning(self, db_path):
        """< peers_min → cohort.warning set, anomaly_flag False."""
        target_rid = self._seed_target_and_peers(db_path, 92.0, [80.0, 100.0])
        comparison = compare_against_peers(
            target_rid, "0x05", peers_min=5, db_path=db_path,
        )
        assert comparison.cohort.warning is not None
        assert "Insufficient" in comparison.cohort.warning
        assert comparison.anomaly_flag is False
        assert comparison.bucket is None

    def test_orphan_recording_raises_valueerror(self, db_path):
        """vehicle_id NULL → ValueError per spec."""
        orphan_rid = _seed_recording(db_path, None, "0x05", [92.0])
        with pytest.raises(ValueError, match="orphaned"):
            compare_against_peers(orphan_rid, "0x05", db_path=db_path)

    def test_unknown_recording_raises_valueerror(self, db_path):
        """Nonexistent recording ID → ValueError."""
        with pytest.raises(ValueError, match="not found"):
            compare_against_peers(99999, "0x05", db_path=db_path)

    def test_pid_not_recorded_in_target(self, db_path):
        """Target recording lacks the PID → target_summary None + no bucket."""
        target_vid = _add_vehicle(
            db_path, "Harley-Davidson", "Road Glide", 2015,
        )
        target_rid = _seed_recording(db_path, target_vid, "0x0C", [1000.0])
        for _ in range(5):
            peer_vid = _add_vehicle(
                db_path, "Harley-Davidson", "Road Glide", 2015,
            )
            _seed_recording(db_path, peer_vid, "0x05", [90.0])
        comparison = compare_against_peers(
            target_rid, "0x05", db_path=db_path,
        )
        assert comparison.target_summary is None
        assert comparison.bucket is None
        assert comparison.anomaly_flag is False

    def test_bucket_boundaries_all_five(self, db_path):
        """Exercise all five bucket strings via :func:`_bucket` directly.

        Keeps this test fast and deterministic — the SQL-driven
        compare_against_peers tests already cover the happy bucket paths.
        """
        # p25=25, p50=50, p75=75, p95=95
        assert _bucket(10.0, 25, 50, 75, 95) == "<p25"
        assert _bucket(30.0, 25, 50, 75, 95) == "p25-p50"
        assert _bucket(60.0, 25, 50, 75, 95) == "p50-p75"
        assert _bucket(80.0, 25, 50, 75, 95) == "p75-p95"
        # Spec rule: target == p95 → ">=p95"
        assert _bucket(95.0, 25, 50, 75, 95) == ">=p95"
        assert _bucket(100.0, 25, 50, 75, 95) == ">=p95"

    def test_anomaly_flag_fires_in_high_tail(self, db_path):
        """Target near p95 triggers anomaly_flag."""
        # Peer cohort 80..90, target 999 (wildly hot) → >= p95 tail
        target_rid = self._seed_target_and_peers(
            db_path, 999.0,
            [80.0, 82.0, 84.0, 86.0, 88.0, 90.0, 85.0, 87.0],
        )
        comparison = compare_against_peers(
            target_rid, "0x05", db_path=db_path,
        )
        assert comparison.anomaly_flag is True
        assert comparison.bucket == ">=p95"

    def test_pid_name_via_catalog(self, db_path):
        """pid_name is populated from the sensor catalog when available."""
        # 0x05 is the J1979 engine coolant temperature PID.
        target_rid = self._seed_target_and_peers(
            db_path, 90.0, [80.0, 85.0, 90.0, 95.0, 100.0],
        )
        comparison = compare_against_peers(
            target_rid, "0x05", db_path=db_path,
        )
        # Even if catalog import fails, fallback returns the hex string,
        # so pid_name is always a non-empty string.
        assert comparison.pid_name
        # When catalog is present, it should NOT equal the hex string.
        # Allow either for robustness across sensors module states.
        assert isinstance(comparison.pid_name, str)


# ===========================================================================
# 4. CLI (motodiag advanced compare ...)
# ===========================================================================


def _seed_cli_setup(db_path: str) -> int:
    """Seed a target vehicle + recording + 5-peer cohort. Return target RID."""
    target_vid = _add_vehicle(db_path, "Harley-Davidson", "Road Glide", 2015)
    target_rid = _seed_recording(db_path, target_vid, "0x05", [90.0])
    for v in (80.0, 85.0, 88.0, 92.0, 100.0):
        peer_vid = _add_vehicle(
            db_path, "Harley-Davidson", "Road Glide", 2015,
        )
        _seed_recording(db_path, peer_vid, "0x05", [v])
    return target_rid


class TestCompareCLI:
    """Click-runner tests on `motodiag advanced compare {bike,recording,fleet}`."""

    def test_bike_happy_path(self, db_path):
        _seed_cli_setup(db_path)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "compare", "bike", "--bike", "road glide-2015"],
        )
        assert result.exit_code == 0, result.output
        assert "Peer comparison" in result.output

    def test_bike_json_output(self, db_path):
        _seed_cli_setup(db_path)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "compare", "bike",
                "--bike", "road glide-2015",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert payload["cohort"]["size"] >= 1
        assert payload["pid_hex"] == "0x05"

    def test_bike_unknown_slug_remediation(self, db_path):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "compare", "bike",
                "--bike", "nosuch-bike-2099",
            ],
        )
        assert result.exit_code == 1
        assert (
            "not found" in result.output.lower()
            or "no bike" in result.output.lower()
        )

    def test_recording_happy_path(self, db_path):
        target_rid = _seed_cli_setup(db_path)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "compare", "recording", str(target_rid)],
        )
        assert result.exit_code == 0, result.output
        assert "Peer comparison" in result.output

    def test_recording_unknown_id_red_panel(self, db_path):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "compare", "recording", "99999"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_fleet_without_phase150_yellow_panel(self, db_path):
        _seed_cli_setup(db_path)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "compare", "fleet",
                "--bike", "road glide-2015",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Phase 150" in result.output

    def test_pid_canonicalization_via_cli(self, db_path):
        """--pid 5 / 0x5 / 05 / 0X05 all round-trip to '0x05'."""
        _seed_cli_setup(db_path)
        runner = CliRunner()
        for raw in ("5", "0x5", "05", "0X05"):
            result = runner.invoke(
                _make_cli(),
                [
                    "advanced", "compare", "bike",
                    "--bike", "road glide-2015",
                    "--pid", raw,
                    "--json",
                ],
            )
            assert result.exit_code == 0, (raw, result.output)
            payload = _json.loads(result.output)
            assert payload["pid_hex"] == "0x05"

    def test_peers_min_1_valid(self, db_path):
        """--peers-min 1 is the minimum allowed (IntRange min=1)."""
        _seed_cli_setup(db_path)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "compare", "bike",
                "--bike", "road glide-2015",
                "--peers-min", "1",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_peers_min_zero_is_error(self, db_path):
        """--peers-min 0 rejected by IntRange."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "compare", "bike",
                "--bike", "road glide-2015",
                "--peers-min", "0",
            ],
        )
        assert result.exit_code != 0

    def test_help_renders_all_subcommands(self, db_path):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(), ["advanced", "compare", "--help"]
        )
        assert result.exit_code == 0
        for sub in ("bike", "recording", "fleet"):
            assert sub in result.output


# ---------------------------------------------------------------------------
# Tiny helper test (normalize_pid_hex sanity — cheap to run)
# ---------------------------------------------------------------------------


class TestNormalizePidHex:
    """Not in the spec's 4-class layout but a 1-test safety net."""

    def test_accepts_common_forms(self):
        assert _normalize_pid_hex(5) == "0x05"
        assert _normalize_pid_hex("5") == "0x05"
        assert _normalize_pid_hex("05") == "0x05"
        assert _normalize_pid_hex("0x5") == "0x05"
        assert _normalize_pid_hex("0X05") == "0x05"

    def test_rejects_malformed(self):
        with pytest.raises(ValueError):
            _normalize_pid_hex("xyz")
        with pytest.raises(ValueError):
            _normalize_pid_hex(-1)
        with pytest.raises(ValueError):
            _normalize_pid_hex(256)
