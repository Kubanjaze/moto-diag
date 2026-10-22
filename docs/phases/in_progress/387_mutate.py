"""Phase 387's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/387_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 384's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`P` the checklist, `X` the XO and the shared call, `Y` the Yeoman, `L` the
labels.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

PC = ".claude/skills/fleet/plan_check.py"
XO = ".claude/skills/fleet/xo.py"
RC = ".claude/skills/fleet/rank_call.py"
YE = ".claude/skills/fleet/yeoman.py"
LA = ".claude/skills/fleet/labels.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_PC = pytest("tests/test_phase387_fleet_contract.py")
T_XO = pytest("tests/test_phase387_xo.py")
T_YE = pytest("tests/test_phase387_yeoman.py")

MUTATIONS = [
    ("P1 a row that is not in progress passes", [(PC,
     "    elif status[phase] != ACTIVE:", "    elif False:")], T_PC),
    ("P2 a missing step-0 report passes", [(PC,
     '        fail("P2", [f"no {step0_path}"])', "        pass")], T_PC),
    ("P3 a count with no query passes", [(PC,
     "        if found and not QUERY.search(b.text)", "        if False and found and not QUERY.search(b.text)")], T_PC),
    ("P3 a number naming a phase is a count", [(PC,
     "or _YEAR.match(num) or _NAMING.search(before)", "or _YEAR.match(num) or False")], T_PC),
    ("P3 a table's lead is not read", [(PC,
     'and not (b.kind == "row" and QUERY.search(b.lead))', "and not False")], T_PC),
    ("P4 reshape passes", [(PC, '        elif word == "reshape":', "        elif False:"),
                           (PC, 'not in ("greenfield", "extension"):',
                            'not in ("greenfield", "extension", "reshape"):')], T_PC),
    ("P4 no classification passes", [(PC,
     """        if word is None:
            fail("P4", ["the step-0 report has no 'Classification:' line"])""",
     """        if word is None:
            pass""")], T_PC),
    ("P5 a data/ path passes", [(PC,
     '("a path under data/", _DATA_PATH.search(body)),', '("a path under data/", None),')], T_PC),
    ("P5 the knowledge path passes", [(PC,
     "next((p for p in seed_paths if p in body), None)", "None")], T_PC),
    ("P5 seed data passes", [(PC, '("seed data", _SEED_PHRASE.search(body)),',
                              '("seed data", None),')], T_PC),
    ("P5 a split passes", [(PC, '("a split", _SPLIT.search(body)),', '("a split", None),')], T_PC),
    ("P5 an eval protocol passes", [(PC, '("an eval protocol", _EVAL.search(body))',
                                     '("an eval protocol", None)')], T_PC),
    ("P5 the Non-goals are read", [(PC,
     "    body = without_sections(plan, _NON_GOALS)", "    body = plan")], T_PC),
    ("P6 an empty section passes", [(PC, "        if not content:", "        if False:")], T_PC),
    ("P6 a stub passes", [(PC, "            if _STUB.match(ln.strip()):", "            if False:")], T_PC),
    ("P6 Goal and Logic not required", [(PC,
     "for r in REQUIRED_SECTIONS\n", "for r in ()\n")], T_PC),
    ("P7 a cited path need not exist", [(PC,
     "ok = any(any(src.exists(p) for p in _paths(b.text)) for b in citing)",
     "ok = any(any(True for p in _paths(b.text)) for b in citing)")], T_PC),
    ("P7 'no check' accepted for any entry", [(PC,
     "            _TEXT_ONLY.search(body) and any(", "            True and any(")], T_PC),
    ("P7 only two entries cited", [(PC,
     "    newest = changelog(claude_md)[:3]", "    newest = changelog(claude_md)[:2]")], T_PC),
    ("P7 the oldest entries taken", [(PC,
     "key=lambda e: e[0], reverse=True)", "key=lambda e: e[0], reverse=False)")], T_PC),
    ("P8 no stop section passes", [(PC, "    if not secs:\n        return [",
                                    "    if False:\n        return [")], T_PC),
    ("P8 any stop is a kind", [(PC, "            for b in bullets if not any(",
                                "            for b in bullets if False and not any(")], T_PC),
    ("P9 --no-pin ignored", [(PC,
     "    pinned = WRITTEN_BEFORE.get(phase, frozenset()) if pin else frozenset()",
     "    pinned = WRITTEN_BEFORE.get(phase, frozenset())")], T_PC),
    ("P9 387 pinned too", [(PC, '    "386": frozenset({"P7", "P8"}),\n}',
                           '    "386": frozenset({"P7", "P8"}),\n    "387": frozenset({"P3"}),\n}')], T_PC),
    ("P9 cannot read is exit 1", [(PC, '        print(f"plan_check {a.phase}: CANNOT READ")\n        return 2',
                                   '        print(f"plan_check {a.phase}: CANNOT READ")\n        return 1')], T_PC),

    ("X1 approve sets the wrong label", [(XO,
     'LABEL = {APPROVE: "plan:approved",', 'LABEL = {APPROVE: "plan:needs-review",')], T_XO),
    ("X2 three rounds", [(XO, "MAX_ROUNDS = 2", "MAX_ROUNDS = 3")], T_XO),
    ("X3 rounds not counted", [(XO, "for v, _ in _MARKER.findall(b) if v == BACK)",
                                "for v, _ in _MARKER.findall(b) if False)")], T_XO),
    ("X4 a failed checklist still calls the model", [(XO,
     "        if not report.ok:", "        if False:")], T_XO),
    ("X5 back-to-captain with no items", [(XO,
     '    if v["verdict"] == BACK and not items:', "    if False:")], T_XO),
    ("X6 the old plan label stays", [(XO,
     "        if old != label and old in have:", "        if False:")], T_XO),
    ("X7 Bash not disallowed", [(RC, '"--disallowedTools", "Bash", ', "")], T_XO),
    ("X8 Bash among the tools", [(RC, 'FENCE = ("--tools", "Read,Grep,Glob",',
                                  'FENCE = ("--tools", "Read,Grep,Glob,Bash",')], T_XO),
    ("X9 no usage is not a stop", [(RC, "or sum(counts) == 0:", "or False:")], T_XO),
    ("X10 the wrong model accepted", [(RC, "    if model not in served:", "    if False:")], T_XO),
    ("X11 no structured output accepted", [(RC,
     '    if schema is not None and not isinstance(d.get("structured_output"), dict):',
     "    if False:")], T_XO),
    ("X12 a failed claude accepted", [(RC,
     "    if r.returncode != 0:\n        raise Stop(f\"claude exited",
     "    if False:\n        raise Stop(f\"claude exited")], T_XO),
    ("X13 the call goes unrecorded", [(RC, "    record(c, ledger)\n", "")], T_XO),

    ("Y1 any --kid accepted", [(YE, '    if kid is not None and kid != f"K{nxt}":', "    if False:")], T_YE),
    ("Y2 unresolved K-ids accepted", [(YE,
     '    unresolved = sorted({int(n) for n in _KID_CITED.findall(words + " " + check)} - known)',
     "    unresolved = []")], T_YE),
    ("Y3 the triage bullets not read", [(YE, r'|- \*\*K(\d+)\b)", re.M)',
                                         r'|- \*\*K(\d+)\bNOPE)", re.M)')], T_YE),
    ("Y4 a missing path accepted", [(YE, 'and not (root / p.split("::")[0]).exists()]',
                                     "and False]")], T_YE),
    ("Y5 a pipe not escaped", [(YE, '    cell = lambda s: s.replace("|", "\\\\|")',
                                "    cell = lambda s: s")], T_YE),
    ("Y6 a two-day window", [(YE, "    end = start + dt.timedelta(days=1)",
                              "    end = start + dt.timedelta(days=2)")], T_YE),
    ("Y7 closed findings counted open", [(YE, "        if _CLOSED.search(rest):\n            continue",
                                          "        if False:\n            continue")], T_YE),
    ("Y8 every issue shown", [(YE, '            if i["state"] == "OPEN" or start <= upd < end:',
                               "            if True:")], T_YE),
    ("Y9 an empty summary written", [(YE, "    if not summary:", "    if False:")], T_YE),
    ("Y10 the digest on Opus", [(YE, '{body}", HAIKU,', '{body}", rank_call.OPUS,')], T_YE),

    ("L1 labels forced", [(LA, '"--description", desc], run=run)',
                           '"--description", desc, "--force"], run=run)')], T_PC),
    ("L2 an existing label made again", [(LA, "        if name in before:", "        if False:")], T_PC),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests", ROOT / ".claude", ROOT / "scripts", ROOT / "ops"):
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
