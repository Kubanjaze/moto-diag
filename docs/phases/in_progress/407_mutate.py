"""Phase 407's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/407_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 388's harness, as
334 used it: exact strings (each must occur once), the tests run after
clearing `__pycache__` (the fleet's folder too), every file restored
whatever happens. Exits 1 if any mutation stays green. An argument runs only
the mutations whose name starts with it.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

DIS = ".claude/skills/fleet/dispatcher.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-p", "no:xdist", "-o", "addopts=", *args]


T_407 = pytest("tests/test_phase407_reshape_asks_first.py")

SCOUT_CALL = ('        self.ask_reshape(issue, "scout", phase,\n'
              '                         (clone / written[0]).read_text(encoding="utf-8"))\n')
CAPTAIN_GUARD = ('        if self.ask_reshape(issue, "captain", phase, step0.read_text(encoding="utf-8")):\n'
                 '            return "reshape: the operator is asked"\n')

MUTATIONS = [
    ("Z1 the scout stage asks nothing", [(DIS, SCOUT_CALL, "")], T_407),
    ("Z2 the plan writer's stage asks nothing", [(DIS, CAPTAIN_GUARD, "")], T_407),
    ("Z3 the helper asks on every word", [(DIS,
     '        if plan_check.classification(step0) != "reshape":\n',
     "        if False:\n")], T_407),
    ("Z4 the helper asks on none", [(DIS,
     '        if plan_check.classification(step0) != "reshape":\n',
     '        if plan_check.classification(step0) != "never":\n')], T_407),
    ("Z5 a reshape leaves no step0:done", [(DIS, SCOUT_CALL,
     '        if self.ask_reshape(issue, "scout", phase,\n'
     '                            (clone / written[0]).read_text(encoding="utf-8")):\n'
     '            return "asked"\n')], T_407),
    ("Z6 the plan writer's guard asks, then goes on to the model", [(DIS,
     '            return "reshape: the operator is asked"\n', "            pass\n")], T_407),
    ("Z7 the reason is not cut at its first sentence", [(DIS,
     '.split(". ")[0]', '.split("\\0")[0]')], T_407),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests", ROOT / ".claude" / "skills"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    commands = []
    for m in chosen:
        if m[2] not in commands:
            commands.append(m[2])
    for command in commands:
        assert run(command) == 0, f"not green before mutating: {command}"
    survivors = []
    for name, edits, command in chosen:
        originals = {}
        try:
            for rel, old, new in edits:
                path = ROOT / rel
                originals.setdefault(rel, path.read_text())
                current = path.read_text()
                assert current.count(old) == 1, f"{name}: the text occurs {current.count(old)} times in {rel}"
                path.write_text(current.replace(old, new))
            code = run(command)
        finally:
            for rel, text in originals.items():
                (ROOT / rel).write_text(text)
        verdict = "red" if code != 0 else "GREEN (survived)"
        print(f"{name}: {verdict}", flush=True)
        if code == 0:
            survivors.append(name)
    for command in commands:
        assert run(command) == 0, f"not green after restoring: {command}"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
