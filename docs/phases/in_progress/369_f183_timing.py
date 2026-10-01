"""Phase 369 — F183: did the worker that armed the push guard's alarm die?

For each parallel regression log in ~/.cache/motodiag/regressions/ that ran
test_phase358_wholetree_contract.py's
TestTheWiring::test_an_error_in_the_whole_tree_gate_blocks, this reports:

- the worker that ran it;
- the seconds of that worker's own test time after it, summed from the
  run's JUnit XML (`time` per testcase), up to the worker's last result;
- whether that worker went down ("[gwN] node down"), and on which test.

The alarm `_pre_push_guard.main()` leaves armed is FAST_LIMIT_S + 60 = 345 s.
A worker whose remaining test time reaches 345 s is still alive when it
fires. Test time excludes setup and teardown between tests, so it is a
lower bound on the wall time that passed.

Run: python docs/phases/in_progress/369_f183_timing.py
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

LOGS = Path.home() / ".cache" / "motodiag" / "regressions"
LEAK = ("tests/test_phase358_wholetree_contract.py::TestTheWiring::"
        "test_an_error_in_the_whole_tree_gate_blocks")
ALARM_S = 345
RESULT = re.compile(r"^\[(gw\d+)\] \[ *\d+%\] (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (\S+)")
DOWN = re.compile(r"^\[(gw\d+)\] node down")


def junit_times(xml: Path) -> dict[str, float]:
    times: dict[str, float] = {}
    for case in ET.parse(xml).getroot().iter("testcase"):
        cls = case.get("classname", "")
        name = case.get("name", "")
        times[f"{cls}::{name}"] = float(case.get("time") or 0)
    return times


def key(nodeid: str) -> str:
    """tests/test_x.py::Class::name[p] -> tests.test_x.Class::name[p]"""
    path, _, rest = nodeid.partition("::")
    mod = path[:-3].replace("/", ".")
    parts = rest.split("::")
    return f"{'.'.join([mod] + parts[:-1])}::{parts[-1]}"


def one(log: Path) -> dict | None:
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    worker = start = None
    for i, ln in enumerate(lines):
        m = RESULT.match(ln)
        if m and m.group(3) == LEAK:
            worker, start = m.group(1), i
            break
    if worker is None:
        return None
    xml = log.with_suffix(".xml")
    times = junit_times(xml) if xml.exists() else {}
    after, n, died_on, missing = 0.0, 0, None, 0
    for i in range(start + 1, len(lines)):
        d = DOWN.match(lines[i])
        if d and d.group(1) == worker:
            nxt = RESULT.match(lines[i + 1]) if i + 1 < len(lines) else None
            died_on = nxt.group(3) if nxt else "?"
            break
        m = RESULT.match(lines[i])
        if m and m.group(1) == worker:
            t = times.get(key(m.group(3)))
            if t is None:
                missing += 1
            else:
                after += t
            n += 1
    return {"log": log.name, "worker": worker, "tests_after": n,
            "test_seconds_after": round(after, 1), "missing_times": missing,
            "died_on": died_on}


def main() -> int:
    rows = [r for r in (one(p) for p in sorted(LOGS.glob("*_parallel_*.log"))) if r]
    for r in rows:
        verdict = f"DIED on {r['died_on']}" if r["died_on"] else "survived"
        print(f"{r['log']}: {r['worker']} ran the leak; then {r['tests_after']} tests, "
              f"{r['test_seconds_after']} s of test time "
              f"({r['missing_times']} without a time); {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
