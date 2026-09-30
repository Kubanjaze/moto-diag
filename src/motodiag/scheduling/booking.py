"""Booking by shop staff: an appointment's time, mechanic, status and check-in.

An appointment is the customer's booking: who comes in, with which bike,
when, and which mechanic sees them. A bay slot (``shop/bay_scheduler.py``)
is where a work order's work happens. The two are linked through the work
order that :func:`check_in` opens or links, and neither is copied into the
other; ``calendar`` reads both.

**Times.** The shop records no time zone, so an appointment's times are
the shop's clock time as entered, stored without an offset. The bay
scheduler reads a naive entry as UTC and stores ``+00:00``; :func:`clock_time`
reads such a slot back as the clock time it was entered at. A slot with any
other offset is converted to UTC. The calendar and the overlap checks use
this one rule.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.crm import communication_repo
from motodiag.scheduling.appointment_repo import (
    create_appointment, get_appointment, update_appointment,
)
from motodiag.scheduling.models import Appointment, AppointmentType

ACTIVE_STATUSES: tuple[str, ...] = ("scheduled", "confirmed", "in_progress")

_MOVES: dict[str, frozenset[str]] = {
    "scheduled": frozenset({"confirmed", "in_progress", "cancelled", "no_show"}),
    "confirmed": frozenset({"confirmed", "in_progress", "cancelled", "no_show"}),
    "in_progress": frozenset({"completed"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
    "no_show": frozenset(),
}

WEEKDAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
SLOT_STEP_MINUTES = 15
CONFIRM_CHANNELS: tuple[str, ...] = ("phone", "sms", "email", "in_person")

TYPE_LABELS = {
    "ppi": "Pre-purchase inspection",
    "diagnostic": "Diagnostic",
    "service": "Service",
    "consultation": "Consultation",
}


class BookingError(ValueError):
    """A booking, a move or a status change that is refused, with the reason."""


# ---------------------------------------------------------------------------
# Times
# ---------------------------------------------------------------------------


def parse_entered_time(value: str) -> datetime:
    """A time as staff enter it: the shop's clock time, with no zone."""
    try:
        t = datetime.fromisoformat(str(value).strip().replace(" ", "T", 1))
    except ValueError as e:
        raise BookingError(
            f"not a date and time: {value!r} (use YYYY-MM-DDTHH:MM)"
        ) from e
    if t.tzinfo is not None:
        raise BookingError(
            f"enter the shop's clock time without a time zone: {value!r}"
        )
    return t.replace(second=0, microsecond=0)


def clock_time(value: str) -> datetime:
    """A stored time as the shop's clock time (the module docstring's rule)."""
    t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if t.tzinfo is None:
        return t
    if t.utcoffset() == timedelta(0):
        return t.replace(tzinfo=None)
    return t.astimezone(timezone.utc).replace(tzinfo=None)


def is_zoned_elsewhere(value: str) -> bool:
    """True for a stored time with an offset other than UTC's."""
    t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return t.tzinfo is not None and t.utcoffset() != timedelta(0)


def _stored(t: datetime) -> str:
    return t.isoformat(timespec="minutes")


def _overlaps(a_start: datetime, a_end: datetime,
              b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def require_appointment(appt_id: int, db_path: Optional[str] = None) -> dict:
    row = get_appointment(appt_id, db_path=db_path)
    if row is None:
        raise BookingError(f"appointment not found: id={appt_id}")
    return row


def _require_shop(conn, shop_id: int) -> dict:
    row = conn.execute("SELECT * FROM shops WHERE id = ?", (shop_id,)).fetchone()
    if row is None:
        raise BookingError(f"shop not found: id={shop_id}")
    return dict(row)


def active_member_ids(shop_id: int, db_path: Optional[str] = None) -> list[int]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT user_id FROM shop_members WHERE shop_id = ? AND is_active = 1 "
            "ORDER BY user_id",
            (shop_id,),
        ).fetchall()
    return [r["user_id"] for r in rows]


def user_label(user_id: Optional[int], db_path: Optional[str] = None) -> str:
    if user_id is None:
        return "no mechanic assigned"
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT username, full_name FROM users WHERE id = ?", (user_id,),
        ).fetchone()
    if row is None:
        return f"user {user_id}"
    return row["full_name"] or row["username"]


