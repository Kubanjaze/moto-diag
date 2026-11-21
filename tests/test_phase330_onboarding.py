"""Phase 330: `motodiag shop onboard {status, run, import-bikes}`.

Every test runs on a fresh migrated database under MOTODIAG_DB_PATH (the
`cli_db` form of tests/test_phase160_shop.py); none reads live. The CLI
under test is the real root, `motodiag.cli.main.cli`, because the finish
lines read `user`, `garage` and `workflow` as well as `shop`.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from motodiag.auth.models import User
from motodiag.auth.terms_acceptance import TERMS_VERSION, has_accepted, record_acceptance
from motodiag.auth.users_repo import create_user, get_user_by_username
from motodiag.cli.main import cli
from motodiag.core.database import init_db
from motodiag.crm.bike_import import import_bikes, read_bike_rows
from motodiag.crm.customer_repo import create_customer
from motodiag.crm.models import Customer
from motodiag.shop import create_shop
from motodiag.shop.rbac import add_shop_member

REPO_ROOT = Path(__file__).resolve().parent.parent

TABLES = ("shops", "users", "shop_members", "terms_acceptances", "vehicles",
          "customers", "customer_bikes", "workflow_runs")

GOOD_CSV = (
    "make,model,year,vin,powertrain,customer_name,customer_phone\n"
    "Honda,CBR600RR,2009,VIN001,ice,Marcus Webb,512-555-0188\n"
    "Zero,SR/F,2021,VIN002,electric,Marcus Webb,512-555-0188\n"
    "Harley-Davidson,Sportster 1200,2001,VIN003,ice,Dana Cole,512-555-0199\n"
)

#: brake_service_v1, the first active template on a fresh database, has 7 items.
SEVEN_PASSES = "p\np\np\np\np\np\np\n"


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """A fresh migrated database for the CLI; the Phase 160 fixture's form."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase330_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def invoke(args: list[str], input: str | None = None):
    return CliRunner().invoke(cli, args, input=input, catch_exceptions=False)


def counts(db: str) -> dict[str, int]:
    conn = sqlite3.connect(db)
    try:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
    finally:
        conn.close()


def sql(db: str, query: str, params: tuple = ()) -> list[tuple]:
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(query, params).fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


def write_csv(tmp_path: Path, text: str, name: str = "bikes.csv") -> str:
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def status_json(args: list[str] | None = None) -> list[dict]:
    result = invoke(["shop", "onboard", "status", "--json", *(args or [])])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def owner(db: str, shop_id: int, username: str) -> int:
    uid = int(create_user(User(username=username, full_name=username.title(),
                               password_hash="x" * 20), db))
    add_shop_member(shop_id, uid, "owner", db_path=db)
    return uid


def happy_input(csv_path: str) -> str:
    """The first input string: all five steps, then the walkthrough."""
    return (
        # 1. the shop: yes, name, then address, city, state, zip, phone, email
        "y\nBandit Hero Cycles\n\nAustin\nTX\n\n\n\n"
        # 2. the owner: yes, username, full name, email, password twice
        "y\ntess\nTess Ramirez\n\nownerpass1\nownerpass1\n"
        # 3. the staff: yes; two people, then no more
        "y\n"
        "y\nmo\nMo Diaz\n\ntech\ntechpass12\ntechpass12\n"
        "y\nsam\nSam Lee\n\nservice_writer\nwriterpass1\nwriterpass1\n"
        "n\n"
        # 4. the terms: yes, tess at the keyboard, tess accepts
        "y\ntess\ny\n"
        # 5. the bikes: yes, from a file, its path, write them
        f"y\ny\n{csv_path}\ny\n"
        # the walkthrough: yes, the default slug, the default powertrain
        "y\n\n\n" + SEVEN_PASSES
    )


# ---------------------------------------------------------------------------
# reachability
# ---------------------------------------------------------------------------


