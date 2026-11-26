"""Phase 210's mutations: each breaks one row the day walks, or one thing the
launch check holds, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/210_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 388's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it.

Every test runs on temporary databases and stand-ins; nothing reads the live
database.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

DEPS = "src/motodiag/auth/deps.py"
SHOP = "src/motodiag/api/routes/shop_mgmt.py"
TAX = "src/motodiag/accounting/tax.py"
PAY = "src/motodiag/payments/invoice_payments.py"
AUDIT = "src/motodiag/audit/log.py"
SNAP = "src/motodiag/backup/snapshot.py"
CAPS = "src/motodiag/vehicles/registry.py"
CHECK = "src/motodiag/launch/check.py"
LAUNCH = "src/motodiag/cli/launch.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-p", "no:xdist", "-o", "addopts=", *args]


DAY = "tests/test_phase210_first_shops_day.py"
LC = "tests/test_phase210_launch_check.py"


def day(test: str) -> list[str]:
    return pytest(f"{DAY}::{test}")


def lc(*k: str) -> list[str]:
    return pytest(LC, "-k", " or ".join(k))


MUTATIONS = [
    ("M1 the terms gate without its version comparison", [(DEPS,
     "                and not terms.has_accepted(api_key.user_id, terms.TERMS_VERSION,\n"
     "                                           db_path)):",
     "                and False):")],
     day("test_the_terms")),
    ("M2 creating a customer without the membership check", [(SHOP,
     "    require_shop_access(shop_id, user, db_path)\n    customer = Customer(",
     "    customer = Customer(")],
     day("test_a_customer_and_a_bike")),
    ("M3 no 409 for a shop with no tax jurisdiction", [(TAX,
     "    wanted = [t for t in LINE_TYPES if t in set(line_types)]\n"
     "    jur = shop_jurisdiction(shop_id, db_path=db_path)\n    if jur is None:",
     "    wanted = [t for t in LINE_TYPES if t in set(line_types)]\n"
     "    jur = shop_jurisdiction(shop_id, db_path=db_path)\n    if jur is None and False:")],
     day("test_an_invoice_at_the_shops_own_tax_rate")),
    ("M4 the feed's succeeded event leaves the invoice unpaid", [(PAY,
     '        if outcome == "paid_invoice":\n            changed = conn.execute(',
     '        if outcome == "paid_invoice" and False:\n            changed = conn.execute(')],
     day("test_paid_by_card_through_the_payments_feed")),
    ("M5 the audit row without the actor's username", [(AUDIT,
     '            "actor_username": event.actor_username,',
     '            "actor_username": None,')],
     day("test_the_audit_log_names_who_did_each_step")),
    ("M6 the manuals folder out of the backup", [(SNAP,
     'MEDIA_DIRS = ("videos", "photos", "audio", "manuals")',
     'MEDIA_DIRS = ("videos", "photos", "audio")')],
     day("test_the_nights_backup")),
    ("M7 adding a member without manage_shop", [(SHOP,
     '    require_shop_access(shop_id, user, db_path, permission="manage_shop")\n'
     "    add_shop_member(",
     "    require_shop_access(shop_id, user, db_path)\n    add_shop_member(")],
     day("test_each_limited_to_their_role")),
    ("M8 the Shop plan's bike cap at 50", [(CAPS,
     '    "shop": -1,', '    "shop": 50,')],
     day("test_the_plans_limits")),
    ("M9 the schema condition one version behind", [(CHECK,
     "    if found != SCHEMA_VERSION:", "    if found != SCHEMA_VERSION - 1:")],
     lc("ready_stand_in", "schema")),
    ("M10 the test shop active read as ready", [(CHECK,
     "    if row[0]:\n", "    if not row[0]:\n")],
     lc("ready_stand_in", "shop")),
    ("M11 the key's value in condition 2's detail", [(CHECK,
     '        ("key", key, key == "live"),',
     '        ("key", settings.stripe_api_key or key, key == "live"),')],
     lc("planted")),
    ("M12 SOMETHING IS OFF exits 0", [(LAUNCH,
     '        click.echo("SOMETHING IS OFF")\n        raise click.exceptions.Exit(1)\n',
     '        click.echo("SOMETHING IS OFF")\n')],
     lc("broken_alone")),
    ("M13 the check opens the database through init_db", [(CHECK,
     '    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)',
     "    from motodiag.core.database import init_db\n    init_db(str(path))\n"
     '    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)')],
     lc("init_db", "bulletins")),
    ("M14 the disk floor at 5 GB", [(CHECK,
     "DISK_FLOOR_GB = 50\n", "DISK_FLOOR_GB = 5\n")],
     lc("disk_floor", "under_50")),
    ("M15 the backup with no age bound", [(CHECK,
     "    if age_h > BACKUP_MAX_AGE_H:", "    if False:")],
     lc("26_hours")),
    ("M16 the loopback read to any host", [(CHECK,
     "    if host not in LOOPBACK_HOSTS:", "    if False:")],
     lc("loopback_server")),
    ("M17 condition 3 without its own DSN test", [(CHECK,
     "    if event_feed.alarm_dsn(settings) is None:\n"
     '        problems.append("the alarm is off: no Sentry DSN")\n', "")],
     lc("no_DSN", "no_dsn")),
    ("M18 the complete transition without the ledger's fill", [(SHOP,
     "            if tracked > 0:\n                hours = round(tracked / 3600.0, 2)",
     "            if False:\n                hours = round(tracked / 3600.0, 2)")],
     day("test_a_work_order_with_parts_and_labour")),
]


def clear_caches() -> None:
    for folder in ROOT.joinpath("src").rglob("__pycache__"):
        shutil.rmtree(folder, ignore_errors=True)


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode


def apply(rel: str, old: str, new: str, originals: dict) -> None:
    path = ROOT / rel
    originals.setdefault(rel, path.read_text(encoding="utf-8"))
    current = path.read_text(encoding="utf-8")
    assert current.count(old) == 1, f"the text occurs {current.count(old)} times in {rel}"
    path.write_text(current.replace(old, new), encoding="utf-8")


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0] + " ")
              or m[0].startswith(argv[0])]
    commands: list[list[str]] = []
    for m in chosen:
        if m[2] not in commands:
            commands.append(m[2])
    for command in commands:
        assert run(command) == 0, f"not green before mutating: {command}"
    survivors = []
    for name, edits, command in chosen:
        originals: dict = {}
        try:
            for rel, old, new in edits:
                apply(rel, old, new, originals)
            code = run(command)
        finally:
            for rel, data in originals.items():
                (ROOT / rel).write_text(data, encoding="utf-8")
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