def _check_mechanic(conn, shop_id: int, user_id: int) -> None:
    row = conn.execute(
        "SELECT is_active FROM shop_members WHERE shop_id = ? AND user_id = ?",
        (shop_id, user_id),
    ).fetchone()
    if row is None or not row["is_active"]:
        raise BookingError(
            f"user id={user_id} is not an active member of shop id={shop_id}; "
            "add them with `motodiag shop member add` first"
        )


def _mechanic_clashes(conn, user_id: int, start: datetime, end: datetime,
                      exclude_id: Optional[int]) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM appointments WHERE user_id = ? AND status IN "
        "('scheduled', 'confirmed', 'in_progress') AND id != ?",
        (user_id, exclude_id or -1),
    ).fetchall()
    return [
        dict(r) for r in rows
        if _overlaps(start, end, clock_time(r["scheduled_start"]),
                     clock_time(r["scheduled_end"]))
    ]


def _bay_work_overlaps(conn, shop_id: int, user_id: int,
                       start: datetime, end: datetime) -> list[dict]:
    rows = conn.execute(
        """SELECT bss.id, bss.scheduled_start, bss.scheduled_end, bss.work_order_id,
                  sb.name AS bay_name
             FROM bay_schedule_slots bss
             JOIN shop_bays sb ON sb.id = bss.bay_id
             JOIN work_orders wo ON wo.id = bss.work_order_id
            WHERE sb.shop_id = ? AND wo.assigned_mechanic_user_id = ?
              AND bss.status IN ('planned', 'active')""",
        (shop_id, user_id),
    ).fetchall()
    return [
        dict(r) for r in rows
        if _overlaps(start, end, clock_time(r["scheduled_start"]),
                     clock_time(r["scheduled_end"]))
    ]


def _check_times(start: datetime, end: datetime) -> None:
    if end <= start:
        raise BookingError("an appointment must end after it starts")


def _clash_message(clashes: list[dict], who: str) -> str:
    c = clashes[0]
    return (
        f"{who} already has appointment #{c['id']} from "
        f"{c['scheduled_start']} to {c['scheduled_end']}; pick another time "
        "or mechanic (`motodiag shop appointment slots` lists free times)"
    )


def _bay_warnings(slots: list[dict]) -> list[str]:
    return [
        f"The mechanic has work order #{s['work_order_id']} in bay "
        f"{s['bay_name']} from {s['scheduled_start']} to {s['scheduled_end']}."
        for s in slots
    ]


# ---------------------------------------------------------------------------
# Booking and moving
# ---------------------------------------------------------------------------


def book(
    shop_id: int,
    customer_id: int,
    vehicle_id: int,
    start: str,
    end: str,
    appointment_type: str = "service",
    mechanic_user_id: Optional[int] = None,
    notes: Optional[str] = None,
    db_path: Optional[str] = None,
) -> tuple[int, list[str]]:
    """Book an appointment. Returns its id and any warnings.

    Refused: an end not after the start; an unknown shop, customer or bike;
    a customer of another shop; a bike not linked to the customer; a
    mechanic who is not an active member of the shop, or who already has an
    active appointment overlapping this one. An overlap with a bay slot of a
    work order assigned to the same mechanic is a warning.
    """
    t_start, t_end = parse_entered_time(start), parse_entered_time(end)
    _check_times(t_start, t_end)
    try:
        kind = AppointmentType(appointment_type)
    except ValueError as e:
        raise BookingError(f"unknown appointment type: {appointment_type!r}") from e
    with get_connection(db_path) as conn:
        _require_shop(conn, shop_id)
        customer = conn.execute(
            "SELECT id, name, shop_id FROM customers WHERE id = ?", (customer_id,),
        ).fetchone()
        if customer is None:
            raise BookingError(f"customer not found: id={customer_id}")
        if customer["shop_id"] is not None and customer["shop_id"] != shop_id:
            raise BookingError(
                f"{customer['name']} is a customer of shop id={customer['shop_id']}"
            )
        link = conn.execute(
            "SELECT 1 FROM customer_bikes WHERE customer_id = ? AND vehicle_id = ?",
            (customer_id, vehicle_id),
        ).fetchone()
        if link is None:
            raise BookingError(
                f"bike id={vehicle_id} is not linked to {customer['name']}; run "
                f"`motodiag shop customer link-bike {customer_id} --bike {vehicle_id}` first"
            )
        warnings: list[str] = []
        if mechanic_user_id is not None:
            _check_mechanic(conn, shop_id, mechanic_user_id)
            clashes = _mechanic_clashes(conn, mechanic_user_id, t_start, t_end, None)
            if clashes:
                raise BookingError(_clash_message(clashes, "The mechanic"))
            warnings = _bay_warnings(
                _bay_work_overlaps(conn, shop_id, mechanic_user_id, t_start, t_end))
    appt_id = create_appointment(
        Appointment(
            customer_id=customer_id, vehicle_id=vehicle_id,
            user_id=mechanic_user_id, appointment_type=kind,
            scheduled_start=_stored(t_start), scheduled_end=_stored(t_end),
            notes=notes, shop_id=shop_id,
        ),
        db_path=db_path,
    )
    return appt_id, warnings


