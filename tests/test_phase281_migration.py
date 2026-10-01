"""Phase 281 — migration 078: tax by jurisdiction, exchange rates, recall fetches, VIN decodes.

Eight tables, columns on `recalls` and `invoices`, and Massachusetts's rate
and three line rules. The migration changes no existing row: planted rows in
the tables it touches read back the same after the upgrade (the new columns
NULL) and after the rollback. Massachusetts's rows carry exactly the sources
quoted in the phase's sources file.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

from motodiag.core.database import SCHEMA_VERSION
from motodiag.core.migrations import MIGRATIONS, apply_pending_migrations, rollback_to_version
from support.phase281 import new_db, sql

MIGRATION = 78

NEW_TABLES = {"tax_jurisdictions", "shop_tax_jurisdictions", "tax_rates", "tax_line_rules",
              "exchange_rates", "recall_fetches", "recall_vehicles", "vin_decodes"}
RECALL_COLUMNS = ["source", "fetched_at", "component", "consequence"]
INVOICE_COLUMNS = ["tax_rate", "tax_rate_id", "tax_source", "tax_recheck_by",
                   "taxed_line_types", "fx_from_currency", "fx_rate", "fx_rate_id",
                   "fx_rate_date", "fx_source"]

REPO = Path(__file__).parent.parent


def _sources_file() -> Path:
    for folder in ("in_progress", "completed"):
        path = REPO / "docs" / "phases" / folder / "281_sources.md"
        if path.exists():
            return path
    raise AssertionError("281_sources.md not found")


@pytest.fixture
def db(tmp_path):
    return new_db(tmp_path)


def _tables(db_path) -> set[str]:
    return {r[0] for r in sql(db_path, "SELECT name FROM sqlite_master WHERE type = 'table'")}


def _columns(db_path, table) -> list[str]:
    return [r[1] for r in sql(db_path, f"PRAGMA table_info({table})")]


class TestMigration078:
    def test_the_head_is_at_least_078_and_the_last_migration(self):
        assert SCHEMA_VERSION >= MIGRATION
        assert SCHEMA_VERSION == max(m.version for m in MIGRATIONS)

    def test_a_fresh_database_has_the_tables_and_columns(self, db):
        assert NEW_TABLES <= _tables(db)
        recall_cols, invoice_cols = _columns(db, "recalls"), _columns(db, "invoices")
        start = recall_cols.index(RECALL_COLUMNS[0])
        assert recall_cols[start:start + 4] == RECALL_COLUMNS
        start = invoice_cols.index(INVOICE_COLUMNS[0])
        assert invoice_cols[start:start + 10] == INVOICE_COLUMNS
        assert "tax_jurisdiction" not in " ".join(_columns(db, "shops"))

    def test_the_rollback_removes_exactly_what_the_upgrade_added(self, db):
        rollback_to_version(MIGRATION - 1, db)
        assert not (NEW_TABLES & _tables(db))
        assert not set(RECALL_COLUMNS) & set(_columns(db, "recalls"))
        assert not set(INVOICE_COLUMNS) & set(_columns(db, "invoices"))
        assert apply_pending_migrations(db) == [
            m.version for m in MIGRATIONS if m.version >= MIGRATION]
        assert NEW_TABLES <= _tables(db)

    def test_existing_rows_are_unchanged_either_way(self, db):
        rollback_to_version(MIGRATION - 1, db)
        sql(db, "INSERT INTO shops (name) VALUES ('Planted Shop')")
        sql(db, "INSERT INTO customers (name, shop_id) VALUES ('Dana Reyes', 1)")
        sql(db, "INSERT INTO vehicles (make, model, year) VALUES ('Honda', 'CB500F', 2020)")
        sql(db, "INSERT INTO recalls (campaign_number, make, description) "
                "VALUES ('PLANT-1', 'Honda', 'planted')")
        sql(db, "INSERT INTO recall_resolutions (vehicle_id, recall_id) VALUES (1, 1)")
        sql(db, "INSERT INTO invoices (customer_id, invoice_number, total) "
                "VALUES (2, 'INV-PLANT', 12.5)")
        watched = ("shops", "customers", "vehicles", "recall_resolutions",
                   "invoice_line_items", "work_orders")
        before = {t: sql(db, f"SELECT * FROM {t} ORDER BY rowid") for t in watched}
        recalls_before = sql(db, "SELECT * FROM recalls ORDER BY rowid")
        invoices_before = sql(db, "SELECT * FROM invoices ORDER BY rowid")

        apply_pending_migrations(db)

        def prefix(table, before_rows, extra):
            # This migration's new columns read NULL; a later migration's
            # columns, if any, are not this test's to pin.
            after = sql(db, f"SELECT * FROM {table} ORDER BY rowid")
            assert len(after) == len(before_rows), table
            return [row[:len(b) + extra] for row, b in zip(after, before_rows)]

        for t in watched:
            assert prefix(t, before[t], 0) == before[t], t
        assert prefix("recalls", recalls_before, 4) == [
            row + (None,) * 4 for row in recalls_before]
        assert prefix("invoices", invoices_before, 10) == [
            row + (None,) * 10 for row in invoices_before]
        assert sql(db, "PRAGMA foreign_key_check") == []

        rollback_to_version(MIGRATION - 1, db)
        for t in watched:
            assert sql(db, f"SELECT * FROM {t} ORDER BY rowid") == before[t], t
        assert sql(db, "SELECT * FROM recalls ORDER BY rowid") == recalls_before
        assert sql(db, "SELECT * FROM invoices ORDER BY rowid") == invoices_before

    def test_massachusetts_is_the_only_jurisdiction_shipped(self, db):
        assert sql(db, "SELECT code, name, currency FROM tax_jurisdictions") == [
            ("US-MA", "Massachusetts", "USD")]
        assert sql(db, "SELECT rate, effective_from, valid_until, checked_on, provenance, "
                       "shop_id FROM tax_rates") == [
            (0.0625, "2009-08-01", "2027-09-30", "2026-09-30", "regulation", None)]

    def test_massachusetts_rules_parts_labour_and_a_diagnostic_reading(self, db):
        rules = {r[0]: r[1:] for r in sql(
            db, "SELECT line_type, taxable, basis, valid_until FROM tax_line_rules")}
        assert rules == {
            "parts": (1, "stated", "2027-09-30"),
            "labor": (0, "stated", "2027-09-30"),
            "diagnostic": (0, "reading", "2027-09-30"),
        }
        assert "misc" not in rules, "no DOR page names a shop-supplies charge"
        clause = sql(db, "SELECT source_clause FROM tax_line_rules "
                         "WHERE line_type = 'diagnostic'")[0][0]
        assert clause.startswith("a reading of 830 CMR 64H.1.1(2)(a)1")

    def test_every_shipped_source_is_quoted_in_the_sources_file(self, db):
        text = _sources_file().read_text()
        urls = {r[0] for r in sql(db, "SELECT source_url FROM tax_rates UNION "
                                      "SELECT source_url FROM tax_line_rules")}
        notes = sql(db, "SELECT notes FROM tax_rates")[0][0]
        urls |= set(re.findall(r"https://\S+", notes))
        assert len(urls) == 3
        for url in urls:
            assert url in text, url
        for clause in ("(2)(b)", "(2)(a)", "(5)(a)"):
            assert clause in text

    def test_the_checks_hold_the_rules(self, db):
        with pytest.raises(sqlite3.IntegrityError):
            sql(db, "INSERT INTO tax_rates (jurisdiction_id, shop_id, rate, effective_from, "
                    "valid_until, source_title, checked_on, provenance) "
                    "VALUES (1, NULL, 0.05, '2026-01-01', '2026-12-31', 'x', '2026-01-01', "
                    "'shop')")
        with pytest.raises(sqlite3.IntegrityError):
            sql(db, "INSERT INTO tax_rates (jurisdiction_id, shop_id, rate, effective_from, "
                    "valid_until, source_title, checked_on, provenance) "
                    "VALUES (1, NULL, 0.05, '2026-01-01', '2025-12-31', 'x', '2026-01-01', "
                    "'regulation')")
        with pytest.raises(sqlite3.IntegrityError):
            sql(db, "INSERT INTO recall_fetches (make, model, model_year, fetched_at, url, "
                    "outcome, error) VALUES ('H', 'M', 2020, 'now', 'u', 'ok', 'boom')")
        with pytest.raises(sqlite3.IntegrityError):
            sql(db, "INSERT INTO exchange_rates (base, quote, rate, rate_date, valid_until, "
                    "source) VALUES ('EUR', 'USD', '0', '2026-09-30', '2026-10-05', 'ecb')")
