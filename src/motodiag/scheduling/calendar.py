"""One calendar of a shop's appointments and bay slots, and its iCal file.

Both kinds are read live from their own tables each time; each entry comes
from exactly one row, and its UID names that row, so the calendar has no
store of its own that could disagree with the booking or the bay schedule.

The iCal output follows RFC 5545: CRLF line ends, lines folded at 75
octets, text escaped. Times follow ``booking``'s rule: the shop's clock
time, written without a zone (a "floating" time, shown at the same clock
time wherever it is opened), except a bay slot stored with an offset other
than UTC's, which is written in UTC.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.scheduling.booking import (
    TYPE_LABELS, clock_time, is_zoned_elsewhere, list_for_shop, user_label,
)

_APPOINTMENT_ICS_STATUS = {
    "scheduled": "TENTATIVE", "confirmed": "CONFIRMED", "in_progress": "CONFIRMED",
    "completed": "CONFIRMED", "cancelled": "CANCELLED", "no_show": "CANCELLED",
}
_SLOT_ICS_STATUS = {
    "planned": "TENTATIVE", "active": "CONFIRMED", "completed": "CONFIRMED",
    "overrun": "CONFIRMED", "cancelled": "CANCELLED",
}


def bike_label(row: dict) -> str:
    parts = [row.get("bike_year"), row.get("bike_make"), row.get("bike_model")]
    return " ".join(str(p) for p in parts if p) or "no bike recorded"


def calendar_entries(
    shop_id: int,
    from_day: str,
    to_day: str,
    mechanic_user_id: Optional[int] = None,
    bay_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Appointments and bay slots overlapping the days ``from_day``..``to_day``.

    With ``mechanic_user_id``: that mechanic's appointments and the slots of
    work orders assigned to them. With ``bay_id``: that bay's slots only.
    Each entry has ``kind``, ``id``, ``start``, ``end`` (clock times),
    ``in_utc``, ``status``, ``summary``, ``description``, ``location``,
    ``uid`` and ``ics_status``.
    """
    lo = datetime.fromisoformat(from_day)
    hi = datetime.fromisoformat(to_day) + timedelta(days=1)
    if hi <= lo:
        raise ValueError("the range must end on or after its first day")
    with get_connection(db_path) as conn:
        shop = conn.execute("SELECT * FROM shops WHERE id = ?", (shop_id,)).fetchone()
        if shop is None:
            raise ValueError(f"shop not found: id={shop_id}")
        shop_name = shop["name"]
        slot_rows = [dict(r) for r in conn.execute(
            """SELECT bss.*, sb.name AS bay_name, wo.title AS wo_title,
                      wo.assigned_mechanic_user_id AS mechanic_id
                 FROM bay_schedule_slots bss
                 JOIN shop_bays sb ON sb.id = bss.bay_id
                 LEFT JOIN work_orders wo ON wo.id = bss.work_order_id
                WHERE sb.shop_id = ? ORDER BY bss.id""",
            (shop_id,),
        ).fetchall()]

    entries: list[dict] = []
    if bay_id is None:
        for a in list_for_shop(shop_id, from_day, to_day,
                               mechanic_user_id=mechanic_user_id, db_path=db_path):
            label = TYPE_LABELS.get(a["appointment_type"], a["appointment_type"])
            description = [
                f"Customer: {a['customer_name']}",
                f"Bike: {bike_label(a)}",
                f"Mechanic: {user_label(a['user_id'], db_path)}",
                f"Status: {a['status'].replace('_', ' ')}",
            ]
            if a["work_order_id"]:
                description.append(f"Work order: #{a['work_order_id']}")
            if a["notes"]:
                description.append(f"Notes: {a['notes']}")
            entries.append({
                "kind": "appointment", "id": a["id"],
                "start": clock_time(a["scheduled_start"]),
                "end": clock_time(a["scheduled_end"]), "in_utc": False,
                "status": a["status"],
                "summary": f"{label}: {a['customer_name']} ({bike_label(a)})",
                "description": "\n".join(description),
                "location": shop_name,
                "uid": f"appointment-{a['id']}@motodiag-shop-{shop_id}",
                "ics_status": _APPOINTMENT_ICS_STATUS[a["status"]],
            })
    for s in slot_rows:
        if bay_id is not None and s["bay_id"] != bay_id:
            continue
        if mechanic_user_id is not None and s["mechanic_id"] != mechanic_user_id:
            continue
        start, end = clock_time(s["scheduled_start"]), clock_time(s["scheduled_end"])
        if not (start < hi and end > lo):
            continue
        wo = f"work order #{s['work_order_id']}" if s["work_order_id"] else "no work order"
        title = f": {s['wo_title']}" if s.get("wo_title") else ""
        entries.append({
            "kind": "bay_slot", "id": s["id"], "start": start, "end": end,
            "in_utc": is_zoned_elsewhere(s["scheduled_start"]),
            "status": s["status"],
            "summary": f"Bay {s['bay_name']}: {wo}{title}",
            "description": "\n".join([
                f"Bay: {s['bay_name']}",
                f"Mechanic: {user_label(s['mechanic_id'], db_path)}",
                f"Status: {s['status']}",
            ]),
            "location": f"{shop_name}, bay {s['bay_name']}",
            "uid": f"bay-slot-{s['id']}@motodiag-shop-{shop_id}",
            "ics_status": _SLOT_ICS_STATUS[s["status"]],
        })
    entries.sort(key=lambda e: (e["start"], e["kind"], e["id"]))
    return entries


# ---------------------------------------------------------------------------
# iCal (RFC 5545)
# ---------------------------------------------------------------------------


def escape_text(value: str) -> str:
    """Escape a TEXT value (RFC 5545 section 3.3.11)."""
    return (
        str(value).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
        .replace("\r\n", "\\n").replace("\n", "\\n")
    )


def fold_line(line: str) -> str:
    """Fold a content line at 75 octets, never inside a UTF-8 character."""
    out: list[str] = []
    current = ""
    limit = 75
    for ch in line:
        if len((current + ch).encode("utf-8")) > limit:
            out.append(current)
            current = " " + ch
            limit = 75
        else:
            current += ch
    out.append(current)
    return "\r\n".join(out)


def _ics_time(t: datetime, in_utc: bool) -> str:
    return t.strftime("%Y%m%dT%H%M%S") + ("Z" if in_utc else "")


def to_ics(entries: list[dict], calendar_name: str,
           now: Optional[datetime] = None) -> str:
    """The entries as one VCALENDAR, CRLF-terminated."""
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//MotoDiag//Shop calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(calendar_name)}",
    ]
    for e in entries:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{e['uid']}",
            f"DTSTAMP:{stamp.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{_ics_time(e['start'], e['in_utc'])}",
            f"DTEND:{_ics_time(e['end'], e['in_utc'])}",
            f"SUMMARY:{escape_text(e['summary'])}",
            f"DESCRIPTION:{escape_text(e['description'])}",
            f"LOCATION:{escape_text(e['location'])}",
            f"STATUS:{e['ics_status']}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "".join(fold_line(line) + "\r\n" for line in lines)
