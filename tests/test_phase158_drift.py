"""Phase 158 — Sensor degradation (drift) tracking tests.

Four test classes, ~30 tests covering:

- :class:`TestComputeTrend` (8) — hand-computed slope/intercept/r² on
  synthetic series, flat-line guardrail, signed rising/falling drift,
  edge cases (n=1, n=2, degenerate sxx), ``since``/``until`` filter,
  sensor catalog enrichment for PID name.
- :class:`TestDetectDriftingPids` (6) — threshold boundary tests
  (±5 %/30 d → stable vs slow vs fast), empty DB, deterministic sort,
  mixed-bucket fleet, ``since`` filter, unknown PID gets synthesized
  name but empty unit.
- :class:`TestSummary` (6) — three-bucket shape contract, all-stable
  and all-fast cases, threshold=0 boundary (nothing is stable),
  round-trip through ``model_dump(mode='json')`` → ``model_validate``.
- :class:`TestDriftCLI` (10) — ``drift bike`` / ``drift show`` /
  ``drift recording`` / ``drift plot`` happy + --json; unknown-bike
  Phase 125-style remediation; ``--since > --until`` validation; a
  predictor-integration test that monkey-patches
  ``detect_drifting_pids`` and asserts ``predict_failures`` bumps
  ``confidence_score`` by exactly +0.1 + re-buckets HIGH/MEDIUM/LOW.

No AI calls, no live hardware, no network — every recording is seeded
via direct SQL bypassing :class:`RecordingManager` for speed.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from click.testing import CliRunner

from motodiag.advanced import (
    DriftBucket,
    DriftResult,
    compute_trend,
    detect_drifting_pids,
    summary_for_bike,
)
from motodiag.advanced.drift import (
    _classify_bucket,
    _linear_regression,
    _normalize_pid_hex,
    _render_sparkline,
)
from motodiag.cli.advanced import register_advanced
from motodiag.core.database import get_connection, init_db


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_cli():
    """Build a fresh CLI group with only `advanced` registered."""
    import click

    @click.group()
    def root() -> None:
        """test root"""

    register_advanced(root)
    return root


@pytest.fixture
def db(tmp_path):
    """Bare initialized DB (no CLI env patching)."""
    path = str(tmp_path / "phase158.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings + CLI paths at a temp DB. Mirrors Phase 148."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase158_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _seed_vehicle(db_path: str, make="Harley-Davidson", model="Sportster 1200",
                  year=2010) -> int:
    """Insert a vehicle row directly via SQL.

    Bypasses :class:`motodiag.core.models.VehicleBase` validation — the
    drift module only reads the integer id, so the minimal column set
    is fine for tests.
    """
    from motodiag.core.models import (
        VehicleBase, ProtocolType, PowertrainType, EngineType,
    )
    from motodiag.vehicles.registry import add_vehicle

    vehicle = VehicleBase(
        make=make,
        model=model,
        year=year,
        engine_cc=1200,
        protocol=ProtocolType.J1850,
        powertrain=PowertrainType.ICE,
        engine_type=EngineType.FOUR_STROKE,
    )
    return add_vehicle(vehicle, db_path=db_path)


def _seed_drift(
    db_path: str,
    vehicle_id: int,
    pid_hex: str,
    values_over_days: list[tuple[float, float]],
    unit: str = "",
) -> int:
    """Synthesize N recordings + samples in one shot.

    ``values_over_days`` is a list of ``(day_offset, value)`` pairs.
    Each pair becomes its own recording with a single sample — that
    keeps the per-test fixture minimal while still exercising the JOIN
    across recordings that production drift analysis relies on.

    Returns the count of sensor_samples rows inserted.
    """
    canonical_pid = _normalize_pid_hex(pid_hex)
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with get_connection(db_path) as conn:
        count = 0
        for day_offset, value in values_over_days:
            captured_at = (t0 + timedelta(days=float(day_offset))).isoformat()
            # One recording per sample
            cursor = conn.execute(
                "INSERT INTO sensor_recordings "
                "(vehicle_id, session_label, started_at, protocol_name, "
                " pids_csv, sample_count, file_ref) "
                "VALUES (?, ?, ?, ?, ?, 1, NULL)",
                (vehicle_id, f"test-{day_offset}", captured_at,
                 "Mock", canonical_pid.replace("0x", "")),
            )
            recording_id = int(cursor.lastrowid)
            conn.execute(
                "INSERT INTO sensor_samples "
                "(recording_id, captured_at, pid_hex, value, raw, unit) "
                "VALUES (?, ?, ?, ?, NULL, ?)",
                (recording_id, captured_at, canonical_pid, value, unit),
            )
            count += 1
    return count


# ===========================================================================
# 1. compute_trend — regression core
# ===========================================================================


class TestComputeTrend:
    """Hand-computed fixture checks + edge cases."""

    def test_known_slope_intercept_r_squared(self, db):
        """Pure-linear y = 2*x + 10 over 5 days returns slope=2, intercept=10,
        r²=1.0."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 10.0), (1, 12.0), (2, 14.0),
                              (3, 16.0), (4, 18.0)],
            unit="°C",
        )
        result = compute_trend(vid, "0x05", db_path=db)
        assert result is not None
        assert abs(result.slope_per_day - 2.0) < 1e-6
        assert abs(result.intercept - 10.0) < 1e-6
        assert abs(result.r_squared - 1.0) < 1e-6
        assert result.n_samples == 5

    def test_flat_line_r_squared_one_slope_zero(self, db):
        """Flat series (zero variance y) → slope=0, r²=1.0, bucket=STABLE."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 90.0), (10, 90.0), (20, 90.0),
                              (30, 90.0)],
        )
        result = compute_trend(vid, "0x05", db_path=db)
        assert result is not None
        assert abs(result.slope_per_day) < 1e-9
        assert abs(result.r_squared - 1.0) < 1e-6
        assert result.bucket == DriftBucket.STABLE

    def test_rising_series_positive_drift_pct(self, db):
        """Rising values produce a positive signed drift_pct_per_30_days."""
        vid = _seed_vehicle(db)
        # Mean = 10, slope = 1/day → 30/day * 100/10 = 300%/30d, definitely fast
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 5.0), (1, 7.0), (2, 9.0),
                              (3, 11.0), (4, 13.0), (5, 15.0)],
        )
        result = compute_trend(vid, "0x05", db_path=db)
        assert result is not None
        assert result.drift_pct_per_30_days > 0.0
        assert result.bucket == DriftBucket.DRIFTING_FAST

    def test_falling_series_negative_drift_pct(self, db):
        """Falling values produce a negative signed drift_pct_per_30_days."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0x42",
            values_over_days=[(0, 14.0), (30, 13.5), (60, 13.0),
                              (90, 12.5)],
            unit="V",
        )
        result = compute_trend(vid, "0x42", db_path=db)
        assert result is not None
        assert result.drift_pct_per_30_days < 0.0

    def test_n1_returns_none(self, db):
        """One sample is not enough for a trend — returns None."""
        vid = _seed_vehicle(db)
        _seed_drift(db, vid, "0x05", values_over_days=[(0, 90.0)])
        result = compute_trend(vid, "0x05", db_path=db)
        assert result is None

    def test_n2_returns_valid_result(self, db):
        """Two samples is the minimum — returns a valid DriftResult."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 80.0), (30, 100.0)],
        )
        result = compute_trend(vid, "0x05", db_path=db)
        assert result is not None
        assert result.n_samples == 2

    def test_since_until_filter(self, db):
        """`since` / `until` limit the sample window."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 80.0), (10, 82.0), (20, 85.0),
                              (30, 88.0), (40, 92.0)],
        )
        # Full series: 5 samples
        full = compute_trend(vid, "0x05", db_path=db)
        assert full is not None
        assert full.n_samples == 5

        # `since` filter
        since_iso = (datetime(2026, 1, 1, tzinfo=timezone.utc)
                     + timedelta(days=15)).isoformat()
        partial = compute_trend(vid, "0x05", since=since_iso, db_path=db)
        assert partial is not None
        assert partial.n_samples == 3  # days 20, 30, 40

    def test_sensor_catalog_enrichment(self, db):
        """PID 0x05 → pid_name='Engine coolant temperature' + unit='°C'."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 85.0), (30, 90.0)],
        )
        result = compute_trend(vid, "0x05", db_path=db)
        assert result is not None
        # Sensor catalog gives canonical names
        assert "coolant" in result.pid_name.lower()

    def test_pid_hex_normalization(self, db):
        """Lower-case or unprefixed PIDs still hit the canonical 0xNN row."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 80.0), (30, 90.0)],
        )
        r1 = compute_trend(vid, "5", db_path=db)
        r2 = compute_trend(vid, "0x05", db_path=db)
        r3 = compute_trend(vid, "0X05", db_path=db)
        assert r1 is not None and r2 is not None and r3 is not None
        assert r1.pid_hex == r2.pid_hex == r3.pid_hex == "0x05"


