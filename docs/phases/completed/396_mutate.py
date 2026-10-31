"""Phase 396's mutations: each puts one slip back, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/396_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 395's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`A`, `B`, `C` or `D`, the slip.

No mutation reads live, reaches GitHub or makes a model call. Run it only
when no fleet model-free run is in progress on this machine (F220).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

F = ".claude/skills/fleet/"
DI, QM, RT, EN = F + "dispatcher.py", F + "quartermaster.py", F + "red_team.py", F + "engineer.py"
CC = ".claude/skills/closeout/closeout_check.py"
T = "tests/test_phase396_slips.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_A = pytest(T, "-k", "TestA")
T_B = pytest(T, "-k", "TestB")
T_C = pytest(T, "-k", "test_c_")
T_D = pytest(T, "-k", "TestD")

MUTATIONS = [
    # (a) the fenced code check
    ("A1 a command joined with spaces again",
     [(DI, "script = (shlex.join(command) if command else",
       'script = (" ".join(command) if command else')], T_A),
    ("A2 the reason is the output's tail again",
     [(DI, 'why = "" if pr is not None else quartermaster.no_result_why(code.out, ok=code.ok,\n'
           "                                                                    why=code.why)",
       'why = "" if pr is not None else code.why[-300:]')], T_A),
    ("A3 the first error line is not looked for",
     [(QM, "said = next((ln for ln in lines if _ERROR_LINE.search(ln)), lines[-1])",
       "said = lines[-1]")], T_A),
    ("A4 a time limit is not said first",
     [(QM, '    if "time limit" in why:\n        return f"{ended}: {why.strip()[:240]}"\n', "")],
     T_A),
    ("A5 an empty reason is left bare",
     [(QM, "{why.strip() or 'and no reason was given'}", "{why}")], T_A),
    # (b) the refute line
    ("B1 the contradiction is not part of A8",
     [(CC, '        fails += [f"A8 {f}" for f in refute_contradictions(repo, phase)]\n', "")],
     T_B),
    ("B2 a Red Team round in the log is not a record",
     [(CC, "    if block is None and not _RED_TEAM_ROUND.search(log_txt):",
       "    if block is None:")], T_B),
    ("B3 the checklist's own rows are read",
     [(CC, '        log_txt = log_txt[:block.start()] + "\\n" * table.count("\\n") + '
           "rest[len(table):]\n", "")], T_B),
    ("B4 a wrapped line is not found",
     [(CC, r'_NO_REFUTE_CLAIM = re.compile(r"\bno\s+refute\s+pass\b", re.I)',
       r'_NO_REFUTE_CLAIM = re.compile(r"\bno refute pass\b", re.I)')], T_B),
    ("B5 the handoff is not read",
     [(CC, '    texts += [(p, _read(p)) for p in sorted((repo / "docs" / "handoffs")\n'
           '                                            .glob(f"*_{phase}_closed.md"))]\n', "")],
     T_B),
    ("B6 v1.1 is not read",
     [(CC, '             (done / f"{phase}_implementation.md", _read(done / '
           'f"{phase}_implementation.md"))]',
       "             ]")], T_B),
    ("B7 the brief does not tell the Engineer",
     [(EN, "   saying a refute pass did or did not run, in v1.1, the phase log or the\n",
       "   about it, in v1.1, the phase log or the\n")], T_B),
    # (c) the stale plan
    ("C1 the mirror is not refreshed before the next mission",
     [(DI, "            self.update_mirror()\n            entry = self.next_due(self.master_rows())",
       "            entry = self.next_due(rows)")], T_C),
    # (d) the plan of record
    ("D1 the first commit again, whatever the approval",
     [(RT, '    if approved_at is None:\n        out = _git(clone, "log", "--diff-filter=A"',
       '    if True:\n        out = _git(clone, "log", "--diff-filter=A"')], T_D),
    ("D2 the newest plan commit, whatever the approval",
     [(RT, '"-1", f"--before={approved_at}", "--format=%H"', '"-1", "--format=%H"')], T_D),
    ("D3 the Red Team is not given the time",
     [(DI, "            context = red_team.gather(clone, phase, f9.why, scan=scan,\n"
           "                                      approved_at=self.plan_approved_at(issue))",
       "            context = red_team.gather(clone, phase, f9.why, scan=scan)")], T_D),
    ("D4 the Quartermaster is not given the time",
     [(QM, "    pc = red_team.plan_commit(clone, phase, approved_at)",
       "    pc = red_team.plan_commit(clone, phase)")], T_D),
    ("D5 an unapproved plan is called approved",
     [(RT, '            + (f"\\n\\n=== v1.0 as approved ({plan_label(pc, approved_at)}) ===\\n{v10}"\n'
           "               if approved_at is not None else\n"
           '               f"\\n\\n=== v1.0 ({plan_label(pc, approved_at)}) ===\\n{v10}")',
       '            + f"\\n\\n=== v1.0 as approved ({(pc or \'not found\')[:12]}) ===\\n{v10}"')],
     T_D),
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
