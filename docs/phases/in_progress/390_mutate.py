"""Phase 390's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/390_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 389's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`J` the journal, `R` the replay, `S` the steps and markers, `P` the pause and
the prune, `U` the search on start, `H` the held run and the recheck, `F`
free space (F221).

No mutation makes a real model call or reaches GitHub: every stage runs on
389's stand-ins. Run it only when no fleet model-free run is in progress on
this machine (F220).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

DI = ".claude/skills/fleet/dispatcher.py"
JO = ".claude/skills/fleet/journal.py"
RC = ".claude/skills/fleet/rank_call.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_390 = pytest("tests/test_phase390_resume.py", "tests/test_phase390_search.py",
               "tests/test_phase390_resume_contract.py")
T_ALL = pytest("tests/test_phase390_resume.py", "tests/test_phase390_search.py",
               "tests/test_phase390_resume_contract.py", "tests/test_phase389_dispatcher.py",
               "tests/test_phase388_dispatcher.py")
T_KILL = pytest("tests/test_phase390_kill.py")
T_SPACE = pytest("tests/test_phase390_space.py")

MUTATIONS = [
    # the journal
    ("J1 the journal not written before the clone", [(DI,
     "journal.Journal.create(run, record, self.now())", "pass")], T_390),
    ("J2 a paused stage's journal ended", [(DI,
     'if j is not None and outcome != "rate-limited":', "if j is not None:")], T_390),
    ("J3 a call known by its prompt", [(JO,
     'for flag in ("--resume", "-p"):', 'for flag in ("--resume",):')], T_390),
    ("J4 the clone made again on a resume", [(DI,
     'self.step("clone", do)', "do()")], T_390),
    ("J5 a resumed stage's date taken from today", [(DI,
     'today = dt.date.fromisoformat(j.data["started"][:10])',
     'today = self.now().date() + dt.timedelta(days=1)')], T_390),
    # the replay
    ("R1 a finished call made again", [(DI,
     '        if entry.get("done"):', '        if False:')], T_390),
    ("R2 the cut call not resumed", [(DI,
     'return entry.get("session") or next(', 'return None and next(')], T_390),
    ("R3 a replayed call put in the ledger again", [(RC,
     'if not d.get("fleet_replayed"):', "if True:")], T_390),
    ("R4 the cut session resumed without CONTINUE", [(DI,
     'cmd = [cmd[0], "--resume", session, cmd[1], engineer.CONTINUE, *cmd[3:]]',
     'cmd = [cmd[0], "--resume", session, *cmd[1:]]')], T_390),
    ("R5 a session that had ended run again", [(DI,
     "if done is None and self.resumed and session_ended(out):",
     "if done is None and False:")], T_390),
    ("R6 a finished model-free run run again", [(DI,
     "        if saved is not None:", "        if False:")], T_390),
    # the steps and markers
    ("S1 a resumed step does not ask GitHub first", [(DI,
     "        if j.resumed and done is not None:", "        if False:")], T_390),
    ("S2 markers without their run", [(DI,
     'return marker.replace(" -->", f" run={self.journal.run.name} -->", 1)',
     "return marker")], T_390),
    ("S3 the started marker under the dispatcher's prefix", [(DI,
     'STARTED_M = "<!-- fleet-started:"', 'STARTED_M = "<!-- fleet-dispatcher: started"')],
     T_ALL),
    ("S4 the Engineer's PR mode decided again on a resume", [(DI,
     'mode = self.step("pr-mode"', 'mode = (lambda name, f: f())("pr-mode"')], T_390),
    ("S5 the XO reviews again after its verdict", [(DI,
     "        if j.resumed:", "        if False:")], T_390),
    # the pause and the prune
    ("P1 the pause dropped when its stage ends again paused", [(DI,
     'if state.get("paused") == paused:', "if True:")], T_ALL),
    ("P2 prune removes an unfinished run", [(DI,
     "if str(p) not in keep_also and not (j and j.unfinished):",
     "if str(p) not in keep_also:")], T_390),
    ("P3 prune removes an unreadable journal's run", [(DI,
     "continue                      # unreadable: the search on start names it", "pass")],
     T_390),
    ("P4 prune removes a held run", [(DI,
     "continue                      # held for the operator (F220)", "pass")], T_390),
    # the search on start
    ("U1 no search before the first cycle", [(DI,
     "            fleet.recover()", "            pass")], T_390),
    ("U2 the paused run resumed before its reset", [(DI,
     "            if str(j.run) == paused:", "            if False:")], T_390),
    ("U3 a journal resumed on an issue the operator holds", [(DI,
     'if held and not j.done("escalate"):', "if False:")], T_390),
    ("U4 a journal resumed after another stage ran", [(DI,
     "and mine not in first", "and False")], T_390),
    ("U5 a stop said when a stage is due", [(DI,
     "if not self.stalled(n, phase, issue):", "if False:")], T_390),
    ("U6 an open marker never said", [(DI,
     "            if found is None:", "            if True:")], T_390),
    ("U7 the dry run writes", [(DI,
     "            if not dry_run:\n"
     "                self.comment(n, f\"stopped rank={rank} run={run or 'none'}\",",
     "            if True:\n"
     "                self.comment(n, f\"stopped rank={rank} run={run or 'none'}\",")], T_390),
    ("U8 a failed resume not said", [(DI,
     'self.say_stopped(n, rank, f"the resumed stage failed',
     '(lambda *a: None)(n, rank, f"the resumed stage failed')], T_390),
    # the held run and the recheck
    ("H1 a model-free-only failure not held", [(DI,
     "again = not check.ok and not engineer.verify(",
     "again = False and not engineer.verify(")], T_390),
    ("H2 the recheck never due", [(DI,
     'if "build:open" in labels and (held := self.held_for(n)) is not None:',
     'if False and (held := self.held_for(n)) is not None:')], T_390),
    ("H3 the hold kept after the recheck", [(DI,
     'self.step("release", lambda: journal.release(held))', "pass")], T_390),
    ("H4 the recheck due while the operator's stop is not the last word", [(DI,
     "return runs[0] if ranked and ranked[-1].startswith(stop) else None",
     "return runs[0]")], T_390),
    # the real process
    ("K1 a real process's cut call not resumed", [(DI,
     'return entry.get("session") or next(', 'return None and next(')], T_KILL),
    # free space, phase to phase (F221, the operator's added scope)
    ("F1 the floor never read", [(DI,
     "if not self.disks or not self.below(self.free_gb()):", "if True:")], T_SPACE),
    ("F2 no reclaim before a hold", [(DI,
     'self.reclaim("below the floor")', "None")], T_SPACE),
    ("F3 a model-free run not gated", [(DI,
     'raise LowSpace(f"no model-free run: {why}")', "pass")], T_SPACE),
    ("F4 a new stage not gated", [(DI,
     'self.hold_for_space(n, chosen[0], f"no new stage: {why}")\n                    continue',
     "pass")], T_SPACE),
    ("F5 needs-hands not added", [(DI,
     'self.step("space-label", lambda:', '(lambda *a, **k: None)("space-label", lambda:')],
     T_SPACE),
    ("F6 a space hold never due again", [(DI,
     "return runs[0] if spaced and (not later or spaced[0] > max(later)) else None",
     "return None")], T_SPACE),
    ("F7 a space hold due after it was answered", [(DI,
     "return runs[0] if spaced and (not later or spaced[0] > max(later)) else None",
     "return runs[0]")], T_SPACE),
    ("F8 no timer", [(DI,
     "if not merged and self.reclaim_due():", "if False:")], T_SPACE),
    ("F9 a merge not seen", [(DI,
     'merged = [p for p in self.load().get("active", []) if rows.get(p) == roadmap_check.DONE]',
     "merged = []")], T_SPACE),
    ("F10 no close-out reclaim", [(DI,
     "space = self.reclaim(f\"phase {phase}'s close-out\") if check.ok and self.disks else None",
     "space = None")], T_SPACE),
    ("F11 the service not given the disks", [(DI,
     'sweep_hours=getattr(a, "sweep_hours", SWEEP_HOURS), disks=DISKS,',
     'sweep_hours=getattr(a, "sweep_hours", SWEEP_HOURS), disks=None,')], T_SPACE),
    ("F12 a disk that cannot be read passes", [(DI,
     "for name, gb in free.items() if gb is None or gb < SPACE_FLOOR_GB[name]]",
     "for name, gb in free.items() if gb is not None and gb < SPACE_FLOOR_GB[name]]")],
     T_SPACE),
    ("F13 the CLI writes the service's state", [(DI,
     '.reclaim("by hand", record=False)', '.reclaim("by hand")')], T_SPACE),
    ("F14 a low-space stop said as a plain stop", [(DI,
     'out = f"held: {e}"\n            self.hold_for_space(n, rank, str(e))',
     'out = f"held: {e}"\n            self.say_stopped(n, rank, str(e))')], T_SPACE),
    ("F15 an Engineer held for space not kept for the same commit", [(DI,
     '"why": "space"}))', "}))")], T_SPACE),
    ("F16 a recheck held again releases its run", [(DI,
     'if out.startswith("PR "):', "if True:")], T_SPACE),
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
