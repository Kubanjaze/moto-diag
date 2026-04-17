"""Intermittent fault analysis — specialized reasoning for "sometimes it does X" problems.

Intermittent faults are the hardest to diagnose because they don't appear on demand.
This module provides structured pattern matching for condition-dependent faults:
- Temperature-dependent (cold start, heat soak)
- Load-dependent (acceleration, sustained speed)
- Weather-dependent (rain, humidity)
- RPM-dependent (idle vs high RPM)
- Time-dependent (morning, after sitting)

The analyzer extracts environmental conditions from freeform descriptions,
matches against predefined intermittent patterns, and provides targeted
diagnostic approaches for each pattern.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field


class EnvironmentalFactor(BaseModel):
    """An environmental or operating condition relevant to an intermittent fault."""
    factor_type: str = Field(
        ...,
        description="Category: temperature, humidity, vibration, load, time_of_day, "
                    "fuel_level, rpm, weather, duration, electrical_load",
    )
    description: str = Field(..., description="Specific condition described")
    relevance: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="How strongly this factor influences the intermittent behavior (0.0-1.0)",
    )


class IntermittentPattern(BaseModel):
    """A predefined pattern for condition-dependent intermittent faults."""
    pattern_id: str = Field(..., description="Unique identifier for this pattern")
    description: str = Field(..., description="Human-readable name for the pattern")
    trigger_conditions: list[str] = Field(
        ..., description="Conditions under which the fault appears"
    )
    likely_causes: list[str] = Field(
        ..., description="Probable root causes for this pattern"
    )
    diagnostic_approach: list[str] = Field(
        ..., description="Step-by-step diagnostic procedure"
    )
    system_category: str = Field(
        default="general",
        description="Primary system: electrical, fuel, mechanical, cooling, drivetrain",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords that indicate this pattern in freeform text",
    )


class IntermittentMatch(BaseModel):
    """Result of matching a fault description against intermittent patterns."""
    pattern: IntermittentPattern = Field(..., description="The matched pattern")
    keyword_hits: list[str] = Field(
        default_factory=list, description="Which keywords matched in the input text"
    )
    match_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="How well the input matches this pattern (0.0-1.0)",
    )
    extracted_factors: list[EnvironmentalFactor] = Field(
        default_factory=list,
        description="Environmental factors extracted from the input relevant to this pattern",
    )


# ---------------------------------------------------------------------------
# Predefined intermittent fault patterns — motorcycle-specific
# ---------------------------------------------------------------------------

INTERMITTENT_PATTERNS: list[IntermittentPattern] = [
    # --- Temperature-dependent ---
    IntermittentPattern(
        pattern_id="INT-001",
        description="Only when cold — cold start / warm-up issues",
        trigger_conditions=[
            "Fault appears only during cold start or first few minutes of riding",
            "Disappears once engine reaches operating temperature",
            "More pronounced in cold weather or after overnight sitting",
        ],
        likely_causes=[
            "Enrichment circuit malfunction (choke cable, fast idle cam, cold start injector)",
            "Tight valve clearances — valves seat fully only when metal contracts cold",
            "Temperature sensor providing incorrect reading to ECU (stuck reading 'hot')",
            "Thickened engine oil increasing drag on cold internals",
            "Stiff carburetor slides or throttle cables in cold conditions",
        ],
        diagnostic_approach=[
            "Check valve clearances cold — compare to service manual spec",
            "Verify choke / fast idle / cold start enrichment is functioning",
            "Read coolant temperature sensor with scan tool while cold — should match ambient",
            "Check oil grade — switch to manufacturer-recommended cold-weather weight",
            "Inspect throttle cables and carburetor slides for free movement when cold",
            "Log data while cold-starting: RPM, fuel trim, coolant temp, intake temp",
        ],
        system_category="fuel",
        keywords=["cold", "cold start", "warm up", "warming up", "first start", "morning",
                  "overnight", "sitting", "choke", "cold weather", "winter"],
    ),
    IntermittentPattern(
        pattern_id="INT-002",
        description="Only when hot — heat soak / thermal issues",
        trigger_conditions=[
            "Fault appears after engine is fully warmed up",
            "Worse in hot weather or after extended riding",
            "May appear after shut-down and restart (heat soak)",
        ],
        likely_causes=[
            "Vapor lock in fuel lines (fuel boils in hot line near engine)",
            "Heat soak after shutdown — fuel percolates in carburetor bowls",
            "Thermal expansion closing valve clearances (valves too tight when hot)",
            "Ignition module heat failure (common on older CDI/TCI units)",
            "Coolant system marginal — thermostat, water pump, radiator cap",
            "Hot-start enrichment circuit fault (EFI only)",
        ],
        diagnostic_approach=[
            "Check valve clearances hot — compare to service manual hot spec",
            "Inspect fuel line routing — reroute away from exhaust if too close",
            "Test ignition module: ride until fault appears, immediately check for spark",
            "Check coolant level, thermostat opening temp, water pump flow, radiator cap pressure",
            "On carbureted bikes: check float level, inspect for fuel percolation after shutdown",
            "Monitor fuel pressure during hot operation with inline gauge",
        ],
        system_category="fuel",
        keywords=["hot", "heat", "warm", "after riding", "hot weather", "summer",
                  "heat soak", "shut down", "restart", "vapor lock", "overheated"],
    ),

    # --- Load-dependent ---
    IntermittentPattern(
        pattern_id="INT-003",
        description="Only under load — acceleration / hill climbing issues",
        trigger_conditions=[
            "Fault appears during hard acceleration or hill climbing",
            "Normal at idle and light cruising",
            "Worse with passenger or cargo",
        ],
        likely_causes=[
            "Fuel delivery insufficient at high demand (weak pump, clogged filter, small jets)",
            "Ignition breakdown under load (weak coil, failing plug wires, worn plugs)",
            "Compression loss under load (leaking head gasket, worn rings)",
            "Exhaust restriction (clogged catalytic converter, crushed pipe)",
            "Clutch slipping under high torque — not drivetrain but mimics power loss",
        ],
        diagnostic_approach=[
            "Check fuel pressure under load — install inline gauge, ride under load, watch for pressure drop",
            "Perform compression test and leak-down test — compare cylinders",
            "Check spark plug condition — load-related misfire leaves distinct plug appearance",
            "Inspect exhaust for restrictions — check backpressure at header with gauge",
            "Test clutch: hold brake, engage gear, slowly release clutch — engine should stall (not slip)",
            "Check coil resistance primary and secondary — compare to spec",
        ],
        system_category="fuel",
        keywords=["under load", "acceleration", "accelerating", "hill", "uphill", "hard riding",
                  "passenger", "cargo", "full throttle", "wide open", "WOT"],
    ),

    # --- Weather-dependent ---
    IntermittentPattern(
        pattern_id="INT-004",
        description="Only in rain — moisture-related electrical faults",
        trigger_conditions=[
            "Fault appears in rain or high humidity",
            "Disappears when dry or after garage time",
            "May appear after washing the bike",
        ],
        likely_causes=[
            "Moisture in ignition system — cracked plug caps, worn boots, water in coil",
            "Corroded electrical connections allowing water ingress",
            "Ground fault through water bridge on corroded frame ground points",
            "Water in air filter housing affecting mixture or MAF sensor",
            "Wet clutch cable or throttle cable binding when wet",
        ],
        diagnostic_approach=[
            "Spray plug wires, coil, and caps with water while running — watch for misfire",
            "Inspect all electrical connectors for corrosion, green residue, or loose fit",
            "Check frame ground points — clean to bare metal, apply dielectric grease",
            "Inspect air filter housing for water ingress path (missing drain, cracked housing)",
            "Test all sensors (TPS, MAP, O2) for erratic readings in humid conditions",
            "Apply dielectric grease to all exposed connectors as preventive measure",
        ],
        system_category="electrical",
        keywords=["rain", "wet", "water", "humid", "humidity", "moisture", "washing",
                  "damp", "fog", "spray", "puddle"],
    ),

    # --- RPM-dependent ---
    IntermittentPattern(
        pattern_id="INT-005",
        description="Only at high RPM — fuel/ignition/valve-related limits",
        trigger_conditions=[
            "Fault appears only above a specific RPM threshold",
            "Normal at idle and low-to-mid RPM",
            "May feel like hitting a wall or rev limiter early",
        ],
        likely_causes=[
            "Fuel pump capacity exceeded at high RPM fuel demand",
            "Valve float — springs too weak to close valves at high RPM",
            "Ignition breakdown at high RPM — coil can't fire fast enough",
            "Rev limiter set incorrectly (aftermarket ECU, loose connection to speed sensor)",
            "Exhaust restriction becoming limiting at high flow rates",
            "Cam chain tensioner allowing chain to skip at high RPM",
        ],
        diagnostic_approach=[
            "Check fuel pressure at high RPM with inline gauge — should hold steady",
            "Check valve spring free length and installed height against spec",
            "Scope ignition waveform at high RPM — look for breakdown or misfire",
            "Check for aftermarket ECU / piggyback that may have incorrect rev limit",
            "Inspect cam chain tensioner — manual check for excessive play",
            "Listen for unusual valve train noise at the RPM threshold",
        ],
        system_category="mechanical",
        keywords=["high rpm", "high revs", "revving", "redline", "top end", "above 6000",
                  "above 8000", "above 10000", "rev limit", "power band"],
    ),
    IntermittentPattern(
        pattern_id="INT-006",
        description="Only at idle — low-speed running issues",
        trigger_conditions=[
            "Fault appears at idle or very low RPM",
            "Clears up once RPM is raised above ~2000",
            "Worse when electrical accessories are on (lights, heated grips)",
        ],
        likely_causes=[
            "Idle air control valve stuck or carbon-clogged",
            "Vacuum leak too small to affect running above idle",
            "Idle mixture screw out of adjustment (carbureted)",
            "Low charging output at idle dragging RPM down (electrical load)",
            "Intake valves slightly tight — leaking at low-lift idle opening",
        ],
        diagnostic_approach=[
            "Clean idle air control valve with throttle body cleaner",
            "Spray carb cleaner around intake joints at idle — listen for RPM change",
            "Adjust idle mixture screws to factory spec (turns from seated)",
            "Measure charging voltage at idle with all accessories on — should be >13V",
            "Check valve clearances — intake side especially",
        ],
        system_category="fuel",
        keywords=["idle", "idling", "at idle", "low rpm", "stopped", "traffic",
                  "red light", "sitting still"],
    ),

    # --- Random / no pattern ---
    IntermittentPattern(
        pattern_id="INT-007",
        description="Random / no discernible pattern — intermittent connection faults",
        trigger_conditions=[
            "Fault appears and disappears with no obvious trigger",
            "Cannot reproduce on demand",
            "May be related to vibration (appears on rough roads)",
        ],
        likely_causes=[
            "Loose wire connection — makes/breaks contact with vibration",
            "Intermittent short circuit — insulation chafe making random contact",
            "Cracked solder joint on PCB (ECU, instrument cluster, relay)",
            "Corroded connector pin with intermittent contact resistance",
            "Failing relay with intermittent internal contact",
            "Broken wire strand inside insulation (flexion failure)",
        ],
        diagnostic_approach=[
            "Wiggle test: with engine running, wiggle every connector and harness section — watch for fault",
            "Visual inspection: look for chafed wires, green corrosion, melted insulation, loose pins",
            "Check ALL ground points — frame, engine, battery negative",
            "Measure voltage drop across suspect connections under load",
            "Tap test: gently tap relays and ECU while running — unstable relay will cut out",
            "Thermal cycle: use heat gun on suspect components to reveal thermal-sensitive failures",
            "If vibration-related: ride on rough road with data logger connected to narrow down",
        ],
        system_category="electrical",
        keywords=["random", "sometimes", "intermittent", "no pattern", "can't reproduce",
                  "comes and goes", "unpredictable", "vibration", "bumpy road", "rough road"],
    ),

    # --- Time-dependent ---
    IntermittentPattern(
        pattern_id="INT-008",
        description="After sitting / time-dependent — deterioration-related",
        trigger_conditions=[
            "Fault appears after the bike has sat unused for days/weeks/months",
            "Goes away after riding for a while",
            "Worse after longer storage periods",
        ],
        likely_causes=[
            "Stale fuel — varnish clogging jets or injectors",
            "Battery sulfation from sitting — reduced capacity",
            "Stuck float valve — varnish or corrosion from stagnant fuel",
            "Moisture condensation in fuel tank (temperature cycling during storage)",
            "Seized caliper pistons from corrosion during inactivity",
            "Dry-rotted rubber components (hoses, seals, diaphragms)",
        ],
        diagnostic_approach=[
            "Check fuel age and quality — drain and replace if over 3 months old",
            "Load test battery — not just voltage, but capacity under load",
            "Inspect carburetor passages with carb cleaner spray — all jets must flow freely",
            "Check brake calipers for drag — spin each wheel by hand",
            "Inspect all rubber hoses, vacuum lines, and diaphragms for cracking",
            "Add fuel stabilizer before storage; use battery tender during storage",
        ],
        system_category="fuel",
        keywords=["sitting", "sat", "storage", "stored", "parked", "unused", "garage",
                  "winter storage", "hasn't been ridden", "first ride"],
    ),

    # --- Electrical load dependent ---
    IntermittentPattern(
        pattern_id="INT-009",
        description="Only with accessories on — electrical load / charging system marginal",
        trigger_conditions=[
            "Fault appears when headlights, heated grips, or other accessories are on",
            "Worse at idle or low RPM",
            "May involve dim lights, gauge flickering, or stalling",
        ],
        likely_causes=[
            "Charging system output marginal — stator partially failed (lost phase)",
            "Regulator-rectifier degraded — can't maintain 14V under full load",
            "Undersized wiring for aftermarket accessories (heated gear, auxiliary lights)",
            "Battery losing capacity — can't buffer voltage dips at low RPM",
            "Poor ground connections increasing resistance under high current draw",
        ],
        diagnostic_approach=[
            "Measure charging voltage at battery: idle with lights on, 3000RPM with all accessories",
            "Should see 13.5-14.5V at 3000RPM; below 13V = charging problem",
            "Test stator AC output (disconnect from reg/rec, measure across each phase pair)",
            "Load test battery — should hold >9.6V for 15 seconds under load",
            "Check total accessory current draw vs charging system rated output",
            "Inspect main fuse, battery cables, and frame ground for corrosion/resistance",
        ],
        system_category="electrical",
        keywords=["accessories", "lights on", "headlight", "heated grips", "heated gear",
                  "auxiliary lights", "electrical load", "turn signals"],
    ),

    # --- Speed-dependent ---
    IntermittentPattern(
        pattern_id="INT-010",
        description="Only at specific speed — resonance / aerodynamic / drivetrain",
        trigger_conditions=[
            "Fault appears at a specific speed or narrow speed range",
            "Gone above and below that speed",
            "May involve vibration, wobble, or noise",
        ],
        likely_causes=[
            "Wheel balance issue — out-of-balance wheel resonates at specific speed",
            "Tire flat spot or belt separation — harmonic at certain rotational speed",
            "Drivetrain resonance — chain/belt tension creates vibration at specific RPM/speed",
            "Steering head bearing notch (Brinelling) — headshake at specific lean+speed combo",
            "Aerodynamic buffeting from fairing/windscreen at certain speeds",
        ],
        diagnostic_approach=[
            "Check wheel balance — remove and spin on balancer, add weights as needed",
            "Inspect tires for flat spots, uneven wear, belt separation (bulges)",
            "Check chain/belt tension against spec — test at different points of rotation",
            "Check steering head bearings: lift front wheel, check for notchy feeling when turning",
            "Try different windscreen height or remove fairing components to test aero theory",
            "Check wheel bearings for play — grab wheel at 12 and 6, push/pull",
        ],
        system_category="mechanical",
        keywords=["at speed", "specific speed", "60 mph", "70 mph", "highway",
                  "cruising speed", "wobble", "shimmy", "death wobble"],
    ),

    # --- Fuel level dependent ---
    IntermittentPattern(
        pattern_id="INT-011",
        description="Only on low fuel — fuel pickup / pump related",
        trigger_conditions=[
            "Fault appears when fuel tank is below quarter full",
            "Worse during hard acceleration, cornering, or uphill on low fuel",
            "Goes away after refueling",
        ],
        likely_causes=[
            "Fuel pump pickup not reaching fuel at low level (especially during lean angles)",
            "Fuel tank rust or debris settling at bottom — sucked into filter when low",
            "Fuel sender unit interfering with fuel flow at low levels",
            "Cracked fuel line inside tank exposed only when fuel level drops",
            "Fuel pump overheating — fuel normally cools the pump; low fuel = less cooling",
        ],
        diagnostic_approach=[
            "Try to reproduce at different fuel levels — compare half tank vs reserve",
            "Inspect fuel tank interior for rust, debris, sealant flakes",
            "Check inline fuel filter — replace if discolored or restricted",
            "Monitor fuel pressure during cornering and acceleration on low fuel",
            "Inspect fuel pump pickup strainer — may be partially clogged",
            "Check if fuel petcock (if equipped) reserve position resolves the issue",
        ],
        system_category="fuel",
        keywords=["low fuel", "reserve", "almost empty", "quarter tank", "fuel light",
                  "after cornering", "lean angle"],
    ),

    # --- Gear / position dependent ---
    IntermittentPattern(
        pattern_id="INT-012",
        description="Only in specific gear — transmission / drivetrain related",
        trigger_conditions=[
            "Fault appears only in one specific gear",
            "Other gears work normally",
            "May involve popping out of gear, grinding, or false neutral",
        ],
        likely_causes=[
            "Worn engagement dogs on that specific gear pair",
            "Bent or worn shift fork for that gear",
            "Shift drum detent worn — can't hold that gear position",
            "Transmission output shaft bearing worn — affects alignment in specific gear",
            "Clutch hub nut loose — allows slight shaft movement under specific gear loading",
        ],
        diagnostic_approach=[
            "Identify which gear specifically — note if it's the same gear every time",
            "Check shift linkage adjustment — may not be fully engaging that gear",
            "With engine off, shift through all gears — feel for excess resistance or looseness in the problem gear",
            "Listen for noise in that specific gear vs adjacent gears",
            "Transmission inspection requires splitting the cases — check shift forks for bend, dogs for rounding",
            "Check oil level and condition — shiny metal particles indicate internal wear",
        ],
        system_category="drivetrain",
        keywords=["specific gear", "second gear", "third gear", "fourth gear", "fifth gear",
                  "pops out", "false neutral", "won't stay in gear", "grinding gear"],
    ),
]


# ---------------------------------------------------------------------------
# Condition extraction patterns for parsing freeform text
# ---------------------------------------------------------------------------

_CONDITION_PATTERNS: list[tuple[str, str, str]] = [
    # (regex_pattern, factor_type, description_template)
    (r"\bcold\b|\bcold start\b|\bwinter\b|\bfreezing\b|\bbelow \d+", "temperature", "Cold conditions reported"),
    (r"\bhot\b|\bheat\b|\bsummer\b|\boverheated\b|\bheat soak\b", "temperature", "Hot conditions reported"),
    (r"\brain\b|\bwet\b|\bwater\b|\bhumid\b|\bmoisture\b|\bfog\b|\bdamp\b", "humidity", "Wet/humid conditions"),
    (r"\bvibrat\w*\b|\bbumpy\b|\brough road\b|\bpothole\b", "vibration", "Vibration or rough surface"),
    (r"\bunder load\b|\baccelerat\w*\b|\bhill\b|\buphill\b|\bfull throttle\b|\bWOT\b", "load", "Under load/acceleration"),
    (r"\bmorning\b|\bfirst start\b|\bovernight\b|\bafter sitting\b", "time_of_day", "Time-dependent — first start"),
    (r"\blow fuel\b|\breserve\b|\balmost empty\b|\bquarter tank\b", "fuel_level", "Low fuel condition"),
    (r"\bhigh rpm\b|\brevving\b|\bredline\b|\babove \d+\s*rpm\b", "rpm", "High RPM condition"),
    (r"\bidle\b|\bidling\b|\bstopped\b|\btraffic\b|\bred light\b", "rpm", "Idle/low RPM condition"),
    (r"\bhighway\b|\bcruising\b|\b\d+\s*mph\b|\bat speed\b", "load", "Specific speed / cruising condition"),
    (r"\blights on\b|\bheadlight\b|\baccessor\w*\b|\bheated grip\b", "electrical_load", "Electrical accessories active"),
    (r"\bafter riding\b|\blong ride\b|\bextended\b|\bsustained\b", "duration", "Extended operation duration"),
    (r"\bsitting\b|\bstorage\b|\bparked\b|\bunused\b|\bgarage\b", "time_of_day", "After storage/sitting"),
    (r"\bgear\b|\bsecond gear\b|\bthird gear\b|\bspecific gear\b", "load", "Gear-specific condition"),
    (r"\bcornering\b|\blean\b|\bturn\b|\bcurve\b", "load", "Cornering / lean angle condition"),
]


# ---------------------------------------------------------------------------
# Specialized prompt for Claude intermittent fault reasoning
# ---------------------------------------------------------------------------

INTERMITTENT_PROMPT = """You are an expert motorcycle mechanic specializing in intermittent fault diagnosis.

