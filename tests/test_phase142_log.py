"""Phase 142 — Data logging + recording tests.

Five test classes, ~50+ tests, zero real serial I/O, zero live tokens.

Test classes
------------

- :class:`TestMigration016` — migration presence, table/index creation,
  SCHEMA_VERSION bump, rollback symmetry.
- :class:`TestRecordingManager` — lifecycle, SQLite/JSONL split policy,
  transparent merge, concurrent buffers, nullable vehicle_id, FK
  enforcement, prune.
- :class:`TestLogCLI` — CliRunner-driven: all 8 subcommands' happy paths
  + the error edges described by the spec.
- :class:`TestDiffReport` — linear-interp stats, zero-overlap, flag
  threshold, metric switch, div-by-zero guard.
- :class:`TestReplay` — speed=0 no sleep, speed=1/10 scaled deltas,
  --pids filter, merge ordering across SQLite + JSONL, KeyboardInterrupt.

All tests use a **local synthetic SensorReading** dataclass — no
import of :class:`motodiag.hardware.sensors.SensorReading`, so this
suite survives any Phase 141 API drift.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from motodiag.cli.hardware import register_hardware
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.core.migrations import (
    get_migration_by_version,
    rollback_migration,
)


# ---------------------------------------------------------------------------
# Synthetic SensorReading — decouples the test suite from Phase 141
# ---------------------------------------------------------------------------


@dataclass
class _SyntheticReading:
    """Duck-typed replacement for Phase 141's SensorReading.

    Mirrors the field surface Phase 142's ``_reading_to_sample_row``
    consults: ``pid``, ``pid_hex``, ``name``, ``value``, ``unit``,
    ``raw``, ``captured_at``, ``status``. Using a local synthetic
    dataclass insulates the test suite from any rename / repackaging
    in the sensors module.
    """
    pid: int = 0x0C
    pid_hex: str = "0x0C"
    name: str = "Engine RPM"
    value: Optional[float] = 1726.0
    unit: str = "rpm"
    raw: Optional[int] = 0x1AF8
    captured_at: datetime = field(
        default_factory=lambda: datetime(2026, 4, 18, 12, 0, 0,
                                         tzinfo=timezone.utc)
    )
    status: str = "ok"


def _make_reading(
    pid: int = 0x0C,
    value: Optional[float] = 1500.0,
    offset_s: float = 0.0,
    raw: Optional[int] = None,
    unit: str = "rpm",
) -> _SyntheticReading:
    base = datetime(2026, 4, 18, 12, 0, 0, tzinfo=timezone.utc)
    return _SyntheticReading(
        pid=pid,
        pid_hex=f"0x{pid:02X}",
        name=f"PID 0x{pid:02X}",
        value=value,
        unit=unit,
        raw=raw if raw is not None else (int(value) if value is not None else None),
        captured_at=base + timedelta(seconds=offset_s),
        status="ok" if value is not None else "unsupported",
    )


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch, tmp_path):
    """Redirect init_db + RecordingManager.recordings_dir to tmp_path."""
    db_path = str(tmp_path / "phase142.db")
    init_db(db_path)

    # Patch cli.hardware's init_db so CLI subcommands see the tmp DB.
    from motodiag.cli import hardware as hw_mod

    original_init_db = hw_mod.init_db

    def _patched(*args, **kwargs):
        if args or kwargs:
            return original_init_db(db_path, *args[1:], **kwargs)
        return original_init_db(db_path)

    monkeypatch.setattr(hw_mod, "init_db", _patched)

    # Patch RecordingManager default db_path + recordings_dir so every
    # CLI subcommand and every direct-construction test lands in tmp.
    from motodiag.hardware import recorder as rec_mod

    original_init = rec_mod.RecordingManager.__init__

    def _patched_init(self, db_path=None, recordings_dir=None):
        original_init(
            self,
            db_path=db_path or str(tmp_path / "phase142.db"),
            recordings_dir=recordings_dir or tmp_path / "recordings",
        )

    monkeypatch.setattr(
        rec_mod.RecordingManager, "__init__", _patched_init,
    )

    yield {"db_path": db_path, "tmp_path": tmp_path}


@pytest.fixture
def db_path(_patch_env):
    return _patch_env["db_path"]


@pytest.fixture
def recordings_dir(_patch_env):
    return _patch_env["tmp_path"] / "recordings"


def _make_cli():
    """Build a fresh Click group with just `hardware` attached."""

    @click.group()
    def root() -> None:
        """test root"""

    register_hardware(root)
    return root


# ===========================================================================
# 1. Migration 016
# ===========================================================================


class TestMigration016:
    """Schema migration for sensor_recordings + sensor_samples."""

    def test_migration_in_registry_with_version_16(self):
        m = get_migration_by_version(16)
        assert m is not None
        assert m.name == "sensor_recordings"
        assert "CREATE TABLE" in m.upgrade_sql
        assert "sensor_recordings" in m.upgrade_sql
        assert "sensor_samples" in m.upgrade_sql
        assert "DROP TABLE IF EXISTS sensor_samples" in m.rollback_sql
        assert "DROP TABLE IF EXISTS sensor_recordings" in m.rollback_sql

    def test_both_tables_created_post_init_db(self, db_path):
        with get_connection(db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            names = {row["name"] for row in tables}
            assert "sensor_recordings" in names
            assert "sensor_samples" in names

    def test_four_indexes_present(self, db_path):
        with get_connection(db_path) as conn:
            idx_rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            idx_names = {row["name"] for row in idx_rows}
            assert "idx_recordings_vehicle" in idx_names
            assert "idx_recordings_started" in idx_names
            assert "idx_samples_recording_time" in idx_names
            assert "idx_samples_recording_pid" in idx_names

    def test_schema_version_at_least_16(self):
        assert SCHEMA_VERSION >= 16

    def test_rollback_drops_both_tables(self, db_path, tmp_path):
        # Start from a clean DB that only has baseline + migration 015.
        target_db = str(tmp_path / "rollback.db")
        init_db(target_db)
        # Verify tables exist post-init.
        with get_connection(target_db) as conn:
            names = {
                row["name"] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            assert "sensor_recordings" in names
            assert "sensor_samples" in names
        # Roll back migration 016.
        m = get_migration_by_version(16)
        rollback_migration(m, target_db)
        with get_connection(target_db) as conn:
            names = {
                row["name"] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            assert "sensor_recordings" not in names
            assert "sensor_samples" not in names


# ===========================================================================
# 2. RecordingManager lifecycle + split policy
# ===========================================================================


class TestRecordingManager:
    """Core CRUD + SQLite/JSONL split."""

    def _manager(self, db_path, recordings_dir):
        from motodiag.hardware.recorder import RecordingManager
        return RecordingManager(
            db_path=db_path, recordings_dir=recordings_dir,
        )

    def test_start_and_stop_lifecycle(self, db_path, recordings_dir):
        mgr = self._manager(db_path, recordings_dir)
        rid = mgr.start_recording(
            vehicle_id=None,
            label="smoke",
            pids=["0x0C", "0x05"],
            protocol_name="Mock",
            notes="unit test",
        )
        assert isinstance(rid, int) and rid > 0

        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM sensor_recordings WHERE id = ?", (rid,),
            ).fetchone()
            assert row is not None
            assert row["session_label"] == "smoke"
            assert row["protocol_name"] == "Mock"
            assert row["pids_csv"] == "0C,05"
            assert row["stopped_at"] is None

        mgr.stop_recording(rid, hz_stats=(1.8, 2.1))
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM sensor_recordings WHERE id = ?", (rid,),
            ).fetchone()
            assert row["stopped_at"] is not None
            assert row["min_hz"] == pytest.approx(1.8)
            assert row["max_hz"] == pytest.approx(2.1)

    def test_under_threshold_stays_in_sqlite(
        self, db_path, recordings_dir,
    ):
        mgr = self._manager(db_path, recordings_dir)
        rid = mgr.start_recording(
            vehicle_id=None, label="small", pids=["0x0C"],
            protocol_name="Mock",
        )
        # 500 readings — well under the 1000 threshold.
        batch = [_make_reading(offset_s=i * 0.5, value=1000 + i)
                 for i in range(500)]
        mgr.append_samples(rid, batch)
        mgr.stop_recording(rid)

        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM sensor_recordings WHERE id = ?", (rid,),
            ).fetchone()
            assert row["file_ref"] is None
            count = conn.execute(
                "SELECT COUNT(*) c FROM sensor_samples WHERE recording_id = ?",
                (rid,),
            ).fetchone()["c"]
            assert count == 500

    def test_over_threshold_spills_to_jsonl(
        self, db_path, recordings_dir,
    ):
        mgr = self._manager(db_path, recordings_dir)
        rid = mgr.start_recording(
            vehicle_id=None, label="big", pids=["0x0C"],
            protocol_name="Mock",
        )
        # 1500 readings — crosses the 1000 threshold.
        batch = [_make_reading(offset_s=i * 0.5, value=1000 + i)
                 for i in range(1500)]
        mgr.append_samples(rid, batch)
        mgr.stop_recording(rid)

        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM sensor_recordings WHERE id = ?", (rid,),
            ).fetchone()
            assert row["file_ref"] is not None
            assert str(row["file_ref"]).endswith(".jsonl")

        sidecar = recordings_dir / row["file_ref"]
        assert sidecar.exists()
        # Sidecar should contain every post-threshold reading.
        with open(sidecar, "r", encoding="utf-8") as fh:
            jsonl_lines = [ln for ln in fh.readlines() if ln.strip()]
        assert len(jsonl_lines) == 500

    def test_load_recording_transparent_merge(
        self, db_path, recordings_dir,
    ):
        mgr = self._manager(db_path, recordings_dir)
        rid = mgr.start_recording(
            vehicle_id=None, label="merge", pids=["0x0C"],
            protocol_name="Mock",
        )
        batch = [_make_reading(offset_s=i * 0.5, value=1000 + i)
                 for i in range(1500)]
        mgr.append_samples(rid, batch)
        mgr.stop_recording(rid)

        meta, iterator = mgr.load_recording(rid)
        assert meta["file_ref"] is not None
        samples = list(iterator)
        # 1000 from SQLite (pre-threshold) + 500 from JSONL — sparse
        # summary duplicates are filtered by the merge.
        assert len(samples) == 1500
        # Sorted ascending by captured_at.
        timestamps = [s["captured_at"] for s in samples]
        assert timestamps == sorted(timestamps)

    def test_two_concurrent_recordings_isolate_buffers(
        self, db_path, recordings_dir,
    ):
        mgr = self._manager(db_path, recordings_dir)
        rid_a = mgr.start_recording(
            vehicle_id=None, label="A", pids=["0x0C"],
            protocol_name="Mock",
        )
        rid_b = mgr.start_recording(
            vehicle_id=None, label="B", pids=["0x05"],
            protocol_name="Mock",
        )
        # 120 readings into A, 80 into B.
        mgr.append_samples(
            rid_a,
            [_make_reading(pid=0x0C, offset_s=i * 0.5, value=1000 + i)
             for i in range(120)],
        )
        mgr.append_samples(
            rid_b,
            [_make_reading(pid=0x05, offset_s=i * 0.5, value=80 + i,
                           unit="C")
             for i in range(80)],
        )
        mgr.stop_recording(rid_a)
        mgr.stop_recording(rid_b)

        with get_connection(db_path) as conn:
            a_count = conn.execute(
                "SELECT COUNT(*) c FROM sensor_samples WHERE recording_id=?",
                (rid_a,),
            ).fetchone()["c"]
            b_count = conn.execute(
                "SELECT COUNT(*) c FROM sensor_samples WHERE recording_id=?",
                (rid_b,),
            ).fetchone()["c"]
            assert a_count == 120
            assert b_count == 80

    def test_stop_recording_sets_stopped_at_and_hz(
        self, db_path, recordings_dir,
    ):
        mgr = self._manager(db_path, recordings_dir)
        rid = mgr.start_recording(
            vehicle_id=None, label="hz", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.stop_recording(rid, hz_stats=(0.5, 2.5))

        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM sensor_recordings WHERE id=?", (rid,),
            ).fetchone()
            assert row["stopped_at"] is not None
            assert row["min_hz"] == pytest.approx(0.5)
            assert row["max_hz"] == pytest.approx(2.5)

    def test_prune_deletes_rows_and_unlinks_sidecars(
        self, db_path, recordings_dir,
    ):
        mgr = self._manager(db_path, recordings_dir)
        rid = mgr.start_recording(
            vehicle_id=None, label="old", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.append_samples(
            rid,
            [_make_reading(offset_s=i * 0.5, value=1000 + i)
             for i in range(1200)],
        )
        mgr.stop_recording(rid)
        # Force the started_at column into the past so prune(30) matches.
        with get_connection(db_path) as conn:
            conn.execute(
                "UPDATE sensor_recordings SET started_at = ? WHERE id = ?",
                ("2020-01-01T00:00:00+00:00", rid),
            )

        rowcount, bytes_freed = mgr.prune(older_than_days=30)
        assert rowcount == 1
        assert bytes_freed > 0
        # Sidecar should be gone.
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM sensor_recordings WHERE id = ?", (rid,),
            ).fetchone()
            assert row is None

    def test_prune_tolerates_missing_sidecar(
        self, db_path, recordings_dir,
    ):
        mgr = self._manager(db_path, recordings_dir)
        rid = mgr.start_recording(
            vehicle_id=None, label="missing", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.append_samples(
            rid,
            [_make_reading(offset_s=i * 0.5, value=1000 + i)
             for i in range(1200)],
        )
        mgr.stop_recording(rid)
        # Manually delete the JSONL sidecar, then age-out the recording.
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT file_ref FROM sensor_recordings WHERE id = ?",
                (rid,),
            ).fetchone()
            sidecar = recordings_dir / row["file_ref"]
            sidecar.unlink()
            conn.execute(
                "UPDATE sensor_recordings SET started_at = ? WHERE id = ?",
                ("2020-01-01T00:00:00+00:00", rid),
            )
        rowcount, _ = mgr.prune(older_than_days=30)
        assert rowcount == 1

    def test_vehicle_id_nullable_dealer_lot(
        self, db_path, recordings_dir,
    ):
        mgr = self._manager(db_path, recordings_dir)
        rid = mgr.start_recording(
            vehicle_id=None, label="dealer",
            pids=["0x0C"], protocol_name="Mock",
        )
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT vehicle_id FROM sensor_recordings WHERE id=?",
                (rid,),
            ).fetchone()
            assert row["vehicle_id"] is None

    def test_invalid_vehicle_id_fk_raises(
        self, db_path, recordings_dir,
    ):
        mgr = self._manager(db_path, recordings_dir)
        with pytest.raises(sqlite3.IntegrityError):
            # Open a connection that enforces FKs strictly.
            with get_connection(db_path) as conn:
                conn.execute(
                    "INSERT INTO sensor_recordings "
                    "(vehicle_id, started_at, protocol_name, pids_csv) "
                    "VALUES (?, ?, ?, ?)",
                    (42, "2026-04-18T12:00:00", "Mock", "0C"),
                )

    def test_list_recordings_orders_recent_first(
        self, db_path, recordings_dir,
    ):
        mgr = self._manager(db_path, recordings_dir)
        # Seed three recordings with increasing started_at so
        # DESC order puts them in reverse-insertion order.
        ids = []
        for i in range(3):
            rid = mgr.start_recording(
                vehicle_id=None, label=f"rec{i}",
                pids=["0x0C"], protocol_name="Mock",
            )
            ids.append(rid)
            with get_connection(db_path) as conn:
                conn.execute(
                    "UPDATE sensor_recordings SET started_at = ? WHERE id = ?",
                    (f"2026-04-{10 + i:02d}T00:00:00+00:00", rid),
                )
        rows = mgr.list_recordings(limit=50)
        assert [r["id"] for r in rows] == list(reversed(ids))

    def test_append_samples_on_unknown_recording_raises(
        self, db_path, recordings_dir,
    ):
        mgr = self._manager(db_path, recordings_dir)
        with pytest.raises(ValueError):
            mgr.append_samples(999, [_make_reading()])


# ===========================================================================
# 3. CLI subcommands
# ===========================================================================


class TestLogCLI:
    """Click-runner driven subcommand tests."""

    def _mk(self):
        return _make_cli()

    def test_log_start_mock_happy_path(self):
        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "start", "--port", "COM3",
             "--mock", "--duration", "0.2", "--interval", "0.05",
             "--label", "smoke"],
        )
        assert result.exit_code == 0, result.output

    def test_log_start_bike_missing_shows_remediation(self):
        runner = CliRunner()
        with patch("motodiag.cli.hardware._resolve_bike_slug",
                   return_value=None):
            result = runner.invoke(
                self._mk(),
                ["hardware", "log", "start", "--port", "COM3",
                 "--bike", "does-not-exist", "--mock",
                 "--duration", "0.1"],
            )
        assert result.exit_code == 1
        assert "No bike matches" in result.output

    def test_log_start_bike_and_make_mutex(self):
        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "start", "--port", "COM3",
             "--bike", "x", "--make", "honda", "--mock"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_log_stop_nonexistent(self):
        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "stop", "999"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_log_stop_already_stopped_warns(
        self, db_path, recordings_dir,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="ss", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.stop_recording(rid)

        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "stop", str(rid)],
        )
        # Should exit cleanly with a warn message — not ClickException.
        assert result.exit_code == 0
        assert "already" in result.output.lower()

    def test_log_list_empty_yellow_message(self):
        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "list"],
        )
        assert result.exit_code == 0
        assert "No recordings match" in result.output

    def test_log_list_returns_recording(self, db_path, recordings_dir):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="label-a", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.stop_recording(rid)

        runner = CliRunner()
        result = runner.invoke(
            self._mk(), ["hardware", "log", "list"],
        )
        assert result.exit_code == 0
        assert "label-a" in result.output
        assert str(rid) in result.output

    def test_log_show_missing(self):
        runner = CliRunner()
        result = runner.invoke(
            self._mk(), ["hardware", "log", "show", "999"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_log_show_renders_metadata(
        self, db_path, recordings_dir,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="my-label", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.stop_recording(rid)

        runner = CliRunner()
        result = runner.invoke(
            self._mk(), ["hardware", "log", "show", str(rid)],
        )
        assert result.exit_code == 0
        assert "my-label" in result.output
        assert "Mock" in result.output

    def test_log_replay_speed_zero_no_sleep(
        self, db_path, recordings_dir,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="r", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.append_samples(
            rid,
            [_make_reading(offset_s=i * 0.5, value=1000 + i)
             for i in range(10)],
        )
        mgr.stop_recording(rid)

        runner = CliRunner()
        with patch("motodiag.cli.hardware._time.sleep") as m_sleep:
            result = runner.invoke(
                self._mk(),
                ["hardware", "log", "replay", str(rid), "--speed", "0"],
            )
            assert result.exit_code == 0
            assert m_sleep.call_count == 0

    def test_log_replay_speed_one_sleeps(
        self, db_path, recordings_dir,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="r", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.append_samples(
            rid,
            [_make_reading(offset_s=i * 0.5, value=1000 + i)
             for i in range(5)],
        )
        mgr.stop_recording(rid)

        runner = CliRunner()
        with patch("motodiag.cli.hardware._time.sleep") as m_sleep:
            result = runner.invoke(
                self._mk(),
                ["hardware", "log", "replay", str(rid), "--speed", "1"],
            )
            assert result.exit_code == 0
            # Four deltas between five consecutive samples.
            assert m_sleep.call_count >= 1

    def test_log_replay_speed_ten_scaled(
        self, db_path, recordings_dir,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="r10", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.append_samples(
            rid,
            [_make_reading(offset_s=i * 1.0, value=1000 + i)
             for i in range(3)],
        )
        mgr.stop_recording(rid)

        runner = CliRunner()
        with patch("motodiag.cli.hardware._time.sleep") as m_sleep:
            runner.invoke(
                self._mk(),
                ["hardware", "log", "replay", str(rid), "--speed", "10"],
            )
            # Each gap is 1s real-time → 0.1s at 10x.
            for call in m_sleep.call_args_list:
                assert call.args[0] == pytest.approx(0.1, rel=1e-2)

    def test_log_replay_pids_filter(
        self, db_path, recordings_dir,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="mix", pids=["0x0C", "0x05"],
            protocol_name="Mock",
        )
        mgr.append_samples(rid, [
            _make_reading(pid=0x0C, value=1500, offset_s=0),
            _make_reading(pid=0x05, value=90, offset_s=0.1, unit="C"),
            _make_reading(pid=0x0C, value=1600, offset_s=0.5),
        ])
        mgr.stop_recording(rid)

        runner = CliRunner()
        with patch("motodiag.cli.hardware._time.sleep"):
            result = runner.invoke(
                self._mk(),
                ["hardware", "log", "replay", str(rid),
                 "--speed", "0", "--pids", "0x0C"],
            )
        assert result.exit_code == 0
        assert "0x0C" in result.output
        assert "0x05" not in result.output

    def test_log_diff_zero_overlap_exits_1(
        self, db_path, recordings_dir,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid_a = mgr.start_recording(
            vehicle_id=None, label="A", pids=["0x0C"],
            protocol_name="Mock",
        )
        rid_b = mgr.start_recording(
            vehicle_id=None, label="B", pids=["0x05"],
            protocol_name="Mock",
        )
        mgr.append_samples(rid_a,
                           [_make_reading(pid=0x0C, value=1500, offset_s=0)])
        mgr.append_samples(rid_b,
                           [_make_reading(pid=0x05, value=90, offset_s=0,
                                          unit="C")])
        mgr.stop_recording(rid_a)
        mgr.stop_recording(rid_b)

        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "diff", str(rid_a), str(rid_b)],
        )
        assert result.exit_code == 1

    def test_log_diff_flag_fire_at_large_pct_change(
        self, db_path, recordings_dir,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid_a = mgr.start_recording(
            vehicle_id=None, label="A", pids=["0x05"],
            protocol_name="Mock",
        )
        rid_b = mgr.start_recording(
            vehicle_id=None, label="B", pids=["0x05"],
            protocol_name="Mock",
        )
        mgr.append_samples(rid_a, [
            _make_reading(pid=0x05, value=80, offset_s=i, unit="C")
            for i in range(10)
        ])
        mgr.append_samples(rid_b, [
            # +30% — well over the 10% flag threshold.
            _make_reading(pid=0x05, value=104, offset_s=i, unit="C")
            for i in range(10)
        ])
        mgr.stop_recording(rid_a)
        mgr.stop_recording(rid_b)

        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "diff", str(rid_a), str(rid_b)],
        )
        assert result.exit_code == 0
        assert "🔥" in result.output

    def test_log_diff_aligns_different_lengths(
        self, db_path, recordings_dir,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid_a = mgr.start_recording(
            vehicle_id=None, label="A", pids=["0x05"],
            protocol_name="Mock",
        )
        rid_b = mgr.start_recording(
            vehicle_id=None, label="B", pids=["0x05"],
            protocol_name="Mock",
        )
        mgr.append_samples(rid_a, [
            _make_reading(pid=0x05, value=80 + (i * 0.1),
                          offset_s=i * 0.01, unit="C")
            for i in range(200)
        ])
        mgr.append_samples(rid_b, [
            _make_reading(pid=0x05, value=85 + (i * 0.1),
                          offset_s=i * 0.01, unit="C")
            for i in range(500)
        ])
        mgr.stop_recording(rid_a)
        mgr.stop_recording(rid_b)

        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "diff", str(rid_a), str(rid_b)],
        )
        # Both sides got aligned — should succeed with a non-empty diff.
        assert result.exit_code == 0
        assert "0x05" in result.output

    def test_log_export_csv_wide_format(
        self, db_path, recordings_dir, tmp_path,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="x", pids=["0x0C", "0x05"],
            protocol_name="Mock",
        )
        mgr.append_samples(rid, [
            _make_reading(pid=0x0C, value=1500, offset_s=0),
            _make_reading(pid=0x05, value=90, offset_s=0, unit="C"),
        ])
        mgr.stop_recording(rid)

        out = tmp_path / "out.csv"
        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "export", str(rid),
             "--format", "csv", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        text = out.read_text(encoding="utf-8")
        assert "captured_at" in text
        assert "pid_0x0C" in text
        assert "pid_0x05" in text

    def test_log_export_json_structure(
        self, db_path, recordings_dir, tmp_path,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="j", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.append_samples(rid, [
            _make_reading(pid=0x0C, value=1500, offset_s=0),
        ])
        mgr.stop_recording(rid)

        out = tmp_path / "out.json"
        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "export", str(rid),
             "--format", "json", "--output", str(out)],
        )
        assert result.exit_code == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "metadata" in data
        assert "samples" in data
        assert isinstance(data["samples"], list)

    def test_log_export_parquet_missing_dep_hint(
        self, db_path, recordings_dir, tmp_path, monkeypatch,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="p", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.append_samples(rid, [_make_reading(pid=0x0C, value=1500)])
        mgr.stop_recording(rid)

        # Patch the CLI's _export_parquet helper to always simulate
        # the missing-pyarrow code path. This exercises the exact
        # error surface (ClickException with the pip install hint)
        # without requiring pyarrow to actually be absent from the
        # environment.
        from motodiag.cli import hardware as hw_mod

        def _raise_missing(*args, **kwargs):
            raise click.ClickException(
                "Parquet export requires pyarrow. Install with: "
                "pip install 'motodiag[parquet]'"
            )

        monkeypatch.setattr(hw_mod, "_export_parquet", _raise_missing)

        out = tmp_path / "out.parquet"
        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "export", str(rid),
             "--format", "parquet", "--output", str(out)],
        )
        assert result.exit_code != 0
        assert "pyarrow" in result.output
        assert "motodiag[parquet]" in result.output

    def test_log_export_creates_parent_dir(
        self, db_path, recordings_dir, tmp_path,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="nested", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.append_samples(rid, [_make_reading(pid=0x0C, value=1500)])
        mgr.stop_recording(rid)

        out = tmp_path / "deeply" / "nested" / "dir" / "out.csv"
        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "export", str(rid),
             "--format", "csv", "--output", str(out)],
        )
        assert result.exit_code == 0
        assert out.exists()

    def test_log_prune_yes_skips_prompt(
        self, db_path, recordings_dir,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="old", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.stop_recording(rid)
        with get_connection(db_path) as conn:
            conn.execute(
                "UPDATE sensor_recordings SET started_at = ? WHERE id = ?",
                ("2020-01-01T00:00:00+00:00", rid),
            )

        runner = CliRunner()
        result = runner.invoke(
            self._mk(),
            ["hardware", "log", "prune", "--older-than", "30", "--yes"],
        )
        assert result.exit_code == 0
        assert "Pruned" in result.output


# ===========================================================================
# 4. DiffReport
# ===========================================================================


class TestDiffReport:
    """Unit tests for the RecordingManager.diff_recordings logic."""

    def _mgr(self):
        from motodiag.hardware.recorder import RecordingManager
        return RecordingManager()

    def _seed(self, mgr, pid_values):
        """Build a recording with a list of (pid, value, offset) tuples."""
        rid = mgr.start_recording(
            vehicle_id=None, label="seed",
            pids=list({f"0x{p:02X}" for p, _, _ in pid_values}),
            protocol_name="Mock",
        )
        readings = [
            _make_reading(pid=p, value=v, offset_s=off,
                          unit="C" if p == 0x05 else "rpm")
            for p, v, off in pid_values
        ]
        mgr.append_samples(rid, readings)
        mgr.stop_recording(rid)
        return rid

    def test_matched_avg_stats_correct(self):
        mgr = self._mgr()
        rid1 = self._seed(mgr, [(0x0C, 1000, 0), (0x0C, 2000, 1)])
        rid2 = self._seed(mgr, [(0x0C, 1500, 0), (0x0C, 2500, 1)])
        report = mgr.diff_recordings(rid1, rid2, metric="avg")
        assert len(report.matched) == 1
        d = report.matched[0]
        assert d.stat_1 == pytest.approx(1500)
        assert d.stat_2 == pytest.approx(2000)
        assert d.delta == pytest.approx(500)
        assert d.pct_change == pytest.approx(33.33, rel=1e-2)
        assert d.flagged is True

    def test_only_in_1_and_only_in_2(self):
        mgr = self._mgr()
        rid1 = self._seed(mgr, [(0x0C, 1000, 0), (0x05, 80, 0)])
        rid2 = self._seed(mgr, [(0x0C, 1100, 0), (0x42, 13, 0)])
        report = mgr.diff_recordings(rid1, rid2)
        only1 = set(report.only_in_1)
        only2 = set(report.only_in_2)
        assert "0x05" in only1
        assert "0x42" in only2

    def test_zero_overlap_empty_matched(self):
        mgr = self._mgr()
        rid1 = self._seed(mgr, [(0x0C, 1000, 0)])
        rid2 = self._seed(mgr, [(0x05, 80, 0)])
        report = mgr.diff_recordings(rid1, rid2)
        assert report.matched == []

    def test_flag_below_threshold_not_set(self):
        mgr = self._mgr()
        # 5% change — under the 10% threshold.
        rid1 = self._seed(mgr, [(0x0C, 1000, 0), (0x0C, 1000, 1)])
        rid2 = self._seed(mgr, [(0x0C, 1050, 0), (0x0C, 1050, 1)])
        report = mgr.diff_recordings(rid1, rid2)
        assert report.matched[0].flagged is False

    def test_pct_change_zero_when_stat_1_is_zero(self):
        mgr = self._mgr()
        rid1 = self._seed(mgr, [(0x0C, 0.0, 0), (0x0C, 0.0, 1)])
        rid2 = self._seed(mgr, [(0x0C, 1500, 0), (0x0C, 1500, 1)])
        report = mgr.diff_recordings(rid1, rid2)
        # Division guard kicks in — pct_change should be 0.0.
        assert report.matched[0].pct_change == 0.0

    def test_metric_min(self):
        mgr = self._mgr()
        rid1 = self._seed(mgr, [(0x0C, 1000, 0), (0x0C, 2000, 1)])
        rid2 = self._seed(mgr, [(0x0C, 1500, 0), (0x0C, 2500, 1)])
        report = mgr.diff_recordings(rid1, rid2, metric="min")
        assert report.matched[0].stat_1 == pytest.approx(1000)
        assert report.matched[0].stat_2 == pytest.approx(1500)

    def test_metric_max(self):
        mgr = self._mgr()
        rid1 = self._seed(mgr, [(0x0C, 1000, 0), (0x0C, 2000, 1)])
        rid2 = self._seed(mgr, [(0x0C, 1500, 0), (0x0C, 2500, 1)])
        report = mgr.diff_recordings(rid1, rid2, metric="max")
        assert report.matched[0].stat_1 == pytest.approx(2000)
        assert report.matched[0].stat_2 == pytest.approx(2500)

    def test_invalid_metric_raises(self):
        mgr = self._mgr()
        rid1 = self._seed(mgr, [(0x0C, 1000, 0)])
        rid2 = self._seed(mgr, [(0x0C, 1100, 0)])
        with pytest.raises(ValueError):
            mgr.diff_recordings(rid1, rid2, metric="median")


# ===========================================================================
# 5. Replay
# ===========================================================================


class TestReplay:
    """Focused replay-path tests — speed scaling + merge ordering."""

    def _mgr_with_samples(self, n):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="rep", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.append_samples(
            rid,
            [_make_reading(pid=0x0C, offset_s=i * 1.0,
                           value=1000 + i) for i in range(n)],
        )
        mgr.stop_recording(rid)
        return mgr, rid

    def test_speed_zero_no_sleep(self):
        mgr, rid = self._mgr_with_samples(5)
        runner = CliRunner()
        with patch("motodiag.cli.hardware._time.sleep") as m_sleep:
            result = runner.invoke(
                _make_cli(),
                ["hardware", "log", "replay", str(rid), "--speed", "0"],
            )
            assert result.exit_code == 0
            assert m_sleep.call_count == 0

    def test_speed_one_wall_clock_delta(self):
        mgr, rid = self._mgr_with_samples(3)
        runner = CliRunner()
        with patch("motodiag.cli.hardware._time.sleep") as m_sleep:
            result = runner.invoke(
                _make_cli(),
                ["hardware", "log", "replay", str(rid), "--speed", "1"],
            )
            assert result.exit_code == 0
            # Two deltas between three consecutive 1s-spaced samples.
            # Each is ~1.0 seconds at speed=1.
            for call in m_sleep.call_args_list:
                assert call.args[0] == pytest.approx(1.0, rel=1e-2)

    def test_speed_ten_scaled(self):
        mgr, rid = self._mgr_with_samples(3)
        runner = CliRunner()
        with patch("motodiag.cli.hardware._time.sleep") as m_sleep:
            runner.invoke(
                _make_cli(),
                ["hardware", "log", "replay", str(rid), "--speed", "10"],
            )
            for call in m_sleep.call_args_list:
                assert call.args[0] == pytest.approx(0.1, rel=1e-2)

    def test_pids_filter_skips_other_pids(
        self, db_path, recordings_dir,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="f", pids=["0x0C", "0x05"],
            protocol_name="Mock",
        )
        mgr.append_samples(rid, [
            _make_reading(pid=0x0C, value=1500, offset_s=0),
            _make_reading(pid=0x05, value=90, offset_s=0.5, unit="C"),
        ])
        mgr.stop_recording(rid)

        runner = CliRunner()
        with patch("motodiag.cli.hardware._time.sleep"):
            result = runner.invoke(
                _make_cli(),
                ["hardware", "log", "replay", str(rid),
                 "--speed", "0", "--pids", "0x05"],
            )
        assert result.exit_code == 0
        assert "0x05" in result.output
        assert "0x0C" not in result.output

    def test_merged_order_from_sqlite_and_jsonl(
        self, db_path, recordings_dir,
    ):
        """load_recording yields merged samples in ascending time."""
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="merge", pids=["0x0C"],
            protocol_name="Mock",
        )
        batch = [_make_reading(pid=0x0C, offset_s=i * 0.5,
                               value=1000 + i) for i in range(1500)]
        mgr.append_samples(rid, batch)
        mgr.stop_recording(rid)

        _, iterator = mgr.load_recording(rid)
        samples = list(iterator)
        ts = [s["captured_at"] for s in samples]
        assert ts == sorted(ts)
        assert len(samples) == 1500

    def test_keyboard_interrupt_exits_cleanly(
        self, db_path, recordings_dir,
    ):
        from motodiag.hardware.recorder import RecordingManager
        mgr = RecordingManager()
        rid = mgr.start_recording(
            vehicle_id=None, label="kbi", pids=["0x0C"],
            protocol_name="Mock",
        )
        mgr.append_samples(rid, [
            _make_reading(pid=0x0C, value=1000, offset_s=0),
            _make_reading(pid=0x0C, value=1100, offset_s=1),
        ])
        mgr.stop_recording(rid)

        def _raise_kbi(_):
            raise KeyboardInterrupt()

        runner = CliRunner()
        with patch("motodiag.cli.hardware._time.sleep", side_effect=_raise_kbi):
            result = runner.invoke(
                _make_cli(),
                ["hardware", "log", "replay", str(rid), "--speed", "1"],
            )
        # Ctrl+C in replay → clean exit 0, with an "aborted" message.
        assert result.exit_code == 0
        assert "aborted" in result.output.lower()
