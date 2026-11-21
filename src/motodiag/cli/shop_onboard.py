"""CLI: ``motodiag shop onboard {status, run, import-bikes}`` (Phase 330).

A front door onto commands that already exist. ``run`` walks a new shop
through five steps in order (the shop, the owner's login, the staff, the
Terms of Service, the bikes), each skippable and each safe to run again: a
step whose ``status`` row is done prints what is there and asks nothing.
It ends with one checklist walked through on the terminal by
``workflow run``, which saves nothing, and a closing screen.

Everything written goes through the functions the existing commands call
(``create_shop``, ``create_user``, ``add_shop_member``,
``record_acceptance``, ``add_vehicle``, ``create_customer``,
``link_customer_bike``), and only new rows are written.

Readings, recorded in the phase log: the shop's ``owner_user_id`` stays the
default, as ``profile init`` leaves it, and ownership is the ``owner`` role
in ``shop_members``; the terms are accepted only by the one owner who says
they are at the keyboard, for themselves.
"""

from __future__ import annotations

import json as _json
import sqlite3
from typing import Callable, Optional

import click

from motodiag.auth.models import User
from motodiag.auth.terms_acceptance import (
    TERMS_DATE,
    TERMS_VERSION,
    has_accepted,
    record_acceptance,
)
from motodiag.auth.users_repo import create_user, get_user, get_user_by_username
from motodiag.cli.shop import _resolve_shop_identifier
from motodiag.cli.user import _hash_or_fail, _read_password
from motodiag.cli.workflow import run_cmd
from motodiag.core.config import get_settings
from motodiag.core.database import get_connection, get_db_path, init_db
from motodiag.crm.bike_import import (
    COLUMNS,
    ImportReport,
    import_bikes,
    parse_row,
    read_bike_rows,
)
from motodiag.shop import create_shop, get_shop, list_shops
from motodiag.shop.rbac import SHOP_ROLES, add_shop_member, list_shop_members
from motodiag.shop.shop_repo import ShopNameExistsError
from motodiag.workflows import list_templates

Step = tuple[bool, str]

SWITCH_SENTENCE = (
    "Each owner accepts the terms for themselves: here, on a later run, or "
    "in the app. The server asks for it when MOTODIAG_TERMS_REQUIRED is on."
)
STAFF_ROLES = [r for r in SHOP_ROLES if r != "owner"]


# ---------------------------------------------------------------------------
# The five rows: one function each, shared by `status` and `run`
# ---------------------------------------------------------------------------


def _owners(shop: dict) -> list:
    return list_shop_members(int(shop["id"]), role="owner")


def step_shop(shop: Optional[dict]) -> Step:
    if shop is None:
        return False, "no shop registered"
    return True, f"{shop['name']} (id={shop['id']})"


def step_owner(shop: Optional[dict]) -> Step:
    if shop is None:
        return False, "no shop yet"
    named = []
    for member in _owners(shop):
        user = get_user(member.user_id)
        if user is not None and user.get("password_hash"):
            named.append(f"{user['username']} ({user.get('full_name') or '-'})")
    if not named:
        return False, "no owner with a login"
    return True, ", ".join(named)


def step_staff(shop: Optional[dict]) -> Step:
    if shop is None:
        return False, "no shop yet"
    staff = [
        f"{m.username} ({m.role})"
        for m in list_shop_members(int(shop["id"])) if m.role != "owner"
    ]
    if not staff:
        return False, "no staff yet; a one-person shop is complete"
    return True, ", ".join(staff)


def step_terms(shop: Optional[dict]) -> Step:
    if shop is None:
        return False, "no shop yet"
    owners = _owners(shop)
    if not owners:
        return False, "no owner yet"
    waiting = [
        m.username or str(m.user_id) for m in owners
        if not has_accepted(m.user_id, TERMS_VERSION)
    ]
    if waiting:
        return False, (
            f"version {TERMS_VERSION} not yet accepted by: {', '.join(waiting)}"
        )
    return True, f"version {TERMS_VERSION} accepted by every owner"


def _linked_bikes(shop_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(DISTINCT cb.vehicle_id) FROM customer_bikes cb "
            "JOIN customers c ON c.id = cb.customer_id WHERE c.shop_id = ?",
            (shop_id,),
        ).fetchone()
    return int(row[0])


