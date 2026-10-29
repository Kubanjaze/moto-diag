"""Phase 393's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/393_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 394's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`R` the ratchet and its counts, `C` the coverage gate, `Q` Q10-Q12, `T` the
Red Team's five questions, `W` the weekly page, `B` the two bug fixes.

No mutation makes a real model call or reaches GitHub. Run it only when no
fleet model-free run is in progress on this machine (F220).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

F = ".claude/skills/fleet/"
CQ, QM, RT, DI = "scripts/code_quality.py", F + "quartermaster.py", F + "red_team.py", \
    F + "dispatcher.py"
QR, YE, RS = F + "quality_report.py", F + "yeoman.py", ".claude/skills/closeout/regression.sh"
RE, ER = "src/motodiag/reporting/renderers.py", "src/motodiag/memory/erase.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_RATCHET = pytest("tests/test_phase393_quality_ratchet.py")
T_CODE = pytest("tests/test_phase393_code_checks.py")
T_RED = pytest("tests/test_phase393_red_team_code.py")
T_WEEK = pytest("tests/test_phase393_quality_report.py")
T_BUGS = pytest("tests/test_phase393_bug_fixes.py")

MUTATIONS = [
    # the ratchet and its counts
    ("R1 a count above its pin holds",
     [("tests/test_phase393_quality_ratchet.py", "    if measured > pin:",
       "    if measured > pin + 10**6:")], T_RATCHET),
    ("R2 a count below its pin holds",
     [("tests/test_phase393_quality_ratchet.py", "    if measured < pin:", "    if False:")],
     T_RATCHET),
    ("R3 a handler naming any error is counted as swallowed",
     [(CQ, 'isinstance(h.type, ast.Name) and h.type.id == "Exception"',
       "isinstance(h.type, ast.Name)")], T_RATCHET),
    ("R4 only _money is a helper",
     [(CQ, 'HELPER_NAMES = frozenset({"_money", "_now", "_now_iso"})',
       'HELPER_NAMES = frozenset({"_money"})')], T_RATCHET),
    ("R5 the size limit is 200 KB",
     [(CQ, "SIZE_LIMIT = 100_000", "SIZE_LIMIT = 200_000")], T_RATCHET),
    ("R6 mypy reads the site-packages",
     [("pyproject.toml", "no_site_packages = true", "no_site_packages = false")], T_RATCHET),
    # the coverage gate
    ("C1 coverage below its pin passes",
     [(CQ, "    if total < pin:", "    if total < pin - 100:")], T_RATCHET),
    ("C2 regression.sh ignores the gate",
     [(RS, '"$HASH") \\\n  || RC=1', '"$HASH") \\\n  || true')], T_RATCHET),
    ("C3 regression.sh measures no coverage",
     [(RS, 'ARGS="$ARGS --cov=motodiag"', 'ARGS="$ARGS"')], T_RATCHET),
    # Q10-Q12
    ("Q1 Q10 counts no new finding",
     [(CQ, "if h.get(p, 0) > bb.get(p, 0):", "if h.get(p, 0) > bb.get(p, 0) + 10**6:")], T_CODE),
    ("Q2 Q10 takes the head's rules",
     [(CQ, 'return b if b.is_file() and "[tool.mypy]" in b.read_text(encoding="utf-8") else \\',
       'return b if False else \\')], T_CODE),
    ("Q3 Q11 passes any coverage",
     [(CQ, '"ok": pct >= CHANGED_COVERAGE', '"ok": True')], T_CODE),
    ("Q4 Q11 passes with no coverage data",
     [(CQ, '        return {"ok": False, "covered": 0, "measured": 0, "percent": None, "worst": [],\n'
           '                "why": "the full run on the head left no coverage data"}',
       '        return {"ok": True, "covered": 0, "measured": 0, "percent": None, "worst": []}')],
     T_CODE),
    ("Q5 Q12 ignores a changed complex function",
     [(CQ, 'if span is not None and changed[f["path"]] & set(span):', "if False:")], T_CODE),
    ("Q6 Q12 lets a file already over the limit grow",
     [(CQ, "if head_size > size_limit and head_size > base_size:",
       "if head_size > size_limit and base_size <= size_limit:")], T_CODE),
    ("Q7 the Quartermaster drops a Q10 failure",
     [(QM, 'q10 = Finding("Q10", not pr["Q10"], "; ".join(', 'q10 = Finding("Q10", True, "; ".join(')],
     T_CODE),
    ("Q8 the stage leaves Q10-Q12 out",
     [(DI, "found = [q1, *found, *self.code_findings(run, clone, head, full)]",
       "found = [q1, *found]")], T_CODE),
    ("Q9 the fenced command runs the head's script",
     [(QM, 'f"git show {base}:{CODE_SCRIPT} > /fleet/run/code_quality.py; "',
       'f"cp {CODE_SCRIPT} /fleet/run/code_quality.py; "')], T_CODE),
    # the Red Team's five questions
    ("T1 the scan misses a swallowed handler",
     [(RT, "if (isinstance(n, ast.ExceptHandler) and n.lineno in lines and _broad(n)\n"
           "                    and _swallows(n)):",
       "if False:")], T_RED),
    ("T2 a no does not make a back",
     [(RT, '"verdict": BACK if nos else v["verdict"]', '"verdict": v["verdict"]')], T_RED),
    ("T3 a missing checklist is allowed",
     [(RT, '        raise Stop("no code checklist")', "        return []")], T_RED),
    ("T4 the stage does not hand the scan to the review",
     [(DI, "clone=clone, run=runner, scan=scan)", "clone=clone, run=runner, scan=None)")], T_RED),
    ("T5 the brief does not ask the questions",
     [(RT, '"{QUESTIONS}", "\\n".join(f"   {k}. {q}" for k, q in QUESTIONS.items()))',
       '"{QUESTIONS}", "")')], T_RED),
    # the weekly page
    ("W1 the page is due any day",
     [(DI, "if now < start or since is None or start < _time(since):",
       "if since is None:")], T_WEEK),
    ("W2 the page is posted every cycle",
     [(DI, 'return None if state.get("last_quality") == monday.isoformat() else monday',
       "return monday")], T_WEEK),
    ("W3 once the wrong way is two weeks running",
     [(QR, "             and _worse(key, last.get(key), before.get(key))]", "             ]")],
     T_WEEK),
    ("W4 the digest gets no line",
     [(YE, "    if quality:\n", "    if False:\n")], T_WEEK),
    ("W5 the page is posted without the fleet's account",
     [(DI, "        if ident is None:\n            self.log(f\"the weekly page for {week}",
       "        if False:\n            self.log(f\"the weekly page for {week}")], T_WEEK),
    # the two bug fixes
    ("B1 the PDF title is escaped as HTML",
     [(RE, '_markup_escape(doc.get("title") or "Report"),',
       '_html_escape(doc.get("title") or "Report"),')], T_BUGS),
    ("B2 the erase swallows every OperationalError",
     [(ER, '    if "no such table" not in str(e):\n        raise e',
       '    if False:\n        raise e')], T_BUGS),
    ("B3 the erase drops no error at all",
     [(ER, '    if "no such table" not in str(e):\n        raise e', "    raise e")], T_BUGS),
]


def clear_caches() -> None:
    for top in (ROOT / ".claude" / "skills", ROOT / "scripts", ROOT / "src"):
        for d in top.rglob("__pycache__"):
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
