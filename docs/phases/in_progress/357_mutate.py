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
