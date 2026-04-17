"""Fault code interpretation subsystem — DTC analysis with make-specific handling.

Takes a DTC code + vehicle context, classifies the code format, correlates with
the DTC database and knowledge base, and produces a root cause analysis with
repair recommendations via Claude AI.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field

from motodiag.engine.client import DiagnosticClient
from motodiag.engine.models import TokenUsage


# --- DTC code classification ---

class CodeFormat:
    """DTC code format identifiers.

    Phase 111 (Retrofit): added European OEM-specific formats + electric bike
    format for expansion Track K and Track L.
    """
    OBD2_GENERIC = "obd2_generic"       # P0xxx, P2xxx — standard OBD-II
    OBD2_MANUFACTURER = "obd2_mfr"      # P1xxx — manufacturer-specific OBD-II
    KAWASAKI_DEALER = "kawasaki_dealer"  # 2-digit: 11, 12, 13... (FI dealer mode)
    SUZUKI_CMODE = "suzuki_cmode"       # C00, C12, C13, C28... (C-mode diagnostic)
    HONDA_BLINK = "honda_blink"         # Blink count patterns: 1, 2, 7, etc.
    HARLEY_DTC = "harley_dtc"           # Harley-specific: B-codes, U-codes, P-codes
    YAMAHA_DIAG = "yamaha_diag"         # Yamaha self-diagnostic: 12, 14, 19...
    # European OEM-specific formats (Phase 111 additions)
    BMW_ISTA = "bmw_ista"               # BMW ISTA format (5-digit hex + namespace)
    DUCATI_DDS = "ducati_dds"           # Ducati DDS diagnostic system (DTC-P, DTC-A prefixes)
    KTM_KDS = "ktm_kds"                 # KTM dealer system (P/C prefixes, KTM-specific)
    TRIUMPH_TUNEECU = "triumph_tuneecu"  # Triumph TuneECU blink/hex codes
    APRILIA_DIAG = "aprilia_diag"       # Aprilia diagnostic (Marelli-based, DTC-xxxx format)
    # Electric bike format (Phase 111 addition)
    ELECTRIC_HV = "electric_hv"         # Zero/LiveWire/Energica HV battery/motor DTCs (HV_, MC_, BMS_ prefixes)
    UNKNOWN = "unknown"


# OBD-II P-code system mapping (first digit after P0/P1)
OBD2_SYSTEM_MAP = {
    "1": "fuel_and_air_metering",
    "2": "fuel_and_air_metering_injector",
    "3": "ignition_misfire",
    "4": "auxiliary_emissions",
    "5": "vehicle_speed_idle",
    "6": "computer_output",
    "7": "transmission",
}

# Kawasaki dealer mode code descriptions
KAWASAKI_CODE_MAP = {
    "11": "ECU fault",
    "12": "ISC (Idle Speed Control) valve",
    "13": "TPS (Throttle Position Sensor)",
    "14": "IAP (Intake Air Pressure) sensor",
    "15": "ECT (Engine Coolant Temperature) sensor",
    "16": "Intake air temperature sensor",
    "21": "Front O2 sensor",
    "22": "Rear O2 sensor",
    "23": "IAP vacuum hose",
    "24": "Vehicle speed sensor",
    "25": "Gear position sensor",
    "31": "Shift sensor (quickshifter)",
    "32": "Bank angle sensor",
    "33": "Battery voltage",
    "41": "FI relay",
    "42": "Fuel pump",
    "43": "SET valve (exhaust)",
    "44": "PAIR solenoid",
    "51": "KTRC/TC system",
    "52": "KIBS/ABS system",
    "53": "IMU sensor",
    "54": "Cruise control",
    "61": "KIPASS antenna",
    "62": "KIPASS key registration",
}

# Suzuki C-mode code descriptions
SUZUKI_CODE_MAP = {
    "C00": "No fault stored",
    "C12": "TPS (Throttle Position Sensor)",
    "C13": "IAP (Intake Air Pressure) sensor",
    "C14": "ECT (Engine Coolant Temperature) sensor",
    "C15": "Intake air temperature sensor",
    "C21": "MAP sensor high",
    "C22": "MAP sensor low",
    "C23": "TIP (Throttle Intake Pressure) sensor",
    "C24": "Vehicle speed sensor",
    "C25": "Atmospheric pressure sensor",
    "C28": "Fuel pump / FI relay",
    "C29": "STPS (Secondary Throttle Position Sensor)",
    "C31": "Gear position / shift sensor",
    "C32": "Exhaust control valve position",
    "C33": "Camshaft position sensor",
    "C41": "SET (exhaust) valve actuator",
    "C42": "SET valve position",
    "C44": "STPS actuator",
    "C46": "Front wheel speed sensor",
    "C49": "Rear wheel speed sensor",
}


def classify_code(code: str, make: Optional[str] = None) -> tuple[str, str]:
    """Classify a DTC code into its format type and system.

    Args:
        code: The DTC code string (e.g., "P0301", "C28", "12").
        make: Optional vehicle make to help with ambiguous codes.

    Returns:
        Tuple of (code_format, system_or_description).
    """
    code = code.strip().upper()

    # OBD-II P-codes: P0xxx (generic) or P1xxx (manufacturer)
    if re.match(r'^P[0-9]{4}$', code):
        if code[1] == '0' or code[1] == '2':
            system = OBD2_SYSTEM_MAP.get(code[2], "unknown_system")
            return CodeFormat.OBD2_GENERIC, system
        elif code[1] == '1':
            return CodeFormat.OBD2_MANUFACTURER, "manufacturer_specific"
        return CodeFormat.OBD2_GENERIC, "unknown_system"

    # OBD-II B-codes (body), C-codes (chassis), U-codes (communication)
    if re.match(r'^[BCU][0-9]{4}$', code):
        if code[0] == 'B':
            return CodeFormat.HARLEY_DTC, "body_electrical"
        elif code[0] == 'C':
            return CodeFormat.HARLEY_DTC, "chassis"
        elif code[0] == 'U':
            return CodeFormat.HARLEY_DTC, "communication_network"

    # Suzuki C-mode codes: C00, C12, C13, C28, etc.
    if re.match(r'^C[0-9]{2}$', code):
        desc = SUZUKI_CODE_MAP.get(code, "unknown Suzuki C-mode code")
        return CodeFormat.SUZUKI_CMODE, desc

    # Kawasaki / Yamaha 2-digit dealer mode codes: 11, 12, 13...
    if re.match(r'^[0-9]{2}$', code):
        if make and make.lower() == "yamaha":
            return CodeFormat.YAMAHA_DIAG, f"Yamaha diagnostic code {code}"
        # Default to Kawasaki for 2-digit codes
        desc = KAWASAKI_CODE_MAP.get(code, f"Kawasaki dealer mode code {code}")
        return CodeFormat.KAWASAKI_DEALER, desc

    # Honda blink codes: single digit 1-9
    if re.match(r'^[1-9]$', code):
        return CodeFormat.HONDA_BLINK, f"Honda blink code {code}"

    # --- European OEM formats (Phase 111) ---

    # BMW ISTA: 5-digit hex codes like A2B4C (namespace + 4 hex)
    # Example: "A0B12" — BMW body domain fault
    if re.match(r'^[0-9A-F]{5}$', code) and make and make.lower() == "bmw":
        return CodeFormat.BMW_ISTA, f"BMW ISTA code {code}"

    # Aprilia: DTC-xxxx with 4-digit numeric codes (Marelli). Checked before Ducati
    # because Aprilia's DTC- prefix uses numeric digits, while Ducati uses letter+digits.
    if make and make.lower() == "aprilia" and re.match(r'^DTC-?[0-9]{4}$', code):
        return CodeFormat.APRILIA_DIAG, f"Aprilia diagnostic code {code}"

    # Ducati DDS: DTC-P0xxx or DTC-A0xxx (Powertrain / Auxiliary namespaces)
    # Requires explicit letter prefix after DTC- to distinguish from Aprilia's numeric format.
    if re.match(r'^DTC-[PA][0-9]{4}$', code):
        namespace = code.split("-")[1][0]
        desc = "powertrain" if namespace == "P" else "auxiliary"
        return CodeFormat.DUCATI_DDS, f"Ducati DDS {desc}"

    # KTM KDS: KP-xxxx or KC-xxxx (Powertrain / Chassis)
    if re.match(r'^K[PC]-[0-9]{4}$', code):
        namespace = "powertrain" if code[1] == "P" else "chassis"
        return CodeFormat.KTM_KDS, f"KTM KDS {namespace}"

    # Triumph TuneECU: T-xxx (3-digit hex after T-)
    if re.match(r'^T-[0-9A-F]{3}$', code) or (make and make.lower() == "triumph" and re.match(r'^[0-9A-F]{3}$', code)):
        return CodeFormat.TRIUMPH_TUNEECU, f"Triumph TuneECU code {code}"

    # --- Electric bike formats (Phase 111) ---

    # Electric HV namespaces: HV_, MC_, BMS_, INV_, CHG_ prefixes
    # Used by Zero, LiveWire, Energica for HV battery / motor controller / inverter faults
    if re.match(r'^(HV|MC|BMS|INV|CHG|REG)_[0-9A-Z]{2,5}$', code):
        prefix = code.split("_")[0]
        subsystem = {
            "HV": "high-voltage system",
            "MC": "motor controller",
            "BMS": "battery management system",
            "INV": "inverter",
            "CHG": "charging system",
            "REG": "regenerative braking",
        }.get(prefix, "electric powertrain")
        return CodeFormat.ELECTRIC_HV, f"Electric {subsystem} fault"

    return CodeFormat.UNKNOWN, "unrecognized code format"


# --- Fault code result model ---

class FaultCodeResult(BaseModel):
    """Structured result from fault code interpretation."""
    code: str = Field(..., description="The DTC code as reported")
    code_format: str = Field(..., description="Classified format (obd2_generic, kawasaki_dealer, etc.)")
    description: str = Field(default="", description="Human-readable code description")
    system: str = Field(default="", description="Affected system (fuel, ignition, electrical, etc.)")
    possible_causes: list[str] = Field(default_factory=list, description="Ranked possible root causes")
    tests_to_confirm: list[str] = Field(default_factory=list, description="Diagnostic tests to perform before replacing parts")
    related_symptoms: list[str] = Field(default_factory=list, description="Symptoms that should be present if this code is accurate")
    repair_steps: list[str] = Field(default_factory=list, description="Repair procedure once root cause is confirmed")
    estimated_hours: Optional[float] = Field(None, description="Estimated labor hours for repair")
    estimated_cost: Optional[str] = Field(None, description="Estimated total cost range")
    safety_critical: bool = Field(default=False, description="Whether this code indicates a safety issue")
    notes: Optional[str] = Field(None, description="Additional context or caveats")


# --- DTC interpretation prompt ---

DTC_INTERPRETATION_PROMPT = """You are interpreting a motorcycle Diagnostic Trouble Code (DTC). Follow this structured approach:

