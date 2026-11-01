"""Phase 397, Step 0: F241 re-measured on this machine.

Run from the repository root:
`.venv/bin/python docs/phases/in_progress/397_measure.py [window|knownbad|alive] [N]`

- window: how long 392's planted command takes to print "started", from
  the moment `run_group` starts it, N times idle and N times beside
  4 x nproc busy processes. Prints min, median, 95th percentile and max.
- knownbad: the test as it stands, with `sleep 2` planted before
  `echo started` (the operator's known-bad), run N times; prints how many
  went red. The test file is restored whatever happens.
- alive: a child that escapes the kill (its own process group, through
  bash's job control) is alive; `alive()` as written in the test file
  answers for it, and so does a copy of `alive()` that reads `/proc`
  from a folder that does not exist, as on macOS.

No step reads live, reaches GitHub or makes a model call.
"""
from __future__ import annotations

import os
import pathlib
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
TEST = ROOT / "tests" / "test_phase392_check_limit.py"
NODE = f"{TEST.relative_to(ROOT)}::test_run_group_kills_the_whole_group_and_says_what_it_printed"
SCRIPT = ("#!/bin/bash\nwhile [ \"$1\" != --run ]; do shift; done\n"
          "mkdir -p \"$2/tmp/pytest-of-fleet\"\necho started\nexec sleep 30\n")


def time_to_started(tmp: pathlib.Path) -> float:
    f = tmp / "fence.sh"
    f.write_text(SCRIPT)
    f.chmod(0o755)
    p = subprocess.Popen([str(f), "--run", str(tmp / "r")], start_new_session=True,
                         stdout=subprocess.PIPE, text=True)
    t = time.monotonic()
    line = p.stdout.readline()
    took = time.monotonic() - t
    os.killpg(p.pid, 9)
    p.wait()
    p.stdout.close()
    assert line == "started\n", line
    return took


def summary(xs: list[float]) -> str:
    xs = sorted(xs)
    return (f"n={len(xs)} min={xs[0] * 1000:.1f} ms median={statistics.median(xs) * 1000:.1f} ms "
            f"p95={xs[int(0.95 * (len(xs) - 1))] * 1000:.1f} ms max={xs[-1] * 1000:.1f} ms")


def window(n: int) -> None:
    with tempfile.TemporaryDirectory() as d:
        print("idle:", summary([time_to_started(pathlib.Path(d)) for _ in range(n)]), flush=True)
        hogs = [subprocess.Popen([sys.executable, "-c", "while True: pass"])
                for _ in range(4 * (os.cpu_count() or 1))]
        try:
            time.sleep(1)
            print(f"beside {len(hogs)} busy processes:",
                  summary([time_to_started(pathlib.Path(d)) for _ in range(n)]), flush=True)
        finally:
            for h in hogs:
                h.kill()
                h.wait()


def knownbad(n: int) -> None:
    original = TEST.read_text()
    old = 'echo started\\n"'
    assert original.count(old) == 1, f"{old!r} occurs {original.count(old)} times"
    red = 0
    try:
        TEST.write_text(original.replace(old, 'sleep 2\\necho started\\n"'))
        for i in range(n):
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                "-o", "addopts=", NODE], cwd=ROOT, capture_output=True, text=True)
            red += r.returncode != 0
            last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]
            last += "".join([f"; {ln.strip()}" for ln in r.stdout.splitlines()
                             if ln.startswith("E ")][:1])
            print(f"run {i + 1}: {'red' if r.returncode else 'green'} ({last})", flush=True)
    finally:
        TEST.write_text(original)
    print(f"known-bad (sleep 2 before echo started): {red} of {n} red")


def alive_now(pid: int) -> None:
    sys.path.insert(0, str(ROOT / "tests"))
    sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
    import test_phase392_check_limit as T

    def alive_without_proc(pid: int) -> bool:   # the test's alive() of 2026-10-27, /proc absent
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        stat = pathlib.Path(f"/no-such-proc/{pid}/stat")
        return stat.exists() and stat.read_text().rsplit(")", 1)[1].split()[0] != "Z"

    print(f"pid {pid}: the test's alive() says {T.alive(pid)}; "
          f"with /proc absent (macOS) it says {alive_without_proc(pid)}")


def escaped() -> None:
    with tempfile.TemporaryDirectory() as d:
        pidfile = pathlib.Path(d) / "pid"
        sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
        import dispatcher as D
        f = pathlib.Path(d) / "fence.sh"
        f.write_text(f"#!/bin/bash\nset -m\nsleep 30 >/dev/null 2>&1 & echo $! > {pidfile}\n"
                     "echo started\nwait\n")
        f.chmod(0o755)
        try:
            D.run_group([str(f)], timeout=2, text=True)
        except subprocess.TimeoutExpired as e:
            print(f"run_group timed out as planned; it kept {e.stdout!r}")
        pid = int(pidfile.read_text())
        time.sleep(1)
        try:
            alive_now(pid)
        finally:
            os.kill(pid, 9)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "window"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    {"window": lambda: window(n), "knownbad": lambda: knownbad(n), "alive": escaped}[what]()
