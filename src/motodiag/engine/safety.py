"""Safety warnings and critical alerts — rule-based hazard detection for diagnoses.

Scans diagnosis text, symptom lists, and repair procedures against predefined
safety rules to flag dangerous conditions: brake failure, fuel leaks, fire risk,
electrical shorts, and other hazards that could cause injury or property damage.

Pure logic — no API calls required.
"""

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Alert level enum
# ---------------------------------------------------------------------------

class AlertLevel(str, Enum):
    """Severity of a safety alert, ordered from most to least critical."""
    CRITICAL = "critical"   # Immediate danger — do NOT ride/start
    WARNING = "warning"     # Serious risk — stop riding, shut down
    CAUTION = "caution"     # Elevated risk — address before next ride
    INFO = "info"           # Awareness — schedule service soon


# Ordering for sorting (lower index = higher priority)
_ALERT_ORDER = {
    AlertLevel.CRITICAL: 0,
    AlertLevel.WARNING: 1,
    AlertLevel.CAUTION: 2,
    AlertLevel.INFO: 3,
}


# ---------------------------------------------------------------------------
# Safety alert model
# ---------------------------------------------------------------------------

class SafetyAlert(BaseModel):
    """A single safety alert triggered by a rule match."""
    level: AlertLevel = Field(..., description="Severity level of this alert")
    title: str = Field(..., description="Short alert title")
    message: str = Field(..., description="Detailed explanation of the hazard")
    affected_system: str = Field(..., description="Vehicle system involved (brakes, fuel, electrical, etc.)")
    immediate_action: str = Field(..., description="What to do right now")
    do_not: Optional[str] = Field(None, description="What NOT to do — critical safety warning")


# ---------------------------------------------------------------------------
# Safety rules — keyword patterns mapped to alerts
# ---------------------------------------------------------------------------

