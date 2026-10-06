"""Stripe webhook event dispatch (Phase 176; Phase 273, F187).

Idempotent: every event is recorded in ``stripe_webhook_events`` by
``event_id``, and a repeat is acknowledged without running its handler.

Order-independent: Stripe does not deliver events in order and says not
to use ``created`` to order them. A subscription event only names the
subscription; the handler re-reads it from Stripe and stores what Stripe
says now. An invoice payment only moves forward (see
:mod:`motodiag.payments.invoice_payments`).

Retried when Stripe could not be read: the event's record is removed and
the route answers 503, so Stripe (or ``stripe listen``) delivers it
again. Any other handler failure is recorded with its error and
acknowledged.
"""

from __future__ import annotations

import json as _json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from motodiag.billing.providers import (
    BillingProvider, BillingProviderError, tier_for_price,
)
from motodiag.billing.subscription_repo import (
    get_subscription_by_stripe_id, upsert_from_stripe,
)
from motodiag.core.config import Environment, Settings, get_settings
from motodiag.core.database import get_connection
from motodiag.core.timestamps import utc_now
from motodiag.payments import invoice_payments, stripe_api


logger = logging.getLogger(__name__)


class LiveEventRefused(ValueError):
    """An event with ``livemode: true`` outside ``env=prod``."""


class SubscriptionEventError(ValueError):
    """A subscription event that cannot be applied; recorded, not retried."""


# ---------------------------------------------------------------------------
# Event-id idempotency
# ---------------------------------------------------------------------------


def _record_event(
    event: dict, db_path: Optional[str] = None,
) -> bool:
    """Insert the event into ``stripe_webhook_events``. Returns True
    on first insert, False if already seen (idempotent skip)."""
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "unknown")
    payload = _json.dumps(event, default=str)
    if not event_id:
        logger.warning("webhook event missing id; skipping dedup")
        return True
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO stripe_webhook_events
               (event_id, type, payload_json, received_at, account, livemode)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                event_id, event_type, payload,
                datetime.now(timezone.utc).isoformat(),
                event.get("account"),
                1 if event.get("livemode") else 0,
            ),
        )
        if cur.rowcount == 0:
            logger.info(
                "stripe webhook replay: event_id=%s (already processed)",
                event_id,
            )
            return False
        return True


def _mark_processed(
    event_id: str, error: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """UPDATE stripe_webhook_events
               SET processed_at = ?, error = ?
               WHERE event_id = ?""",
            (
                datetime.now(timezone.utc).isoformat(),
                error, event_id,
            ),
        )


def _forget_event(event_id: str, db_path: Optional[str]) -> None:
    """Remove the record of an event that must be delivered again."""
    if not event_id:
        return
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM stripe_webhook_events WHERE event_id = ?",
                     (event_id,))


# ---------------------------------------------------------------------------
# Subscriptions: re-read, never trust the payload's state
# ---------------------------------------------------------------------------


def _iso_ts(ts: Any) -> Optional[str]:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OSError):
        return None


def _first_item(sub: dict) -> dict:
    items = ((sub.get("items") or {}).get("data")) or []
    return items[0] if items else {}


def _resolve_user_id(sub: dict, db_path: Optional[str]) -> Optional[int]:
    """The motodiag user: ``metadata.user_id`` (set through
    ``subscription_data.metadata`` at checkout), else the row already
    holding this subscription or customer."""
    meta = sub.get("metadata") or {}
    if "user_id" in meta:
        try:
            return int(meta["user_id"])
        except (ValueError, TypeError):
            pass
    existing = get_subscription_by_stripe_id(str(sub.get("id")), db_path=db_path)
    if existing is not None:
        return int(existing["user_id"])
    customer_id = sub.get("customer")
    if customer_id:
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT user_id FROM subscriptions "
                "WHERE stripe_customer_id = ? LIMIT 1",
                (customer_id,),
            ).fetchone()
        if row is not None:
            return int(row["user_id"])
    return None


