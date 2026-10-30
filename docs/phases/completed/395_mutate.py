"""Phase 395's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/395_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 392's harness, as
394's: exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`T` the paste block's script, `E` the Engineer, `D` the dispatcher, `Q`
Q1, `P` the planners.

No mutation reads live, reaches GitHub or makes a model call. Run it only
when no fleet model-free run is in progress on this machine (F220).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

F = ".claude/skills/fleet/"
TF = ".claude/skills/deploy/through_fleet.py"
EN, DI, QM, CA, XO = (F + "engineer.py", F + "dispatcher.py", F + "quartermaster.py",
                      F + "captain.py", F + "xo.py")


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_TF = pytest("tests/test_phase395_through_fleet.py")
T_EN = pytest("tests/test_phase395_engineer_deploy.py")
T_DI = pytest("tests/test_phase395_dispatcher_deploy.py")
T_Q = pytest("tests/test_phase395_q1.py")

MUTATIONS = [
    # the paste block's script
    ("T1 a branch that changes the deploy tools is not refused",
     [(TF, "touched = [p for p in paths if p.startswith(TOOLS)]", "touched = []")], T_TF),
    ("T2 a branch with no scope file is not refused",
     [(TF, "    if not D.scope_path(co, phase).is_file():", "    if False:")], T_TF),
    ("T3 any answer is a yes",
     [(TF, "    if words.strip().lower() != YES:", "    if False:")], T_TF),
    ("T4 the commit need not be the branch's head",
     [(TF, "    if head != commit:", "    if False:")], T_TF),
    ("T5 the API is stopped whatever database it serves",
     [(TF, "stopped, started = service.serves(db), False", "stopped, started = True, False")],
     T_TF),
    ("T6 the live diff is not committed",
     [(TF, "    if live_diff.is_file():", "    if False:")], T_TF),
    ("T7 verify-live's exit after the apply is ignored",
     [(TF, '    say(text.rstrip())\n    if rc != 0:\n        raise Off("the live database does not '
           'match the change that was approved")\n    return 0\n\n\ndef main',
       '    say(text.rstrip())\n    return 0\n\n\ndef main')], T_TF),
    ("T8 the answer is not saved as typed",
     [(TF, 'f"The operator typed, verbatim:\\n\\n> {words}\\n")', '"")')], T_TF),
    ("T9 a second run applies again",
     [(TF, "    if applied(co, phase):", "    if False:")], T_TF),
    ("T10 the question opens the terminal once, read-write (bug fix #1 undone)",
     [(TF, 'with open("/dev/tty", "w") as out, open("/dev/tty") as tty:\n        out.write(prompt)\n'
           '        out.flush()',
       'with open("/dev/tty", "r+") as tty:\n        tty.write(prompt)\n        tty.flush()')],
     T_TF),
    # the Engineer
    ("E1 a deploy is believed from a dirty clone",
     [(EN, "    fails = _dirty(clone)\n    inp = clone", "    fails = []\n    inp = clone")], T_EN),
    ("E2 a deploy is believed with no scope file",
     [(EN, '    if not (clone / scope).is_file() or not _git(clone, "ls-files", scope):',
       "    if False:")], T_EN),
    ("E3 a deploy's counts are not compared with the model-free run",
     [(EN, "    return fails + _same_run(result, model_free_line)\n\n\ndef verify_after_apply",
       "    return fails\n\n\ndef verify_after_apply")], T_EN),
    ("E4 code may change after the apply",
     [(EN, "    if code:\n        fails.append", "    if False:\n        fails.append")], T_EN),
    ("E5 the answer need not be quoted",
     [(EN, '    elif log is None or f"> {said[-1]}" not in log.read_text(encoding="utf-8"):',
       "    elif log is None:")], T_EN),
    ("E6 an applied migration may change",
     [(EN, '    if MIGRATIONS in _git(clone, "diff", "--name-only", f"{at}..HEAD").split():',
       "    if False:")], T_EN),
    ("E7 a pr-ready's migration need not have gone through the step",
     [(EN, "    fails += migration_changes(clone, phase)\n", "")], T_EN),
    ("E8 a deploy need not say what it does to live",
     [(EN, '    if outcome == "deploy" and not str(r.get("live_change", "")).strip():',
       "    if False:")], T_EN),
    ("E9 the brief lets a deploy close out",
     [(EN, "record (rule 6) and commit it. Then do NOT close out:",
       "record (rule 6) and commit it. Then close out:")], T_EN),
    # the dispatcher
    ("D1 a deploy is taken for a pr-ready",
     [(DI, '        if result["outcome"] == "deploy":\n            return self.engineer_deploy('
           'issue, phase, branch, ident, run, result, rnd)\n', "")], T_DI),
    ("D2 the deploy is not held",
     [(DI, '"commit": head, "why": "deploy"}))', '"commit": head}))')], T_DI),
    ("D3 needs-hands is not added",
     [(DI, '                  lambda: self.gh("issue", "edit", str(issue), "--add-label", '
           '"needs-hands"),', "                  lambda: None,")], T_DI),
    ("D4 verify-live's exit is ignored on the resume",
     [(DI, '        if rc != 0:\n            self.escalate(issue, "engineer", "needs-admiral",\n'
           '                          f"Chief Engineer, phase {phase}: the live database',
       '        if False:\n            self.escalate(issue, "engineer", "needs-admiral",\n'
       '                          f"Chief Engineer, phase {phase}: the live database')], T_DI),
    ("D5 the step's checkout may change any file",
     [(DI, "if not paths <= allowed or through_fleet.deploy_files(phase)[2] not in paths:",
       "if through_fleet.deploy_files(phase)[2] not in paths:")], T_DI),
    ("D6 the close-out after the apply is not held to documents",
     [(DI, 'out = self.engineer_finish(issue, phase, branch, ident, held, result, info["rnd"],\n'
           '                                   after_apply=applied)',
       'out = self.engineer_finish(issue, phase, branch, ident, held, result, info["rnd"])')],
     T_DI),
    ("D7 needs-hands off does not release a deploy hold",
     [(DI, '        if why in ("space", "deploy"):', '        if why == "space":')], T_DI),
    ("D8 the close-out round is not told it is one",
     [(DI, "brief = engineer.session_brief(phase, issue, closeout=True)",
       "brief = engineer.session_brief(phase, issue)")], T_DI),
    ("D9 the block's gh names no repository",
     [(DI, "gh issue edit {issue} -R {REPO} --remove-label", "gh issue edit {issue} --remove-label")],
     T_DI),
    ("D10 the Quartermaster gives Q1 no live check",
     [(DI, "q1 = quartermaster.scope(clone, phase, live_check=lambda: self.live_check(clone, phase))",
       "q1 = quartermaster.scope(clone, phase)")], T_DI),
    # Q1
    ("Q1 a migration passes with no database step",
     [(QM, "    step = database_step(clone, phase, live_check) if deploys else []",
       "    step = []")], T_Q),
    ("Q2 the live diff's own record is not read",
     [(QM, "    if live and (", "    if False and (")], T_Q),
    ("Q3 verify-live's exit is ignored",
     [(QM, "        if rc != 0:\n            why.append(f\"verify-live exits",
       "        if False:\n            why.append(f\"verify-live exits")], T_Q),
    ("Q4 with no live in the fence a migration passes",
     [(QM, "    if live_check is None:\n        why.append", "    if False:\n        why.append")],
     T_Q),
    # the planners
    ("P1 the Captain is not told of the database step",
     [(CA, '- "## The database step", only when the plan adds a migration to',
       '- "## A section", only when the plan adds a migration to')], T_DI),
    ("P2 the XO is not told of the database step",
     [(XO, 'names the database step in a section "## The database step": what the',
       "names the database step in a section: what the")], T_DI),
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
