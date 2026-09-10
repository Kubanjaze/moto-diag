"""Shared visual-diagnostic data types, prompt, and color guides for the live Vision pipeline.

These are the REAL, production Vision schemas consumed by
``motodiag.media.vision_analysis_pipeline`` (the image-bytes Claude Vision
analyzer, Phase 191B). This module is pure data/schemas — no analyzer logic:

  - ``FindingType`` / ``Severity`` / ``VisualFinding`` / ``VisualAnalysisResult``
    — the structured-output schema the pipeline validates Claude's tool-use
    response against.
  - ``VehicleContext`` — vehicle info injected into the prompt.
  - ``VISION_ANALYSIS_PROMPT`` — the motorcycle-specific system prompt.
  - ``SMOKE_COLOR_GUIDE`` / ``FLUID_COLOR_GUIDE`` — diagnostic reference tables.

The text-only simulation analyzer that historically lived alongside these types
has moved to ``motodiag.media.sim.vision_analyzer_textsim`` (superseded, tests
only). Keep this module analyzer-free so both the live pipeline and the retained
sim can import the shared types without pulling in any analysis behavior.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FindingType(str, Enum):
    """Categories of visual diagnostic findings."""
    SMOKE = "smoke"
    LEAK = "leak"
    DAMAGE = "damage"
    GAUGE_READING = "gauge_reading"
    WEAR = "wear"
    CORROSION = "corrosion"
    MISSING_PART = "missing_part"
    MODIFICATION = "modification"


class Severity(str, Enum):
    """Severity levels for visual findings."""
    CRITICAL = "critical"   # Safety risk — do not ride
    HIGH = "high"           # Significant issue — repair before riding
    MEDIUM = "medium"       # Moderate concern — schedule repair
    LOW = "low"             # Minor observation — monitor
    INFO = "info"           # Informational — no action needed


class VisualFinding(BaseModel):
    """A single visual diagnostic finding from image analysis."""
    finding_type: FindingType = Field(..., description="Category of finding")
    description: str = Field(..., description="Detailed description of what was observed")
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence in this finding (0.0-1.0)",
    )
    location_in_image: str = Field(
        default="",
        description="Where in the image this was found (e.g., 'lower left, near exhaust')",
    )
    severity: Severity = Field(
        default=Severity.MEDIUM,
        description="How serious is this finding",
    )


class VisualAnalysisResult(BaseModel):
    """Complete result from analyzing one or more images."""
    findings: list[VisualFinding] = Field(
        default_factory=list,
        description="All visual findings detected in the image(s)",
    )
    overall_assessment: str = Field(
        default="",
        description="Summary assessment of the motorcycle's visible condition",
    )
    suggested_diagnostics: list[str] = Field(
        default_factory=list,
        description="Follow-up diagnostic tests suggested based on visual findings",
    )
    image_quality_note: str = Field(
        default="",
        description="Notes on image quality issues that may affect analysis accuracy",
    )

    # Phase 191B additions (non-breaking — defaults preserve Phase 101 callers).
    frames_analyzed: int = Field(
        default=0,
        ge=0,
        description="Number of video frames analyzed in this batch (Phase 191B; 0 for non-video Phase 101 paths)",
    )
    model_used: str = Field(
        default="",
        description="Claude model that produced these findings (e.g., 'claude-sonnet-4-6')",
    )
    cost_estimate_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="USD cost estimate for the analysis call (Phase 191B; 0.0 for non-API mock paths)",
    )

    @property
    def finding_count(self) -> int:
        """Total number of findings."""
        return len(self.findings)

    @property
    def critical_findings(self) -> list[VisualFinding]:
        """Findings with CRITICAL severity."""
        return [f for f in self.findings if f.severity == Severity.CRITICAL]

    @property
    def high_severity_findings(self) -> list[VisualFinding]:
        """Findings with HIGH or CRITICAL severity."""
        return [
            f for f in self.findings
            if f.severity in (Severity.CRITICAL, Severity.HIGH)
        ]

    @property
    def average_confidence(self) -> float:
        """Average confidence across all findings."""
        if not self.findings:
            return 0.0
        return sum(f.confidence for f in self.findings) / len(self.findings)

    def findings_by_type(self, finding_type: FindingType) -> list[VisualFinding]:
        """Return all findings of a specific type."""
        return [f for f in self.findings if f.finding_type == finding_type]


# --- Smoke Color Diagnostic Guide ---

SMOKE_COLOR_GUIDE: dict[str, dict] = {
    "white": {
        "cause": "Coolant entering combustion chamber",
        "common_sources": [
            "Blown head gasket",
            "Cracked cylinder head",
            "Cracked engine block",
            "Warped head from overheating",
        ],
        "severity": Severity.HIGH,
        "notes": "Thin white vapor on cold starts is normal (condensation). "
                 "Persistent thick white smoke indicates coolant burn.",
    },
    "blue": {
        "cause": "Oil entering combustion chamber",
        "common_sources": [
            "Worn piston rings",
            "Worn valve seals",
            "Worn valve guides",
            "Overfilled oil level",
            "PCV system malfunction (if equipped)",
        ],
        "severity": Severity.HIGH,
        "notes": "Blue smoke on startup that clears = valve seals. "
                 "Blue smoke under acceleration = piston rings.",
    },
    "black": {
        "cause": "Running rich — excess unburned fuel",
        "common_sources": [
            "Dirty or clogged air filter",
            "Carburetor float stuck / needle valve worn",
            "Faulty fuel injector(s) (stuck open)",
            "Bad O2 sensor / fuel trim issue (FI bikes)",
            "Choke stuck on",
        ],
        "severity": Severity.MEDIUM,
        "notes": "Often accompanied by strong fuel smell, fouled spark plugs, "
                 "and poor fuel economy.",
    },
    "gray": {
        "cause": "Could be oil or rich fuel mixture",
        "common_sources": [
            "Mild valve seal seepage",
            "Slightly rich air/fuel mixture",
            "Automatic transmission fluid (if applicable via breather)",
        ],
        "severity": Severity.MEDIUM,
        "notes": "Gray smoke is ambiguous — correlate with other symptoms "
                 "(oil consumption, fuel smell, plug condition).",
    },
}


# --- Fluid Color Diagnostic Guide ---

FLUID_COLOR_GUIDE: dict[str, dict] = {
    "green": {
        "fluid": "Coolant (ethylene glycol, most common)",
        "severity": Severity.HIGH,
        "action": "Check radiator, hoses, water pump, head gasket",
    },
    "orange": {
        "fluid": "Coolant (Dex-Cool / extended life) or rusty coolant",
        "severity": Severity.HIGH,
        "action": "Check cooling system; rusty coolant indicates corrosion",
    },
    "red": {
        "fluid": "Transmission fluid or power steering fluid",
        "severity": Severity.HIGH,
        "action": "Check transmission seals, cooler lines",
    },
    "dark_brown": {
        "fluid": "Old engine oil or brake fluid",
        "severity": Severity.MEDIUM,
        "action": "Check oil pan gasket, valve cover gasket, brake lines/calipers",
    },
    "light_brown": {
        "fluid": "Fresh engine oil or gear oil",
        "severity": Severity.MEDIUM,
        "action": "Check gaskets, seals, drain plugs",
    },
    "clear": {
        "fluid": "Water (condensation) or brake fluid (fresh DOT)",
        "severity": Severity.LOW,
        "action": "Normal condensation from A/C or exhaust. If oily, check brake system.",
    },
}


# --- Vision Analysis Prompt ---

VISION_ANALYSIS_PROMPT = """You are an expert motorcycle diagnostic technician analyzing images
for visual symptoms. Examine the image carefully and report findings in these categories:

