"""Phase 376's mutations: each breaks one thing the phase built, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/376_mutate.py`
(ROOT is three levels up from in_progress/ or completed/).
373's form: each mutation replaces one exact string (which must occur once),
runs its tests with `-B` after clearing `__pycache__`, and restores the file
whatever happens. Prints one line per mutation and exits 1 if any stayed
green. An argument runs only the mutations whose name starts with it: `S`
selection, `Q` QuickBooks, `X` Xero, `T` the tax readings, `R` the record,
`M` migration 083, `N` the invoice number (F194).
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PHASE = ["tests/test_phase376_settlement_export.py"]
WITH_373 = PHASE + ["tests/test_phase373_warranty_invoice.py"]

EXPORT = "src/motodiag/accounting/export.py"
TAX = "src/motodiag/accounting/tax.py"
CLI = "src/motodiag/cli/shop_accounting.py"
INVOICING = "src/motodiag/shop/invoicing.py"
MIGRATIONS = "src/motodiag/core/migrations.py"

MUTATIONS = [
    # ------------------------------------------------------------ selection
    ("S1 the settlement's day is read as text, not parsed (the month-end evening)", EXPORT,
     "                  AND datetime(c.settled_at) >= ? AND datetime(c.settled_at) < ?",
     "                  AND c.settled_at >= ? AND c.settled_at < ?", PHASE),
    ("S2 a settlement is exported again to the same target", EXPORT,
     '            if s["id"] in settled and not include_exported:', "            if False:",
     PHASE),
    ("S3 a settlement is booked against a claim the books never held (D1)", EXPORT,
     '        if not s["claim_exported"] and s["id"] not in claim_ids:', "        if False:",
     PHASE),
    ("S4 a range with settlements and no invoices is refused", EXPORT,
     "    if not invoices and not settlements:", "    if not invoices:", PHASE),
    # ------------------------------------------------------------ QuickBooks
    ("Q1 the credit leaves out the claim's tax inside the shortfall", EXPORT,
     "        if tax_share:\n            rows.append({", "        if False:\n            rows.append({",
     PHASE),
    ("Q2 the shortfall invoice's own journal is not written", EXPORT,
     '    if s["shortfall_invoice"] is not None:\n        rows += _quickbooks_invoice_rows',
     "    if False:\n        rows += _quickbooks_invoice_rows", WITH_373),
    ("Q3 an absorbed shortfall is debited to income, not the absorbed account", EXPORT,
     '            "Account Name": mapping["absorbed"]["account"],',
     '            "Account Name": mapping["labor"]["account"],', PHASE),
    ("Q4 the tax share out of step with its claim is booked anyway", EXPORT,
     '    if tax_share < 0 or tax_share > int(s["tax_cents"] or 0):', "    if False:", PHASE),
    # ------------------------------------------------------------ Xero
    ("X1 the credit note is written tax-exclusive", EXPORT,
     '            parts = [(line["item_type"], line["description"], amount + share)',
     '            parts = [(line["item_type"], line["description"], amount)', PHASE),
    ("X2 the absorbed credit note goes to the claim's income account", EXPORT,
     '            parts = [("absorbed", f"Warranty claim #',
     '            parts = [("labor", f"Warranty claim #', PHASE),
    ("X3 the billed shortfall invoice is left out of the invoices file", EXPORT,
     "    for inv in list(invoices) + billed:\n        rows += _xero_invoice_rows",
     "    for inv in invoices:\n        rows += _xero_invoice_rows", PHASE),
    ("X4 an absorbed credit note gets no expected-tax line", CLI,
     "        for cn in result.credit_notes:",
     "        for cn in [c for c in result.credit_notes if not c.absorbed]:", PHASE),
    # ------------------------------------------------------------ tax readings
    ("T1 an absorbed taxed claim exports with no reading on record", EXPORT,
     "        if tax:\n            day = date.fromisoformat", "        if False:\n            day = date.fromisoformat",
     PHASE),
    ("T2 F195's line is printed for a labour-only claim", EXPORT,
     '        elif any(line["line_type"] == "parts" for line in s["lines"]):',
     "        elif True:", PHASE),
    ("T3 status does not show the settlement rule", TAX,
     "            settlement_rule = _item(row, SETTLEMENT_RULE, 1.0)",
     "            settlement_rule = None", PHASE),
    ("T4 confirm does not renew the settlement rule", TAX,
     "        for rule in settlement_rules:", "        for rule in []:", PHASE),
    # ------------------------------------------------------------ the record
    ("R1 the files an export wrote are not recorded", EXPORT,
     "            [(export_id, f.holds, str(f.path), f.sha256, f.row_count) for f in written],",
     "            [],", PHASE),
    ("R2 the billed shortfall invoice is not recorded as exported", EXPORT,
     '    invoice_ids = [inv["id"] for inv in invoices] + [inv["id"] for inv in billed]',
     '    invoice_ids = [inv["id"] for inv in invoices]', PHASE),
    # ------------------------------------------------------------ migration 083
    ("M1 the rebuilt CHECK leaves out absorbed", MIGRATIONS,
     "                                    'tax', 'receivable', 'absorbed')),",
     "                                    'tax', 'receivable')),", PHASE),
    ("M2 the rebuild runs with foreign keys on (DROP cascades to the children)", MIGRATIONS,
     "            PRAGMA foreign_keys=OFF;\n\n            CREATE TABLE accounting_accounts_rebuild",
     "            CREATE TABLE accounting_accounts_rebuild", PHASE),
    ("M3 an export with no invoices is still refused by the schema", MIGRATIONS,
     "                invoice_count INTEGER NOT NULL CHECK (invoice_count >= 0),",
     "                invoice_count INTEGER NOT NULL CHECK (invoice_count > 0),", PHASE),
    # ------------------------------------------------------------ F194
    ("N1 the invoice number takes the UTC day again", INVOICING,
     '    return local_day(now.isoformat()).replace("-", "")',
     "    return now.strftime('%Y%m%d')", PHASE),
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