SAFETY_RULES: list[dict] = [
    # --- CRITICAL ---
    {
        "patterns": [r"brake.*(fail|leak|loss|no pressure|spongy feel|complete loss)"],
        "level": AlertLevel.CRITICAL,
        "title": "Brake system failure",
        "message": "Brake failure detected. Loss of braking ability is immediately life-threatening.",
        "affected_system": "brakes",
        "immediate_action": "Do NOT ride. Inspect brake system immediately.",
        "do_not": "Do NOT ride the motorcycle under any circumstances until brakes are verified functional.",
    },
    {
        "patterns": [r"fuel.*(leak|spill|pooling|drip)", r"gas(oline)?.*(leak|spill|pooling|drip)"],
        "level": AlertLevel.CRITICAL,
        "title": "Fuel leak detected",
        "message": "Fuel leak creates fire and explosion risk, especially near hot engine surfaces.",
        "affected_system": "fuel",
        "immediate_action": "Do NOT start engine. Check for fuel pooling near hot surfaces.",
        "do_not": "Do NOT start the engine or create any ignition source near the motorcycle.",
    },
    {
        "patterns": [r"stator.*(connector|plug).*(melt|burn|char|scorch|fire)"],
        "level": AlertLevel.CRITICAL,
        "title": "Stator connector melting — fire risk",
        "message": "Melting stator connector indicates high-resistance connection that can cause electrical fire.",
        "affected_system": "electrical",
        "immediate_action": "Disconnect battery immediately. Solder the connector — do NOT use a replacement plug.",
        "do_not": "Do NOT reconnect the stock plug connector. It WILL melt again. Solder direct.",
    },
    {
        "patterns": [r"throttle.*(stuck|jam|wide open|won'?t close|hang)", r"stuck.*(throttle|open)"],
        "level": AlertLevel.CRITICAL,
        "title": "Stuck throttle — loss of control",
        "message": "A throttle that does not close on its own is an immediate crash risk.",
        "affected_system": "controls",
        "immediate_action": "Kill engine immediately. Inspect throttle cables and return spring.",
        "do_not": "Do NOT ride until throttle snaps closed on its own when released.",
    },
    {
        "patterns": [r"(fuel|gas).*(smell|odor|fumes).*(strong|heavy|inside|cockpit)"],
        "level": AlertLevel.CRITICAL,
        "title": "Strong fuel odor — leak likely",
        "message": "Strong fuel smell indicates a leak or vapor escape. Fire risk near hot engine or exhaust.",
        "affected_system": "fuel",
        "immediate_action": "Shut off engine. Inspect fuel lines, tank, petcock, and injector seals.",
        "do_not": "Do NOT start the engine until the fuel smell source is identified and fixed.",
    },

    # --- WARNING ---
    {
        "patterns": [r"head gasket.*(blow|fail|leak|crack)"],
        "level": AlertLevel.WARNING,
        "title": "Head gasket failure",
        "message": "Blown head gasket can cause rapid overheating and engine seizure.",
        "affected_system": "engine",
        "immediate_action": "Do not continue riding. Risk of engine seizure.",
        "do_not": "Do NOT keep riding — coolant loss leads to seizure within minutes.",
    },
    {
        "patterns": [r"overheat.*(steam|boil|blow)", r"steam.*(radiator|coolant|overflow)",
                     r"(coolant|radiator).*(steam|boil)"],
        "level": AlertLevel.WARNING,
        "title": "Engine overheating with steam",
        "message": "Steam from the cooling system indicates boiling coolant — engine damage imminent.",
        "affected_system": "cooling",
        "immediate_action": "Shut off engine. Allow to cool before opening radiator cap.",
        "do_not": "Do NOT open the radiator cap while hot — pressurized coolant causes severe burns.",
    },
    {
        "patterns": [r"electrical.*(short|fire|smoke|arc|spark)", r"wir(e|ing).*(short|smoke|melt|burn)"],
        "level": AlertLevel.WARNING,
        "title": "Electrical short detected",
        "message": "Electrical short can cause wiring fire. Smoke or melting insulation is an emergency.",
        "affected_system": "electrical",
        "immediate_action": "Disconnect battery. Inspect wiring before reconnecting.",
        "do_not": "Do NOT reconnect battery until the short is found and repaired.",
    },
    {
        "patterns": [r"steering.*(lock|seize|bind|wobble.*death)", r"headstock.*(loose|play|worn)"],
        "level": AlertLevel.WARNING,
        "title": "Steering system compromise",
        "message": "Steering problems cause loss of control at speed — death wobble or locked steering is immediately dangerous.",
        "affected_system": "chassis",
        "immediate_action": "Stop riding immediately. Inspect steering head bearings and front end.",
        "do_not": "Do NOT ride at highway speed with known steering issues.",
    },
    {
        "patterns": [r"wheel.*(bearing|hub).*(seiz|lock|fail|grind|collapse)"],
        "level": AlertLevel.WARNING,
        "title": "Wheel bearing failure",
        "message": "Failed wheel bearings can cause wheel lockup or separation — catastrophic at any speed.",
        "affected_system": "chassis",
        "immediate_action": "Stop riding. Check for wheel play by grabbing top and bottom of tire and rocking.",
        "do_not": "Do NOT ride with a grinding or clicking wheel bearing.",
    },

    # --- CAUTION ---
    {
        "patterns": [r"chain.*(worn|stretch|tight|loose|skip|break|kink)",
                     r"(drive|final).*(chain).*(worn|stretch)"],
        "level": AlertLevel.CAUTION,
        "title": "Drive chain condition — wear detected",
        "message": "A worn or improperly adjusted chain can break, locking the rear wheel or causing loss of drive.",
        "affected_system": "drivetrain",
        "immediate_action": "Replace before next ride. Broken chain can lock rear wheel.",
        "do_not": "Do NOT ride with a kinked or severely stretched chain.",
    },
    {
        "patterns": [r"tire.*(worn|bald|flat|crack|tread|plug)", r"(front|rear).*(tire|tyre).*(low|flat)"],
        "level": AlertLevel.CAUTION,
        "title": "Tire condition — replacement needed",
        "message": "Worn tires provide reduced traction, especially in wet conditions.",
        "affected_system": "tires",
        "immediate_action": "Replace immediately. Worn tires = reduced traction.",
        "do_not": "Do NOT ride in rain on bald or cracked tires.",
    },
    {
        "patterns": [r"oil.*(leak|drip|seep|pool|puddle)", r"(engine|primary|transmission).*(leak|seep)"],
        "level": AlertLevel.CAUTION,
        "title": "Oil leak detected",
        "message": "Oil on tires or brakes creates a crash hazard. Monitor oil level closely.",
        "affected_system": "engine",
        "immediate_action": "Monitor level closely. Oil on tires or brakes = crash risk.",
        "do_not": "Do NOT ignore oil dripping onto the rear tire or brake rotor.",
    },
    {
        "patterns": [r"coolant.*(leak|drip|low|loss)", r"(radiator|hose).*(leak|crack|split)"],
        "level": AlertLevel.CAUTION,
        "title": "Coolant leak — overheating risk",
        "message": "Coolant loss leads to overheating. Coolant on tires is extremely slippery.",
        "affected_system": "cooling",
        "immediate_action": "Top off coolant. Find and fix the leak source before extended riding.",
        "do_not": "Do NOT ride long distances with a known coolant leak.",
    },
    {
        "patterns": [r"exhaust.*(leak|crack|hole|blow|gasket)"],
        "level": AlertLevel.CAUTION,
        "title": "Exhaust leak — fumes and burn risk",
        "message": "Exhaust leak can expose rider to CO fumes and cause burns from hot gases.",
        "affected_system": "exhaust",
        "immediate_action": "Inspect header gaskets and pipe joints. Repair before riding in traffic.",
        "do_not": None,
    },

    # --- INFO ---
    {
        "patterns": [r"valve.*(clearance|adjust|tight|loose|shim|lash)"],
        "level": AlertLevel.INFO,
        "title": "Valve clearance service needed",
        "message": "Out-of-spec valve clearance accelerates valve and seat wear. Tight valves are worse than loose.",
        "affected_system": "engine",
        "immediate_action": "Schedule service. Continued riding accelerates valve damage.",
        "do_not": None,
    },
    {
        "patterns": [r"air.*(filter|cleaner).*(dirty|clogged|restrict|neglect)"],
        "level": AlertLevel.INFO,
        "title": "Air filter maintenance needed",
        "message": "Restricted airflow causes rich running, reduced power, and increased fuel consumption.",
        "affected_system": "intake",
        "immediate_action": "Replace or clean air filter at next service.",
        "do_not": None,
    },
    {
        "patterns": [r"spark.*(plug|plugs).*(foul|worn|gap|replace|old)"],
        "level": AlertLevel.INFO,
        "title": "Spark plug service needed",
        "message": "Worn or fouled plugs cause misfires, hard starting, and reduced fuel economy.",
        "affected_system": "ignition",
        "immediate_action": "Replace spark plugs at next service. Check gap to spec.",
        "do_not": None,
    },
    {
        "patterns": [r"brake.*(fluid|dot).*(old|dark|contaminated|moisture|water|flush)"],
        "level": AlertLevel.INFO,
        "title": "Brake fluid service needed",
        "message": "Contaminated brake fluid absorbs moisture, lowering boiling point and reducing brake performance.",
        "affected_system": "brakes",
        "immediate_action": "Schedule brake fluid flush. Use DOT 4 unless manual specifies DOT 5.",
        "do_not": None,
    },
]


