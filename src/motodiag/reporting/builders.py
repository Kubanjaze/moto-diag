"""Report document builders (Phase 182).

Three builders that hydrate a normalized ``ReportDocument`` dict
from DB rows:

- :func:`build_session_report_doc` — diagnostic session report
  (session owner only; cross-user → 404 via
  :class:`motodiag.core.session_repo.SessionOwnershipError`).
- :func:`build_work_order_report_doc` — work-order receipt
  (shop-tier + membership via Phase 172
  :func:`motodiag.shop.rbac.require_shop_permission`).
- :func:`build_invoice_report_doc` — invoice PDF (shop-tier +
  membership in the WO's shop; composes Phase 169
  :func:`motodiag.shop.invoicing.get_invoice_with_items`).

Builders raise domain exceptions (``SessionOwnershipError``,
``WorkOrderNotFoundError``, ``InvoiceNotFoundError``,
``PermissionDenied``) which the API error handler maps to HTTP.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from motodiag.core.session_repo import (
    SessionOwnershipError, get_session_for_owner,
)
from motodiag.knowledge.dtc_repo import get_dtc
from motodiag.shop.invoicing import (
    InvoiceNotFoundError, get_invoice_with_items,
)
from motodiag.shop.issue_repo import list_issues
from motodiag.shop.parts_needs import list_parts_for_wo
from motodiag.shop.rbac import PermissionDenied, has_shop_permission
from motodiag.shop.shop_repo import get_shop
from motodiag.shop.work_order_repo import (
    WorkOrderNotFoundError, get_work_order,
)


class ReportBuildError(ValueError):
    """Raised when a builder can't assemble a valid document."""


ReportDocument = dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _money(cents: Optional[int]) -> str:
    if cents is None:
        return "—"
    return f"${cents / 100:,.2f}"


def _require_member(
    user_id: int, shop_id: int, db_path: str,
) -> None:
    """Shop-tier callers must be an active member of the shop.
    Non-member → 403 via PermissionDenied."""
    from motodiag.shop import get_shop_member
    member = get_shop_member(
        shop_id=shop_id, user_id=user_id, db_path=db_path,
    )
    if member is None or not member.is_active:
        raise PermissionDenied(
            f"user id={user_id} is not an active member of "
            f"shop id={shop_id}"
        )


def _footer(extra: Optional[str] = None) -> str:
    base = f"MotoDiag — generated {_now_iso()}"
    return f"{base}  •  {extra}" if extra else base


# ---------------------------------------------------------------------------
# Session report
# ---------------------------------------------------------------------------


def build_session_report_doc(
    session_id: int,
    user_id: int,
    db_path: Optional[str] = None,
) -> ReportDocument:
    """Build a diagnostic-session report document.

    Owner-scoped: ``user_id`` must match the session's ``user_id``
    column (Phase 178 retrofit); otherwise
    :class:`SessionOwnershipError` is raised (maps to 404).
    """
    row = get_session_for_owner(session_id, user_id, db_path=db_path)
    if row is None:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )

    vehicle_make = str(row.get("vehicle_make") or "")
    vehicle_model = str(row.get("vehicle_model") or "")
    vehicle_year = row.get("vehicle_year")
    vehicle_line = (
        f"{vehicle_make} {vehicle_model}" +
        (f" ({vehicle_year})" if vehicle_year else "")
    ).strip()

    sections: list[dict] = []

    # Vehicle
    sections.append({
        "heading": "Vehicle",
        "rows": [
            ("Make", vehicle_make or "—"),
            ("Model", vehicle_model or "—"),
            ("Year", str(vehicle_year) if vehicle_year else "—"),
        ],
    })

    # Symptoms
    symptoms = row.get("symptoms") or []
    if symptoms:
        sections.append({
            "heading": "Reported symptoms",
            "bullets": [str(s) for s in symptoms],
        })

    # Fault codes
    fault_codes = row.get("fault_codes") or []
    if fault_codes:
        dtc_rows: list[list[str]] = []
        for code in fault_codes:
            info = get_dtc(str(code), db_path=db_path)
            if info is not None:
                description = str(info.get("description") or "")
                severity = str(info.get("severity") or "—")
            else:
                description = "Unknown DTC"
                severity = "—"
            dtc_rows.append([str(code), description, severity])
        sections.append({
            "heading": "Fault codes",
            "table": {
                "columns": ["Code", "Description", "Severity"],
                "rows": dtc_rows,
            },
        })

    # Diagnosis + confidence + severity
    diag = row.get("diagnosis")
    if diag:
        diag_rows: list[tuple[str, str]] = [("Diagnosis", str(diag))]
        if row.get("confidence") is not None:
            diag_rows.append((
                "Confidence", f"{float(row['confidence']):.2f}",
            ))
        if row.get("severity"):
            diag_rows.append(("Severity", str(row["severity"])))
        if row.get("cost_estimate") is not None:
            diag_rows.append((
                "Cost estimate",
                f"${float(row['cost_estimate']):,.2f}",
            ))
        sections.append({
            "heading": "AI diagnosis",
            "rows": diag_rows,
        })

    # Repair steps
    repair_steps = row.get("repair_steps") or []
    if repair_steps:
        sections.append({
            "heading": "Recommended repair steps",
            "bullets": [str(s) for s in repair_steps],
        })

    # Notes
    if row.get("notes"):
        sections.append({
            "heading": "Notes",
            "body": str(row["notes"]),
        })

    # Timestamps
    sections.append({
        "heading": "Timeline",
        "rows": [
            ("Status", str(row.get("status") or "open")),
            ("Created", str(row.get("created_at") or "—")),
            ("Updated", str(row.get("updated_at") or "—")),
            ("Closed", str(row.get("closed_at") or "—")),
        ],
    })

    return {
        "title": f"Diagnostic session report #{int(row['id'])}",
        "subtitle": vehicle_line or None,
        "issued_at": _now_iso(),
        "sections": sections,
        "footer": _footer(f"Session {row['id']}"),
    }


