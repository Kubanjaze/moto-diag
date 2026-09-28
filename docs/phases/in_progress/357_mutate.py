"""Phase 357's mutations: each breaks one thing the phase promises, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/357_mutate.py`
(the path moves to completed/ at close-out). 356's form: each mutation
replaces one exact string (which must occur once), runs its tests with `-B`
after clearing `__pycache__`, and restores the file whatever happens. Prints
one line per mutation and exits 1 if any stayed green. An argument runs only
the mutations whose name starts with it (`F172`, `F175`, `RUN`).
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
DEPLOY = ".claude/skills/deploy/deploy.py"
DEPLOY_TESTS = ["tests/test_phase357_deploy_exact.py", "tests/test_phase358_deploy_contract.py",
                "tests/test_phase359_deploy_to.py"]
WHOLETREE = ".claude/skills/closeout/wholetree.py"
WHOLETREE_TESTS = ["tests/test_phase357_wholetree_ledger.py",
                   "tests/test_phase358_wholetree_contract.py"]
CLI = "src/motodiag/cli/workflow.py"
REPO = "src/motodiag/workflows/run_repo.py"
MIGRATIONS = "src/motodiag/core/migrations.py"
MAIN = "src/motodiag/cli/main.py"
RUN_TESTS = ["tests/test_phase357_saved_runs.py"]

MUTATIONS = [
    ("F172-M1 apply-live ignores a fresh run that differs from the approved diff", DEPLOY,
     "    if gaps:\n        raise Refused(f\"a fresh dry run differs",
     "    if False:\n        raise Refused(f\"a fresh dry run differs", DEPLOY_TESTS),
    ("F172-M2 no clock value is masked", DEPLOY,
     "    return CLOCK if abs(t - clock) <= dt.timedelta(days=1) else v",
     "    return v", DEPLOY_TESTS),
    ("F172-M3 every timestamp is masked, whatever its date", DEPLOY,
     "    return CLOCK if abs(t - clock) <= dt.timedelta(days=1) else v",
     "    return CLOCK", DEPLOY_TESTS),
    ("F172-M4 a diff with no exact block is accepted", DEPLOY,
     "    if approved is None:\n        raise Refused(",
     "    if approved is None:\n        return head\n        raise Refused(", DEPLOY_TESTS),
    ("F172-M5 the exact diff leaves out schema objects", DEPLOY,
     "{\"rows\": rows, \"schema\": {**sch, \"sql\": objects}}",
     "{\"rows\": rows}", DEPLOY_TESTS),
    ("F172-M6 an unnamed schema change is in scope", DEPLOY,
     "        if names != named:\n            probs.append(f\"schema",
     "        if False:\n            probs.append(f\"schema", DEPLOY_TESTS),
    ("F175-M1 full mode leaves out the ledger class", WHOLETREE,
     " + c[\"outside\"] + c[\"ledger\"])", " + c[\"outside\"])", WHOLETREE_TESTS),
    ("F175-M2 a support module with a function counts as a ledger", WHOLETREE,
     "        if kinds & {ast.Assign, ast.AnnAssign} and kinds <= {",
     "        if kinds & {ast.Assign, ast.AnnAssign} or kinds <= {", WHOLETREE_TESTS),
    ("F175-M3 a data module no member imports counts as a ledger", WHOLETREE,
     "        ledgers = [m for m in data if any(_imports([m]).search(t) for t in texts.values())]",
     "        ledgers = list(data)", WHOLETREE_TESTS),
    ("F175-M4 ledger tests join fast mode", WHOLETREE,
     "    return [f for f in c[\"code\"]\n",
     "    return [f for f in c[\"code\"] + c[\"ledger\"]\n", WHOLETREE_TESTS),
    ("RUN-M1 the walk saves no answer", CLI,
     "_walk(console, template, items, save=_saver(run[\"id\"]))",
     "_walk(console, template, items, save=None)", RUN_TESTS),
    ("RUN-M2 a bike stored with another powertrain is not refused", CLI,
     "    if stored and stored != powertrain:", "    if False:", RUN_TESTS),
    ("RUN-M3 finish allows unanswered items", REPO,
     "        if open_items:\n", "        if False:\n", RUN_TESTS),
    ("RUN-M4 resume asks every item again", CLI,
     "items = [_walkable(r) for r in rows if r[\"result\"] is None]",
     "items = [_walkable(r) for r in rows]", RUN_TESTS),
    ("RUN-M5 a finished run accepts a new answer", REPO,
     "        if run[\"status\"] == \"complete\":\n            raise RunRefused(f\"Run #{run_id} is finished",
     "        if False:\n            raise RunRefused(f\"Run #{run_id} is finished", RUN_TESTS),
    ("RUN-M6 a skip on a required item reaches the database", REPO,
     "        if result == \"skipped\" and item[\"required\"]:", "        if False:", RUN_TESTS),
    ("RUN-M7 a fail keeps no diagnosis", REPO,
     "(result, notes, diagnosis if result == \"fail\" else None,",
     "(result, notes, None,", RUN_TESTS),
    ("RUN-M8 a work order and another bike are accepted", CLI,
     "        if vehicle is not None and vehicle[\"id\"] != order[\"vehicle_id\"]:",
     "        if False:", RUN_TESTS),
    ("RUN-M9 a closed work order is accepted", CLI,
     "        if order[\"status\"] in (\"completed\", \"cancelled\"):", "        if False:", RUN_TESTS),
    ("RUN-M10 a run with neither bike nor work order is not refused", CLI,
     "    if vehicle is None:\n        _refuse(console, \"A saved run",
     "    if False:\n        _refuse(console, \"A saved run", RUN_TESTS),
    ("RUN-M11 the schema lets a required item be skipped", MIGRATIONS,
     "                CHECK (result IS NOT 'skipped' OR required = 0),\n", "", RUN_TESTS),
    ("RUN-M12 the rollback leaves the run table", MIGRATIONS,
     "            DROP TABLE IF EXISTS workflow_runs;\n        \"\"\",\n    ),\n]",
     "        \"\"\",\n    ),\n]", RUN_TESTS),
    ("RUN-M13 garage update ignores --powertrain", MAIN,
     "        updates[\"powertrain\"] = powertrain", "        pass", RUN_TESTS),
    ("RUN-M14 runs ignores the bike filter", REPO,
     "    if vehicle_id is not None:\n        where.append", "    if False:\n        where.append",
     RUN_TESTS),
    ("RUN-M15 the report reads the template's current title", REPO,
     "SELECT ri.*, ci.description,",
     "SELECT ri.id, ri.run_id, ri.checklist_item_id, ri.sequence_number, ci.title, "
     "ri.required, ri.result, ri.diagnosis, ri.notes, ri.answered_at, ci.description,",
     RUN_TESTS),
    ("RUN-M16 a run is not tied to its work order", CLI,
     "powertrain,\n                                work_order_id=work_order_id,",
     "powertrain,\n                                work_order_id=None,", RUN_TESTS),
]


def run_tests(tests: list[str]) -> int:
    for base in (ROOT / "src", ROOT / ".claude", ROOT / "tests"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests],
        cwd=ROOT, capture_output=True, text=True,
    ).returncode


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    every = sorted({t for m in chosen for t in m[4]})
    assert run_tests(every) == 0, "the tests are not green before mutating"
    survivors = []
    for name, rel, old, new, tests in chosen:
        path = ROOT / rel
        original = path.read_text()
        assert original.count(old) == 1, f"{name}: the text occurs {original.count(old)} times"
        try:
            path.write_text(original.replace(old, new))
            code = run_tests(tests)
        finally:
            path.write_text(original)
        verdict = "red" if code != 0 else "GREEN (survived)"
        print(f"{name}: {verdict}", flush=True)
        if code == 0:
            survivors.append(name)
    assert run_tests(every) == 0, "the tests are not green after restoring"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