def step_bikes(shop: Optional[dict]) -> Step:
    if shop is None:
        return False, "no shop yet"
    count = _linked_bikes(int(shop["id"]))
    if count == 0:
        return False, "no bike linked to a customer of the shop"
    return True, f"{count} bike(s) linked to the shop's customers"


STEPS: list[tuple[str, Callable[[Optional[dict]], Step]]] = [
    ("shop", step_shop),
    ("owner", step_owner),
    ("staff", step_staff),
    ("terms", step_terms),
    ("bikes", step_bikes),
]


def _word(name: str, done: bool) -> str:
    if done:
        return "done"
    return "none yet" if name == "staff" else "not yet"


def _rows(shop: Optional[dict]) -> dict[str, dict[str, str]]:
    out = {}
    for name, read in STEPS:
        done, detail = read(shop)
        out[name] = {"status": _word(name, done), "detail": detail}
    return out


def _print_block(shop: Optional[dict]) -> None:
    if shop is None:
        click.echo("No shop registered")
    else:
        click.echo(f"Shop #{shop['id']}: {shop['name']}")
    for name, row in _rows(shop).items():
        click.echo(f"  {name:<6} {row['status']:<9} {row['detail']}")


# ---------------------------------------------------------------------------
# The group
# ---------------------------------------------------------------------------


@click.group("onboard")
def onboard() -> None:
    """Onboard a new shop: status, the five-step wizard, the bike import."""


def register_onboard(shop_group: click.Group) -> None:
    """Attach ``onboard`` to the ``shop`` group (Phase 330)."""
    shop_group.add_command(onboard)


@onboard.command("status")
@click.option("--shop", "shop_identifier", default=None,
              help="Shop id or name (default: every shop).")
@click.option("--json", "as_json", is_flag=True, default=False)
def status_cmd(shop_identifier: Optional[str], as_json: bool) -> None:
    """Say which onboarding steps are done, for one shop or every shop."""
    init_db()
    shops: list[Optional[dict]]
    if shop_identifier is not None:
        shops = [_resolve_shop_identifier(shop_identifier)]
    else:
        shops = list(list_shops()) or [None]
    if as_json:
        click.echo(_json.dumps([
            {
                "shop_id": s["id"] if s else None,
                "shop_name": s["name"] if s else None,
                **_rows(s),
            }
            for s in shops
        ], indent=2))
        return
    for shop in shops:
        _print_block(shop)
    click.echo(
        "The first diagnostic walkthrough leaves no record; "
        "`motodiag shop onboard run` offers it."
    )


# ---------------------------------------------------------------------------
# run: the five steps
# ---------------------------------------------------------------------------


def _offer(number: int, name: str, title: str, shop: Optional[dict]) -> bool:
    """Print the step's row; True when it is not done and the owner says yes."""
    done, detail = dict(STEPS)[name](shop)
    click.echo(f"\n{number}. {title}")
    if done:
        click.echo(f"   already done: {detail}")
        return False
    click.echo(f"   {_word(name, done)}: {detail}")
    return click.confirm("Do this step now?", default=True)


def _needs_shop(shop: Optional[dict]) -> bool:
    if shop is None:
        click.echo("   This step needs the shop: do the shop step first.")
        return True
    return False


def _optional(label: str) -> Optional[str]:
    value = click.prompt(label, default="", show_default=False).strip()
    return value or None


def do_shop() -> Optional[dict]:
    while True:
        name = click.prompt("Shop name").strip()
        address, city, state, zip_code, phone, email = (
            _optional(label)
            for label in ("Address", "City", "State", "Zip", "Phone", "Email")
        )
        try:
            shop_id = create_shop(
                name=name, address=address, city=city, state=state,
                zip=zip_code, phone=phone, email=email,
            )
        except (ShopNameExistsError, ValueError) as e:
            click.echo(f"   {e}")
            continue
        click.echo(f"   Registered shop id={shop_id}.")
        return get_shop(shop_id)


def _ask_identity() -> tuple[str, str, Optional[str]]:
    while True:
        username = click.prompt("Username").strip()
        if get_user_by_username(username) is None:
            break
        click.echo(f"   username {username!r} is already taken")
    full_name = click.prompt("Full name").strip()
    return username, full_name, _optional("Email")


def _ask_password() -> str:
    while True:
        try:
            return _hash_or_fail(_read_password(False))
        except click.ClickException as e:
            click.echo(f"   {e.message}")


