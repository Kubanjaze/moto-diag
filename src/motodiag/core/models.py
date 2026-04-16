"""Base data models shared across all tracks."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DiagnosticStatus(str, Enum):
    """Status of a diagnostic session."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DIAGNOSED = "diagnosed"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Severity(str, Enum):
    """Severity level for diagnostic findings."""
    CRITICAL = "critical"   # Safety risk — stop riding
    HIGH = "high"           # Ride-home only, fix ASAP
    MEDIUM = "medium"       # Fix soon, degraded performance
    LOW = "low"             # Minor, fix at next service
    INFO = "info"           # Informational only


class SymptomCategory(str, Enum):
    """Top-level symptom categories."""
    ENGINE = "engine"
    ELECTRICAL = "electrical"
    FUEL = "fuel"
    DRIVETRAIN = "drivetrain"
    BRAKES = "brakes"
    SUSPENSION = "suspension"
    EXHAUST = "exhaust"
    COOLING = "cooling"
    STARTING = "starting"
    IDLE = "idle"
    NOISE = "noise"
    VIBRATION = "vibration"
    OTHER = "other"


class ProtocolType(str, Enum):
    """OBD/ECU communication protocols."""
    CAN = "can"             # ISO 15765 — modern bikes (2011+ Harley, Euro 4/5)
    K_LINE = "k_line"       # ISO 14230 / KWP2000 — 90s/2000s Japanese bikes
    J1850 = "j1850"         # SAE J1850 — older Harleys
    PROPRIETARY = "proprietary"  # Manufacturer-specific
    NONE = "none"           # No electronic diagnostics (older carb bikes)


class VehicleBase(BaseModel):
    """Base vehicle information."""
    make: str = Field(..., description="Manufacturer (e.g., Harley-Davidson, Honda)")
    model: str = Field(..., description="Model name (e.g., Sportster 1200, CBR929RR)")
    year: int = Field(..., ge=1970, le=2030, description="Model year")
    engine_cc: Optional[int] = Field(None, description="Engine displacement in cc")
    vin: Optional[str] = Field(None, description="Vehicle Identification Number")
    protocol: ProtocolType = Field(ProtocolType.NONE, description="ECU protocol type")
    notes: Optional[str] = None


class DiagnosticSessionBase(BaseModel):
    """Base diagnostic session."""
    id: Optional[str] = None
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    status: DiagnosticStatus = DiagnosticStatus.OPEN
    symptoms: list[str] = Field(default_factory=list)
    fault_codes: list[str] = Field(default_factory=list)
    diagnosis: Optional[str] = None
    repair_steps: list[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    severity: Optional[Severity] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class DTCCode(BaseModel):
    """Diagnostic Trouble Code."""
    code: str = Field(..., description="DTC code (e.g., P0115, B1004)")
    description: str = Field(..., description="Plain-English description")
    category: SymptomCategory
    severity: Severity = Severity.MEDIUM
    make: Optional[str] = Field(None, description="Manufacturer-specific (None = generic)")
    common_causes: list[str] = Field(default_factory=list)
    fix_summary: Optional[str] = None
