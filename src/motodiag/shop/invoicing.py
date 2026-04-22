"""Revenue tracking + invoicing (Phase 169).

Generates invoices from completed Phase 161 work orders. Reuses Phase 118
``invoices`` + ``invoice_line_items`` tables + ``accounting.invoice_repo``
CRUD — zero schema duplication. Micro-migration 033 adds a single
``invoices.work_order_id`` column (soft FK; repo-layer validated).

Line-item composition pulls Phase 165 ``work_order_parts`` (installed +
received rows) for parts lines and Phase 167 WO.actual_hours (fallback
to estimated_hours) for the labor line. Tax + shop supplies + optional
diagnostic fee stack on top. No AI, no token spend.

Cents / dollars convention
--------------------------
- Public API *inputs* and Pydantic summary *outputs* are **cents** (int).
- Phase 118 ``invoices``/``invoice_line_items`` tables store **dollars**
  (REAL). The module converts at the boundary.
- Phase 118 ``InvoiceStatus`` enum uses ``"sent"`` + ``"cancelled"``; we
  surface those as the public "issued"/"void" equivalents and map at
  write time.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from motodiag.accounting.invoice_repo import (
    add_line_item,
    create_invoice,
    get_invoice as _get_invoice_row,
    get_line_items,
    update_invoice as _update_invoice,
)
from motodiag.accounting.models import (
    Invoice,
    InvoiceLineItem,
    InvoiceLineItemType,
    InvoiceStatus as _AccountingInvoiceStatus,
)
from motodiag.core.database import get_connection
from motodiag.shop.work_order_repo import require_work_order


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InvoiceGenerationError(ValueError):
    """Raised when an invoice cannot be generated (WO not completed,
    duplicate invoice exists, missing labor rate, etc.)."""


class InvoiceNotFoundError(ValueError):
    """Raised when an invoice id does not resolve."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


INVOICE_STATUSES: tuple[str, ...] = (
    "draft", "sent", "paid", "overdue", "cancelled",
)


InvoiceStatus = Literal["draft", "sent", "paid", "overdue", "cancelled"]


# ---------------------------------------------------------------------------
# Pydantic
# ---------------------------------------------------------------------------


class InvoiceLineItemSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    item_type: str
    description: str
    quantity: float
    unit_price_cents: int
    line_total_cents: int


class InvoiceSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    invoice_number: str
    work_order_id: Optional[int]
    customer_id: Optional[int]
    customer_name: Optional[str]
    status: str
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    issued_at: Optional[str]
    due_at: Optional[str]
    paid_at: Optional[str]
    notes: Optional[str]
    items: list[InvoiceLineItemSummary] = Field(default_factory=list)


