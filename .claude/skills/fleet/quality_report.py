#!/usr/bin/env python3
"""The weekly page: the code's seven counts on master (Phase 393, K54).

    quality_report.py measure [--root DIR]         # the counts, JSON, model-free
    quality_report.py --print [--root DIR] [--history FILE]

`measure` is what the dispatcher runs in the fence on a clone of master,
with no model and no network. Coverage is not run again here: a full run
is forty minutes, so the page takes the newest "Line coverage of record"
line a phase log on that tree carries, and names the commit it came from.

`page` is pure: this week's counts, last week's and the week before's
(from `quality.jsonl` in the dispatcher's state), an arrow for each, and on
the first line the counts that went the wrong way two weeks running. The
dispatcher posts it each Monday from 08:00 local as a comment on one pinned
issue, "Code health, weekly", in the fleet's name.

`--print` measures the tree it is run in and prints the page, posting
nothing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import code_quality  # noqa: E402

TITLE = "Code health, weekly"
HISTORY = pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet" / "quality.jsonl"

#: (key, what the page calls it, the direction that is better)
COUNTS = (
    ("ruff", "lint findings (ruff)", "down"),
    ("mypy", "type errors (mypy)", "down"),
    ("complex", "functions over McCabe 20", "down"),
    ("big", "files in src/ over 100 KB", "down"),
    ("helpers", "private money and time helpers", "down"),
    ("swallowed", "`except Exception: pass` blocks", "down"),
    ("coverage", "line coverage, % (regression of record)", "up"),
)


def coverage_of_record(root: pathlib.Path) -> tuple[float | None, str | None]:
    """The newest line coverage a phase log records on this tree, by its
    commit's date: (percent, commit), or (None, None)."""
    best: tuple[int, float, str] | None = None
    for log in sorted((root / "docs" / "phases").glob("*/*_phase_log.md")):
        for m in code_quality.COVERAGE_LINE.finditer(log.read_text(encoding="utf-8")):
            r = subprocess.run(["git", "-C", str(root), "show", "-s", "--format=%ct",
                                m.group(2)], capture_output=True, text=True)
            when = int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else 0
            if best is None or when > best[0]:
                best = (when, float(m.group(1)), m.group(2))
    return (best[1], best[2]) if best else (None, None)


def measure(root: pathlib.Path) -> dict:
    out = code_quality.counts(root)
    out["coverage"], out["coverage_commit"] = coverage_of_record(root)
    out["commit"] = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                                   capture_output=True, text=True).stdout.strip()
    return out


def _worse(key: str, new, old) -> bool:
    if new is None or old is None:
        return False
    better = dict((k, d) for k, _, d in COUNTS)[key]
    return new < old if better == "up" else new > old


def _arrow(key: str, new, old) -> str:
    if new is None or old is None:
        return "·"
    if new == old:
        return "→"
    return ("↑" if new > old else "↓") + (" (worse)" if _worse(key, new, old) else " (better)")


def page(now: dict, history: list[dict], day: dt.date) -> str:
    """The page. `history`: earlier weeks, oldest first."""
    last = history[-1] if history else {}
    before = history[-2] if len(history) > 1 else {}
    twice = [label for key, label, _ in COUNTS
             if _worse(key, now.get(key), last.get(key))
             and _worse(key, last.get(key), before.get(key))]
    first = ("Two weeks running the wrong way: " + "; ".join(twice) + "." if twice
             else "Nothing went the wrong way two weeks running.")
    rows = ["| count | this week | last week | |", "|---|---|---|---|"]
    for key, label, _ in COUNTS:
        v, o = now.get(key), last.get(key)
        rows.append(f"| {label} | {'—' if v is None else v} | {'—' if o is None else o} "
                    f"| {_arrow(key, v, o)} |")
    cov = (f"Coverage is the regression of record's, at `{now['coverage_commit']}`."
           if now.get("coverage_commit") else
           "No phase log on master records line coverage yet.")
    return "\n".join([first, "", f"**{TITLE}, {day.isoformat()}**, master at "
                      f"`{now.get('commit', '?')}`.", "", *rows, "", cov,
                      "Measured with no model (`quality_report.py`)."]) + "\n"


def parse_measure(out: str) -> dict | None:
    """`measure`'s JSON from a run's output: its last line that parses."""
    for line in reversed(out.strip().splitlines()):
        try:
            got = json.loads(line)
        except ValueError:
            continue
        if isinstance(got, dict) and "ruff" in got:
            return got
    return None


def first_line(page_text: str) -> str:
    return page_text.splitlines()[0] if page_text else ""


def read_history(path: pathlib.Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="quality_report.py")
    ap.add_argument("cmd", nargs="?", choices=["measure"])
    ap.add_argument("--print", action="store_true", dest="show")
    ap.add_argument("--root", type=pathlib.Path, default=ROOT)
    ap.add_argument("--history", type=pathlib.Path, default=HISTORY)
    a = ap.parse_args(argv)
    if a.cmd == "measure":
        print(json.dumps(measure(a.root.resolve())))
        return 0
    if not a.show:
        ap.error("measure, or --print")
    print(page(measure(a.root.resolve()), read_history(a.history), dt.date.today()), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
