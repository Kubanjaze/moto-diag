"""Shared helpers for Phase 371's tests (the payments feed).

The event-list pages are built from Stripe's documented list shape
(docs.stripe.com/api/events/list: ``{"object": "list", "url":
"/v1/events", "has_more": …, "data": […]}``) around
:func:`stripe_fixtures.event`, and handed to :class:`FixtureHTTP` as
``(status, body)`` tuples. No fixture file is read or written.
"""

from __future__ import annotations

from typing import Optional

from motodiag.payments import invoice_payments as ip
from support.phase273 import answer, seed_account, seed_invoice
from support.stripe_fixtures import FROZEN_AT, SHOP_ACCOUNT, event, stripe_settings

EVENTS = r"/v1/events"
CHECKOUT = ("POST", r"/v1/checkout/sessions", "checkout_session_invoice")
#: The documentation's example DSN (docs.sentry.io), with a made-up key.
PLANTED_DSN_KEY = "plantedPublicKey371"
DSN_TEXT = f"https://{PLANTED_DSN_KEY}@o0.ingest.sentry.io/0"


def page(events: list[dict], has_more: bool = False) -> tuple[int, dict]:
    return 200, {"object": "list", "url": "/v1/events", "has_more": has_more,
                 "data": events}


def ask(events: Optional[list[dict]] = None, has_more: bool = False):
    return ("GET", EVENTS, page(events or [], has_more))


def refused():
    return ("GET", EVENTS, (401, {"error": {"type": "invalid_request_error",
                                            "message": "Invalid API Key"}}))


def busy():
    return ("GET", EVENTS, (429, {"error": {"type": "invalid_request_error",
                                            "message": "slow down"}}))


def succeeded(payment_id: int, invoice_id: int, *, event_id: str = "evt_feed_ok",
              account: Optional[str] = None, created: int = FROZEN_AT,
              livemode: bool = False) -> dict:
    """A ``payment_intent.succeeded`` with no ``account`` unless given."""
    evt = event("payment_intent.succeeded", {
        "id": "pi_test_1", "object": "payment_intent", "amount": 25000,
        "amount_received": 25000, "currency": "usd", "status": "succeeded",
        "metadata": {"motodiag_payment_id": str(payment_id),
                     "motodiag_invoice_id": str(invoice_id)},
    }, event_id=event_id, account=account, livemode=livemode)
    evt["created"] = created
    return evt


def started_payment(db: str, monkeypatch) -> dict:
    """A sent invoice of 250.00 USD at a connected shop, with a started
    Checkout payment (payment id 1)."""
    ids = seed_invoice(db)
    seed_account(db, ids["shop_id"])
    answer(monkeypatch, [CHECKOUT])
    ip.start_checkout(ids["invoice_id"], settings=stripe_settings(), db_path=db)
    return ids


__all__ = ["SHOP_ACCOUNT", "FROZEN_AT"]