def _make_login(identity: tuple[str, str, Optional[str]], password_hash: str) -> int:
    username, full_name, email = identity
    try:
        return int(create_user(User(
            username=username, full_name=full_name, email=email,
            password_hash=password_hash,
        )))
    except sqlite3.IntegrityError as e:
        raise click.ClickException(f"username {username!r} is already taken") from e


def do_owner(shop: dict) -> None:
    user_id = _make_login(_ask_identity(), _ask_password())
    add_shop_member(int(shop["id"]), user_id, "owner")
    click.echo(f"   User #{user_id} is the owner of {shop['name']!r}.")


def do_staff(shop: dict) -> None:
    while click.confirm("Add a staff member?", default=False):
        identity = _ask_identity()
        role = click.prompt(
            "Role", type=click.Choice(STAFF_ROLES), default="tech",
        )
        user_id = _make_login(identity, _ask_password())
        add_shop_member(int(shop["id"]), user_id, role)
        click.echo(f"   User #{user_id} ({identity[0]}) is {role} of {shop['name']!r}.")
    click.echo(
        "   Each person logs in from the app (POST /v1/auth/login) and changes "
        "their first password at POST /v1/auth/password after the first login."
    )


def do_terms(shop: dict) -> None:
    owners = _owners(shop)
    if not owners:
        click.echo("   No owner yet: the owner's login step comes first.")
        return
    settings = get_settings()
    click.echo(f"   Terms of Service, version {TERMS_VERSION} ({TERMS_DATE})")
    click.echo(f"   Terms: {settings.terms_url}")
    click.echo(f"   Privacy policy: {settings.privacy_url}")
    accepted = [m for m in owners if has_accepted(m.user_id, TERMS_VERSION)]
    waiting = [m for m in owners if m not in accepted and m.username]
    if accepted:
        click.echo("   Already accepted: " + ", ".join(
            m.username or str(m.user_id) for m in accepted))
    at_keyboard = click.prompt(
        "Which owner is at the keyboard?",
        type=click.Choice([m.username for m in waiting] + ["none"]),
        default="none",
    )
    if at_keyboard == "none":
        click.echo(f"   Nothing recorded. {SWITCH_SENTENCE}")
        return
    member = next(m for m in waiting if m.username == at_keyboard)
    if click.confirm(
        "Have you read both, and do you accept them for yourself?", default=False,
    ):
        record_acceptance(member.user_id, TERMS_VERSION)
        click.echo(f"   Recorded: {at_keyboard} accepted version {TERMS_VERSION}.")
        return
    click.echo(f"   Nothing recorded. {SWITCH_SENTENCE}")


def _print_report(report: ImportReport) -> None:
    for line in report.lines():
        click.echo(f"   {line}")


def _import_file(shop: dict) -> None:
    path = click.prompt("CSV file", type=click.Path(exists=True, dir_okay=False))
    rows, problems = read_bike_rows(path)
    shop_id = int(shop["id"])
    preview = import_bikes(rows, shop_id, problems=problems, dry_run=True)
    if not preview.problems:
        click.echo("   Checked; nothing written yet. Writing would do this:")
    _print_report(preview)
    if preview.problems:
        return
    if click.confirm(f"Write these {len(preview.added)} bikes?", default=False):
        _print_report(import_bikes(rows, shop_id))


def _bike_by_hand(shop: dict) -> None:
    record = {
        "make": click.prompt("Make"),
        "model": click.prompt("Model"),
        "year": str(click.prompt("Year", type=int)),
        "vin": _optional("VIN (blank for none)"),
    }
    powertrain = click.prompt(
        "Powertrain", type=click.Choice(["ice", "electric", "hybrid", "unknown"]),
        default="unknown",
    )
    record["powertrain"] = None if powertrain == "unknown" else powertrain
    record["customer_name"] = _optional("Customer's name (blank for none)")
    if record["customer_name"] is not None:
        record["customer_phone"] = _optional("Customer's phone (blank for none)")
    row, problems = parse_row(1, record)
    rows = [row] if row is not None else []
    _print_report(import_bikes(rows, int(shop["id"]), problems=problems))


