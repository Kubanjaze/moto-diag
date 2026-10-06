"""A shop invoice paid through Stripe (Phase 273).

Two ways to start a payment: a Checkout Session the customer pays online,
or a Payment Intent sent to the shop's Terminal reader. Neither marks the
invoice paid. Only Stripe's verified ``payment_intent.succeeded``, from
the shop's own account, for a payment this app started, with the exact
amount and currency, does (:func:`apply_payment_intent`).

Money is integer cents here. The invoice's total is stored in REAL
dollars (migration 118); :func:`invoice_amount_cents` is the one place
it is read for a payment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from motodiag.core.config import Settings, get_settings
from motodiag.core.database import get_connection
from motodiag.core.timestamps import utc_now
from motodiag.payments import stripe_api
from motodiag.payments.connect import ConnectError, require_payable_account
from motodiag.payments.terminal import get_reader
from motodiag.shop.invoicing import _dollars_to_cents

PAYABLE_STATUSES = ("sent", "overdue")
META_PAYMENT = "motodiag_payment_id"
META_INVOICE = "motodiag_invoice_id"


class PaymentEventRejected(ValueError):
    """A verified event that this app will not apply; the message says why."""


@dataclass(frozen=True)
class StartedPayment:
    payment_id: int
    invoice_id: int
    invoice_number: str
    channel: str
    amount_cents: int
    currency: str
    checkout_url: Optional[str] = None
    payment_intent_id: Optional[str] = None
    reader_action_status: Optional[str] = None


def invoice_amount_cents(invoice: dict) -> int:
    """The invoice's total in cents: the one read of ``invoices.total``."""
    return _dollars_to_cents(invoice["total"])


def _invoice_with_shop(invoice_id: int, db_path: Optional[str]) -> dict:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT i.*, w.shop_id AS shop_id FROM invoices i "
            "LEFT JOIN work_orders w ON w.id = i.work_order_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
    if row is None:
        raise ConnectError(f"invoice not found: id={invoice_id}")
    inv = dict(row)
    if inv["shop_id"] is None:
        raise ConnectError(
            f"invoice {inv['invoice_number']} has no work order, so no shop to pay"
        )
    return inv


def _require_payable(inv: dict) -> int:
    if inv["status"] not in PAYABLE_STATUSES:
        raise ConnectError(
            f"invoice {inv['invoice_number']} is {inv['status']}; only a sent or "
            "overdue invoice can be paid"
        )
    cents = invoice_amount_cents(inv)
    if cents <= 0:
        raise ConnectError(f"invoice {inv['invoice_number']} has nothing to pay")
    return cents