# ---------------------------------------------------------------------------
# Work-order report
# ---------------------------------------------------------------------------


def build_work_order_report_doc(
    wo_id: int,
    user_id: int,
    db_path: Optional[str] = None,
) -> ReportDocument:
    """Build a work-order receipt.

    Shop-scoped: caller must be an active member of the WO's shop
    (Phase 172 RBAC). Non-member raises
    :class:`PermissionDenied` (maps to 403).
    """
    wo = get_work_order(wo_id, db_path=db_path)
    if wo is None:
        raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")

    shop_id = wo.get("shop_id")
    if shop_id is None:
        raise ReportBuildError(
            f"work order id={wo_id} has no shop — cannot authorize"
        )
    _require_member(user_id, int(shop_id), db_path or "")

    shop_name = wo.get("shop_name") or "—"
    customer = wo.get("customer_name") or "—"
    vehicle_line = " ".join(
        str(x) for x in (
            wo.get("vehicle_year"),
            wo.get("vehicle_make"),
            wo.get("vehicle_model"),
        )
        if x
    ) or "—"

    sections: list[dict] = []

    sections.append({
        "heading": "Shop & customer",
        "rows": [
            ("Shop", shop_name),
            ("Customer", customer),
            ("Customer phone", wo.get("customer_phone") or "—"),
            ("Customer email", wo.get("customer_email") or "—"),
            ("Vehicle", vehicle_line),
        ],
    })

    # WO header
    sections.append({
        "heading": "Work order",
        "rows": [
            ("WO number",
             str(wo.get("wo_number") or wo.get("id") or "—")),
            ("Status", str(wo.get("status") or "—")),
            ("Priority", str(wo.get("priority") or "—")),
            ("Intake", str(wo.get("intake_at") or "—")),
            ("Assigned", str(wo.get("assigned_mechanic_name") or "—")),
        ],
    })

    if wo.get("intake_problems"):
        sections.append({
            "heading": "Reported problems",
            "body": str(wo["intake_problems"]),
        })

    # Issues
    issues = list_issues(
        work_order_id=wo_id, include_terminal=True,
        limit=500, db_path=db_path,
    )
    if issues:
        issue_rows = [
            [
                str(i.get("category") or "—"),
                str(i.get("severity") or "—"),
                str(i.get("status") or "—"),
                str(i.get("description") or ""),
            ]
            for i in issues
        ]
        sections.append({
            "heading": "Issues",
            "table": {
                "columns": ["Category", "Severity", "Status", "Description"],
                "rows": issue_rows,
            },
        })

    # Parts
    parts = list_parts_for_wo(
        wo_id, include_cancelled=True, db_path=db_path,
    )
    if parts:
        parts_rows: list[list[str]] = []
        for p in parts:
            qty = int(p.get("quantity") or 0)
            unit_cents = int(p.get("unit_cost_cents") or 0)
            line_cents = int(p.get("line_subtotal_cents") or 0)
            parts_rows.append([
                str(p.get("description") or p.get("part_slug") or "—"),
                str(qty),
                _money(unit_cents),
                _money(line_cents),
                str(p.get("status") or "—"),
            ])
        sections.append({
            "heading": "Parts",
            "table": {
                "columns": ["Part", "Qty", "Unit", "Line", "Status"],
                "rows": parts_rows,
            },
        })

    # Labor
    labor_rows: list[tuple[str, str]] = []
    if wo.get("estimated_hours") is not None:
        labor_rows.append((
            "Estimated hours", f"{float(wo['estimated_hours']):.2f}",
        ))
    if wo.get("actual_hours") is not None:
        labor_rows.append((
            "Actual hours", f"{float(wo['actual_hours']):.2f}",
        ))
    if labor_rows:
        sections.append({
            "heading": "Labor",
            "rows": labor_rows,
        })

    # Notes
    if wo.get("notes"):
        sections.append({
            "heading": "Notes",
            "body": str(wo["notes"]),
        })

    return {
        "title": (
            f"Work order receipt — "
            f"{wo.get('wo_number') or f'#{wo_id}'}"
        ),
        "subtitle": f"{shop_name} — {customer}",
        "issued_at": _now_iso(),
        "sections": sections,
        "footer": _footer(f"WO #{wo_id}"),
    }