def test_onboard_is_reachable_from_the_root_with_its_three_commands():
    shop = cli.commands["shop"]
    assert "onboard" in shop.commands
    assert set(shop.commands["onboard"].commands) == {"status", "run", "import-bikes"}
    result = invoke(["shop", "onboard", "--help"])
    for name in ("status", "run", "import-bikes"):
        assert name in result.output


def test_shop_py_carries_the_import_and_the_call_once_each():
    text = (REPO_ROOT / "src" / "motodiag" / "cli" / "shop.py").read_text()
    assert text.count("from motodiag.cli.shop_onboard import register_onboard") == 1
    assert text.count("register_onboard(shop_group)") == 1
    assert text.count("register_inventory(shop_group)") == 1


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def test_status_on_a_fresh_database_is_five_not_yet_and_exits_0(cli_db):
    result = invoke(["shop", "onboard", "status"])
    assert result.exit_code == 0
    assert "No shop registered" in result.output
    [block] = status_json()
    assert block["shop_id"] is None
    assert {k: block[k]["status"] for k in ("shop", "owner", "staff", "terms", "bikes")} == {
        "shop": "not yet", "owner": "not yet", "staff": "none yet",
        "terms": "not yet", "bikes": "not yet",
    }
    assert "walkthrough leaves no record" in result.output


def test_each_row_turns_after_its_step(cli_db, tmp_path):
    def statuses() -> dict[str, str]:
        [b] = status_json()
        return {k: b[k]["status"] for k in ("shop", "owner", "staff", "terms", "bikes")}

    shop_id = create_shop(name="Bandit", db_path=cli_db)
    assert statuses()["shop"] == "done"
    assert statuses()["owner"] == "not yet"
    uid = owner(cli_db, shop_id, "tess")
    assert statuses()["owner"] == "done"
    assert statuses()["terms"] == "not yet"
    staff = int(create_user(User(username="mo", password_hash="y" * 20), cli_db))
    add_shop_member(shop_id, staff, "tech", db_path=cli_db)
    assert statuses()["staff"] == "done"
    record_acceptance(uid, TERMS_VERSION, cli_db)
    assert statuses()["terms"] == "done"
    rows, problems = read_bike_rows(write_csv(tmp_path, GOOD_CSV))
    import_bikes(rows, shop_id, cli_db, problems=problems)
    assert statuses() == dict.fromkeys(("shop", "owner", "staff", "terms", "bikes"), "done")


def test_an_acceptance_of_an_older_version_leaves_terms_not_yet(cli_db):
    shop_id = create_shop(name="Bandit", db_path=cli_db)
    uid = owner(cli_db, shop_id, "tess")
    record_acceptance(uid, "0.9", cli_db)
    [b] = status_json()
    assert b["terms"]["status"] == "not yet"


def test_a_shop_with_no_owner_leaves_terms_not_yet_whatever_acceptances_hold(cli_db):
    shop_id = create_shop(name="Bandit", db_path=cli_db)
    tech = int(create_user(User(username="mo", password_hash="y" * 20), cli_db))
    add_shop_member(shop_id, tech, "tech", db_path=cli_db)
    record_acceptance(tech, TERMS_VERSION, cli_db)
    record_acceptance(1, TERMS_VERSION, cli_db)
    [b] = status_json()
    assert b["terms"]["status"] == "not yet"
    assert b["staff"]["status"] == "done"


def test_two_shops_and_no_shop_print_two_blocks_in_id_order_and_exit_0(cli_db):
    # Named so that name order (Alpha first) is the reverse of id order.
    create_shop(name="Zulu Cycles", db_path=cli_db)
    create_shop(name="Alpha Moto", db_path=cli_db)
    result = invoke(["shop", "onboard", "status"])
    assert result.exit_code == 0
    assert "Multiple shops exist" not in result.output
    first = result.output.index("Shop #1: Zulu Cycles")
    second = result.output.index("Shop #2: Alpha Moto")
    assert first < second
    blocks = status_json()
    assert [b["shop_id"] for b in blocks] == [1, 2]
    assert [b["shop_name"] for b in blocks] == ["Zulu Cycles", "Alpha Moto"]