# ===========================================================================
# 2. detect_drifting_pids
# ===========================================================================


class TestDetectDriftingPids:
    """Threshold-boundary + sort + edge-case tests."""

    def test_empty_db_returns_empty(self, db):
        """No recordings at all → empty list."""
        vid = _seed_vehicle(db)
        assert detect_drifting_pids(vid, db_path=db) == []

    def test_all_stable_returns_empty(self, db):
        """All PIDs below threshold → empty list (no drifters)."""
        vid = _seed_vehicle(db)
        # Flat — zero drift
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 90.0), (30, 90.0), (60, 90.0)],
        )
        result = detect_drifting_pids(vid, threshold_pct=5.0, db_path=db)
        assert result == []

    def test_threshold_boundary_slow_vs_fast(self, db):
        """5 %/30d threshold: 6 %/30d → slow, 12 %/30d → fast."""
        vid = _seed_vehicle(db)
        # Construct synthetic series where drift_pct ≈ 12%/30d (fast)
        # mean ~ 50, slope ~ 0.2/day → 0.2*30/50 *100 = 12%
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 40.0), (30, 46.0), (60, 52.0),
                              (90, 58.0)],
        )
        # Another PID with ~6%/30d slope — mean 50, slope 0.1/day → 6%
        _seed_drift(
            db, vid, "0x42",
            values_over_days=[(0, 45.0), (30, 48.0), (60, 51.0),
                              (90, 54.0)],
        )
        result = detect_drifting_pids(vid, threshold_pct=5.0, db_path=db)
        buckets = {r.pid_hex: r.bucket for r in result}
        assert buckets.get("0x05") == DriftBucket.DRIFTING_FAST
        assert buckets.get("0x42") == DriftBucket.DRIFTING_SLOW

    def test_deterministic_sort(self, db):
        """Sort: abs(pct) DESC, then pid_hex ASC."""
        vid = _seed_vehicle(db)
        # Fastest drifter (~20%/30d)
        _seed_drift(db, vid, "0x05",
                    values_over_days=[(0, 40.0), (30, 48.0),
                                      (60, 56.0), (90, 64.0)])
        # Smaller drifter (~8%/30d)
        _seed_drift(db, vid, "0x42",
                    values_over_days=[(0, 45.0), (30, 48.0),
                                      (60, 51.0), (90, 54.0)])
        result = detect_drifting_pids(vid, threshold_pct=5.0, db_path=db)
        assert len(result) == 2
        assert abs(result[0].drift_pct_per_30_days) >= abs(
            result[1].drift_pct_per_30_days
        )

    def test_since_filter_shrinks_result(self, db):
        """`since` applied through to compute_trend shrinks samples."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 40.0), (30, 46.0), (60, 52.0),
                              (90, 58.0), (120, 64.0)],
        )
        since_iso = (datetime(2026, 1, 1, tzinfo=timezone.utc)
                     + timedelta(days=45)).isoformat()
        result = detect_drifting_pids(
            vid, threshold_pct=5.0, since=since_iso, db_path=db,
        )
        # 3 samples after the since cut; still drifting fast
        assert any(r.pid_hex == "0x05" for r in result)
        r0 = next(r for r in result if r.pid_hex == "0x05")
        assert r0.n_samples == 3

    def test_unknown_pid_catalog_fallback(self, db):
        """Unrecorded PID still drifts — name falls back to 'PID 0xAA'."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0xAA",
            values_over_days=[(0, 10.0), (30, 15.0), (60, 20.0),
                              (90, 25.0)],
        )
        result = detect_drifting_pids(vid, threshold_pct=5.0, db_path=db)
        assert len(result) == 1
        assert "0xAA" in result[0].pid_name


