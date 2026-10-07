"""Phase 377 Step 0: what converting the live rows' naive local times would change.

Read-only. Opens the database given (default: data/motodiag.db) with
``mode=ro`` and writes nothing. For every column a Phase 377 writer stamps,
it prints each value in the defect shape (naive ``YYYY-MM-DDTHH:MM:SS...``,
written by the old ``datetime.now().isoformat()``, so local time) beside
what Phase 370's ``to_utc`` makes of it. A value with a space is SQLite's
``CURRENT_TIMESTAMP``, already UTC, and is counted but not listed.

    python docs/phases/in_progress/377_live_rows_preview.py [db_path]
"""

from __future__ import annotations

import re
import sqlite3
import sys

from motodiag.core.timestamps import to_utc

NAIVE_LOCAL = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d(:\d\d(\.\d+)?)?$")

# Each table with a column a Phase 377 writer stamps, and those columns.
STAMPED = {
    "customers": ("created_at", "updated_at"),
    "vehicles": ("created_at", "updated_at"),
    "work_orders": ("opened_at", "started_at", "completed_at", "closed_at", "updated_at"),
    "issues": ("resolved_at", "updated_at"),
    "intake_visits": ("updated_at", "closed_at"),
    "repair_plans": ("created_at", "updated_at", "approved_at", "completed_at"),
    "appointments": ("updated_at",),
    "shops": ("updated_at",),
    "workflow_templates": ("created_at", "updated_at"),
    "customer_bikes": ("assigned_at",),
    "users": ("created_at",),
    "performance_baselines": ("last_rebuilt_at",),
    "known_issues": ("created_at",),
}
LISTED_IN_FULL = 50


def main(db_path: str) -> None:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    print(f"database {db_path}, schema "
          f"{conn.execute('SELECT MAX(version) FROM schema_version').fetchone()[0]}")
    total = 0
    for table, columns in STAMPED.items():
        # rowid: customer_bikes has a two-column key and no id.
        rows = conn.execute(f"SELECT rowid, {', '.join(columns)} FROM {table} ORDER BY rowid").fetchall()
        changes = [(row[0], name, value, to_utc(value))
                   for row in rows for name, value in zip(columns, row[1:])
                   if value is not None and NAIVE_LOCAL.match(str(value))]
        print(f"\n{table}: {len(rows)} rows, {len(changes)} fields in the defect shape")
        for name in columns:
            n = sum(1 for c in changes if c[1] == name)
            if n:
                print(f"  {name}: {n}")
        if len(changes) <= LISTED_IN_FULL:
            for row_id, name, before, after in changes:
                print(f"  | {row_id} | {name} | {before} | {after} |")
        else:
            first, last = changes[0], changes[-1]
            print(f"  first: | {first[0]} | {first[1]} | {first[2]} | {first[3]} |")
            print(f"  last:  | {last[0]} | {last[1]} | {last[2]} | {last[3]} |")
        total += len(changes)
    print(f"\ntotal fields in the defect shape: {total}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/motodiag.db")