def test_status_with_shop_by_name_prints_that_block_alone(cli_db):
    create_shop(name="Alpha Moto", db_path=cli_db)
    create_shop(name="Bravo Cycles", db_path=cli_db)
    result = invoke(["shop", "onboard", "status", "--shop", "Bravo Cycles"])
    assert result.exit_code == 0
    assert "Bravo Cycles" in result.output
    assert "Alpha Moto" not in result.output
    assert [b["shop_name"] for b in status_json(["--shop", "Bravo Cycles"])] == ["Bravo Cycles"]


# ---------------------------------------------------------------------------
# several shops: the writing commands refuse
# ---------------------------------------------------------------------------


def test_run_and_import_with_several_shops_and_no_shop_refuse(cli_db, tmp_path):
    create_shop(name="Alpha Moto", db_path=cli_db)
    create_shop(name="Bravo Cycles", db_path=cli_db)
    before = counts(cli_db)
    for args, text in (
        (["shop", "onboard", "run"], "y\n" * 30),
        (["shop", "onboard", "import-bikes", write_csv(tmp_path, GOOD_CSV)], None),
    ):
        result = invoke(args, input=text)
        assert result.exit_code == 1
        assert ("Multiple shops exist (Alpha Moto, Bravo Cycles); "
                "pass --shop NAME or --shop ID.") in result.output
    assert counts(cli_db) == before


# ---------------------------------------------------------------------------
# run: the three input strings
# ---------------------------------------------------------------------------


def test_run_the_happy_path_then_again_then_the_rows_it_made(cli_db, tmp_path):
    csv_path = write_csv(tmp_path, GOOD_CSV)
    result = invoke(["shop", "onboard", "run"], input=happy_input(csv_path))
    assert result.exit_code == 0, result.output
    assert "Summary · brake_service_v1 · for ice: 7 passed" in result.output
    assert "Nothing was saved" in result.output
    closing = result.output[result.output.index("Where the shop stands:"):]
    assert closing.count(" done ") == 5
    assert "ownerpass1" not in result.output
    after_first = counts(cli_db)
    assert after_first["workflow_runs"] == 0

    # reading 3's control: the existing no-argument path still finds the shop
    shown = invoke(["shop", "profile", "show"])
    assert shown.exit_code == 0 and "Bandit Hero Cycles" in shown.output
    assert sql(cli_db, "SELECT owner_user_id FROM shops") == [(1,)]

    users = json.loads(invoke(["user", "list", "--json"]).output)
    by_name = {u["username"]: u for u in users}
    assert all(by_name[n]["password_set"] for n in ("tess", "mo", "sam"))
    listing = invoke(["user", "list"]).output
    for (hashed,) in sql(cli_db, "SELECT password_hash FROM users WHERE password_hash IS NOT NULL"):
        assert hashed not in listing
    members = json.loads(invoke(["shop", "member", "list", "--json"]).output)
    assert sorted(m["role"] for m in members) == ["owner", "service_writer", "tech"]

    ids = {n: get_user_by_username(n)["id"] for n in ("tess", "mo", "sam")}
    assert has_accepted(ids["tess"], TERMS_VERSION)
    assert not has_accepted(ids["mo"], TERMS_VERSION)
    assert not has_accepted(ids["sam"], TERMS_VERSION)
    assert sql(cli_db, "SELECT COUNT(*) FROM terms_acceptances") == [(1,)]

    garage = invoke(["garage", "list"]).output
    for model in ("CBR600RR", "SR/F", "Sportster 1200"):
        assert model in garage
    customers = sql(cli_db, "SELECT name, shop_id FROM customers WHERE id > 1 ORDER BY id")
    assert customers == [("Marcus Webb", 1), ("Dana Cole", 1)]
    assert "Marcus Webb" in invoke(["shop", "customer", "list"]).output
    assert sql(cli_db, "SELECT COUNT(*) FROM customer_bikes") == [(3,)]
    assert "CBR600RR" in invoke(["shop", "customer", "bikes", "2"]).output

    # run, again: the second input string, one answer
    again = invoke(["shop", "onboard", "run"], input="n\n")
    assert again.exit_code == 0, again.output
    assert "Do this step now?" not in again.output
    assert again.output.count("already done:") == 5
    assert "Walk through a checklist now?" in again.output
    assert "Summary" not in again.output
    assert counts(cli_db) == after_first


