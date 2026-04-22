"""Phase 160 — Shop profile + multi-bike intake tests.

Five test classes across ~42 tests:

- :class:`TestMigration025` (5) — schema-version bump to >=25, `shops` +
  `intake_visits` tables + 3 indexes present, UNIQUE(owner, name)
  violation on shops, intake_visits.status CHECK enforced, rollback
  child-first DROP.
- :class:`TestShopRepo` (10) — create + get roundtrip, get_by_name,
  list with open/total intake counts, update whitelist (unknown keys
  dropped), rename dup-name raises, deactivate/reactivate, hours_json
  JSON validation, hours_json non-object rejected, delete cascades
  intake history, delete-then-get None.
- :class:`TestIntakeRepo` (14) — create + get roundtrip with
  denormalized fields, missing shop/customer/vehicle raises ValueError,
  negative/invalid mileage rejected, list filters (shop/status/
  customer/vehicle), since offset parsing, list_open_for_bike,
  update whitelist cannot mutate status, close happy + close already-
  closed raises, cancel vs close distinction, reopen clears closed_at
  + close_reason, reopen already-open is no-op, count_intakes filter
  composition.
- :class:`TestShopCLI` (8, Click CliRunner) — profile init happy +
  duplicate-name idempotent, profile show by name + by id,
  profile list empty + with data + JSON, profile update --set,
  customer add + list.
- :class:`TestIntakeCLI` (6, Click CliRunner) — intake create happy
  path, intake create missing-bike remediation, intake list open +
  JSON, intake show + JSON, intake close + already-closed error,
  intake reopen --yes round-trip.

All tests are SW + SQL only. Zero AI calls, zero network, zero live
tokens.
"""

from __future__ import annotations

import json as _json

import click
import pytest
from click.testing import CliRunner

from motodiag.cli.shop import register_shop
from motodiag.core.database import (
    SCHEMA_VERSION,
    get_connection,
    get_schema_version,
    init_db,
    table_exists,
)
from motodiag.core.migrations import (
    get_migration_by_version,
    rollback_migration,
)
from motodiag.crm import customer_repo
from motodiag.crm.models import Customer
from motodiag.shop import (
    IntakeAlreadyClosedError,
    IntakeNotFoundError,
    ShopNameExistsError,
    ShopNotFoundError,
    cancel_intake,
    close_intake,
    count_intakes,
    create_intake,
    create_shop,
    delete_shop,
    get_intake,
    get_shop,
    get_shop_by_name,
    list_intakes,
    list_open_for_bike,
    list_shops,
    reopen_intake,
    update_intake,
    update_shop,
)
from motodiag.shop.shop_repo import deactivate_shop, reactivate_shop


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_cli():
    """Build a fresh CLI group with only `shop` registered."""

    @click.group()
    def root() -> None:
        """test root"""

    register_shop(root)
    return root