STEP 1 — CODE IDENTIFICATION
Identify the code format (OBD-II generic, manufacturer-specific, make dealer mode, etc.) and the system it relates to. State the standard definition of this code.

STEP 2 — ROOT CAUSE ANALYSIS
The DTC is a SYMPTOM, not the diagnosis. List the possible root causes ranked by probability for this specific vehicle. Consider:
- The sensor/actuator the code references (most common: wiring fault, connector corrosion, component failure)
- Make/model-specific known failure patterns
- Environmental factors (age, mileage, riding conditions)

STEP 3 — DIAGNOSTIC TESTS
For each possible cause, provide a specific "check before replacing" test:
- Resistance tests with expected values
- Voltage tests with expected ranges
- Visual inspections (connector condition, wiring routing, component condition)
- Live data checks (if available via dealer tool)

STEP 4 — RELATED SYMPTOMS
What symptoms should the mechanic observe if this code is accurately reflecting a real fault (vs. intermittent/false trigger)? If the code doesn't match the reported symptoms, flag this discrepancy.

STEP 5 — REPAIR RECOMMENDATION
Once the root cause is confirmed via testing, provide:
- Step-by-step repair procedure
- Parts needed with approximate costs
- Labor time estimate
- Whether clearing the code requires a special procedure (dealer tool, battery disconnect, drive cycle)

