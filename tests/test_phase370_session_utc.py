"""Phase 370 — F10: diagnostic session times stored in UTC.

Until 370, ``session_repo`` stamped sessions with naive local time while the
monthly quota's month start was UTC. On a month's last evening in a US
timezone (local still the 31st, UTC already the 1st) a new session counted
toward neither month, and gate 9's lifecycle and six Phase 178 quota tests
failed. Every test here runs at that moment: 2026-10-31 21:42:07 EDT,
which is 2026-11-01 01:42:07 UTC, with ``TZ=America/New_York``.

The planted return to local time is ``370_mutate.py``'s first mutation.
"""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from motodiag.core import session_repo
from motodiag.core.database import init_db
from motodiag.core.migrations import apply_pending_migrations, get_migration_by_version, rollback_to_version
from motodiag.core.session_repo import (
    _month_start_iso,
    add_fault_code_to_session,
    add_symptom_to_session,
    append_note,
    close_session,
    count_sessions_this_month_for_owner,
    create_session,
    create_session_for_owner,
    get_session,
    list_sessions_for_owner,
    reopen_session,
    set_diagnosis,
    update_session,
)
from motodiag.core.timestamps import local_display, to_utc, utc_now
from support.frozen_clock import CLOCKED, frozen_datetime, set_zone

REPO = Path(__file__).resolve().parent.parent
ZONE = "America/New_York"
EVENING = datetime(2026, 11, 1, 1, 42, 7, 123456, tzinfo=timezone.utc)   # 2026-10-31 21:42:07 EDT
OCTOBER_EVENING = datetime(2026, 10, 31, 23, 30, tzinfo=timezone.utc)   # 2026-10-31 19:30 EDT
STORED = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$")
OWNER = 1

# Gate 9's lifecycle and the Phase 178 tests that failed at this moment
# before 370 (Step 0, S0-3), plus the three that passed then.
AT_THAT_MOMENT = [
    "tests/test_phase184_gate9.py::TestGate9HappyPath::test_full_lifecycle",
    "tests/test_phase178_session_api.py::TestQuota",
    "tests/test_phase178_session_api.py::TestSessionEndpointsHappy::test_empty_list_response",
    "tests/test_phase178_session_api.py::TestSessionEndpointsErrors::test_quota_exceeded_returns_402",
    "tests/test_phase178_session_api.py::TestSessionEndpointsErrors::test_shop_tier_bigger_quota",
]


@pytest.fixture
def clock(monkeypatch):
    """Freeze the session clock at ``EVENING`` in New York; ``clock(instant)``
    moves it. TZ is restored, and tzset called, afterwards."""
    previous = os.environ.get("TZ")
    set_zone(ZONE)

    def at(instant: datetime) -> None:
        frozen = frozen_datetime(instant)
        for name in CLOCKED:
            monkeypatch.setattr(f"{name}.datetime", frozen)

    at(EVENING)
    yield at
    monkeypatch.undo()
    set_zone(previous)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase370.db")
    init_db(path)
    return path


class TestTheMoment:
    def test_the_moment_straddles_the_month(self, clock):
        local = session_repo.datetime.now()
        utc = session_repo.datetime.now(timezone.utc)
        assert (local.month, local.day) == (10, 31)
        assert (utc.month, utc.day) == (11, 1)

    def test_a_local_stamp_written_then_is_not_counted(self, clock, db):
        """The control on the rig: at this moment a naive local stamp, what
        the code wrote before 370, falls outside the month."""
        sid = create_session_for_owner(OWNER, "X", "Y", 2000, db_path=db)
        with sqlite3.connect(db) as conn:
            conn.execute("UPDATE diagnostic_sessions SET created_at = ? WHERE id = ?",
                         (session_repo.datetime.now().isoformat(), sid))
        assert count_sessions_this_month_for_owner(OWNER, db_path=db) == 0


class TestTheRightMonth:
    def test_a_session_created_then_counts_toward_november(self, clock, db):
        sid = create_session_for_owner(OWNER, "X", "Y", 2000, db_path=db)
        assert get_session(sid, db_path=db)["created_at"] == "2026-11-01T01:42:07.123+00:00"
        assert _month_start_iso() == "2026-11-01T00:00:00.000+00:00"
        assert count_sessions_this_month_for_owner(OWNER, db_path=db) == 1

    def test_one_created_earlier_that_evening_counts_toward_october(self, clock, db):
        clock(OCTOBER_EVENING)
        create_session_for_owner(OWNER, "X", "Y", 2000, db_path=db)
        assert count_sessions_this_month_for_owner(OWNER, db_path=db) == 1
        clock(EVENING)
        assert count_sessions_this_month_for_owner(OWNER, db_path=db) == 0


