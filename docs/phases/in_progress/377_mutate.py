"""Phase 377's mutations: each undoes one thing the phase adds, and the
tests named beside it must go red.

M1 is the planted control the prompt asks for: a return to local time in
the work order's completion stamp. LOCAL reads the clock through
``core/timestamps``, so under the tests' frozen clock it is the naive local
time the old code wrote, at the frozen moment.

Run from the repository root: `.venv/bin/python docs/phases/completed/377_mutate.py`
(moved from in_progress/ at close-out). 370's form: each mutation replaces one
exact string (which must occur once), runs its tests with `-B` after
clearing `__pycache__`, and restores the file whatever happens. Prints one
line per mutation and exits 1 if any stayed green.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
T = "tests/test_phase377_shop_utc.py"
TESTS = [T]
S = "src/motodiag/"
STAMP = S + "core/timestamps.py"
WO = S + "shop/work_order_repo.py"
INTAKE = S + "shop/intake_repo.py"
ISSUE = S + "shop/issue_repo.py"
ANALYTICS = S + "shop/analytics.py"
EXPORT = S + "accounting/export.py"
CLI = S + "cli/shop.py"
REPORT = S + "reporting/builders.py"
SHOP_API = S + "api/routes/shop_mgmt.py"
VEHICLE_API = S + "api/routes/vehicles.py"
MIGRATIONS = S + "core/migrations.py"
BOOKING = S + "scheduling/booking.py"
CUSTOMERS = S + "crm/customer_repo.py"
LOCAL = "__import__('motodiag.core.timestamps', fromlist=['datetime']).datetime.now().isoformat()"

MUTATIONS = [
    ("M1 complete_work_order returns to local time (the planted control)", WO,
     "    now = utc_now()\n    actual_hours = _validate_hours(actual_hours, \"actual_hours\")\n",
     f"    now = {LOCAL}\n    actual_hours = _validate_hours(actual_hours, \"actual_hours\")\n",
     TESTS),
    ("M2 a relative cutoff is local time in the T shape (F191's cutoff)", STAMP,
     "    return moment.astimezone(timezone.utc).strftime(SQLITE_UTC)\n",
     "    return moment.astimezone().replace(tzinfo=None).isoformat()\n", TESTS),
    ("M3 list_intakes compares intake_at as text", INTAKE,
     "        conditions.append(\"datetime(iv.intake_at) >= ?\")\n        params.append(cutoff)\n"
     "    if conditions:\n        query += \" WHERE \" + \" AND \".join(conditions)\n    query +=",
     "        conditions.append(\"iv.intake_at >= ?\")\n        params.append(cutoff)\n"
     "    if conditions:\n        query += \" WHERE \" + \" AND \".join(conditions)\n    query +=",
     TESTS),
    ("M4 count_intakes compares intake_at as text", INTAKE,
     "        conditions.append(\"datetime(iv.intake_at) >= ?\")\n        params.append(cutoff)\n"
     "    if conditions:\n        query += \" WHERE \" + \" AND \".join(conditions)\n    with",
     "        conditions.append(\"iv.intake_at >= ?\")\n        params.append(cutoff)\n"
     "    if conditions:\n        query += \" WHERE \" + \" AND \".join(conditions)\n    with",
     TESTS),
    ("M5 list_work_orders compares created_at as text", WO,
     "\"datetime(wo.created_at) >= ?\"", "\"wo.created_at >= ?\"", TESTS),
    ("M6 list_issues compares reported_at as text", ISSUE,
     "\"datetime(i.reported_at) >= ?\"", "\"i.reported_at >= ?\"", TESTS),
    ("M7 throughput compares completed_at as text (F186)", ANALYTICS,
     "WHERE shop_id = ? AND completed_at IS NOT NULL\n                 AND datetime(completed_at) >= ?",
     "WHERE shop_id = ? AND completed_at IS NOT NULL\n                 AND completed_at >= ?",
     TESTS),
    ("M8 completions are grouped by the UTC date", ANALYTICS,
     "        day = local_day(r[\"completed_at\"])\n",
     "        day = str(r[\"completed_at\"])[:10]\n", TESTS),
    ("M9 turnaround parses each time as written (a legacy naive one cannot subtract)", ANALYTICS,
     "        opened = stored_instant(row[\"opened_at\"])\n",
     "        opened = datetime.fromisoformat(row[\"opened_at\"])\n", TESTS),
    ("M10 turnaround drops a bad time in silence", ANALYTICS,
     "    except ValueError as e:\n        raise ValueError(\n            f\"work order {row['id']}",
     "    except ValueError as e:\n        return -1.0\n        raise ValueError(\n            f\"work order {row['id']}",
     TESTS),
    ("M11 the P&L month is the UTC month", ANALYTICS,
     "(shop_id, local_day_start(start), local_day_start(end)),",
     "(shop_id, start + \" 00:00:00\", end + \" 00:00:00\"),", TESTS),
    ("M12 the export's window is UTC days", EXPORT,
     "    return local_day_start(from_day), local_day_start(after)\n",
     "    return f\"{from_day} 00:00:00\", f\"{after} 00:00:00\"\n", TESTS),
    ("M13 the export's invoice date is the UTC date", EXPORT,
     "    day = text if len(text) == 10 else local_day(text)\n",
     "    day = text[:10]\n", TESTS),
    ("M14 local_display shows SQLite's UTC as written", STAMP,
     "        if not _SQLITE_SHAPE.match(text):\n            return value\n",
     "        return value\n", TESTS),
    ("M15 the API passes each time on as stored", STAMP,
     "                out[key] = to_utc(value)\n", "                out[key] = value\n", TESTS),
    ("M16 the shop API's list is not converted", SHOP_API,
     "    return {\"items\": [with_utc_times(r) for r in rows], \"total\": len(rows)}\n",
     "    return {\"items\": rows, \"total\": len(rows)}\n", TESTS),
    ("M17 the vehicle API is not converted", VEHICLE_API,
     "    row = with_utc_times(row)  # times in the stored UTC format (Phase 377)\n", "", TESTS),
    ("M18 work-order show prints the stored Opened", CLI,
     "{local_display(wo['opened_at'])}", "{wo['opened_at']}", TESTS),
    ("M19 intake show prints the stored time", CLI,
     "    lines.append(f\"Intake at: {local_display(intake.get('intake_at')) or '?'}\")\n",
     "    lines.append(f\"Intake at: {intake.get('intake_at', '?')}\")\n", TESTS),
    ("M20 issue show prints the stored Reported", CLI,
     "{local_display(issue.get('reported_at')) or '?'}", "{issue.get('reported_at', '?')}", TESTS),
    ("M21 the work-order report prints the stored intake time", REPORT,
     "(\"Intake\", str(local_display(wo.get(\"intake_at\")) or \"—\")),",
     "(\"Intake\", str(wo.get(\"intake_at\") or \"—\")),", TESTS),
    ("M22 082 converts SQLite's space-shaped UTC too", STAMP,
     "                if value is not None and _NAIVE_LOCAL.match(str(value))\n",
     "                if value is not None\n", TESTS),
    ("M23 082's rollback leaves the times in UTC", MIGRATIONS,
     "            f\"WHERE {column} LIKE '%+00:00';\\n\"\n", "            f\"WHERE 0;\\n\"\n", TESTS),
    ("M24 a booking change stamps updated_at in local time", BOOKING,
     "        updated_at=utc_now(), **fields,\n", f"        updated_at={LOCAL}, **fields,\n", TESTS),
    ("M25 update_customer stamps local", CUSTOMERS,
     "    filtered[\"updated_at\"] = utc_now()\n", f"    filtered[\"updated_at\"] = {LOCAL}\n", TESTS),
    ("M26 a typed date is read as UTC (the old analytics rule)", STAMP,
     "    if moment.tzinfo is None:\n        moment = moment.astimezone()  # the shop's zone (F192)\n",
     "    if moment.tzinfo is None:\n        moment = moment.replace(tzinfo=timezone.utc)\n", TESTS),
]


def run_tests(tests: list[str]) -> int:
    for base in (ROOT / "src", ROOT / "tests"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:xdist",
         *tests],
        cwd=ROOT, capture_output=True, text=True,
    ).returncode


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].split()[0] in argv]
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