IMPORTANT: A DTC alone is NEVER sufficient for parts replacement. Always recommend testing first.

Respond as structured JSON with these fields: possible_causes, tests_to_confirm, related_symptoms, repair_steps, estimated_hours, estimated_cost, safety_critical, notes."""


class FaultCodeInterpreter:
    """Interprets motorcycle DTCs with make-specific handling and AI analysis.

    Two-pass approach:
    1. Classify the code format and look up in local DTC database
    2. Send code + vehicle context + DB results to Claude for root cause analysis
    """

    def __init__(self, client: DiagnosticClient):
        self.client = client

    def interpret(
        self,
        code: str,
        make: str,
        model_name: str,
        year: int,
        symptoms: Optional[list[str]] = None,
        mileage: Optional[int] = None,
        known_issues: Optional[list[dict]] = None,
        ai_model: Optional[str] = None,
    ) -> tuple[FaultCodeResult, TokenUsage]:
        """Interpret a DTC code with vehicle context and AI analysis.

        Args:
            code: The DTC code string.
            make: Vehicle manufacturer.
            model_name: Vehicle model.
            year: Model year.
            symptoms: Optional reported symptoms (for correlation).
            mileage: Optional current mileage.
            known_issues: Optional relevant known issues from KB.
            ai_model: Optional model override.

        Returns:
            Tuple of (FaultCodeResult, TokenUsage).
        """
        from motodiag.engine.prompts import (
            build_vehicle_context,
            build_knowledge_context,
        )

        # Step 1: Classify the code
        code_format, system_desc = classify_code(code, make)

        # Step 2: Build context
        vehicle_ctx = build_vehicle_context(make=make, model=model_name, year=year, mileage=mileage)
        knowledge_ctx = build_knowledge_context(known_issues or [])

        prompt_parts = [
            vehicle_ctx,
            "",
            f"DTC Code: {code}",
            f"Code Format: {code_format}",
            f"System/Description: {system_desc}",
        ]

        if symptoms:
            prompt_parts.append(f"\nReported symptoms: {', '.join(symptoms)}")

        if knowledge_ctx:
            prompt_parts.append(knowledge_ctx)

        prompt_parts.append(
            "\nPlease interpret this fault code following the structured approach "
            "in the system prompt. Respond as structured JSON."
        )

        prompt = "\n".join(prompt_parts)

        # Step 3: Call Claude
        response_text, usage = self.client.ask(
            prompt=prompt,
            system=DTC_INTERPRETATION_PROMPT,
            model=ai_model,
        )

        # Step 4: Parse response into FaultCodeResult
        result = self._parse_result(response_text, code, code_format, system_desc)

        return result, usage

    def _parse_result(
        self,
        response_text: str,
        code: str,
        code_format: str,
        system_desc: str,
    ) -> FaultCodeResult:
        """Parse AI response into a FaultCodeResult."""
        import json

        try:
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)
            return FaultCodeResult(
                code=code,
                code_format=code_format,
                description=system_desc,
                system=data.get("system", system_desc),
                possible_causes=data.get("possible_causes", []),
                tests_to_confirm=data.get("tests_to_confirm", []),
                related_symptoms=data.get("related_symptoms", []),
                repair_steps=data.get("repair_steps", []),
                estimated_hours=data.get("estimated_hours"),
                estimated_cost=data.get("estimated_cost"),
                safety_critical=data.get("safety_critical", False),
                notes=data.get("notes"),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return FaultCodeResult(
                code=code,
                code_format=code_format,
                description=system_desc,
                possible_causes=[response_text[:500]],
                notes="AI response could not be parsed as structured JSON — raw text in possible_causes.",
            )

    def quick_lookup(self, code: str, make: Optional[str] = None) -> dict:
        """Fast local lookup without AI — returns code format and description only.

        Useful for displaying code info without waiting for AI analysis.
        """
        code_format, description = classify_code(code, make)
        return {
            "code": code,
            "code_format": code_format,
            "description": description,
            "requires_ai": code_format != CodeFormat.UNKNOWN,
        }
