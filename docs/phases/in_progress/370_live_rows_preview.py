"""Phase 370 Step 0: what converting the live session times to UTC would change.

Reads data/motodiag.db read-only (``mode=ro``) and writes nothing. For each
diagnostic session it prints every time field before and after the conversion
option A would apply:

- a naive value with a ``T`` (``2026-09-17T15:22:14.228127``) was written by
  ``session_repo``'s ``datetime.now().isoformat()``: local time on the
  machine that wrote it. It is read as this machine's local time, with that
  date's own offset (EDT, UTC-4, for every live row);
- a naive value with a space (``2026-09-07 17:27:55``) is the column's
  ``CURRENT_TIMESTAMP`` default: already UTC, so only its shape changes;
- the result is ``YYYY-MM-DDTHH:MM:SS.mmm+00:00``, the format Phase 370 writes.

Run: .venv/bin/python docs/phases/in_progress/370_live_rows_preview.py
"""
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ("created_at", "updated_at", "closed_at")


def to_utc(value: str) -> str:
    if " " in value and "T" not in value:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc)
    else:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()  # this machine's zone, that date's offset
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def main() -> int:
    db = Path(sys.argv[1] if len(sys.argv) > 1 else "data/motodiag.db")
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    print(f"database: {db} (read only)")
    print(f"this machine's zone: {time.tzname} ")
    changed = 0
    rows = conn.execute(
        "SELECT id, " + ", ".join(FIELDS) + " FROM diagnostic_sessions ORDER BY id"
    ).fetchall()
    print(f"sessions: {len(rows)}")
    print()
    print("| id | field | before | after |")
    print("|---|---|---|---|")
    for row in rows:
        sid = row[0]
        for name, value in zip(FIELDS, row[1:]):
            if value is None:
                continue
            after = to_utc(value)
            if after != value:
                changed += 1
            print(f"| {sid} | {name} | `{value}` | `{after}` |")
    print()
    print(f"fields that would change: {changed}")
    notes = conn.execute(
        "SELECT COUNT(*) FROM diagnostic_sessions WHERE notes LIKE '[____-__-__T__:__]%' "
        "OR notes LIKE '%' || char(10) || '[____-__-__T__:__]%'"
    ).fetchone()[0]
    print(f"sessions whose notes text carries a [YYYY-MM-DDTHH:MM] stamp (not changed): {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
