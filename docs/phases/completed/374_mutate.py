"""Phase 374's mutations: each breaks one thing the phase built, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/completed/374_mutate.py`
(written in in_progress/; ROOT is three levels up either way).
373's form: each mutation replaces one exact string (which must occur once),
runs its tests with `-B` after clearing `__pycache__`, and restores the file
whatever happens. Prints one line per mutation and exits 1 if any stayed
green. An argument runs only the mutations whose name starts with it: `L`
linking, `R` recording, `W` with a work order, `P` the packet, `S` showing.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PHASE = ["tests/test_phase374_check_in_intake.py"]
GATE = ["tests/test_phase292_gate16.py"]

BOOKING = "src/motodiag/scheduling/booking.py"
INTAKE = "src/motodiag/shop/intake_repo.py"
CLAIMS = "src/motodiag/inventory/warranty_claims.py"
CLI = "src/motodiag/cli/shop_booking.py"
SHOP_CLI = "src/motodiag/cli/shop.py"

MUTATIONS = [
    # ------------------------------------------------------------ linking
    ("L1 an open intake is linked whenever it was taken", BOOKING,
     '            and abs(intake_clock_time(candidates[0]["intake_at"]) - start) <= INTAKE_WINDOW):',
     "            ):", PHASE),
    ("L2 the window is two days", BOOKING,
     "INTAKE_WINDOW = timedelta(days=1)", "INTAKE_WINDOW = timedelta(days=2)", PHASE),
    ("L3 the newest of two open intakes is linked", BOOKING,
     "    if (len(candidates) == 1", "    if (len(candidates) >= 1", PHASE),
    ("L4 the intake's UTC time is read as the shop's clock", BOOKING,
     "    return t.astimezone().replace(tzinfo=None)", "    return t.replace(tzinfo=None)",
     PHASE),
    ("L5 a closed intake is a candidate", BOOKING,
     'vehicle_id=appt["vehicle_id"], status="open", limit=0',
     'vehicle_id=appt["vehicle_id"], status=None, limit=0', PHASE),
    ("L6 another customer's intake is a candidate", BOOKING,
     'shop_id=appt["shop_id"], customer_id=appt["customer_id"],',
     'shop_id=appt["shop_id"],', PHASE),
    ("L7 a closed intake named with --intake is linked", BOOKING,
     '        if intake["status"] != "open":', "        if False:", PHASE),
    ("L8 another customer's intake named with --intake is linked", BOOKING,
     "            raise BookingError(f\"intake #{intake_id} is for another {', '.join(mismatches)}\")",
     "            pass", PHASE),
    ("L9 details given with an open intake are dropped", BOOKING,
     '        if given:\n            raise BookingError(\n                f"{intake_label',
     '        if False:\n            raise BookingError(\n                f"{intake_label', PHASE),
    ("L10 the work order is opened without its intake", BOOKING,
     '            intake_visit_id=intake["id"],\n', "", PHASE + GATE),
    # ------------------------------------------------------------ recording
    ("R1 a recorded intake leaves out the booking's notes", BOOKING,
     'reported_problems=problems if problems is not None else appt["notes"],',
     "reported_problems=problems,", PHASE + GATE),
    ("R2 the intake is stamped in local time", INTAKE,
     'datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")',
     'datetime.now().strftime("%Y-%m-%d %H:%M:%S")', PHASE),
    ("R3 no hint to record the mileage", CLI,
     '        if done.intake["mileage_at_intake"] is None:', "        if False:", PHASE),
    ("R4 no warning of the bike's other open intakes", CLI,
     "            if others:", "            if False:", PHASE),
    # ------------------------------------------------------------ with --wo
    ("W1 --wo takes intake options and ignores them", BOOKING,
     "        if intake_id is not None or mileage is not None or problems is not None:",
     "        if False:", PHASE),
    ("W2 --wo does not print the work order's intake", BOOKING,
     '        if wo["intake_visit_id"] is not None:', "        if False:", PHASE),
    # ------------------------------------------------------------ the packet
    ("P1 an unknown mileage at intake falls back to the bike's", CLAIMS,
     '        mileage = (intake["mileage_at_intake"] if intake is not None',
     '        mileage = (intake["mileage_at_intake"] if intake is not None'
     ' and intake["mileage_at_intake"] is not None', PHASE),
    ("P2 the packet leaves out the mileage at intake", CLAIMS,
     '        out.append("Mileage at intake: " + _miles(intake["mileage_at_intake"]))',
     "        pass", PHASE + GATE),
    ("P3 the packet leaves out the reported problems", CLAIMS,
     '        if intake["reported_problems"]:', "        if False:", PHASE + GATE),
    # ------------------------------------------------------------ showing
    ("S1 work-order show prints only the intake's id", SHOP_CLI,
     '        lines.append(f"Intake:   {intake_label(intake)}")',
     "        lines.append(f\"Intake:   id={intake['id']}\")", PHASE),
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