# ---------------------------------------------------------------------------
# Repair procedure safety keywords
# ---------------------------------------------------------------------------

REPAIR_SAFETY_KEYWORDS: dict[str, dict] = {
    "drain fuel": {
        "level": AlertLevel.CAUTION,
        "title": "Fire hazard — fuel handling",
        "message": "Draining fuel creates fire and vapor explosion risk.",
        "affected_system": "fuel",
        "immediate_action": "Work in ventilated area away from ignition sources. Have fire extinguisher ready.",
        "do_not": "Do NOT smoke or use open flames near fuel. Do NOT drain into unapproved containers.",
    },
    "remove fuel tank": {
        "level": AlertLevel.CAUTION,
        "title": "Fire hazard — fuel tank removal",
        "message": "Fuel tank removal involves disconnecting fuel lines. Spillage likely.",
        "affected_system": "fuel",
        "immediate_action": "Disconnect battery first. Have rags ready for fuel drips. Work in ventilated area.",
        "do_not": "Do NOT leave fuel lines uncapped. Do NOT work near ignition sources.",
    },
    "brake fluid": {
        "level": AlertLevel.CAUTION,
        "title": "Brake fluid damages paint",
        "message": "DOT 3/4 brake fluid destroys paint and plastic finishes on contact.",
        "affected_system": "brakes",
        "immediate_action": "Cover painted surfaces before opening brake fluid reservoir. Clean spills instantly with water.",
        "do_not": "Do NOT let brake fluid contact painted surfaces, plastic, or rubber seals.",
    },
    "brake caliper": {
        "level": AlertLevel.CAUTION,
        "title": "Brake service — proper torque required",
        "message": "Improperly torqued brake components can fail under braking load.",
        "affected_system": "brakes",
        "immediate_action": "Use torque wrench on all brake fasteners. Verify caliper slides freely after install.",
        "do_not": "Do NOT use impact tools on brake caliper bolts. Always torque to spec.",
    },
    "jack": {
        "level": AlertLevel.WARNING,
        "title": "Crush hazard — motorcycle support",
        "message": "A motorcycle falling from a jack or lift can cause serious injury.",
        "affected_system": "safety",
        "immediate_action": "Use proper motorcycle jack with straps. Ensure stable footing on level surface.",
        "do_not": "Do NOT work under a motorcycle supported only by a jack without additional stabilization.",
    },
    "lift": {
        "level": AlertLevel.WARNING,
        "title": "Crush hazard — motorcycle on lift",
        "message": "An unsecured motorcycle on a lift can fall and cause serious injury.",
        "affected_system": "safety",
        "immediate_action": "Strap motorcycle to lift at multiple points. Lock lift in position.",
        "do_not": "Do NOT rely on the bike's weight alone to keep it stable on a lift.",
    },
    "battery": {
        "level": AlertLevel.CAUTION,
        "title": "Electrical shock and acid hazard",
        "message": "Motorcycle batteries contain sulfuric acid and can produce explosive hydrogen gas.",
        "affected_system": "electrical",
        "immediate_action": "Disconnect negative terminal first. Wear eye protection.",
        "do_not": "Do NOT create sparks near the battery. Do NOT tip a flooded battery.",
    },
    "coolant drain": {
        "level": AlertLevel.CAUTION,
        "title": "Hot coolant — burn risk",
        "message": "Coolant can be scalding hot if engine was recently running. Ethylene glycol is toxic to animals.",
        "affected_system": "cooling",
        "immediate_action": "Let engine cool completely before draining. Dispose of coolant properly.",
        "do_not": "Do NOT open drain while engine is hot. Do NOT leave coolant accessible to pets.",
    },
    "exhaust": {
        "level": AlertLevel.CAUTION,
        "title": "Burn hazard — exhaust components",
        "message": "Exhaust headers and pipes reach 500-1200F during operation.",
        "affected_system": "exhaust",
        "immediate_action": "Allow exhaust to cool completely before touching. Use heat-resistant gloves.",
        "do_not": "Do NOT touch exhaust components after the engine has been running.",
    },
    "chain adjust": {
        "level": AlertLevel.CAUTION,
        "title": "Pinch hazard — chain and sprocket",
        "message": "Fingers caught between chain and sprocket cause severe injury.",
        "affected_system": "drivetrain",
        "immediate_action": "Engine OFF, transmission in neutral. Never rotate wheel by hand near chain with engine running.",
        "do_not": "Do NOT put fingers between chain and sprocket. Do NOT spin wheel with engine running.",
    },
    "spring compress": {
        "level": AlertLevel.WARNING,
        "title": "Stored energy — compressed spring",
        "message": "Compressed suspension springs store lethal energy. Improper release can cause serious injury.",
        "affected_system": "suspension",
        "immediate_action": "Use proper spring compressor tool. Keep face and body clear of spring path.",
        "do_not": "Do NOT use makeshift spring compressors. Do NOT remove retainer without proper tool.",
    },
    "electrical wiring": {
        "level": AlertLevel.CAUTION,
        "title": "Short circuit risk — wiring work",
        "message": "Incorrect wiring can cause shorts, blown fuses, or electrical fire.",
        "affected_system": "electrical",
        "immediate_action": "Disconnect battery before any wiring work. Use proper connectors and heat shrink.",
        "do_not": "Do NOT splice wires with electrical tape alone. Do NOT work on wiring with battery connected.",
    },
}


