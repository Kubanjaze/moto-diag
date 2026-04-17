"""Multi-symptom correlation — connects seemingly unrelated symptoms to a single root cause.

Motorcycles often present multiple symptoms from a single underlying failure. A mechanic
who recognizes the pattern can diagnose faster and avoid chasing individual symptoms.

Example: {overheating, loss of power, coolant smell} → head gasket failure.
Without correlation, a tech might chase the overheating separately from the power loss.

Matching logic:
- Full match: all symptoms in a rule's set are present → highest confidence
- Partial match: >= 2 symptoms from a 3+ symptom rule → reduced confidence
- Match quality = (symptoms matched / total symptoms in rule)
"""

from typing import Optional

from pydantic import BaseModel, Field


class CorrelationRule(BaseModel):
    """A predefined multi-symptom correlation pattern."""
    rule_id: str = Field(..., description="Unique identifier for this rule")
    symptom_set: set[str] = Field(..., description="Set of symptoms that together indicate the root cause")
    root_cause: str = Field(..., description="The single root cause that produces all these symptoms")
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Base confidence when all symptoms match (1.0 = certain, 0.7 = likely)",
    )
    explanation: str = Field(..., description="Mechanic-readable explanation of why these symptoms correlate")
    system_category: str = Field(
        ..., description="Primary system: electrical, fuel, mechanical, cooling, drivetrain, braking"
    )
    severity: str = Field(
        default="medium",
        description="Typical severity: critical, high, medium, low",
    )
    common_vehicles: list[str] = Field(
        default_factory=list,
        description="Vehicle makes/models where this pattern is especially common",
    )


class CorrelationMatch(BaseModel):
    """Result of matching symptoms against a correlation rule."""
    rule: CorrelationRule = Field(..., description="The matched correlation rule")
    matched_symptoms: set[str] = Field(
        default_factory=set, description="Which of the input symptoms matched the rule"
    )
    unmatched_rule_symptoms: set[str] = Field(
        default_factory=set, description="Rule symptoms NOT present in the input"
    )
    match_quality: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Fraction of rule symptoms that were matched (matched / total)",
    )
    adjusted_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Base confidence * match_quality — reflects partial match uncertainty",
    )
    is_full_match: bool = Field(
        default=False, description="True if all rule symptoms were found in the input"
    )


# ---------------------------------------------------------------------------
# Predefined correlation rules — motorcycle-specific multi-symptom patterns
# ---------------------------------------------------------------------------