class RevenueRollup(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shop_id: Optional[int]
    since: Optional[str]
    invoice_count: int
    total_invoiced_cents: int
    total_paid_cents: int
    total_pending_cents: int
    by_status: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cents_to_dollars(cents: int) -> float:
    return round(int(cents) / 100.0, 2)


def _dollars_to_cents(dollars) -> int:
    return int(round(float(dollars or 0.0) * 100))


def _lookup_labor_rate_cents(
    shop_id: int, db_path: Optional[str] = None,
) -> Optional[int]:
    """Look up an hourly labor rate from Phase G ``labor_rates``.

    Tries the shop's state, then 'national', then any first row. Returns
    cents per hour or None when the table is empty.
    """
    with get_connection(db_path) as conn:
        shop = conn.execute(
            "SELECT state FROM shops WHERE id = ?", (shop_id,),
        ).fetchone()
        shop_state = shop["state"] if shop else None
        if shop_state:
            row = conn.execute(
                "SELECT hourly_rate FROM labor_rates WHERE state = ? "
                "ORDER BY effective_date DESC LIMIT 1",
                (shop_state,),
            ).fetchone()
            if row is not None:
                return int(round(float(row["hourly_rate"]) * 100))
        row = conn.execute(
            "SELECT hourly_rate FROM labor_rates "
            "WHERE rate_type = 'national' ORDER BY effective_date DESC "
            "LIMIT 1",
        ).fetchone()
        if row is not None:
            return int(round(float(row["hourly_rate"]) * 100))
        row = conn.execute(
            "SELECT hourly_rate FROM labor_rates "
            "ORDER BY effective_date DESC LIMIT 1",
        ).fetchone()
        if row is not None:
            return int(round(float(row["hourly_rate"]) * 100))
    return None


def _check_existing_invoice(
    wo_id: int, db_path: Optional[str] = None,
) -> Optional[int]:
    """Return existing non-cancelled invoice id for wo_id, or None."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM invoices WHERE work_order_id = ? "
            "AND status != 'cancelled' LIMIT 1",
            (wo_id,),
        ).fetchone()
        return int(row["id"]) if row else None


def _format_invoice_number(
    shop_id: int, wo_id: int, now: datetime,
    db_path: Optional[str] = None,
) -> str:
    base = f"INV-{shop_id}-{wo_id}-{now.strftime('%Y%m%d')}"
    # Count existing invoices for this WO (including cancelled); suffix
    # regeneration index so voided+regenerated WOs don't collide on
    # invoices.invoice_number UNIQUE.
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM invoices WHERE work_order_id = ?",
            (wo_id,),
        ).fetchone()
    n = int(row["n"]) if row else 0
    if n == 0:
        return base
    return f"{base}-R{n}"


def _get_customer_name(
    customer_id: Optional[int], db_path: Optional[str] = None,
) -> Optional[str]:
    if customer_id is None:
        return None
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT name FROM customers WHERE id = ?", (customer_id,),
        ).fetchone()
        return row["name"] if row else None


def _load_installed_parts(
    wo_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """Phase 165 installed/received parts lines for an invoice."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT wop.id AS wop_id, wop.quantity, wop.status,
                      wop.unit_cost_cents_override,
                      p.slug, p.description, p.brand, p.typical_cost_cents
               FROM work_order_parts wop
               JOIN parts p ON p.id = wop.part_id
               WHERE wop.work_order_id = ?
                 AND wop.status IN ('received', 'installed')
               ORDER BY wop.id""",
            (wo_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            override = d.get("unit_cost_cents_override")
            unit_cents = (
                int(override) if override is not None
                else int(d.get("typical_cost_cents") or 0)
            )
            d["effective_unit_cents"] = unit_cents
            out.append(d)
        return out


def _add_line_cents(
    invoice_id: int,
    item_type: InvoiceLineItemType,
    description: str,
    quantity: float,
    unit_price_cents: int,
    sort_order: int,
    db_path: Optional[str] = None,
) -> int:
    """Add a single line item, converting cents → dollars at the boundary."""
    line_total_cents = int(round(quantity * unit_price_cents))
    add_line_item(
        InvoiceLineItem(
            invoice_id=invoice_id,
            item_type=item_type,
            description=description,
            quantity=max(0.0001, float(quantity)),
            unit_price=_cents_to_dollars(unit_price_cents),
            line_total=_cents_to_dollars(line_total_cents),
            source_repair_plan_item_id=None,
            sort_order=sort_order,
        ),
        db_path=db_path,
    )
    return line_total_cents


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_invoice_for_wo(
    wo_id: int,
    tax_rate: float = 0.0,
    shop_supplies_pct: float = 0.0,
    shop_supplies_flat_cents: int = 0,
    diagnostic_fee_cents: int = 0,
    labor_hourly_rate_cents: Optional[int] = None,
    notes: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Build an invoice from a completed work order. Returns new invoice_id.

    Raises :class:`InvoiceGenerationError` when:
    - WO is not completed
    - WO has no customer_id (required by Phase 118 invoices.customer_id FK)
    - an invoice already exists for this WO (idempotency)
    - no actual_hours AND no estimated_hours to bill labor against
    - no labor rate available (table empty AND no kwarg)

    Writes to ``invoices`` + ``invoice_line_items`` via Phase 118
    ``accounting.invoice_repo``. Patches ``invoices.work_order_id`` post-insert
    (Phase 118 Invoice model predates the column).
    """
    wo = require_work_order(wo_id, db_path=db_path)
    if wo["status"] != "completed":
        raise InvoiceGenerationError(
            f"work order id={wo_id} is {wo['status']!r}; only completed "
            "WOs can be invoiced"
        )

    customer_id = wo.get("customer_id")
    if customer_id is None:
        raise InvoiceGenerationError(
            f"work order id={wo_id} has no customer_id; link a customer "
            "before invoicing"
        )

    existing = _check_existing_invoice(wo_id, db_path=db_path)
    if existing is not None:
        raise InvoiceGenerationError(
            f"invoice id={existing} already exists for work order id={wo_id}; "
            "void or mark-paid before regenerating"
        )

    if tax_rate < 0 or tax_rate > 1:
        raise ValueError(f"tax_rate must be 0-1 (got {tax_rate})")
    if shop_supplies_pct < 0 or shop_supplies_pct > 1:
        raise ValueError(
            f"shop_supplies_pct must be 0-1 (got {shop_supplies_pct})"
        )

    # Resolve labor rate
    if labor_hourly_rate_cents is None:
        labor_hourly_rate_cents = _lookup_labor_rate_cents(
            wo["shop_id"], db_path=db_path,
        )
    if labor_hourly_rate_cents is None:
        raise InvoiceGenerationError(
            "no labor rate available — labor_rates table is empty and "
            "labor_hourly_rate_cents not supplied; seed labor_rates or "
            "pass the rate explicitly"
        )

    # Determine labor hours (actual preferred, estimated fallback)
    hours = wo.get("actual_hours")
    if hours is None:
        hours = wo.get("estimated_hours")
    if hours is None or float(hours) <= 0:
        raise InvoiceGenerationError(
            f"work order id={wo_id} has no labor hours (actual_hours and "
            "estimated_hours both empty); cannot generate labor line"
        )
    hours = float(hours)

    # Load parts
    parts_lines = _load_installed_parts(wo_id, db_path=db_path)

    # Create invoice header (subtotal/tax/total set after line items)
    now = datetime.now(timezone.utc)
    invoice = Invoice(
        customer_id=int(customer_id),
        repair_plan_id=None,
        invoice_number=_format_invoice_number(
            wo["shop_id"], wo_id, now, db_path=db_path,
        ),
        status=_AccountingInvoiceStatus.SENT,
        subtotal=0.0, tax_amount=0.0, total=0.0,
        currency="USD",
        issued_at=now,
        due_at=None, paid_at=None,
        notes=notes,
    )
    invoice_id = create_invoice(invoice, db_path=db_path)

    # Patch work_order_id post-insert (Phase 118 model predates the column)
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE invoices SET work_order_id = ? WHERE id = ?",
            (wo_id, invoice_id),
        )

    subtotal_cents = 0

    # --- Labor line ---
    subtotal_cents += _add_line_cents(
        invoice_id,
        InvoiceLineItemType.LABOR,
        f"Labor — {hours:.2f}h × ${labor_hourly_rate_cents / 100:.2f}/h",
        hours,
        labor_hourly_rate_cents,
        sort_order=10,
        db_path=db_path,
    )

    # --- Parts lines ---
    sort = 20
    for part in parts_lines:
        qty = int(part.get("quantity", 1) or 1)
        if qty <= 0:
            continue
        unit_cents = int(part.get("effective_unit_cents", 0) or 0)
        desc_parts = [
            (part.get("brand") or "").strip(),
            (part.get("description") or part.get("slug") or "?").strip(),
        ]
        desc = " ".join(p for p in desc_parts if p) or "Part"
        subtotal_cents += _add_line_cents(
            invoice_id,
            InvoiceLineItemType.PARTS,
            desc,
            float(qty),
            unit_cents,
            sort_order=sort,
            db_path=db_path,
        )
        sort += 1

    # --- Optional diagnostic line ---
    if diagnostic_fee_cents and diagnostic_fee_cents > 0:
        subtotal_cents += _add_line_cents(
            invoice_id,
            InvoiceLineItemType.DIAGNOSTIC,
            "Diagnostic fee",
            1.0,
            int(diagnostic_fee_cents),
            sort_order=sort,
            db_path=db_path,
        )
        sort += 1

    # --- Optional shop supplies line (pct applies to pre-supplies subtotal) ---
    supplies_cents = 0
    if shop_supplies_pct > 0:
        supplies_cents += int(round(subtotal_cents * shop_supplies_pct))
    if shop_supplies_flat_cents and shop_supplies_flat_cents > 0:
        supplies_cents += int(shop_supplies_flat_cents)
    if supplies_cents > 0:
        subtotal_cents += _add_line_cents(
            invoice_id,
            InvoiceLineItemType.MISC,
            "Shop supplies",
            1.0,
            supplies_cents,
            sort_order=sort,
            db_path=db_path,
        )

    # --- Tax + totals ---
    tax_cents = int(round(subtotal_cents * tax_rate))
    total_cents = subtotal_cents + tax_cents

    _update_invoice(
        invoice_id, db_path=db_path,
        subtotal=_cents_to_dollars(subtotal_cents),
        tax_amount=_cents_to_dollars(tax_cents),
        total=_cents_to_dollars(total_cents),
    )
    return invoice_id


