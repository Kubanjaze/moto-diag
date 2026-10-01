"""Usage written on the 1st of a month counts toward that month (Phase 281, bug fix #2).

`intake_usage_log.created_at` is SQLite's CURRENT_TIMESTAMP (UTC,
"YYYY-MM-DD HH:MM:SS"). The month start was local isoformat() ("…T00:00:00"),
and " " sorts before "T", so a row written on the 1st was never counted: the
quota and budget alert ignored the 1st's photo identifications all month.
Found when the regression of record ran on 2026-10-01 and five Phase 122
quota tests failed on master too.
"""

from __future__ import annotations

from datetime import datetime, timezone

from motodiag.core.database import get_connection, init_db
from motodiag.intake.vehicle_identifier import VehicleIdentifier


def _identifier(tmp_path):
    path = str(tmp_path / "intake.db")
    init_db(path)
    with get_connection(path) as conn:
        user = conn.execute("INSERT INTO users (username) VALUES ('rider')").lastrowid
    return path, user, VehicleIdentifier(db_path=path)


def _log(path, user, created_at):
    with get_connection(path) as conn:
        conn.execute("INSERT INTO intake_usage_log (user_id, kind, created_at) "
                     "VALUES (?, 'identify', ?)", (user, created_at))


def test_a_row_written_on_the_first_counts(tmp_path):
    path, user, ident = _identifier(tmp_path)
    first = datetime.now(timezone.utc).strftime("%Y-%m-01 00:00:01")
    _log(path, user, first)
    assert ident._count_this_month(user) == 1


def test_a_row_the_database_stamps_itself_counts(tmp_path):
    path, user, ident = _identifier(tmp_path)
    with get_connection(path) as conn:
        conn.execute("INSERT INTO intake_usage_log (user_id, kind) VALUES (?, 'identify')",
                     (user,))
    assert ident._count_this_month(user) == 1


def test_last_months_rows_do_not_count(tmp_path):
    path, user, ident = _identifier(tmp_path)
    now = datetime.now(timezone.utc)
    year, month = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
    _log(path, user, f"{year:04d}-{month:02d}-28 23:59:59")
    assert ident._count_this_month(user) == 0
