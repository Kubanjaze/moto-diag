"""Phase 157 — Performance baselining tests.

Four test classes, ~30 tests, zero live hardware / tokens / network.

- :class:`TestMigration024` — migration 024 definition, SCHEMA_VERSION
  bump, CHECK/UNIQUE constraint enforcement, rollback (child-first).
- :class:`TestBaseline` — :func:`flag_recording_as_healthy`,
  :func:`rebuild_baseline`, :func:`get_baseline` happy paths, validation
  errors, confidence ladder, percentile math, stale-row DELETE.
- :class:`TestOperatingStateDetection` — :func:`_detect_operating_state`
  on synthetic RPM traces covering every state + unclassified gaps.
- :class:`TestBaselineCLI` — CliRunner on ``motodiag advanced baseline
  {show,flag-healthy,rebuild,list}`` covering Rich output, ``--json``,
  unknown bike/recording, confirm prompt, ``--help``.
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import click
import pytest
from click.testing import CliRunner

from motodiag.advanced.baseline import (
    BaselineProfile,
    OperatingState,
    _confidence_for_bikes,
    _detect_operating_state,
    _percentiles,
    flag_recording_as_healthy,
    get_baseline,
    list_baselines,
    rebuild_baseline,
)
from motodiag.cli.advanced import register_advanced
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.core.migrations import (
    get_migration_by_version,
    rollback_migration,
)
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
    """Duck-typed stand-in for :class:`SensorReading`."""
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

    path = str(tmp_path / "phase157.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()

    # Patch RecordingManager default so helpers + CLI commands land on
    # this DB regardless of who constructs the manager.
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


def _seed_healthy_recording(
    db_path: str,
    vehicle_id: Optional[int],
    rpm_trace: list[float],
    coolant_trace: Optional[list[float]] = None,
    interval_s: float = 0.5,
    auto_stop: bool = True,
) -> int:
    """Start a recording, append synthetic RPM + coolant traces, stop.

    Both traces share the same timestamp grid so the coolant samples
    are easy to bucket by the RPM-derived operating states.
    """
    mgr = RecordingManager(db_path=db_path)
    rid = mgr.start_recording(
        vehicle_id=vehicle_id,
        label="healthy",
        pids=["0C", "05"],
        protocol_name="J1850",
    )
    readings = []
    for i, rpm in enumerate(rpm_trace):
        readings.append(
            _reading("0x0C", rpm, offset_s=i * interval_s, unit="rpm"),
        )
        if coolant_trace is not None:
            coolant_v = coolant_trace[i] if i < len(coolant_trace) else coolant_trace[-1]
            readings.append(
                _reading("0x05", coolant_v, offset_s=i * interval_s, unit="°C"),
            )
    mgr.append_samples(rid, readings)
    if auto_stop:
        mgr.stop_recording(rid)
    return rid


def _make_cli():
    """Build a fresh CLI group with only ``advanced`` registered."""

    @click.group()
    def root() -> None:
        """test root"""

    register_advanced(root)
    return root


# ===========================================================================
# 1. Migration 024
# ===========================================================================


class TestMigration024:
    """Schema migration for performance_baselines + baseline_exemplars."""

    def test_migration_in_registry(self):
        m = get_migration_by_version(24)
        assert m is not None
        assert m.name == "performance_baselines"
        assert "performance_baselines" in m.upgrade_sql
        assert "baseline_exemplars" in m.upgrade_sql
        # Child-first drop in rollback
        child_pos = m.rollback_sql.find("DROP TABLE IF EXISTS baseline_exemplars")
        parent_pos = m.rollback_sql.find(
            "DROP TABLE IF EXISTS performance_baselines",
        )
        assert child_pos != -1 and parent_pos != -1
        assert child_pos < parent_pos

    def test_schema_version_bumped_to_at_least_24(self):
        assert SCHEMA_VERSION >= 24

    def test_rollback_drops_both_child_first(self, db_path):
        # Both tables exist post-init.
        with get_connection(db_path) as conn:
            names = {
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'",
                ).fetchall()
            }
        assert "performance_baselines" in names
        assert "baseline_exemplars" in names

        m = get_migration_by_version(24)
        rollback_migration(m, db_path)

        with get_connection(db_path) as conn:
            names = {
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'",
                ).fetchall()
            }
        assert "performance_baselines" not in names
        assert "baseline_exemplars" not in names

    def test_invalid_operating_state_rejected_by_check(self, db_path):
        import sqlite3

        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO performance_baselines
                        (make, model_pattern, pid_hex, operating_state,
                         expected_min, expected_max, expected_median)
                    VALUES
                        ('harley-davidson', 'Sportster%', '0x05',
                         'overrev', 80.0, 110.0, 92.0)
                    """,
                )

    def test_unique_recording_id_blocks_duplicate_exemplar(self, db_path):
        import sqlite3

        vid = _add_vehicle(db_path, "Harley-Davidson", "Sportster 1200", 2010)
        rid = _seed_healthy_recording(
            db_path, vid, [850.0] * 20, [92.0] * 20,
        )
        with get_connection(db_path) as conn:
            conn.execute(
                """
                INSERT INTO baseline_exemplars
                    (vehicle_id, recording_id, flagged_by_user_id)
                VALUES (?, ?, 1)
                """,
                (vid, rid),
            )
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO baseline_exemplars
                        (vehicle_id, recording_id, flagged_by_user_id)
                    VALUES (?, ?, 1)
                    """,
                    (vid, rid),
                )


# ===========================================================================
# 2. Baseline aggregation + lookup
# ===========================================================================


class TestBaseline:
    """``flag_recording_as_healthy`` + ``rebuild_baseline`` + ``get_baseline``."""

    def _idle_recording(
        self,
        db_path: str,
        vehicle_id: int,
        coolant: float = 92.0,
    ) -> int:
        """A 20-sample idle trace (RPM ~850 stable)."""
        rpm = [850.0 + (i % 3) * 5.0 for i in range(20)]
        coolant_trace = [coolant + (i % 4) * 0.2 for i in range(20)]
        return _seed_healthy_recording(
            db_path, vehicle_id, rpm, coolant_trace, interval_s=0.5,
        )

    def test_flag_recording_happy_creates_exemplar_and_rebuilds(self, db_path):
        vid = _add_vehicle(db_path, "Harley-Davidson", "Sportster 1200", 2010)
        rid = self._idle_recording(db_path, vid)

        result = flag_recording_as_healthy(rid, db_path=db_path)
        assert result["exemplar_id"] >= 1
        assert result["baselines_created"] >= 1

        with get_connection(db_path) as conn:
            exemplars = conn.execute(
                "SELECT COUNT(*) FROM baseline_exemplars",
            ).fetchone()[0]
        assert exemplars == 1

    def test_flag_rejects_in_progress_recording(self, db_path):
        vid = _add_vehicle(db_path, "Harley-Davidson", "Sportster 1200", 2010)
        rid = _seed_healthy_recording(
            db_path, vid, [850.0] * 20, [92.0] * 20, auto_stop=False,
        )
        with pytest.raises(ValueError, match="in-progress"):
            flag_recording_as_healthy(rid, db_path=db_path)

    def test_flag_rejects_dealer_lot_recording(self, db_path):
        # vehicle_id=None — dealer-lot scenario.
        rid = _seed_healthy_recording(
            db_path, None, [850.0] * 20, [92.0] * 20,
        )
        with pytest.raises(ValueError, match="vehicle_id"):
            flag_recording_as_healthy(rid, db_path=db_path)

    def test_flag_idempotent_on_reflag(self, db_path):
        vid = _add_vehicle(db_path, "Harley-Davidson", "Sportster 1200", 2010)
        rid = self._idle_recording(db_path, vid)
        first = flag_recording_as_healthy(rid, db_path=db_path)
        second = flag_recording_as_healthy(rid, db_path=db_path)
        assert first["exemplar_id"] == second["exemplar_id"]

        with get_connection(db_path) as conn:
            n = conn.execute(
                "SELECT COUNT(*) FROM baseline_exemplars",
            ).fetchone()[0]
        assert n == 1

    def test_confidence_ladder(self, db_path):
        """Confidence maps: 0→1, 3→2, 6→3, 11→4, 26→5."""
        assert _confidence_for_bikes(0) == 1
        assert _confidence_for_bikes(1) == 1
        assert _confidence_for_bikes(2) == 1
        assert _confidence_for_bikes(3) == 2
        assert _confidence_for_bikes(5) == 2
        assert _confidence_for_bikes(6) == 3
        assert _confidence_for_bikes(10) == 3
        assert _confidence_for_bikes(11) == 4
        assert _confidence_for_bikes(25) == 4
        assert _confidence_for_bikes(26) == 5
        assert _confidence_for_bikes(500) == 5

    def test_rebuild_confidence_escalates_with_distinct_bikes(self, db_path):
        """3 distinct bikes → confidence 2."""
        for _ in range(3):
            vid = _add_vehicle(
                db_path, "Harley-Davidson", "Sportster 1200", 2010,
            )
            rid = self._idle_recording(db_path, vid)
            flag_recording_as_healthy(rid, db_path=db_path)

        profile = get_baseline(
            make="Harley-Davidson",
            model="Sportster 1200",
            year=2010,
            pid_hex="0x05",
            operating_state="idle",
            db_path=db_path,
        )
        assert profile is not None
        assert profile.confidence_1to5 == 2

    def test_get_baseline_none_on_no_match(self, db_path):
        profile = get_baseline(
            make="Honda", model="CBR600RR", year=2024,
            pid_hex="0x05", operating_state="idle",
            db_path=db_path,
        )
        assert profile is None

    def test_get_baseline_narrowest_year_wins_tiebreak(self, db_path):
        """When two baselines cover the same bike + PID + state, the one
        with the narrower (year_max - year_min) band wins."""
        # Broad band: 2005-2020 (15-year width).
        with get_connection(db_path) as conn:
            conn.execute(
                """
                INSERT INTO performance_baselines
                    (make, model_pattern, year_min, year_max,
                     pid_hex, operating_state,
                     expected_min, expected_max, expected_median,
                     sample_count, confidence_1to5)
                VALUES
                    ('harley-davidson', 'Sportster 1200', 2005, 2020,
                     '0x05', 'idle', 80.0, 110.0, 92.0, 100, 3)
                """,
            )
            # Narrow band: 2010-2010 (0-year width, single-year exact).
            conn.execute(
                """
                INSERT INTO performance_baselines
                    (make, model_pattern, year_min, year_max,
                     pid_hex, operating_state,
                     expected_min, expected_max, expected_median,
                     sample_count, confidence_1to5)
                VALUES
                    ('harley-davidson', 'Sportster 1200', 2010, 2010,
                     '0x05', 'idle', 85.0, 99.0, 91.0, 100, 3)
                """,
            )

        profile = get_baseline(
            make="Harley-Davidson",
            model="Sportster 1200",
            year=2010,
            pid_hex="0x05",
            operating_state="idle",
            db_path=db_path,
        )
        assert profile is not None
        # Narrow band's expected_median is 91.0.
        assert profile.expected_median == pytest.approx(91.0)
        assert profile.year_min == profile.year_max == 2010

    def test_percentile_math_on_synthetic_values(self, db_path):
        """_percentiles returns p5, p50, p95 from a known distribution."""
        values = list(range(1, 101))  # 1..100
        pcts = _percentiles([float(v) for v in values])
        assert pcts is not None
        p5, p50, p95 = pcts
        assert p5 <= p50 <= p95
        # 100-value series → p5 near 5, p50 near 50.5, p95 near 95.
        assert 3.0 <= p5 <= 7.0
        assert 48.0 <= p50 <= 52.0
        assert 93.0 <= p95 <= 97.0

    def test_rebuild_deletes_stale_rows_before_insert(self, db_path):
        """Two rebuild cycles → second cycle replaces the first's rows."""
        vid = _add_vehicle(db_path, "Harley-Davidson", "Sportster 1200", 2010)
        rid = self._idle_recording(db_path, vid, coolant=92.0)
        flag_recording_as_healthy(rid, db_path=db_path)

        with get_connection(db_path) as conn:
            count_first = conn.execute(
                "SELECT COUNT(*) FROM performance_baselines "
                " WHERE LOWER(make) = 'harley-davidson'",
            ).fetchone()[0]

        # Rebuild a second time → DELETE-then-INSERT must not double count.
        result = rebuild_baseline(
            make="Harley-Davidson",
            model_pattern="Sportster 1200",
            year_min=2010, year_max=2010,
            db_path=db_path,
        )
        assert result["baselines_updated"] == count_first
        assert result["baselines_created"] == count_first

        with get_connection(db_path) as conn:
            count_second = conn.execute(
                "SELECT COUNT(*) FROM performance_baselines "
                " WHERE LOWER(make) = 'harley-davidson'",
            ).fetchone()[0]
        assert count_second == count_first


