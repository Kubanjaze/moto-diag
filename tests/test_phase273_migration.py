"""Phase 273 — migration 080: Stripe payments.

New tables and two new columns; no existing row changes; the rollback
takes them all away. The schema head is read from the code, never pinned
as a literal (F124).
"""

from __future__ import annotations

import sqlite3

import pytest

from motodiag.core.database import get_connection, init_db
from motodiag.core.migrations import (
    apply_pending_migrations, get_current_version, get_migration_by_version,
    rollback_to_version,
)

NEW_TABLES = {"shop_payment_accounts", "invoice_payments", "terminal_locations",
              "terminal_readers", "subscription_payments"}


def _tables(db):
    with sqlite3.connect(db) as c:
        return {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _columns(db, table):
    with sqlite3.connect(db) as c:
        return [r[1] for r in c.execute(f"PRAGMA table_info({table})")]


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "m080.db")
    init_db(path)
    return path


def test_080_adds_the_tables_and_columns(db):
    assert get_migration_by_version(80) is not None
    assert get_current_version(db) >= 80
    assert NEW_TABLES <= _tables(db)
    assert {"account", "livemode"} <= set(_columns(db, "stripe_webhook_events"))
    for table in ("invoice_payments", "subscription_payments"):
        cols = _columns(db, table)
        assert any(c.endswith("_cents") for c in cols)
        assert "amount" not in cols  # money is integer cents here


def test_the_rollback_takes_them_away_and_keeps_existing_rows(db):
    with get_connection(db) as conn:
        conn.execute("INSERT INTO stripe_webhook_events (event_id, type, payload_json) "
                     "VALUES ('evt_kept', 'x', '{}')")
    rollback_to_version(79, db)
    assert not (NEW_TABLES & _tables(db))
    assert {"account", "livemode"}.isdisjoint(_columns(db, "stripe_webhook_events"))
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT event_id FROM stripe_webhook_events").fetchall() == [
            ("evt_kept",)]
    assert 80 in apply_pending_migrations(db)
    assert NEW_TABLES <= _tables(db)


def test_amounts_must_be_positive_and_statuses_known(db):
    with get_connection(db) as conn:
        shop = conn.execute("INSERT INTO shops (name) VALUES ('S')").lastrowid
        cust = conn.execute("INSERT INTO customers (name) VALUES ('C')").lastrowid
        inv = conn.execute("INSERT INTO invoices (customer_id, invoice_number) "
                           "VALUES (?, 'I-1')", (cust,)).lastrowid
    row = ("INSERT INTO invoice_payments (invoice_id, shop_id, stripe_account_id, channel, "
           "amount_cents, currency, status, started_at) VALUES (?, ?, 'acct_x', ?, ?, 'usd', ?, 'now')")
    for channel, cents, status in (("checkout", 0, "started"), ("cash", 100, "started"),
                                   ("checkout", 100, "refunded")):
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(row, (inv, shop, channel, cents, status))
    with get_connection(db) as conn:
        conn.execute(row, (inv, shop, "terminal", 100, "started"))


def test_a_payment_keeps_its_invoice(db):
    """ON DELETE RESTRICT: an invoice with a Stripe payment cannot vanish."""
    with get_connection(db) as conn:
        shop = conn.execute("INSERT INTO shops (name) VALUES ('S')").lastrowid
        cust = conn.execute("INSERT INTO customers (name) VALUES ('C')").lastrowid
        inv = conn.execute("INSERT INTO invoices (customer_id, invoice_number) "
                           "VALUES (?, 'I-1')", (cust,)).lastrowid
        conn.execute("INSERT INTO invoice_payments (invoice_id, shop_id, stripe_account_id, "
                     "channel, amount_cents, currency, started_at) VALUES "
                     "(?, ?, 'acct_x', 'checkout', 100, 'usd', 'now')", (inv, shop))
    with pytest.raises(sqlite3.IntegrityError):
        with get_connection(db) as conn:
            conn.execute("DELETE FROM invoices WHERE id = ?", (inv,))
