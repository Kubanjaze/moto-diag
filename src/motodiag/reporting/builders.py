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

Phase 192B extends :func:`build_session_report_doc` with optional
``preset`` + ``overrides`` parameters for composer-side section-
visibility filtering. Renderer stays pure (``ReportDocument →
flowables``) so PDF + JSON-preview both consume the same pre-
filtered document. The mobile-side semantics in
``moto-diag-mobile/src/screens/reportPresets.ts`` are mirrored
exactly (Customer hides ``Notes``; Insurance + Full hide nothing;
explicit override beats preset default).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from motodiag.core.session_repo import (
    SessionOwnershipError, get_session_for_owner,
)
from motodiag.core.video_repo import list_session_videos
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
# Section-visibility presets (Phase 192B)
# ---------------------------------------------------------------------------
#
# Composer-side filtering: ``build_session_report_doc`` accepts an
# optional ``preset`` + ``overrides`` and drops hidden sections
# BEFORE returning. The renderer stays pure (``ReportDocument →
# flowables``) so PDF + JSON-preview consume the same pre-filtered
# document. The mobile semantics in
# ``src/screens/reportPresets.ts`` are mirrored exactly here so the
# two codebases can't drift on which sections each preset hides
# (drift catchable via Phase 192B Commit 1's
# ``test_phase192b_preset_semantics_match_mobile`` cross-source pin).

ReportPreset = Literal["full", "customer", "insurance"]

# Customer-facing posture: hide diagnostic-internal sections that
# may carry mechanic-only commentary. Mirrors mobile
# ``CUSTOMER_HIDDEN_HEADINGS``. Heading match is case-sensitive +
# exact (matches the backend builder's section-iteration shape).
_CUSTOMER_HIDDEN_HEADINGS: tuple[str, ...] = ("Notes",)

# Insurance posture: full disclosure (claims docs need everything).
_INSURANCE_HIDDEN_HEADINGS: tuple[str, ...] = ()

# Full posture: show everything.
_FULL_HIDDEN_HEADINGS: tuple[str, ...] = ()


def _preset_hidden_headings(preset: ReportPreset) -> tuple[str, ...]:
    if preset == "customer":
        return _CUSTOMER_HIDDEN_HEADINGS
    if preset == "insurance":
        return _INSURANCE_HIDDEN_HEADINGS
    return _FULL_HIDDEN_HEADINGS


def _is_section_hidden(
    heading: str,
    preset: Optional[ReportPreset],
    overrides: Optional[dict[str, bool]],
) -> bool:
    """True iff the section is hidden under (preset + overrides).

    ``preset is None`` → no preset filter (full document, the
    Phase 182 default). Used by the unchanged GET ``/pdf`` route.

    Override semantics: an explicit ``True`` / ``False`` in the
    ``overrides`` dict ALWAYS wins over the preset default. Absence
    means "fall through to preset". Mirrors the mobile
    ``isSectionHidden(heading, preset, overrides)`` resolution.
    """
    if overrides is not None:
        explicit = overrides.get(heading)
        if explicit is True:
            return False  # explicit visible
        if explicit is False:
            return True   # explicit hidden
    if preset is None:
        return False
    return heading in _preset_hidden_headings(preset)


# ---------------------------------------------------------------------------
# Session report
# ---------------------------------------------------------------------------


def build_session_report_doc(
    session_id: int,
    user_id: int,
    db_path: Optional[str] = None,
    *,
    preset: Optional[ReportPreset] = None,
    overrides: Optional[dict[str, bool]] = None,
) -> ReportDocument:
    """Build a diagnostic-session report document.

    Owner-scoped: ``user_id`` must match the session's ``user_id``
    column (Phase 178 retrofit); otherwise
    :class:`SessionOwnershipError` is raised (maps to 404).

    Phase 192B: optional ``preset`` + ``overrides`` filter sections
    before returning. ``preset=None`` (default) returns the full
    document — back-compat with the Phase 182 GET ``/pdf`` route.
    The new POST ``/pdf`` route requires ``preset`` in the request
    body (FastAPI 422 if absent). ``overrides`` is reserved for
    future per-card UI (F28); the route does NOT yet expose it.
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

    # Videos (Phase 192) — variant 5 in
    # docs/architecture/report-document-shape.md. Omit-when-empty
    # per Pattern 1 (mirrors symptoms / fault_codes). For each
    # video card we surface required metadata + (only when
    # ``analysis_state == 'analyzed'``) a nested ``findings`` key
    # containing the verbatim ``VisualAnalysisResult.model_dump()``
    # shape persisted by Phase 191B's set_analysis_findings.
    videos = list_session_videos(int(row["id"]), db_path=db_path)
    if videos:
        video_cards: list[dict] = []
        for v in videos:
            file_path_value = v.get("file_path") or ""
            filename = (
                os.path.basename(str(file_path_value))
                if file_path_value
                else "—"
            )
            card: dict[str, Any] = {
                "video_id": int(v["id"]),
                "filename": filename,
                # Phase 191B videos table stores the capture
                # start time in ``started_at``; ``created_at`` is
                # the row-insert timestamp. ``started_at`` is the
                # right surface for ``captured_at``.
                "captured_at": str(v.get("started_at") or "—"),
                "duration_ms": int(v.get("duration_ms") or 0),
                "size_bytes": int(v.get("file_size_bytes") or 0),
                "interrupted": bool(v.get("interrupted")),
                "analysis_state": str(
                    v.get("analysis_state") or "pending"
                ),
                # Phase 192 Commit 1 added migration 040 which
                # introduces the ``analyzing_started_at`` column
                # (nullable, no default, no backfill per Contract
                # A). Pre-migration rows return ``None``; post-
                # migration ``pending → analyzing`` transitions
                # write the timestamp atomically with the state
                # via Contract B. Mobile stuck-detection branches
                # on the NULL check.
                "analyzing_started_at": v.get(
                    "analyzing_started_at"
                ),
            }
            # Findings key is OMITTED entirely (not present-with-
            # None) for any non-analyzed state. Renderers check
            # ``if "findings" in video`` per the shape doc.
            if card["analysis_state"] == "analyzed":
                findings_payload = v.get("analysis_findings")
                if findings_payload:
                    card["findings"] = findings_payload
            video_cards.append(card)
        sections.append({
            "heading": "Videos",
            "videos": video_cards,
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

    # Phase 192B: composer-side preset filter. ``preset=None``
    # (default) bypasses entirely → full document for the GET
    # ``/pdf`` route. The new POST ``/pdf`` route always passes
    # an explicit preset. Filter applied AFTER all sections are
    # built so the omit-when-empty logic for individual variants
    # is independent of the visibility filter.
    if preset is not None or overrides is not None:
        sections = [
            s for s in sections
            if not _is_section_hidden(
                str(s.get("heading", "")), preset, overrides,
            )
        ]

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
