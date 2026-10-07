"""Phase 373's mutations: each breaks one thing the phase built, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/373_mutate.py`
(moved to completed/ at close-out; ROOT is three levels up either way).
292's form: each mutation replaces one exact string (which must occur once),
runs its tests with `-B` after clearing `__pycache__`, and restores the file
whatever happens. Prints one line per mutation and exits 1 if any stayed
green. An argument runs only the mutations whose name starts with it: `C`
covering lines, `I` the invoice, `S` settlement, `E` the export, `T` the
tax rule.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PHASE = ["tests/test_phase373_warranty_invoice.py"]
GATE = ["tests/test_phase292_gate16.py"]

CLAIMS = "src/motodiag/inventory/warranty_claims.py"
INVOICING = "src/motodiag/shop/invoicing.py"
EXPORT = "src/motodiag/accounting/export.py"
TAX = "src/motodiag/accounting/tax.py"

MUTATIONS = [
    # ------------------------------------------------------------ covering
    ("C1 a claim covers lines with no payer on record", CLAIMS,
     '    if not covers_nothing and warranty.get("repair_payer") is None:',
     "    if False:", PHASE),
    ("C2 a claim covers more of a part than the order holds", CLAIMS,
     '            if count < 1 or count + taken > int(part["quantity"]):',
     "            if count < 1:", PHASE),
    ("C3 lines change under an issued invoice", CLAIMS,
     "        if invoiced is not None:", "        if False:", PHASE),
    # ------------------------------------------------------------ the invoice
    ("I1 an invoice ignores a claim with no coverage recorded", INVOICING,
     '        if claim["coverage_recorded_at"] is None:', "        if False:", PHASE),
    ("I2 covered labour stays on the customer's invoice", INVOICING,
     "    customer_hours = _hours_left(hours, covered_hours)",
     "    customer_hours = hours", PHASE + GATE),
    ("I3 covered parts stay on the customer's invoice", INVOICING,
     '               - covered_qty.get(int(part["wop_id"]), 0))', "               - 0)",
     PHASE + GATE),
    ("I4 the claim's tax ignores who owes the repair", INVOICING,
     "            if rule.value:", "            if True:", PHASE),
    ("I5 the claim's tax falls on labour too", INVOICING,
     "                taxable = sum(by_type[t] for t in by_type if t in decision.taxable_types)",
     "                taxable = sum(by_type.values())", PHASE + GATE),
    ("I6 the amount claimed leaves out the claim's tax", INVOICING,
     '        claim["amount"] = claim["covered_cents"] + claim["tax_cents"]',
     '        claim["amount"] = claim["covered_cents"]', PHASE + GATE),
    ("I7 a claim past draft is priced again at another amount", INVOICING,
     '        if claim["status"] != "draft" and old is not None and old != claim["amount"]:',
     "        if False:", PHASE),
    ("I8 nothing owed is left unpaid", INVOICING,
     "    if total_cents == 0:", "    if False:", PHASE),
    ("I9 a denied claim still takes its lines off", INVOICING,
     "AND (c.status != 'denied' OR c.settlement IS NOT NULL) ORDER BY c.id",
     "ORDER BY c.id", PHASE),
    # ------------------------------------------------------------ settlement
    ("S1 a part approval bills the customer the whole claim", INVOICING,
     "    pre_tax = (covered if shortfall_cents == claimed else",
     "    pre_tax = (covered if True else", PHASE),
    ("S2 a settled, denied claim's lines return to the regenerated invoice", INVOICING,
     "AND (c.status != 'denied' OR c.settlement IS NOT NULL) ORDER BY c.id",
     "AND c.status != 'denied' ORDER BY c.id", PHASE),
    ("S3 a shortfall invoice blocks nothing and counts as the order's", INVOICING,
     "            \"AND status != 'cancelled' AND shortfall_claim_id IS NULL LIMIT 1\",",
     "            \"AND status != 'cancelled' LIMIT 1\",", PHASE),
    ("S4 a claim settles twice", CLAIMS,
     '    if claim["settlement"] is not None:', "    if False:", PHASE),
    ("S5 an approval above the claim is taken", CLAIMS,
     "            and amount_approved_cents > claimed):", "            and False):", PHASE),
    # ------------------------------------------------------------ the export
    ("E1 the claim's receivable names no one", EXPORT,
     '            "Journal/Description": description, "Name": provider,',
     '            "Journal/Description": description, "Name": "",', PHASE + GATE),
    ("E2 Xero spreads the claim's tax over labour", EXPORT,
     '              if taxed is None or line["line_type"] in taxed]', "              if True]",
     PHASE + GATE),
    ("E3 a shortfall invoice is exported as an ordinary one", EXPORT,
     "                  AND i.shortfall_claim_id IS NULL\n", "", PHASE),
    ("E4 a claim with no provider is exported", EXPORT,
     "    if not provider:\n", "    if False:\n", PHASE),
    # ------------------------------------------------------------ the tax rule
    ("T1 a lapsed warranty rule does not fail the status", TAX,
     "                failures.append(_missing_warranty_rule(conn, jur, shop_id, on, payer))",
     "                pass", PHASE),
    ("T2 confirm leaves the warranty rules lapsed", TAX,
     "        for rule in warranty_rules:", "        for rule in []:", PHASE),
]


def run_tests(tests: list[str]) -> int:
    for base in (ROOT / "src", ROOT / "tests"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
         "-o", "addopts=", *tests],
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