1. SMOKE: Color (white/blue/black/gray), density, source location
   - White = coolant burn (head gasket, cracked head)
   - Blue = oil burn (rings, valve seals, guides)
   - Black = rich fuel (dirty filter, carb/injector, choke)

2. FLUID LEAKS: Color, location, volume estimate
   - Green/orange = coolant (radiator, hoses, water pump)
   - Brown/black = oil (gaskets, seals)
   - Red = transmission/hydraulic fluid
   - Clear = condensation or brake fluid

3. PHYSICAL DAMAGE: Dents, cracks, broken parts, bent components

4. GAUGE READINGS: Temperature, oil pressure, RPM, warning lights
   - Flag any readings outside normal operating range

5. WEAR INDICATORS:
   - Chain: stretch, rust, missing O-rings, sprocket tooth wear
   - Tires: tread depth, cupping, flat spots, cracking, uneven wear
   - Brake pads: thickness, glazing, uneven wear
   - Controls: lever condition, cable fraying, grip wear

6. CORROSION: Rust, pitting, electrolysis, oxidation locations

For each finding, provide:
- Finding type (smoke/leak/damage/gauge_reading/wear/corrosion/missing_part/modification)
- Description of what you see
- Confidence (0.0-1.0)
- Location in the image
- Severity (critical/high/medium/low/info)

