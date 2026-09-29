"""Phase 361's mutations: each breaks one thing the phase promises, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/361_mutate.py`
(moved to completed/ at close-out). 360's form: each mutation replaces one
exact string (which must occur once), runs its tests with `-B` after
clearing `__pycache__`, and restores the file whatever happens. Prints one
line per mutation and exits 1 if any stayed green. An argument runs only the
mutations whose name starts with it (`S` safety, `C` contract, `E` F177).

The edit guard does not stop this script: a script run by name is outside
what it can see, which is its first known limit.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SAFETY_TESTS = ["tests/test_phase361_safety_unknown_powertrain.py"]
TESTS = ["tests/test_phase361_contract_and_engine_type.py"]
SAFETY = "src/motodiag/engine/safety.py"
API = "src/motodiag/api/routes/vehicles.py"
REGISTRY = "src/motodiag/vehicles/registry.py"
MODELS = "src/motodiag/core/models.py"
MIGRATIONS = "src/motodiag/core/migrations.py"
MAIN = "src/motodiag/cli/main.py"
SOURCING = "src/motodiag/shop/parts_sourcing.py"
DIAGNOSE = "src/motodiag/cli/diagnose.py"
PROMPTS = "src/motodiag/engine/prompts.py"

MUTATIONS = [
    # ------------------------------------------------------------ F178, the checker
    ("S1 only None reads as unknown (the checker before 361)", SAFETY,
     "        if self.powertrain not in _KNOWN_POWERTRAINS:",
     "        if self.powertrain is None:", SAFETY_TESTS),
    ("S2 an old API value counts as known", SAFETY,
     "_KNOWN_POWERTRAINS = frozenset(p.value for p in PowertrainType)",
     "_KNOWN_POWERTRAINS = frozenset(p.value for p in PowertrainType) | {\"hybrid_parallel\"}",
     SAFETY_TESTS),
    # ------------------------------------------------------------ F178, the contract
    ("C1 the API takes a hybrid variant again", API,
     "PowertrainLiteral = Literal[\"ice\", \"electric\", \"hybrid\"]",
     "PowertrainLiteral = Literal[\"ice\", \"electric\", \"hybrid\", \"hybrid_parallel\"]",
     TESTS),
    ("C2 update_vehicle stores any string", REGISTRY,
     "            filtered[key] = enum(filtered[key]).value", "            pass", TESTS),
    ("C3 the API takes rotary again", API,
     "    \"four_stroke\", \"two_stroke\", \"electric_motor\", \"hybrid\", \"desmodromic\",\n]",
     "    \"four_stroke\", \"two_stroke\", \"electric_motor\", \"hybrid\", \"desmodromic\",\n"
     "    \"rotary\",\n]", TESTS),
    # ------------------------------------------------------------ F177
    ("E1 the model assumes four_stroke", MODELS,
     "    engine_type: Optional[EngineType] = Field(\n        None,",
     "    engine_type: Optional[EngineType] = Field(\n        EngineType.FOUR_STROKE,", TESTS),
    ("E2 the API's create assumes four_stroke", API,
     "not four_stroke.\n    engine_type: Optional[EngineTypeLiteral] = None",
     "not four_stroke.\n    engine_type: Optional[EngineTypeLiteral] = \"four_stroke\"", TESTS),
    ("E3 migration 075 keeps the column default", MIGRATIONS,
     "                                      \"engine_type TEXT\"),",
     "                                      \"engine_type TEXT DEFAULT 'four_stroke'\"),",
     TESTS),
    ("E4 075's rollback does not restore the default", MIGRATIONS,
     "rollback_sql=_vehicles_rebuild(\"powertrain TEXT\", \"vehicles_rollback_075\"),",
     "rollback_sql=_vehicles_rebuild(\"powertrain TEXT\", \"vehicles_rollback_075\", "
     "\"engine_type TEXT\"),", TESTS),
    ("E5 074's SQL moves", MIGRATIONS,
     "engine_type_def: str = \"engine_type TEXT DEFAULT 'four_stroke'\"",
     "engine_type_def: str = \"engine_type TEXT DEFAULT  'four_stroke'\"", TESTS),
    ("E6 the CLI assumes four_stroke instead of asking", MAIN,
     "            return \"electric_motor\"\n        try:",
     "            return \"electric_motor\"\n        return \"four_stroke\"\n        try:", TESTS),
    ("E7 electric is not derived", MAIN,
     "        if powertrain == \"electric\":\n            return \"electric_motor\"",
     "        if False:\n            return \"electric_motor\"", TESTS),
    ("E8 `unknown` is stored as a word", MAIN,
     "    return None if given == \"unknown\" else given", "    return given", TESTS),
    ("E9 garage update cannot clear", MAIN,
     "updates[\"engine_type\"] = None if engine_type == \"unknown\" else engine_type",
     "updates[\"engine_type\"] = engine_type", TESTS),
    ("E10 add-from-photo assumes four_stroke", MAIN,
     "    engine_type = _engine_type_for(powertrain, engine_type)\n    vehicle = VehicleBase(",
     "    engine_type = engine_type or \"four_stroke\"\n    vehicle = VehicleBase(", TESTS),
    ("E11 the registry binds four_stroke for unknown", REGISTRY,
     "                vehicle.engine_type.value if vehicle.engine_type else None,\n"
     "                vehicle.battery_chemistry.value if vehicle.battery_chemistry else None,",
     "                vehicle.engine_type.value if vehicle.engine_type else \"four_stroke\",\n"
     "                vehicle.battery_chemistry.value if vehicle.battery_chemistry else None,",
     TESTS),
    ("E12 parts sourcing prints None", SOURCING,
     "{vehicle.get('engine_type') or 'unknown'}", "{vehicle.get('engine_type', '?')}", TESTS),
    ("E13 diagnose fills in four_stroke", DIAGNOSE,
     "            engine_type=vehicle.get(\"engine_type\"),\n            known_issues=known,\n"
     "            ai_model=ai_model,\n            offline=offline,",
     "            engine_type=vehicle.get(\"engine_type\") or \"four_stroke\",\n"
     "            known_issues=known,\n            ai_model=ai_model,\n            offline=offline,",
     TESTS),
    ("E14 the prompt prints an unknown engine", PROMPTS,
     "    if engine_type:", "    if True:", TESTS),
]


def run_tests(tests: list[str]) -> int:
    for base in (ROOT / "src", ROOT / "tests"):
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
