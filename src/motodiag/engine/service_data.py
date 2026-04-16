"""Torque specs + service data reference — quick lookup for common values.

Phase 93: Provides structured service data for common motorcycle maintenance
tasks across all makes. Torque specs, fluid capacities, clearances, and
standard service intervals. These are generic/typical values — always verify
against the model-specific service manual for exact specs.
"""

from typing import Optional
from pydantic import BaseModel, Field


class TorqueSpec(BaseModel):
    """A single torque specification."""
    fastener: str = Field(..., description="What bolt/nut (e.g., 'Oil drain plug')")
    spec_nm: float = Field(..., description="Torque specification in Newton-meters")
    spec_ftlbs: float = Field(default=0.0, description="Torque in foot-pounds (auto-calculated if 0)")
    thread_locker: Optional[str] = Field(None, description="Thread locker required (e.g., 'Loctite 243 blue')")
    notes: Optional[str] = Field(None, description="Additional notes (e.g., 'Replace crush washer')")

    def __init__(self, **data):
        super().__init__(**data)
        if self.spec_ftlbs == 0.0 and self.spec_nm > 0:
            self.spec_ftlbs = round(self.spec_nm * 0.7376, 1)


class FluidCapacity(BaseModel):
    """Fluid capacity specification."""
    fluid_type: str = Field(..., description="What fluid (e.g., 'Engine oil')")
    capacity_ml: float = Field(default=0.0, description="Capacity in milliliters")
    capacity_liters: float = Field(default=0.0, description="Capacity in liters")
    capacity_quarts: float = Field(default=0.0, description="Capacity in US quarts")
    recommended_spec: str = Field(default="", description="Recommended fluid spec (e.g., '10W-40 JASO MA2')")
    notes: Optional[str] = Field(None, description="Additional notes")


class ServiceInterval(BaseModel):
    """Standard service interval."""
    service_item: str = Field(..., description="What service (e.g., 'Oil change')")
    interval_miles: int = Field(default=0, description="Interval in miles")
    interval_km: int = Field(default=0, description="Interval in kilometers")
    interval_months: int = Field(default=0, description="Time-based interval in months")
    notes: Optional[str] = Field(None, description="Additional context")


class Clearance(BaseModel):
    """Valve or other clearance specification."""
    component: str = Field(..., description="What clearance (e.g., 'Intake valve')")
    spec_mm_low: float = Field(..., description="Minimum clearance in mm")
    spec_mm_high: float = Field(..., description="Maximum clearance in mm")
    notes: Optional[str] = Field(None, description="Additional context")


# --- Common torque specifications (typical values across Japanese motorcycles) ---

COMMON_TORQUE_SPECS: list[dict] = [
    {"fastener": "Oil drain plug (M12)", "spec_nm": 20.0, "notes": "Replace aluminum crush washer every change. NEVER over-torque — strips aluminum cases."},
    {"fastener": "Oil drain plug (M14)", "spec_nm": 25.0, "notes": "Replace copper crush washer every change."},
    {"fastener": "Oil filter (cartridge type)", "spec_nm": 18.0, "notes": "Hand-tight + 3/4 turn, or torque with strap wrench."},
    {"fastener": "Spark plug (12mm)", "spec_nm": 13.0, "notes": "Finger-tight + 1/4 turn for new gasket, 1/8 turn for used gasket. Over-torque strips aluminum head threads."},
    {"fastener": "Spark plug (14mm)", "spec_nm": 18.0, "notes": "Finger-tight + 1/2 turn for new gasket. Harley heads use 14mm plugs."},
    {"fastener": "Axle nut — front (typical Japanese)", "spec_nm": 60.0, "notes": "Varies by model. Always torque after fork leg clamp bolts."},
    {"fastener": "Axle nut — rear (typical Japanese)", "spec_nm": 100.0, "notes": "Use new cotter pin. Verify chain alignment after tightening."},
    {"fastener": "Caliper mounting bolt (M8)", "spec_nm": 30.0, "thread_locker": "Loctite 243 blue", "notes": "Critical safety fastener. Loctite mandatory."},
    {"fastener": "Caliper mounting bolt (M10)", "spec_nm": 40.0, "thread_locker": "Loctite 243 blue", "notes": "Critical safety fastener. Inspect at every pad change."},
    {"fastener": "Brake disc bolt (M6 or M8)", "spec_nm": 23.0, "thread_locker": "Loctite 243 blue", "notes": "Cross-pattern tightening. Safety wire on track bikes."},
    {"fastener": "Sprocket nut — rear", "spec_nm": 55.0, "thread_locker": "Loctite 243 blue", "notes": "Tighten in star pattern. Check after first 100 miles."},
    {"fastener": "Engine mount bolt (M10)", "spec_nm": 45.0, "notes": "Tighten with engine warm. Check after vibration-related complaints."},
    {"fastener": "Cam cover bolt (M6)", "spec_nm": 10.0, "notes": "DO NOT over-torque — strips aluminum threads. Criss-cross pattern."},
    {"fastener": "Handlebar clamp bolt", "spec_nm": 23.0, "notes": "Alternate between bolts. Gap should be equal front and back."},
    {"fastener": "Triple clamp pinch bolt", "spec_nm": 20.0, "notes": "Tighten after fork leg is fully seated. Loosen to adjust fork height."},
    {"fastener": "Steering stem nut", "spec_nm": 35.0, "notes": "Preload adjustment — not a fastener torque. Set for zero play, smooth rotation."},
    {"fastener": "Banjo bolt (M10 brake)", "spec_nm": 25.0, "notes": "Use NEW copper crush washers every time. Over-torque = cracked banjo."},
    {"fastener": "Chain adjuster lock nut", "spec_nm": 16.0, "notes": "Tighten AFTER setting chain tension. Recheck axle alignment."},
    {"fastener": "Footpeg mount bolt", "spec_nm": 30.0, "thread_locker": "Loctite 243 blue", "notes": "Vibration-prone fastener. Check monthly."},
    {"fastener": "Exhaust header nut/bolt", "spec_nm": 20.0, "notes": "Tighten COLD. Thermal expansion provides additional clamping force. Apply anti-seize to threads."},
]

