"""Phase 391's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/391_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 390's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`Q` the Quartermaster's checks, `M` the model's answer and the verdict, `D`
the dispatcher's stage, `Y` the digest, `R8` the paste-block rule (F222,
made before Step 0 and mutated here, as the edit guard refused a mutation
loop then).

No mutation makes a real model call or reaches GitHub. Run it only when no
fleet model-free run is in progress on this machine (F220).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

QM = ".claude/skills/fleet/quartermaster.py"
DI = ".claude/skills/fleet/dispatcher.py"
YE = ".claude/skills/fleet/yeoman.py"
RC = ".claude/skills/closeout/roadmap_check.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_Q = pytest("tests/test_phase391_quartermaster.py")
T_D = pytest("tests/test_phase391_dispatcher.py", "tests/test_phase391_contract.py",
             "tests/test_phase389_dispatcher.py", "tests/test_phase390_resume_contract.py")
T_R = pytest("tests/test_roadmap_continuity.py")

MUTATIONS = [
    # Q1 the scope
    ("Q1a a reshape is in scope", [(QM, 'if word not in ("extension", "greenfield"):',
                                    'if word in ("nothing",):')], T_Q),
    ("Q1b a migration is in scope", [(QM, 'why += [f"it changes {p}, a migration" for p in paths if p == MIGRATIONS]',
                                      "why += []")], T_Q),
    ("Q1c content is in scope", [(QM, "if p != MIGRATIONS and p.startswith(CONTENT_PATHS)]",
                                  "if False]")], T_Q),
    ("Q1d data/ is in scope", [(QM, 'for p in paths if p.startswith("data/")]',
                                'for p in paths if p.startswith("nodata/")]')], T_Q),
    ("Q1e a deploy is in scope", [(QM, 'if p.endswith("_dryrun_diff.md")]', 'if p.endswith("_never.md")]')], T_Q),
    # Q2, Q3 the issue
    ("Q2 a hold passes", [(QM, 'Finding("Q2", cap[1].group(1) == MERGE,', 'Finding("Q2", True,')], T_Q),
    ("Q3a a back passes", [(QM, 'elif red[1].group(1) != "clear":', "elif False:")], T_Q),
    ("Q3b a pull request after the clear passes", [(QM, "elif ready is not None and ready[0] > red[0]:",
                                                    "elif False:")], T_Q),
    # Q4 the full run
    ("Q4a the counts not compared", [(QM, "    if mine != theirs:", "    if False:")], T_Q),
    ("Q4b a failed run passes", [(QM, '    if not ok:\n        return Finding("Q4"',
                                  '    if False:\n        return Finding("Q4"')], T_Q),
    # Q5 verify_phase.sh
    ("Q5-2 code after the hash passes", [(QM, 'rule(n, "none (docs only)" in s,', "rule(n, True,")], T_Q),
    ("Q5-3 in_progress not read", [(QM, "rule(n, bool(have) and not left.strip(),", "rule(n, bool(have),")], T_Q),
    ("Q5-4 a hit is a pass", [(QM, 'out.append(Finding(key, True if s.strip() == "none" else None,',
                               "out.append(Finding(key, True,")], T_Q),
    ("Q5-5 A4 not read", [(QM, ' and "A4 ok" in s,', ",")], T_Q),
    ("Q5-6 the words not read", [(QM, 'rule(n, "within cap" in s,', "rule(n, True,")], T_Q),
    ("Q5-10a no summary needed", [(QM, "rule(n, bool(_SUMMARY.search(s)) and not _RED_COUNT.search(s),",
                                   "rule(n, not _RED_COUNT.search(s),")], T_Q),
    ("Q5-10b failures ignored", [(QM, "rule(n, bool(_SUMMARY.search(s)) and not _RED_COUNT.search(s),",
                                  "rule(n, bool(_SUMMARY.search(s)),")], T_Q),
    ("Q5-11 the close-out not read", [(QM, 'rule(n, "closeout complete" in s,', "rule(n, True,")], T_Q),
    ("Q5-12 no refuter block passes", [(QM, 'rule(n, "every row has a verdict, a quote and a page" in s,',
                                        "rule(n, True,")], T_Q),
    ("Q5-13 findings not read", [(QM, 'rule(n, "every cited F-number resolves" in s,', "rule(n, True,")], T_Q),
    ("Q5-14 the command not read", [(QM, 'rule(n, "python -m pytest" in s and "no regression line names" not in s,',
                                     "rule(n, True,")], T_Q),
    ("Q5-x a missing section passes", [(QM, 'out.append(Finding(key, False, "verify_phase.sh printed no such section"))',
                                        "out.append(Finding(key, True))")], T_Q),
    # Q6 - Q9
    ("Q6 claims not checked", [(QM, 'missing = [h for h in claimed if _git(clone, "merge-base", "--is-ancestor", h, tip).returncode]',
                                "missing = []")], T_Q),
    ("Q7a P6's rule dropped", [(QM, 'why = list(plan_check.unfilled(v11)) if v11 else ["no v1.1"]',
                                'why = [] if v11 else ["no v1.1"]')], T_Q),
    ("Q7b Deviations not needed", [(QM, 'for need in ("Deviations", "Results"):', 'for need in ("Results",):')], T_Q),
    ("Q7c an open box passes", [(QM, "    if _BOX.search(v11):", "    if False:")], T_Q),
    ("Q8a no handoff passes", [(QM, 'why.append(f"no docs/handoffs/<date>_{phase}_closed.md")', "pass")], T_Q),
    ("Q8c the sections not read", [(QM, 'for s in ("What is open", "What is next")', "for s in ()")], T_Q),
    ("Q8d roadmap_check not run", [(QM, "why += roadmap_check.check_tree(clone, sib)", "why += []")], T_Q),
    ("Q9a a dirty clone passes", [(QM, '    if dirty:\n        return Finding("Q9"', '    if False:\n        return Finding("Q9"')], T_Q),
    ("Q9b a conflict passes", [(QM, "    if r.returncode != 0:\n        conflicts", "    if False:\n        conflicts")], T_Q),
    # the model's answer and the verdict
    ("M1 an unknown check accepted", [(QM, "    if unknown:\n        raise Stop", "    if False:\n        raise Stop")], T_Q),
    ("M2 a refusal naming none accepted", [(QM, 'if v["verdict"] == REFUSE and not failed:', "if False:")], T_Q),
    ("M3 a merge naming failures accepted", [(QM, 'if v["verdict"] == MERGE and failed:', "if False:")], T_Q),
    ("M4 the model overrides the scripts", [(QM, "return (REFUSE if failed else MERGE), failed, note",
                                             'return (judged["verdict"] if judged else (REFUSE if failed else MERGE)), failed, note')], T_Q),
    ("M5 the model's refusals dropped", [(QM, 'failed += [(f["check"], f["why"]) for f in judged.get("failed", [])',
                                          'failed += [(f["check"], f["why"]) for f in []')], T_Q),
    ("M6 the brief lists no ids", [(QM, '"{IDS}", "\\n".join(f"  {k}: {v}" for k, v in CHECKS.items()))',
                                    '"{IDS}", "")')], T_Q),
    # the dispatcher's stage
    ("D1 out of scope still runs", [(DI, "        if not q1.ok:", "        if False:")], T_D),
    ("D2 quartermaster_since not read", [(DI, "return (since is not None and applied is not None and _time(applied) > _time(since)",
                                          "return (applied is not None")], T_D),
    ("D3 not once per application", [(DI, '                and self.due_for(n, QM, self.markers(QM_M, "quartermaster")))',
                                      "                )")], T_D),
    ("D4 quartermaster_since never set", [(DI, 'if "quartermaster_since" not in state:', "if False:")], T_D),
    ("D5 no full run", [(DI, "            full = self.checked(clone, head, full=True)",
                         "            full = Check(True, head, None)")], T_D),
    ("D6 verify_phase.sh not run", [(DI, "            ver = self.checked(clone, head, full=False,\n"
                                         "                               command=[quartermaster.VERIFY, phase, reg, head])",
                                     "            ver = Check(True, head)")], T_D),
    ("D7 the PR comment made again on a resume", [(DI, 'f"{pr_marker}\\n{text}"),\n                  lambda: self.pr_has_comment(pr["number"], pr_marker))',
                                                   'f"{pr_marker}\\n{text}"))')], T_D),
    ("D8 a command run's output not journaled", [(DI, '"why": c.why, "out": c.out})', '"why": c.why})')], T_D),
    ("D9 the stage not resumed", [(DI, '        if s == "quartermaster":\n            return self.stage_quartermaster',
                                   '        if False:\n            return self.stage_quartermaster')], T_D),
    ("D10 not a rank comment", [(DI, "RED_M, QM_M, *RANK_COMMENT)", "RED_M, *RANK_COMMENT)")], T_D),
    ("D11 a label moved", [(DI, '        record = {"at": self.now().isoformat(timespec="seconds"), "issue": issue,',
                            '        self.label_once(issue, "merged")\n'
                            '        record = {"at": self.now().isoformat(timespec="seconds"), "issue": issue,')], T_D),
    ("D12 the digest gets no verdicts", [(DI, "verdicts=self.verdicts_on(day))", "verdicts=None)")], T_D),
    # the digest
    ("Y1 every verdict agrees", [(YE, 'else "yes" if (v["verdict"] == "merge") == (now == "merged") else "NO")',
                                  'else "yes")')], T_D),
    ("Y2 no section", [(YE, '        out += [""] + shadow(verdicts, run)', "        pass")], T_D),
    # R8, the paste-block rule (F222)
    ("R8a every fenced block read", [(RC, '        if "ALL GOOD" not in body:\n            continue',
                                      "        if False:\n            continue")], T_R),
    ("R8b issue and pr not repository-scoped", [(RC, 'GH_REPO_SCOPED = frozenset({"issue", "pr", ', "GH_REPO_SCOPED = frozenset({")], T_R),
    ("R8c -R not read", [(RC, 'GH_NAMED = re.compile(r"(?:^|\\s)(?:-R|--repo)(?:\\s+|=)\\S+")',
                          'GH_NAMED = re.compile(r"(?!)")')], T_R),
    ("R8d a cd or GH_REPO first not read", [(RC, "ctx = GH_CONTEXT.search(body, 0, at) or",
                                             "ctx = False and GH_CONTEXT.search(body, 0, at) or")], T_R),
    ("R8e a comment is a call", [(RC, '            if line.lstrip().startswith("#"):\n                continue',
                                  "            if False:\n                continue")], T_R),
    ("R8f an api placeholder passes", [(RC, 'if not re.search(r"\\{owner\\}|\\{repo\\}|:owner\\b|:repo\\b", args):',
                                        "if True:")], T_R),
    ("R8g phase documents not read", [(RC, '    for sub in ("handoffs", "phases"):\n        d = docs / sub',
                                       '    for sub in ("handoffs",):\n        d = docs / sub')], T_R),
    ("R8h R8 not run on the tree", [(RC, 'history=read(root / "implementation.md"), pastes=paste_documents(root))',
                                     'history=read(root / "implementation.md"))')], T_R),
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
