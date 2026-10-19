"""Phase 382, V-A: the 6 videos' file_path moves from the Mac's tree to live's.

Run from the repository root, on the machine live.json names:
    .venv/bin/python docs/phases/in_progress/382_video_paths.py dryrun
    .venv/bin/python docs/phases/in_progress/382_video_paths.py apply-live

There is no schema migration (live and the code are both at 86), so
`deploy.py`'s command line, which applies the code's pending migrations,
would change nothing. This passes the rewrite to `deploy.dryrun` and
`deploy.apply_live` as their `migrate` step; every refusal of the deploy
skill still runs, against `382_deploy_scope.json`. The apply goes through
this script too: `deploy.py apply-live 382` would migrate nothing and be
refused, since its fresh run would not equal the approved diff.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "deploy"))

import deploy as D  # noqa: E402

OLD = "/Users/lilquant/Projects/moto-diag/data/videos/"
NEW = "/home/lilcu/motodiag/live/videos/"
ROWS = 6


def rewrite(path: pathlib.Path) -> list[int]:
    """Swap the prefix on exactly the 6 rows whose file is on this machine; no migration runs."""
    c = sqlite3.connect(path)
    try:
        rows = c.execute("select id, file_path from videos where substr(file_path, 1, ?) = ?",
                         (len(OLD), OLD)).fetchall()
        if len(rows) != ROWS:
            raise SystemExit(f"{len(rows)} videos carry {OLD}, not {ROWS}")
        for vid, old in rows:
            new = NEW + old[len(OLD):]
            if not pathlib.Path(new).is_file():
                raise SystemExit(f"video {vid}: {new} is not a file on this machine")
            c.execute("update videos set file_path = ? where id = ? and file_path = ?", (new, vid, old))
        c.commit()
    finally:
        c.close()
    return []


def main(argv: list[str]) -> int:
    if argv not in (["dryrun"], ["apply-live"]):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        if argv == ["dryrun"]:
            return D.dryrun("382", migrate=rewrite)
        return D.apply_live("382", migrate=rewrite)
    except D.L.LiveElsewhere as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return D.L.REFUSED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