class TestEveryWriter:
    def test_every_session_time_is_stored_in_utc(self, clock, db):
        expected = "2026-11-01T01:42:07.123+00:00"
        a = create_session("Honda", "CBR", 2005, db_path=db)
        b = create_session_for_owner(OWNER, "Honda", "CBR", 2005, db_path=db)
        assert get_session(a, db_path=db)["created_at"] == expected
        assert get_session(b, db_path=db)["created_at"] == expected

        for write in (
            lambda: update_session(a, {"diagnosis": "stator"}, db_path=db),
            lambda: update_session(a, {"status": "diagnosed"}, db_path=db),
            lambda: add_symptom_to_session(a, "no charge", db_path=db),
            lambda: add_fault_code_to_session(a, "P0562", db_path=db),
            lambda: set_diagnosis(a, "stator", confidence=0.8, db_path=db),
            lambda: reopen_session(a, db_path=db),
            lambda: append_note(a, "checked", db_path=db),
        ):
            with sqlite3.connect(db) as conn:
                conn.execute("UPDATE diagnostic_sessions SET updated_at = NULL WHERE id = ?", (a,))
            write()
            assert get_session(a, db_path=db)["updated_at"] == expected

        close_session(a, db_path=db)
        row = get_session(a, db_path=db)
        assert row["closed_at"] == expected and row["updated_at"] == expected

    def test_utc_now_is_the_stored_format(self):
        assert STORED.match(utc_now())

    def test_a_note_is_stamped_local_with_its_offset(self, clock, db):
        sid = create_session("Honda", "CBR", 2005, db_path=db)
        append_note(sid, "checked", db_path=db)
        assert get_session(sid, db_path=db)["notes"] == "[2026-10-31T21:42-04:00] checked"


class TestTheGatesAtThatMoment:
    def test_gate9_lifecycle_and_the_178_quota_tests_pass(self):
        env = {**os.environ,
               "MOTODIAG_FROZEN_UTC": EVENING.isoformat(),
               "MOTODIAG_FROZEN_TZ": ZONE,
               "PYTHONPATH": os.pathsep.join(filter(None, [str(REPO / "tests"),
                                                            os.environ.get("PYTHONPATH")]))}
        result = subprocess.run(
            [sys.executable, "-m", "pytest", *AT_THAT_MOMENT,
             "-p", "support.frozen_clock", "-p", "no:cacheprovider", "-p", "no:xdist"],
            cwd=REPO, env=env, capture_output=True, text=True, timeout=600,
        )
        assert "frozen clock: local 2026-10-31T21:42:07.123456 (America/New_York)" in result.stdout, \
            result.stdout[-2000:]
        assert result.returncode == 0, result.stdout[-3000:]
        assert re.search(r"\b10 passed\b", result.stdout), result.stdout[-2000:]


class TestTheReaders:
    def test_cli_show_prints_local_time(self, clock):
        from motodiag.cli.diagnose import _short_ts

        assert _short_ts("2026-11-01T01:42:07.123+00:00") == "2026-10-31T21:42:07"
        assert _short_ts("2026-09-17T15:22:14.228127") == "2026-09-17T15:22:14"   # before 370: local
        assert _short_ts(None) == "-"

    def test_cli_list_shows_local_time_and_filters_by_the_local_day(self, clock, db, monkeypatch):
        from motodiag.cli.main import cli
        from motodiag.core.config import reset_settings

        monkeypatch.setenv("MOTODIAG_DB_PATH", db)
        reset_settings()
        try:
            create_session("Honda", "CBR", 2005, db_path=db)   # 21:42 local on the 31st
            runner = CliRunner()
            shown = runner.invoke(cli, ["diagnose", "list", "--until", "2026-10-31"])
            assert shown.exit_code == 0, shown.output
            # Rich folds the column at 80 characters; UTC would read 2026-11-01T01:4.
            assert "2026-10-31T21:4" in shown.output
            later = runner.invoke(cli, ["diagnose", "list", "--since", "2026-11-01"])
            assert "No sessions match" in later.output
            bad = runner.invoke(cli, ["diagnose", "list", "--since", "yesterday"])
            assert bad.exit_code != 0
        finally:
            reset_settings()

    def test_the_report_timeline_prints_local_time(self, clock, db):
        from motodiag.reporting.builders import build_session_report_doc

        sid = create_session_for_owner(OWNER, "Honda", "CBR", 2005, db_path=db)
        close_session(sid, db_path=db)
        doc = build_session_report_doc(sid, OWNER, db_path=db)
        timeline = next(s for s in doc["sections"] if s.get("heading") == "Timeline")
        rows = dict(timeline["rows"])
        assert rows["Created"] == rows["Closed"] == "2026-10-31T21:42:07"

    def test_client_memory_dates_by_the_local_day(self, clock):
        from motodiag.memory.compile import _date_of

        assert _date_of("2026-11-01T01:42:07.123+00:00") == "2026-10-31"
        assert _date_of("2026-04-18T14:22:07.113") == "2026-04-18"
        assert _date_of(None) == ""

    def test_the_api_since_compares_in_utc(self, clock, db):
        from motodiag.api.routes.sessions import _parse_since

        assert _parse_since("2026-10-31T21:00:00-04:00") == "2026-11-01T01:00:00.000+00:00"
        assert _parse_since("2026-11-01T01:00:00Z") == "2026-11-01T01:00:00.000+00:00"
        assert STORED.match(_parse_since("2d"))
        create_session_for_owner(OWNER, "Honda", "CBR", 2005, db_path=db)
        assert len(list_sessions_for_owner(
            OWNER, since_iso=_parse_since("2026-10-31T21:00:00-04:00"), db_path=db)) == 1
        assert list_sessions_for_owner(
            OWNER, since_iso=_parse_since("2026-10-31T22:00:00-04:00"), db_path=db) == []

    def test_local_display_leaves_a_naive_or_unparsable_value_alone(self, clock):
        assert local_display("2026-09-07 17:27:55") == "2026-09-07 17:27:55"
        assert local_display("not a time") == "not a time"
        assert local_display(None) is None