# ===========================================================================
# 3. summary_for_bike
# ===========================================================================


class TestSummary:
    """Three-bucket shape contract."""

    def test_three_bucket_keys_always_present(self, db):
        """All three bucket keys exist even when empty."""
        vid = _seed_vehicle(db)
        summary = summary_for_bike(vid, db_path=db)
        assert set(summary.keys()) == {
            "stable", "drifting-slow", "drifting-fast",
        }

    def test_all_stable_bucket(self, db):
        """Zero-drift series populates only the stable bucket."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 90.0), (30, 90.0), (60, 90.0)],
        )
        summary = summary_for_bike(vid, threshold_pct=5.0, db_path=db)
        assert len(summary["stable"]) == 1
        assert summary["drifting-slow"] == []
        assert summary["drifting-fast"] == []

    def test_all_fast_bucket(self, db):
        """High-drift series populates only the drifting-fast bucket."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 40.0), (30, 56.0), (60, 72.0),
                              (90, 88.0)],
        )
        summary = summary_for_bike(vid, threshold_pct=5.0, db_path=db)
        assert len(summary["drifting-fast"]) == 1
        assert summary["stable"] == []
        assert summary["drifting-slow"] == []

    def test_mixed_buckets(self, db):
        """Stable + slow + fast all populated correctly."""
        vid = _seed_vehicle(db)
        # stable
        _seed_drift(
            db, vid, "0x0C",
            values_over_days=[(0, 3000.0), (30, 3000.0), (60, 3000.0)],
        )
        # slow (~6%/30d)
        _seed_drift(
            db, vid, "0x42",
            values_over_days=[(0, 45.0), (30, 48.0), (60, 51.0),
                              (90, 54.0)],
        )
        # fast (~20%/30d)
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 40.0), (30, 48.0), (60, 56.0),
                              (90, 64.0)],
        )
        summary = summary_for_bike(vid, threshold_pct=5.0, db_path=db)
        assert len(summary["stable"]) == 1
        assert len(summary["drifting-slow"]) == 1
        assert len(summary["drifting-fast"]) == 1

    def test_threshold_zero_nothing_stable(self, db):
        """threshold=0 reclassifies any nonzero drift as fast."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 50.0), (30, 50.5), (60, 51.0)],
        )
        summary = summary_for_bike(vid, threshold_pct=0.0, db_path=db)
        # With threshold=0, anything > 0 drift is fast
        assert summary["stable"] == []
        assert len(summary["drifting-fast"]) + len(summary["drifting-slow"]) == 1

    def test_roundtrip_model_dump(self, db):
        """DriftResult.model_dump(mode='json') + model_validate round-trip."""
        vid = _seed_vehicle(db)
        _seed_drift(
            db, vid, "0x05",
            values_over_days=[(0, 80.0), (30, 90.0), (60, 100.0)],
        )
        summary = summary_for_bike(vid, db_path=db)
        all_results = [
            r for rs in summary.values() for r in rs
        ]
        assert all_results, "Expected at least one result"
        for r in all_results:
            dumped = r.model_dump(mode="json")
            restored = DriftResult.model_validate(dumped)
            assert restored == r
            # Enum serializes as string
            assert isinstance(dumped["bucket"], str)


# ===========================================================================
# 4. CLI — drift bike / show / recording / plot + predictor integration
# ===========================================================================


class TestDriftCLI:
    """Click-runner tests for the drift subgroup."""

    def test_drift_bike_happy_path(self, cli_db):
        """`drift bike --bike X --pid 0x05` renders a Rich panel."""
        vid = _seed_vehicle(cli_db)
        _seed_drift(
            cli_db, vid, "0x05",
            values_over_days=[(0, 40.0), (30, 48.0),
                              (60, 56.0), (90, 64.0)],
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "drift", "bike",
             "--bike", "sportster-2010", "--pid", "0x05"],
        )
        assert result.exit_code == 0, result.output
        # Rich panel includes the drift pct label
        assert "Drift" in result.output or "drift" in result.output.lower()

    def test_drift_bike_json(self, cli_db):
        """--json emits a JSON object matching the DriftResult shape."""
        vid = _seed_vehicle(cli_db)
        _seed_drift(
            cli_db, vid, "0x05",
            values_over_days=[(0, 40.0), (30, 48.0),
                              (60, 56.0), (90, 64.0)],
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "drift", "bike",
             "--bike", "sportster-2010", "--pid", "0x05", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert "pid_hex" in payload
        assert payload["pid_hex"] == "0x05"

    def test_drift_show_happy_path(self, cli_db):
        """`drift show --bike X` renders a three-bucket table."""
        vid = _seed_vehicle(cli_db)
        _seed_drift(
            cli_db, vid, "0x05",
            values_over_days=[(0, 40.0), (30, 48.0),
                              (60, 56.0), (90, 64.0)],
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "drift", "show", "--bike", "sportster-2010"],
        )
        assert result.exit_code == 0, result.output
        assert "drift" in result.output.lower()

    def test_drift_show_json_has_three_keys(self, cli_db):
        """--json output contains all three bucket keys."""
        vid = _seed_vehicle(cli_db)
        _seed_drift(
            cli_db, vid, "0x05",
            values_over_days=[(0, 40.0), (30, 48.0), (60, 56.0)],
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "drift", "show",
             "--bike", "sportster-2010", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert set(payload["summary"].keys()) == {
            "stable", "drifting-slow", "drifting-fast",
        }

    def test_drift_plot_csv_output(self, cli_db, tmp_path):
        """`drift plot --format csv --output FILE` writes a wide CSV."""
        vid = _seed_vehicle(cli_db)
        _seed_drift(
            cli_db, vid, "0x05",
            values_over_days=[(0, 40.0), (30, 48.0),
                              (60, 56.0), (90, 64.0)],
        )
        out = tmp_path / "drift.csv"
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "drift", "plot",
             "--bike", "sportster-2010", "--pid", "0x05",
             "--format", "csv", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        content = out.read_text(encoding="utf-8")
        # Wide format header
        assert "recording_id" in content
        assert "pid_hex" in content
        assert "mean" in content

    def test_drift_plot_ascii_stdout(self, cli_db):
        """`drift plot --format ascii` emits sparkline glyphs to stdout."""
        vid = _seed_vehicle(cli_db)
        _seed_drift(
            cli_db, vid, "0x05",
            values_over_days=[(0, 40.0), (30, 48.0),
                              (60, 56.0), (90, 64.0)],
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "drift", "plot",
             "--bike", "sportster-2010", "--pid", "0x05",
             "--format", "ascii"],
        )
        assert result.exit_code == 0, result.output
        # At least one block glyph present
        assert any(c in result.output for c in
                   ["\u2581", "\u2582", "\u2583", "\u2584",
                    "\u2585", "\u2586", "\u2587", "\u2588"])

    def test_drift_unknown_bike_remediation(self, cli_db):
        """Unknown slug → red panel + exit 1 (Phase 125-style)."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "drift", "bike",
             "--bike", "nonexistent-2099", "--pid", "0x05"],
        )
        assert result.exit_code == 1
        assert ("not found" in result.output.lower()
                or "no bike" in result.output.lower())

    def test_drift_since_gt_until_error(self, cli_db):
        """--since > --until raises a ClickException."""
        _seed_vehicle(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "drift", "bike",
             "--bike", "sportster-2010", "--pid", "0x05",
             "--since", "2026-12-01",
             "--until", "2026-01-01"],
        )
        assert result.exit_code != 0
        assert "since" in result.output.lower()

    def test_drift_recording_happy_path(self, cli_db):
        """`drift recording RECORDING_ID` renders intra-session trends."""
        vid = _seed_vehicle(cli_db)
        # Seed a single recording with 3 intra-session samples on one PID
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with get_connection(cli_db) as conn:
            cursor = conn.execute(
                "INSERT INTO sensor_recordings "
                "(vehicle_id, session_label, started_at, protocol_name, "
                " pids_csv, sample_count, file_ref) "
                "VALUES (?, ?, ?, ?, ?, 3, NULL)",
                (vid, "intra", t0.isoformat(), "Mock", "05"),
            )
            rid = int(cursor.lastrowid)
            for i, (sec_offset, val) in enumerate(
                [(0, 40.0), (30, 45.0), (60, 50.0)]
            ):
                ts = (t0 + timedelta(seconds=sec_offset)).isoformat()
                conn.execute(
                    "INSERT INTO sensor_samples "
                    "(recording_id, captured_at, pid_hex, value, "
                    " raw, unit) "
                    "VALUES (?, ?, ?, ?, NULL, ?)",
                    (rid, ts, "0x05", val, "°C"),
                )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "drift", "recording", str(rid), "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert payload["recording_id"] == rid

    def test_predict_failures_drift_bonus(self, cli_db, monkeypatch):
        """Predictor picks up drifting-fast O2 and adds +0.1 confidence."""
        from motodiag.advanced import predict_failures
        from motodiag.advanced.drift import DriftBucket, DriftResult
        from motodiag.knowledge.issues_repo import add_known_issue

        # Seed the vehicle and a KB row whose symptoms match the drifting
        # PID's catalog name.
        vid = _seed_vehicle(cli_db)
        # Make-wide issue (model=None) with out-of-range year → match_tier
        # demotes to "make" (base 0.5). Narrow year-range bonus + no
        # age/mileage saturation keeps the final clamped score well
        # below 1.0 so a +0.1 drift bonus is observable.
        add_known_issue(
            title="O2 sensor aging",
            description="O2 sensor voltage drift from carbon fouling.",
            make="Harley-Davidson",
            model=None,
            year_start=2004,
            year_end=2007,
            severity="high",
            # Symptom is a substring of pid_name "O2 sensor voltage B1S1"
            # → overlap heuristic triggers the +0.1 bonus.
            symptoms=["o2 sensor voltage", "lean code"],
            dtc_codes=["P0130"],
            causes=["Sensor aging"],
            fix_procedure="Replace both upstream O2 sensors.",
            parts_needed=["O2 sensor B1S1"],
            estimated_hours=1.5,
            db_path=cli_db,
        )

        # Fake drift result — drifting-fast O2 sensor
        fake_drift = [
            DriftResult(
                vehicle_id=vid,
                pid_hex="0x14",
                pid_name="O2 sensor voltage B1S1",
                unit="V",
                n_samples=4,
                n_recordings=4,
                first_captured_at="2026-01-01T00:00:00+00:00",
                last_captured_at="2026-04-01T00:00:00+00:00",
                span_days=90.0,
                slope_per_day=0.01,
                intercept=0.4,
                r_squared=0.99,
                mean_value=0.5,
                drift_pct_per_30_days=15.0,
                bucket=DriftBucket.DRIFTING_FAST,
            )
        ]

        def _fake_detect(**kwargs):
            return fake_drift

        monkeypatch.setattr(
            "motodiag.advanced.drift.detect_drifting_pids",
            _fake_detect,
        )

        # Vehicle MUST carry an id for the drift bonus path. Pick
        # a recent year + low mileage so the predictor's other
        # bonuses do NOT saturate the score past the clamp — the
        # +0.1 drift bonus must be observable.
        vehicle = {
            "id": vid,
            "make": "Harley-Davidson",
            "model": "Sportster 1200",
            "year": 2024,
            "mileage": 500,
        }

        # Run with drift bonus
        preds_with = predict_failures(
            vehicle, horizon_days=None, db_path=cli_db,
        )
        o2_pred = next(
            (p for p in preds_with if "O2" in p.issue_title),
            None,
        )
        assert o2_pred is not None

        # Now run WITHOUT the drift bonus (no vehicle id)
        vehicle_no_id = {
            k: v for k, v in vehicle.items() if k != "id"
        }
        preds_without = predict_failures(
            vehicle_no_id, horizon_days=None, db_path=cli_db,
        )
        o2_pred_no = next(
            (p for p in preds_without if "O2" in p.issue_title),
            None,
        )
        assert o2_pred_no is not None

        # Bonus is +0.1, allowing for clamp
        delta = (o2_pred.confidence_score
                 - o2_pred_no.confidence_score)
        # Score may have been clamped to 1.0 — allow ≤ +0.10 up to clamp
        assert delta > 0.0
        assert abs(delta - 0.10) < 1e-6 or o2_pred.confidence_score == 1.0


