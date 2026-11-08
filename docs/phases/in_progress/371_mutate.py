"""Phase 371's mutations: each breaks one guard the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/371_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 392's harness, as
348's: exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`F` the feed, `A` the alarm, `L` the limit check, `C` the commands and the mask.

No mutation reads the live database or reaches the network.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

A = "src/motodiag/"
FEED, MON = A + "payments/event_feed.py", A + "telemetry/monitor.py"
CLI, MAIN = A + "cli/payments.py", A + "cli/main.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-p", "no:xdist", "-o", "addopts=", *args]


T_FEED = pytest("tests/test_phase371_event_feed.py")
T_MON = pytest("tests/test_phase371_monitor.py")
T_LIM = pytest("tests/test_phase371_limits.py")
T_CLI = pytest("tests/test_phase371_cli.py")

MUTATIONS = [
    # the feed
    ("F1 the overlap set to 0",
     [(FEED, "OVERLAP_S = 300", "OVERLAP_S = 0")], T_FEED),
    ("F2 types dropped from the ask",
     [(FEED, '"types": list(FEED_TYPES), "limit": PAGE_LIMIT}',
       '"limit": PAGE_LIMIT}')], T_FEED),
    ("F3 Stripe-Account not sent for a shop",
     [(FEED, 'options = None if account == PLATFORM else {"stripe_account": account}',
       "options = None")], T_FEED),
    ("F4 the shop's id not written into an event without account",
     [(FEED, '            event["account"] = account\n', "            pass\n")], T_FEED),
    ("F5 an older event moves last_created backwards",
     [(FEED, "    if not done.hold and done.newest > place:",
       "    if not done.hold and done.newest:")], T_FEED),
    ("F6 a retry=True result advances the cursor",
     [(FEED, "    if not done.hold and done.newest > place:",
       "    if done.newest > place:")], T_FEED),
    ("F7 the 30-day floor removed",
     [(FEED, "    if place < floor:", "    if False:"),
      (FEED, "    return place, max(place - OVERLAP_S, floor), gap",
       "    return place, place - OVERLAP_S, gap")], T_FEED),
    ("F8 the back-off never doubles",
     [(FEED, "            self.wait = min(self.wait * 2, MAX_BACKOFF_S)",
       "            self.wait = self.settings.stripe_poll_interval_s")], T_FEED),
    # the alarm
    ("A1 the check-in URL without the key segment",
     [(MON, 'f"{dsn.project_id}/cron/{slug}/{dsn.public_key}/")',
       'f"{dsn.project_id}/cron/{slug}/")')], T_MON),
    ("A2 the margin set to 0",
     [(MON, "MARGIN_MINUTES = 10", "MARGIN_MINUTES = 0")], T_MON),
    # the limit check
    ("L1 shops_plan compared with > instead of >=",
     [(FEED, "    if shops >= settings.stripe_feed_shops_plan:",
       "    if shops > settings.stripe_feed_shops_plan:")], T_LIM),
    ("L2 a notice sent on every check",
     [(FEED, "        if already_sent(db_path, line, utc_day(now)):\n            continue\n",
       "")], T_LIM),
    ("L3 the guide's page dropped from the notice text",
     [(FEED, 'GUIDE = "docs/guide/payments.md"', 'GUIDE = "the guide"')], T_LIM),
    # the commands and the mask
    ("C1 webhook_secret dropped from SECRET_SETTING_NAMES",
     [(MAIN, 'SECRET_SETTING_NAMES = ("api_key", "sentry_dsn", "webhook_secret")',
       'SECRET_SETTING_NAMES = ("api_key", "sentry_dsn")')], T_CLI),
    ("C2 feed status exits 0 with a stale polled_at",
     [(CLI, "    return now - asked > 2 * interval_s", "    return False")], T_CLI),
]


def clear_caches() -> None:
    for d in (ROOT / "src").rglob("__pycache__"):
        for f in d.glob("*.pyc"):
            f.unlink()


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
                assert current.count(old) == 1, \
                    f"{name}: the text occurs {current.count(old)} times in {rel}"
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
