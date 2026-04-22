"""Stripe webhook event dispatch (Phase 176).

Idempotent: every event is looked up in ``stripe_webhook_events`` by
``event_id``; replays return 200 but skip the handler. This matches
Stripe's retry semantics (they resend on 5xx for up to 3 days).
"""

from __future__ import annotations

import json as _json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from motodiag.billing.subscription_repo import (
    get_subscription_by_stripe_id, upsert_from_stripe,
)
from motodiag.core.database import get_connection


logger = logging.getLogger(__name__)


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
        existing = conn.execute(
            "SELECT event_id FROM stripe_webhook_events "
            "WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        if existing is not None:
            logger.info(
                "stripe webhook replay: event_id=%s (already processed)",
                event_id,
            )
            return False
        conn.execute(
            """INSERT INTO stripe_webhook_events
               (event_id, type, payload_json, received_at)
               VALUES (?, ?, ?, ?)""",
            (
                event_id, event_type, payload,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
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


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _sub_data_from_event(event: dict) -> dict[str, Any]:
    """Extract subscription fields from a Stripe event payload."""
    obj = (event.get("data") or {}).get("object") or {}
    tier = None
    # Tier is encoded in metadata OR derived from price id
    meta = obj.get("metadata") or {}
    if isinstance(meta, dict):
        tier = meta.get("tier")
    # period start/end come as unix timestamps in Stripe
    def _iso_ts(ts):
        if ts is None:
            return None
        try:
            return datetime.fromtimestamp(
                int(ts), tz=timezone.utc,
            ).isoformat()
        except (ValueError, TypeError, OSError):
            return None

    return {
        "tier": tier,
        "status": obj.get("status"),
        "stripe_customer_id": obj.get("customer"),
        "stripe_price_id": (
            (obj.get("items") or {}).get("data") or [{}]
        )[0].get("price", {}).get("id") if obj.get("items") else None,
        "current_period_start": _iso_ts(
            obj.get("current_period_start"),
        ),
        "current_period_end": _iso_ts(
            obj.get("current_period_end"),
        ),
        "cancel_at_period_end": bool(
            obj.get("cancel_at_period_end") or False,
        ),
        "canceled_at": _iso_ts(obj.get("canceled_at")),
        "trial_end": _iso_ts(obj.get("trial_end")),
    }


def _resolve_user_id(event: dict, db_path: Optional[str]) -> Optional[int]:
    """Find the motodiag user_id for this event.

    Looks at:
    1. metadata.user_id (preferred — set at checkout time)
    2. customer_id → existing subscription → user_id

    Returns None when unresolvable; handler logs + skips.
    """
    obj = (event.get("data") or {}).get("object") or {}
    meta = obj.get("metadata") or {}
    if isinstance(meta, dict) and "user_id" in meta:
        try:
            return int(meta["user_id"])
        except (ValueError, TypeError):
            pass
    # Fall back: look up by stripe_customer_id
    customer_id = obj.get("customer")
    if customer_id:
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT user_id FROM subscriptions "
                "WHERE stripe_customer_id = ? LIMIT 1",
                (customer_id,),
            ).fetchone()
            if row is not None:
                return int(row["user_id"])
    # Fall back again: look up by stripe_subscription_id
    sub_id = obj.get("id")
    if sub_id and isinstance(sub_id, str) and sub_id.startswith("sub_"):
        existing = get_subscription_by_stripe_id(sub_id, db_path=db_path)
        if existing is not None:
            return int(existing["user_id"])
    return None


def _handle_subscription_created_or_updated(
    event: dict, db_path: Optional[str],
) -> None:
    obj = (event.get("data") or {}).get("object") or {}
    sub_id = obj.get("id")
    if not sub_id:
        logger.warning("subscription event missing sub id: %s", event.get("id"))
        return
    user_id = _resolve_user_id(event, db_path)
    if user_id is None:
        logger.warning(
            "could not resolve user for event %s (sub %s) — skipping",
            event.get("id"), sub_id,
        )
        return
    data = _sub_data_from_event(event)
    # Provide defensible defaults when Stripe's payload omits values
    if not data.get("status"):
        data["status"] = "active"
    if not data.get("tier"):
        data["tier"] = "individual"
    upsert_from_stripe(
        user_id=user_id,
        stripe_subscription_id=sub_id,
        data=data,
        db_path=db_path,
    )


def _handle_subscription_deleted(
    event: dict, db_path: Optional[str],
) -> None:
    obj = (event.get("data") or {}).get("object") or {}
    sub_id = obj.get("id")
    if not sub_id:
        return
    existing = get_subscription_by_stripe_id(sub_id, db_path=db_path)
    if existing is None:
        return
    now_iso = datetime.now(timezone.utc).isoformat()
    from motodiag.billing.subscription_repo import update_subscription
    update_subscription(
        int(existing["id"]),
        db_path=db_path,
        status="canceled",
        canceled_at=now_iso,
        updated_at=now_iso,
    )


def _handle_payment_succeeded(
    event: dict, db_path: Optional[str],
) -> None:
    # Nothing to mutate in Phase 176 — Phase 176 doesn't track
    # individual payments; Phase 118 `payments` table is updated
    # separately when Phase 182 wires up invoicing webhooks.
    logger.info(
        "invoice.payment_succeeded event_id=%s (noop)",
        event.get("id"),
    )


def _handle_payment_failed(
    event: dict, db_path: Optional[str],
) -> None:
    # Same as _payment_succeeded — noop for Phase 176. Subscription
    # status will transition to past_due via customer.subscription.updated.
    logger.info(
        "invoice.payment_failed event_id=%s (noop)", event.get("id"),
    )


HANDLERS: dict[str, Callable[[dict, Optional[str]], None]] = {
    "customer.subscription.created":
        _handle_subscription_created_or_updated,
    "customer.subscription.updated":
        _handle_subscription_created_or_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "invoice.payment_succeeded": _handle_payment_succeeded,
    "invoice.payment_failed": _handle_payment_failed,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class WebhookDispatchResult:
    """Structured dispatch outcome."""

    def __init__(
        self, received: bool, processed: bool,
        event_id: str, event_type: str,
        error: Optional[str] = None,
    ) -> None:
        self.received = received
        self.processed = processed
        self.event_id = event_id
        self.event_type = event_type
        self.error = error

    def to_dict(self) -> dict:
        return {
            "received": self.received,
            "processed": self.processed,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "error": self.error,
        }


def dispatch_event(
    event: dict, db_path: Optional[str] = None,
) -> WebhookDispatchResult:
    """Idempotent dispatch.

    - Inserts the event into ``stripe_webhook_events`` (returns
      duplicate=False on first insert, True on replay).
    - Skips the handler if duplicate.
    - On handler success: stamps ``processed_at``.
    - On handler failure: stamps ``processed_at`` with ``error``
      text; does NOT re-raise (the webhook response is still 200
      so Stripe doesn't retry — we prefer clean audit trail with
      error column over infinite retry on bad data).
    """
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
        handler(event, db_path)
        _mark_processed(event_id, error=None, db_path=db_path)
        return WebhookDispatchResult(
            received=True, processed=True,
            event_id=event_id, event_type=event_type,
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
