"""Phase 397's mutations and known-bad cases, on Linux and on macOS.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/397_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 396's harness:
exact strings (each must occur once), the tests run after clearing caches,
every file restored whatever happens. An argument runs only the cases whose
name starts with it (`M`, `K`, `O`, or one name such as `M4`).

- M*: each must turn the test red.
- K1: the known-bad that the fixed test must stay green on, three times.
- O*: master's file before this phase (`48cf7ca`), for the record: on
  `sleep 2` it must go red; on an escaped child it goes red where /proc
  exists (Linux) and stays green where it does not (macOS), which is the
  weakness this phase fixes.

Exits 1 if a mutation stays green, K1 goes red, or an O case differs from
what this system should give. M2 takes about five minutes: with only the
direct child killed, the planted `sleep 300` holds the output open, and
the run ends only when it does.

No case reads live, reaches GitHub or makes a model call. Run it only when
no fleet model-free run is in progress on this machine (F220).
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
DI = ".claude/skills/fleet/dispatcher.py"
T = "tests/test_phase392_check_limit.py"
OLD_COMMIT = "48cf7ca"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_KILL = pytest(T, "-k", "kills_the_whole_group")
T_ALIVE = pytest(T, "-k", "alive_answers")

SLEEP2 = (T, 'echo started\\n"', 'sleep 2\\necho started\\n"')
ESCAPE = (T, 'f"sleep 300 & echo $! > {pidfile}\\nwait\\n"',
          'f"set -m; sleep 30 >/dev/null 2>&1 & echo $! > {pidfile}\\nwait\\n"')

MUTATIONS = [
    ("M1 what was printed is lost",
     [(DI, "raise subprocess.TimeoutExpired(argv, timeout, out, err) from None",
       "raise subprocess.TimeoutExpired(argv, timeout, out[:0], err) from None")], T_KILL),
    ("M2 only the direct child is killed",
     [(DI, "                os.killpg(p.pid, signal.SIGKILL)", "                p.kill()")],
     T_KILL),
    ("M3 the run outlives its bound",
     [(DI, "out, err = p.communicate(timeout=timeout)",
       "out, err = p.communicate(timeout=timeout + 40)")], T_KILL),
    ("M4 a child escapes the group (b's known-bad)", [ESCAPE], T_KILL),
    ("M5 alive() answers 'ended' without asking",
     [(T, 'return bool(state) and not state.startswith("Z")', "return False")], T_ALIVE),
    ("M6 a zombie counts as alive",
     [(T, 'return bool(state) and not state.startswith("Z")', "return bool(state)")], T_ALIVE),
    ("M7 the windows do not widen, sleep 2 planted",
     [(T, "WINDOWS = (1, 2, 4, 8, 16, 32)", "WINDOWS = (1,)"), SLEEP2], T_KILL),
    ("M8 a window counts before its child is reached, sleep 2 planted",
     [(T, 'if pidfile.is_file() and pidfile.read_text().endswith("\\n"):', "if True:"), SLEEP2],
     T_KILL),
]

KEEP_GREEN = [("K1 sleep 2 before echo started", [SLEEP2], T_KILL)]

HAS_PROC = pathlib.Path("/proc/self/stat").exists()
OLD = [
    ("O1 master's old test, sleep 2 planted", [SLEEP2], "red"),
    ("O2 master's old test, a child escapes the group", [ESCAPE], "red" if HAS_PROC else "green"),
]


def clear_caches() -> None:
    for top in (ROOT / ".claude" / "skills", ROOT / "tests"):
        for d in top.rglob("__pycache__"):
            for f in d.glob("*.pyc"):
                if top.name != "tests" or "test_phase392_check_limit" in f.name:
                    f.unlink()


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode


def applied(edits, command: list[str], base: dict[str, str] | None = None) -> int:
    """`command`'s exit with `edits` made (to `base`'s text where given),
    every file restored afterwards."""
    originals: dict[str, str] = {}
    try:
        for rel, text in (base or {}).items():
            originals.setdefault(rel, (ROOT / rel).read_text())
            (ROOT / rel).write_text(text)
        for rel, old, new in edits:
            path = ROOT / rel
            originals.setdefault(rel, path.read_text())
            current = path.read_text()
            assert current.count(old) == 1, f"{old!r} occurs {current.count(old)} times in {rel}"
            path.write_text(current.replace(old, new))
        return run(command)
    finally:
        for rel, text in originals.items():
            (ROOT / rel).write_text(text)


def main(argv: list[str]) -> int:
    def chosen(cases):
        return [c for c in cases if not argv or c[0].startswith(argv[0])]

    print(f"{sys.platform}, /proc {'present' if HAS_PROC else 'absent'}", flush=True)
    for command in (T_KILL, T_ALIVE):
        assert run(command) == 0, f"not green before mutating: {command}"
    bad = []
    ms = chosen(MUTATIONS)
    for name, edits, command in ms:
        t = time.monotonic()
        code = applied(edits, command)
        print(f"{name}: {'red' if code else 'GREEN (survived)'} ({time.monotonic() - t:.0f} s)",
              flush=True)
        if code == 0:
            bad.append(name)
    for name, edits, command in chosen(KEEP_GREEN):
        codes = [applied(edits, command) for _ in range(3)]
        print(f"{name}: {sum(c == 0 for c in codes)} of 3 green", flush=True)
        if any(codes):
            bad.append(name)
    olds = chosen(OLD)
    if olds:
        old_text = subprocess.run(["git", "show", f"{OLD_COMMIT}:{T}"], cwd=ROOT, check=True,
                                  capture_output=True, text=True).stdout
        for name, edits, expected in olds:
            code = applied(edits, T_KILL, base={T: old_text})
            got = "red" if code else "green"
            print(f"{name}: {got} (expected {expected} here)", flush=True)
            if got != expected:
                bad.append(name)
    for command in (T_KILL, T_ALIVE):
        assert run(command) == 0, f"not green after restoring: {command}"
    print(f"{len(ms) - sum(n in bad for n, _, _ in ms)}/{len(ms)} mutations red; "
          f"{'all as expected' if not bad else 'NOT as expected: ' + ', '.join(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main(sys.argv[1:]))
