"""Phase 274 — migration 076: the shop's business records.

Eight new tables and one column on `inventory_items`. The migration changes
no existing row: a planted row in every table it touches reads back the same
after the upgrade and after the rollback.
"""

from __future__ import annotations

import pytest

from motodiag.core.database import SCHEMA_VERSION
from motodiag.core.migrations import MIGRATIONS, apply_pending_migrations, rollback_to_version
from support.phase274 import new_db, sql

MIGRATION = 76

NEW_TABLES = {
    "customer_communications", "purchase_orders", "purchase_order_lines",
    "warranty_claims", "mechanic_cost_rates", "work_order_part_costs",
    "shop_expenses", "work_order_quotes",
}


@pytest.fixture
def db(tmp_path):
    return new_db(tmp_path)


def _tables(db_path) -> set[str]:
    return {r[0] for r in sql(db_path, "SELECT name FROM sqlite_master WHERE type = 'table'")}


def _inventory_columns(db_path) -> dict:
    return {r[1]: (r[2], r[3], r[4]) for r in sql(db_path, "PRAGMA table_info(inventory_items)")}


class TestMigration076:
    def test_the_head_is_at_least_076_and_the_last_migration(self):
        assert SCHEMA_VERSION >= MIGRATION
        assert SCHEMA_VERSION == max(m.version for m in MIGRATIONS)

    def test_a_fresh_database_has_every_table_and_the_column(self, db):
        assert NEW_TABLES <= _tables(db)
        assert _inventory_columns(db)["reorder_quantity"] == ("INTEGER", 1, "0")

    def test_the_rollback_removes_exactly_what_the_upgrade_added(self, db):
        rollback_to_version(MIGRATION - 1, db)
        assert not (NEW_TABLES & _tables(db))
        assert "reorder_quantity" not in _inventory_columns(db)
        assert apply_pending_migrations(db) == [
            m.version for m in MIGRATIONS if m.version >= MIGRATION]
        assert NEW_TABLES <= _tables(db)

    def test_existing_rows_are_unchanged_either_way(self, db):
        rollback_to_version(MIGRATION - 1, db)
        sql(db, "INSERT INTO vendors (name, email) VALUES ('Acme Parts', 'a@x.com')")
        sql(db, "INSERT INTO inventory_items (sku, name, quantity_on_hand, reorder_point, "
                "unit_cost, vendor_id) VALUES ('OF-1', 'Oil filter', 3, 5, 4.25, 1)")
        sql(db, "INSERT INTO vehicles (make, model, year) VALUES ('Honda', 'CB500F', 2020)")
        sql(db, "INSERT INTO warranties (vehicle_id, coverage_type, end_date) "
                "VALUES (1, 'powertrain', '2027-01-01')")
        watched = ("vendors", "inventory_items", "warranties", "customers", "work_orders",
                   "customer_notifications", "work_order_parts", "users", "shops")
        before = {t: sql(db, f"SELECT * FROM {t} ORDER BY rowid") for t in watched}

        apply_pending_migrations(db)
        after = {t: sql(db, f"SELECT * FROM {t} ORDER BY rowid") for t in watched}
        # the new column reads its default on the existing item, nothing else moves
        assert after["inventory_items"] == [row + (0,) for row in before["inventory_items"]]
        for t in watched:
            if t != "inventory_items":
                assert after[t] == before[t], t
        assert sql(db, "PRAGMA foreign_key_check") == []

        rollback_to_version(MIGRATION - 1, db)
        for t in watched:
            assert sql(db, f"SELECT * FROM {t} ORDER BY rowid") == before[t], t

    @pytest.mark.parametrize("query", [
        "INSERT INTO customer_communications (customer_id, direction, channel, summary, "
        "occurred_at) VALUES (1, 'sideways', 'phone', 'x', '2026-09-29')",
        "INSERT INTO customer_communications (customer_id, direction, channel, summary, "
        "occurred_at) VALUES (1, 'inbound', 'pigeon', 'x', '2026-09-29')",
        "INSERT INTO customer_communications (customer_id, direction, channel, summary, "
        "occurred_at) VALUES (1, 'inbound', 'phone', '   ', '2026-09-29')",
        "INSERT INTO shop_expenses (shop_id, month, category, amount_cents) "
        "VALUES (1, '2026-9', 'rent', 100)",
        "INSERT INTO mechanic_cost_rates (shop_id, user_id, cost_cents_per_hour, "
        "effective_from) VALUES (1, 1, -5, '2026-09-01')",
        "UPDATE inventory_items SET reorder_quantity = -1",
    ])
    def test_the_checks_refuse_a_bad_value(self, db, query):
        sql(db, "INSERT INTO shops (name) VALUES ('S')")
        sql(db, "INSERT INTO inventory_items (sku, name) VALUES ('X', 'x')")
        with pytest.raises(Exception, match="CHECK constraint failed"):
            sql(db, query)