def subscription_data_from_stripe(sub: dict, settings: Settings) -> dict[str, Any]:
    """What to store from a subscription as Stripe returned it. The
    billing period is per item since API version 2025-03-31.basil."""
    from motodiag.auth.deps import SUBSCRIPTION_TIERS

    item = _first_item(sub)
    price_id = (item.get("price") or {}).get("id")
    tier = (sub.get("metadata") or {}).get("tier")
    if tier not in SUBSCRIPTION_TIERS:
        tier = tier_for_price(price_id, settings)
    if tier is None:
        raise SubscriptionEventError(
            f"subscription {sub.get('id')}: no tier in its metadata, and its "
            f"price {price_id!r} is none of the three configured tier prices"
        )
    if not sub.get("status"):
        raise SubscriptionEventError(f"subscription {sub.get('id')} has no status")
    return {
        "tier": tier,
        "status": sub["status"],
        "stripe_customer_id": sub.get("customer"),
        "stripe_price_id": price_id,
        "current_period_start": _iso_ts(item.get("current_period_start")),
        "current_period_end": _iso_ts(item.get("current_period_end")),
        "cancel_at_period_end": bool(sub.get("cancel_at_period_end") or False),
        "canceled_at": _iso_ts(sub.get("canceled_at")),
        "trial_end": _iso_ts(sub.get("trial_end")),
    }


def _handle_subscription(
    event: dict, db_path: Optional[str], provider: Optional[BillingProvider],
    settings: Settings,
) -> None:
    obj = (event.get("data") or {}).get("object") or {}
    sub_id = obj.get("id")
    if not sub_id:
        raise SubscriptionEventError("subscription event names no subscription")
    _store_from_stripe(sub_id, db_path, provider, settings)


def _store_from_stripe(
    sub_id: str, db_path: Optional[str], provider: Optional[BillingProvider],
    settings: Settings,
) -> None:
    """Read the subscription from Stripe and store what it says."""
    if provider is None:
        raise BillingProviderError("no billing provider to re-read the subscription")
    sub = provider.retrieve_subscription(sub_id)
    user_id = _resolve_user_id(sub, db_path)
    if user_id is None:
        raise SubscriptionEventError(
            f"subscription {sub_id}: no user_id in its metadata and no "
            "stored subscription for it or its customer"
        )
    upsert_from_stripe(
        user_id=user_id,
        stripe_subscription_id=sub_id,
        data=subscription_data_from_stripe(sub, settings),
        db_path=db_path,
    )