def _insert_started(inv: dict, account_id: str, channel: str, cents: int,
                    user_id: Optional[int], db_path: Optional[str]) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO invoice_payments
               (invoice_id, shop_id, stripe_account_id, channel, amount_cents,
                currency, status, started_by_user_id, started_at)
               VALUES (?, ?, ?, ?, ?, ?, 'started', ?, ?)""",
            (inv["id"], inv["shop_id"], account_id, channel, cents,
             inv["currency"].lower(), user_id, utc_now()),
        )
        return int(cur.lastrowid)


def _forget(payment_id: int, db_path: Optional[str]) -> None:
    """Remove a payment row Stripe never accepted."""
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM invoice_payments WHERE id = ? AND status = 'started' "
                     "AND payment_intent_id IS NULL AND checkout_session_id IS NULL",
                     (payment_id,))


def _metadata(payment_id: int, inv: dict) -> dict:
    return {META_PAYMENT: str(payment_id), META_INVOICE: str(inv["id"]),
            "invoice_number": inv["invoice_number"]}


def start_checkout(invoice_id: int, *, user_id: Optional[int] = None,
                   settings: Optional[Settings] = None,
                   db_path: Optional[str] = None) -> StartedPayment:
    """A Checkout Session on the shop's account for the invoice's total."""
    s = settings or get_settings()
    inv = _invoice_with_shop(invoice_id, db_path)
    cents = _require_payable(inv)
    acct = require_payable_account(inv["shop_id"], db_path=db_path)
    sc = stripe_api.client(s)
    payment_id = _insert_started(inv, acct.stripe_account_id, "checkout", cents,
                                 user_id, db_path)
    meta = _metadata(payment_id, inv)
    try:
        session = stripe_api.as_dict(stripe_api.call(
            "create the invoice's checkout session",
            lambda: sc.v1.checkout.sessions.create({
                "mode": "payment",
                "line_items": [{
                    "quantity": 1,
                    "price_data": {
                        "currency": inv["currency"].lower(),
                        "unit_amount": cents,
                        "product_data": {"name": f"Invoice {inv['invoice_number']}"},
                    },
                }],
                "client_reference_id": str(inv["id"]),
                "metadata": meta,
                "payment_intent_data": {"metadata": meta},
                "success_url": s.invoice_payment_return_url,
                "cancel_url": s.invoice_payment_return_url,
            }, {
                "stripe_account": acct.stripe_account_id,
                "idempotency_key": f"motodiag-invoice-payment-{payment_id}",
            }),
        ))
    except Exception:
        _forget(payment_id, db_path)
        raise
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE invoice_payments SET checkout_session_id = ?, livemode = ? WHERE id = ?",
            (session["id"], 1 if session.get("livemode") else 0, payment_id),
        )
    return StartedPayment(payment_id, inv["id"], inv["invoice_number"], "checkout",
                          cents, inv["currency"].lower(), checkout_url=session["url"])


def start_terminal(invoice_id: int, *, user_id: Optional[int] = None,
                   settings: Optional[Settings] = None,
                   db_path: Optional[str] = None) -> StartedPayment:
    """A card-present Payment Intent, sent to the shop's reader. With a
    test key and a simulated reader, the test card is presented too."""
    s = settings or get_settings()
    inv = _invoice_with_shop(invoice_id, db_path)
    cents = _require_payable(inv)
    acct = require_payable_account(inv["shop_id"], db_path=db_path)
    reader = get_reader(inv["shop_id"], db_path=db_path)
    if reader is None:
        raise ConnectError(
            f"shop {inv['shop_id']} has no Terminal reader; set one up with "
            f"`motodiag shop terminal setup --shop {inv['shop_id']}`"
        )
    sc = stripe_api.client(s)
    opts = {"stripe_account": acct.stripe_account_id}
    payment_id = _insert_started(inv, acct.stripe_account_id, "terminal", cents,
                                 user_id, db_path)
    meta = _metadata(payment_id, inv)
    try:
        intent = stripe_api.as_dict(stripe_api.call(
            "create the invoice's card-present payment",
            lambda: sc.v1.payment_intents.create({
                "amount": cents,
                "currency": inv["currency"].lower(),
                "allowed_payment_method_types": ["card_present"],
                "capture_method": "automatic",
                "description": f"Invoice {inv['invoice_number']}",
                "metadata": meta,
            }, {**opts, "idempotency_key": f"motodiag-invoice-payment-{payment_id}"}),
        ))
    except Exception:
        _forget(payment_id, db_path)
        raise
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE invoice_payments SET payment_intent_id = ?, terminal_reader_id = ?, "
            "livemode = ? WHERE id = ?",
            (intent["id"], reader.stripe_reader_id,
             1 if intent.get("livemode") else 0, payment_id),
        )
    action = stripe_api.as_dict(stripe_api.call(
        "send the payment to the reader",
        lambda: sc.v1.terminal.readers.process_payment_intent(
            reader.stripe_reader_id, {"payment_intent": intent["id"]}, opts),
    ))
    if reader.simulated and stripe_api.is_test_key(s.stripe_api_key):
        action = stripe_api.as_dict(stripe_api.call(
            "present the simulated card",
            lambda: sc.v1.test_helpers.terminal.readers.present_payment_method(
                reader.stripe_reader_id, {}, opts),
        ))
    status = ((action.get("action") or {}).get("status"))
    return StartedPayment(payment_id, inv["id"], inv["invoice_number"], "terminal",
                          cents, inv["currency"].lower(),
                          payment_intent_id=intent["id"], reader_action_status=status)


def payments_for_invoice(invoice_id: int, db_path: Optional[str] = None) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM invoice_payments WHERE invoice_id = ? ORDER BY id",
            (invoice_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Stripe's verified events
# ---------------------------------------------------------------------------


def apply_payment_intent(event: dict, db_path: Optional[str] = None) -> str:
    """``payment_intent.succeeded`` or ``.payment_failed``.

    One-way: started → failed → succeeded, or started → succeeded. A
    success is final, so a repeat or a late failure changes nothing.
    Returns what was done.
    """
    pi = (event.get("data") or {}).get("object") or {}
    meta = pi.get("metadata") or {}
    raw_id = meta.get(META_PAYMENT)
    if raw_id is None:
        return "ignored: not a payment this app started"
    try:
        payment_id = int(raw_id)
    except (TypeError, ValueError):
        return "ignored: not a payment this app started"
    succeeded = event.get("type") == "payment_intent.succeeded"
    with get_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM invoice_payments WHERE id = ?",
                           (payment_id,)).fetchone()
        if row is None:
            return "ignored: no such payment"
        row = dict(row)
        _check_source(event, pi, meta, row)
        if row["status"] == "succeeded":
            return "unchanged: the payment had already succeeded"
        now = _event_time(event)
        if not succeeded:
            message = ((pi.get("last_payment_error") or {}).get("message")
                       or "the payment failed")
            conn.execute(
                "UPDATE invoice_payments SET status = 'failed', failure_message = ?, "
                "payment_intent_id = COALESCE(payment_intent_id, ?) WHERE id = ?",
                (message, pi.get("id"), payment_id),
            )
            return "failed"
        inv = dict(conn.execute("SELECT * FROM invoices WHERE id = ?",
                                (row["invoice_id"],)).fetchone())
        outcome, reason = _decide(pi, row, inv)
        if outcome == "paid_invoice":
            changed = conn.execute(
                "UPDATE invoices SET status = 'paid', paid_at = ?, updated_at = ? "
                "WHERE id = ? AND status IN ('sent', 'overdue')",
                (now, now, inv["id"]),
            ).rowcount
            if changed != 1:
                outcome, reason = "rejected", "the invoice changed while being paid"
        conn.execute(
            "UPDATE invoice_payments SET status = 'succeeded', outcome = ?, "
            "outcome_reason = ?, settled_at = ?, "
            "payment_intent_id = COALESCE(payment_intent_id, ?) WHERE id = ?",
            (outcome, reason, now, pi.get("id"), payment_id),
        )
        return outcome


def _event_time(event: dict) -> str:
    """When Stripe recorded the event (its ``created``, UTC seconds), in
    Phase 370's format; the time it reached us only if Stripe gave none."""
    created = event.get("created")
    if isinstance(created, int):
        return datetime.fromtimestamp(created, tz=timezone.utc).isoformat(
            timespec="milliseconds")
    return utc_now()


