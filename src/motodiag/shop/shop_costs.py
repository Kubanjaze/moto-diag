"""The shop's direct costs and overheads: what a P&L needs beyond revenue.

Revenue is on the invoices. Three costs are recorded here, because nothing
else holds them:

- **a mechanic's cost rate** (``mechanic_cost_rates``): what an hour of
  that person's time costs the shop, from a date. **This is pay data.** It
  is shown only by the CLI; no API route serves it, and any later one must
  be owner-only.
- **a part line's purchase cost** (``work_order_part_costs``): what the
  shop paid for each unit on a work order's part line. The invoice bills
  the line's own figure, so the two are kept apart.
- **shop expenses** (``shop_expenses``): overheads per month and category.
"""

from __future__ import annotations

import re
from typing import Optional

from motodiag.core.database import get_connection

_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def set_mechanic_cost_rate(
    shop_id: int, user_id: int, cost_cents_per_hour: int, effective_from: str,
    db_path: Optional[str] = None,
) -> int:
    """Record a member's cost rate from ``effective_from`` (YYYY-MM-DD).

    The user must be a member of the shop. A rate for the same date
    replaces the earlier entry for that date.
    """
    if cost_cents_per_hour < 0:
        raise ValueError("a cost rate cannot be negative")
    if not _DATE.match(effective_from):
        raise ValueError("the date must be YYYY-MM-DD")
    with get_connection(db_path) as conn:
        member = conn.execute(
            "SELECT 1 FROM shop_members WHERE shop_id = ? AND user_id = ?",
            (shop_id, user_id),
        ).fetchone()
        if member is None:
            raise ValueError(f"user id={user_id} is not a member of shop id={shop_id}")
        conn.execute(
            "DELETE FROM mechanic_cost_rates WHERE shop_id = ? AND user_id = ? "
            "AND effective_from = ?",
            (shop_id, user_id, effective_from),
        )
        return conn.execute(
            "INSERT INTO mechanic_cost_rates (shop_id, user_id, cost_cents_per_hour, "
            "effective_from) VALUES (?, ?, ?, ?)",
            (shop_id, user_id, cost_cents_per_hour, effective_from),
        ).lastrowid


def list_mechanic_cost_rates(shop_id: int, db_path: Optional[str] = None) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT r.*, u.username FROM mechanic_cost_rates r "
            "JOIN users u ON u.id = r.user_id WHERE r.shop_id = ? "
            "ORDER BY r.user_id, r.effective_from",
            (shop_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def cost_rate_on(rates: list[dict], user_id: int, on_date: str) -> Optional[int]:
    """The rate in force for ``user_id`` on ``on_date``, or None."""
    best = None
    for r in rates:
        if r["user_id"] == user_id and r["effective_from"] <= on_date:
            if best is None or r["effective_from"] > best["effective_from"]:
                best = r
    return None if best is None else int(best["cost_cents_per_hour"])


def set_part_purchase_cost(
    work_order_part_id: int, cents_each: int, db_path: Optional[str] = None,
) -> None:
    """Record what the shop paid per unit on a work order's part line."""
    if cents_each < 0:
        raise ValueError("a purchase cost cannot be negative")
    with get_connection(db_path) as conn:
        line = conn.execute(
            "SELECT 1 FROM work_order_parts WHERE id = ?", (work_order_part_id,),
        ).fetchone()
        if line is None:
            raise ValueError(f"part line not found: id={work_order_part_id}")
        conn.execute(
            "INSERT INTO work_order_part_costs (work_order_part_id, "
            "purchase_cost_cents_each) VALUES (?, ?) "
            "ON CONFLICT(work_order_part_id) DO UPDATE SET "
            "purchase_cost_cents_each = excluded.purchase_cost_cents_each, "
            "recorded_at = CURRENT_TIMESTAMP",
            (work_order_part_id, cents_each),
        )


def add_expense(
    shop_id: int, month: str, category: str, amount_cents: int,
    description: Optional[str] = None, db_path: Optional[str] = None,
) -> int:
    if not _MONTH.match(month):
        raise ValueError("the month must be YYYY-MM")
    if amount_cents < 0:
        raise ValueError("an expense cannot be negative")
    if not category or not category.strip():
        raise ValueError("an expense needs a category")
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO shop_expenses (shop_id, month, category, amount_cents, "
            "description) VALUES (?, ?, ?, ?, ?)",
            (shop_id, month, category.strip(), amount_cents, description),
        ).lastrowid


def list_expenses(
    shop_id: int, months: Optional[list[str]] = None, db_path: Optional[str] = None,
) -> list[dict]:
    query = "SELECT * FROM shop_expenses WHERE shop_id = ?"
    params: list = [shop_id]
    if months:
        query += f" AND month IN ({', '.join('?' * len(months))})"
        params.extend(months)
    query += " ORDER BY month, category, id"
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]
