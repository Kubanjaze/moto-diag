"""Phase 404's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/404_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 388's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`P` the plan's AI figure, `S` a paid call site, `N` the names and the CLI's
table, `B` the bike limit, `F` the feed's check-ins, `M` the migration.

No mutation makes a model call or reaches Stripe or Sentry: every test it
runs uses stand-ins.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

CAP = "src/motodiag/shop/cost_cap.py"
SUB = "src/motodiag/billing/subscription_repo.py"
LAB = "src/motodiag/shop/labor_estimator.py"
TRN = "src/motodiag/api/routes/transcripts.py"
COD = "src/motodiag/cli/code.py"
VID = "src/motodiag/intake/vehicle_identifier.py"
SRC = "src/motodiag/shop/parts_sourcing.py"
PRI = "src/motodiag/shop/priority_scorer.py"
SHP = "src/motodiag/cli/shop.py"
ERR = "src/motodiag/api/errors.py"
TIE = "src/motodiag/cli/subscription.py"
REG = "src/motodiag/vehicles/registry.py"
FED = "src/motodiag/payments/event_feed.py"
PAY = "src/motodiag/cli/payments.py"
MON = "src/motodiag/telemetry/monitor.py"
MIG = "src/motodiag/core/migrations.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_AI = pytest("tests/test_phase404_plan_ai_limit.py")
T_NAMES = pytest("tests/test_phase404_plan_names.py")
T_BIKE = pytest("tests/test_phase404_bike_limit.py", "tests/test_phase109_cli_foundation.py")
T_FEED = pytest("tests/test_phase404_feed_checkin_status.py")
T_MIG = pytest("tests/test_phase404_migration_090.py")

OWNER_SQL = ("\"SELECT DISTINCT user_id FROM shop_members \"\n"
             "            \"WHERE shop_id = ? AND role = 'owner' AND is_active = 1\",")
OWNER_WHERE = "\"WHERE shop_id = ? AND role = 'owner' AND is_active = 1\","

MUTATIONS = [
    ("P1 the plan figure off by one", [(CAP, '"shop": 5000,', '"shop": 5001,')], T_AI),
    ("P2 refused only past the figure, not at it", [(CAP,
     "if spent < min(limits):", "if spent <= min(limits):")], T_AI),
    ("P3 the shop's plan read from shops.owner_user_id", [(SUB,
     OWNER_SQL, "\"SELECT owner_user_id FROM shops WHERE id = ?\",")], T_AI),
    ("P4 the shop's plan read from every member, the caller's own included", [(SUB,
     OWNER_WHERE, "\"WHERE shop_id = ? AND is_active = 1\",")], T_AI),
    ("P5 an inactive owner counted", [(SUB,
     OWNER_WHERE, "\"WHERE shop_id = ? AND role = 'owner'\",")], T_AI),
    ("P6 the plan refuses even when the brake is lower", [(CAP,
     "(cap <= 0 or figure <= cap)", "True")], T_AI),
    ("P7 the API answers the brake's slug", [(ERR,
     '(PlanAILimitReached, 402, "plan-ai-limit-reached",',
     '(PlanAILimitReached, 402, "ai-spend-cap-reached",')], T_AI),
    ("S1 the labor estimate checks after the paid call", [
        (LAB, "        check_cost_cap(wo.get(\"shop_id\"), db_path=db_path)\n", ""),
        (LAB, "        payload = _parse_estimate(ai_resp.text, wo_id, skill_tier)\n",
         "        payload = _parse_estimate(ai_resp.text, wo_id, skill_tier)\n"
         "        check_cost_cap(wo.get(\"shop_id\"), db_path=db_path)\n")], T_AI),
    ("S2 the transcript upload unchecked", [(TRN,
     "    check_cost_cap(shop_id, db_path=db_path)\n", "")], T_AI),
    ("S3 code explain unchecked", [(COD,
     "    _check_cap(_resolve_shop(None, db_path), db_path)\n", "")], T_AI),
    ("S4 the photo identification unchecked", [(VID,
     "        check_cost_cap(only_shop(self._db_path), db_path=self._db_path)\n", "")], T_AI),
    ("S5 the parts sourcing unchecked", [(SRC,
     "        check_cost_cap(only_shop(db_path), db_path=db_path)\n", "")], T_AI),
    ("S6 the priority score unchecked", [(PRI,
     "        check_cost_cap(wo.get(\"shop_id\"), db_path=db_path)\n", "")], T_AI),
    ("S7 the labor command prints no red line", [(SHP,
     "            _refused_spend(console, e)\n        except (LaborEstimatorError, WorkOrderNotFoundError) as e:",
     "            raise\n        except (LaborEstimatorError, WorkOrderNotFoundError) as e:")], T_AI),
    ("N1 a name left as Solo Mechanic", [(TIE,
     'display_name="Individual: for your own bikes",', 'display_name="Solo Mechanic",')], T_NAMES),
    ("N2 Company's locations left unlimited", [(TIE, "max_locations=3,", "max_locations=-1,")], T_NAMES),
    ("N3 Company's AI row left at $500", [(TIE,
     "ai_monthly_cost_cap_usd=150.0,", "ai_monthly_cost_cap_usd=500.0,")], T_NAMES),
    ("B1 the Shop plan's bike cap back", [(REG, '"shop": -1,', '"shop": 50,')], T_BIKE),
    ("B2 the CLI's table drifts from the server's", [(TIE,
     "max_vehicles=-1,         # unlimited (Phase 404, F270)", "max_vehicles=50,")], T_BIKE),
    ("F1 a 401 recorded as accepted", [(FED,
     "(utc_at(now), 1 if sent.ok else 0, sent.answer, slug))",
     "(utc_at(now), 1, sent.answer, slug))")], T_FEED),
    ("F2 the monitor calls a 4xx accepted", [(MON,
     "return CheckinAnswer(False, answer)", "return CheckinAnswer(True, answer)")], T_FEED),
    ("F3 the stale window at one interval", [(PAY,
     "> 2 * settings.stripe_poll_checkin_s):", "> settings.stripe_poll_checkin_s):")], T_FEED),
    ("F4 never checking in is not a problem", [(PAY,
     'return ["the alarm has never checked in"]', "return []")], T_FEED),
    ("F5 a refused check-in is not a problem", [(PAY,
     "problems.append(f\"the last check-in was refused: {newest['answer']}\")", "pass")], T_FEED),
    ("F6 no housekeeping at the day's turn", [(FED,
     "            prune_checkins(self.db_path, self.clock())\n", "")], T_FEED),
    ("M1 the rollback keeps the table", [(MIG,
     "            DROP TABLE IF EXISTS stripe_feed_checkins;\n", "")], T_MIG),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    commands = []
    for m in chosen:
        if m[2] not in commands:
            commands.append(m[2])
    for command in commands:
        assert run(command) == 0, f"not green before mutating: {command}"
    survivors = []
    for name, edits, command in chosen:
        originals = {}
        try:
            for rel, old, new in edits:
                path = ROOT / rel
                originals.setdefault(rel, path.read_text())
                current = path.read_text()
                assert current.count(old) == 1, f"{name}: the text occurs {current.count(old)} times in {rel}"
                path.write_text(current.replace(old, new))
            code = run(command)
        finally:
            for rel, text in originals.items():
                (ROOT / rel).write_text(text)
        verdict = "red" if code != 0 else "GREEN (survived)"
        print(f"{name}: {verdict}", flush=True)
        if code == 0:
            survivors.append(name)
    for command in commands:
        assert run(command) == 0, f"not green after restoring: {command}"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
