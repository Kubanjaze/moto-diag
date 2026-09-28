"""Phase 356's mutations: each breaks one thing `workflow run` promises, and
the phase's tests must go red on it.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/356_mutate.py`.
Each mutation replaces one exact string (which must occur once), runs the
tests with `-B` after clearing `__pycache__` (stale bytecode can serve the
unmutated source), and restores the file whatever happens. Prints one line
per mutation and exits 1 if any stayed green.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
ENGINE = "src/motodiag/engine/workflows.py"
RUNNER = "src/motodiag/workflows/runner.py"
CLI = "src/motodiag/cli/workflow.py"
TESTS = ["tests/test_phase356_workflow_run.py", "tests/test_phase82_workflows.py"]

MUTATIONS = [
    ("M1 engine default no longer stops on a fail", ENGINE,
     "        default=True,\n        description=\"End the workflow",
     "        default=False,\n        description=\"End the workflow"),
    ("M2 the runner keeps the engine's stop on fail", RUNNER,
     "stop_on_fail=False,", "stop_on_fail=True,"),
    ("M3 the runner leaves max_steps at the default", RUNNER,
     "        max_steps=len(items),\n", ""),
    ("M4 an optional item is not offered a skip", CLI,
     "choices = [\"p\", \"f\"] if item[\"required\"] else [\"p\", \"f\", \"s\"]",
     "choices = [\"p\", \"f\"]"),
    ("M5 a fail prints no diagnosis", CLI,
     "        if answer.lower() == \"f\" and item.get(\"diagnosis_if_fail\"):",
     "        if False:"),
    ("M6 a retired template is not refused", CLI,
     "    if not template[\"is_active\"]:", "    if False:"),
    ("M7 an uncovered powertrain is not refused", CLI,
     "    if powertrain not in covers:", "    if False:"),
    ("M8 a skip is counted as a pass", CLI,
     "f\"{results.count(StepResult.PASS)} passed, \"",
     "f\"{results.count(StepResult.PASS) + results.count(StepResult.SKIPPED)} passed, \""),
    ("M9 no prompt: a missing powertrain is taken as ice", CLI,
     "        powertrain = click.prompt(\n            \"Powertrain\", type=click.Choice(POWERTRAINS, case_sensitive=False),\n        )",
     "        powertrain = \"ice\""),
    ("M10 the powertrain is asked before the template is checked", CLI,
     "    template = _template_or_refuse(console, slug)\n    if powertrain is None:",
     "    if powertrain is None:\n        powertrain = click.prompt(\"Powertrain\")\n    template = _template_or_refuse(console, slug)\n    if powertrain is None:"),
    ("M11 the summary lists no failed item", CLI,
     "        if step.result == StepResult.FAIL:\n            console.print(",
     "        if False:\n            console.print("),
]


def run_tests() -> int:
    for cache in (ROOT / "src").rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *TESTS],
        cwd=ROOT, capture_output=True, text=True,
    ).returncode


def main() -> int:
    assert run_tests() == 0, "the tests are not green before mutating"
    survivors = []
    for name, rel, old, new in MUTATIONS:
        path = ROOT / rel
        original = path.read_text()
        assert original.count(old) == 1, f"{name}: the text occurs {original.count(old)} times"
        try:
            path.write_text(original.replace(old, new))
            code = run_tests()
        finally:
            path.write_text(original)
        verdict = "red" if code != 0 else "GREEN (survived)"
        print(f"{name}: {verdict}")
        if code == 0:
            survivors.append(name)
    assert run_tests() == 0, "the tests are not green after restoring"
    print(f"{len(MUTATIONS) - len(survivors)}/{len(MUTATIONS)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
