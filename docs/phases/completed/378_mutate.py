"""Phase 378's mutations: each breaks one thing the phase built, and the
check named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/378_mutate.py`
(ROOT is three levels up from in_progress/ or completed/).
373's form, widened for a phase whose checks include a shell script: each
mutation replaces exact strings (each must occur once), in one or more
files, runs its check (pytest, or a command) after clearing `__pycache__`,
and restores every file whatever happens. Prints one line per mutation and
exits 1 if any stayed green. An argument runs only the mutations whose name
starts with it: `D` deploy order (K18), `C` the clock census (K19), `S` the
clock script (K19), `F` findings (K20), `R` folds (K21), `V` verify-live
(K25), `L` labels (K22, K24).
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

DEPLOY = ".claude/skills/deploy/deploy.py"
CENSUS = "tests/support/clock_census.py"
SCRIPT = ".claude/skills/closeout/clock_check.sh"
FINDING = ".claude/skills/finding/finding_check.py"
ROADMAP_CHECK = ".claude/skills/closeout/roadmap_check.py"
VERIFY = ".claude/skills/closeout/verify_phase.sh"
SKILL = ".claude/skills/closeout/SKILL.md"
PNL = "tests/test_phase274_pnl.py"


def pytest(*files: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *files]


ORDER = pytest("tests/test_phase378_deploy_order.py")
CENSUS_T = pytest("tests/test_phase378_test_clock_census.py")
CLOCK = ["sh", SCRIPT]
FINDINGS = pytest("tests/test_phase378_findings_per_repo.py")
FOLDS = pytest("tests/test_roadmap_continuity.py")
LIVE = pytest("tests/test_phase378_verify_live.py")
LABELS = pytest("tests/test_phase378_labels.py")

MUTATIONS = [
    # ------------------------------------------------------------ K18
    ("D1 apply-live never asks for the regression", [(DEPLOY,
     "    problem = regression_problem(repo, phase)\n    if problem:\n        raise Refused(problem)",
     "    problem = None")], ORDER),
    ("D2 code after the regression is allowed", [(DEPLOY,
     "    if after:\n        return (f\"code changed", "    if False:\n        return (f\"code changed")],
     ORDER),
    ("D3 uncommitted code is allowed", [(DEPLOY, "    if pending:", "    if False:")], ORDER),
    ("D4 only src/ and tests/ count as code", [(DEPLOY,
     "    after = code_after_regression.code_paths(\n"
     "        _git_lines(repo, \"diff\", \"--name-only\", f\"{commit}..HEAD\"))",
     "    after = [p for p in _git_lines(repo, \"diff\", \"--name-only\", f\"{commit}..HEAD\")\n"
     "             if p.startswith((\"src/\", \"tests/\"))]")], ORDER),
    # ------------------------------------------------------------ K19, the census
    ("C1 a strftime is never read as a day", [(CENSUS,
     'SECONDS = re.compile(r"%[STfsXcr]")', 'SECONDS = re.compile(r"%")')], CENSUS_T),
    ("C2 every file is exempt", [(CENSUS,
     'FROZEN = re.compile(r"^\\s*(from|import)\\s+support\\.frozen_clock\\b", re.M)',
     'FROZEN = re.compile(r"datetime")')], CENSUS_T),
    ("C3 a name bound to the clock is not followed", [(CENSUS,
     "            kind = bound.get(n.id)", "            kind = None")], CENSUS_T),
    ("C4 the clock plus a timedelta is not followed", [(CENSUS,
     "            cur = par  # a datetime plus or minus a timedelta is still the clock",
     "            return False")], CENSUS_T),
    # ------------------------------------------------------------ K19, the script
    ("S1 274's P&L back on the UTC day turns the script red", [(PNL,
     "TODAY = local_day(datetime.now(timezone.utc).isoformat())",
     'TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")')], CLOCK),
    ("S2 a clock that was not faked is refused, not passed", [(SCRIPT,
     '  SEEN=$(TZ=$ZONE faketime "$MOMENT" "$PY" -B -c "',
     '  SEEN=$(TZ=$ZONE "$PY" -B -c "')], CLOCK),
    # S1 is also the control for the script's `rc=1`: without it, a red moment
    # would leave the script at exit 0 and S1 would survive.
    # ------------------------------------------------------------ K20
    ("F1 B1 back on the union", [(FINDING,
     "    elif own:\n        claimed, actual = int(m.group(1)), max(own)",
     "    elif present:\n        claimed, actual = int(m.group(1)), max(present)")], FINDINGS),
    # ------------------------------------------------------------ K21
    ("R1 roadmap_check stops seeing three-digit folds", [(ROADMAP_CHECK,
     'FOLDED = re.compile(r"^\\s*Folded into (\\d{2,3}[A-Z]?)\\b")',
     'FOLDED = re.compile(r"^\\s*Folded into (\\d{2}[A-Z]?)\\b")')], FOLDS),
    # ------------------------------------------------------------ K25
    ("V1 the backup is opened plainly, leaving -shm", [(DEPLOY,
     '    s = sqlite3.connect(f"file:{src}?mode=ro&immutable=1", uri=True)',
     "    s = _ro(src)")], LIVE),
    ("V2 a masked clock matches nothing", [(DEPLOY,
     "        if va == vb or (va == CLOCK and isinstance(vb, str) and _TIMESTAMP.match(vb)):",
     "        if va == vb:")], LIVE),
    ("V3 a foreign-key break passes", [(DEPLOY,
     '    return 1 if integrity != "ok" or fk else 0', "    return 0")], LIVE),
    ("V4 check 8 does not call verify-live", [(VERIFY,
     '  "$PY" -B "$DIR/../deploy/deploy.py" verify-live "$PHASE"', "  true")], LIVE),
    # ------------------------------------------------------------ K22, K24
    ("L1 the description goes back to seven", [(SKILL,
     "and the eight artefacts that must exist", "and the seven artefacts that must exist")],
     LABELS),
    ("L2 the generator rule goes", [(SKILL,
     "   or whose output a migration loads, is committed in the phase folder with\n",
     "   or whose output a migration loads, is kept wherever it was written, with\n")],
     LABELS),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests", ROOT / ".claude"):
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