@pytest.fixture
def db(tmp_path):
    """Per-test SQLite DB pre-migrated to the latest schema."""
    path = str(tmp_path / "phase160.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings + CLI env at a temp DB. Mirrors Phase 148/150."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase160_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _add_vehicle(
    db_path: str,
    make: str = "Harley-Davidson",
    model: str = "Sportster 1200",
    year: int = 2010,
) -> int:
    """Insert a vehicles row directly so tests don't import Pydantic models."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES (?, ?, ?, 'none')",
            (make, model, year),
        )
        return cursor.lastrowid


def _add_customer(
    db_path: str, name: str = "Jane Doe",
    phone: str = "555-0100", email: str = "jane@example.com",
) -> int:
    """Insert a customer via the Phase 113 repo."""
    customer = Customer(name=name, phone=phone, email=email)
    return customer_repo.create_customer(customer, db_path=db_path)


# ===========================================================================
# 1. Migration 025
# ===========================================================================


class TestMigration025:
    """Migration 025 bumps schema, creates 2 tables + 3 indexes, rolls back."""

    def test_schema_version_bumped_to_at_least_25(self, db):
        assert SCHEMA_VERSION >= 25
        assert get_schema_version(db) >= 25

    def test_shops_and_intake_visits_tables_created(self, db):
        assert table_exists("shops", db) is True
        assert table_exists("intake_visits", db) is True

    def test_indexes_present(self, db):
        expected = {
            "idx_shops_owner_name",
            "idx_intake_shop_status",
            "idx_intake_vehicle",
            "idx_intake_customer",
        }
        with get_connection(db) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            actual = {r[0] for r in rows}
        assert expected.issubset(actual)

    def test_intake_status_check_rejects_invalid(self, db):
        shop_id = create_shop("test-shop", db_path=db)
        customer_id = _add_customer(db)
        vehicle_id = _add_vehicle(db)
        # Use a direct INSERT to bypass repo validation so we exercise the
        # CHECK constraint itself.
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO intake_visits "
                    "(shop_id, customer_id, vehicle_id, status) "
                    "VALUES (?, ?, ?, 'bogus')",
                    (shop_id, customer_id, vehicle_id),
                )

    def test_rollback_drops_child_first(self, tmp_path):
        """intake_visits (child via shop_id FK) must drop before shops.

        Forward-compat: any later migration (Phase 161+ work_orders, etc.)
        that adds an FK to intake_visits or shops must be rolled back first
        so this test isolates Phase 160's rollback semantics. We use
        rollback_to_version(target=24) to peel everything above 24 in
        reverse-version order.
        """
        from motodiag.core.migrations import rollback_to_version

        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("shops", path) is True
        assert table_exists("intake_visits", path) is True
        # Roll back ALL migrations beyond 24 (which is Phase 157, the last
        # Track F migration). This drops migration 025 (Phase 160) plus
        # any later migrations (026+) that depend on shops/intake_visits.
        rollback_to_version(24, path)
        assert table_exists("intake_visits", path) is False
        assert table_exists("shops", path) is False


# ===========================================================================
# 2. shop_repo CRUD
# ===========================================================================


class TestShopRepo:
    """CRUD + delete cascade + hours_json validation."""

    def test_create_and_get_roundtrip(self, db):
        shop_id = create_shop(
            "main-street-cycles",
            address="123 Main St", city="Austin", state="TX", zip="78701",
            phone="555-0101", email="shop@example.com",
            tax_id="EIN-12-3456789",
            db_path=db,
        )
        assert shop_id > 0
        row = get_shop(shop_id, db_path=db)
        assert row is not None
        assert row["name"] == "main-street-cycles"
        assert row["city"] == "Austin"
        assert row["tax_id"] == "EIN-12-3456789"
        assert row["is_active"] == 1

    def test_get_by_name(self, db):
        create_shop("my-shop", db_path=db)
        row = get_shop_by_name("my-shop", db_path=db)
        assert row is not None
        assert row["name"] == "my-shop"
        assert get_shop_by_name("does-not-exist", db_path=db) is None

    def test_list_shops_with_open_and_total_counts(self, db):
        s1 = create_shop("s1", db_path=db)
        s2 = create_shop("s2", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        i1 = create_intake(s1, c, v, db_path=db)
        create_intake(s1, c, v, db_path=db)
        # Close one of s1's intakes so counts differ.
        close_intake(i1, db_path=db)
        # s2 stays empty.
        _ = s2

        rows = list_shops(db_path=db)
        by_name = {r["name"]: r for r in rows}
        assert by_name["s1"]["open_intake_count"] == 1
        assert by_name["s1"]["total_intake_count"] == 2
        assert by_name["s2"]["open_intake_count"] == 0
        assert by_name["s2"]["total_intake_count"] == 0

    def test_update_whitelist_drops_unknown_keys(self, db):
        shop_id = create_shop("orig", db_path=db)
        changed = update_shop(
            shop_id,
            {"phone": "555-9999", "evil_field": "x"},
            db_path=db,
        )
        assert changed is True
        row = get_shop(shop_id, db_path=db)
        assert row["phone"] == "555-9999"
        assert "evil_field" not in row

    def test_update_rename_duplicate_raises(self, db):
        create_shop("shop-a", db_path=db)
        b_id = create_shop("shop-b", db_path=db)
        with pytest.raises(ShopNameExistsError):
            update_shop(b_id, {"name": "shop-a"}, db_path=db)

    def test_duplicate_create_raises(self, db):
        create_shop("dup", db_path=db)
        with pytest.raises(ShopNameExistsError):
            create_shop("dup", db_path=db)

    def test_deactivate_then_reactivate(self, db):
        shop_id = create_shop("soft", db_path=db)
        deactivate_shop(shop_id, db_path=db)
        assert get_shop(shop_id, db_path=db)["is_active"] == 0
        reactivate_shop(shop_id, db_path=db)
        assert get_shop(shop_id, db_path=db)["is_active"] == 1

    def test_hours_json_validates_parseable_json_object(self, db):
        ok = create_shop(
            "good-hours",
            hours_json='{"mon":"08:00-17:00","tue":"08:00-17:00"}',
            db_path=db,
        )
        assert ok > 0
        with pytest.raises(ValueError):
            create_shop("bad-hours", hours_json="not json at all", db_path=db)

    def test_hours_json_rejects_non_object(self, db):
        with pytest.raises(ValueError):
            create_shop("list-hours", hours_json='[1,2,3]', db_path=db)

    def test_delete_cascades_intake_history(self, db):
        shop_id = create_shop("doomed", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        intake_id = create_intake(shop_id, c, v, db_path=db)
        assert get_intake(intake_id, db_path=db) is not None
        delete_shop(shop_id, db_path=db)
        # Shop gone, intake gone (CASCADE).
        assert get_shop(shop_id, db_path=db) is None
        assert get_intake(intake_id, db_path=db) is None


# ===========================================================================
# 3. intake_repo — CRUD + status lifecycle
# ===========================================================================


class TestIntakeRepo:
    """Intake CRUD + guarded lifecycle + list filters."""

    def _setup_triple(self, db):
        shop_id = create_shop("s", db_path=db)
        customer_id = _add_customer(db)
        vehicle_id = _add_vehicle(db)
        return shop_id, customer_id, vehicle_id

    def test_create_and_get_roundtrip_with_denorm(self, db):
        shop_id, c, v = self._setup_triple(db)
        intake_id = create_intake(
            shop_id=shop_id, customer_id=c, vehicle_id=v,
            reported_problems="won't start", mileage_at_intake=12500,
            db_path=db,
        )
        row = get_intake(intake_id, db_path=db)
        assert row is not None
        assert row["status"] == "open"
        assert row["reported_problems"] == "won't start"
        assert row["mileage_at_intake"] == 12500
        assert row["shop_name"] == "s"
        assert row["customer_name"] == "Jane Doe"
        assert row["vehicle_make"] == "Harley-Davidson"

    def test_create_missing_shop_raises_valueerror(self, db):
        c = _add_customer(db)
        v = _add_vehicle(db)
        with pytest.raises(ValueError, match="shop"):
            create_intake(shop_id=999, customer_id=c, vehicle_id=v, db_path=db)

    def test_create_missing_customer_raises(self, db):
        shop_id = create_shop("s", db_path=db)
        v = _add_vehicle(db)
        with pytest.raises(ValueError, match="customer"):
            create_intake(
                shop_id=shop_id, customer_id=999, vehicle_id=v, db_path=db,
            )

    def test_create_missing_vehicle_raises(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        with pytest.raises(ValueError, match="vehicle"):
            create_intake(
                shop_id=shop_id, customer_id=c, vehicle_id=999, db_path=db,
            )

    def test_negative_mileage_rejected(self, db):
        shop_id, c, v = self._setup_triple(db)
        with pytest.raises(ValueError):
            create_intake(
                shop_id=shop_id, customer_id=c, vehicle_id=v,
                mileage_at_intake=-10, db_path=db,
            )

    def test_list_filters_by_shop_and_status(self, db):
        s1 = create_shop("s1", db_path=db)
        s2 = create_shop("s2", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        i1 = create_intake(s1, c, v, db_path=db)
        i2 = create_intake(s2, c, v, db_path=db)
        close_intake(i1, db_path=db)

        open_rows = list_intakes(status="open", db_path=db)
        assert {r["id"] for r in open_rows} == {i2}

        s1_rows = list_intakes(shop_id=s1, db_path=db)
        assert {r["id"] for r in s1_rows} == {i1}

    def test_list_filters_by_customer_and_vehicle(self, db):
        shop_id = create_shop("s", db_path=db)
        c1 = _add_customer(db, name="A", email="a@ex.com", phone="1")
        c2 = _add_customer(db, name="B", email="b@ex.com", phone="2")
        v1 = _add_vehicle(db)
        v2 = _add_vehicle(db, model="Road Glide")
        i1 = create_intake(shop_id, c1, v1, db_path=db)
        i2 = create_intake(shop_id, c2, v2, db_path=db)

        c1_rows = list_intakes(customer_id=c1, db_path=db)
        assert {r["id"] for r in c1_rows} == {i1}
        v2_rows = list_intakes(vehicle_id=v2, db_path=db)
        assert {r["id"] for r in v2_rows} == {i2}

    def test_list_since_offset_parses(self, db):
        shop_id, c, v = self._setup_triple(db)
        create_intake(shop_id, c, v, db_path=db)
        # 24h lookback should include it; far-future lookback should exclude.
        assert len(list_intakes(since="24h", db_path=db)) == 1
        assert len(list_intakes(
            since="2099-01-01T00:00:00", db_path=db,
        )) == 0

    def test_list_open_for_bike(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v1 = _add_vehicle(db)
        v2 = _add_vehicle(db, model="Road King")
        i1 = create_intake(shop_id, c, v1, db_path=db)
        create_intake(shop_id, c, v2, db_path=db)
        assert [r["id"] for r in list_open_for_bike(v1, db_path=db)] == [i1]

    def test_update_whitelist_cannot_mutate_status(self, db):
        shop_id, c, v = self._setup_triple(db)
        intake_id = create_intake(shop_id, c, v, db_path=db)
        # Attempt to mutate status via update_intake — whitelist drops it.
        update_intake(
            intake_id,
            {"status": "closed", "reported_problems": "new notes"},
            db_path=db,
        )
        row = get_intake(intake_id, db_path=db)
        assert row["status"] == "open"
        assert row["reported_problems"] == "new notes"

    def test_close_and_already_closed_raises(self, db):
        shop_id, c, v = self._setup_triple(db)
        intake_id = create_intake(shop_id, c, v, db_path=db)
        assert close_intake(intake_id, close_reason="completed", db_path=db)
        row = get_intake(intake_id, db_path=db)
        assert row["status"] == "closed"
        assert row["close_reason"] == "completed"
        assert row["closed_at"] is not None
        with pytest.raises(IntakeAlreadyClosedError):
            close_intake(intake_id, db_path=db)

    def test_cancel_distinct_from_close(self, db):
        shop_id, c, v = self._setup_triple(db)
        intake_id = create_intake(shop_id, c, v, db_path=db)
        assert cancel_intake(
            intake_id, reason="customer-withdrew", db_path=db,
        )
        row = get_intake(intake_id, db_path=db)
        assert row["status"] == "cancelled"
        assert row["close_reason"] == "customer-withdrew"

    def test_reopen_clears_closed_fields(self, db):
        shop_id, c, v = self._setup_triple(db)
        intake_id = create_intake(shop_id, c, v, db_path=db)
        close_intake(intake_id, db_path=db)
        assert reopen_intake(intake_id, db_path=db) is True
        row = get_intake(intake_id, db_path=db)
        assert row["status"] == "open"
        assert row["closed_at"] is None
        assert row["close_reason"] is None

    def test_reopen_already_open_is_noop(self, db):
        shop_id, c, v = self._setup_triple(db)
        intake_id = create_intake(shop_id, c, v, db_path=db)
        # Open intake; reopen → no-op → returns False.
        assert reopen_intake(intake_id, db_path=db) is False

    def test_count_intakes_filter_composition(self, db):
        s1 = create_shop("s1", db_path=db)
        s2 = create_shop("s2", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        create_intake(s1, c, v, db_path=db)
        create_intake(s1, c, v, db_path=db)
        create_intake(s2, c, v, db_path=db)
        assert count_intakes(db_path=db) == 3
        assert count_intakes(shop_id=s1, db_path=db) == 2
        assert count_intakes(shop_id=s1, status="open", db_path=db) == 2
        assert count_intakes(shop_id=s1, status="closed", db_path=db) == 0


# ===========================================================================
# 4. CLI — shop profile + customer
# ===========================================================================


class TestShopCLI:
    """Click CliRunner tests for profile + customer subcommands."""

    def test_profile_init_and_idempotent_rerun(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        r1 = runner.invoke(
            root, ["shop", "profile", "init", "--name", "test-shop"],
        )
        assert r1.exit_code == 0, r1.output
        assert "Registered shop" in r1.output

        r2 = runner.invoke(
            root, ["shop", "profile", "init", "--name", "test-shop"],
        )
        # Second run must not double-create; idempotent.
        assert r2.exit_code == 0, r2.output
        assert "already exists" in r2.output
        assert len(list_shops(db_path=cli_db)) == 1

    def test_profile_show_by_name_and_by_id(self, cli_db):
        shop_id = create_shop("alpha", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        by_name = runner.invoke(
            root, ["shop", "profile", "show", "--shop", "alpha"],
        )
        assert by_name.exit_code == 0, by_name.output
        assert "alpha" in by_name.output

        by_id = runner.invoke(
            root, ["shop", "profile", "show", "--shop", str(shop_id)],
        )
        assert by_id.exit_code == 0, by_id.output
        assert "alpha" in by_id.output

    def test_profile_list_empty_and_with_data_and_json(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        empty = runner.invoke(root, ["shop", "profile", "list"])
        assert empty.exit_code == 0
        assert "No shops" in empty.output

        create_shop("s1", db_path=cli_db)
        create_shop("s2", db_path=cli_db)
        filled = runner.invoke(root, ["shop", "profile", "list"])
        assert filled.exit_code == 0
        assert "s1" in filled.output and "s2" in filled.output

        as_json = runner.invoke(
            root, ["shop", "profile", "list", "--json"],
        )
        assert as_json.exit_code == 0
        parsed = _json.loads(as_json.output)
        assert {s["name"] for s in parsed} == {"s1", "s2"}

    def test_profile_update_set(self, cli_db):
        create_shop("u", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "profile", "update", "--shop", "u",
                "--set", "phone=555-1234", "--set", "city=Dallas",
            ],
        )
        assert result.exit_code == 0, result.output
        row = get_shop_by_name("u", db_path=cli_db)
        assert row["phone"] == "555-1234"
        assert row["city"] == "Dallas"

    def test_profile_delete_requires_force(self, cli_db):
        shop_id = create_shop("doomed", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        # Without --force, confirm prompt aborts.
        aborted = runner.invoke(
            root, ["shop", "profile", "delete", "--shop", "doomed"],
            input="n\n",
        )
        assert aborted.exit_code != 0  # click.abort()
        assert get_shop(shop_id, db_path=cli_db) is not None

        forced = runner.invoke(
            root, [
                "shop", "profile", "delete", "--shop", "doomed", "--force",
            ],
        )
        assert forced.exit_code == 0, forced.output
        assert get_shop(shop_id, db_path=cli_db) is None

    def test_customer_add_and_list(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        add = runner.invoke(
            root, [
                "shop", "customer", "add",
                "--name", "Alice Example",
                "--phone", "555-9999",
                "--email", "alice@example.com",
            ],
        )
        assert add.exit_code == 0, add.output
        assert "Alice Example" in add.output

        listed = runner.invoke(root, ["shop", "customer", "list"])
        assert listed.exit_code == 0
        assert "Alice Example" in listed.output

    def test_customer_deactivate_refuses_unassigned(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, ["shop", "customer", "deactivate", "1"],
        )
        assert result.exit_code != 0
        assert "Unassigned" in result.output

    def test_customer_search_no_match(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, ["shop", "customer", "search", "NoSuchNameXyz"],
        )
        assert result.exit_code == 0
        assert "No matches" in result.output


# ===========================================================================
# 5. CLI — intake
# ===========================================================================


class TestIntakeCLI:
    """Click CliRunner tests for the intake subgroup."""

    def test_intake_create_happy_path(self, cli_db):
        shop_id = create_shop("s", db_path=cli_db)
        customer_id = _add_customer(cli_db, name="Bob")
        vehicle_id = _add_vehicle(cli_db, model="Sportster", year=2005)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "intake", "create",
                "--shop", str(shop_id),
                "--customer", str(customer_id),
                "--bike", str(vehicle_id),
                "--mileage", "15000",
                "--notes", "rough idle at stop lights",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Created intake" in result.output
        rows = list_intakes(db_path=cli_db)
        assert len(rows) == 1
        assert rows[0]["mileage_at_intake"] == 15000

    def test_intake_create_missing_bike_remediates(self, cli_db):
        create_shop("s", db_path=cli_db)
        customer_id = _add_customer(cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "intake", "create",
                "--customer", str(customer_id),
                "--bike", "no-such-bike",
            ],
        )
        assert result.exit_code != 0
        assert "Bike not found" in result.output
        assert "motodiag vehicle" in result.output  # remediation hint

    def test_intake_list_open_and_json(self, cli_db):
        shop_id = create_shop("s", db_path=cli_db)
        c = _add_customer(cli_db)
        v = _add_vehicle(cli_db)
        i1 = create_intake(shop_id, c, v, db_path=cli_db)
        i2 = create_intake(shop_id, c, v, db_path=cli_db)
        close_intake(i1, db_path=cli_db)

        runner = CliRunner()
        root = _make_cli()
        open_only = runner.invoke(
            root, ["shop", "intake", "list", "--status", "open"],
        )
        assert open_only.exit_code == 0, open_only.output
        assert str(i2) in open_only.output

        as_json = runner.invoke(
            root, ["shop", "intake", "list", "--status", "all", "--json"],
        )
        assert as_json.exit_code == 0
        parsed = _json.loads(as_json.output)
        assert {r["id"] for r in parsed} == {i1, i2}

    def test_intake_show_and_json(self, cli_db):
        shop_id = create_shop("s", db_path=cli_db)
        c = _add_customer(cli_db)
        v = _add_vehicle(cli_db)
        intake_id = create_intake(shop_id, c, v, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        panel = runner.invoke(
            root, ["shop", "intake", "show", str(intake_id)],
        )
        assert panel.exit_code == 0, panel.output
        assert f"Intake id={intake_id}" in panel.output

        as_json = runner.invoke(
            root, ["shop", "intake", "show", str(intake_id), "--json"],
        )
        assert as_json.exit_code == 0
        parsed = _json.loads(as_json.output)
        assert parsed["id"] == intake_id

    def test_intake_close_and_already_closed_error(self, cli_db):
        shop_id = create_shop("s", db_path=cli_db)
        c = _add_customer(cli_db)
        v = _add_vehicle(cli_db)
        intake_id = create_intake(shop_id, c, v, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()

        closed = runner.invoke(
            root, ["shop", "intake", "close", str(intake_id)],
        )
        assert closed.exit_code == 0, closed.output
        assert "Closed intake" in closed.output

        twice = runner.invoke(
            root, ["shop", "intake", "close", str(intake_id)],
        )
        assert twice.exit_code != 0
        assert "already" in twice.output

    def test_intake_reopen_roundtrip(self, cli_db):
        shop_id = create_shop("s", db_path=cli_db)
        c = _add_customer(cli_db)
        v = _add_vehicle(cli_db)
        intake_id = create_intake(shop_id, c, v, db_path=cli_db)
        close_intake(intake_id, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, ["shop", "intake", "reopen", str(intake_id), "--yes"],
        )
        assert result.exit_code == 0, result.output
        row = get_intake(intake_id, db_path=cli_db)
        assert row["status"] == "open"
