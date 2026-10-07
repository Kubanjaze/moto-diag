"""Warranty claims kept by the shop, and the printable claim packet.

A claim ties a recorded warranty (``warranties``) to the work order the
repair was done on. Its status is what the shop records as the claim moves:

    draft → submitted → approved | denied;  approved → paid

``submitted`` means the shop sent the claim by whatever means the maker
accepts. Submitting through a maker's own system needs that maker's dealer
portal and is not built here.

:func:`render_claim_packet` assembles the documentation a claim needs from
stored data: the shop, the customer, the bike and its VIN, the coverage and
whether it applied on the repair's date, the work order, its issues, parts
and labour time, and the claim itself.

Phase 373 (F188): :func:`cover_claim` records which of the work order's
lines a claim covers. The invoice leaves them off what the customer owes and
prices them for the claim, so the amount claimed is derived, never typed.
:func:`settle_claim` records the shop's decision on a claim denied or paid
short: bill the customer for the shortfall, or absorb it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from motodiag.accounting.tax import PAYER_LABELS
from motodiag.core.database import get_connection
from motodiag.inventory.warranty_repo import (
    coverage_status,
    get_warranty,
    increment_claim_count,
)
from motodiag.shop.invoicing import generate_shortfall_invoice

SETTLEMENTS: tuple[str, ...] = ("bill_customer", "absorb")

CLAIM_STATUSES: tuple[str, ...] = ("draft", "submitted", "approved", "denied", "paid")

_MOVES: dict[str, tuple[str, ...]] = {
    "draft": ("submitted",),
    "submitted": ("approved", "denied"),
    "approved": ("paid",),
    "denied": (),
    "paid": (),
}
_STAMP = {"submitted": "submitted_at", "approved": "decided_at",
          "denied": "decided_at", "paid": "paid_at"}


class WarrantyClaimError(ValueError):
    """A claim or warranty that does not exist, or a move not allowed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def open_claim(
    warranty_id: int,
    description: str,
    work_order_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> int:
    """Open a draft claim. Returns its id.

    The work order, when given, must be on the warranty's bike. The
    warranty's ``claim_count`` goes up by one. The amount claimed is not
    given: the invoice derives it from the lines the claim covers.
    """
    warranty = get_warranty(warranty_id, db_path=db_path)
    if warranty is None:
        raise WarrantyClaimError(f"warranty not found: id={warranty_id}")
    if not description or not description.strip():
        raise WarrantyClaimError("a claim needs a description of the failure and repair")
    with get_connection(db_path) as conn:
        if work_order_id is not None:
            wo = conn.execute(
                "SELECT vehicle_id FROM work_orders WHERE id = ?", (work_order_id,),
            ).fetchone()
            if wo is None:
                raise WarrantyClaimError(f"work order not found: id={work_order_id}")
            if wo["vehicle_id"] != warranty["vehicle_id"]:
                raise WarrantyClaimError(
                    f"work order id={work_order_id} is on another bike than "
                    f"warranty id={warranty_id}"
                )
        claim_id = conn.execute(
            "INSERT INTO warranty_claims (warranty_id, work_order_id, description, "
            "opened_at) VALUES (?, ?, ?, ?)",
            (warranty_id, work_order_id, description.strip(), _now()),
        ).lastrowid
    increment_claim_count(warranty_id, db_path=db_path)
    return int(claim_id)


def get_claim(claim_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT c.*, w.vehicle_id, w.coverage_type, w.provider "
            "FROM warranty_claims c JOIN warranties w ON w.id = c.warranty_id "
            "WHERE c.id = ?",
            (claim_id,),
        ).fetchone()
        return dict(row) if row else None


def list_claims(
    status: Optional[str] = None,
    vehicle_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Claims newest first, optionally one status or one bike."""
    query = (
        "SELECT c.*, w.vehicle_id, w.coverage_type, w.provider "
        "FROM warranty_claims c JOIN warranties w ON w.id = c.warranty_id WHERE 1=1"
    )
    params: list = []
    if status is not None:
        query += " AND c.status = ?"
        params.append(status)
    if vehicle_id is not None:
        query += " AND w.vehicle_id = ?"
        params.append(vehicle_id)
    query += " ORDER BY c.id DESC"
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def claim_lines(claim_id: int, db_path: Optional[str] = None) -> list[dict]:
    """The lines a claim covers, in the order recorded."""
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM warranty_claim_lines WHERE claim_id = ? ORDER BY id",
            (claim_id,),
        ).fetchall()]


def cover_claim(
    claim_id: int,
    labour_hours: Optional[float] = None,
    parts: Optional[list[tuple[int, Optional[int]]]] = None,
    covers_nothing: bool = False,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Record which of the work order's lines a draft claim covers.

    ``parts`` holds (work-order part row, quantity or None for all of it).
    Covering again replaces the claim's lines. Refused once the order has an
    invoice, since what the customer was asked to pay would change under it.
    Returns the claim's lines.
    """
    parts = parts or []
    claim = get_claim(claim_id, db_path=db_path)
    if claim is None:
        raise WarrantyClaimError(f"claim not found: id={claim_id}")
    if claim["status"] != "draft":
        raise WarrantyClaimError(
            f"claim #{claim_id} is {claim['status']}; only a draft's lines can change"
        )
    wo_id = claim["work_order_id"]
    if wo_id is None:
        raise WarrantyClaimError(
            f"claim #{claim_id} has no work order, so it has no lines to cover"
        )
    if covers_nothing and (labour_hours or parts):
        raise WarrantyClaimError("--none covers nothing; give lines or --none, not both")
    if not covers_nothing and not labour_hours and not parts:
        raise WarrantyClaimError(
            "say which lines the claim covers (--labour-hours, --part), or --none"
        )
    if labour_hours is not None and labour_hours <= 0:
        raise WarrantyClaimError("covered labour hours must be more than 0")
    warranty = get_warranty(claim["warranty_id"], db_path=db_path)
    if not covers_nothing and warranty.get("repair_payer") is None:
        raise WarrantyClaimError(
            f"warranty #{warranty['id']} does not record who owes the repair, which "
            f"decides the tax on the claim; record it with `motodiag shop warranty "
            f"update {warranty['id']} --payer …`"
        )
    if not covers_nothing and not (warranty.get("provider") or "").strip():
        raise WarrantyClaimError(
            f"warranty #{warranty['id']} does not record who gives it, so the claim "
            f"has no one to be owed by; record it with `motodiag shop warranty update "
            f"{warranty['id']} --provider NAME`"
        )
    rows: list[tuple[str, Optional[int], float, str]] = []
    with get_connection(db_path) as conn:
        invoiced = conn.execute(
            "SELECT id FROM invoices WHERE work_order_id = ? AND status != 'cancelled' "
            "AND shortfall_claim_id IS NULL LIMIT 1", (wo_id,),
        ).fetchone()
        if invoiced is not None:
            raise WarrantyClaimError(
                f"work order id={wo_id} is already invoiced (invoice id={invoiced[0]}); "
                f"void it with `motodiag shop invoice void {invoiced[0]}`, cover the "
                f"lines, then generate it again"
            )
        others = conn.execute(
            "SELECT l.* FROM warranty_claim_lines l JOIN warranty_claims c "
            "ON c.id = l.claim_id WHERE c.work_order_id = ? AND c.id != ? "
            "AND c.status != 'denied'", (wo_id, claim_id),
        ).fetchall()
        if labour_hours:
            wo = conn.execute("SELECT actual_hours, estimated_hours FROM work_orders "
                              "WHERE id = ?", (wo_id,)).fetchone()
            billed = wo["actual_hours"] if wo["actual_hours"] is not None \
                else wo["estimated_hours"]
            taken = sum(float(r["quantity"]) for r in others if r["line_type"] == "labor")
            if billed is not None and labour_hours + taken > float(billed) + 1e-9:
                raise WarrantyClaimError(
                    f"work order id={wo_id} has {float(billed):g} h; other claims cover "
                    f"{taken:g} h, so this one can cover at most {float(billed) - taken:g} h"
                )
            rows.append(("labor", None, float(labour_hours),
                         f"labour {float(labour_hours):.2f} h"))
        seen: set[int] = set()
        for wop_id, qty in parts:
            if wop_id in seen:
                raise WarrantyClaimError(f"part row {wop_id} is given twice")
            seen.add(wop_id)
            part = conn.execute(
                "SELECT wop.quantity, wop.status, p.brand, p.description, p.slug "
                "FROM work_order_parts wop JOIN parts p ON p.id = wop.part_id "
                "WHERE wop.id = ? AND wop.work_order_id = ?", (wop_id, wo_id),
            ).fetchone()
            if part is None:
                raise WarrantyClaimError(
                    f"part row {wop_id} is not on work order id={wo_id}; see `motodiag "
                    f"shop parts-needs list --wo {wo_id}`"
                )
            if part["status"] == "cancelled":
                raise WarrantyClaimError(f"part row {wop_id} is cancelled")
            count = int(part["quantity"]) if qty is None else int(qty)
            taken = sum(int(r["quantity"]) for r in others
                        if r["work_order_part_id"] == wop_id)
            if count < 1 or count + taken > int(part["quantity"]):
                raise WarrantyClaimError(
                    f"part row {wop_id} holds {part['quantity']}; other claims cover "
                    f"{taken}, so this one can cover 1 to {int(part['quantity']) - taken}"
                )
            name = " ".join(b for b in ((part["brand"] or "").strip(),
                                        (part["description"] or part["slug"]).strip()) if b)
            rows.append(("parts", wop_id, float(count), f"{count} x {name}"))
        conn.execute("DELETE FROM warranty_claim_lines WHERE claim_id = ?", (claim_id,))
        for line_type, wop_id, quantity, description in rows:
            conn.execute(
                "INSERT INTO warranty_claim_lines (claim_id, line_type, "
                "work_order_part_id, quantity, description) VALUES (?, ?, ?, ?, ?)",
                (claim_id, line_type, wop_id, quantity, description),
            )
        conn.execute("UPDATE warranty_claims SET coverage_recorded_at = ? WHERE id = ?",
                     (_now(), claim_id))
    return claim_lines(claim_id, db_path=db_path)


def settle_claim(claim_id: int, settlement: str,
                 db_path: Optional[str] = None) -> dict:
    """Record the shop's decision on a claim denied, or approved or paid for
    less than claimed: bill the customer for the shortfall, or absorb it.
    Once per claim. Returns the claim after it."""
    if settlement not in SETTLEMENTS:
        raise WarrantyClaimError(f"a settlement is one of {', '.join(SETTLEMENTS)}")
    claim = get_claim(claim_id, db_path=db_path)
    if claim is None:
        raise WarrantyClaimError(f"claim not found: id={claim_id}")
    if claim["settlement"] is not None:
        raise WarrantyClaimError(
            f"claim #{claim_id} was settled on {claim['settled_at']} "
            f"({claim['settlement']})"
        )
    if claim["invoice_id"] is None or claim["amount_claimed_cents"] is None:
        raise WarrantyClaimError(
            f"claim #{claim_id} was never invoiced, so its lines were billed to the "
            f"customer and there is nothing to settle"
        )
    with get_connection(db_path) as conn:
        invoice = conn.execute("SELECT status FROM invoices WHERE id = ?",
                               (claim["invoice_id"],)).fetchone()
    if invoice is None or invoice["status"] == "cancelled":
        raise WarrantyClaimError(
            f"claim #{claim_id}'s invoice is void; generate the work order's invoice "
            f"again before settling"
        )
    if claim["status"] == "denied":
        approved = 0
    elif claim["status"] in ("approved", "paid"):
        if claim["amount_approved_cents"] is None:
            raise WarrantyClaimError(
                f"claim #{claim_id} has no approved amount; record it with `motodiag "
                f"shop warranty claim status {claim_id} --to {claim['status']} "
                f"--approved-cents N`"
            )
        approved = int(claim["amount_approved_cents"])
    else:
        raise WarrantyClaimError(
            f"claim #{claim_id} is {claim['status']}; settle it once it is denied, "
            f"approved or paid"
        )
    shortfall = int(claim["amount_claimed_cents"]) - approved
    if shortfall <= 0:
        raise WarrantyClaimError(
            f"claim #{claim_id} was approved for the amount claimed; nothing to settle"
        )
    shortfall_invoice_id = (generate_shortfall_invoice(claim, shortfall, db_path=db_path)
                            if settlement == "bill_customer" else None)
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE warranty_claims SET settlement = ?, settled_at = ?, "
            "shortfall_cents = ?, shortfall_invoice_id = ? WHERE id = ?",
            (settlement, _now(), shortfall, shortfall_invoice_id, claim_id),
        )
    return get_claim(claim_id, db_path=db_path)


def set_claim_status(
    claim_id: int,
    target: str,
    claim_number: Optional[str] = None,
    amount_approved_cents: Optional[int] = None,
    db_path: Optional[str] = None,
) -> dict:
    """Move a claim to ``target``, recording the maker's number and the
    approved amount when given. Returns the claim after the move."""
    claim = get_claim(claim_id, db_path=db_path)
    if claim is None:
        raise WarrantyClaimError(f"claim not found: id={claim_id}")
    if target not in _MOVES.get(claim["status"], ()):
        raise WarrantyClaimError(
            f"claim #{claim_id} is {claim['status']}; it cannot be marked {target}"
        )
    if amount_approved_cents is not None and target not in ("approved", "paid"):
        raise WarrantyClaimError("an approved amount goes with approved or paid")
    claimed = claim.get("amount_claimed_cents")
    if (amount_approved_cents is not None and claimed is not None
            and amount_approved_cents > claimed):
        raise WarrantyClaimError(
            f"claim #{claim_id} claims {claimed} cents; it cannot be approved for "
            f"{amount_approved_cents}"
        )
    fields = {"status": target, _STAMP[target]: _now()}
    if claim_number is not None:
        fields["claim_number"] = claim_number
    if amount_approved_cents is not None:
        fields["amount_approved_cents"] = amount_approved_cents
    sets = ", ".join(f"{k} = ?" for k in fields)
    with get_connection(db_path) as conn:
        conn.execute(f"UPDATE warranty_claims SET {sets} WHERE id = ?",
                     (*fields.values(), claim_id))
    return get_claim(claim_id, db_path=db_path)


def _money(cents: Optional[int]) -> str:
    return "not recorded" if cents is None else f"${cents / 100:,.2f}"


def _miles(value: Optional[int]) -> str:
    return "not recorded" if value is None else f"{value:,} mi"


def render_claim_packet(claim_id: int, db_path: Optional[str] = None) -> str:
    """The claim's documentation as plain text, from stored data only."""
    claim = get_claim(claim_id, db_path=db_path)
    if claim is None:
        raise WarrantyClaimError(f"claim not found: id={claim_id}")
    warranty = get_warranty(claim["warranty_id"], db_path=db_path)
    wo = customer = shop = None
    issues: list = []
    parts: list = []
    time_rows: list = []
    intake = None
    with get_connection(db_path) as conn:
        bike = dict(conn.execute("SELECT * FROM vehicles WHERE id = ?",
                                 (claim["vehicle_id"],)).fetchone())
        if claim["work_order_id"] is not None:
            row = conn.execute("SELECT * FROM work_orders WHERE id = ?",
                               (claim["work_order_id"],)).fetchone()
            wo = dict(row) if row else None
        if wo:
            customer = conn.execute("SELECT * FROM customers WHERE id = ?",
                                    (wo["customer_id"],)).fetchone()
            shop = conn.execute("SELECT * FROM shops WHERE id = ?",
                                (wo["shop_id"],)).fetchone()
            issues = conn.execute(
                "SELECT title, category, severity, description, resolution_notes "
                "FROM issues WHERE work_order_id = ? ORDER BY id", (wo["id"],),
            ).fetchall()
            parts = conn.execute(
                "SELECT wop.quantity, wop.status, p.brand, p.description, "
                "p.oem_part_number FROM work_order_parts wop "
                "JOIN parts p ON p.id = wop.part_id "
                "WHERE wop.work_order_id = ? AND wop.status != 'cancelled' "
                "ORDER BY wop.id", (wo["id"],),
            ).fetchall()
            time_rows = conn.execute(
                "SELECT duration_seconds FROM work_order_time_entries "
                "WHERE work_order_id = ? AND duration_seconds IS NOT NULL",
                (wo["id"],),
            ).fetchall()
            if wo.get("intake_visit_id"):
                intake = conn.execute(
                    "SELECT mileage_at_intake, reported_problems FROM intake_visits "
                    "WHERE id = ?", (wo["intake_visit_id"],)).fetchone()
        if customer is None:
            customer = conn.execute(
                "SELECT c.* FROM customers c JOIN customer_bikes cb "
                "ON cb.customer_id = c.id WHERE cb.vehicle_id = ? "
                "AND cb.relationship = 'owner' ORDER BY cb.assigned_at DESC LIMIT 1",
                (bike["id"],),
            ).fetchone()

    out: list[str] = []
    out.append(f"WARRANTY CLAIM #{claim['id']}")
    out.append(f"Status: {claim['status']}    Opened: {claim['opened_at']}")
    out.append(f"Maker's claim number: {claim.get('claim_number') or 'not assigned'}")
    out.append("")
    if shop:
        out.append(f"Shop: {shop['name']}")
        addr = ", ".join(b for b in (shop["address"], shop["city"], shop["state"],
                                     shop["zip"]) if b)
        if addr:
            out.append(f"      {addr}")
        if shop["phone"]:
            out.append(f"      {shop['phone']}")
    out.append(f"Customer: {customer['name'] if customer else 'not recorded'}")
    out.append("")
    out.append(f"Bike: {bike.get('year') or ''} {bike['make']} {bike['model']}".rstrip())
    out.append(f"VIN: {bike.get('vin') or 'not recorded'}")
    out.append("Mileage on record: " + _miles(bike.get("mileage")))
    if intake is not None:
        out.append("Mileage at intake: " + _miles(intake["mileage_at_intake"]))
        if intake["reported_problems"]:
            out.append(f"Reported at intake: {intake['reported_problems']}")
    out.append("")
    provider = warranty.get("provider")
    out.append(f"Coverage: {warranty['coverage_type']}"
               + (f" ({provider})" if provider else ""))
    out.append(f"  Term: {warranty.get('start_date') or 'start not recorded'} to "
               f"{warranty.get('end_date') or 'end not recorded'}")
    out.append("  Mileage limit: " + _miles(warranty.get("mileage_limit")))
    payer = warranty.get("repair_payer")
    out.append("  Repair owed by: "
               + (PAYER_LABELS[payer] if payer else "not recorded"))
    if warranty.get("terms"):
        out.append(f"  Terms: {warranty['terms']}")
    repair_date = None
    if wo:
        repair_date = str(wo.get("completed_at") or wo.get("opened_at") or "")[:10] or None
    if repair_date:
        # An intake's unknown mileage stays unknown: never the bike's instead.
        mileage = (intake["mileage_at_intake"] if intake is not None
                   else bike.get("mileage"))
        verdict, reasons = coverage_status(warranty, repair_date, mileage)
        out.append(f"  On the repair date ({repair_date}): {verdict} — {'; '.join(reasons)}")
    out.append("")
    out.append("Claim")
    out.append(f"  {claim['description']}")
    out.append("  Covered lines:")
    lines = claim_lines(claim_id, db_path=db_path)
    if claim.get("coverage_recorded_at") is None:
        out.append("    not recorded yet")
    elif not lines:
        out.append("    none: the claim covers no line of the work order")
    for line in lines:
        price = (_money(line["amount_cents"]) if line["amount_cents"] is not None
                 else "priced when the invoice is generated")
        out.append(f"    - {line['description']}: {price}")
    if claim.get("covered_cents") is not None:
        out.append(f"  Covered work: {_money(claim['covered_cents'])}")
        tax = f"  Tax on the claim: {_money(claim['tax_cents'])}"
        if claim.get("tax_source"):
            tax += f" ({claim['tax_source']})"
        out.append(tax)
    out.append(f"  Amount claimed: {_money(claim.get('amount_claimed_cents'))}")
    out.append(f"  Amount approved: {_money(claim.get('amount_approved_cents'))}")
    if claim.get("settlement"):
        how = ("billed to the customer" if claim["settlement"] == "bill_customer"
               else "absorbed by the shop")
        out.append(f"  Shortfall: {_money(claim['shortfall_cents'])}, {how} "
                   f"({claim['settled_at']})")
    for label, key in (("Submitted", "submitted_at"), ("Decided", "decided_at"),
                       ("Paid", "paid_at")):
        if claim.get(key):
            out.append(f"  {label}: {claim[key]}")
    out.append("")
    if wo is None:
        out.append("Work order: none linked")
    else:
        out.append(f"Work order #{wo['id']}: {wo['title']} ({wo['status']})")
        if wo.get("description"):
            out.append(f"  {wo['description']}")
        out.append(f"  Opened {wo.get('opened_at') or '—'}; "
                   f"completed {wo.get('completed_at') or '—'}")
        out.append("  Issues:")
        if not issues:
            out.append("    none recorded")
        for i in issues:
            out.append(f"    - {i['title']} [{i['category']}, {i['severity']}]")
            if i["description"]:
                out.append(f"      {i['description']}")
            if i["resolution_notes"]:
                out.append(f"      Resolution: {i['resolution_notes']}")
        out.append("  Parts:")
        if not parts:
            out.append("    none recorded")
        for p in parts:
            number = f" (part no. {p['oem_part_number']})" if p["oem_part_number"] else ""
            out.append(f"    - {p['quantity']} x {p['brand']} {p['description']}"
                       f"{number} [{p['status']}]")
        hours = sum(t["duration_seconds"] for t in time_rows) / 3600
        entries = "entry" if len(time_rows) == 1 else "entries"
        billed = (f"; billed hours {wo['actual_hours']}"
                  if wo.get("actual_hours") is not None else "")
        out.append(f"  Labour: {hours:.2f} h logged in {len(time_rows)} time "
                   f"{entries}{billed}")
    return "\n".join(out) + "\n"
