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
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from motodiag.accounting import exchange
from motodiag.accounting import tax as tax_mod
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


class InvoiceTaxNotOnRecord(InvoiceGenerationError):
    """Raised when the shop's tax is not on record for the invoice date
    (Phase 281, F184): no jurisdiction, no valid rate, or no rule for a line
    type the invoice carries. The API answers 409."""


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
    # Phase 281: what the tax came from, and any conversion (NULL on
    # invoices made before either was recorded).
    currency: Optional[str] = None
    tax_rate: Optional[float] = None
    tax_source: Optional[str] = None
    tax_recheck_by: Optional[str] = None
    taxed_line_types: Optional[str] = None
    fx_from_currency: Optional[str] = None
    fx_rate: Optional[str] = None
    fx_rate_date: Optional[str] = None
    fx_source: Optional[str] = None


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
        # Phase 373: a settled claim's shortfall invoice is not the order's invoice.
        row = conn.execute(
            "SELECT id FROM invoices WHERE work_order_id = ? "
            "AND status != 'cancelled' AND shortfall_claim_id IS NULL LIMIT 1",
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


def _line_total_cents(quantity: float, unit_price_cents: int) -> int:
    """A line's total in cents: the one rounding every line uses."""
    return int(round(quantity * unit_price_cents))


# ---------------------------------------------------------------------------
# Phase 373: the warranty claims on a work order
# ---------------------------------------------------------------------------


def _claims_on_wo(wo_id: int, db_path: Optional[str] = None) -> list[dict]:
    """The work order's claims that are not denied, each with its covered
    lines, and its warranty's payer and provider. A settled claim counts
    whatever its status: its shortfall was billed or absorbed on its own, so
    its lines stay off the order's invoice when that is generated again."""
    with get_connection(db_path) as conn:
        claims = [dict(r) for r in conn.execute(
            "SELECT c.*, w.repair_payer, w.provider FROM warranty_claims c "
            "JOIN warranties w ON w.id = c.warranty_id WHERE c.work_order_id = ? "
            "AND (c.status != 'denied' OR c.settlement IS NOT NULL) ORDER BY c.id",
            (wo_id,),
        ).fetchall()]
        for claim in claims:
            claim["lines"] = [dict(r) for r in conn.execute(
                "SELECT * FROM warranty_claim_lines WHERE claim_id = ? ORDER BY id",
                (claim["id"],),
            ).fetchall()]
    return claims


def _hours_left(hours: float, covered: float) -> float:
    return float(Decimal(str(hours)) - Decimal(str(covered)))


def _price_claims(
    wo_id: int,
    hours: float,
    rate_cents: int,
    parts_lines: list[dict],
    unit_cents_by_wop: dict[int, int],
    decision,
    shop_id: int,
    invoice_day,
    db_path: Optional[str] = None,
) -> tuple[list[dict], float, dict[int, int]]:
    """Price each claim on the work order, before anything is written.

    Returns the priced claims, the labour hours they cover, and the parts
    quantities they cover by work-order part row. Raises
    :class:`InvoiceGenerationError` when a claim's coverage is not recorded
    or covers more than the order holds, and :class:`InvoiceTaxNotOnRecord`
    when no rule says whether its tax goes on the claim.
    """
    claims = _claims_on_wo(wo_id, db_path=db_path)
    covered_hours = 0.0
    covered_qty: dict[int, int] = {}
    on_order = {int(p["wop_id"]): int(p.get("quantity", 1) or 1) for p in parts_lines}
    for claim in claims:
        if claim["coverage_recorded_at"] is None:
            raise InvoiceGenerationError(
                f"warranty claim #{claim['id']} on work order id={wo_id} does not say "
                f"which lines it covers; record them with `motodiag shop warranty "
                f"claim cover {claim['id']}` (or `--none`) before invoicing"
            )
        for line in claim["lines"]:
            if line["line_type"] == "labor":
                covered_hours = float(Decimal(str(covered_hours))
                                      + Decimal(str(line["quantity"])))
                continue
            wop_id = int(line["work_order_part_id"])
            if wop_id not in on_order:
                raise InvoiceGenerationError(
                    f"warranty claim #{claim['id']} covers part row {wop_id}, which "
                    f"is not received or installed on work order id={wo_id}"
                )
            covered_qty[wop_id] = covered_qty.get(wop_id, 0) + int(line["quantity"])
    if covered_hours > hours:
        raise InvoiceGenerationError(
            f"the claims on work order id={wo_id} cover {covered_hours:g} h of labour; "
            f"the order bills {hours:g} h"
        )
    for wop_id, qty in covered_qty.items():
        if qty > on_order[wop_id]:
            raise InvoiceGenerationError(
                f"the claims on work order id={wo_id} cover {qty} of part row "
                f"{wop_id}; the order holds {on_order[wop_id]}"
            )

    rate = Decimal(str(decision.rate.value))
    for claim in claims:
        by_type = {"labor": 0, "parts": 0}
        for line in claim["lines"]:
            unit = (rate_cents if line["line_type"] == "labor"
                    else unit_cents_by_wop[int(line["work_order_part_id"])])
            line["amount_cents"] = _line_total_cents(float(line["quantity"]), unit)
            by_type[line["line_type"]] += line["amount_cents"]
        claim["covered_cents"] = by_type["labor"] + by_type["parts"]
        claim["tax_cents"] = 0
        claim["tax_source"] = None
        if claim["lines"] and claim["repair_payer"] is None:
            raise InvoiceGenerationError(
                f"warranty claim #{claim['id']}'s warranty does not record who owes the "
                f"repair; record it with `motodiag shop warranty update "
                f"{claim['warranty_id']} --payer …`"
            )
        if claim["lines"]:
            try:
                rule = tax_mod.resolve_warranty_rule(shop_id, invoice_day,
                                                     claim["repair_payer"],
                                                     db_path=db_path)
            except tax_mod.TaxNotOnRecord as exc:
                raise InvoiceTaxNotOnRecord(str(exc)) from exc
            claim["tax_source"] = rule.source_text
            if rule.value:
                taxable = sum(by_type[t] for t in by_type if t in decision.taxable_types)
                claim["tax_cents"] = int((Decimal(taxable) * rate)
                                         .quantize(Decimal(1), ROUND_HALF_UP))
        claim["amount"] = claim["covered_cents"] + claim["tax_cents"]
        old = claim.get("amount_claimed_cents")
        if claim["status"] != "draft" and old is not None and old != claim["amount"]:
            raise InvoiceGenerationError(
                f"warranty claim #{claim['id']} is {claim['status']} at {old} cents; "
                f"this invoice would price it at {claim['amount']} cents"
            )
    return claims, covered_hours, covered_qty


def _claim_note(claim: dict) -> str:
    parts = [line["description"] or line["line_type"] for line in claim["lines"]]
    return f"Warranty claim #{claim['id']} covers: {'; '.join(parts)}"


def _split_cents(total: int, weights: list[int]) -> list[int]:
    """``total`` over ``weights`` in proportion, by largest remainder: the
    shares sum to ``total`` exactly, and a tie goes to the earlier line."""
    whole = sum(weights)
    if whole == 0:
        return [0 for _ in weights]
    exact = [Decimal(total) * w / whole for w in weights]
    shares = [int(x) for x in exact]
    order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - shares[i]), i))
    for i in order[: total - sum(shares)]:
        shares[i] += 1
    return shares


