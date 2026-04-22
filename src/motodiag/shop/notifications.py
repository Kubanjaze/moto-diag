"""Customer notifications — persistence + rendering (Phase 170).

Queue-only: this module writes rendered notifications to
``customer_notifications`` with status='pending' and expects a future
transport layer (Phase 181+ or an operator's own integration) to pick
up, send, and flip status via :func:`mark_notification_sent` /
:func:`mark_notification_failed`. Zero network, zero AI.

Lifecycle (mirrors Phase 161 guarded pattern)::

    pending → sent      (terminal)
    pending → failed    (terminal)
    pending → cancelled (terminal)

``resend_notification`` creates a NEW pending row rather than mutating
the prior one — preserves failure audit trail.
"""

from __future__ import annotations

import json as _json
import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from motodiag.accounting.invoice_repo import (
    get_invoice as _get_invoice_row,
    get_line_items as _get_invoice_line_items,
)
from motodiag.core.database import get_connection
from motodiag.shop.notification_templates import (
    NOTIFICATION_CHANNELS,
    NOTIFICATION_EVENTS,
    NotificationChannel,
    NotificationEvent,
    TemplateNotFoundError,
    UnknownEventError,
    get_template,
    list_templates as _list_templates_raw,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class NotificationContextError(ValueError):
    """Can't assemble the template context (missing WO, customer, etc.)."""


class NotificationNotFoundError(ValueError):
    """Raised when a notification_id does not resolve."""


class InvalidNotificationTransition(ValueError):
    """Raised when attempting an illegal status transition."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


NOTIFICATION_STATUSES: tuple[str, ...] = (
    "pending", "sent", "failed", "cancelled",
)

NotificationStatus = Literal["pending", "sent", "failed", "cancelled"]


_VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"sent", "failed", "cancelled"},
    "sent": set(),
    "failed": set(),
    "cancelled": set(),
}


# ---------------------------------------------------------------------------
# Pydantic
# ---------------------------------------------------------------------------


class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    customer_id: int
    shop_id: int
    work_order_id: Optional[int]
    invoice_id: Optional[int]
    event: str
    channel: str
    recipient: str
    subject: Optional[str]
    body: str
    status: str
    failure_reason: Optional[str]
    triggered_by_user_id: Optional[int]
    triggered_at: str
    sent_at: Optional[str]
    updated_at: Optional[str]


class NotificationPreview(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event: str
    channel: str
    recipient: str
    subject: Optional[str]
    body: str
    context_keys: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers: context assembly
# ---------------------------------------------------------------------------


_DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_DAY_LABEL_SHORT = {
    "mon": "M", "tue": "T", "wed": "W", "thu": "Th",
    "fri": "F", "sat": "Sa", "sun": "Su",
}


def _format_hours_line(hours_json: Optional[str]) -> tuple[str, str]:
    """Return (long_form, short_form) for shop hours.

    Long form is used in email bodies ("Pickup hours: Mon-Fri 8am-5pm,
    Sat 9am-3pm"); short is for SMS ("M-F 8-5, Sa 9-3"). Both fall back
    to "(call for hours)" on missing/invalid input.
    """
    fallback = ("Pickup hours: call $shop_phone", "call for hours")
    if not hours_json:
        return fallback
    try:
        parsed = _json.loads(hours_json)
    except (ValueError, TypeError):
        return fallback
    if not isinstance(parsed, dict) or not parsed:
        return fallback
    # Render in day order
    chunks: list[str] = []
    short_chunks: list[str] = []
    for d in _DAY_NAMES:
        if d not in parsed:
            continue
        v = str(parsed[d] or "").strip()
        if not v:
            continue
        chunks.append(f"{d.capitalize()} {v}")
        short_chunks.append(f"{_DAY_LABEL_SHORT[d]} {v}")
    if not chunks:
        return fallback
    return ("Pickup hours: " + ", ".join(chunks), ", ".join(short_chunks))


def _first_name(full_name: Optional[str]) -> str:
    if not full_name:
        return "there"
    parts = str(full_name).split()
    return parts[0] if parts else "there"


def _money(dollars) -> str:
    try:
        v = float(dollars or 0.0)
    except (ValueError, TypeError):
        v = 0.0
    return f"{v:,.2f}"


def _bike_label(veh: Optional[dict]) -> str:
    if not veh:
        return "bike"
    parts = [
        str(veh.get("year") or "").strip(),
        str(veh.get("make") or "").strip(),
        str(veh.get("model") or "").strip(),
    ]
    return " ".join(p for p in parts if p) or "bike"


def _load_wo(wo_id: int, db_path: Optional[str] = None) -> dict:
    from motodiag.shop.work_order_repo import get_work_order
    wo = get_work_order(wo_id, db_path=db_path)
    if wo is None:
        raise NotificationContextError(
            f"work order not found: id={wo_id}"
        )
    return dict(wo)


def _load_customer(customer_id: int, db_path: Optional[str] = None) -> dict:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,),
        ).fetchone()
    if row is None:
        raise NotificationContextError(
            f"customer not found: id={customer_id}"
        )
    return dict(row)


def _load_shop(shop_id: int, db_path: Optional[str] = None) -> dict:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM shops WHERE id = ?", (shop_id,),
        ).fetchone()
    if row is None:
        raise NotificationContextError(
            f"shop not found: id={shop_id}"
        )
    return dict(row)


def _load_vehicle(vehicle_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM vehicles WHERE id = ?", (vehicle_id,),
        ).fetchone()
    return dict(row) if row else None


def _load_invoice(invoice_id: int, db_path: Optional[str] = None) -> dict:
    row = _get_invoice_row(invoice_id, db_path=db_path)
    if row is None:
        raise NotificationContextError(
            f"invoice not found: id={invoice_id}"
        )
    return dict(row)


def _invoice_for_wo(wo_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM invoices WHERE work_order_id = ? "
            "AND status != 'cancelled' "
            "ORDER BY id DESC LIMIT 1",
            (wo_id,),
        ).fetchone()
    return dict(row) if row else None


def _parts_list_for_wo(wo_id: int, db_path: Optional[str] = None) -> str:
    """Comma-joined description of parts currently on the WO.

    For parts_arrived / estimate_ready. Falls back to "(no parts)" when
    the WO has none yet.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT p.description, p.slug, wop.quantity, wop.status
               FROM work_order_parts wop
               JOIN parts p ON p.id = wop.part_id
               WHERE wop.work_order_id = ?
                 AND wop.status != 'cancelled'
               ORDER BY wop.id""",
            (wo_id,),
        ).fetchall()
    if not rows:
        return "(no parts)"
    chunks = []
    for r in rows:
        qty = int(r["quantity"] or 1)
        desc = (r["description"] or r["slug"] or "part").strip()
        chunks.append(f"{qty}× {desc}")
    return ", ".join(chunks)


def _recipient_for(
    customer: dict, channel: str,
) -> str:
    """Pick the right contact field for the channel.

    email → customer.email (required for email)
    sms → customer.phone (required for sms)
    in_app → customer.name (always available; in-shop dashboard)
    """
    if channel == "email":
        email = (customer.get("email") or "").strip()
        if not email:
            raise NotificationContextError(
                f"customer id={customer['id']} has no email; set one "
                "first or pick channel=sms/in_app"
            )
        return email
    if channel == "sms":
        phone = (customer.get("phone") or "").strip()
        if not phone:
            raise NotificationContextError(
                f"customer id={customer['id']} has no phone; set one "
                "first or pick channel=email/in_app"
            )
        return phone
    # in_app
    return (customer.get("name") or f"customer#{customer['id']}").strip()


def _load_event_context(
    event: str,
    *,
    wo_id: Optional[int] = None,
    invoice_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> tuple[dict, dict, dict, Optional[dict], Optional[dict]]:
    """Assemble (context_dict, customer, shop, wo, invoice).

    Resolution rules:
    - If wo_id given, load WO + its customer + its shop + its vehicle.
    - Else if invoice_id given, load invoice + customer + shop (via
      invoice.work_order_id if present).
    - Else customer_id required; shop resolved to customer's first
      active shop if a WO doesn't tell us otherwise.
    """
    wo: Optional[dict] = None
    invoice: Optional[dict] = None
    vehicle: Optional[dict] = None

    if wo_id is not None:
        wo = _load_wo(wo_id, db_path=db_path)
        customer_id = wo["customer_id"]
        shop_id = wo["shop_id"]
        if wo.get("vehicle_id"):
            vehicle = _load_vehicle(wo["vehicle_id"], db_path=db_path)
        if invoice_id is not None:
            invoice = _load_invoice(invoice_id, db_path=db_path)
        else:
            invoice = _invoice_for_wo(wo_id, db_path=db_path)
    elif invoice_id is not None:
        invoice = _load_invoice(invoice_id, db_path=db_path)
        customer_id = invoice["customer_id"]
        wo_id_from_inv = invoice.get("work_order_id")
        if wo_id_from_inv:
            wo = _load_wo(wo_id_from_inv, db_path=db_path)
            shop_id = wo["shop_id"]
            if wo.get("vehicle_id"):
                vehicle = _load_vehicle(
                    wo["vehicle_id"], db_path=db_path,
                )
        else:
            raise NotificationContextError(
                f"invoice id={invoice_id} has no work_order_id; cannot "
                "resolve shop — pass wo_id or customer_id + shop context"
            )
    elif customer_id is not None:
        # Freeform message to a customer with no WO/invoice. Pick
        # customer's most-recent-WO's shop.
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT shop_id FROM work_orders WHERE customer_id = ? "
                "ORDER BY id DESC LIMIT 1",
                (customer_id,),
            ).fetchone()
        if row is None:
            raise NotificationContextError(
                f"customer id={customer_id} has no work orders; cannot "
                "infer shop — pass wo_id or invoice_id"
            )
        shop_id = int(row["shop_id"])
    else:
        raise NotificationContextError(
            "one of wo_id, invoice_id, customer_id must be provided"
        )

    customer = _load_customer(customer_id, db_path=db_path)
    shop = _load_shop(shop_id, db_path=db_path)
    hours_long, hours_short = _format_hours_line(shop.get("hours_json"))

    ctx: dict = {
        "customer_first": _first_name(customer.get("name")),
        "customer_name": customer.get("name") or "customer",
        "shop_name": shop.get("name") or "your shop",
        "shop_phone": shop.get("phone") or "(phone on file)",
        "shop_hours_line": hours_long,
        "shop_hours_short": hours_short,
        "bike_label": _bike_label(vehicle),
        "wo_id": wo["id"] if wo else (invoice.get("work_order_id") if invoice else 0),
        "wo_title": (wo or {}).get("title") or "service",
        "wo_status": (wo or {}).get("status") or "",
        "hold_reason": (wo or {}).get("on_hold_reason") or "",
        "cancellation_reason": (wo or {}).get("cancellation_reason") or "",
        "invoice_number": (invoice or {}).get("invoice_number") or "",
        "invoice_total": _money((invoice or {}).get("total")),
    }
    # Event-specific extras
    if event in ("parts_arrived", "estimate_ready") and wo:
        ctx["parts_list"] = _parts_list_for_wo(wo["id"], db_path=db_path)
    if event == "estimate_ready":
        hrs = (wo or {}).get("estimated_hours") or 0.0
        ctx["estimate_labor_hours"] = f"{float(hrs):.1f}"
        labor = float(hrs or 0) * 100.0  # rough placeholder if no invoice
        if invoice and invoice.get("total"):
            ctx["estimate_total"] = _money(invoice["total"])
        else:
            ctx["estimate_total"] = _money(labor)
    if event == "approval_requested":
        # These come from extra_context overlay; set defaults for safety.
        ctx.setdefault("approval_finding", "(unspecified)")
        ctx.setdefault("approval_cost", "0.00")
    return ctx, customer, shop, wo, invoice


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def preview_notification(
    event: str,
    *,
    wo_id: Optional[int] = None,
    invoice_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    channel: str = "email",
    extra_context: Optional[dict] = None,
    db_path: Optional[str] = None,
) -> NotificationPreview:
    """Render (event, channel) without persisting."""
    if event not in NOTIFICATION_EVENTS:
        raise UnknownEventError(
            f"event {event!r} not in {NOTIFICATION_EVENTS}"
        )
    if channel not in NOTIFICATION_CHANNELS:
        raise ValueError(
            f"channel {channel!r} not in {NOTIFICATION_CHANNELS}"
        )

    ctx, customer, _shop, _wo, _inv = _load_event_context(
        event,
        wo_id=wo_id, invoice_id=invoice_id,
        customer_id=customer_id, db_path=db_path,
    )
    if extra_context:
        ctx.update(extra_context)

    tmpl = get_template(event, channel)
    try:
        subject, body = tmpl.render(ctx)
    except KeyError as e:
        raise NotificationContextError(
            f"template ({event!r},{channel!r}) missing placeholder {e.args[0]!r}; "
            f"pass via extra_context={{{e.args[0]!r}: ...}}"
        ) from e
    recipient = _recipient_for(customer, channel)
    return NotificationPreview(
        event=event, channel=channel, recipient=recipient,
        subject=subject, body=body,
        context_keys=sorted(ctx.keys()),
    )


def trigger_notification(
    event: str,
    *,
    wo_id: Optional[int] = None,
    invoice_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    channel: str = "email",
    extra_context: Optional[dict] = None,
    triggered_by_user_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> int:
    """Render + persist a pending notification. Returns notification_id."""
    preview = preview_notification(
        event,
        wo_id=wo_id, invoice_id=invoice_id, customer_id=customer_id,
        channel=channel, extra_context=extra_context, db_path=db_path,
    )
    # Re-resolve customer / shop ids from context for persistence; we
    # already validated them inside _load_event_context.
    ctx, customer, shop, wo, invoice = _load_event_context(
        event,
        wo_id=wo_id, invoice_id=invoice_id,
        customer_id=customer_id, db_path=db_path,
    )
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO customer_notifications
               (customer_id, shop_id, work_order_id, invoice_id,
                event, channel, recipient, subject, body, status,
                triggered_by_user_id, triggered_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
            (
                int(customer["id"]), int(shop["id"]),
                int(wo["id"]) if wo else None,
                int(invoice["id"]) if invoice else None,
                event, channel, preview.recipient,
                preview.subject, preview.body,
                triggered_by_user_id, now, now,
            ),
        )
        return int(cursor.lastrowid)


def get_notification(
    notification_id: int, db_path: Optional[str] = None,
) -> Optional[Notification]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM customer_notifications WHERE id = ?",
            (notification_id,),
        ).fetchone()
    if row is None:
        return None
    return Notification(**dict(row))


def _assert_transition(current: str, target: str) -> None:
    if target not in _VALID_TRANSITIONS.get(current, set()):
        raise InvalidNotificationTransition(
            f"cannot transition {current!r} → {target!r}; "
            f"legal transitions from {current!r}: "
            f"{sorted(_VALID_TRANSITIONS.get(current, set()))}"
        )


def _transition(
    notification_id: int,
    target: NotificationStatus,
    *,
    db_path: Optional[str] = None,
    **fields,
) -> bool:
    """Guarded status transition + optional field updates."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT status FROM customer_notifications WHERE id = ?",
            (notification_id,),
        ).fetchone()
        if row is None:
            raise NotificationNotFoundError(
                f"notification not found: id={notification_id}"
            )
        _assert_transition(row["status"], target)
        cols = ["status = ?", "updated_at = ?"]
        params: list = [target, now]
        for k, v in fields.items():
            cols.append(f"{k} = ?")
            params.append(v)
        params.append(notification_id)
        cursor = conn.execute(
            f"UPDATE customer_notifications SET {', '.join(cols)} "
            f"WHERE id = ?",
            params,
        )
        return cursor.rowcount > 0


def mark_notification_sent(
    notification_id: int,
    sent_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    stamp = sent_at or datetime.now(timezone.utc).isoformat()
    return _transition(
        notification_id, "sent", db_path=db_path, sent_at=stamp,
    )


def mark_notification_failed(
    notification_id: int,
    failure_reason: str,
    db_path: Optional[str] = None,
) -> bool:
    if not failure_reason or not failure_reason.strip():
        raise ValueError("failure_reason required")
    return _transition(
        notification_id, "failed", db_path=db_path,
        failure_reason=failure_reason.strip(),
    )


def cancel_notification(
    notification_id: int,
    reason: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    kwargs: dict = {}
    if reason:
        kwargs["failure_reason"] = f"cancelled: {reason.strip()}"
    return _transition(
        notification_id, "cancelled", db_path=db_path, **kwargs,
    )


def resend_notification(
    notification_id: int, db_path: Optional[str] = None,
) -> int:
    """Create a NEW pending notification duplicating the source row.

    Source row status is untouched — failure/cancellation audit trail
    survives. Intended for cases where the transport layer reported a
    transient failure and the mechanic wants another attempt.
    """
    src = get_notification(notification_id, db_path=db_path)
    if src is None:
        raise NotificationNotFoundError(
            f"notification not found: id={notification_id}"
        )
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO customer_notifications
               (customer_id, shop_id, work_order_id, invoice_id,
                event, channel, recipient, subject, body, status,
                triggered_by_user_id, triggered_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
            (
                src.customer_id, src.shop_id, src.work_order_id,
                src.invoice_id, src.event, src.channel, src.recipient,
                src.subject, src.body, src.triggered_by_user_id,
                now, now,
            ),
        )
        return int(cursor.lastrowid)


def list_notifications(
    *,
    customer_id: Optional[int] = None,
    shop_id: Optional[int] = None,
    wo_id: Optional[int] = None,
    status: Optional[str] = None,
    event: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Composable filter query."""
    if status is not None and status not in NOTIFICATION_STATUSES:
        raise ValueError(
            f"status must be one of {NOTIFICATION_STATUSES}"
        )
    if event is not None and event not in NOTIFICATION_EVENTS:
        raise UnknownEventError(
            f"event {event!r} not in {NOTIFICATION_EVENTS}"
        )
    query = "SELECT * FROM customer_notifications WHERE 1=1"
    params: list = []
    if customer_id is not None:
        query += " AND customer_id = ?"
        params.append(customer_id)
    if shop_id is not None:
        query += " AND shop_id = ?"
        params.append(shop_id)
    if wo_id is not None:
        query += " AND work_order_id = ?"
        params.append(wo_id)
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if event is not None:
        query += " AND event = ?"
        params.append(event)
    if since:
        query += " AND triggered_at >= ?"
        params.append(since)
    query += " ORDER BY triggered_at DESC, id DESC"
    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(int(limit))
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def list_template_catalog() -> list[dict]:
    """Public wrapper for the template enumeration helper."""
    return _list_templates_raw()