# ---------------------------------------------------------------------------
# Invoice report
# ---------------------------------------------------------------------------


def build_invoice_report_doc(
    invoice_id: int,
    user_id: int,
    db_path: Optional[str] = None,
) -> ReportDocument:
    """Build an invoice PDF document.

    Shop-scoped via the invoice's work order — caller must be an
    active member of the WO's shop. Composes Phase 169
    :func:`get_invoice_with_items`.
    """
    inv = get_invoice_with_items(invoice_id, db_path=db_path)
    if inv is None:
        raise InvoiceNotFoundError(f"invoice not found: id={invoice_id}")

    wo_id = inv.work_order_id
    wo = None
    shop_id: Optional[int] = None
    shop_info: Optional[dict] = None
    if wo_id is not None:
        wo = get_work_order(int(wo_id), db_path=db_path)
        if wo is not None:
            shop_id = wo.get("shop_id")

    if shop_id is None:
        raise ReportBuildError(
            f"invoice id={invoice_id} has no resolvable shop "
            "— cannot authorize"
        )
    _require_member(user_id, int(shop_id), db_path or "")
    shop_info = get_shop(int(shop_id), db_path=db_path)

    shop_name = (shop_info or {}).get("name") if shop_info else None
    shop_phone = (shop_info or {}).get("phone") if shop_info else None
    shop_address = (shop_info or {}).get("address") if shop_info else None

    customer = inv.customer_name or "—"

    sections: list[dict] = []

    sections.append({
        "heading": "From",
        "rows": [
            ("Shop", str(shop_name or "—")),
            ("Address", str(shop_address or "—")),
            ("Phone", str(shop_phone or "—")),
        ],
    })

    sections.append({
        "heading": "Bill to",
        "rows": [
            ("Customer", customer),
            ("Work order", str(wo_id) if wo_id else "—"),
            ("Invoice #", str(inv.invoice_number or inv.id)),
            ("Status", str(inv.status)),
            ("Issued", str(inv.issued_at or "—")),
            ("Due", str(inv.due_at or "—")),
            ("Paid", str(inv.paid_at or "—")),
        ],
    })

    # Line items
    item_rows = [
        [
            item.item_type,
            item.description or "—",
            f"{item.quantity:g}",
            _money(item.unit_price_cents),
            _money(item.line_total_cents),
        ]
        for item in inv.items
    ]
    if item_rows:
        sections.append({
            "heading": "Line items",
            "table": {
                "columns": ["Type", "Description", "Qty", "Unit", "Line"],
                "rows": item_rows,
            },
        })

    # Totals
    sections.append({
        "heading": "Totals",
        "rows": [
            ("Subtotal", _money(inv.subtotal_cents)),
            ("Tax", _money(inv.tax_cents)),
            ("Total", _money(inv.total_cents)),
        ],
    })

    if inv.notes:
        sections.append({
            "heading": "Notes",
            "body": str(inv.notes),
        })

    return {
        "title": f"Invoice {inv.invoice_number or f'#{inv.id}'}",
        "subtitle": f"{shop_name or ''} — {customer}".strip(" —"),
        "issued_at": inv.issued_at or _now_iso(),
        "sections": sections,
        "footer": _footer(f"Invoice {inv.invoice_number or inv.id}"),
    }