CORRELATION_RULES: list[CorrelationRule] = [
    # --- Cooling system ---
    CorrelationRule(
        rule_id="CORR-001",
        symptom_set={"overheating", "loss of power", "coolant smell"},
        root_cause="Head gasket failure",
        confidence=0.85,
        explanation="Coolant leaking past the head gasket causes overheating (lost coolant volume), "
                    "power loss (compression leak into coolant jacket), and coolant smell (burning coolant "
                    "in exhaust or on hot surfaces). Common on air-cooled twins after high-mileage thermal cycling.",
        system_category="cooling",
        severity="critical",
        common_vehicles=["Harley-Davidson Twin Cam", "Harley-Davidson Evolution"],
    ),
    CorrelationRule(
        rule_id="CORR-002",
        symptom_set={"overheating", "fan not running", "temperature gauge high"},
        root_cause="Cooling fan circuit failure",
        confidence=0.90,
        explanation="Fan relay, fan motor, or temperature sensor failure prevents the cooling fan from "
                    "activating. Coolant temperature rises, gauge shows high, engine overheats at idle or "
                    "low speed where airflow can't compensate. Common on liquid-cooled sport bikes in traffic.",
        system_category="cooling",
        severity="high",
        common_vehicles=["Honda CBR", "Kawasaki Ninja", "Yamaha YZF"],
    ),

    # --- Electrical system ---
    CorrelationRule(
        rule_id="CORR-003",
        symptom_set={"battery not charging", "dim lights", "check engine light on"},
        root_cause="Stator / regulator-rectifier failure",
        confidence=0.88,
        explanation="A failed stator produces insufficient AC, so the reg/rec can't charge the battery. "
                    "Voltage drops below 12V causing dim lights and ECU errors (check engine light). The "
                    "battery slowly drains until the bike dies. Classic failure on many Japanese bikes and "
                    "Harley Sportsters with known stator connector melting issues.",
        system_category="electrical",
        severity="high",
        common_vehicles=["Harley-Davidson Sportster", "Honda CBR600", "Kawasaki Vulcan"],
    ),
    CorrelationRule(
        rule_id="CORR-004",
        symptom_set={"no spark", "battery not charging", "fuse blowing"},
        root_cause="Electrical short circuit in ignition/charging harness",
        confidence=0.80,
        explanation="A short in the wiring harness (often from chafed insulation near frame welds or "
                    "connector corrosion) draws excess current, blowing fuses. The short can simultaneously "
                    "kill the ignition circuit (no spark) and damage the charging system. Check for melted "
                    "wires near the steering head, under the tank, and at the stator connector.",
        system_category="electrical",
        severity="critical",
        common_vehicles=["Harley-Davidson", "older Japanese bikes"],
    ),
    CorrelationRule(
        rule_id="CORR-005",
        symptom_set={"gauge flicker", "dim lights", "intermittent stalling"},
        root_cause="Loose or corroded battery/ground connections",
        confidence=0.82,
        explanation="Corroded battery terminals or loose ground connections cause voltage instability. "
                    "Gauges flicker as voltage fluctuates, lights dim under load, and the ECU may lose "
                    "power momentarily causing stalls. Often misdiagnosed as a bad stator when the real "
                    "problem is a $0 cleanup of battery posts and ground bolts.",
        system_category="electrical",
        severity="medium",
        common_vehicles=["all makes"],
    ),

    # --- Fuel system ---
    CorrelationRule(
        rule_id="CORR-006",
        symptom_set={"won't start", "fuel smell", "flooding"},
        root_cause="Fuel system flooding (stuck float/injector)",
        confidence=0.85,
        explanation="A stuck carburetor float needle or leaking fuel injector allows fuel to continuously "
                    "flow into the intake. The engine floods, won't start (spark plugs fouled), and raw fuel "
                    "smell is obvious. On carbureted bikes check float height and needle valve; on EFI bikes "
                    "check injector seal and fuel pressure regulator.",
        system_category="fuel",
        severity="high",
        common_vehicles=["all carbureted bikes", "early EFI models"],
    ),
    CorrelationRule(
        rule_id="CORR-007",
        symptom_set={"backfires", "loss of power", "rough idle"},
        root_cause="Intake vacuum leak",
        confidence=0.83,
        explanation="A vacuum leak at the intake manifold, carburetor boot, or throttle body gasket allows "
                    "unmetered air into the engine. The lean condition causes rough idle, backfires on "
                    "deceleration (unburned fuel igniting in hot exhaust), and power loss under load. "
                    "Spray carb cleaner around intake joints with engine running — RPM change confirms leak.",
        system_category="fuel",
        severity="medium",
        common_vehicles=["all makes"],
    ),
    CorrelationRule(
        rule_id="CORR-008",
        symptom_set={"hesitation", "loss of power", "lean surge"},
        root_cause="Clogged fuel filter or failing fuel pump",
        confidence=0.78,
        explanation="A restricted fuel filter or weak fuel pump can't deliver enough fuel at higher demand. "
                    "The engine hesitates during acceleration, loses power at sustained high RPM, and may "
                    "surge at steady cruise as fuel pressure fluctuates. Check fuel pressure and flow rate.",
        system_category="fuel",
        severity="medium",
        common_vehicles=["EFI bikes with in-tank pumps"],
    ),

    # --- Mechanical ---
    CorrelationRule(
        rule_id="CORR-009",
        symptom_set={"noise", "rough idle", "loss of power"},
        root_cause="Cam chain tensioner failure",
        confidence=0.80,
        explanation="A worn or failed cam chain tensioner allows the cam chain to slap against the guides, "
                    "producing a rattling/slapping noise. Loose chain timing shifts valve events, causing "
                    "rough idle and power loss. If ignored, the chain can skip teeth and bend valves. "
                    "Listen for rattle at startup that fades — the tensioner takes up slack when oil pressure builds.",
        system_category="mechanical",
        severity="high",
        common_vehicles=["Honda CB", "Kawasaki", "Suzuki GSX"],
    ),
    CorrelationRule(
        rule_id="CORR-010",
        symptom_set={"knocking", "loss of power", "overheating"},
        root_cause="Detonation / pre-ignition damage",
        confidence=0.82,
        explanation="Detonation (knock) causes piston/ring damage leading to power loss and increased "
                    "friction heat. Often caused by low-octane fuel, excessive carbon buildup, or "
                    "over-advanced ignition timing. The knock itself is audible under load. If sustained, "
                    "can crack pistons or damage bearings. Check timing, fuel grade, and carbon deposits.",
        system_category="mechanical",
        severity="critical",
        common_vehicles=["high-compression engines", "Harley-Davidson Twin Cam"],
    ),

    # --- Drivetrain ---
    CorrelationRule(
        rule_id="CORR-011",
        symptom_set={"vibration at speed", "noise", "chain noise"},
        root_cause="Worn chain and sprockets",
        confidence=0.87,
        explanation="A worn chain and sprockets create play that manifests as vibration at speed, "
                    "metallic noise under acceleration/deceleration, and audible chain slapping/grinding. "
                    "Check chain tension (should have ~1 inch free play), inspect sprocket teeth for "
                    "hooked or sharpened profiles. Always replace chain and both sprockets as a set.",
        system_category="drivetrain",
        severity="medium",
        common_vehicles=["all chain-drive bikes"],
    ),
    CorrelationRule(
        rule_id="CORR-012",
        symptom_set={"clutch slipping", "burning smell", "loss of power"},
        root_cause="Worn clutch plates",
        confidence=0.88,
        explanation="Worn friction plates can't grip under load — RPM rises but speed doesn't. "
                    "The slipping generates heat (burning smell from overheated oil) and manifests as "
                    "power loss under acceleration. May also cause hard shifting. Measure plate thickness "
                    "and warpage against service limits; replace friction and steel plates as a set.",
        system_category="drivetrain",
        severity="medium",
        common_vehicles=["all wet-clutch bikes"],
    ),

    # --- Braking ---
    CorrelationRule(
        rule_id="CORR-013",
        symptom_set={"spongy brake lever", "brake fade", "brake fluid leak"},
        root_cause="Brake hydraulic system failure",
        confidence=0.90,
        explanation="Air in brake lines (from a leak or old fluid) makes the lever spongy. Fluid loss "
                    "reduces hydraulic pressure causing fade under sustained braking. A visible leak at "
                    "caliper seals, banjo bolts, or master cylinder confirms the diagnosis. Rebuild or "
                    "replace the leaking component, flush and bleed the entire circuit.",
        system_category="braking",
        severity="critical",
        common_vehicles=["all makes — age-related"],
    ),
    CorrelationRule(
        rule_id="CORR-014",
        symptom_set={"brake squeal", "brake drag", "overheating"},
        root_cause="Seized brake caliper piston",
        confidence=0.85,
        explanation="A corroded caliper piston doesn't retract fully after braking. The pad drags on "
                    "the rotor, causing squeal (pad vibration), heat buildup (overheating rotor and "
                    "caliper), and potential brake fade. The wheel may be noticeably harder to spin by "
                    "hand. Rebuild the caliper: clean bore, replace seals, and install new pads.",
        system_category="braking",
        severity="high",
        common_vehicles=["all makes — common after winter storage"],
    ),

    # --- Ignition ---
    CorrelationRule(
        rule_id="CORR-015",
        symptom_set={"hard starting", "rough idle", "backfires"},
        root_cause="Fouled or worn spark plugs",
        confidence=0.75,
        explanation="Worn or carbon-fouled plugs produce weak spark, causing incomplete combustion. "
                    "The engine is hard to start (weak ignition), idles rough (misfiring cylinders), "
                    "and backfires (unburned fuel reaching the exhaust). Pull plugs and inspect: black "
                    "sooty = rich/fouled, white = lean, tan = good. Check gap and replace if worn.",
        system_category="electrical",
        severity="low",
        common_vehicles=["all makes"],
    ),
    CorrelationRule(
        rule_id="CORR-016",
        symptom_set={"stalls at idle", "hesitation", "check engine light on"},
        root_cause="Idle air control valve / throttle position sensor failure",
        confidence=0.79,
        explanation="A faulty IAC valve can't regulate idle air, causing stalls. A bad TPS sends wrong "
                    "throttle position data to the ECU, causing hesitation during transitions. Both throw "
                    "CEL codes. Clean the IAC first (often carbon-clogged); if symptoms persist, check TPS "
                    "voltage sweep with a multimeter — should be smooth 0.5V-4.5V with no dead spots.",
        system_category="fuel",
        severity="medium",
        common_vehicles=["EFI bikes"],
    ),

    # --- Suspension / handling ---
    CorrelationRule(
        rule_id="CORR-017",
        symptom_set={"vibration at speed", "wobble", "uneven tire wear"},
        root_cause="Wheel bearing failure or bent rim",
        confidence=0.80,
        explanation="A worn wheel bearing introduces play in the axle, causing vibration and potential "
                    "speed wobble. Uneven tire wear results from the wheel not tracking true. Grab the "
                    "wheel at 12 and 6 o'clock and check for play; spin it and listen for grinding. "
                    "A bent rim causes vibration at a specific speed — visible on a truing stand.",
        system_category="mechanical",
        severity="high",
        common_vehicles=["all makes — especially after pothole impact"],
    ),

    # --- Exhaust / emissions ---
    CorrelationRule(
        rule_id="CORR-018",
        symptom_set={"loss of power", "excessive exhaust smoke", "oil consumption"},
        root_cause="Worn piston rings or valve stem seals",
        confidence=0.83,
        explanation="Worn rings or valve seals allow oil past into the combustion chamber. Blue/white "
                    "exhaust smoke (especially on startup or deceleration), power loss from reduced "
                    "compression, and increasing oil consumption between changes. Compression test and "
                    "leak-down test differentiate rings (low compression) from valve seals (smoke on decel).",
        system_category="mechanical",
        severity="high",
        common_vehicles=["high-mileage engines"],
    ),
]