def test_run_declined_writes_nothing(cli_db):
    before = counts(cli_db)
    # the third input string: no to each of the five steps, no to the walkthrough
    result = invoke(["shop", "onboard", "run"], input="n\nn\nn\nn\nn\nn\n")
    assert result.exit_code == 0, result.output
    assert result.output.count("Do this step now?") == 5
    assert "Summary" not in result.output
    assert counts(cli_db) == before
    assert counts(cli_db)["shops"] == 0


# ---------------------------------------------------------------------------
# run: the refusals that ask again
# ---------------------------------------------------------------------------


def test_a_short_password_and_a_taken_username_are_asked_again(cli_db):
    create_shop(name="Bandit", db_path=cli_db)
    create_user(User(username="taken", password_hash=None), cli_db)
    text = (
        "y\ntaken\ntess\nTess Ramirez\n\nshort\nshort\nownerpass1\nownerpass1\n"
        "n\nn\nn\nn\n"
    )
    result = invoke(["shop", "onboard", "run"], input=text)
    assert result.exit_code == 0, result.output
    assert "username 'taken' is already taken" in result.output
    assert "a password needs at least 8 characters" in result.output
    [b] = status_json()
    assert b["owner"]["status"] == "done"
    assert "tess" in b["owner"]["detail"]


def test_with_an_owner_and_staff_present_their_steps_ask_nothing(cli_db):
    shop_id = create_shop(name="Bandit", db_path=cli_db)
    owner(cli_db, shop_id, "tess")
    tech = int(create_user(User(username="mo", password_hash="y" * 20), cli_db))
    add_shop_member(shop_id, tech, "tech", db_path=cli_db)
    result = invoke(["shop", "onboard", "run"], input="n\nn\nn\n")
    assert result.exit_code == 0, result.output
    assert result.output.count("Do this step now?") == 2  # the terms and the bikes
    assert "Username:" not in result.output
    assert "Add a staff member?" not in result.output


# ---------------------------------------------------------------------------
# the terms
# ---------------------------------------------------------------------------


@pytest.fixture
def owned_shop(cli_db):
    shop_id = create_shop(name="Bandit", db_path=cli_db)
    return shop_id, owner(cli_db, shop_id, "tess")


def test_none_at_the_keyboard_writes_no_row(cli_db, owned_shop):
    result = invoke(["shop", "onboard", "run"], input="n\ny\n\nn\nn\n")
    assert "Which owner is at the keyboard? (tess, none) [none]" in result.output
    assert "MOTODIAG_TERMS_REQUIRED is on" in result.output
    assert "Have you read both" not in result.output
    assert counts(cli_db)["terms_acceptances"] == 0


def test_the_owner_answering_no_writes_no_row(cli_db, owned_shop):
    result = invoke(["shop", "onboard", "run"], input="n\ny\ntess\nn\nn\nn\n")
    assert "Have you read both, and do you accept them for yourself?" in result.output
    assert "MOTODIAG_TERMS_REQUIRED is on" in result.output
    assert counts(cli_db)["terms_acceptances"] == 0
    assert not has_accepted(owned_shop[1], TERMS_VERSION)


