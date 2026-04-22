"""Subscription repository."""

from typing import Optional

from motodiag.core.database import get_connection
from motodiag.billing.models import (
    Subscription, SubscriptionTier, SubscriptionStatus,
)


def create_subscription(sub: Subscription, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, ends_at, stripe_customer_id, stripe_subscription_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                sub.user_id, sub.tier.value, sub.status.value,
                sub.ends_at.isoformat() if sub.ends_at else None,
                sub.stripe_customer_id, sub.stripe_subscription_id,
            ),
        )
        return cursor.lastrowid


def get_subscription(sub_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM subscriptions WHERE id = ?", (sub_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_subscription_by_user(user_id: int, db_path: str | None = None) -> Optional[dict]:
    """Return most recent active/trialing subscription for a user."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT * FROM subscriptions
               WHERE user_id = ? AND status IN ('active', 'trialing')
               ORDER BY started_at DESC LIMIT 1""",
            (user_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_subscriptions(
    user_id: Optional[int] = None,
    status: SubscriptionStatus | str | None = None,
    tier: SubscriptionTier | str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM subscriptions WHERE 1=1"
    params: list = []
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    if status is not None:
        s = status.value if isinstance(status, SubscriptionStatus) else status
        query += " AND status = ?"
        params.append(s)
    if tier is not None:
        t = tier.value if isinstance(tier, SubscriptionTier) else tier
        query += " AND tier = ?"
        params.append(t)
    query += " ORDER BY started_at DESC, id DESC"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def update_subscription(sub_id: int, db_path: str | None = None, **fields) -> bool:
    if not fields:
        return False
    for k in ("tier", "status"):
        v = fields.get(k)
        if hasattr(v, "value"):
            fields[k] = v.value
    if "ends_at" in fields and hasattr(fields["ends_at"], "isoformat"):
        fields["ends_at"] = fields["ends_at"].isoformat()
    keys = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [sub_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE subscriptions SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def delete_subscription(sub_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM subscriptions WHERE id = ?", (sub_id,),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Phase 176 additions: Stripe-aware helpers
# ---------------------------------------------------------------------------


from pydantic import BaseModel, ConfigDict
from typing import Any


class ActiveSubscription(BaseModel):
    """Phase 176 — subscription row projected with Stripe billing fields.

    Distinct from Phase 118 :class:`Subscription` Pydantic (which
    predates the Stripe columns). Returned by
    :func:`get_active_subscription` for routes + dependencies.
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    user_id: int
    tier: str
    status: str
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    stripe_price_id: Optional[str] = None
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False
    canceled_at: Optional[str] = None
    trial_end: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


_ACTIVE_STATUSES: tuple[str, ...] = ("active", "trialing")


def get_active_subscription(
    user_id: int, db_path: Optional[str] = None,
) -> Optional[ActiveSubscription]:
    """Return the user's current active/trialing subscription, or None.

    Preference order if the user somehow has multiple active
    rows (shouldn't happen, but defends against webhook races):
    - highest tier (company > shop > individual)
    - most-recent updated_at / created_at
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            """SELECT * FROM subscriptions
               WHERE user_id = ? AND status IN ('active', 'trialing')
               ORDER BY
                   CASE tier
                       WHEN 'company' THEN 3
                       WHEN 'shop' THEN 2
                       ELSE 1
                   END DESC,
                   COALESCE(updated_at, created_at, started_at) DESC,
                   id DESC
               LIMIT 1""",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return ActiveSubscription(
        id=int(d["id"]),
        user_id=int(d["user_id"]),
        tier=str(d["tier"]),
        status=str(d["status"]),
        stripe_customer_id=d.get("stripe_customer_id"),
        stripe_subscription_id=d.get("stripe_subscription_id"),
        stripe_price_id=d.get("stripe_price_id"),
        current_period_start=d.get("current_period_start"),
        current_period_end=d.get("current_period_end"),
        cancel_at_period_end=bool(d.get("cancel_at_period_end") or 0),
        canceled_at=d.get("canceled_at"),
        trial_end=d.get("trial_end"),
        created_at=d.get("created_at"),
        updated_at=d.get("updated_at"),
    )


def get_subscription_by_stripe_id(
    stripe_subscription_id: str, db_path: Optional[str] = None,
) -> Optional[dict]:
    """Look up by Stripe's subscription id (sub_XXX). Used by
    webhook handlers."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM subscriptions "
            "WHERE stripe_subscription_id = ? LIMIT 1",
            (stripe_subscription_id,),
        ).fetchone()
    return dict(row) if row else None


def upsert_from_stripe(
    user_id: int,
    stripe_subscription_id: str,
    data: dict[str, Any],
    db_path: Optional[str] = None,
) -> int:
    """Create or update a subscription row from a Stripe event payload.

    ``data`` dict keys (all optional except tier/status):
    - tier, status, stripe_customer_id, stripe_price_id,
      current_period_start, current_period_end,
      cancel_at_period_end, canceled_at, trial_end

    Returns the subscription id (existing or newly-created). This is
    the idempotent upsert used by webhook handlers — replaying a
    Stripe event with the same sub id updates in place rather than
    duplicating.
    """
    import json as _json  # only for logging; not stored here

    now = datetime_now_iso()
    existing = get_subscription_by_stripe_id(
        stripe_subscription_id, db_path=db_path,
    )
    with get_connection(db_path) as conn:
        if existing is not None:
            # Update in place
            fields = {k: v for k, v in data.items() if v is not None}
            fields["updated_at"] = now
            if not fields:
                return int(existing["id"])
            keys = ", ".join(f"{k} = ?" for k in fields)
            params = list(fields.values()) + [int(existing["id"])]
            conn.execute(
                f"UPDATE subscriptions SET {keys} WHERE id = ?",
                params,
            )
            return int(existing["id"])
        # Insert new
        cursor = conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, stripe_customer_id,
                stripe_subscription_id, stripe_price_id,
                current_period_start, current_period_end,
                cancel_at_period_end, canceled_at, trial_end,
                started_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                data.get("tier", "individual"),
                data.get("status", "active"),
                data.get("stripe_customer_id"),
                stripe_subscription_id,
                data.get("stripe_price_id"),
                data.get("current_period_start"),
                data.get("current_period_end"),
                1 if data.get("cancel_at_period_end") else 0,
                data.get("canceled_at"),
                data.get("trial_end"),
                now, now,
            ),
        )
        return int(cursor.lastrowid)


def datetime_now_iso() -> str:
    """Local helper so we don't pull datetime into the header of
    every module using this repo."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
