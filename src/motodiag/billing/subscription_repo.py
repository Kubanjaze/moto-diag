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
