"""Phase 281's mutations: each breaks one thing the batch promises, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/completed/281_mutate.py`
(moved from in_progress/ at close-out). 274's and 275's form: each mutation
replaces one exact string (which must occur once), runs its tests with `-B`
after clearing `__pycache__`, and restores the file whatever happens. Prints
one line per mutation and exits 1 if any stayed green. An argument runs only
the mutations whose name starts with it: `G` the network guard, `M` migration
078, `O` the outbound client, `R` recalls (281), `V` VIN decoding (287), `T`
tax and invoices (288), `X` exchange rates (289), `Y` bug fix #1.

No mutation can reach a real service: the network guard's own tests name
only reserved hosts, and every other test answers from recorded fixtures.
The edit guard does not stop this script: a script run by name is outside
what it can see.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
T_GUARD = ["tests/test_phase281_network_guard.py"]
T_MIG = ["tests/test_phase281_migration.py"]
T_TAX = ["tests/test_phase281_tax.py"]
T_X = ["tests/test_phase281_exchange.py"]
T_REC = ["tests/test_phase281_recalls.py"]
T_VIN = ["tests/test_phase281_vin.py"]
T_YEAR = ["tests/test_phase281_vin_year.py"]

GUARD = "tests/support/network_guard.py"
MIGRATIONS = "src/motodiag/core/migrations.py"
OUTBOUND = "src/motodiag/core/outbound.py"
NHTSA = "src/motodiag/advanced/nhtsa.py"
RECALLS = "src/motodiag/advanced/recall_repo.py"
INV_RECALLS = "src/motodiag/inventory/recall_repo.py"
CLI_ADV = "src/motodiag/cli/advanced.py"
TAX = "src/motodiag/accounting/tax.py"
CLI_TAX = "src/motodiag/cli/shop_tax.py"
INVOICING = "src/motodiag/shop/invoicing.py"
CLI_SHOP = "src/motodiag/cli/shop.py"
ERRORS = "src/motodiag/api/errors.py"
EXCHANGE = "src/motodiag/accounting/exchange.py"
CLI_CUR = "src/motodiag/cli/shop_currency.py"

MUTATIONS = [
    # ------------------------------------------------------------ the network guard
    ("G1 every host counts as loopback", GUARD,
     "    if host in _LOOPBACK_NAMES:\n        return True\n", "    return True\n", T_GUARD),
    ("G2 name lookups are not guarded", GUARD,
     "    socket.getaddrinfo = _guarded_getaddrinfo\n", "", T_GUARD),
    # ------------------------------------------------------------ migration 078
    ("M1 the rollback keeps invoices.tax_rate", MIGRATIONS,
     "            ALTER TABLE invoices DROP COLUMN tax_rate;\n", "", T_MIG),
    ("M2 the diagnostic rule is shipped as stated", MIGRATIONS,
     "SELECT id, NULL, 'diagnostic', 0, 'reading',",
     "SELECT id, NULL, 'diagnostic', 0, 'stated',", T_MIG),
    ("M3 Massachusetts's rate is valid 24 months", MIGRATIONS,
     "SELECT id, NULL, 0.0625, '2009-08-01', '2027-09-30',",
     "SELECT id, NULL, 0.0625, '2009-08-01', '2028-09-30',", T_MIG),
    ("M4 a shop row can claim regulation provenance", MIGRATIONS,
     "                CHECK ((provenance = 'regulation') = (shop_id IS NULL)),\n"
     "                FOREIGN KEY (jurisdiction_id)\n"
     "                    REFERENCES tax_jurisdictions(id) ON DELETE CASCADE,\n"
     "                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,\n"
     "                FOREIGN KEY (entered_by_user_id) REFERENCES users(id) ON DELETE SET NULL\n"
     "            );\n"
     "            CREATE INDEX IF NOT EXISTS idx_tax_rates_jurisdiction",
     "                FOREIGN KEY (jurisdiction_id)\n"
     "                    REFERENCES tax_jurisdictions(id) ON DELETE CASCADE,\n"
     "                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,\n"
     "                FOREIGN KEY (entered_by_user_id) REFERENCES users(id) ON DELETE SET NULL\n"
     "            );\n"
     "            CREATE INDEX IF NOT EXISTS idx_tax_rates_jurisdiction", T_MIG),
    # ------------------------------------------------------------ the outbound client
    ("O1 a 403 is not a block", OUTBOUND, "    if status == 403:\n", "    if False:\n",
     T_REC),
    ("O2 a web page where data was expected is accepted", OUTBOUND,
     "    if _looks_like_html(body):\n", "    if False:\n", T_REC + T_X),
    ("O3 an accepted status is refused (NHTSA's 400 zero answer)", OUTBOUND,
     "    if not (200 <= status < 300) and status not in accept:",
     "    if not (200 <= status < 300):", T_REC),
    # ------------------------------------------------------------ 281, recalls
    ("R1 a 400 carrying campaigns is accepted", NHTSA,
     "    if response.status == 400 and count != 0:", "    if False:", T_REC),
    ("R2 a Count that disagrees with the results is accepted", NHTSA,
     "    if not isinstance(count, int) or count != len(results):",
     "    if not isinstance(count, int):", T_REC),
    ("R3 a failed fetch returns an empty result", RECALLS,
     "                          exc.message)\n        raise\n",
     "                          exc.message)\n"
     "        return {\"fetch_id\": None, \"url\": \"\", \"status\": 0, \"count\": 0, "
     "\"campaigns\": [], \"recall_ids\": [], \"fetched_at\": \"\", \"size\": 0}\n", T_REC),
    ("R4 NHTSA's park flags are ignored", RECALLS,
     "    severity = \"critical\" if (result.get(\"parkIt\") or result.get(\"parkOutSide\")) "
     "else \"unrated\"",
     "    severity = \"unrated\"", T_REC),
    ("R5 an unrated campaign is stored medium", RECALLS,
     "else \"unrated\"", "else \"medium\"", T_REC),
    ("R6 a fetched campaign matches a whole make (lookup)", INV_RECALLS,
     "WHERE ((source IS NULL AND make = ?", "WHERE ((make = ?", T_REC),
    ("R7 a fetched campaign matches a whole make (the predictor's feed)", RECALLS,
     "                  AND ((r.source IS NULL\n", "                  AND ((1\n", T_REC),
    ("R8 zero fetched results clear a bike", CLI_ADV,
     "            if state[\"fetch\"] is not None or _legacy_recall_count() == 0:",
     "            if state[\"fetch\"] is None and _legacy_recall_count() == 0:", T_REC),
    ("R9 every bike is refreshed without the known campaign", RECALLS,
     "    if known[\"campaign\"] not in check[\"campaigns\"]:", "    if False:", T_REC),
    ("R10 a bike that fails is not reported", RECALLS,
     "            failed.append({**bike, \"error\": exc.message})\n", "", T_REC),
    ("R11 NHTSA's dates are read month first", RECALLS,
     "\"%d/%m/%Y\"", "\"%m/%d/%Y\"", T_REC),
    ("R12 check-vin ignores the stored decode", CLI_ADV,
     "online = _check_vin_online(console, vin) if refresh else stored_vin_decode(vin)",
     "online = _check_vin_online(console, vin) if refresh else None", T_REC),
    # ------------------------------------------------------------ 287, VIN decoding
    ("V1 a stored decode is asked for again", RECALLS,
     "    if not refresh:\n        stored = stored_vin_decode(vin_upper, db_path)",
     "    if False:\n        stored = stored_vin_decode(vin_upper, db_path)", T_VIN),
    ("V2 a partial decode is not labelled", RECALLS,
     "    return (decoded.get(\"error_code\") or \"0\").strip() not in (\"\", \"0\")",
     "    return False", T_VIN),
    ("V3 --save replaces a bike's VIN", RECALLS,
     "        if bike[\"vin\"]:", "        if False:", T_VIN),
    ("V4 a disagreement with the bike is not reported", RECALLS,
     "            if theirs and mine and str(mine).strip().upper() != "
     "str(theirs).strip().upper():",
     "            if False:", T_VIN),
    # ------------------------------------------------------------ 288, tax and invoices
    ("T1 tax falls on the whole subtotal", INVOICING,
     "    taxable_cents = sum(by_type[t] for t in decision.taxable_types)",
     "    taxable_cents = subtotal_cents", T_TAX),
    ("T2 a rate past its validity is used", TAX,
     "        where += \" AND effective_from <= ? AND valid_until >= ?\"",
     "        where += \" AND effective_from <= ? AND ? IS NOT NULL\"", T_TAX),
    ("T3 the regulation wins over the shop's own rate", TAX,
     "    if own is not None:\n        return own\n", "    if False:\n        return own\n",
     T_TAX),
    ("T4 a failing status exits 0", CLI_TAX,
     "        if not st.ok:\n            raise click.exceptions.Exit(1)",
     "        if False:\n            raise click.exceptions.Exit(1)", T_TAX),
    ("T5 confirm moves validity 6 months", TAX,
     "until = add_months(checked, REGULATION_RECHECK_MONTHS).isoformat()",
     "until = add_months(checked, 6).isoformat()", T_TAX),
    ("T6 a line type with no rule is taxed as not taxable", TAX,
     "            if row is None:\n"
     "                problems.append(_missing_rule(conn, jur, shop_id, on, line_type))\n",
     "            if row is None:\n                pass\n", T_TAX),
    ("T7 the API answers 422, not 409", ERRORS,
     "(InvoiceTaxNotOnRecord, 409,", "(InvoiceTaxNotOnRecord, 422,", T_TAX),
    ("T8 the invoice does not print its recheck date", CLI_SHOP,
     "        lines.append(f\"Rate must be re-checked by {summary.tax_recheck_by}\")\n",
     "", T_TAX),
    ("T9 a half cent rounds to even", INVOICING,
     "    tax_cents = int((Decimal(taxable_cents) * Decimal(str(decision.rate.value)))\n"
     "                    .quantize(Decimal(1), ROUND_HALF_UP))",
     "    tax_cents = int((Decimal(taxable_cents) * Decimal(str(decision.rate.value)))\n"
     "                    .quantize(Decimal(1)))", T_TAX),
    ("T10 the invoice's currency is always USD", INVOICING,
     "        currency=invoice_currency,", "        currency=\"USD\",", T_TAX),
    ("T11 another currency is invoiced with no rate of the shop's own", INVOICING,
     "        if fx_rate_row is None:\n            raise InvoiceGenerationError(",
     "        if False:\n            raise InvoiceGenerationError(", T_TAX),
    # ------------------------------------------------------------ 289, exchange rates
    ("X1 ECB rates last 4 days", EXCHANGE, "ECB_VALID_DAYS = 5", "ECB_VALID_DAYS = 4", T_X),
    ("X2 a cross rate is not labelled", EXCHANGE,
     "        method, rate_id = \"cross\", None", "        method, rate_id = \"direct\", None",
     T_X),
    ("X3 a conversion by an ECB rate omits the caveat", CLI_CUR,
     "        if conv.is_ecb:\n", "        if False:\n", T_X),
    ("X4 a shop's rate past its validity is used", EXCHANGE,
     "\"AND base = ? AND quote = ? AND rate_date <= ? AND valid_until >= ? \"",
     "\"AND base = ? AND quote = ? AND rate_date <= ? AND ? IS NOT NULL \"", T_X),
    # ------------------------------------------------------------ bug fix #1
    ("Y1 the year code picks the closest cycle again", RECALLS,
     "    while year + 30 <= latest_possible:", "    while year + 15 < latest_possible:",
     T_YEAR),
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
