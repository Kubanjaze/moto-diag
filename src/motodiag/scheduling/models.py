"""Scheduling Pydantic models."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AppointmentType(str, Enum):
    PPI = "ppi"
    DIAGNOSTIC = "diagnostic"
    SERVICE = "service"
    CONSULTATION = "consultation"


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Appointment(BaseModel):
    id: Optional[int] = None
    customer_id: int
    vehicle_id: Optional[int] = None
    user_id: Optional[int] = Field(None, description="Assigned mechanic user_id")
    appointment_type: AppointmentType = AppointmentType.SERVICE
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    scheduled_start: str = Field(..., description="ISO 8601 datetime string")
    scheduled_end: str = Field(..., description="ISO 8601 datetime string")
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    notes: Optional[str] = None
