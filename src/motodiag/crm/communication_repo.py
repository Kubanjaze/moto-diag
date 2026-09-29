"""Customer communication log — each contact with a customer, as it happened.

Distinct from ``customer_notifications`` (shop/notifications.py), which is
the queue of outbound template messages the shop generates on work-order
and invoice events. This log is what a service writer records by hand: a
phone call, a conversation at the counter, an email or text either way.
:func:`customer_timeline` shows both, newest first, each labelled with its
source, so neither table has to pretend to be the other.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from motodiag.core.database import get_connection

DIRECTIONS: tuple[str, ...] = ("inbound", "outbound")
CHANNELS: tuple[str, ...] = ("phone", "in_person", "email", "sms", "other")


def log_contact(
    customer_id: int,
    direction: str,
    channel: str,
    summary: str,
    shop_id: Optional[int] = None,
    work_order_id: Optional[int] = None,
    logged_by_user_id: Optional[int] = None,
    occurred_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Record one contact. Returns its id.

    ``occurred_at`` defaults to now (UTC). Raises ``ValueError`` for an
    unknown direction or channel, an empty summary, or a work order that
    belongs to another customer.
    """
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {', '.join(DIRECTIONS)}")
    if channel not in CHANNELS:
        raise ValueError(f"channel must be one of {', '.join(CHANNELS)}")
    if not summary or not summary.strip():
        raise ValueError("a contact needs a summary of what was said")
    when = occurred_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_connection(db_path) as conn:
        if work_order_id is not None:
            wo = conn.execute(
                "SELECT customer_id FROM work_orders WHERE id = ?",
                (work_order_id,),
            ).fetchone()
            if wo is None:
                raise ValueError(f"work order not found: id={work_order_id}")
            if wo["customer_id"] != customer_id:
                raise ValueError(
                    f"work order id={work_order_id} belongs to another customer"
                )
        cursor = conn.execute(
            """INSERT INTO customer_communications
               (customer_id, shop_id, work_order_id, direction, channel,
                summary, logged_by_user_id, occurred_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (customer_id, shop_id, work_order_id, direction, channel,
             summary.strip(), logged_by_user_id, when),
        )
        return cursor.lastrowid


def list_contacts(customer_id: int, db_path: Optional[str] = None) -> list[dict]:
    """Every logged contact for a customer, newest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM customer_communications WHERE customer_id = ? "
            "ORDER BY occurred_at DESC, id DESC",
            (customer_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def customer_timeline(customer_id: int, db_path: Optional[str] = None) -> list[dict]:
    """Logged contacts and queued notifications for a customer, newest first.

    Each entry carries ``source`` (``contact`` or ``notification``), ``at``,
    ``direction``, ``channel``, ``work_order_id`` and ``text``; a
    notification also carries its ``event`` and ``status``.
    """
    entries: list[dict] = []
    for c in list_contacts(customer_id, db_path=db_path):
        entries.append({
            "source": "contact", "id": c["id"], "at": c["occurred_at"],
            "direction": c["direction"], "channel": c["channel"],
            "work_order_id": c["work_order_id"], "text": c["summary"],
        })
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT id, event, channel, status, subject, body, work_order_id, "
            "triggered_at FROM customer_notifications WHERE customer_id = ?",
            (customer_id,),
        ).fetchall()
    for n in rows:
        entries.append({
            "source": "notification", "id": n["id"], "at": n["triggered_at"],
            "direction": "outbound", "channel": n["channel"],
            "work_order_id": n["work_order_id"],
            "text": n["subject"] or n["body"],
            "event": n["event"], "status": n["status"],
        })
    entries.sort(key=lambda e: (str(e["at"]), e["source"], e["id"]), reverse=True)
    return entries
