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
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.inventory.warranty_repo import (
    coverage_status,
    get_warranty,
    increment_claim_count,
)

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
    amount_claimed_cents: Optional[int] = None,
    db_path: Optional[str] = None,
) -> int:
    """Open a draft claim. Returns its id.

    The work order, when given, must be on the warranty's bike. The
    warranty's ``claim_count`` goes up by one.
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
            "amount_claimed_cents, opened_at) VALUES (?, ?, ?, ?, ?)",
            (warranty_id, work_order_id, description.strip(),
             amount_claimed_cents, _now()),
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
    intake_mileage = None
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
                v = conn.execute("SELECT mileage_at_intake FROM intake_visits WHERE id = ?",
                                 (wo["intake_visit_id"],)).fetchone()
                intake_mileage = v[0] if v else None
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
    out.append("")
    provider = warranty.get("provider")
    out.append(f"Coverage: {warranty['coverage_type']}"
               + (f" ({provider})" if provider else ""))
    out.append(f"  Term: {warranty.get('start_date') or 'start not recorded'} to "
               f"{warranty.get('end_date') or 'end not recorded'}")
    out.append("  Mileage limit: " + _miles(warranty.get("mileage_limit")))
    if warranty.get("terms"):
        out.append(f"  Terms: {warranty['terms']}")
    repair_date = None
    if wo:
        repair_date = str(wo.get("completed_at") or wo.get("opened_at") or "")[:10] or None
    if repair_date:
        mileage = intake_mileage if intake_mileage is not None else bike.get("mileage")
        verdict, reasons = coverage_status(warranty, repair_date, mileage)
        out.append(f"  On the repair date ({repair_date}): {verdict} — {'; '.join(reasons)}")
    out.append("")
    out.append("Claim")
    out.append(f"  {claim['description']}")
    out.append(f"  Amount claimed: {_money(claim.get('amount_claimed_cents'))}")
    out.append(f"  Amount approved: {_money(claim.get('amount_approved_cents'))}")
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
