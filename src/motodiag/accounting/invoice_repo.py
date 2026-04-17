"""Invoice + line item repository."""

from typing import Optional

from motodiag.core.database import get_connection
from motodiag.accounting.models import (
    Invoice, InvoiceLineItem, InvoiceStatus, InvoiceLineItemType,
)


# --- Invoice CRUD ---


def create_invoice(invoice: Invoice, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO invoices
               (customer_id, repair_plan_id, invoice_number, status,
                subtotal, tax_amount, total, currency, issued_at, due_at,
                paid_at, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                invoice.customer_id, invoice.repair_plan_id,
                invoice.invoice_number, invoice.status.value,
                invoice.subtotal, invoice.tax_amount, invoice.total,
                invoice.currency,
                invoice.issued_at.isoformat() if invoice.issued_at else None,
                invoice.due_at.isoformat() if invoice.due_at else None,
                invoice.paid_at.isoformat() if invoice.paid_at else None,
                invoice.notes,
            ),
        )
        return cursor.lastrowid


def get_invoice(invoice_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_invoice_by_number(invoice_number: str, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM invoices WHERE invoice_number = ?",
            (invoice_number,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_invoices(
    customer_id: Optional[int] = None,
    status: InvoiceStatus | str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM invoices WHERE 1=1"
    params: list = []
    if customer_id is not None:
        query += " AND customer_id = ?"
        params.append(customer_id)
    if status is not None:
        s = status.value if isinstance(status, InvoiceStatus) else status
        query += " AND status = ?"
        params.append(s)
    query += " ORDER BY created_at DESC, id DESC"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def update_invoice(invoice_id: int, db_path: str | None = None, **fields) -> bool:
    if not fields:
        return False
    if "status" in fields and isinstance(fields["status"], InvoiceStatus):
        fields["status"] = fields["status"].value
    for k in ("issued_at", "due_at", "paid_at"):
        v = fields.get(k)
        if hasattr(v, "isoformat"):
            fields[k] = v.isoformat()
    keys = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [invoice_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE invoices SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def delete_invoice(invoice_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM invoices WHERE id = ?", (invoice_id,),
        )
        return cursor.rowcount > 0


# --- Line items ---


def add_line_item(item: InvoiceLineItem, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO invoice_line_items
               (invoice_id, item_type, description, quantity, unit_price,
                line_total, source_repair_plan_item_id, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.invoice_id, item.item_type.value, item.description,
                item.quantity, item.unit_price, item.line_total,
                item.source_repair_plan_item_id, item.sort_order,
            ),
        )
        return cursor.lastrowid


def get_line_items(invoice_id: int, db_path: str | None = None) -> list[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM invoice_line_items WHERE invoice_id = ? "
            "ORDER BY sort_order, id",
            (invoice_id,),
        )
        return [dict(r) for r in cursor.fetchall()]


def update_line_item(item_id: int, db_path: str | None = None, **fields) -> bool:
    if not fields:
        return False
    if "item_type" in fields and isinstance(fields["item_type"], InvoiceLineItemType):
        fields["item_type"] = fields["item_type"].value
    keys = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [item_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE invoice_line_items SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def delete_line_item(item_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM invoice_line_items WHERE id = ?", (item_id,),
        )
        return cursor.rowcount > 0


def recalculate_invoice_totals(
    invoice_id: int, tax_rate: float = 0.0, db_path: str | None = None,
) -> dict:
    """Sum line_total across all line items, recompute subtotal/tax/total.

    tax_rate is a fraction (e.g., 0.0875 for 8.75%).
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT COALESCE(SUM(line_total), 0) FROM invoice_line_items "
            "WHERE invoice_id = ?",
            (invoice_id,),
        )
        subtotal = cursor.fetchone()[0] or 0.0
        tax_amount = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax_amount, 2)
        conn.execute(
            "UPDATE invoices SET subtotal = ?, tax_amount = ?, total = ? "
            "WHERE id = ?",
            (subtotal, tax_amount, total, invoice_id),
        )
    return {"subtotal": subtotal, "tax_amount": tax_amount, "total": total}