def reschedule(appt_id: int, start: str, end: str,
               db_path: Optional[str] = None) -> list[str]:
    """Move an active appointment, with the same checks as booking."""
    appt = require_appointment(appt_id, db_path=db_path)
    if appt["status"] not in ("scheduled", "confirmed"):
        raise BookingError(
            f"appointment #{appt_id} is {appt['status']}; only a scheduled or "
            "confirmed appointment can be moved"
        )
    t_start, t_end = parse_entered_time(start), parse_entered_time(end)
    _check_times(t_start, t_end)
    warnings: list[str] = []
    if appt["user_id"] is not None:
        with get_connection(db_path) as conn:
            clashes = _mechanic_clashes(conn, appt["user_id"], t_start, t_end, appt_id)
            if clashes:
                raise BookingError(_clash_message(clashes, "The mechanic"))
            if appt["shop_id"] is not None:
                warnings = _bay_warnings(_bay_work_overlaps(
                    conn, appt["shop_id"], appt["user_id"], t_start, t_end))
    update_appointment(
        appt_id, db_path=db_path,
        scheduled_start=_stored(t_start), scheduled_end=_stored(t_end),
        updated_at=datetime.now().isoformat(timespec="seconds"),
    )
    return warnings


def _move(appt_id: int, to: str, db_path: Optional[str], **fields) -> dict:
    appt = require_appointment(appt_id, db_path=db_path)
    if to not in _MOVES[appt["status"]]:
        raise BookingError(
            f"appointment #{appt_id} is {appt['status']}; it cannot become {to}"
        )
    update_appointment(
        appt_id, db_path=db_path, status=to,
        updated_at=datetime.now().isoformat(timespec="seconds"), **fields,
    )
    return appt


def cancel(appt_id: int, reason: Optional[str] = None,
           db_path: Optional[str] = None) -> None:
    appt = require_appointment(appt_id, db_path=db_path)
    fields = {}
    if reason:
        notes = (appt["notes"] or "").strip()
        fields["notes"] = f"{notes} | Cancelled: {reason}".strip(" |")
    _move(appt_id, "cancelled", db_path, **fields)


def mark_no_show(appt_id: int, db_path: Optional[str] = None) -> None:
    _move(appt_id, "no_show", db_path)


def complete(appt_id: int, db_path: Optional[str] = None) -> None:
    _move(appt_id, "completed", db_path,
          actual_end=_stored(datetime.now()))


# ---------------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------------


def confirmation_text(appt: dict, db_path: Optional[str] = None) -> str:
    """The confirmation staff send or read out, from stored data only."""
    with get_connection(db_path) as conn:
        shop = dict(conn.execute(
            "SELECT * FROM shops WHERE id = ?", (appt["shop_id"],)).fetchone())
        bike = conn.execute(
            "SELECT year, make, model FROM vehicles WHERE id = ?",
            (appt["vehicle_id"],)).fetchone()
        customer = conn.execute(
            "SELECT name FROM customers WHERE id = ?", (appt["customer_id"],)).fetchone()
    start, end = clock_time(appt["scheduled_start"]), clock_time(appt["scheduled_end"])
    lines = [
        f"Hello {customer['name']},",
        f"your appointment at {shop['name']} is confirmed for "
        f"{start.strftime('%A %d %B %Y')}, {start.strftime('%H:%M')} to "
        f"{end.strftime('%H:%M')}.",
        f"What: {TYPE_LABELS.get(appt['appointment_type'], appt['appointment_type'])}.",
    ]
    if bike is not None:
        lines.append(
            f"Bike: {' '.join(str(p) for p in (bike['year'], bike['make'], bike['model']) if p)}.")
    if appt["user_id"] is not None:
        lines.append(f"Mechanic: {user_label(appt['user_id'], db_path)}.")
    place = ", ".join(p for p in (shop.get("address"), shop.get("city")) if p)
    region = " ".join(p for p in (shop.get("state"), shop.get("zip")) if p)
    where = ", ".join(p for p in (place, region) if p)
    if where:
        lines.append(f"Address: {where}.")
    if shop.get("phone"):
        lines.append(f"To change it, call {shop['phone']}.")
    return "\n".join(lines)