# --- Common service intervals ---

COMMON_SERVICE_INTERVALS: list[dict] = [
    {"service_item": "Engine oil change", "interval_miles": 4000, "interval_km": 6000, "interval_months": 12, "notes": "Synthetic: 5000mi/8000km. Always replace filter with oil."},
    {"service_item": "Oil filter replacement", "interval_miles": 4000, "interval_km": 6000, "interval_months": 12, "notes": "Replace every oil change, not every other."},
    {"service_item": "Coolant flush (liquid-cooled)", "interval_miles": 24000, "interval_km": 38000, "interval_months": 24, "notes": "Use motorcycle-specific coolant or 50/50 premixed. Never use automotive 'long life' coolant."},
    {"service_item": "Brake fluid flush", "interval_miles": 0, "interval_km": 0, "interval_months": 24, "notes": "Time-based, not mileage. DOT 4 absorbs water from atmosphere. Flush ALL calipers and master cylinder."},
    {"service_item": "Spark plug replacement", "interval_miles": 12000, "interval_km": 20000, "interval_months": 0, "notes": "Iridium plugs: 24000mi/40000km. Gap to spec before install."},
    {"service_item": "Air filter replacement", "interval_miles": 12000, "interval_km": 20000, "interval_months": 24, "notes": "More frequent in dusty conditions. Paper filters replace, foam filters clean and oil."},
    {"service_item": "Valve clearance check", "interval_miles": 15000, "interval_km": 24000, "interval_months": 0, "notes": "Track bikes: 7500mi/12000km. Shim-under-bucket is the standard on all Japanese bikes."},
    {"service_item": "Chain adjustment and lube", "interval_miles": 500, "interval_km": 800, "interval_months": 0, "notes": "More frequent in rain. Check tension + lube every 300-500 miles."},
    {"service_item": "Chain and sprocket replacement", "interval_miles": 20000, "interval_km": 32000, "interval_months": 0, "notes": "O-ring/X-ring: 25000+mi. Replace chain AND both sprockets together."},
    {"service_item": "Fork oil change", "interval_miles": 15000, "interval_km": 24000, "interval_months": 12, "notes": "More frequent on track bikes. Weight affects damping: 10W (stock), 15W (firmer)."},
    {"service_item": "Tire replacement", "interval_miles": 8000, "interval_km": 13000, "interval_months": 60, "notes": "Varies dramatically by tire compound and riding style. Sport tires: 5000-8000mi. Touring: 10000-15000mi."},
    {"service_item": "Battery check/replacement", "interval_miles": 0, "interval_km": 0, "interval_months": 36, "notes": "AGM: 3-5 years. Lithium: 5-7 years. Check voltage monthly. Battery Tender for storage."},
    {"service_item": "Final drive oil (shaft drive)", "interval_miles": 10000, "interval_km": 16000, "interval_months": 24, "notes": "80W-90 hypoid gear oil. Check for metal particles on drain plug."},
    {"service_item": "Steering head bearing check", "interval_miles": 12000, "interval_km": 20000, "interval_months": 0, "notes": "Check at every tire change. Adjust preload if play detected. Replace if notchy."},
]