def _record_claim_prices(claims: list[dict], invoice_id: int,
                         db_path: Optional[str] = None) -> None:
    with get_connection(db_path) as conn:
        for claim in claims:
            for line in claim["lines"]:
                conn.execute(
                    "UPDATE warranty_claim_lines SET amount_cents = ? WHERE id = ?",
                    (line["amount_cents"], line["id"]),
                )
            conn.execute(
                "UPDATE warranty_claims SET invoice_id = ?, covered_cents = ?, "
                "tax_cents = ?, tax_source = ?, amount_claimed_cents = ? WHERE id = ?",
                (invoice_id, claim["covered_cents"], claim["tax_cents"],
                 claim["tax_source"], claim["amount"], claim["id"]),
            )


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
    line_total_cents = _line_total_cents(quantity, unit_price_cents)
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
    shop_supplies_pct: float = 0.0,
    shop_supplies_flat_cents: int = 0,
    diagnostic_fee_cents: int = 0,
    labor_hourly_rate_cents: Optional[int] = None,
    notes: Optional[str] = None,
    currency: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Build an invoice from a completed work order. Returns new invoice_id.

    Raises :class:`InvoiceGenerationError` when:
    - WO is not completed
    - WO has no customer_id (required by Phase 118 invoices.customer_id FK)
    - an invoice already exists for this WO (idempotency)
    - no actual_hours AND no estimated_hours to bill labor against
    - no labor rate available (table empty AND no kwarg)
    - the shop's tax is not on record for today (Phase 281, F184): no
      jurisdiction, no valid rate, or no rule for a line type it carries
    - ``currency`` differs from the shop's and the shop has no rate of its
      own for it (ECB reference rates never convert an invoice)

    Tax comes only from the shop's jurisdiction on record, on the taxable
    lines only, and the invoice records the rate, its source and the date it
    must be re-checked by. Nothing is written when any check refuses.

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

    # Phase 281: the tax, and any conversion, are settled before anything is
    # written, so a refusal leaves no half-built invoice.
    line_types = {"labor"}
    if any(int(p.get("quantity", 1) or 1) > 0 for p in parts_lines):
        line_types.add("parts")
    if diagnostic_fee_cents and diagnostic_fee_cents > 0:
        line_types.add("diagnostic")
    if shop_supplies_pct > 0 or (shop_supplies_flat_cents and shop_supplies_flat_cents > 0):
        line_types.add("misc")
    invoice_day = tax_mod.today()
    try:
        decision = tax_mod.resolve_tax(wo["shop_id"], invoice_day, line_types,
                                       db_path=db_path)
    except tax_mod.TaxNotOnRecord as exc:
        raise InvoiceTaxNotOnRecord(str(exc)) from exc
    invoice_currency = decision.currency
    fx_rate_row: Optional[dict] = None
    if currency and currency.strip().upper() != decision.currency:
        invoice_currency = currency.strip().upper()
        fx_rate_row = exchange.shop_rate(wo["shop_id"], decision.currency,
                                         invoice_currency, invoice_day, db_path=db_path)
        if fx_rate_row is None:
            raise InvoiceGenerationError(
                f"no rate of the shop's own converts {decision.currency} to "
                f"{invoice_currency} on {invoice_day}; record one with `motodiag shop "
                f"currency set --shop {wo['shop_id']} --from {decision.currency} --to "
                f"{invoice_currency}`. ECB reference rates are not used on invoices."
            )
    fx_factor = Decimal(fx_rate_row["rate"]) if fx_rate_row else None

    def in_invoice_currency(cents: int) -> int:
        if fx_factor is None:
            return int(cents)
        return int((Decimal(int(cents)) * fx_factor).quantize(Decimal(1), ROUND_HALF_UP))

    # Phase 373: the warranty claims on the order are priced, and what they
    # cover comes off the customer's lines, before anything is written.
    rate_cents = in_invoice_currency(labor_hourly_rate_cents)
    unit_cents_by_wop = {int(p["wop_id"]): in_invoice_currency(
        int(p.get("effective_unit_cents", 0) or 0)) for p in parts_lines}
    claims, covered_hours, covered_qty = _price_claims(
        wo_id, hours, rate_cents, parts_lines, unit_cents_by_wop, decision,
        wo["shop_id"], invoice_day, db_path=db_path,
    )
    customer_hours = _hours_left(hours, covered_hours)
    claim_notes = [_claim_note(c) for c in claims if c["lines"]]
    if claim_notes:
        notes = " | ".join(([notes] if notes else []) + claim_notes)

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
        currency=invoice_currency,
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
    # Phase 281: each line's total by type, so tax falls on taxable lines only.
    by_type: dict[str, int] = {t: 0 for t in tax_mod.LINE_TYPES}

    # --- Labor line (the hours no claim covers) ---
    money_mark = "$" if invoice_currency == "USD" else f"{invoice_currency} "
    if customer_hours > 0:
        labor_cents = _add_line_cents(
            invoice_id,
            InvoiceLineItemType.LABOR,
            f"Labor — {customer_hours:.2f}h × {money_mark}{rate_cents / 100:.2f}/h",
            customer_hours,
            rate_cents,
            sort_order=10,
            db_path=db_path,
        )
        subtotal_cents += labor_cents
        by_type["labor"] += labor_cents

    # --- Parts lines (the quantity no claim covers) ---
    sort = 20
    for part in parts_lines:
        qty = (int(part.get("quantity", 1) or 1)
               - covered_qty.get(int(part["wop_id"]), 0))
        if qty <= 0:
            continue
        unit_cents = int(part.get("effective_unit_cents", 0) or 0)
        desc_parts = [
            (part.get("brand") or "").strip(),
            (part.get("description") or part.get("slug") or "?").strip(),
        ]
        desc = " ".join(p for p in desc_parts if p) or "Part"
        part_cents = _add_line_cents(
            invoice_id,
            InvoiceLineItemType.PARTS,
            desc,
            float(qty),
            in_invoice_currency(unit_cents),
            sort_order=sort,
            db_path=db_path,
        )
        subtotal_cents += part_cents
        by_type["parts"] += part_cents
        sort += 1

    # --- Optional diagnostic line ---
    if diagnostic_fee_cents and diagnostic_fee_cents > 0:
        diag_cents = _add_line_cents(
            invoice_id,
            InvoiceLineItemType.DIAGNOSTIC,
            "Diagnostic fee",
            1.0,
            in_invoice_currency(int(diagnostic_fee_cents)),
            sort_order=sort,
            db_path=db_path,
        )
        subtotal_cents += diag_cents
        by_type["diagnostic"] += diag_cents
        sort += 1

    # --- Optional shop supplies line (pct applies to pre-supplies subtotal) ---
    supplies_cents = 0
    if shop_supplies_pct > 0:
        supplies_cents += int(round(subtotal_cents * shop_supplies_pct))
    if shop_supplies_flat_cents and shop_supplies_flat_cents > 0:
        supplies_cents += in_invoice_currency(int(shop_supplies_flat_cents))
    if supplies_cents > 0:
        misc_cents = _add_line_cents(
            invoice_id,
            InvoiceLineItemType.MISC,
            "Shop supplies",
            1.0,
            supplies_cents,
            sort_order=sort,
            db_path=db_path,
        )
        subtotal_cents += misc_cents
        by_type["misc"] += misc_cents

    # --- Tax + totals (Phase 281: the taxable lines, at the recorded rate) ---
    taxable_cents = sum(by_type[t] for t in decision.taxable_types)
    tax_cents = int((Decimal(taxable_cents) * Decimal(str(decision.rate.value)))
                    .quantize(Decimal(1), ROUND_HALF_UP))
    total_cents = subtotal_cents + tax_cents
    _record_claim_prices(claims, invoice_id, db_path=db_path)
    if total_cents == 0:
        # Phase 373: every line is covered; the customer owes nothing.
        _update_invoice(invoice_id, db_path=db_path,
                        status=_AccountingInvoiceStatus.PAID, paid_at=now.isoformat())

    _update_invoice(
        invoice_id, db_path=db_path,
        subtotal=_cents_to_dollars(subtotal_cents),
        tax_amount=_cents_to_dollars(tax_cents),
        total=_cents_to_dollars(total_cents),
        tax_rate=decision.rate.value,
        tax_rate_id=decision.rate.row_id,
        tax_source=decision.source_text,
        tax_recheck_by=decision.recheck_by,
        taxed_line_types=",".join(decision.taxable_types) or "none",
        fx_from_currency=decision.currency if fx_rate_row else None,
        fx_rate=fx_rate_row["rate"] if fx_rate_row else None,
        fx_rate_id=fx_rate_row["id"] if fx_rate_row else None,
        fx_rate_date=fx_rate_row["rate_date"] if fx_rate_row else None,
        fx_source=(f"the shop's own rate: {fx_rate_row['source_note']}"
                   if fx_rate_row else None),
    )
    return invoice_id