def confirm(appt_id: int, channel: str, by_user_id: Optional[int] = None,
            db_path: Optional[str] = None) -> tuple[str, int]:
    """Mark confirmed and log the confirmation as an outbound contact.

    Nothing is queued or sent: the staff send the returned text by their
    own means. Returns the text and the contact's id.
    """
    if channel not in CONFIRM_CHANNELS:
        raise BookingError(f"channel must be one of {', '.join(CONFIRM_CHANNELS)}")
    appt = require_appointment(appt_id, db_path=db_path)
    if appt["shop_id"] is None:
        raise BookingError(f"appointment #{appt_id} is not booked at a shop")
    if "confirmed" not in _MOVES[appt["status"]]:
        raise BookingError(
            f"appointment #{appt_id} is {appt['status']}; it cannot be confirmed"
        )
    text = confirmation_text(appt, db_path=db_path)
    contact_id = communication_repo.log_contact(
        appt["customer_id"], "outbound", channel,
        f"Appointment #{appt_id} confirmed.\n{text}",
        shop_id=appt["shop_id"], work_order_id=appt["work_order_id"],
        logged_by_user_id=by_user_id, db_path=db_path,
    )
    _move(appt_id, "confirmed", db_path)
    return text, contact_id


# ---------------------------------------------------------------------------
# Check-in
# ---------------------------------------------------------------------------


def check_in(appt_id: int, work_order_id: Optional[int] = None,
             created_by_user_id: int = 1,
             db_path: Optional[str] = None) -> tuple[int, bool]:
    """Open or link the appointment's work order. Returns (id, created)."""
    from motodiag.shop.work_order_repo import (
        TERMINAL_STATUSES, create_work_order, open_work_order,
    )

    appt = require_appointment(appt_id, db_path=db_path)
    if "in_progress" not in _MOVES[appt["status"]]:
        raise BookingError(
            f"appointment #{appt_id} is {appt['status']}; it cannot be checked in"
        )
    if appt["shop_id"] is None or appt["vehicle_id"] is None:
        raise BookingError(f"appointment #{appt_id} has no shop or no bike")
    created = False
    if work_order_id is not None:
        with get_connection(db_path) as conn:
            wo = conn.execute(
                "SELECT * FROM work_orders WHERE id = ?", (work_order_id,)).fetchone()
        if wo is None:
            raise BookingError(f"work order not found: id={work_order_id}")
        mismatches = [
            label for label, a, b in (
                ("shop", wo["shop_id"], appt["shop_id"]),
                ("customer", wo["customer_id"], appt["customer_id"]),
                ("bike", wo["vehicle_id"], appt["vehicle_id"]),
            ) if a != b
        ]
        if mismatches:
            raise BookingError(
                f"work order #{work_order_id} is for another {', '.join(mismatches)}"
            )
        if wo["status"] in TERMINAL_STATUSES:
            raise BookingError(
                f"work order #{work_order_id} is {wo['status']}")
    else:
        label = TYPE_LABELS.get(appt["appointment_type"], "Appointment")
        title = f"{label}: {appt['notes']}" if appt["notes"] else label
        work_order_id = create_work_order(
            appt["shop_id"], appt["vehicle_id"], appt["customer_id"], title,
            assigned_mechanic_user_id=appt["user_id"],
            created_by_user_id=created_by_user_id, db_path=db_path,
        )
        open_work_order(work_order_id, db_path=db_path)
        created = True
    _move(appt_id, "in_progress", db_path, work_order_id=work_order_id,
          actual_start=_stored(datetime.now()))
    return work_order_id, created


# ---------------------------------------------------------------------------
# Free time slots
# ---------------------------------------------------------------------------


