"""Phase 275's mutations: each breaks one thing the batch promises, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/completed/275_mutate.py`
(moved from in_progress/ at close-out). 274's form: each mutation replaces one
exact string (which must occur once), runs its tests with `-B` after clearing
`__pycache__`, and restores the file whatever happens. Prints one line per
mutation and exits 1 if any stayed green. An argument runs only the
mutations whose name starts with it: `M` migration, `B` booking (275), `K`
the calendar (276), `A` the export files (277, 278).

The edit guard does not stop this script: a script run by name is outside
what it can see, which is its first known limit.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
T_MIG = ["tests/test_phase275_migration.py"]
T_BOOK = ["tests/test_phase275_booking.py"]
T_CAL = ["tests/test_phase275_calendar.py"]
T_ACC = ["tests/test_phase275_accounting_export.py"]

MIGRATIONS = "src/motodiag/core/migrations.py"
BOOKING = "src/motodiag/scheduling/booking.py"
CALENDAR = "src/motodiag/scheduling/calendar.py"
EXPORT = "src/motodiag/accounting/export.py"

MUTATIONS = [
    # ------------------------------------------------------------ migration 077
    ("M1 the rollback keeps appointments.shop_id", MIGRATIONS,
     "            ALTER TABLE appointments DROP COLUMN shop_id;\n", "", T_MIG),
    ("M2 an account's target is unchecked", MIGRATIONS,
     "                target TEXT NOT NULL\n"
     "                    CHECK (target IN ('quickbooks_online', 'xero')),\n"
     "                kind TEXT NOT NULL",
     "                target TEXT NOT NULL,\n"
     "                kind TEXT NOT NULL", T_MIG),
    # ------------------------------------------------------------ 275, booking
    ("B1 a mechanic can be double-booked", BOOKING,
     "            if clashes:\n                raise BookingError(_clash_message(clashes, \"The mechanic\"))\n"
     "            warnings = _bay_warnings(",
     "            if False:\n                raise BookingError(_clash_message(clashes, \"The mechanic\"))\n"
     "            warnings = _bay_warnings(", T_BOOK),
    ("B2 back-to-back appointments count as overlapping", BOOKING,
     "    return a_start < b_end and b_start < a_end",
     "    return a_start <= b_end and b_start <= a_end", T_BOOK),
    ("B3 a bike not linked to the customer is booked", BOOKING,
     "        if link is None:", "        if False:", T_BOOK),
    ("B4 a cancelled appointment still blocks its time", BOOKING,
     "('scheduled', 'confirmed', 'in_progress') AND id != ?",
     "('scheduled', 'confirmed', 'in_progress', 'cancelled') AND id != ?", T_BOOK),
    ("B5 an overlap with bay work gives no warning", BOOKING,
     "    return [\n        f\"The mechanic has work order",
     "    return [] and [\n        f\"The mechanic has work order", T_BOOK),
    ("B6 no recorded hours are read as 09:00-17:00", BOOKING,
     "        if hours is None:\n            raise BookingError(",
     "        if hours is None:\n            hours = (\"09:00\", \"17:00\")\n"
     "        if False:\n            raise BookingError(", T_BOOK),
    ("B7 a confirmation is not logged", BOOKING,
     "    contact_id = communication_repo.log_contact(",
     "    contact_id = 0 and communication_repo.log_contact(", T_BOOK),
    ("B8 check-in links another customer's work order", BOOKING,
     "        if mismatches:", "        if False:", T_BOOK),
    ("B9 a scheduled appointment can be completed", BOOKING,
     "    \"scheduled\": frozenset({\"confirmed\", \"in_progress\", \"cancelled\", \"no_show\"}),",
     "    \"scheduled\": frozenset({\"confirmed\", \"in_progress\", \"cancelled\", \"no_show\", \"completed\"}),",
     T_BOOK),
    ("B10 a day with no hours is not read as closed", BOOKING,
     "    if value is None or str(value).strip().lower() == \"closed\":",
     "    if False:", T_BOOK),
    # ------------------------------------------------------------ 276, the calendar
    ("K1 commas are not escaped", CALENDAR,
     r'.replace(",", "\\,")', "", T_CAL),
    ("K2 long lines are not folded", CALENDAR,
     "    limit = 75\n    for ch in line:", "    limit = 10**6\n    for ch in line:", T_CAL),
    ("K3 lines end in LF, not CRLF", CALENDAR,
     r'fold_line(line) + "\r\n" for line in lines', r'fold_line(line) + "\n" for line in lines',
     T_CAL),
    ("K4 a slot in another zone is read as clock time", BOOKING,
     "    return t.astimezone(timezone.utc).replace(tzinfo=None)",
     "    return t.replace(tzinfo=None)", T_CAL),
    ("K5 a mechanic's calendar shows everyone's bay work", CALENDAR,
     "        if mechanic_user_id is not None and s[\"mechanic_id\"] != mechanic_user_id:",
     "        if False:", T_CAL),
    ("K6 a cancelled appointment is written as confirmed", CALENDAR,
     "\"completed\": \"CONFIRMED\", \"cancelled\": \"CANCELLED\", \"no_show\": \"CANCELLED\",",
     "\"completed\": \"CONFIRMED\", \"cancelled\": \"CONFIRMED\", \"no_show\": \"CANCELLED\",",
     T_CAL),
    # ------------------------------------------------------------ 277, 278, the files
    ("A1 the tax credit line is dropped", EXPORT,
     "        if tax:\n            rows.append({", "        if False:\n            rows.append({", T_ACC),
    ("A2 an unbalanced entry is written", EXPORT,
     "        if credits != total:", "        if False:", T_ACC),
    ("A3 an exported invoice is exported again", EXPORT,
     "            if inv[\"id\"] in exported and not include_exported:", "            if False:", T_ACC),
    ("A4 cancelled invoices are exported", EXPORT,
     "WHERE wo.shop_id = ? AND i.status != 'cancelled'", "WHERE wo.shop_id = ? AND 1", T_ACC),
    ("A5 the tax remainder is lost", EXPORT,
     "    shares[-1] += tax_cents - sum(shares)", "    shares[-1] += 0", T_ACC),
    ("A6 a missing account is not refused", EXPORT,
     "    if missing:", "    if False:", T_ACC),
    ("A7 the plain statement is not printed", EXPORT,
     "            QBO_STATEMENT,\n", "", T_ACC),
    ("A8 Xero is written without a tax rate", EXPORT,
     "        if untaxed:", "        if False:", T_ACC),
    ("A9 a column not on either list is added", EXPORT,
     "    \"Currency\", \"BrandingTheme\",\n)\n\nQBO_STATEMENT",
     "    \"Currency\", \"BrandingTheme\", \"Reference\",\n)\n\nQBO_STATEMENT", T_ACC),
    ("A10 an existing file is overwritten", EXPORT,
     "    if path.exists():\n        raise ExportError", "    if False:\n        raise ExportError",
     T_ACC),
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