def test_the_terms_step_shows_the_version_and_both_addresses(cli_db, owned_shop):
    result = invoke(["shop", "onboard", "run"], input="n\ny\ntess\ny\nn\nn\n")
    assert f"version {TERMS_VERSION}" in result.output
    assert "https://getmekno.com/terms/" in result.output
    assert "https://getmekno.com/privacy/" in result.output
    assert has_accepted(owned_shop[1], TERMS_VERSION)
    later = invoke(["shop", "onboard", "run"], input="n\nn\nn\n")
    assert "Which owner is at the keyboard?" not in later.output
    assert counts(cli_db)["terms_acceptances"] == 1


def test_no_acceptance_is_recorded_for_a_staff_user(cli_db, owned_shop):
    shop_id, _ = owned_shop
    tech = int(create_user(User(username="mo", password_hash="y" * 20), cli_db))
    add_shop_member(shop_id, tech, "tech", db_path=cli_db)
    invoke(["shop", "onboard", "run"], input="y\ntess\ny\nn\nn\n")
    assert not has_accepted(tech, TERMS_VERSION)
    assert sql(cli_db, "SELECT user_id FROM terms_acceptances") == [(owned_shop[1],)]


def test_two_owners_as_two_runs(cli_db):
    shop_id = create_shop(name="Bandit", db_path=cli_db)
    alice = owner(cli_db, shop_id, "alice")
    bob = owner(cli_db, shop_id, "bob")

    first = invoke(["shop", "onboard", "run"], input="n\ny\nalice\ny\nn\nn\n")
    assert "(alice, bob, none) [none]" in first.output
    assert first.output.count("Which owner is at the keyboard?") == 1
    assert first.output.count("Have you read both") == 1
    assert has_accepted(alice, TERMS_VERSION) and not has_accepted(bob, TERMS_VERSION)
    assert counts(cli_db)["terms_acceptances"] == 1
    assert status_json()[0]["terms"]["status"] == "not yet"

    second = invoke(["shop", "onboard", "run"], input="n\ny\nbob\ny\nn\nn\n")
    assert "(bob, none) [none]" in second.output
    assert "alice, bob" not in second.output.split("Which owner")[1].split("\n")[0]
    assert second.output.count("Have you read both") == 1
    assert has_accepted(bob, TERMS_VERSION)
    assert status_json()[0]["terms"]["status"] == "done"


# ---------------------------------------------------------------------------
# the walkthrough
# ---------------------------------------------------------------------------


def test_every_template_retired_means_no_walkthrough_prompt(cli_db):
    sql(cli_db, "UPDATE workflow_templates SET is_active = 0")
    result = invoke(["shop", "onboard", "run"], input="n\nn\nn\nn\nn\n")
    assert result.exit_code == 0
    assert "No active checklist template" in result.output
    assert "Walk through a checklist now?" not in result.output
    assert "Where the shop stands:" in result.output


def test_no_at_the_walkthrough_runs_no_walk(cli_db):
    result = invoke(["shop", "onboard", "run"], input="n\nn\nn\nn\nn\nn\n")
    assert "Walk through a checklist now? [y/N]" in result.output
    assert "Summary" not in result.output
    assert "Checklist (" not in result.output


def test_an_ice_only_template_with_an_electric_bike_walks_for_ice(cli_db, tmp_path):
    sql(cli_db, "UPDATE workflow_templates SET applicable_powertrains = '[\"ice\"]' "
                "WHERE slug = 'brake_service_v1'")
    shop_id = create_shop(name="Bandit", db_path=cli_db)
    owner(cli_db, shop_id, "tess")
    csv_path = write_csv(tmp_path, "make,model,year,vin,powertrain,customer_name\n"
                                   "Zero,SR/F,2021,VIN9,electric,Dana Cole\n")
    text = f"n\nn\ny\ny\n{csv_path}\ny\n" + "y\n\n\n" + SEVEN_PASSES
    before = counts(cli_db)["workflow_runs"]
    result = invoke(["shop", "onboard", "run"], input=text)
    assert result.exit_code == 0, result.output
    assert "Powertrain (ice) [ice]:" in result.output
    assert "Summary · brake_service_v1 · for ice" in result.output
    assert "Where the shop stands:" in result.output
    assert counts(cli_db)["workflow_runs"] == before