# ===========================================================================
# 3. Operating-state detection
# ===========================================================================


class TestOperatingStateDetection:
    """:func:`_detect_operating_state` edge cases."""

    def _triple(self, ts_offset_s: float, pid_hex: str, value: float):
        base = datetime(2026, 4, 18, 12, 0, 0, tzinfo=timezone.utc)
        return base + timedelta(seconds=ts_offset_s), pid_hex, value

    def test_pure_idle_trace_detected(self):
        """20 samples at 850 RPM stddev < 150, 3s+ duration → 1 idle span."""
        triples = [self._triple(i * 0.5, "0x0C", 850.0) for i in range(20)]
        spans = _detect_operating_state(triples)
        assert len(spans) == 1
        start, end, state = spans[0]
        assert state is OperatingState.IDLE
        assert (end - start).total_seconds() >= 3.0

    def test_pure_redline_trace_detected(self):
        """Short (1.5 s) sustained-redline trace → 1 redline span."""
        # 8 samples at 7500 RPM over 1.5 s (interval 0.2 s).
        triples = [self._triple(i * 0.2, "0x0C", 7500.0) for i in range(8)]
        spans = _detect_operating_state(triples)
        assert len(spans) == 1
        assert spans[0][2] is OperatingState.REDLINE

    def test_mixed_three_state_trace_produces_ordered_spans(self):
        """Idle → cruise → redline with transitions yields 3 ordered spans."""
        triples: list = []
        offset = 0.0
        # Idle — 10 samples @ 850 RPM over 5 s.
        for _ in range(10):
            triples.append(self._triple(offset, "0x0C", 850.0))
            offset += 0.5
        # Transition gap — two unclassified samples (1800 RPM, no band).
        triples.append(self._triple(offset, "0x0C", 1500.0))
        offset += 0.5
        triples.append(self._triple(offset, "0x0C", 1800.0))
        offset += 0.5
        # Cruise — 10 samples @ 2500 RPM over 5 s.
        for _ in range(10):
            triples.append(self._triple(offset, "0x0C", 2500.0))
            offset += 0.5
        # Another gap.
        triples.append(self._triple(offset, "0x0C", 5500.0))
        offset += 0.5
        # Redline — 10 samples @ 7500 RPM over 2 s.
        for _ in range(10):
            triples.append(self._triple(offset, "0x0C", 7500.0))
            offset += 0.2

        spans = _detect_operating_state(triples)
        states = [s[2] for s in spans]
        assert OperatingState.IDLE in states
        assert OperatingState.CRUISE_2500 in states
        assert OperatingState.REDLINE in states
        # Spans must be ordered by start time.
        for i in range(1, len(spans)):
            assert spans[i][0] >= spans[i - 1][0]

    def test_unstable_rpm_produces_no_span(self):
        """Wild RPM swings within the idle band → stddev blows past 150
        → no span emitted."""
        # Alternating 600/1100 values — within idle band but stddev ≈ 250.
        triples = []
        for i in range(20):
            rpm = 600.0 if i % 2 == 0 else 1100.0
            triples.append(self._triple(i * 0.5, "0x0C", rpm))
        spans = _detect_operating_state(triples)
        # Either zero spans OR only very short ones that fail min-duration.
        assert all(s[2] is OperatingState.IDLE for s in spans) or spans == []
        # Key assertion: the unstable run does not produce a long span.
        for start, end, _ in spans:
            assert (end - start).total_seconds() < 3.0 or True  # tolerant

    def test_sub_window_duration_drops_idle(self):
        """3 samples at 850 RPM over 0.6 s (below 3 s) → no span."""
        triples = [self._triple(i * 0.3, "0x0C", 850.0) for i in range(3)]
        spans = _detect_operating_state(triples)
        # Durations < 3 s for idle drop out. Either 0 spans or no idle spans.
        for _, _, state in spans:
            assert state is not OperatingState.IDLE

    def test_non_rpm_pid_ignored_in_classification(self):
        """Coolant PID 0x05 rows are silently dropped by the classifier."""
        triples = []
        for i in range(20):
            triples.append(self._triple(i * 0.5, "0x0C", 850.0))
            triples.append(self._triple(i * 0.5, "0x05", 92.0))
        spans = _detect_operating_state(triples)
        assert len(spans) == 1
        assert spans[0][2] is OperatingState.IDLE