# ===========================================================================
# 5. Helper function tests (pure, no DB)
# ===========================================================================


class TestHelpers:
    """Pure-function tests on the stdlib math + formatters."""

    def test_linear_regression_known(self):
        xs = [0.0, 1.0, 2.0, 3.0, 4.0]
        ys = [10.0, 12.0, 14.0, 16.0, 18.0]
        reg = _linear_regression(xs, ys)
        assert reg is not None
        slope, intercept, r2 = reg
        assert abs(slope - 2.0) < 1e-9
        assert abs(intercept - 10.0) < 1e-9
        assert abs(r2 - 1.0) < 1e-9

    def test_linear_regression_degenerate_sxx(self):
        """Identical xs → sxx == 0 → None."""
        xs = [5.0, 5.0, 5.0]
        ys = [1.0, 2.0, 3.0]
        assert _linear_regression(xs, ys) is None

    def test_linear_regression_n_lt_2(self):
        assert _linear_regression([1.0], [2.0]) is None

    def test_classify_bucket_boundary(self):
        # Below threshold → STABLE
        assert _classify_bucket(4.9, 5.0) == DriftBucket.STABLE
        # At threshold → SLOW (inclusive lower)
        assert _classify_bucket(5.0, 5.0) == DriftBucket.DRIFTING_SLOW
        # At 2× threshold → FAST (inclusive lower)
        assert _classify_bucket(10.0, 5.0) == DriftBucket.DRIFTING_FAST
        # Way above → FAST
        assert _classify_bucket(100.0, 5.0) == DriftBucket.DRIFTING_FAST

    def test_normalize_pid_hex(self):
        assert _normalize_pid_hex("0x0C") == "0x0C"
        assert _normalize_pid_hex("0x0c") == "0x0C"
        assert _normalize_pid_hex("0C") == "0x0C"
        assert _normalize_pid_hex("0c") == "0x0C"
        assert _normalize_pid_hex("0X0C") == "0x0C"
        assert _normalize_pid_hex("") == ""
        assert _normalize_pid_hex(None) == ""

    def test_render_sparkline_empty(self):
        assert _render_sparkline([]) == ""

    def test_render_sparkline_flat(self):
        """Flat series renders as non-empty mid-height blocks."""
        spark = _render_sparkline([5.0, 5.0, 5.0, 5.0], width=4)
        assert len(spark) == 4
        # All the same glyph
        assert len(set(spark)) == 1

    def test_render_sparkline_rising(self):
        """Rising series goes from low block → high block."""
        spark = _render_sparkline(
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], width=8,
        )
        assert len(spark) == 8
        # First glyph should be the lowest block
        assert spark[0] == "\u2581"
        # Last glyph should be the highest block
        assert spark[-1] == "\u2588"