def _check_source(event: dict, pi: dict, meta: dict, row: dict) -> None:
    if str(meta.get(META_INVOICE)) != str(row["invoice_id"]):
        raise PaymentEventRejected(
            f"payment {row['id']} is for invoice {row['invoice_id']}, the event "
            f"names invoice {meta.get(META_INVOICE)}"
        )
    if event.get("account") != row["stripe_account_id"]:
        raise PaymentEventRejected(
            f"payment {row['id']} belongs to the shop's account, and the event "
            f"came from {event.get('account') or 'the platform account'}"
        )
    if row["payment_intent_id"] and pi.get("id") != row["payment_intent_id"]:
        raise PaymentEventRejected(
            f"payment {row['id']} is Payment Intent {row['payment_intent_id']}, "
            f"the event is {pi.get('id')}"
        )


def _decide(pi: dict, row: dict, inv: dict) -> tuple[str, Optional[str]]:
    received = pi.get("amount_received")
    currency = (pi.get("currency") or "").lower()
    owed = invoice_amount_cents(inv)
    if received != row["amount_cents"] or received != owed:
        return "rejected", (f"Stripe received {received} {currency} cents; the "
                            f"invoice is {owed} and the payment was started for "
                            f"{row['amount_cents']}. Refund in Stripe.")
    if currency != inv["currency"].lower():
        return "rejected", (f"Stripe received {currency}; the invoice is in "
                            f"{inv['currency']}. Refund in Stripe.")
    if inv["status"] in PAYABLE_STATUSES:
        return "paid_invoice", None
    if inv["status"] == "paid":
        return "paid_twice", "the invoice was already paid: refund one in Stripe"
    return "rejected", f"the invoice is {inv['status']}: refund in Stripe"


def apply_refund(event: dict, db_path: Optional[str] = None) -> str:
    """``charge.refunded``: record the refunded cents; the invoice's status
    is not changed."""
    charge = (event.get("data") or {}).get("object") or {}
    pi_id = charge.get("payment_intent")
    if not pi_id:
        return "ignored: no payment intent"
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM invoice_payments WHERE payment_intent_id = ?",
                           (pi_id,)).fetchone()
        if row is None:
            return "ignored: not a payment this app started"
        if event.get("account") != row["stripe_account_id"]:
            raise PaymentEventRejected(
                f"refund for payment {row['id']} came from "
                f"{event.get('account') or 'the platform account'}, not the shop's account"
            )
        refunded = int(charge.get("amount_refunded") or 0)
        conn.execute(
            "UPDATE invoice_payments SET refunded_cents = MAX(refunded_cents, ?) WHERE id = ?",
            (refunded, row["id"]),
        )
    return "refund recorded"
