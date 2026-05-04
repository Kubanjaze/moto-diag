"""Visual symptom analysis using Claude Vision for motorcycle diagnostics.

Phase 101: Analyzes motorcycle images/frames for visual diagnostic symptoms —
smoke color and density, fluid leaks (location + color), physical damage,
gauge readings, wear indicators (chain, tires, brake pads). Uses Claude Vision
API (mocked in tests) with a motorcycle-specific system prompt.

Designed to process frames from VideoFrameExtractor (Phase 100) or standalone
images captured by the mechanic's phone.
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

    def to_context_string(self) -> str:
        """Format vehicle context as a text block for prompt injection."""
        parts = []
        if self.make or self.model:
            parts.append(f"Vehicle: {self.year or '?'} {self.make} {self.model}")
        if self.mileage is not None:
            parts.append(f"Mileage: {self.mileage:,}")
        if self.reported_symptoms:
            parts.append(f"Reported symptoms: {', '.join(self.reported_symptoms)}")
        return "\n".join(parts) if parts else "No vehicle context provided."


class VisualAnalyzer:
    """Analyzes motorcycle images for visual diagnostic symptoms using Claude Vision.

    In production, calls Claude Vision API with the motorcycle-specific prompt.
    In tests, the API call is mocked and the analyzer processes the mock response.

    Usage:
        analyzer = VisualAnalyzer(client=mock_client)
        result = analyzer.analyze_image(
            image_description="Photo of motorcycle exhaust with blue smoke",
            vehicle_context=VehicleContext(make="Honda", model="CBR600RR", year=2005),
        )
    """

    def __init__(
        self,
        client: Optional[object] = None,
        model: str = "haiku",
        max_tokens: int = 2048,
    ):
        """Initialize the visual analyzer.

        Args:
            client: DiagnosticClient instance (or mock). If None, creates one lazily.
            model: Claude model to use ("haiku" or "sonnet").
            max_tokens: Max response tokens for vision analysis.
        """
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def _get_client(self):
        """Lazy-initialize the DiagnosticClient if not provided."""
        if self._client is None:
            from motodiag.engine.client import DiagnosticClient
            self._client = DiagnosticClient(model=self._model)
        return self._client

    def analyze_image(
        self,
        image_description: str,
        vehicle_context: Optional[VehicleContext] = None,
    ) -> VisualAnalysisResult:
        """Analyze a motorcycle image for visual diagnostic symptoms.

        In the simulated pipeline, image_description is a text description
        of the image content (e.g., "Photo showing blue smoke from exhaust").
        In production, this would accept actual image data (base64 or URL).

        Args:
            image_description: Text description of the image content.
            vehicle_context: Optional vehicle information for context.

        Returns:
            VisualAnalysisResult with findings and recommendations.
        """
        if not image_description or not image_description.strip():
            return VisualAnalysisResult(
                findings=[],
                overall_assessment="No image description provided — cannot analyze.",
                suggested_diagnostics=[],
                image_quality_note="Empty or blank image description received.",
            )

        prompt = self._build_analysis_prompt(image_description, vehicle_context)
        client = self._get_client()

        # Call the AI — in tests, client.ask() is mocked
        response_text, token_usage = client.ask(
            prompt=prompt,
            system=VISION_ANALYSIS_PROMPT,
            model=self._model,
            max_tokens=self._max_tokens,
        )

        result = self._parse_response(response_text)
        return result

    def analyze_smoke(self, smoke_color: str) -> dict:
        """Look up diagnostic info for a specific smoke color.

        Provides immediate guidance without an API call — uses the built-in
        SMOKE_COLOR_GUIDE.

        Args:
            smoke_color: Color of the smoke (white, blue, black, gray).

        Returns:
            Dict with cause, common_sources, severity, and notes.
            Returns unknown entry if color is not in the guide.
        """
        color_lower = smoke_color.lower().strip()
        if color_lower in SMOKE_COLOR_GUIDE:
            return {
                "color": color_lower,
                **SMOKE_COLOR_GUIDE[color_lower],
            }
        return {
            "color": color_lower,
            "cause": "Unknown smoke color",
            "common_sources": [],
            "severity": Severity.MEDIUM,
            "notes": f"Smoke color '{color_lower}' not in diagnostic guide. "
                     f"Known colors: {', '.join(SMOKE_COLOR_GUIDE.keys())}.",
        }

    def analyze_fluid_leak(self, fluid_color: str) -> dict:
        """Look up diagnostic info for a fluid leak by color.

        Args:
            fluid_color: Color of the leaked fluid.

        Returns:
            Dict with fluid type, severity, and recommended action.
        """
        color_lower = fluid_color.lower().strip()
        if color_lower in FLUID_COLOR_GUIDE:
            return {
                "color": color_lower,
                **FLUID_COLOR_GUIDE[color_lower],
            }
        return {
            "color": color_lower,
            "fluid": "Unknown fluid",
            "severity": Severity.MEDIUM,
            "action": f"Fluid color '{color_lower}' not in guide. "
                      f"Collect sample for analysis.",
        }

    def _build_analysis_prompt(
        self,
        image_description: str,
        vehicle_context: Optional[VehicleContext] = None,
    ) -> str:
        """Build the full analysis prompt from image description and vehicle context."""
        parts = []
        if vehicle_context:
            ctx = vehicle_context.to_context_string()
            parts.append(f"VEHICLE CONTEXT:\n{ctx}\n")

        parts.append(f"IMAGE DESCRIPTION:\n{image_description}\n")
        parts.append(
            "Analyze this image for motorcycle diagnostic symptoms. "
            "Return structured findings as JSON matching the VisualAnalysisResult schema."
        )
        return "\n".join(parts)

    def _parse_response(self, response_text: str) -> VisualAnalysisResult:
        """Parse AI response text into a VisualAnalysisResult.

        Attempts JSON parsing first, falls back to text-based extraction.
        """
        import json

        text = response_text.strip()

        # Strip markdown code fences if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)
            return VisualAnalysisResult(**data)
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            # Fallback: return the raw text as the overall assessment
            return VisualAnalysisResult(
                findings=[],
                overall_assessment=response_text[:1000],
                suggested_diagnostics=["Review raw AI response for details"],
                image_quality_note="Response could not be parsed as structured JSON.",
            )