def generate_shortfall_invoice(claim: dict, shortfall_cents: int,
                               db_path: Optional[str] = None) -> int:
    """Bill the work order's customer for a settled claim's shortfall.

    ``claim`` is the claim as stored, invoiced; ``shortfall_cents`` is the
    amount claimed less the amount approved. The pre-tax shortfall is the
    claim's covered amount in the same proportion, rounded half up, split
    over its lines by amount; the customer's tax is computed on it from the
    shop's rules on the day, as on any invoice. Returns the new invoice id.
    """
    claimed = int(claim["amount_claimed_cents"])
    covered = int(claim["covered_cents"])
    pre_tax = (covered if shortfall_cents == claimed else
               int((Decimal(covered) * shortfall_cents / claimed)
                   .quantize(Decimal(1), ROUND_HALF_UP)))
    with get_connection(db_path) as conn:
        lines = [dict(r) for r in conn.execute(
            "SELECT * FROM warranty_claim_lines WHERE claim_id = ? ORDER BY id",
            (claim["id"],),
        ).fetchall()]
        original = dict(conn.execute("SELECT * FROM invoices WHERE id = ?",
                                     (claim["invoice_id"],)).fetchone())
    wo = require_work_order(claim["work_order_id"], db_path=db_path)
    shares = _split_cents(pre_tax, [int(line["amount_cents"]) for line in lines])
    line_types = {line["line_type"] for line, share in zip(lines, shares) if share}
    try:
        decision = tax_mod.resolve_tax(wo["shop_id"], tax_mod.today(), line_types,
                                       db_path=db_path)
    except tax_mod.TaxNotOnRecord as exc:
        raise InvoiceTaxNotOnRecord(str(exc)) from exc

    now = datetime.now(timezone.utc)
    # A claim settles once, so its number is unique without a regeneration index.
    number = f"INV-{wo['shop_id']}-{wo['id']}-{now.strftime('%Y%m%d')}-S{claim['id']}"
    invoice_id = create_invoice(Invoice(
        customer_id=int(original["customer_id"]),
        repair_plan_id=None,
        invoice_number=number,
        status=_AccountingInvoiceStatus.SENT,
        subtotal=0.0, tax_amount=0.0, total=0.0,
        currency=original.get("currency"),
        issued_at=now, due_at=None, paid_at=None,
        notes=f"Warranty claim #{claim['id']}: the part the warranty did not pay",
    ), db_path=db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE invoices SET work_order_id = ?, shortfall_claim_id = ? WHERE id = ?",
            (wo["id"], claim["id"], invoice_id),
        )
    by_type: dict[str, int] = {t: 0 for t in tax_mod.LINE_TYPES}
    item_types = {"labor": InvoiceLineItemType.LABOR, "parts": InvoiceLineItemType.PARTS}
    for sort, (line, share) in enumerate(zip(lines, shares), start=10):
        if not share:
            continue
        _add_line_cents(
            invoice_id, item_types[line["line_type"]],
            f"Warranty claim #{claim['id']} not paid: "
            f"{line['description'] or line['line_type']}",
            1.0, share, sort_order=sort, db_path=db_path,
        )
        by_type[line["line_type"]] += share
    taxable = sum(by_type[t] for t in decision.taxable_types)
    tax_cents = int((Decimal(taxable) * Decimal(str(decision.rate.value)))
                    .quantize(Decimal(1), ROUND_HALF_UP))
    _update_invoice(
        invoice_id, db_path=db_path,
        subtotal=_cents_to_dollars(pre_tax),
        tax_amount=_cents_to_dollars(tax_cents),
        total=_cents_to_dollars(pre_tax + tax_cents),
        tax_rate=decision.rate.value,
        tax_rate_id=decision.rate.row_id,
        tax_source=decision.source_text,
        tax_recheck_by=decision.recheck_by,
        taxed_line_types=",".join(decision.taxable_types) or "none",
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
        currency=row.get("currency"),
        tax_rate=row.get("tax_rate"),
        tax_source=row.get("tax_source"),
        tax_recheck_by=row.get("tax_recheck_by"),
        taxed_line_types=row.get("taxed_line_types"),
        fx_from_currency=row.get("fx_from_currency"),
        fx_rate=row.get("fx_rate"),
        fx_rate_date=row.get("fx_rate_date"),
        fx_source=row.get("fx_source"),
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