class SymptomCorrelator:
    """Matches reported symptoms against predefined multi-symptom correlation rules.

    Identifies cases where multiple seemingly unrelated symptoms point to a single
    root cause, enabling faster and more accurate diagnosis.
    """

    def __init__(self, rules: Optional[list[CorrelationRule]] = None) -> None:
        """Initialize correlator with correlation rules.

        Args:
            rules: Custom rules list. Defaults to CORRELATION_RULES if not provided.
        """
        self._rules = rules if rules is not None else list(CORRELATION_RULES)

    @property
    def rule_count(self) -> int:
        """Number of correlation rules loaded."""
        return len(self._rules)

    def correlate(
        self,
        symptoms: list[str],
        min_matched: int = 2,
        min_quality: float = 0.0,
    ) -> list[CorrelationMatch]:
        """Match symptoms against all correlation rules.

        For each rule, checks how many of its symptom_set appear in the input.
        Full matches (all rule symptoms present) and partial matches (>= min_matched)
        are included.

        Args:
            symptoms: List of reported symptom strings.
            min_matched: Minimum number of rule symptoms that must match (default 2).
            min_quality: Minimum match_quality to include in results (default 0.0).

        Returns:
            List of CorrelationMatch objects ranked by adjusted_confidence descending.
        """
        if not symptoms:
            return []

        # Normalize input symptoms to lowercase for matching
        input_normalized = set(s.lower().strip() for s in symptoms)

        matches: list[CorrelationMatch] = []

        for rule in self._rules:
            rule_symptoms_lower = set(s.lower().strip() for s in rule.symptom_set)

            # Find which rule symptoms appear in the input
            matched = rule_symptoms_lower & input_normalized
            unmatched = rule_symptoms_lower - input_normalized

            matched_count = len(matched)
            total_in_rule = len(rule_symptoms_lower)

            if matched_count < min_matched:
                continue

            match_quality = matched_count / total_in_rule if total_in_rule > 0 else 0.0

            if match_quality < min_quality:
                continue

            adjusted_confidence = round(rule.confidence * match_quality, 3)

            # Map matched symptoms back to original case for readability
            matched_original = set()
            for s in symptoms:
                if s.lower().strip() in matched:
                    matched_original.add(s)

            unmatched_original = set()
            for s in rule.symptom_set:
                if s.lower().strip() in unmatched:
                    unmatched_original.add(s)

            matches.append(CorrelationMatch(
                rule=rule,
                matched_symptoms=matched_original,
                unmatched_rule_symptoms=unmatched_original,
                match_quality=round(match_quality, 3),
                adjusted_confidence=adjusted_confidence,
                is_full_match=(matched_count == total_in_rule),
            ))

        # Sort by adjusted_confidence descending, then match_quality
        matches.sort(key=lambda m: (m.adjusted_confidence, m.match_quality), reverse=True)
        return matches

    def get_rules_by_system(self, system_category: str) -> list[CorrelationRule]:
        """Get all rules for a specific system category.

        Args:
            system_category: System to filter by (electrical, fuel, mechanical, etc.).

        Returns:
            List of matching rules.
        """
        return [
            r for r in self._rules
            if r.system_category.lower() == system_category.lower()
        ]

    def get_rules_by_severity(self, severity: str) -> list[CorrelationRule]:
        """Get all rules at or above a severity level.

        Args:
            severity: Minimum severity level (critical, high, medium, low).

        Returns:
            List of matching rules.
        """
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        min_level = severity_order.get(severity.lower(), 0)
        return [
            r for r in self._rules
            if severity_order.get(r.severity.lower(), 0) >= min_level
        ]

    def get_rule_by_id(self, rule_id: str) -> Optional[CorrelationRule]:
        """Look up a specific rule by ID.

        Args:
            rule_id: The rule identifier (e.g., 'CORR-001').

        Returns:
            The matching rule, or None.
        """
        for r in self._rules:
            if r.rule_id == rule_id:
                return r
        return None