def shop_hours(shop: dict, day: date) -> Optional[tuple[str, str]]:
    """The shop's opening and closing time on ``day``, from ``hours_json``.

    Returns None when the shop has no hours recorded at all. Raises
    :class:`BookingError` when the day is closed or its entry is not in the
    form ``"HH:MM-HH:MM"``.
    """
    raw = shop.get("hours_json")
    if raw is None or not str(raw).strip():
        return None
    hours = json.loads(raw)
    key = WEEKDAYS[day.weekday()]
    value = hours.get(key)
    if value is None or str(value).strip().lower() == "closed":
        raise BookingError(f"the shop is closed on {day.strftime('%A')}s")
    try:
        opens, closes = (p.strip() for p in str(value).split("-"))
        datetime.strptime(opens, "%H:%M")
        datetime.strptime(closes, "%H:%M")
    except ValueError as e:
        raise BookingError(
            f"the shop's hours for {key} read {value!r}; expected HH:MM-HH:MM"
        ) from e
    return opens, closes


def free_slots(
    shop_id: int,
    day: str,
    minutes: int,
    mechanic_user_id: Optional[int] = None,
    open_at: Optional[str] = None,
    close_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> dict[int, list[str]]:
    """Free start times (``HH:MM``) per mechanic on ``day``.

    Hours come from ``open_at``/``close_at`` when given, else from the
    shop's recorded hours; with neither, it refuses. Start times step by
    :data:`SLOT_STEP_MINUTES`, and a slot is free when the mechanic has no
    active appointment overlapping it.
    """
    if minutes <= 0:
        raise BookingError("the length must be at least one minute")
    try:
        the_day = date.fromisoformat(day)
    except ValueError as e:
        raise BookingError(f"not a date: {day!r} (use YYYY-MM-DD)") from e
    with get_connection(db_path) as conn:
        shop = _require_shop(conn, shop_id)
    if (open_at is None) != (close_at is None):
        raise BookingError("give both --open and --close, or neither")
    if open_at is None:
        hours = shop_hours(shop, the_day)
        if hours is None:
            raise BookingError(
                f"{shop['name']} has no opening hours recorded; pass --open and "
                "--close, or record them with `motodiag shop profile update "
                "--set hours_json='{\"mon\": \"08:00-17:00\", ...}'`"
            )
        open_at, close_at = hours
    opens = parse_entered_time(f"{day}T{open_at}")
    closes = parse_entered_time(f"{day}T{close_at}")
    if closes <= opens:
        raise BookingError("the shop must close after it opens")
    if mechanic_user_id is not None:
        with get_connection(db_path) as conn:
            _check_mechanic(conn, shop_id, mechanic_user_id)
        mechanics = [mechanic_user_id]
    else:
        mechanics = active_member_ids(shop_id, db_path=db_path)
        if not mechanics:
            raise BookingError(f"shop id={shop_id} has no active members")
    length = timedelta(minutes=minutes)
    step = timedelta(minutes=SLOT_STEP_MINUTES)
    result: dict[int, list[str]] = {}
    with get_connection(db_path) as conn:
        for user_id in mechanics:
            times: list[str] = []
            t = opens
            while t + length <= closes:
                if not _mechanic_clashes(conn, user_id, t, t + length, None):
                    times.append(t.strftime("%H:%M"))
                t += step
            result[user_id] = times
    return result


def list_for_shop(
    shop_id: int,
    from_day: Optional[str] = None,
    to_day: Optional[str] = None,
    mechanic_user_id: Optional[int] = None,
    status: Optional[str] = None,
    db_path: Optional[str] = None,
) -> list[dict]:
    """A shop's appointments, earliest first, with customer, bike and mechanic."""
    q = (
        "SELECT a.*, c.name AS customer_name, v.year AS bike_year, "
        "v.make AS bike_make, v.model AS bike_model "
        "FROM appointments a JOIN customers c ON c.id = a.customer_id "
        "LEFT JOIN vehicles v ON v.id = a.vehicle_id WHERE a.shop_id = ?"
    )
    params: list = [shop_id]
    if mechanic_user_id is not None:
        q += " AND a.user_id = ?"
        params.append(mechanic_user_id)
    if status is not None:
        q += " AND a.status = ?"
        params.append(status)
    with get_connection(db_path) as conn:
        rows = [dict(r) for r in conn.execute(q + " ORDER BY a.id", params).fetchall()]
    lo = datetime.fromisoformat(from_day) if from_day else None
    hi = datetime.fromisoformat(to_day) + timedelta(days=1) if to_day else None
    kept = [
        r for r in rows
        if (lo is None or clock_time(r["scheduled_end"]) > lo)
        and (hi is None or clock_time(r["scheduled_start"]) < hi)
    ]
    kept.sort(key=lambda r: (clock_time(r["scheduled_start"]), r["id"]))
    return kept