def _handle_subscription_invoice(
    event: dict, db_path: Optional[str], provider: Optional[BillingProvider],
    settings: Settings,
) -> None:
    """``invoice.paid`` / ``invoice.payment_failed`` for a tier
    subscription: one ``subscription_payments`` row per Stripe invoice.
    A failure never overwrites a payment."""
    inv = (event.get("data") or {}).get("object") or {}
    parent = inv.get("parent") or {}
    sub_id = ((parent.get("subscription_details") or {}).get("subscription")
              if parent.get("type") == "subscription_details" else None)
    if not sub_id:
        return
    existing = get_subscription_by_stripe_id(sub_id, db_path=db_path)
    if existing is None:
        # Bug fix #2: the invoice can arrive before its subscription's
        # event, and `stripe listen` never redelivers a 503. Read the
        # subscription now; if Stripe cannot be read, that raises and the
        # event is retried.
        _store_from_stripe(sub_id, db_path, provider, settings)
        existing = get_subscription_by_stripe_id(sub_id, db_path=db_path)
    paid = event.get("type") == "invoice.paid"
    lines = ((inv.get("lines") or {}).get("data")) or [{}]
    period = lines[0].get("period") or {}
    now = utc_now()
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO subscription_payments
               (user_id, subscription_id, stripe_invoice_id,
                stripe_subscription_id, status, amount_due_cents,
                amount_paid_cents, currency, period_start, period_end,
                livemode, recorded_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(stripe_invoice_id) DO UPDATE SET
                 status = CASE WHEN subscription_payments.status = 'paid'
                               THEN 'paid' ELSE excluded.status END,
                 amount_paid_cents = MAX(subscription_payments.amount_paid_cents,
                                         excluded.amount_paid_cents),
                 updated_at = excluded.updated_at""",
            (
                int(existing["user_id"]), int(existing["id"]), inv["id"], sub_id,
                "paid" if paid else "failed",
                int(inv.get("amount_due") or 0),
                int(inv.get("amount_paid") or 0),
                (inv.get("currency") or "usd").lower(),
                _iso_ts(period.get("start")), _iso_ts(period.get("end")),
                1 if inv.get("livemode") else 0, now, now,
            ),
        )


def _handle_payment_intent(event, db_path, provider, settings) -> None:
    outcome = invoice_payments.apply_payment_intent(event, db_path=db_path)
    logger.info("stripe webhook %s: %s", event.get("id"), outcome)


def _handle_refund(event, db_path, provider, settings) -> None:
    outcome = invoice_payments.apply_refund(event, db_path=db_path)
    logger.info("stripe webhook %s: %s", event.get("id"), outcome)


Handler = Callable[[dict, Optional[str], Optional[BillingProvider], Settings], None]

HANDLERS: dict[str, Handler] = {
    "customer.subscription.created": _handle_subscription,
    "customer.subscription.updated": _handle_subscription,
    "customer.subscription.deleted": _handle_subscription,
    "invoice.paid": _handle_subscription_invoice,
    "invoice.payment_failed": _handle_subscription_invoice,
    "payment_intent.succeeded": _handle_payment_intent,
    "payment_intent.payment_failed": _handle_payment_intent,
    "charge.refunded": _handle_refund,
}

# Failures that mean "Stripe or the order of delivery, try again".
RETRYABLE = (BillingProviderError, stripe_api.StripeUnavailable,
             stripe_api.StripeNotConfigured)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class WebhookDispatchResult:
    """Structured dispatch outcome."""

    def __init__(
        self, received: bool, processed: bool,
        event_id: str, event_type: str,
        error: Optional[str] = None,
        retry: bool = False,
    ) -> None:
        self.received = received
        self.processed = processed
        self.event_id = event_id
        self.event_type = event_type
        self.error = error
        self.retry = retry

    def to_dict(self) -> dict:
        return {
            "received": self.received,
            "processed": self.processed,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "error": self.error,
            "retry": self.retry,
        }


def dispatch_event(
    event: dict, db_path: Optional[str] = None,
    provider: Optional[BillingProvider] = None,
    settings: Optional[Settings] = None,
) -> WebhookDispatchResult:
    """Idempotent, order-independent dispatch.

    - A live event outside prod raises :class:`LiveEventRefused` and is
      not recorded.
    - A repeat event id is acknowledged without its handler.
    - A retryable failure removes the record and returns ``retry=True``.
    - Any other failure is recorded with its error.
    """
    s = settings or get_settings()
    if event.get("livemode") and s.env != Environment.PROD:
        raise LiveEventRefused(
            f"a live-mode event ({event.get('type')}) reached a server with "
            f"env={s.env.value!r}; live payments are row 371"
        )
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "unknown")
    inserted = _record_event(event, db_path=db_path)
    if not inserted:
        return WebhookDispatchResult(
            received=True, processed=False,
            event_id=event_id, event_type=event_type,
        )
    handler = HANDLERS.get(event_type)
    if handler is None:
        logger.info(
            "stripe webhook: unhandled event type %s (id=%s)",
            event_type, event_id,
        )
        _mark_processed(event_id, error=None, db_path=db_path)
        return WebhookDispatchResult(
            received=True, processed=True,
            event_id=event_id, event_type=event_type,
        )
    try:
        handler(event, db_path, provider, s)
    except RETRYABLE as e:
        logger.warning(
            "webhook handler must be retried: event_id=%s type=%s: %s",
            event_id, event_type, e,
        )
        _forget_event(event_id, db_path)
        return WebhookDispatchResult(
            received=True, processed=False,
            event_id=event_id, event_type=event_type,
            error=f"{type(e).__name__}: {e}", retry=True,
        )
    except Exception as e:
        logger.exception(
            "webhook handler failed: event_id=%s type=%s: %s",
            event_id, event_type, e,
        )
        _mark_processed(
            event_id, error=f"{type(e).__name__}: {e}",
            db_path=db_path,
        )
        return WebhookDispatchResult(
            received=True, processed=True,
            event_id=event_id, event_type=event_type,
            error=f"{type(e).__name__}: {e}",
        )
    _mark_processed(event_id, error=None, db_path=db_path)
    return WebhookDispatchResult(
        received=True, processed=True,
        event_id=event_id, event_type=event_type,
    )