# ---------------------------------------------------------------------------
# SafetyChecker class
# ---------------------------------------------------------------------------

class SafetyChecker:
    """Rule-based safety checker that scans text for hazardous conditions.

    No API client needed — all checks are pure regex pattern matching
    against predefined safety rules.
    """

    def __init__(self) -> None:
        """Compile regex patterns for efficient repeated matching."""
        self._compiled_rules: list[tuple[list[re.Pattern], dict]] = []
        for rule in SAFETY_RULES:
            compiled = [re.compile(p, re.IGNORECASE) for p in rule["patterns"]]
            self._compiled_rules.append((compiled, rule))

    def check_diagnosis(self, diagnosis_text: str) -> list[SafetyAlert]:
        """Scan diagnosis text for safety-critical conditions.

        Args:
            diagnosis_text: Free-text diagnosis from AI engine or mechanic.

        Returns:
            List of SafetyAlert objects for any matched safety rules.
        """
        alerts: list[SafetyAlert] = []
        seen_titles: set[str] = set()

        for compiled_patterns, rule in self._compiled_rules:
            for pattern in compiled_patterns:
                if pattern.search(diagnosis_text):
                    if rule["title"] not in seen_titles:
                        seen_titles.add(rule["title"])
                        alerts.append(SafetyAlert(
                            level=rule["level"],
                            title=rule["title"],
                            message=rule["message"],
                            affected_system=rule["affected_system"],
                            immediate_action=rule["immediate_action"],
                            do_not=rule.get("do_not"),
                        ))
                    break  # One match per rule is enough

        return alerts

    def check_symptoms(self, symptoms: list[str]) -> list[SafetyAlert]:
        """Scan a list of symptoms for safety-critical combinations.

        Args:
            symptoms: List of symptom descriptions.

        Returns:
            List of SafetyAlert objects for any matched safety rules.
        """
        # Combine symptoms into a single searchable string
        combined = " | ".join(symptoms)
        return self.check_diagnosis(combined)

    def check_repair_procedure(self, steps: list[str]) -> list[SafetyAlert]:
        """Scan repair procedure steps for safety hazards.

        Args:
            steps: List of repair step descriptions.

        Returns:
            List of SafetyAlert objects for steps involving dangerous operations.
        """
        alerts: list[SafetyAlert] = []
        seen_titles: set[str] = set()

        for step in steps:
            step_lower = step.lower()
            for keyword, rule in REPAIR_SAFETY_KEYWORDS.items():
                if keyword in step_lower:
                    if rule["title"] not in seen_titles:
                        seen_titles.add(rule["title"])
                        alerts.append(SafetyAlert(
                            level=rule["level"],
                            title=rule["title"],
                            message=rule["message"],
                            affected_system=rule["affected_system"],
                            immediate_action=rule["immediate_action"],
                            do_not=rule.get("do_not"),
                        ))

        return alerts


