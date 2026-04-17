"""Scheduling package — appointments substrate.

Phase 118 (Retrofit): schema + CRUD only. Track O phases 288-289 wire up
iCal/Google Calendar sync and customer-facing booking.
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
