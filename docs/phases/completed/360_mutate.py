"""Phase 360's mutations: each breaks one thing the phase promises, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/completed/360_mutate.py`
(moved from in_progress/ at close-out). 357's form: each mutation replaces
one exact string (which must occur once), runs its tests with `-B` after
clearing `__pycache__`, and restores the file whatever happens. Prints one
line per mutation and exits 1 if any stayed green. An argument runs only the
mutations whose name starts with it (`G` for the edit guard, `P` for F174).

The edit guard does not stop this script: a script run by name is outside
what it can see, which is its first known limit.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
GUARD = ".claude/skills/closeout/_edit_guard.py"
WRAPPER = ".claude/skills/closeout/edit_guard.sh"
GUARD_TESTS = ["tests/test_phase360_edit_guard.py"]
F174_TESTS = ["tests/test_phase360_powertrain_unknown.py"]
REGISTRY = "src/motodiag/vehicles/registry.py"
MODELS = "src/motodiag/core/models.py"
MAIN = "src/motodiag/cli/main.py"
IDENTIFIER = "src/motodiag/intake/vehicle_identifier.py"
API = "src/motodiag/api/routes/vehicles.py"
WORKFLOW = "src/motodiag/cli/workflow.py"
DIAGNOSE = "src/motodiag/cli/diagnose.py"
PREDICTOR = "src/motodiag/advanced/predictor.py"
SCORER = "src/motodiag/shop/priority_scorer.py"
MIGRATIONS = "src/motodiag/core/migrations.py"

MUTATIONS = [
    # ------------------------------------------------------------ the edit guard
    ("G1 sed -i is not seen", GUARD,
     "            for ch in a[1:]:\n                if ch == \"i\":\n                    return True",
     "            for ch in a[1:]:\n                if ch == \"#\":\n                    return True",
     GUARD_TESTS),
    ("G2 perl -i is not seen", GUARD,
     "            if ch == \"i\":\n                inplace = True",
     "            if ch == \"#\":\n                inplace = True", GUARD_TESTS),
    ("G3 redirects are not judged", GUARD,
     "            _target(target, state, f\"the redirect `{op}`\")", "            pass",
     GUARD_TESTS),
    ("G4 tee is not judged", GUARD,
     "                _target(a, state, \"`tee`\")", "                pass", GUARD_TESTS),
    ("G5 cp and mv are not judged", GUARD,
     "            _target(dest, state, f\"`{name}`\")", "            pass", GUARD_TESTS),
    ("G6 patch with no named file is allowed inside the checkout", GUARD,
     "        if _inside_repo(here):", "        if False:", GUARD_TESTS),
    ("G7 Python bodies are not judged", GUARD,
     "        _python_body(code, state)", "        pass", GUARD_TESTS),
    ("G8 shell bodies are not judged", GUARD,
     "        _analyze(code, state.copy(), depth + 1)", "        pass", GUARD_TESTS),
    ("G9 an exception inside the guard lets the command run", GUARD,
     "        reason = f\"the edit guard failed inside ({e!r}) and fails closed.\"",
     "        reason = None", GUARD_TESTS),
    ("G10 the guard keeps no clock", GUARD,
     "    signal.alarm(LIMIT_S)\n    try:", "    try:", GUARD_TESTS),
    ("G11 a target it cannot resolve is allowed", GUARD,
     "    if path is None or not exact and _holds_protected(path):", "    if False:",
     GUARD_TESTS),
    ("G12 the wrapper passes an exit status other than 0 and 2", WRAPPER,
     "and fails closed.\" >&2\nexit 2", "and fails closed.\" >&2\nexit $rc", GUARD_TESTS),
    ("G13 heredoc bodies are read as commands", GUARD,
     "                for delim, strip, idx in pending:\n"
     "                    i = self._heredoc_body(i, delim, strip, idx)",
     "                for delim, strip, idx in pending:\n                    pass",
     GUARD_TESTS),
    ("G14 a mention of src/ counts whatever the directory", GUARD,
     "        path = _abs(token, cwd)\n        if path is None or is_protected(path):\n"
     "            return True",
     "        return True", GUARD_TESTS),
    ("G15 the fixed directory of a Python path is ignored", GUARD,
     "                return _prefix_dir(\"\".join(lead))", "                return _UNKNOWN",
     GUARD_TESTS),
    # ------------------------------------------------------------ F174
    ("P1 the registry stores ice for an unknown powertrain", REGISTRY,
     "                vehicle.powertrain.value if vehicle.powertrain else None,\n"
     "                vehicle.engine_type.value,\n"
     "                vehicle.battery_chemistry.value if vehicle.battery_chemistry else None,",
     "                vehicle.powertrain.value if vehicle.powertrain else \"ice\",\n"
     "                vehicle.engine_type.value,\n"
     "                vehicle.battery_chemistry.value if vehicle.battery_chemistry else None,",
     F174_TESTS),
    ("P2 the owner's insert stores ice for an unknown powertrain", REGISTRY,
     "                vehicle.powertrain.value if vehicle.powertrain else None,\n"
     "                vehicle.engine_type.value,\n                vehicle.battery_chemistry.value\n",
     "                vehicle.powertrain.value if vehicle.powertrain else \"ice\",\n"
     "                vehicle.engine_type.value,\n                vehicle.battery_chemistry.value\n",
     F174_TESTS),
    ("P3 the model defaults to ice", MODELS,
     "    powertrain: Optional[PowertrainType] = Field(\n        None,",
     "    powertrain: Optional[PowertrainType] = Field(\n        PowertrainType.ICE,",
     F174_TESTS),
    ("P4 garage add assumes ice instead of asking", MAIN,
     "    if powertrain is None:\n        powertrain = _ask_powertrain()\n    init_db()",
     "    if powertrain is None:\n        powertrain = \"ice\"\n    init_db()", F174_TESTS),
    ("P5 no answer stores ice", MAIN,
     "\"Nothing was saved.[/red]\")\n        raise SystemExit(1)",
     "\"Nothing was saved.[/red]\")\n        return \"ice\"", F174_TESTS),
    ("P6 a photo with no powertrain guess is stored as ice", MAIN,
     "    powertrain = powertrain or guess.powertrain_guess or _ask_powertrain()",
     "    powertrain = powertrain or guess.powertrain_guess or \"ice\"", F174_TESTS),
    ("P7 the photo's guess wins over the person", MAIN,
     "    powertrain = powertrain or guess.powertrain_guess or _ask_powertrain()",
     "    powertrain = guess.powertrain_guess or powertrain or _ask_powertrain()",
     F174_TESTS),
    ("P8 a vision reply without the key reads as ice", IDENTIFIER,
     "    return text if text in (\"ice\", \"electric\", \"hybrid\") else None",
     "    return text if text in (\"ice\", \"electric\", \"hybrid\") else \"ice\"",
     F174_TESTS),
    ("P9 the API defaults to ice", API,
     "    powertrain: Optional[PowertrainLiteral] = None\n    engine_type: EngineTypeLiteral",
     "    powertrain: Optional[PowertrainLiteral] = \"ice\"\n    engine_type: EngineTypeLiteral",
     F174_TESTS),
    ("P10 the API reads unknown as ice", API,
     "        powertrain=row.get(\"powertrain\"),",
     "        powertrain=row.get(\"powertrain\") or \"ice\",", F174_TESTS),
    ("P11 garage list prints unknown as ice", MAIN,
     "engine, v.get(\"powertrain\") or \"unknown\",",
     "engine, v.get(\"powertrain\") or \"ice\",", F174_TESTS),
    ("P12 workflow start leaves an unknown bike unknown", WORKFLOW,
     "    if not stored:\n        # Phase 360", "    if False:\n        # Phase 360",
     F174_TESTS),
    ("P13 workflow start rewrites a bike that has a value", WORKFLOW,
     "    if not stored:\n        # Phase 360", "    if True:\n        # Phase 360",
     F174_TESTS),
    ("P14 diagnose retrieval turns unknown into ice", DIAGNOSE,
     "        powertrain=powertrain, transmission=transmission,",
     "        powertrain=powertrain or \"ice\", transmission=transmission,", F174_TESTS),
    ("P15 the predictor turns unknown into ice", PREDICTOR,
     "        powertrain=vehicle.get(\"powertrain\"),\n        transmission=vehicle.get",
     "        powertrain=vehicle.get(\"powertrain\") or \"ice\",\n        transmission=vehicle.get",
     F174_TESTS),
    ("P16 the priority scorer turns unknown into ice", SCORER,
     "        powertrain=row[\"powertrain\"] if \"powertrain\" in keys else None,",
     "        powertrain=(row[\"powertrain\"] or \"ice\") if \"powertrain\" in keys else None,",
     F174_TESTS),
    ("P17 safety scopes an unknown bike as electric", DIAGNOSE,
     "            powertrain=(vehicle or {}).get(\"powertrain\"),",
     "            powertrain=(vehicle or {}).get(\"powertrain\") or \"electric\",", F174_TESTS),
    ("P18 migration 074 keeps the default", MIGRATIONS,
     "upgrade_sql=_vehicles_rebuild_074(\"powertrain TEXT\", \"vehicles_rebuild_074\"),",
     "upgrade_sql=_vehicles_rebuild_074(\"powertrain TEXT DEFAULT 'ice'\", "
     "\"vehicles_rebuild_074\"),", F174_TESTS),
    ("P19 the rebuild resets the sequence to max(id)", MIGRATIONS,
     "             WHERE name = '{scratch}'\n               AND EXISTS",
     "             WHERE 0 AND name = '{scratch}'\n               AND EXISTS", F174_TESTS),
    ("P20 the rebuild rewrites an index's SQL", MIGRATIONS,
     "            CREATE INDEX idx_vehicles_owner\n                ON vehicles(owner_user_id);",
     "            CREATE INDEX idx_vehicles_owner ON vehicles(owner_user_id);", F174_TESTS),
    ("P21 the rollback leaves the default off", MIGRATIONS,
     "rollback_sql=_vehicles_rebuild_074(\"powertrain TEXT DEFAULT 'ice'\",",
     "rollback_sql=_vehicles_rebuild_074(\"powertrain TEXT\",", F174_TESTS),
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