# ---------------------------------------------------------------------------
# Formatting function
# ---------------------------------------------------------------------------

def format_alerts(alerts: list[SafetyAlert]) -> str:
    """Format safety alerts for terminal display.

    Sorts alerts by severity (CRITICAL first), then formats each with
    appropriate visual indicators.

    Args:
        alerts: List of SafetyAlert objects.

    Returns:
        Formatted string for display. Empty string if no alerts.
    """
    if not alerts:
        return ""

    # Sort by alert level priority
    sorted_alerts = sorted(alerts, key=lambda a: _ALERT_ORDER[a.level])

    level_icons = {
        AlertLevel.CRITICAL: "\u26a0\ufe0f  CRITICAL",
        AlertLevel.WARNING: "\u26a0\ufe0f  WARNING",
        AlertLevel.CAUTION: "\u2139\ufe0f  CAUTION",
        AlertLevel.INFO: "\u2139\ufe0f  INFO",
    }

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("SAFETY ALERTS")
    lines.append("=" * 60)

    for alert in sorted_alerts:
        lines.append("")
        lines.append(f"[{level_icons[alert.level]}] {alert.title}")
        lines.append(f"  System: {alert.affected_system}")
        lines.append(f"  {alert.message}")
        lines.append(f"  Action: {alert.immediate_action}")
        if alert.do_not:
            lines.append(f"  DO NOT: {alert.do_not}")
        lines.append("-" * 60)

    return "\n".join(lines)
