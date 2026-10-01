"""F183 reproduction, run by Phase 281 at the operator's request (2026-10-01).

Both regression crashes (274's at 3b7528f, 281's at 4faa46b) lost a worker
with no traceback in test_phase359_content_cleanup.py's round-trip test
while gate 2's tests ran on another worker; 281's trial-run loss was a
gate 2 test. This runs the two files together, repeatedly, until a
deadline, alternating two modes:

- `xdist`: one pytest with `-n 2 --dist load` over both files; a crash is
  xdist's "node down" / "crashed worker" line.
- `pair`: two plain pytest processes side by side (`-p no:xdist`), one per
  file, so each one's own exit code is recorded. A negative return code is
  the signal that killed it; a run with no summary line exited before
  pytest finished.

A third mode, `hammer`, runs six plain processes at once over only the
round-trip test, so a native crash inside SQLite shows as a signal.

Usage (repository root): .venv/bin/python docs/phases/in_progress/281_f183_repro.py OUT.jsonl MINUTES [hammer]
Appends one JSON line per run; prints a line per run.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FILES = ["tests/test_phase359_content_cleanup.py", "tests/test_phase78_gate2_integration.py"]
BASE = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts="]
# `-q` prints "40 passed in 217.17s (0:03:37)" with no banner. (The first
# version required the "=====" banner, so the 2026-10-01 run's own records
# say summary=false throughout; the analysis re-reads each run's tail.)
SUMMARY = re.compile(r"\b\d+ (passed|failed|error)\b.* in [\d.]+s")


def _tail(text: str, n: int = 6) -> list[str]:
    return [l for l in text.strip().splitlines()[-n:]]


def run_xdist() -> dict:
    started = time.monotonic()
    p = subprocess.run(BASE + ["-n", "2", "--dist", "load"] + FILES, cwd=ROOT,
                       capture_output=True, text=True)
    out = p.stdout + p.stderr
    crashed = re.findall(r"worker '(gw\d+)' crashed while running '([^']+)'", out)
    return {"mode": "xdist", "returncode": p.returncode, "seconds": round(time.monotonic() - started),
            "crashed": crashed, "node_down": out.count("node down"),
            "summary": bool(SUMMARY.search(out)), "tail": _tail(out)}


def run_pair() -> dict:
    started = time.monotonic()
    procs = [subprocess.Popen(BASE + ["-p", "no:xdist", f], cwd=ROOT, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True) for f in FILES]
    results = []
    for f, p in zip(FILES, procs):
        out, _ = p.communicate()
        results.append({"file": f, "returncode": p.returncode,
                        "signal": -p.returncode if p.returncode < 0 else None,
                        "summary": bool(SUMMARY.search(out)), "tail": _tail(out, 3)})
    return {"mode": "pair", "seconds": round(time.monotonic() - started), "procs": results}


ROUND_TRIP = ("tests/test_phase359_content_cleanup.py::TestTheMigration::"
              "test_the_round_trip_restores_the_workflow_tables")
HAMMER_PROCS = 6


def run_hammer() -> dict:
    """Six plain pytest processes at once, each running only the round-trip
    test that two of the three crashes were in (a rollback through 078..072)."""
    started = time.monotonic()
    procs = [subprocess.Popen(BASE + ["-p", "no:xdist", ROUND_TRIP], cwd=ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
             for _ in range(HAMMER_PROCS)]
    results = []
    for p in procs:
        out, _ = p.communicate()
        results.append({"returncode": p.returncode,
                        "signal": -p.returncode if p.returncode < 0 else None,
                        "summary": bool(SUMMARY.search(out)), "tail": _tail(out, 3)})
    return {"mode": "hammer", "seconds": round(time.monotonic() - started), "procs": results}


def main(out_path: str, minutes: float, mode: str = "alternate") -> int:
    deadline = time.monotonic() + minutes * 60
    out = Path(out_path)
    i = 0
    while time.monotonic() < deadline:
        i += 1
        if mode == "hammer":
            record = run_hammer()
            record["run"] = i
            record["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with out.open("a") as fh:
                fh.write(json.dumps(record) + "\n")
            codes = [r["returncode"] for r in record["procs"]]
            print(f"{i} hammer {record['seconds']}s rcs={codes}", flush=True)
            continue
        record = run_xdist() if i % 2 else run_pair()
        record["run"] = i
        record["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with out.open("a") as fh:
            fh.write(json.dumps(record) + "\n")
        if record["mode"] == "xdist":
            bad = record["crashed"] or record["node_down"] or not record["summary"]
            print(f"{i} xdist rc={record['returncode']} {record['seconds']}s "
                  f"{'CRASH ' + str(record['crashed']) if bad else 'ok'}", flush=True)
        else:
            parts = [f"{Path(r['file']).name}: rc={r['returncode']} summary={r['summary']}"
                     for r in record["procs"]]
            print(f"{i} pair {record['seconds']}s " + "; ".join(parts), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], float(sys.argv[2]), *(sys.argv[3:4])))
