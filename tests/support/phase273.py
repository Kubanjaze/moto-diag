"""Shared helpers for Phase 273's tests (payments through Stripe).

Seeds write the rows a payment needs (a shop, its customer, a work order,
a sent invoice, the shop's connected account) straight into a scratch
database. Stripe answers from fixtures through :class:`FixtureHTTP`.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

import pytest
from click.testing import CliRunner

from motodiag.cli.main import cli as main_cli
from motodiag.cli.theme import reset_console
from motodiag.core.config import reset_settings
from motodiag.core.database import get_connection, init_db
from motodiag.payments import stripe_api

from support.stripe_fixtures import (
    LOCATION, READER, SHOP_ACCOUNT, TEST_KEY, TEST_SECRET, FixtureHTTP,
)

STRIPE_ENV = {
    "MOTODIAG_BILLING_PROVIDER": "stripe",
    "MOTODIAG_STRIPE_API_KEY": TEST_KEY,
    "MOTODIAG_STRIPE_WEBHOOK_SECRET": TEST_SECRET,
    "MOTODIAG_STRIPE_PRICE_INDIVIDUAL": "price_test_individual",
    "MOTODIAG_STRIPE_PRICE_SHOP": "price_test_shop",
    "MOTODIAG_STRIPE_PRICE_COMPANY": "price_test_company",
}


def new_db(tmp_path, name: str = "phase273.db") -> str:
    path = str(tmp_path / name)
    init_db(path)
    return path


def sql(db_path: str, query: str, params=()):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(query, params).fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


def seed_invoice(db_path: str, *, total: float = 250.00, status: str = "sent",
                 currency: str = "USD", shop_name: str = "Phase 273 Test Shop",
                 address: bool = True) -> dict:
    """A shop, a customer, a bike, a work order and an invoice for it."""
    with get_connection(db_path) as conn:
        shop_id = conn.execute(
            "INSERT INTO shops (name, address, city, state, zip) VALUES (?, ?, ?, ?, ?)",
            (shop_name, *(("1 Test Street", "Boston", "MA", "02110") if address
                          else (None, None, None, None))),
        ).lastrowid
        customer_id = conn.execute(
            "INSERT INTO customers (name) VALUES ('Test Customer')").lastrowid
        bike_id = conn.execute(
            "INSERT INTO vehicles (make, model, year, powertrain, engine_type) "
            "VALUES ('Honda', 'CB500F', 2020, 'ice', 'four_stroke')").lastrowid
        wo_id = conn.execute(
            "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title) "
            "VALUES (?, ?, ?, 'Brake service')", (shop_id, bike_id, customer_id),
        ).lastrowid
        invoice_id = conn.execute(
            "INSERT INTO invoices (customer_id, invoice_number, status, subtotal, "
            "tax_amount, total, currency, work_order_id) VALUES (?, ?, ?, ?, 0, ?, ?, ?)",
            (customer_id, f"INV-273-{wo_id:04d}", status, total, total, currency, wo_id),
        ).lastrowid
    return {"shop_id": shop_id, "customer_id": customer_id, "wo_id": wo_id,
            "invoice_id": invoice_id}


def seed_account(db_path: str, shop_id: int, *, status: Optional[str] = "active",
                 account: str = SHOP_ACCOUNT) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO shop_payment_accounts
               (shop_id, stripe_account_id, dashboard, fees_collector,
                losses_collector, country, currency, card_payments_status,
                requirements_due, status_checked_at)
               VALUES (?, ?, 'full', 'stripe', 'stripe', 'us', 'usd', ?, 0,
                       '2026-10-06T12:00:00.000+00:00')""",
            (shop_id, account, status),
        )


def seed_reader(db_path: str, shop_id: int) -> None:
    with get_connection(db_path) as conn:
        loc = conn.execute(
            "INSERT INTO terminal_locations (shop_id, stripe_account_id, "
            "stripe_location_id, display_name, address_json) VALUES (?, ?, "
            "?, 'Test', '{}')", (shop_id, SHOP_ACCOUNT, LOCATION),
        ).lastrowid
        conn.execute(
            "INSERT INTO terminal_readers (shop_id, location_id, stripe_reader_id, "
            "label, simulated) VALUES (?, ?, ?, 'sim', 1)",
            (shop_id, loc, READER),
        )


def answer(monkeypatch, expected) -> FixtureHTTP:
    """Stripe answers ``expected`` in order, through the SDK's http_client."""
    http = FixtureHTTP(expected)
    monkeypatch.setattr(stripe_api, "_test_http_client", http)
    return http


def cli(db_path: str, *args, env: Optional[dict] = None, columns: int = 10000):
    try:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("MOTODIAG_DB_PATH", db_path)
            mp.setenv("COLUMNS", str(columns))
            for k, v in (env if env is not None else STRIPE_ENV).items():
                mp.setenv(k, v)
            reset_settings()
            reset_console()
            return CliRunner().invoke(main_cli, [str(a) for a in args])
    finally:
        reset_settings()
        reset_console()
