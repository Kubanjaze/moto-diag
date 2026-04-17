"""Appointment repository."""

from datetime import datetime
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.scheduling.models import (
    Appointment, AppointmentType, AppointmentStatus,
)


def create_appointment(appt: Appointment, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO appointments
               (customer_id, vehicle_id, user_id, appointment_type, status,
                scheduled_start, scheduled_end, actual_start, actual_end, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                appt.customer_id, appt.vehicle_id, appt.user_id,
                appt.appointment_type.value, appt.status.value,
                appt.scheduled_start, appt.scheduled_end,
                appt.actual_start, appt.actual_end, appt.notes,
            ),
        )
        return cursor.lastrowid


def get_appointment(appt_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM appointments WHERE id = ?", (appt_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_appointments(
    customer_id: Optional[int] = None,
    status: AppointmentStatus | str | None = None,
    appointment_type: AppointmentType | str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM appointments WHERE 1=1"
    params: list = []
    if customer_id is not None:
        query += " AND customer_id = ?"
        params.append(customer_id)
    if status is not None:
        s = status.value if isinstance(status, AppointmentStatus) else status
        query += " AND status = ?"
        params.append(s)
    if appointment_type is not None:
        t = appointment_type.value if isinstance(appointment_type, AppointmentType) else appointment_type
        query += " AND appointment_type = ?"
        params.append(t)
    query += " ORDER BY scheduled_start"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def list_upcoming(
    from_iso: Optional[str] = None, db_path: str | None = None,
) -> list[dict]:
    """List appointments scheduled >= from_iso (default: now), non-terminal status."""
    if from_iso is None:
        from_iso = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT * FROM appointments
               WHERE scheduled_start >= ?
               AND status IN ('scheduled', 'confirmed', 'in_progress')
               ORDER BY scheduled_start""",
            (from_iso,),
        )
        return [dict(r) for r in cursor.fetchall()]


def list_for_user(user_id: int, db_path: str | None = None) -> list[dict]:
    """List appointments assigned to a specific mechanic user_id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM appointments WHERE user_id = ? ORDER BY scheduled_start",
            (user_id,),
        )
        return [dict(r) for r in cursor.fetchall()]


def update_appointment(appt_id: int, db_path: str | None = None, **fields) -> bool:
    if not fields:
        return False
    for k in ("appointment_type", "status"):
        v = fields.get(k)
        if hasattr(v, "value"):
            fields[k] = v.value
    keys = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [appt_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE appointments SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def cancel_appointment(
    appt_id: int, reason: Optional[str] = None, db_path: str | None = None,
) -> bool:
    fields = {"status": "cancelled"}
    if reason:
        fields["notes"] = reason
    return update_appointment(appt_id, db_path=db_path, **fields)


def complete_appointment(
    appt_id: int, actual_end: Optional[str] = None, db_path: str | None = None,
) -> bool:
    fields = {
        "status": "completed",
        "actual_end": actual_end or datetime.now().isoformat(),
    }
    return update_appointment(appt_id, db_path=db_path, **fields)


def delete_appointment(appt_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM appointments WHERE id = ?", (appt_id,),
        )
        return cursor.rowcount > 0
