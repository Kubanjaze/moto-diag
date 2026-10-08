"""Phase 375's mutations: each breaks one thing the phase built, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/375_mutate.py`
(ROOT is three levels up from in_progress/ or completed/).
373's form: each mutation replaces one exact string (which must occur once),
runs its tests with `-B` after clearing `__pycache__`, and restores the file
whatever happens. Prints one line per mutation and exits 1 if any stayed
green. An argument runs only the mutations whose name starts with it: `I`
the invoice, `C` covering, `W` the warranty, `P` the packet, `T` the tax
readings, `M` migration 084.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PHASE = ["tests/test_phase375_deductibles.py"]

INVOICING = "src/motodiag/shop/invoicing.py"
CLAIMS = "src/motodiag/inventory/warranty_claims.py"
REPO = "src/motodiag/inventory/warranty_repo.py"
TAX = "src/motodiag/accounting/tax.py"
MIGRATIONS = "src/motodiag/core/migrations.py"

MUTATIONS = [
    # ------------------------------------------------------------ the invoice
    ("I1 no deductible is applied", INVOICING,
     "            applied = min(on_record, covered)", "            applied = 0", PHASE),
    ("I2 the deductible is not capped at the covered work", INVOICING,
     "            applied = min(on_record, covered)", "            applied = on_record",
     PHASE),
    ("I3 the claim's lines keep the deductible's share", INVOICING,
     '                line["amount_cents"] -= share\n', "", PHASE),
    ("I4 the claim keeps the tax the customer paid on the deductible", INVOICING,
     '                claim["tax_cents"] = taxed(by_type) - claim["deductible_tax_cents"]',
     '                claim["tax_cents"] = taxed(by_type)', PHASE),
    ("I5 the deductible's tax is not taken off the claim's (2C)", INVOICING,
     '                claim["deductible_tax_cents"] = taxed(claim["deductible_by_type"])',
     '                claim["deductible_tax_cents"] = 0', PHASE),
    ("I6 a deductible is charged with no reading on record", INVOICING,
     "                    deductible_rule = tax_mod.resolve_deductible_rule(",
     "                    deductible_rule = tax_mod.resolve_warranty_rule(", PHASE),
    ("I7 the customer's invoice does not charge the deductible", INVOICING,
     "            if not cents:\n                continue\n            _add_line_cents(invoice_id, item_type,",
     "            if True:\n                continue\n            _add_line_cents(invoice_id, item_type,",
     PHASE),
    ("I8 the claim's covered work is the gross, not the claimed work", INVOICING,
     '        claim["covered_cents"] = sum(line["amount_cents"] for line in claim["lines"])',
     '        claim["covered_cents"] = by_type["labor"] + by_type["parts"]', PHASE),
    ("I9 a deductible not on record at invoicing is read as none", INVOICING,
     '        if claim["lines"] and claim["warranty_deductible_cents"] is None:',
     "        if False:", ["tests/test_phase375_deductibles.py::TestRefusals"]),
    # ------------------------------------------------------------ covering
    ("C1 a claim is covered with no deductible on record", CLAIMS,
     '    if not covers_nothing and warranty.get("deductible_cents") is None:',
     "    if False:", PHASE),
    # ------------------------------------------------------------ the warranty
    ("W1 warranty update ignores --deductible-cents", REPO,
     "        if deductible_cents is not None:\n            conn.execute(\"UPDATE warranties SET deductible_cents",
     "        if False:\n            conn.execute(\"UPDATE warranties SET deductible_cents",
     PHASE),
    ("W2 warranty add does not store the deductible", REPO,
     "                warranty.repair_payer, warranty.deductible_cents,",
     "                warranty.repair_payer, None,", PHASE),
    # ------------------------------------------------------------ the packet
    ("P1 the packet does not show a line's deductible share", CLAIMS,
     '        if line.get("deductible_cents"):', "        if False:", PHASE),
    ("P2 the packet does not show the warranty's deductible", CLAIMS,
     '                                   else f"{_money(deductible)} per covered repair"))',
     '                                   else ""))', PHASE),
    # ------------------------------------------------------------ the tax readings
    ("T1 confirm does not carry the deductible rules forward", TAX,
     "        for rule in deductible_rules:", "        for rule in ():", PHASE),
    ("T2 confirm drops what the readings leave open", TAX,
     "                 f\"re-checked at {url}. {rule['notes'] or ''}\".strip()),",
     "                 f\"re-checked at {url}\"),", PHASE),
    ("T3 status does not list the deductible readings", TAX,
     "                deductible_rules[payer] = _item(row, payer, 1.0)", "                pass",
     PHASE),
    # ------------------------------------------------------------ migration 084
    ("M1 a deductible treatment other than its taxable share is allowed", MIGRATIONS,
     "CHECK (deductible_tax IN ('taxable_share'))", "", PHASE),
    ("M2 the maker's reading does not say what 03-8 leaves open", MIGRATIONS,
     "with no additional consideration from the retail customer; a deductible",
     "; a deductible", PHASE),
    ("M3 the rollback leaves the warranty's column", MIGRATIONS,
     "            ALTER TABLE warranties DROP COLUMN deductible_cents;\n", "", PHASE),
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
