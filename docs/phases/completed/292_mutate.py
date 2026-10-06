"""Phase 292's mutations: each breaks one thing Gate 16 checks, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/completed/292_mutate.py`
(moved from in_progress/ at close-out). 273's form: each mutation replaces
one exact string (which must occur once), runs its tests with `-B` after
clearing `__pycache__`, and restores the file whatever happens. Prints one
line per mutation and exits 1 if any stayed green. An argument runs only
the mutations whose name starts with it: `X` bug fix #1, the Xero tax
spread; `H` the hand-offs the walk checks; `M` the money; `P` payment.

No mutation can reach Stripe: the gate answers from 273's fixtures, and
281's network guard holds.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
GATE = ["tests/test_phase292_gate16.py"]
XERO = ["tests/test_phase292_xero_tax.py"]

EXPORT = "src/motodiag/accounting/export.py"
BOOKING = "src/motodiag/scheduling/booking.py"
SHOP_CLI = "src/motodiag/cli/shop.py"
CLAIMS = "src/motodiag/inventory/warranty_claims.py"
WARRANTY = "src/motodiag/inventory/warranty_repo.py"
INVOICING = "src/motodiag/shop/invoicing.py"
PAY = "src/motodiag/payments/invoice_payments.py"

MUTATIONS = [
    # ------------------------------------------------- bug fix #1, Xero's tax
    ("X1 every line shares the tax again", EXPORT,
     'if taxed is None or line["item_type"] in taxed]', "if True]", XERO + GATE),
    ("X2 tax with no taxed line is not refused", EXPORT,
     "    if tax and not on:", "    if False:", XERO),
    ("X3 an invoice made before the record spreads over no line", EXPORT,
     "        return None\n    return {t for t", "        return set()\n    return {t for t",
     XERO),
    # ------------------------------------------------------------ hand-offs
    ("H1 check-in --wo does not link the work order", BOOKING,
     '_move(appt_id, "in_progress", db_path, work_order_id=work_order_id,',
     '_move(appt_id, "in_progress", db_path, work_order_id=None,', GATE),
    ("H2 work-order create --intake drops the intake", SHOP_CLI,
     "                intake_visit_id=intake_identifier,",
     "                intake_visit_id=None,", GATE),
    ("H3 a claim drops its work order", CLAIMS,
     "(warranty_id, work_order_id, description.strip(),",
     "(warranty_id, None, description.strip(),", GATE),
    ("H4 an ended warranty is still valid", WARRANTY,
     "    elif on_date > end:", "    elif False:", GATE),
    ("H5 the export forgets what it carried", EXPORT,
     '            if inv["id"] in exported and not include_exported:',
     "            if False:", GATE),
    # ------------------------------------------------------------ the money
    ("M1 the invoice bills the estimate, not the hours worked", INVOICING,
     '    hours = wo.get("actual_hours")\n', '    hours = wo.get("estimated_hours")\n', GATE),
    ("M2 the invoice taxes every line", INVOICING,
     "    taxable_cents = sum(by_type[t] for t in decision.taxable_types)",
     "    taxable_cents = sum(by_type.values())", GATE),
    ("M3 QuickBooks leaves out the tax line", EXPORT,
     "        if tax:\n            rows.append({", "        if False:\n            rows.append({",
     GATE),
    # ------------------------------------------------------------ payment
    ("P1 starting a Checkout payment marks the invoice paid", PAY,
     '"UPDATE invoice_payments SET checkout_session_id = ?, livemode = ? WHERE id = ?",',
     "\"UPDATE invoices SET status = 'paid' WHERE ? IS NOT NULL AND ? IS NOT NULL AND id = ?\",",
     GATE),
    ("P2 an event of another amount pays the invoice", PAY,
     '    if received != row["amount_cents"] or received != owed:', "    if False:", GATE),
    ("P3 the invoice is issued as a draft", INVOICING,
     "        status=_AccountingInvoiceStatus.SENT,", "        status=_AccountingInvoiceStatus.DRAFT,",
     GATE),
    ("P4 cash leaves the invoice unpaid", INVOICING,
     "        status=_AccountingInvoiceStatus.PAID,", "        status=_AccountingInvoiceStatus.SENT,",
     GATE),
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
