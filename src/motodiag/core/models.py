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
    """OBD/ECU communication protocols.

    Core protocols: CAN, K_LINE, J1850, PROPRIETARY, NONE.
    Phase 110 (Retrofit): added European OEM-specific CAN variants.
    """
    CAN = "can"             # ISO 15765 — modern bikes (2011+ Harley, Euro 4/5)
    K_LINE = "k_line"       # ISO 14230 / KWP2000 — 90s/2000s Japanese bikes
    J1850 = "j1850"         # SAE J1850 — older Harleys
    BMW_K_CAN = "bmw_k_can"     # BMW K-CAN (body CAN) — R/K/S/F/G series
    DUCATI_CAN = "ducati_can"   # Ducati-specific CAN flavor, Marelli ECU
    KTM_CAN = "ktm_can"         # KTM-specific CAN, Keihin ECU
    PROPRIETARY = "proprietary"  # Manufacturer-specific
    NONE = "none"           # No electronic diagnostics (older carb bikes)


class PowertrainType(str, Enum):
    """Top-level powertrain classification.

    Phase 110 (Retrofit): introduces electric/hybrid distinction alongside ICE
    so downstream modules can gate electric-specific logic (HV safety, BMS,
    regen) without sprinkling make/model checks.
    """
    ICE = "ice"             # Internal combustion engine (gasoline)
    ELECTRIC = "electric"   # Battery-electric (Zero, LiveWire, Energica, Damon)
    HYBRID = "hybrid"       # Hybrid (rare in motorcycles but reserved)


class EngineType(str, Enum):
    """Engine cycle/configuration classification.

    Phase 110 (Retrofit): expanded from implicit 4-stroke-only to cover
    2-stroke (vintage sportbikes, off-road), electric motors, hybrid drives,
    and desmodromic valve trains (Ducati).
    """
    FOUR_STROKE = "four_stroke"         # Standard Otto cycle (most bikes)
    TWO_STROKE = "two_stroke"           # RD350/400, KDX/KMX, older off-road
    ELECTRIC_MOTOR = "electric_motor"   # PMAC, IPM, SRM for electric bikes
    HYBRID = "hybrid"                   # Hybrid powertrain
    DESMODROMIC = "desmodromic"         # Ducati-specific positively-closed valves


class BatteryChemistry(str, Enum):
    """Battery chemistry for electric motorcycles.

    Phase 110 (Retrofit): only meaningful when powertrain=ELECTRIC or HYBRID.
    Chemistry affects charging profiles, thermal management, BMS behavior,
    and degradation patterns.
    """
    LI_ION = "li_ion"       # Generic lithium-ion
    LFP = "lfp"             # Lithium iron phosphate (LiFePO4)
    NMC = "nmc"             # Nickel manganese cobalt
    NCA = "nca"             # Nickel cobalt aluminum
    LEAD_ACID = "lead_acid"  # Starter battery (ICE bikes) — included for completeness


class VehicleBase(BaseModel):
    """Base vehicle information.

    Phase 110 (Retrofit): added optional powertrain/engine_type/battery
    fields. Defaults (ICE, four_stroke, no battery chemistry) preserve
    backward compatibility — existing code that doesn't set these gets
    sensible ICE-bike behavior.
    """
    make: str = Field(..., description="Manufacturer (e.g., Harley-Davidson, Honda)")
    model: str = Field(..., description="Model name (e.g., Sportster 1200, CBR929RR)")
    year: int = Field(..., ge=1970, le=2030, description="Model year")
    engine_cc: Optional[int] = Field(None, description="Engine displacement in cc (ICE only)")
    vin: Optional[str] = Field(None, description="Vehicle Identification Number")
    protocol: ProtocolType = Field(ProtocolType.NONE, description="ECU protocol type")
    powertrain: PowertrainType = Field(
        PowertrainType.ICE,
        description="Powertrain classification (ICE, electric, hybrid)",
    )
    engine_type: EngineType = Field(
        EngineType.FOUR_STROKE,
        description="Engine cycle/configuration (4-stroke, 2-stroke, electric motor, hybrid, desmo)",
    )
    battery_chemistry: Optional[BatteryChemistry] = Field(
        None,
        description="Battery chemistry for electric/hybrid bikes (None for ICE starter batteries)",
    )
    motor_kw: Optional[float] = Field(
        None,
        description="Peak motor power in kW (electric only; ICE bikes use engine_cc)",
    )
    bms_present: bool = Field(
        False,
        description="Whether this vehicle has a Battery Management System (electric/hybrid only)",
    )
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


class RepairPlanStatus(str, Enum):
    """Status of a repair plan."""
    DRAFT = "draft"
    QUOTED = "quoted"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PlanItemType(str, Enum):
    """Type of line item in a repair plan."""
    PREP_LABOR = "prep_labor"       # Access/disassembly time (e.g., remove fairings)
    REPAIR_LABOR = "repair_labor"   # Actual repair wrench time
    PARTS = "parts"                 # Physical parts and materials
    DIAGNOSTIC = "diagnostic"       # Diagnostic time (scanning, testing, inspection)
    MISC = "misc"                   # Miscellaneous charges


class LaborRateType(str, Enum):
    """Type of shop for labor rate context."""
    INDEPENDENT = "independent"
    DEALERSHIP = "dealership"
    MOBILE = "mobile"