Return findings as structured JSON matching the VisualAnalysisResult schema."""


class VehicleContext(BaseModel):
    """Vehicle information provided alongside the image for analysis context."""
    make: str = Field(default="", description="Manufacturer (e.g., 'Honda')")
    model: str = Field(default="", description="Model name (e.g., 'CBR600RR')")
    year: Optional[int] = Field(default=None, description="Model year")
    mileage: Optional[int] = Field(default=None, description="Current mileage")
    reported_symptoms: list[str] = Field(
        default_factory=list,
        description="Symptoms the mechanic has already reported",
    )
    identity_note: str = Field(
        default="",
        description=(
            "Phase 244C: how the machine's name was read, when it differed "
            "from what was typed. Surfaced to the model rather than applied "
            "silently — the technician wrote something, and swapping it "
            "without saying so would be a different kind of guessing."
        ),
    )
    notes: str = Field(
        default="",
        description=(
            "Free-text notes recorded on the session by the technician. "
            "Phase 244B: sessions carry a notes field that no analysis had "
            "ever read, and in the reported failure case it was the only "
            "place the actual complaint ('Leaking oil on left side') was "
            "written down."
        ),
    )

    def to_context_string(self) -> str:
        """Format vehicle context as a text block for prompt injection."""
        parts = []
        if self.make or self.model:
            parts.append(f"Vehicle: {self.year or '?'} {self.make} {self.model}")
        if self.mileage is not None:
            parts.append(f"Mileage: {self.mileage:,}")
        if self.reported_symptoms:
            parts.append(f"Reported symptoms: {', '.join(self.reported_symptoms)}")
        if self.identity_note.strip():
            parts.append(self.identity_note.strip())
        if self.notes.strip():
            parts.append(f"Technician notes on this session: {self.notes.strip()}")
        return "\n".join(parts) if parts else "No vehicle context provided."


# ---------------------------------------------------------------------------
# Phase 244B — guidance mode
# ---------------------------------------------------------------------------
class Grounding(str, Enum):
    """What a guidance candidate rests on.

    The corpus has carried per-entry provenance since Track K. This is the same
    discipline applied to generated reasoning: a technician reading "check the
    countershaft seal first" must be able to tell whether that came from a
    corpus entry for THEIR machine, from a cross-platform entry, or from
    general mechanical reasoning with nothing behind it.
    """

    MACHINE_SPECIFIC = "machine_specific"   # a corpus entry for this make/model/year
    CROSS_PLATFORM = "cross_platform"       # a corpus entry that applies generally
    GENERAL_REASONING = "general_reasoning"  # no corpus support — say so
    NOT_ESTABLISHED = "not_established"      # nothing found; the honest answer


class GuidanceCandidate(BaseModel):
    """One candidate origin, with how to tell it from the others.

    Deliberately NOT a diagnosis. There is no root-cause field, no repair
    steps, no parts and no cost — a guidance answer that carries those has
    stopped guiding and started concluding, which is the drift this phase
    exists to fix.
    """

    candidate: str = Field(..., description="The candidate origin or explanation")
    why_plausible: str = Field(..., description="Why this fits what was observed and asked")
    how_to_discriminate: str = Field(
        ...,
        description=(
            "The observation or check that distinguishes this candidate from "
            "the others — the actual value of a guidance answer"
        ),
    )
    grounding: Grounding = Field(..., description="What this candidate rests on")
    grounding_detail: str = Field(
        default="",
        description=(
            "For machine_specific or cross_platform, the corpus entry title. "
            "For general_reasoning, say plainly that no corpus entry supports it."
        ),
    )
    check_order_rationale: str = Field(
        default="",
        description="Why check this before or after the others — cost, access, or elimination value",
    )


class GuidanceResponse(BaseModel):
    """An answer to the question the technician actually asked.

    Note what is absent by design: no `diagnosis`, no `severity` roll-up, no
    repair steps. The technician remains the diagnostician.
    """

    question_understood_as: str = Field(
        ...,
        description=(
            "Restate the question being answered. If the question could not be "
            "understood, say so here rather than answering a different one."
        ),
    )
    answers_the_question: bool = Field(
        ...,
        description=(
            "False if the available evidence does not let you address what was "
            "asked. False with an honest gap beats a confident sweep."
        ),
    )
    candidates: list[GuidanceCandidate] = Field(
        default_factory=list,
        description="Candidate origins, ordered by what to check first",
    )
    what_would_narrow_it: list[str] = Field(
        default_factory=list,
        description="Observations or tests that would most reduce the candidate set",
    )
    not_established: str = Field(
        default="",
        description=(
            "What could not be established for this machine. A real answer, not "
            "a failure — state it rather than inventing a candidate to fill the list."
        ),
    )
    observation_basis: str = Field(
        default="",
        description="What in the supplied media this answer actually rests on",
    )


GUIDANCE_PROMPT = """You are helping a motorcycle technician who is standing at \
the machine and has asked you a specific question. They are the diagnostician. \
Your job is to guide their search, not to reach a verdict for them.

