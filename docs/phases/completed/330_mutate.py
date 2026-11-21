"""Phase 330's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/330_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 388's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it.

Every test it runs uses fixture databases; none reads live.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

SHOP = "src/motodiag/cli/shop.py"
ONB = "src/motodiag/cli/shop_onboard.py"
IMP = "src/motodiag/crm/bike_import.py"
T330 = "tests/test_phase330_onboarding.py"


def pytest(*names: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *[f"{T330}::{n}" for n in names]]


HAPPY = "test_run_the_happy_path_then_again_then_the_rows_it_made"

TERMS_TAIL = (
    '    at_keyboard = click.prompt(\n'
    '        "Which owner is at the keyboard?",\n'
    '        type=click.Choice([m.username for m in waiting] + ["none"]),\n'
    '        default="none",\n'
    '    )\n'
    '    if at_keyboard == "none":\n'
    '        click.echo(f"   Nothing recorded. {SWITCH_SENTENCE}")\n'
    '        return\n'
    '    member = next(m for m in waiting if m.username == at_keyboard)\n'
    '    if click.confirm(\n'
    '        "Have you read both, and do you accept them for yourself?", default=False,\n'
    '    ):\n'
)
EVERY_OWNER_IN_TURN = (
    '    for member in waiting:\n'
    '        if click.confirm(f"{member.username}: do you accept them?", default=False):\n'
    '            record_acceptance(member.user_id, TERMS_VERSION)\n'
    '    at_keyboard = "none"\n'
    '    if False:\n'
)

MUTATIONS = [
    ("M01 the registration line removed from shop.py", [(SHOP,
     "    register_onboard(shop_group)\n", "")],
     pytest("test_onboard_is_reachable_from_the_root_with_its_three_commands")),
    ("M02 the VIN skip removed", [(IMP,
     "        if existing is not None:\n"
     "            report.skipped.append((row.line, existing))\n"
     "            continue\n", "")],
     pytest("test_the_good_file_then_the_same_file_again")),
    ("M03 the problems check removed before the write", [(IMP,
     "    if report.problems:\n        return report\n", "")],
     pytest("test_a_bad_year_and_a_duplicate_vin_write_nothing_and_name_both_lines")),
    ("M04 shop_id dropped from the created customer", [(IMP,
     "email=row.customer_email, shop_id=shop_id,", "email=row.customer_email,")],
     pytest("test_the_good_file_then_the_same_file_again")),
    ("M05 the owner's role written as tech", [(ONB,
     'add_shop_member(int(shop["id"]), user_id, "owner")',
     'add_shop_member(int(shop["id"]), user_id, "tech")')],
     pytest(HAPPY)),
    ("M06 the acceptance recorded before the answer is read", [(ONB,
     '    if click.confirm(\n'
     '        "Have you read both, and do you accept them for yourself?", default=False,\n'
     '    ):\n'
     '        record_acceptance(member.user_id, TERMS_VERSION)\n',
     '    record_acceptance(member.user_id, TERMS_VERSION)\n'
     '    if click.confirm(\n'
     '        "Have you read both, and do you accept them for yourself?", default=False,\n'
     '    ):\n')],
     pytest("test_the_owner_answering_no_writes_no_row")),
    ("M07 the acceptance recorded for each staff user too", [(ONB,
     "        record_acceptance(member.user_id, TERMS_VERSION)\n",
     "        record_acceptance(member.user_id, TERMS_VERSION)\n"
     "        for other in list_shop_members(int(shop['id'])):\n"
     "            record_acceptance(other.user_id, TERMS_VERSION)\n")],
     pytest("test_no_acceptance_is_recorded_for_a_staff_user")),
    ("M08 the keyboard question removed: every owner not yet accepted asked in turn",
     [(ONB, TERMS_TAIL, EVERY_OWNER_IN_TURN)],
     pytest("test_two_owners_as_two_runs")),
    ("M09 status counts an acceptance of any version", [(ONB,
     "if not has_accepted(m.user_id, TERMS_VERSION)",
     'if not any(has_accepted(m.user_id, v) for v in ("0.9", TERMS_VERSION))')],
     pytest("test_an_acceptance_of_an_older_version_leaves_terms_not_yet")),
    ("M10 the terms row's owner-exists condition removed", [(ONB,
     '    if not owners:\n        return False, "no owner yet"\n', "")],
     # On a fresh database the terms row is `not yet` through the no-shop
     # branch first, so the owner-exists condition is held by a shop with
     # no owner (the phase log, the build entry).
     pytest("test_a_shop_with_no_owner_leaves_terms_not_yet_whatever_acceptances_hold")),
    ("M11 the already-done check removed from the staff step", [(ONB,
     "    if done:\n        click.echo(f\"   already done: {detail}\")\n",
     "    if done and name != \"staff\":\n        click.echo(f\"   already done: {detail}\")\n")],
     pytest(HAPPY)),
    ("M12 create_shop called with the owner's user id", [(ONB,
     "zip=zip_code, phone=phone, email=email,",
     "zip=zip_code, phone=phone, email=email, owner_user_id=2,")],
     pytest(HAPPY)),
    ("M13 the walk replaced by start_cmd", [
        (ONB, "from motodiag.cli.workflow import run_cmd\n",
         "from motodiag.cli.workflow import run_cmd, start_cmd\n"),
        (ONB, "ctx.invoke(run_cmd, slug=slug, powertrain=powertrain)",
         "ctx.invoke(start_cmd, slug=slug, powertrain=powertrain, bike=None, "
         "vehicle_id=1, work_order_id=None)")],
     pytest(HAPPY)),
    ("M14 the powertrain Choice widened to POWERTRAINS, the bike's as default", [(ONB,
     '        "Powertrain", type=click.Choice(covers),\n'
     '        default=last if last in covers else covers[0],\n',
     '        "Powertrain", type=click.Choice(["ice", "electric", "hybrid"]),\n'
     '        default=last or "ice",\n')],
     pytest("test_an_ice_only_template_with_an_electric_bike_walks_for_ice")),
    ("M15 status with no --shop routed through _resolve_shop_identifier(None)", [(ONB,
     "shops = list(list_shops()) or [None]",
     "shops = [_resolve_shop_identifier(None, require=False)]")],
     pytest("test_two_shops_and_no_shop_print_two_blocks_in_id_order_and_exit_0")),
    ("M16 the customer match widened to a LIKE on the phone", [(IMP,
     "        if found.get(column) == wanted:\n", "        if True:\n")],
     pytest("test_a_phone_that_contains_another_customers_phone_is_not_a_match")),
    ("M17 the customer match not scoped to the shop", [(IMP,
     "search_customers(wanted, db_path=db_path, shop_id=shop_id)",
     "search_customers(wanted, db_path=db_path)")],
     pytest("test_a_phone_shared_with_another_shops_customer_makes_a_new_customer")),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode


def mutated(name: str, edits: list[tuple[str, str, str]], command: list[str]) -> int:
    originals: dict[str, str] = {}
    try:
        for rel, old, new in edits:
            path = ROOT / rel
            originals.setdefault(rel, path.read_text())
            current = path.read_text()
            assert current.count(old) == 1, \
                f"{name}: the text occurs {current.count(old)} times in {rel}"
            path.write_text(current.replace(old, new))
        return run(command)
    finally:
        for rel, text in originals.items():
            (ROOT / rel).write_text(text)


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    commands: list[list[str]] = []
    for m in chosen:
        if m[2] not in commands:
            commands.append(m[2])
    for command in commands:
        assert run(command) == 0, f"not green before mutating: {command}"
    survivors = []
    for name, edits, command in chosen:
        code = mutated(name, edits, command)
        print(f"{name}: {'red' if code != 0 else 'GREEN (survived)'}", flush=True)
        if code == 0:
            survivors.append(name)
    for command in commands:
        assert run(command) == 0, f"not green after restoring: {command}"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
