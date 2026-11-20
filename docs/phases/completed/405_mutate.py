"""Phase 405's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/405_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 388's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green, or if a control meant to stay green goes red. An argument runs
only the mutations whose name starts with it: `T` the touched set, `G` the
gaps half, `E` the entries, `H` approved_holds.

Every test it runs uses fixture databases; none reads live.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

DEP = ".claude/skills/deploy/deploy.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T405 = "tests/test_phase405_what_the_change_did.py"
T_NEW = pytest(T405)
T_KEPT = pytest(T405, "tests/test_phase358_deploy_contract.py",
                "tests/test_phase383_server_writes.py", "tests/test_phase385_server_writes.py",
                "tests/test_phase395_through_fleet.py")
T_378_CLOCK = pytest("tests/test_phase378_verify_live.py::"
                     "test_a_masked_clock_matches_any_timestamp_and_nothing_else")
T_379 = pytest("tests/test_phase379_verify_live_fails.py::"
               "test_a_live_row_the_approved_diff_lacks_is_listed")

UNION = ("    for p in sorted(a):\n", "    for p in sorted(set(a) | set(b)):\n")

MUTATIONS = [
    ("T1 the touched set is every table of the backup (the old rule)", [(DEP,
     "drift_gate(bk, db, approved, touched(scope, approved, names))",
     "drift_gate(bk, db, approved, set(dump(bk)))")], T_NEW),
    ("T2 the touched set is empty", [(DEP,
     "drift_gate(bk, db, approved, touched(scope, approved, names))",
     "drift_gate(bk, db, approved, set())")], T_NEW),
    ("T2b the touched set is empty: the kept controls", [(DEP,
     "drift_gate(bk, db, approved, touched(scope, approved, names))",
     "drift_gate(bk, db, approved, set())")],
     pytest("tests/test_phase358_deploy_contract.py", "tests/test_phase383_server_writes.py",
            "tests/test_phase385_server_writes.py", "tests/test_phase395_through_fleet.py")),
    ("T3 an index's table left out of the touched set", [(DEP,
     "            elif obj in names:\n                out.add(names[obj])\n", "")], T_NEW),
    ("T4 the names read from the backup, not the migrated copy", [(DEP,
     "names = {**tbl_names(bk), **tbl_names(fresh)}", "names = tbl_names(bk)")], T_NEW),
    ("G1 shape_gaps finds no gap", [(DEP,
     "    a, b = _leaves(approved), _leaves(now)\n", "    return []\n")], T_NEW),
    ("G2 shape_gaps walks the union of both sides again", [(DEP, *UNION)], T_NEW),
    ("G3 the clock rule dropped from shape_gaps", [(DEP,
     "if va == vb or (va == CLOCK and isinstance(vb, str) and _TIMESTAMP.match(vb)):",
     "if va == vb:")], T_NEW),
    ("G3b the clock rule dropped: 378's test", [(DEP,
     "if va == vb or (va == CLOCK and isinstance(vb, str) and _TIMESTAMP.match(vb)):",
     "if va == vb:")], T_378_CLOCK),
    ("E1 entries keeps the schema's lists whole", [(DEP,
     'if path == ("schema",) and isinstance(v, list):', "if False:")], T_NEW),
    ("E2 entries keeps empty dicts", [(DEP, "            if w != {}:\n",
                                       "            if True:\n")], T_NEW),
    ("E2b entries keeps empty dicts: 379's old shape", [(DEP, "            if w != {}:\n",
                                                         "            if True:\n")], T_379),
    ("E3 entries keeps a changed field's list whole", [(DEP,
     'elif len(path) == 4 and path[0] == "rows" and path[2] == "changed" \\',
     "elif False \\")], T_NEW),
    ("H1 approved_holds calls shape_gaps on an approved diff with no entries", [(DEP,
     "gaps = shape_gaps(ea, eb) if ea else []", "gaps = shape_gaps(ea, eb)")], T_NEW),
]

#: A mutation under which a test must stay GREEN: 378's clock test alone
#: does not hold the narrowed walk (the plan's G2 note).
CONTROLS = [
    ("C1 the union walk: 378's clock test stays green", [(DEP, *UNION)], T_378_CLOCK),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests", ROOT / ".claude" / "skills" / "deploy"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode


def mutated(name: str, edits: list[tuple[str, str, str]], command: list[str]) -> int:
    originals: dict[str, str] = {}
    try:
        for rel, old, new in edits:
            path = ROOT / rel
            originals.setdefault(rel, path.read_text())
            current = path.read_text()
            assert current.count(old) == 1, \
                f"{name}: the text occurs {current.count(old)} times in {rel}"
            path.write_text(current.replace(old, new))
        return run(command)
    finally:
        for rel, text in originals.items():
            (ROOT / rel).write_text(text)


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    commands: list[list[str]] = []
    for m in chosen + CONTROLS:
        if m[2] not in commands:
            commands.append(m[2])
    for command in commands:
        assert run(command) == 0, f"not green before mutating: {command}"
    survivors = []
    for name, edits, command in chosen:
        code = mutated(name, edits, command)
        print(f"{name}: {'red' if code != 0 else 'GREEN (survived)'}", flush=True)
        if code == 0:
            survivors.append(name)
    broken = []
    for name, edits, command in ([] if argv else CONTROLS):
        code = mutated(name, edits, command)
        print(f"{name}: {'green, as expected' if code == 0 else 'RED (not expected)'}", flush=True)
        if code != 0:
            broken.append(name)
    for command in commands:
        assert run(command) == 0, f"not green after restoring: {command}"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red; "
          f"{len(CONTROLS) - len(broken) if not argv else 0}/{len(CONTROLS) if not argv else 0} "
          "controls green")
    return 1 if survivors or broken else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