def mark_invoice_paid(
    invoice_id: int, paid_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Set invoices.status='paid' + paid_at timestamp."""
    row = _get_invoice_row(invoice_id, db_path=db_path)
    if row is None:
        raise InvoiceNotFoundError(f"invoice not found: id={invoice_id}")
    stamp = paid_at or datetime.now(timezone.utc).isoformat()
    _update_invoice(
        invoice_id, db_path=db_path,
        status=_AccountingInvoiceStatus.PAID,
        paid_at=stamp,
    )
    return True


def void_invoice(
    invoice_id: int, reason: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Mark an invoice cancelled (allows regeneration for the WO).

    Phase 118's enum calls this state ``"cancelled"``; the CLI surfaces
    it as "void" for mechanic-friendly vocabulary.
    """
    row = _get_invoice_row(invoice_id, db_path=db_path)
    if row is None:
        raise InvoiceNotFoundError(f"invoice not found: id={invoice_id}")
    notes = row.get("notes") or ""
    if reason:
        notes = (notes + f" | VOID: {reason}").strip(" |")
    _update_invoice(
        invoice_id, db_path=db_path,
        status=_AccountingInvoiceStatus.CANCELLED,
        notes=notes,
    )
    return True


def get_invoice_with_items(
    invoice_id: int, db_path: Optional[str] = None,
) -> Optional[InvoiceSummary]:
    """Load invoice header + items + customer name."""
    row = _get_invoice_row(invoice_id, db_path=db_path)
    if row is None:
        return None
    items_rows = get_line_items(invoice_id, db_path=db_path)
    items = [
        InvoiceLineItemSummary(
            id=int(i["id"]),
            item_type=i["item_type"],
            description=i.get("description") or "",
            quantity=float(i.get("quantity") or 0),
            unit_price_cents=_dollars_to_cents(i.get("unit_price")),
            line_total_cents=_dollars_to_cents(i.get("line_total")),
        )
        for i in items_rows
    ]
    customer_name = _get_customer_name(
        row.get("customer_id"), db_path=db_path,
    )
    return InvoiceSummary(
        id=int(row["id"]),
        invoice_number=row.get("invoice_number") or "",
        work_order_id=row.get("work_order_id"),
        customer_id=row.get("customer_id"),
        customer_name=customer_name,
        status=row.get("status") or "draft",
        subtotal_cents=_dollars_to_cents(row.get("subtotal")),
        tax_cents=_dollars_to_cents(row.get("tax_amount")),
        total_cents=_dollars_to_cents(row.get("total")),
        issued_at=row.get("issued_at"),
        due_at=row.get("due_at"),
        paid_at=row.get("paid_at"),
        notes=row.get("notes"),
        items=items,
    )


def list_invoices_for_shop(
    shop_id: int,
    status: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List invoices whose WO belongs to shop_id.

    Invoices with no ``work_order_id`` (pre-Phase 169) are NOT returned —
    this function only surfaces shop-scoped WO-linked invoices.
    """
    if status is not None and status not in INVOICE_STATUSES:
        raise ValueError(f"status must be one of {INVOICE_STATUSES}")
    query = (
        "SELECT inv.*, wo.shop_id AS wo_shop_id "
        "FROM invoices inv "
        "JOIN work_orders wo ON wo.id = inv.work_order_id "
        "WHERE wo.shop_id = ?"
    )
    params: list = [shop_id]
    if status is not None:
        query += " AND inv.status = ?"
        params.append(status)
    if since:
        query += " AND inv.issued_at >= ?"
        params.append(since)
    query += " ORDER BY inv.issued_at DESC, inv.id DESC"
    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(int(limit))
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["subtotal_cents"] = _dollars_to_cents(d.get("subtotal"))
            d["tax_cents"] = _dollars_to_cents(d.get("tax_amount"))
            d["total_cents"] = _dollars_to_cents(d.get("total"))
            out.append(d)
        return out


def revenue_rollup(
    shop_id: Optional[int] = None,
    since: Optional[str] = None,
    db_path: Optional[str] = None,
) -> RevenueRollup:
    """Aggregate invoice totals by status for the shop dashboard.

    Scopes by ``wo.shop_id`` when ``shop_id`` is provided (invoices
    without a work_order_id are excluded in that case). When
    ``shop_id`` is None, rolls up across all invoices in the DB.
    """
    if shop_id is not None:
        base = (
            "FROM invoices inv "
            "JOIN work_orders wo ON wo.id = inv.work_order_id"
        )
        conditions = ["wo.shop_id = ?"]
        params: list = [shop_id]
    else:
        base = "FROM invoices inv"
        conditions = []
        params = []
    if since:
        conditions.append("inv.issued_at >= ?")
        params.append(since)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    paid_conditions = conditions + ["inv.status = 'paid'"]
    paid_where = " WHERE " + " AND ".join(paid_conditions)
    paid_params = list(params)

    with get_connection(db_path) as conn:
        total_row = conn.execute(
            f"SELECT COUNT(*) AS n, "
            f"       COALESCE(SUM(inv.total), 0.0) AS total_invoiced "
            f"{base}{where}",
            params,
        ).fetchone()
        paid_row = conn.execute(
            f"SELECT COALESCE(SUM(inv.total), 0.0) AS paid {base}{paid_where}",
            paid_params,
        ).fetchone()
        by_status_rows = conn.execute(
            f"SELECT inv.status, COUNT(*) AS n {base}{where} "
            f"GROUP BY inv.status",
            params,
        ).fetchall()

    total_invoiced_cents = _dollars_to_cents(
        total_row["total_invoiced"] if total_row else 0.0
    )
    total_paid_cents = _dollars_to_cents(
        paid_row["paid"] if paid_row else 0.0
    )
    by_status = {r["status"]: int(r["n"]) for r in by_status_rows}
    return RevenueRollup(
        shop_id=shop_id,
        since=since,
        invoice_count=int(total_row["n"]) if total_row else 0,
        total_invoiced_cents=total_invoiced_cents,
        total_paid_cents=total_paid_cents,
        total_pending_cents=max(0, total_invoiced_cents - total_paid_cents),
        by_status=by_status,
    )
