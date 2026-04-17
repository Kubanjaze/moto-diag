"""Payment repository."""

from typing import Optional

from motodiag.core.database import get_connection
from motodiag.billing.models import Payment, PaymentStatus


def record_payment(payment: Payment, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO payments
               (user_id, subscription_id, amount, currency, status,
                stripe_payment_intent_id, payment_method, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                payment.user_id, payment.subscription_id, payment.amount,
                payment.currency, payment.status.value,
                payment.stripe_payment_intent_id, payment.payment_method,
                payment.notes,
            ),
        )
        return cursor.lastrowid


def get_payment(payment_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM payments WHERE id = ?", (payment_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_payments(
    user_id: Optional[int] = None,
    subscription_id: Optional[int] = None,
    status: PaymentStatus | str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM payments WHERE 1=1"
    params: list = []
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    if subscription_id is not None:
        query += " AND subscription_id = ?"
        params.append(subscription_id)
    if status is not None:
        s = status.value if isinstance(status, PaymentStatus) else status
        query += " AND status = ?"
        params.append(s)
    query += " ORDER BY created_at DESC, id DESC"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def update_payment_status(
    payment_id: int, status: PaymentStatus | str, db_path: str | None = None,
) -> bool:
    s = status.value if isinstance(status, PaymentStatus) else status
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE payments SET status = ? WHERE id = ?", (s, payment_id),
        )
        return cursor.rowcount > 0


def delete_payment(payment_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM payments WHERE id = ?", (payment_id,),
        )
        return cursor.rowcount > 0