def test_the_walkthrough_default_is_the_last_bikes_powertrain_when_covered(cli_db, tmp_path):
    shop_id = create_shop(name="Bandit", db_path=cli_db)
    owner(cli_db, shop_id, "tess")
    csv_path = write_csv(tmp_path, "make,model,year,vin,powertrain,customer_name\n"
                                   "Zero,SR/F,2021,VIN9,electric,Dana Cole\n")
    text = f"n\nn\ny\ny\n{csv_path}\ny\n" + "y\n\n\n" + SEVEN_PASSES
    result = invoke(["shop", "onboard", "run"], input=text)
    assert "Powertrain (ice, electric, hybrid) [electric]:" in result.output
    assert "for electric" in result.output


# ---------------------------------------------------------------------------
# the import, the module alone
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase330.db")
    init_db(path)
    return path


def run_import(db: str, shop_id: int, csv_path: str, dry_run: bool = False):
    rows, problems = read_bike_rows(csv_path)
    return import_bikes(rows, shop_id, db, problems=problems, dry_run=dry_run)


def test_the_good_file_then_the_same_file_again(db, tmp_path):
    shop_id = create_shop(name="Bandit", db_path=db)
    path = write_csv(tmp_path, GOOD_CSV)
    report = run_import(db, shop_id, path)
    assert (len(report.added), len(report.customers_made), len(report.customers_matched),
            len(report.links)) == (3, 2, 1, 3)
    assert sql(db, "SELECT shop_id FROM customers WHERE id > 1") == [(shop_id,), (shop_id,)]
    before = counts(db)
    again = run_import(db, shop_id, path)
    assert len(again.added) == 0 and len(again.skipped) == 3
    assert "already in the garage (bike #1)" in "\n".join(again.lines())
    assert counts(db) == before


def test_a_bad_year_and_a_duplicate_vin_write_nothing_and_name_both_lines(db, tmp_path):
    shop_id = create_shop(name="Bandit", db_path=db)
    path = write_csv(tmp_path, "make,model,year,vin\nHonda,CB500F,2015,A1\n"
                               "Honda,CB750,1965,A2\nHonda,CB1000R,2019,A1\n")
    before = counts(db)
    report = run_import(db, shop_id, path)
    assert any(p.startswith("line 3:") and "year" in p for p in report.problems)
    assert any(p.startswith("line 4:") and "A1" in p for p in report.problems)
    assert not report.written
    assert counts(db) == before


@pytest.mark.parametrize("text, needle", [
    ("make,model,year,colour\nHonda,CB500F,2015,red\n", "unknown column 'colour'"),
    ("make,model\nHonda,CB500F\n", "missing required column 'year'"),
    ("make,model,year,customer_phone\nHonda,CB500F,2015,555\n", "with no customer_name"),
    ("make,model,year,powertrain\nHonda,CB500F,2015,diesel\n", "line 2: powertrain"),
])
def test_a_file_problem_is_named(db, tmp_path, text, needle):
    rows, problems = read_bike_rows(write_csv(tmp_path, text))
    assert any(needle in p for p in problems), problems


def test_a_phone_shared_with_another_shops_customer_makes_a_new_customer(db, tmp_path):
    other = create_shop(name="Other", db_path=db)
    mine = create_shop(name="Mine", db_path=db)
    theirs = create_customer(Customer(name="Marcus Webb", phone="512-555-0188",
                                      shop_id=other), db)
    report = run_import(db, mine, write_csv(tmp_path, GOOD_CSV))
    assert len(report.customers_made) == 2
    made = sql(db, "SELECT id, shop_id FROM customers WHERE phone = '512-555-0188' ORDER BY id")
    assert made[0] == (theirs, other) and made[1][1] == mine
    assert sql(db, "SELECT COUNT(*) FROM customer_bikes WHERE customer_id = ?", (theirs,)) == [(0,)]