The customer is describing a fault that does NOT happen consistently — it comes and goes depending on conditions.

CRITICAL APPROACH FOR INTERMITTENT FAULTS:
1. IDENTIFY THE PATTERN — what conditions make it appear vs disappear?
   - Temperature (cold vs hot)
   - Load (idle vs acceleration vs cruise)
   - Weather (dry vs wet)
   - Time (first start vs after riding)
   - Electrical load (accessories on/off)
   - Fuel level (full vs low)
   - Speed/RPM (specific ranges)
   - Position (specific gear, lean angle)

2. MAP THE PATTERN TO ROOT CAUSE:
   - Temperature-dependent → thermal expansion, fluid viscosity, sensor drift
   - Load-dependent → fuel delivery, ignition strength, compression
   - Moisture-dependent → electrical connections, insulation, grounds
   - Vibration-dependent → loose connections, cracked solder, broken wire strands
   - No pattern → random electrical fault (connector, relay, solder joint)

3. PROVIDE TARGETED DIAGNOSTICS:
   - Don't suggest shotgun troubleshooting
   - Each diagnostic step should confirm or eliminate ONE specific cause
   - Order steps from cheapest/easiest to most expensive/invasive
   - Include the specific measurement or observation that confirms/eliminates each cause

4. COMMON MECHANIC TRAPS TO AVOID:
   - Replacing parts that test good in the shop (because the fault isn't active)
   - Missing ground faults that only manifest under load
   - Ignoring stator connector melting on Harleys/Japanese bikes
   - Not checking valve clearances on "random misfire" complaints
   - Assuming fuel quality is fine without testing"""


class IntermittentAnalyzer:
    """Analyzes intermittent faults by matching condition descriptions to known patterns.

    Takes symptom + condition descriptions (often freeform text from the customer),
    extracts environmental conditions, matches against predefined intermittent patterns,
    and returns ranked diagnostic approaches.
    """

    def __init__(self, patterns: Optional[list[IntermittentPattern]] = None) -> None:
        """Initialize analyzer with intermittent patterns.

        Args:
            patterns: Custom patterns list. Defaults to INTERMITTENT_PATTERNS.
        """
        self._patterns = patterns if patterns is not None else list(INTERMITTENT_PATTERNS)
        # Pre-compile condition extraction regexes
        self._condition_regexes: list[tuple[re.Pattern, str, str]] = [
            (re.compile(pat, re.IGNORECASE), ftype, desc)
            for pat, ftype, desc in _CONDITION_PATTERNS
        ]

    @property
    def pattern_count(self) -> int:
        """Number of intermittent patterns loaded."""
        return len(self._patterns)

    def extract_conditions(self, text: str) -> list[EnvironmentalFactor]:
        """Parse freeform text for environmental conditions.

        Uses regex patterns to identify temperature, humidity, vibration, load,
        time-of-day, fuel level, RPM, and other conditions mentioned in the text.

        Args:
            text: Freeform description of when the fault occurs.

        Returns:
            List of extracted EnvironmentalFactor objects (may be empty).
        """
        if not text or not text.strip():
            return []

        factors: list[EnvironmentalFactor] = []
        seen_types: set[str] = set()  # Avoid duplicate factor types

        for regex, factor_type, description in self._condition_regexes:
            if regex.search(text):
                # Only add the first match per factor_type to avoid noise
                key = f"{factor_type}:{description}"
                if key not in seen_types:
                    seen_types.add(key)
                    # Relevance based on how specific the match is
                    relevance = 0.7 if len(regex.pattern) > 20 else 0.5
                    factors.append(EnvironmentalFactor(
                        factor_type=factor_type,
                        description=description,
                        relevance=relevance,
                    ))

        return factors

    def analyze(
        self,
        symptom: str,
        condition_description: str,
        top_n: int = 5,
        min_score: float = 0.0,
    ) -> list[IntermittentMatch]:
        """Match a symptom + condition description against intermittent fault patterns.

        Scores each pattern based on keyword overlap between the combined
        symptom + condition text and the pattern's keyword list.

        Args:
            symptom: The primary symptom (e.g., "engine stalls").
            condition_description: When it happens (e.g., "only when it's raining hard").
            top_n: Maximum number of patterns to return.
            min_score: Minimum match score to include.

        Returns:
            List of IntermittentMatch objects ranked by match_score descending.
        """
        combined_text = f"{symptom} {condition_description}".lower()
        extracted_factors = self.extract_conditions(combined_text)

        matches: list[IntermittentMatch] = []

        for pattern in self._patterns:
            # Count keyword hits
            hits: list[str] = []
            for kw in pattern.keywords:
                if kw.lower() in combined_text:
                    hits.append(kw)

            if not hits:
                continue

            # Score = fraction of pattern keywords that matched
            score = len(hits) / len(pattern.keywords) if pattern.keywords else 0.0
            score = round(min(1.0, score), 3)

            if score < min_score:
                continue

            # Filter extracted factors to those relevant to this pattern
            relevant_factors = [
                f for f in extracted_factors
                if any(kw.lower() in f.description.lower() or kw.lower() in f.factor_type.lower()
                       for kw in hits)
            ]
            # If no direct factor match, include all extracted factors for context
            if not relevant_factors:
                relevant_factors = list(extracted_factors)

            matches.append(IntermittentMatch(
                pattern=pattern,
                keyword_hits=hits,
                match_score=score,
                extracted_factors=relevant_factors,
            ))

        # Sort by match_score descending
        matches.sort(key=lambda m: m.match_score, reverse=True)
        return matches[:top_n]

    def get_pattern_by_id(self, pattern_id: str) -> Optional[IntermittentPattern]:
        """Look up a specific pattern by ID.

        Args:
            pattern_id: The pattern identifier (e.g., 'INT-001').

        Returns:
            The matching pattern, or None.
        """
        for p in self._patterns:
            if p.pattern_id == pattern_id:
                return p
        return None

    def get_patterns_by_system(self, system_category: str) -> list[IntermittentPattern]:
        """Get all patterns for a specific system category.

        Args:
            system_category: System to filter by (electrical, fuel, mechanical, etc.).

        Returns:
            List of matching patterns.
        """
        return [
            p for p in self._patterns
            if p.system_category.lower() == system_category.lower()
        ]

    def get_prompt(self) -> str:
        """Return the specialized intermittent fault prompt for Claude.

        Returns:
            The INTERMITTENT_PROMPT string for injection into AI diagnostic calls.
        """
        return INTERMITTENT_PROMPT