class TestMigration079:
    ROWS = [
        # (created_at, updated_at, closed_at) before 079 → after
        (("2026-09-17T15:22:14.228127", "2026-09-17T15:22:35.263866", "2026-09-17T15:22:35.263866"),
         ("2026-09-17T19:22:14.228+00:00", "2026-09-17T19:22:35.263+00:00", "2026-09-17T19:22:35.263+00:00")),
        (("2026-09-07 17:27:55", None, None),
         ("2026-09-07T17:27:55.000+00:00", None, None)),
        (("2026-01-15T09:00:00", None, None),                      # EST: UTC-5
         ("2026-01-15T14:00:00.000+00:00", None, None)),
        (("2026-11-01T01:42:07.123+00:00", None, None),            # already stored by 370's code
         ("2026-11-01T01:42:07.123+00:00", None, None)),
    ]

    def _planted(self, db) -> list[int]:
        rollback_to_version(78, db)
        ids = []
        with sqlite3.connect(db) as conn:
            for before, _ in self.ROWS:
                ids.append(conn.execute(
                    "INSERT INTO diagnostic_sessions (vehicle_make, vehicle_model, vehicle_year, "
                    "status, created_at, updated_at, closed_at) VALUES ('X', 'Y', 2000, 'open', ?, ?, ?)",
                    before).lastrowid)
        return ids

    def _times(self, db, ids) -> list[tuple]:
        with sqlite3.connect(db) as conn:
            return [conn.execute("SELECT created_at, updated_at, closed_at FROM diagnostic_sessions "
                                 "WHERE id = ?", (i,)).fetchone() for i in ids]

    def test_the_three_shapes_are_converted(self, clock, db):
        ids = self._planted(db)
        apply_pending_migrations(db)
        assert self._times(db, ids) == [after for _, after in self.ROWS]

    def test_a_second_run_changes_nothing(self, clock, db):
        from motodiag.core.timestamps import convert_session_times_079

        ids = self._planted(db)
        apply_pending_migrations(db)
        with sqlite3.connect(db) as conn:
            assert convert_session_times_079(conn) == 0
        assert self._times(db, ids) == [after for _, after in self.ROWS]

    def test_the_rollback_returns_naive_local_time(self, clock, db):
        ids = self._planted(db)
        apply_pending_migrations(db)
        rollback_to_version(78, db)
        assert self._times(db, ids)[0] == ("2026-09-17T15:22:14.228", "2026-09-17T15:22:35.263",
                                           "2026-09-17T15:22:35.263")
        assert self._times(db, ids)[2][0] == "2026-01-15T09:00:00.000"

    def test_it_changes_no_schema(self):
        migration = get_migration_by_version(79)
        assert migration.post_apply == "motodiag.core.timestamps:convert_session_times_079"
        assert not re.search(r"\b(CREATE|ALTER|DROP)\b", migration.upgrade_sql + migration.rollback_sql)

    def test_to_utc_reads_this_machines_zone_for_a_naive_t_value(self, clock):
        assert to_utc("2026-06-13T00:04:48.958638") == "2026-06-13T04:04:48.958+00:00"
