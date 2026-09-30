"""Phase 274's mutations: each breaks one thing the batch promises, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/274_mutate.py`
(`completed/` after close-out). 361's form: each mutation replaces one exact
string (which must occur once), runs its tests with `-B` after clearing
`__pycache__`, and restores the file whatever happens. Prints one line per
mutation and exits 1 if any stayed green. An argument runs only the
mutations whose name starts with it: `M` migration, `C` CRM (274), `I`
inventory (279), `W` warranty (280), `Q` F182 and the quote record, `V`
variance (291), `P` the P&L (290), `G` the gate's seed.

The edit guard does not stop this script: a script run by name is outside
what it can see, which is its first known limit.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
T_MIG = ["tests/test_phase274_migration.py"]
T_CRM = ["tests/test_phase274_crm.py"]
T_REL = ["tests/test_phase274_relationship_column.py"]
T_INV = ["tests/test_phase274_inventory.py"]
T_WAR = ["tests/test_phase274_warranty.py"]
T_QV = ["tests/test_phase274_quotes_variance.py"]
T_PNL = ["tests/test_phase274_pnl.py"]
T_244W = ["tests/test_phase244W_module_islands.py"]

MIGRATIONS = "src/motodiag/core/migrations.py"
COMMS = "src/motodiag/crm/communication_repo.py"
BIKES = "src/motodiag/crm/customer_bikes_repo.py"
CLI_CRM = "src/motodiag/cli/shop_crm.py"
CLI_SHOP = "src/motodiag/cli/shop.py"
PO = "src/motodiag/inventory/purchase_orders.py"
WARRANTY = "src/motodiag/inventory/warranty_repo.py"
CLAIMS = "src/motodiag/inventory/warranty_claims.py"
NOTIFY = "src/motodiag/shop/notifications.py"
ANALYTICS = "src/motodiag/shop/analytics.py"
COSTS = "src/motodiag/shop/shop_costs.py"
GAPS = "tests/support/integration_gaps.py"

MUTATIONS = [
    # ------------------------------------------------------------ migration 076
    ("M1 the rollback keeps reorder_quantity", MIGRATIONS,
     "            ALTER TABLE inventory_items DROP COLUMN reorder_quantity;\n", "", T_MIG),
    ("M2 a contact's channel is unchecked", MIGRATIONS,
     "                    CHECK (channel IN ('phone', 'in_person', 'email',\n"
     "                                       'sms', 'other')),",
     "", T_MIG),
    # ------------------------------------------------------------ 274, the CRM
    ("C1 a contact may cite another customer's work order", COMMS,
     "            if wo[\"customer_id\"] != customer_id:",
     "            if False:", T_CRM),
    ("C2 the history leaves out the notifications", COMMS,
     "    for n in rows:\n        entries.append(",
     "    for n in []:\n        entries.append(", T_CRM),
    ("C3 a non-owner can transfer the bike", CLI_CRM,
     "        if old[\"id\"] not in {o[\"id\"] for o in owners}:",
     "        if False:", T_CRM),
    ("C4 a bike sold back collides with the previous-owner link", BIKES,
     "               WHERE vehicle_id = ? AND customer_id = ? AND relationship = 'owner'\n"
     "                 AND EXISTS (",
     "               WHERE 0 AND vehicle_id = ? AND customer_id = ? AND relationship = 'owner'\n"
     "                 AND EXISTS (", T_CRM),
    ("C5 bug fix #1 undone: the relationship prints ?", CLI_SHOP,
     "                str(b.get(\"cb_relationship\", \"?\")),\n            )\n        console.print(table)\n\n    @customer_group.command(\"search\")",
     "                str(b.get(\"relationship\", \"?\")),\n            )\n        console.print(table)\n\n    @customer_group.command(\"search\")",
     T_REL),
    # ------------------------------------------------------------ 279, inventory
    ("I1 an item on an open PO is ordered again", PO,
     "        if item[\"id\"] in on_order:", "        if False:", T_INV),
    ("I2 an item with no reorder quantity is ordered", PO,
     "        elif not item.get(\"reorder_quantity\"):", "        elif False:", T_INV),
    ("I3 receiving adds nothing to stock", PO,
     "    if target == \"received\":\n        for line",
     "    if False:\n        for line", T_INV),
    ("I4 a draft can be received", PO,
     "    \"draft\": (\"sent\", \"cancelled\"),",
     "    \"draft\": (\"sent\", \"cancelled\", \"received\"),", T_INV),
    # ------------------------------------------------------------ 280, warranty
    ("W1 an unrecorded mileage limit reads as a pass", WARRANTY,
     "    if limit is None:\n        unknown.append(\"no mileage limit recorded\")\n    elif",
     "    if limit is None:\n        pass\n    elif", T_WAR),
    ("W2 an unknown mileage reads as a pass", WARRANTY,
     "        unknown.append(f\"the bike's mileage is not known (limit {limit:,} mi)\")",
     "        pass", T_WAR),
    ("W3 an ended coverage is valid", WARRANTY,
     "    elif on_date > end:", "    elif False:", T_WAR),
    ("W4 a missing figure outranks a failure", WARRANTY,
     "    if failed:\n        return \"not valid\", failed\n    if unknown:\n"
     "        return \"cannot tell\", unknown",
     "    if unknown:\n        return \"cannot tell\", unknown\n    if failed:\n"
     "        return \"not valid\", failed", T_WAR),
    ("W5 a claim may go straight from draft to approved", CLAIMS,
     "    \"draft\": (\"submitted\",),", "    \"draft\": (\"submitted\", \"approved\"),", T_WAR),
    ("W6 a claim may cite a work order on another bike", CLAIMS,
     "            if wo[\"vehicle_id\"] != warranty[\"vehicle_id\"]:",
     "            if False:", T_WAR),
    # ------------------------------------------------------------ F182 and the quote
    ("Q1 F182 back: no rate means $100 an hour", NOTIFY,
     "    rate = _lookup_labor_rate_cents(wo[\"shop_id\"], db_path=db_path)\n",
     "    rate = _lookup_labor_rate_cents(wo[\"shop_id\"], db_path=db_path) or 10000\n",
     T_QV),
    ("Q2 F182 back: the parts are left out", NOTIFY,
     "    parts = int(wo.get(\"estimated_parts_cost_cents\") or 0)\n",
     "    parts = 0\n", T_QV),
    ("Q3 a queued estimate records no quote", NOTIFY,
     "        if est is not None:\n            conn.execute(",
     "        if False:\n            conn.execute(", T_QV),
    ("Q4 the extra context may override the estimate", NOTIFY,
     "        if event == \"estimate_ready\" and ESTIMATE_KEYS & set(extra_context):",
     "        if False:", T_QV),
    # ------------------------------------------------------------ 291, variance
    ("V1 no recorded quote is replaced by the invoice's figure", ANALYTICS,
     "                if quote is None:\n                    quote_note = \"no quote recorded\"",
     "                if quote is None:\n                    quote_note = None\n"
     "                    quote_total = subtotal", T_QV),
    ("V2 a quote made after the invoice is used", ANALYTICS,
     "                    \"AND replace(quoted_at, 'T', ' ') <= replace(?, 'T', ' ') \"",
     "                    \"AND ? IS NOT NULL \"", T_QV),
    ("V3 labour variance is measured the wrong way round", ANALYTICS,
     "    return round((actual - estimate) / estimate, 4)",
     "    return round((estimate - actual) / estimate, 4)", T_QV),
    # ------------------------------------------------------------ 290, the P&L
    ("P1 an unrecorded purchase cost counts as zero", ANALYTICS,
     "        if p[\"purchase_cost_cents_each\"] is None:\n            parts_cost = None\n"
     "            break",
     "        if p[\"purchase_cost_cents_each\"] is None:\n            continue", T_PNL),
    ("P2 an unrecorded cost rate counts as zero", ANALYTICS,
     "            if rate is None:\n                total = None\n                break",
     "            if rate is None:\n                continue", T_PNL),
    ("P3 bays share a work order equally, not by slot hours", ANALYTICS,
     "    return {k: v / total for k, v in hours.items()}",
     "    return {k: 1 / len(hours) for k in hours}", T_PNL),
    ("P4 an unassigned work order goes to the first mechanic", ANALYTICS,
     "                weights = {str(mech) if mech is not None else \"unassigned\": 1.0}",
     "                weights = {str(mech) if mech is not None else \"2\": 1.0}", T_PNL),
    ("P5 net is computed with months missing their expenses", ANALYTICS,
     "        if margin is not None and not report.expense_months_missing:",
     "        if margin is not None:", T_PNL),
    ("P6 a cancelled invoice is revenue", ANALYTICS,
     "            \"WHERE wo.shop_id = ? AND inv.status != 'cancelled' \"\n"
     "            \"AND substr(inv.issued_at, 1, 10) >= ? \"",
     "            \"WHERE wo.shop_id = ? \"\n"
     "            \"AND substr(inv.issued_at, 1, 10) >= ? \"", T_PNL),
    ("P7 an older rate wins over the one in force", COSTS,
     "            if best is None or r[\"effective_from\"] > best[\"effective_from\"]:",
     "            if best is None or r[\"effective_from\"] < best[\"effective_from\"]:", T_PNL),
    ("P8 revenue includes tax", ANALYTICS,
     "            parts_cost, labour_cost, hours = _wo_costs(conn, inv[\"work_order_id\"], rates)",
     "            revenue[\"tax\"] = 1\n"
     "            parts_cost, labour_cost, hours = _wo_costs(conn, inv[\"work_order_id\"], rates)",
     T_PNL),
    # ------------------------------------------------------------ 244W's moved control
    ("G1 the island scan loses its one seed", GAPS,
     "    islands = set(already_dead)\n", "    islands = set()\n", T_244W),
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
