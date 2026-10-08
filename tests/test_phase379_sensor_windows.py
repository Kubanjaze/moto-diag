"""Phase 379, F193 — sensor and drift windows read as the shop's time.

`list_recordings` and the drift queries put a typed `--since`/`--until`
straight into a text comparison, so a typed date was the UTC day: in New
York a 2026-10-07 filter started at 20:00 the evening before. Now the value
goes through 377's `utc_cutoff` and is written in the columns' own shape
(`YYYY-MM-DDTHH:MM:SS+00:00`), so the comparison stays on the index.
"""

from __future__ import annotations

import click
import pytest

from support.frozen_clock import set_zone
from support.phase274 import new_db, seed_bike, sql

ZONE = "America/New_York"


@pytest.fixture
def db(tmp_path):
    set_zone(ZONE)
    path = new_db(tmp_path)
    seed_bike(path, "Honda", "CBR600RR", 2005)
    yield path
    set_zone(None)


def _recording(path, started_at) -> int:
    sql(path, "INSERT INTO sensor_recordings (vehicle_id, started_at, protocol_name, "
              "pids_csv) VALUES (1, ?, 'ISO 15765', '0C')", (started_at,))
    return sql(path, "SELECT MAX(id) FROM sensor_recordings")[0][0]


def test_the_bound_is_the_shops_time_in_the_columns_shape():
    from motodiag.core.timestamps import column_cutoff

    set_zone(ZONE)
    try:
        assert column_cutoff("2026-10-07") == "2026-10-07T04:00:00+00:00"
        assert column_cutoff("2026-10-07T12:00:00+02:00") == "2026-10-07T10:00:00+00:00"
        assert column_cutoff(None) is None
        with pytest.raises(ValueError):
            column_cutoff("last tuesday")
    finally:
        set_zone(None)


def test_a_typed_date_is_the_shops_day(db):
    from motodiag.hardware.recorder import RecordingManager

    evening_before = _recording(db, "2026-10-07T01:00:00.500000+00:00")   # 21:00 EDT on the 6th
    on_the_bound = _recording(db, "2026-10-07T04:00:00+00:00")           # midnight EDT
    just_after = _recording(db, "2026-10-07T04:00:00.250000+00:00")
    found = {r["id"] for r in RecordingManager(db_path=db).list_recordings(since="2026-10-07")}
    assert evening_before not in found
    assert {on_the_bound, just_after} <= found
    until = {r["id"] for r in RecordingManager(db_path=db).list_recordings(until="2026-10-07")}
    assert until == {evening_before, on_the_bound}


def test_the_drift_window_is_the_shops_day(db):
    from motodiag.advanced.drift import compute_trend

    rec = _recording(db, "2026-10-06T00:00:00+00:00")
    for at, value in (("2026-10-07T01:00:00+00:00", 90.0),     # the 6th, in New York
                      ("2026-10-07T05:00:00+00:00", 91.0),
                      ("2026-10-07T06:00:00+00:00", 92.0)):
        sql(db, "INSERT INTO sensor_samples (recording_id, captured_at, pid_hex, value, unit) "
                "VALUES (?, ?, '0x0C', ?, 'rpm')", (rec, at, value))
    result = compute_trend(1, "0C", since="2026-10-07", db_path=db)
    assert result is not None
    assert result.first_captured_at.startswith("2026-10-07T05:00:00")


def test_the_index_is_still_used(db):
    plan = " ".join(str(r) for r in sql(
        db, "EXPLAIN QUERY PLAN SELECT * FROM sensor_recordings WHERE started_at >= ?",
        ("2026-10-07T04:00:00+00:00",)))
    assert "idx_recordings_started" in plan


def test_the_cli_refuses_a_window_backwards_or_unreadable():
    from motodiag.cli.advanced import _check_window

    set_zone(ZONE)
    try:
        with pytest.raises(click.ClickException, match="on or before"):
            _check_window("2026-10-08", "2026-10-07")
        with pytest.raises(click.ClickException, match="since must be"):
            _check_window("soon", None)
        _check_window("2026-10-07", "2026-10-07T23:00:00")
    finally:
        set_zone(None)
