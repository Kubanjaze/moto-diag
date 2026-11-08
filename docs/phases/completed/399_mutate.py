"""Phase 399's mutations: each puts one part of F254 or F255 back, and a test
must go red.

Run from the repository root: `.venv/bin/python docs/phases/completed/399_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 398's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it.

**Every run is under a throwaway HOME, with FLEET_LEDGER and FLEET_STATE
unset**, so a mutation that breaks the fixture or the check writes only
into that HOME, never the operator's ledger (the prompt's "run under a
throwaway HOME"). Only ~/.gitconfig is copied in, for the tests that
commit. No mutation reads live, reaches GitHub or makes a model call. Run it
only when `pgrep -x bwrap` is empty (F220).
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]

LG = "tests/support/ledger_guard.py"
RC = ".claude/skills/fleet/rank_call.py"
DI = ".claude/skills/fleet/dispatcher.py"
T = "tests/test_phase399_cost_ledger.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-p", "no:xdist", "-o", "addopts=", *args]


TESTS = pytest(T)

MUTATIONS = [
    ("M1 the fixture sets no ledger of its own",
     [(LG, '    os.environ["FLEET_LEDGER"] = '
           'str(_cost_ledger_dir / f"calls_{next(_count)}.jsonl")',
       "    pass")], TESTS),
    ("M2 the check never fails the run",
     [(LG, "    session.exitstatus = pytest.ExitCode.TESTS_FAILED", "    pass")], TESTS),
    ("M3 the check takes every appended row for the fleet's",
     [(LG, "        if not sid or sid not in known:", "        if False:")], TESTS),
    ("M4 the check misses a rewrite of the existing rows",
     [(LG, "    if after[:len(before)] != before:", "    if False:")], TESTS),
    ("M5 readers keep the stand-in's rows",
     [(RC, '    return row.get("session_id") == STAND_IN_SESSION', "    return False")], TESTS),
    ("M6 a rank's line names no stage",
     [(RC, '    ctx = getattr(run, "ledger_context", None)', "    ctx = None")], TESTS),
    ("M7 the Engineer's session is not recorded as it ends",
     [(DI, "        self.ledger_session(cmd, out, time.monotonic() - start)\n", "")], TESTS),
    ("M8 a session read back is recorded again (no key check)",
     [(RC, '    if c.key and any(r.get("key") == c.key for r in rows(path, stand_ins=True)):',
       "    if False:")], TESTS),
    ("M9 the search on start does not read kept folders in",
     [(DI, "        self.ledger_read_in(dry_run=dry_run)\n", "")], TESTS),
    ("M10 the read-in keys a session differently from the live write",
     [(DI, "                                       run=p.name, source=\"read-in\")",
       "                                       run=p.name + \"/\", source=\"read-in\")")], TESTS),
    ("M12 the fixture asks for monkeypatch again (its first version)",
     [(LG, "def _never_the_real_cost_ledger(_cost_ledger_dir):",
       "def _never_the_real_cost_ledger(_cost_ledger_dir, monkeypatch):")], TESTS),
    ("M11 a cut stage's resume does not write the missing row",
     [(DI, "            self.ledger_session(cmd, out, None)\n", "")], TESTS),
]


def env_with_throwaway_home() -> dict:
    home = pathlib.Path(tempfile.mkdtemp(prefix="399_mutate_home_"))
    git = pathlib.Path.home() / ".gitconfig"
    if git.is_file():
        shutil.copy(git, home / ".gitconfig")
    env = {k: v for k, v in os.environ.items() if k not in ("FLEET_LEDGER", "FLEET_STATE")}
    env["HOME"] = str(home)
    return env


def clear_caches() -> None:
    for top in (ROOT / ".claude" / "skills", ROOT / "tests"):
        for d in top.rglob("__pycache__"):
            for f in d.glob("*.pyc"):
                f.unlink()


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                          env=env_with_throwaway_home()).returncode


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