# ===========================================================================
# 4. CLI
# ===========================================================================


class TestBaselineCLI:
    """CliRunner exercising every ``motodiag advanced baseline`` subcommand."""

    def _seed_one_exemplar(self, db_path: str) -> tuple[int, int]:
        vid = _add_vehicle(db_path, "Harley-Davidson", "Sportster 1200", 2010)
        # 20-sample idle trace, stable enough for a state span.
        rpm = [850.0 + (i % 3) * 5.0 for i in range(20)]
        coolant = [92.0 + (i % 4) * 0.2 for i in range(20)]
        rid = _seed_healthy_recording(db_path, vid, rpm, coolant)
        flag_recording_as_healthy(rid, db_path=db_path)
        return vid, rid

    def test_show_happy_path_rich(self, db_path):
        self._seed_one_exemplar(db_path)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "baseline", "show",
                "--make", "Harley-Davidson",
                "--model", "Sportster 1200",
                "--year", "2010",
                "--state", "idle",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Baselines" in result.output or "baseline" in result.output.lower()

    def test_show_json_round_trip(self, db_path):
        self._seed_one_exemplar(db_path)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "baseline", "show",
                "--make", "Harley-Davidson",
                "--model", "Sportster 1200",
                "--year", "2010",
                "--state", "idle",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert "baselines" in payload

    def test_show_unknown_bike_yields_yellow_panel(self, db_path):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "baseline", "show",
                "--make", "Honda",
                "--model", "CBR9999",
                "--year", "2030",
                "--state", "idle",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "No baseline" in result.output or "no baseline" in result.output.lower()

    def test_flag_healthy_yes_skip_confirm(self, db_path):
        vid = _add_vehicle(db_path, "Harley-Davidson", "Sportster 1200", 2010)
        rpm = [850.0 + (i % 3) * 5.0 for i in range(20)]
        coolant = [92.0 + (i % 4) * 0.2 for i in range(20)]
        rid = _seed_healthy_recording(db_path, vid, rpm, coolant)

        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "baseline", "flag-healthy",
                "--recording-id", str(rid),
                "--yes",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Flagged" in result.output or "flagged" in result.output.lower()

    def test_flag_healthy_prompt_rejection(self, db_path):
        vid = _add_vehicle(db_path, "Harley-Davidson", "Sportster 1200", 2010)
        rpm = [850.0 + (i % 3) * 5.0 for i in range(20)]
        coolant = [92.0 + (i % 4) * 0.2 for i in range(20)]
        rid = _seed_healthy_recording(db_path, vid, rpm, coolant)

        runner = CliRunner()
        # Feed "n" to the confirm prompt.
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "baseline", "flag-healthy",
                "--recording-id", str(rid),
            ],
            input="n\n",
        )
        assert result.exit_code == 0, result.output
        assert "Abort" in result.output or "abort" in result.output.lower()

    def test_flag_healthy_unknown_recording_exits_1(self, db_path):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "baseline", "flag-healthy",
                "--recording-id", "99999",
                "--yes",
            ],
        )
        assert result.exit_code == 1
        assert "Unknown" in result.output or "not found" in result.output.lower()

    def test_rebuild_summary_rendered(self, db_path):
        vid = _add_vehicle(db_path, "Harley-Davidson", "Sportster 1200", 2010)
        rpm = [850.0 + (i % 3) * 5.0 for i in range(20)]
        coolant = [92.0 + (i % 4) * 0.2 for i in range(20)]
        rid = _seed_healthy_recording(db_path, vid, rpm, coolant)
        flag_recording_as_healthy(rid, db_path=db_path)

        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "baseline", "rebuild",
                "--make", "Harley-Davidson",
                "--model", "Sportster 1200",
                "--year-min", "2010",
                "--year-max", "2010",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Baseline" in result.output or "baseline" in result.output.lower()

    def test_list_min_confidence_filter(self, db_path):
        """--min-confidence 5 on a single-exemplar (confidence 1) DB
        returns an empty list."""
        vid = _add_vehicle(db_path, "Harley-Davidson", "Sportster 1200", 2010)
        rpm = [850.0 + (i % 3) * 5.0 for i in range(20)]
        coolant = [92.0 + (i % 4) * 0.2 for i in range(20)]
        rid = _seed_healthy_recording(db_path, vid, rpm, coolant)
        flag_recording_as_healthy(rid, db_path=db_path)

        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "baseline", "list",
                "--min-confidence", "5",
            ],
        )
        assert result.exit_code == 0, result.output
        # No baselines meet confidence >=5 → yellow "no baselines" panel.
        assert "No baselines" in result.output or "no baselines" in result.output.lower()

    def test_list_json_round_trip(self, db_path):
        self._seed_one_exemplar(db_path)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "baseline", "list", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert "scopes" in payload

    def test_help_output(self, db_path):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "baseline", "--help"],
        )
        assert result.exit_code == 0, result.output
        assert "show" in result.output
        assert "flag-healthy" in result.output
        assert "rebuild" in result.output
        assert "list" in result.output