def test_a_phone_that_contains_another_customers_phone_is_not_a_match(db, tmp_path):
    shop_id = create_shop(name="Mine", db_path=db)
    create_customer(Customer(name="Marcus Webb", phone="512-555-01889", shop_id=shop_id), db)
    report = run_import(db, shop_id, write_csv(tmp_path, GOOD_CSV))
    assert len(report.customers_made) == 2


def test_a_row_without_a_vin_is_added_on_every_import_and_counted(db, tmp_path):
    shop_id = create_shop(name="Bandit", db_path=db)
    path = write_csv(tmp_path, "make,model,year\nHonda,CB500F,2015\n")
    first = run_import(db, shop_id, path)
    second = run_import(db, shop_id, path)
    assert first.without_vin == [2] and second.without_vin == [2]
    assert sql(db, "SELECT COUNT(*) FROM vehicles") == [(2,)]
    assert "Rows without a VIN: 1" in "\n".join(second.lines())


# ---------------------------------------------------------------------------
# the import, the command
# ---------------------------------------------------------------------------


def test_dry_run_prints_the_report_and_changes_no_count(cli_db, tmp_path):
    create_shop(name="Bandit", db_path=cli_db)
    before = counts(cli_db)
    result = invoke(["shop", "onboard", "import-bikes", write_csv(tmp_path, GOOD_CSV),
                     "--dry-run"])
    assert result.exit_code == 0
    assert "Bikes added: 3" in result.output and "Customers made: 2" in result.output
    assert counts(cli_db) == before
    written = invoke(["shop", "onboard", "import-bikes", write_csv(tmp_path, GOOD_CSV)])
    assert written.exit_code == 0 and counts(cli_db)["vehicles"] == 3


@pytest.mark.parametrize("dry", [False, True])
def test_a_file_with_problems_exits_1_and_writes_nothing(cli_db, tmp_path, dry):
    create_shop(name="Bandit", db_path=cli_db)
    path = write_csv(tmp_path, "make,model,year\nHonda,CB500F,2015\nHonda,CB750,1965\n")
    before = counts(cli_db)
    result = invoke(["shop", "onboard", "import-bikes", path, *(["--dry-run"] if dry else [])])
    assert result.exit_code == 1
    assert "line 3" in result.output
    assert counts(cli_db) == before


def test_the_hand_path_makes_the_same_rows_as_a_one_row_file(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    query = ("SELECT v.make, v.model, v.year, v.vin, v.powertrain, c.name, c.phone, "
             "c.shop_id, cb.relationship FROM vehicles v "
             "JOIN customer_bikes cb ON cb.vehicle_id = v.id "
             "JOIN customers c ON c.id = cb.customer_id")
    made = []
    for name in ("by_hand", "by_file"):
        path = str(tmp_path / f"{name}.db")
        init_db(path)
        monkeypatch.setenv("MOTODIAG_DB_PATH", path)
        monkeypatch.setenv("COLUMNS", "240")
        reset_settings()
        create_shop(name="Bandit", db_path=path)
        if name == "by_hand":
            text = ("n\nn\nn\ny\nn\ny\nHonda\nCB500F\n2015\nVIN7\nice\n"
                    "Dana Cole\n512-555-0199\nn\n")
            result = invoke(["shop", "onboard", "run"], input=text)
        else:
            csv_path = write_csv(tmp_path, "make,model,year,vin,powertrain,customer_name,"
                                           "customer_phone\nHonda,CB500F,2015,VIN7,ice,"
                                           "Dana Cole,512-555-0199\n", "one.csv")
            result = invoke(["shop", "onboard", "import-bikes", csv_path])
        assert result.exit_code == 0, result.output
        made.append(sql(path, query))
    reset_settings()
    assert made[0] == made[1] == [("Honda", "CB500F", 2015, "VIN7", "ice", "Dana Cole",
                                   "512-555-0199", 1, "owner")]