# --- Common valve clearances (typical ranges by engine type) ---

COMMON_VALVE_CLEARANCES: list[dict] = [
    {"component": "Inline-4 intake valve (typical)", "spec_mm_low": 0.10, "spec_mm_high": 0.20, "notes": "Check cold. Shim-under-bucket standard on all Japanese inline-4."},
    {"component": "Inline-4 exhaust valve (typical)", "spec_mm_low": 0.20, "spec_mm_high": 0.30, "notes": "Exhaust valves tighten first. Hard cold start = check exhaust clearance."},
    {"component": "V-twin intake valve (typical)", "spec_mm_low": 0.10, "spec_mm_high": 0.20, "notes": "Front cylinder harder to access. Remove radiator for access on many models."},
    {"component": "V-twin exhaust valve (typical)", "spec_mm_low": 0.20, "spec_mm_high": 0.30, "notes": "Tightens faster on rear cylinder (less airflow cooling)."},
    {"component": "Single-cylinder intake (DR-Z/KLX/CRF)", "spec_mm_low": 0.10, "spec_mm_high": 0.15, "notes": "Easiest valve check — only 4 valves. Off-road use shortens interval."},
    {"component": "Single-cylinder exhaust (DR-Z/KLX/CRF)", "spec_mm_low": 0.20, "spec_mm_high": 0.25, "notes": "Kick start getting harder = tight exhaust valves."},
    {"component": "Harley Twin Cam intake", "spec_mm_low": 0.05, "spec_mm_high": 0.10, "notes": "Hydraulic lifters on some models — no adjustment needed. Solid lifters: check at 15000mi."},
    {"component": "Harley Twin Cam exhaust", "spec_mm_low": 0.10, "spec_mm_high": 0.15, "notes": "Solid lifter models only. Milwaukee-Eight uses hydraulic lifters — self-adjusting."},
]


def get_torque_spec(fastener_name: str) -> Optional[TorqueSpec]:
    """Look up a torque spec by fastener name (partial match)."""
    name_lower = fastener_name.lower()
    for spec_dict in COMMON_TORQUE_SPECS:
        if name_lower in spec_dict["fastener"].lower():
            return TorqueSpec(**spec_dict)
    return None


def get_service_interval(service_item: str) -> Optional[ServiceInterval]:
    """Look up a service interval by item name (partial match)."""
    name_lower = service_item.lower()
    for interval_dict in COMMON_SERVICE_INTERVALS:
        if name_lower in interval_dict["service_item"].lower():
            return ServiceInterval(**interval_dict)
    return None


def get_valve_clearance(component: str) -> Optional[Clearance]:
    """Look up valve clearance by component description (partial match)."""
    name_lower = component.lower()
    for clearance_dict in COMMON_VALVE_CLEARANCES:
        if name_lower in clearance_dict["component"].lower():
            return Clearance(**clearance_dict)
    return None


def list_all_torque_specs() -> list[str]:
    """Return all fastener names with torque specs available."""
    return [spec["fastener"] for spec in COMMON_TORQUE_SPECS]


def list_all_service_intervals() -> list[str]:
    """Return all service items with intervals available."""
    return [interval["service_item"] for interval in COMMON_SERVICE_INTERVALS]


def build_service_data_context(
    torque_specs: Optional[list[TorqueSpec]] = None,
    intervals: Optional[list[ServiceInterval]] = None,
    clearances: Optional[list[Clearance]] = None,
) -> str:
    """Format service data into context for AI prompt injection."""
    lines = []

    if torque_specs:
        lines.append("\n--- Torque Specifications ---")
        for spec in torque_specs:
            line = f"  {spec.fastener}: {spec.spec_nm} Nm ({spec.spec_ftlbs} ft-lbs)"
            if spec.thread_locker:
                line += f" [Thread locker: {spec.thread_locker}]"
            if spec.notes:
                line += f" — {spec.notes}"
            lines.append(line)

    if intervals:
        lines.append("\n--- Service Intervals ---")
        for interval in intervals:
            parts = [f"  {interval.service_item}:"]
            if interval.interval_miles:
                parts.append(f"every {interval.interval_miles:,} miles")
            if interval.interval_months:
                parts.append(f"or {interval.interval_months} months")
            if interval.notes:
                parts.append(f"— {interval.notes}")
            lines.append(" ".join(parts))

    if clearances:
        lines.append("\n--- Valve Clearances ---")
        for cl in clearances:
            line = f"  {cl.component}: {cl.spec_mm_low}-{cl.spec_mm_high} mm"
            if cl.notes:
                line += f" — {cl.notes}"
            lines.append(line)

    return "\n".join(lines)
