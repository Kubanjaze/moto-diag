"""Phase 361 Step 0: apply measurement layers to a scratch worktree.

usage: layers.py <worktree root> <layer> [<layer> ...]
layers: f178, f177, opt_a, opt_b, opt_c  (opt_* need f177 first)
Each replacement must match exactly once, or the script stops.
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])


def sub(rel, old, new, count=1):
    p = root / rel
    s = p.read_text()
    n = s.count(old)
    if n != count:
        sys.exit(f"{rel}: expected {count} match(es), found {n}:\n{old}")
    p.write_text(s.replace(old, new))


def f178():
    sub("src/motodiag/engine/safety.py",
        "from pydantic import BaseModel, Field\n",
        "from pydantic import BaseModel, Field\n\n"
        "from motodiag.core.models import PowertrainType\n\n"
        "_KNOWN_POWERTRAINS = frozenset(p.value for p in PowertrainType)\n")
    sub("src/motodiag/engine/safety.py",
        "        if self.powertrain is None:\n            return True\n",
        "        if self.powertrain not in _KNOWN_POWERTRAINS:\n            return True\n")
    sub("src/motodiag/api/routes/vehicles.py",
        '    "ice", "electric", "hybrid_parallel", "hybrid_series",\n',
        '    "ice", "electric", "hybrid",\n')
    sub("src/motodiag/vehicles/registry.py",
        "    if \"bms_present\" in filtered and isinstance(filtered[\"bms_present\"], bool):\n",
        "    if filtered.get(\"powertrain\") is not None:\n"
        "        filtered[\"powertrain\"] = PowertrainType(filtered[\"powertrain\"]).value\n"
        "    if \"bms_present\" in filtered and isinstance(filtered[\"bms_present\"], bool):\n")


def f177():
    sub("src/motodiag/core/models.py",
        "    engine_type: EngineType = Field(\n        EngineType.FOUR_STROKE,\n",
        "    engine_type: Optional[EngineType] = Field(\n        None,\n")
    sub("src/motodiag/vehicles/registry.py",
        "                vehicle.engine_type.value,\n",
        "                vehicle.engine_type.value if vehicle.engine_type else None,\n", 2)
    sub("src/motodiag/vehicles/registry.py",
        "    if \"bms_present\" in filtered and isinstance(filtered[\"bms_present\"], bool):\n",
        "    if filtered.get(\"engine_type\") is not None:\n"
        "        filtered[\"engine_type\"] = EngineType(filtered[\"engine_type\"]).value\n"
        "    if \"bms_present\" in filtered and isinstance(filtered[\"bms_present\"], bool):\n")
    sub("src/motodiag/shop/parts_sourcing.py",
        "{vehicle.get('engine_type', '?')}",
        "{vehicle.get('engine_type') or 'unknown'}")
    sub("src/motodiag/api/routes/vehicles.py",
        '    "four_stroke", "two_stroke", "rotary", "diesel", "none",\n',
        '    "four_stroke", "two_stroke", "electric_motor", "hybrid", "desmodromic",\n')
    sub("src/motodiag/api/routes/vehicles.py",
        "        engine_type=EngineType(req.engine_type),\n",
        "        engine_type=EngineType(req.engine_type) if req.engine_type else None,\n")
    # migration 075
    sub("src/motodiag/core/migrations.py",
        "def _vehicles_rebuild_074(powertrain_default: str, scratch: str) -> str:\n",
        "def _vehicles_rebuild_074(powertrain_default: str, scratch: str,\n"
        "                          engine_type_def: str = \"engine_type TEXT DEFAULT 'four_stroke'\") -> str:\n")
    sub("src/motodiag/core/migrations.py",
        "                {powertrain_default},\n                engine_type TEXT DEFAULT 'four_stroke',\n",
        "                {powertrain_default},\n                {engine_type_def},\n")
    sub("src/motodiag/core/migrations.py",
        "                                           \"vehicles_rollback_074\"),\n    ),\n]\n",
        "                                           \"vehicles_rollback_074\"),\n    ),\n"
        "    Migration(\n        version=75,\n        name=\"vehicles_engine_type_no_default\",\n"
        "        description=\"Phase 361 (F177): engine_type loses its DEFAULT 'four_stroke'.\",\n"
        "        upgrade_sql=_vehicles_rebuild_074(\"powertrain TEXT\", \"vehicles_rebuild_075\", \"engine_type TEXT\"),\n"
        "        rollback_sql=_vehicles_rebuild_074(\"powertrain TEXT\", \"vehicles_rollback_075\"),\n"
        "    ),\n]\n")
    sub("src/motodiag/core/database.py", "SCHEMA_VERSION = 74", "SCHEMA_VERSION = 75")
    # garage update --engine-type
    sub("src/motodiag/cli/main.py",
        "@click.option(\n    \"--yes\", is_flag=True, default=False,\n    help=\"Confirm a non-monotonic mileage change (required for decreases).\",\n)\n",
        "@click.option(\"--engine-type\", default=None,\n"
        "              type=click.Choice([\"four_stroke\", \"two_stroke\", \"electric_motor\", \"hybrid\", \"desmodromic\"]))\n"
        "@click.option(\n    \"--yes\", is_flag=True, default=False,\n    help=\"Confirm a non-monotonic mileage change (required for decreases).\",\n)\n")
    sub("src/motodiag/cli/main.py",
        "    powertrain: str | None,\n    yes: bool,\n) -> None:\n",
        "    powertrain: str | None,\n    engine_type: str | None,\n    yes: bool,\n) -> None:\n")
    sub("src/motodiag/cli/main.py",
        "    if mileage is None and notes is None and vin is None and powertrain is None:\n",
        "    if mileage is None and notes is None and vin is None and powertrain is None and engine_type is None:\n")
    sub("src/motodiag/cli/main.py",
        "    if powertrain is not None:\n        updates[\"powertrain\"] = powertrain\n",
        "    if powertrain is not None:\n        updates[\"powertrain\"] = powertrain\n"
        "    if engine_type is not None:\n        updates[\"engine_type\"] = engine_type\n")
    # garage add and add-from-photo gain --engine-type; the rule is per option
    sub("src/motodiag/cli/main.py",
        "@click.option(\"--notes\", default=None, help=\"Free-text notes.\")\n"
        "def garage_add(make: str, model_name: str, year: int, engine_cc: int | None,\n"
        "               motor_kw: float | None, vin: str | None, protocol: str,\n"
        "               powertrain: str | None, notes: str | None) -> None:\n",
        "@click.option(\"--engine-type\", default=None,\n"
        "              type=click.Choice([\"four_stroke\", \"two_stroke\", \"electric_motor\", \"hybrid\", \"desmodromic\"]))\n"
        "@click.option(\"--notes\", default=None, help=\"Free-text notes.\")\n"
        "def garage_add(make: str, model_name: str, year: int, engine_cc: int | None,\n"
        "               motor_kw: float | None, vin: str | None, protocol: str,\n"
        "               powertrain: str | None, engine_type: str | None, notes: str | None) -> None:\n")
    sub("src/motodiag/cli/main.py",
        "    if powertrain is None:\n        powertrain = _ask_powertrain()\n    init_db()\n",
        "    if powertrain is None:\n        powertrain = _ask_powertrain()\n"
        "    engine_type = _engine_type_for(powertrain, engine_type)\n    init_db()\n")
    sub("src/motodiag/cli/main.py",
        "            engine_type=(\n                EngineType.ELECTRIC_MOTOR if powertrain == \"electric\"\n"
        "                else EngineType.FOUR_STROKE\n            ),\n",
        "            engine_type=EngineType(engine_type) if engine_type else None,\n")
    sub("src/motodiag/cli/main.py",
        "              help=\"The bike's powertrain; wins over the photo's guess. Asked for \"\n"
        "                   \"when neither gives one.\")\n"
        "def garage_add_from_photo(image_path: str, hints: str | None, yes: bool,\n"
        "                          powertrain: str | None) -> None:\n",
        "              help=\"The bike's powertrain; wins over the photo's guess. Asked for \"\n"
        "                   \"when neither gives one.\")\n"
        "@click.option(\"--engine-type\", default=None,\n"
        "              type=click.Choice([\"four_stroke\", \"two_stroke\", \"electric_motor\", \"hybrid\", \"desmodromic\"]))\n"
        "def garage_add_from_photo(image_path: str, hints: str | None, yes: bool,\n"
        "                          powertrain: str | None, engine_type: str | None) -> None:\n")
    sub("src/motodiag/cli/main.py",
        "    engine_type = (\n        EngineType.ELECTRIC_MOTOR if powertrain == \"electric\"\n"
        "        else EngineType.FOUR_STROKE\n    )\n",
        "    engine_type = _engine_type_for(powertrain, engine_type)\n"
        "    engine_type = EngineType(engine_type) if engine_type else None\n")


def _helper(body):
    sub("src/motodiag/cli/main.py",
        "@garage.command(\"add\")\n",
        "def _engine_type_for(powertrain, given):\n" + body + "\n\n@garage.command(\"add\")\n")


ASK = (
    "    if given:\n        return given\n"
    "    if powertrain == \"electric\":\n        return \"electric_motor\"\n"
    "    try:\n"
    "        return click.prompt(\"Engine type\", type=click.Choice([\"four_stroke\", \"two_stroke\", \"electric_motor\", \"hybrid\", \"desmodromic\"]))\n"
    "    except click.Abort:\n"
    "        console.print(\"No engine type given. Nothing was saved.\")\n"
    "        raise SystemExit(1)\n"
)


def opt_a():
    _helper(ASK)
    sub("src/motodiag/api/routes/vehicles.py",
        "    engine_type: EngineTypeLiteral = \"four_stroke\"\n",
        "    engine_type: EngineTypeLiteral\n")


def opt_b():
    _helper("    if given:\n        return given\n"
            "    return \"electric_motor\" if powertrain == \"electric\" else None\n")
    sub("src/motodiag/api/routes/vehicles.py",
        "    engine_type: EngineTypeLiteral = \"four_stroke\"\n",
        "    engine_type: Optional[EngineTypeLiteral] = None\n")


def opt_c():
    _helper(ASK)
    sub("src/motodiag/api/routes/vehicles.py",
        "    engine_type: EngineTypeLiteral = \"four_stroke\"\n",
        "    engine_type: Optional[EngineTypeLiteral] = None\n")


for layer in sys.argv[2:]:
    globals()[layer]()
    print("applied", layer)
