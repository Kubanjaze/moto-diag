"""Scheduling package — appointments, booking by shop staff, and the calendar.

``appointment_repo`` is the CRUD; ``booking`` is what staff do with an
appointment (book, move, confirm, check in, close) and the free time slots;
``calendar`` reads appointments and bay slots together and writes iCal.
Phase 275 wired it (rows 275 and 276). Customer self-booking and Google
Calendar sync are paused (rows 363 and 364).
"""

from motodiag.scheduling.models import (
    AppointmentType, AppointmentStatus, Appointment,
)
from motodiag.scheduling.appointment_repo import (
    create_appointment, get_appointment, list_appointments,
    list_upcoming, list_for_user, update_appointment, cancel_appointment,
    complete_appointment, delete_appointment,
)

__all__ = [
    "AppointmentType", "AppointmentStatus", "Appointment",
    "create_appointment", "get_appointment", "list_appointments",
    "list_upcoming", "list_for_user", "update_appointment",
    "cancel_appointment", "complete_appointment", "delete_appointment",
]
