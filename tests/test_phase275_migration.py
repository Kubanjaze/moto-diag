"""Phase 275 — migration 077: appointments at a shop, and the accounting export records.

Two columns on `appointments`, an index and three tables. The migration
changes no existing row: a planted row in every table it touches reads back
the same after the upgrade and after the rollback.
"""

from __future__ import annotations

import sqlite3

import pytest

from motodiag.core.database import SCHEMA_VERSION
from motodiag.core.migrations import MIGRATIONS, apply_pending_migrations, rollback_to_version
from support.phase274 import new_db, sql

MIGRATION = 77

NEW_TABLES = {"accounting_accounts", "accounting_exports", "accounting_export_invoices"}


@pytest.fixture
def db(tmp_path):
    return new_db(tmp_path)


def _tables(db_path) -> set[str]:
    return {r[0] for r in sql(db_path, "SELECT name FROM sqlite_master WHERE type = 'table'")}


def _appointment_columns(db_path) -> list[str]:
    return [r[1] for r in sql(db_path, "PRAGMA table_info(appointments)")]


def _indexes(db_path) -> set[str]:
    return {r[0] for r in sql(db_path, "SELECT name FROM sqlite_master WHERE type = 'index'")}


class TestMigration077:
    def test_the_head_is_at_least_077_and_the_last_migration(self):
        assert SCHEMA_VERSION >= MIGRATION
        assert SCHEMA_VERSION == max(m.version for m in MIGRATIONS)

    def test_a_fresh_database_has_the_columns_the_index_and_the_tables(self, db):
        assert NEW_TABLES <= _tables(db)
        assert _appointment_columns(db)[-2:] == ["shop_id", "work_order_id"]
        assert "idx_appointments_shop_start" in _indexes(db)

    def test_the_rollback_removes_exactly_what_the_upgrade_added(self, db):
        rollback_to_version(MIGRATION - 1, db)
        assert not (NEW_TABLES & _tables(db))
        assert "shop_id" not in _appointment_columns(db)
        assert "work_order_id" not in _appointment_columns(db)
        assert "idx_appointments_shop_start" not in _indexes(db)
        assert apply_pending_migrations(db) == [
            m.version for m in MIGRATIONS if m.version >= MIGRATION]
        assert NEW_TABLES <= _tables(db)

    def test_existing_rows_are_unchanged_either_way(self, db):
        rollback_to_version(MIGRATION - 1, db)
        sql(db, "INSERT INTO shops (name) VALUES ('Planted Shop')")
        sql(db, "INSERT INTO customers (name, shop_id) VALUES ('Dana Reyes', 1)")
        sql(db, "INSERT INTO vehicles (make, model, year) VALUES ('Honda', 'CB500F', 2020)")
        sql(db, "INSERT INTO appointments (customer_id, vehicle_id, scheduled_start, "
                "scheduled_end) VALUES (2, 1, '2026-10-01T09:00', '2026-10-01T10:00')")
        sql(db, "INSERT INTO invoices (customer_id, invoice_number, total) "
                "VALUES (2, 'INV-PLANT', 12.5)")
        watched = ("shops", "customers", "vehicles", "invoices", "invoice_line_items",
                   "work_orders", "bay_schedule_slots", "customer_communications")
        before = {t: sql(db, f"SELECT * FROM {t} ORDER BY rowid") for t in watched}
        appts_before = sql(db, "SELECT * FROM appointments ORDER BY rowid")

        apply_pending_migrations(db)
        for t in watched:
            # Later migrations may add columns (078 adds ten to invoices);
            # the planted rows' own columns must read back unchanged.
            after = sql(db, f"SELECT * FROM {t} ORDER BY rowid")
            assert [row[:len(b)] for row, b in zip(after, before[t])] == before[t], t
            assert len(after) == len(before[t]), t
        # the two new columns read NULL on the existing appointment, nothing else moves
        assert sql(db, "SELECT * FROM appointments ORDER BY rowid") == [
            row + (None, None) for row in appts_before]
        assert sql(db, "PRAGMA foreign_key_check") == []

        rollback_to_version(MIGRATION - 1, db)
        for t in watched:
            assert sql(db, f"SELECT * FROM {t} ORDER BY rowid") == before[t], t
        assert sql(db, "SELECT * FROM appointments ORDER BY rowid") == appts_before

    @pytest.mark.parametrize("query", [
        "INSERT INTO accounting_accounts (shop_id, target, kind, account) "
        "VALUES (1, 'sage', 'labor', 'Labor income')",
        "INSERT INTO accounting_accounts (shop_id, target, kind, account) "
        "VALUES (1, 'xero', 'freight', 'Freight')",
        "INSERT INTO accounting_accounts (shop_id, target, kind, account) "
        "VALUES (1, 'xero', 'labor', '   ')",
        "INSERT INTO accounting_exports (shop_id, target, period_from, period_to, "
        "file_name, file_sha256, invoice_count, exported_at) "
        "VALUES (1, 'xero', '2026-09-01', '2026-09-30', 'x.csv', 'abc', 0, 'now')",
    ])
    def test_the_checks_refuse_bad_rows(self, db, query):
        sql(db, "INSERT INTO shops (name) VALUES ('S')")
        with pytest.raises(sqlite3.IntegrityError):
            sql(db, query)

    def test_one_account_per_shop_target_and_kind(self, db):
        sql(db, "INSERT INTO shops (name) VALUES ('S')")
        sql(db, "INSERT INTO accounting_accounts (shop_id, target, kind, account) "
                "VALUES (1, 'xero', 'labor', '200')")
        with pytest.raises(sqlite3.IntegrityError):
            sql(db, "INSERT INTO accounting_accounts (shop_id, target, kind, account) "
                    "VALUES (1, 'xero', 'labor', '201')")
        sql(db, "INSERT INTO accounting_accounts (shop_id, target, kind, account) "
                "VALUES (1, 'quickbooks_online', 'labor', 'Labor income')")