def do_bikes(shop: dict) -> None:
    if click.confirm("Import bikes from a CSV file?", default=False):
        _import_file(shop)
    elif click.confirm("Add one bike by hand?", default=False):
        _bike_by_hand(shop)
    click.echo(
        "   Later files: motodiag shop onboard import-bikes FILE "
        f"(columns: {', '.join(COLUMNS)})."
    )


# ---------------------------------------------------------------------------
# run: the walkthrough and the closing screen
# ---------------------------------------------------------------------------


def _last_powertrain(shop: Optional[dict]) -> Optional[str]:
    if shop is None:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT v.powertrain FROM vehicles v "
            "JOIN customer_bikes cb ON cb.vehicle_id = v.id "
            "JOIN customers c ON c.id = cb.customer_id "
            "WHERE c.shop_id = ? ORDER BY v.id DESC LIMIT 1",
            (int(shop["id"]),),
        ).fetchone()
    return row[0] if row else None


def walkthrough(ctx: click.Context, shop: Optional[dict]) -> None:
    templates = list_templates(get_db_path(), is_active=True)
    click.echo("\nThe first diagnostic walkthrough")
    if not templates:
        click.echo("   No active checklist template: there is no walkthrough to offer.")
        return
    if not click.confirm("Walk through a checklist now?", default=False):
        return
    by_slug = {t["slug"]: t for t in templates}
    slugs = list(by_slug)
    slug = click.prompt("Checklist", type=click.Choice(slugs), default=slugs[0])
    covers = list(by_slug[slug]["applicable_powertrains"])
    last = _last_powertrain(shop)
    powertrain = click.prompt(
        "Powertrain", type=click.Choice(covers),
        default=last if last in covers else covers[0],
    )
    ctx.invoke(run_cmd, slug=slug, powertrain=powertrain)


def closing_screen(shop: Optional[dict]) -> None:
    click.echo("\nWhere the shop stands:")
    _print_block(shop)
    click.echo(
        "\nWhat to do next:\n"
        "  motodiag shop customer add          a new customer\n"
        "  motodiag shop intake create         a bike arriving for work\n"
        "  motodiag shop inventory add         parts stock\n"
        "  motodiag user create, then motodiag shop member add\n"
        "                                      another person (another owner: --role owner)\n"
        "  motodiag workflow start <slug> --vehicle-id N\n"
        "                                      a checklist that is saved, on a bike\n"
        "  The app: each person logs in with their username and password."
    )


def _shop_for_run(shop_identifier: Optional[str]) -> Optional[dict]:
    """The one shop the wizard writes to; refuses with several and no --shop."""
    if shop_identifier is not None:
        return _resolve_shop_identifier(shop_identifier)
    return _resolve_shop_identifier(None, require=False)


def _shop_bound_steps(shop: Optional[dict]) -> None:
    for number, name, title, do in (
        (2, "owner", "The owner's login", do_owner),
        (3, "staff", "The staff", do_staff),
        (4, "terms", "The Terms of Service", do_terms),
        (5, "bikes", "The bikes", do_bikes),
    ):
        if _offer(number, name, title, shop) and not _needs_shop(shop):
            assert shop is not None
            do(shop)


@onboard.command("run")
@click.option("--shop", "shop_identifier", default=None,
              help="Shop id or name (required when several shops exist).")
@click.pass_context
def run(ctx: click.Context, shop_identifier: Optional[str]) -> None:
    """Walk a new shop through its five steps, then one checklist."""
    init_db()
    shop = _shop_for_run(shop_identifier)
    if _offer(1, "shop", "The shop", shop):
        shop = do_shop()
    _shop_bound_steps(shop)
    walkthrough(ctx, shop)
    closing_screen(shop)


@onboard.command("import-bikes")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--shop", "shop_identifier", default=None,
              help="Shop id or name (required when several shops exist).")
@click.option("--dry-run", is_flag=True, default=False,
              help="Print what would be written; write nothing.")
def import_bikes_cmd(path: str, shop_identifier: Optional[str], dry_run: bool) -> None:
    """Import a shop's bikes and their customers from a CSV file."""
    init_db()
    shop = _resolve_shop_identifier(shop_identifier)
    assert shop is not None
    rows, problems = read_bike_rows(path)
    report = import_bikes(rows, int(shop["id"]), problems=problems, dry_run=dry_run)
    if dry_run and not report.problems:
        click.echo("Dry run: nothing was written. The import would do this:")
    _print_report(report)
    if report.problems:
        raise SystemExit(1)