ANSWER THE QUESTION THAT WAS ASKED. This is the whole task. A complete survey \
of everything visible is a failure, however accurate it is — the technician \
did not ask for it, and volume buries the answer. If they ask where a leak is \
most likely coming from, give candidate ORIGINS and how to tell them apart; do \
not identify the fluid unless that is what distinguishes the candidates, and do \
not list unrelated findings.

DO NOT DIAGNOSE. Do not name a root cause. Do not give repair steps, parts or \
costs. If you can only offer a verdict, you have misunderstood the task.

GROUND EVERY CANDIDATE. For each one set `grounding`:
  machine_specific   — a supplied corpus entry covers this make/model/year
  cross_platform     — a supplied corpus entry applies generally
  general_reasoning  — no corpus entry supports it; say so in grounding_detail
  not_established    — nothing supports it
Never present general reasoning as though it were documented. A short honest \
answer beats a long confident one.

SAY WHAT YOU CANNOT ESTABLISH. If the media does not show enough to address the \
question, set answers_the_question false and put the gap in not_established. \
Do not fill the candidate list to look thorough.

THE DISCRIMINATOR IS THE PRODUCT. For each candidate, the most valuable field \
is how_to_discriminate — the observation that separates it from its neighbours. \
Order candidates by what to check first, and say why in check_order_rationale: \
cheapest, most accessible, or most eliminating.

Report through the provide_guidance tool."""
