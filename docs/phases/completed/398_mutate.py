"""Phase 398's mutations: each puts one stall, or one part of its fix, back,
and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/398_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 396's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it.

No mutation reads live, reaches GitHub or makes a model call. Run it only
when no fleet model-free run is in progress on this machine (F220).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

DI = ".claude/skills/fleet/dispatcher.py"
CC = ".claude/skills/closeout/closeout_check.py"
T = "tests/test_phase398_two_stalls.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


TESTS = pytest(T)

MUTATIONS = [
    ("M1 A5 reads any line holding the prefix again",
     [(CC, "    at = [i for i, ln in enumerate(lines) if ln.startswith(PREFIX)]",
       "    at = [i for i, ln in enumerate(lines) if PREFIX in ln]")], TESTS),
    ("M2 the hold adds no needs-hands",
     [(DI, '        self.escalate(issue, "red-team", "needs-hands",\n'
           '                      f"Red Team, phase {phase}, round {rnd}: clear,',
       '        self.say_stopped(issue, "red-team",\n'
       '                      f"Red Team, phase {phase}, round {rnd}: clear,')], TESTS),
    ("M3 the cleared table is not kept",
     [(DI, '"table": table, "fnum": fnum, "rows": rows}))', '"fnum": fnum, "rows": rows}))')],
     TESTS),
    ("M4 the release runs a new Red Team round",
     [(DI, 'return "red-team", lambda: self.stage_red_record(n, phase, body, branch(), rec)',
       'return "red-team", lambda: self.stage_red_team(n, phase, body, branch())')], TESTS),
    ("M5 the release sets review:clear without pushing",
     [(DI, "            if changed.strip() or self.committed(clone, subject):",
       "            if False:")], TESTS),
    ("M6 a second refusal does not hold again",
     [(DI, "        except Stop as e:\n            return self.hold_record(issue, phase, rnd, str(e))",
       "        except KeyError as e:\n            return self.hold_record(issue, phase, rnd, str(e))")],
     TESTS),
    ("M7 prune_runs deletes a held table",
     [(DI, "            if (p / journal.HELD).is_file():\n"
           "                continue                      # held for the operator (F220)",
       "            if (p / journal.HELD).is_file() and (journal.held(p) or {}).get(\"why\") != \"record\":\n"
       "                continue                      # held for the operator (F220)")], TESTS),
    ("M8 the Engineer's held_for takes a held table",
     [(DI, '                if (journal.held(p) or {}).get("why") != "record"]  # is not the Engineer\'s',
       "                if True]  # is not the Engineer's")], TESTS),
]


def clear_caches() -> None:
    for d in (ROOT / ".claude" / "skills").rglob("__pycache__"):
        for f in d.glob("*.pyc"):
            f.unlink()


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
                assert current.count(old) == 1, \
                    f"{name}: the text occurs {current.count(old)} times in {rel}"
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
