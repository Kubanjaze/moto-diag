"""Repair procedure generator — produces step-by-step mechanic-friendly repair instructions.

Takes a diagnosis string (from the AI engine or manual input) along with vehicle context,
sends it to Claude, and returns a structured RepairProcedure with numbered steps, tools,
parts, time estimates, skill level, and safety warnings.
"""

import json
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from motodiag.engine.client import DiagnosticClient
from motodiag.engine.models import TokenUsage


class SkillLevel(str, Enum):
    """Mechanic skill level required for a repair."""
    BEGINNER = "beginner"          # Oil change, air filter, basic fluid top-off
    INTERMEDIATE = "intermediate"  # Electrical diagnosis, brake service, suspension
    ADVANCED = "advanced"          # Engine internals, transmission, frame/chassis work


class RepairStep(BaseModel):
    """A single numbered step in a repair procedure."""
    step_number: int = Field(..., ge=1, description="Step sequence number")
    instruction: str = Field(..., description="Detailed mechanic-friendly instruction text")
    tip: Optional[str] = Field(None, description="Pro tip — time saver or technique refinement")
    warning: Optional[str] = Field(None, description="Safety or damage warning for this step")


class RepairProcedure(BaseModel):
    """Complete repair procedure with steps, tooling, parts, and metadata."""
    title: str = Field(..., description="Short title for the repair (e.g., 'Stator Replacement')")
    description: str = Field(..., description="Brief summary of what this procedure addresses")
    steps: list[RepairStep] = Field(default_factory=list, description="Ordered repair steps")
    tools_needed: list[str] = Field(default_factory=list, description="Tools required for this repair")
    parts_needed: list[str] = Field(default_factory=list, description="Parts required for this repair")
    estimated_hours: float = Field(default=0.0, ge=0.0, description="Estimated labor hours")
    skill_level: SkillLevel = Field(default=SkillLevel.INTERMEDIATE, description="Required skill level")
    safety_warnings: list[str] = Field(default_factory=list, description="Top-level safety warnings")
    notes: Optional[str] = Field(None, description="Additional notes or alternative approaches")


# Keywords that map to skill levels — checked in order (advanced first)
_ADVANCED_KEYWORDS = [
    "engine rebuild", "engine internal", "transmission rebuild", "crankshaft",
    "cylinder bore", "valve job", "head gasket", "bottom end", "top end rebuild",
    "connecting rod", "piston ring", "camshaft replacement", "crankcase",
    "frame repair", "frame weld", "steering head bearing press",
]

_INTERMEDIATE_KEYWORDS = [
    "electrical", "wiring", "stator", "regulator", "rectifier",
    "brake caliper rebuild", "brake master cylinder", "suspension",
    "fork seal", "fork rebuild", "shock", "carburetor rebuild",
    "clutch replacement", "valve adjustment", "valve clearance",
    "timing chain", "cam chain tensioner", "fuel injection",
    "throttle body", "ignition", "cooling system", "radiator",
]

_BEGINNER_KEYWORDS = [
    "oil change", "fluid change", "coolant flush", "air filter",
    "spark plug", "battery", "chain lube", "chain adjustment",
    "tire pressure", "brake pad", "brake fluid flush", "light bulb",
    "fuse", "cable lube", "cable adjustment",
]


def assess_skill_level(repair_description: str) -> SkillLevel:
    """Assess the skill level required for a repair based on keyword matching.

    Checks advanced keywords first, then intermediate, then beginner.
    Defaults to intermediate if no keywords match.

    Args:
        repair_description: Free-text description of the repair.

    Returns:
        SkillLevel enum value.
    """
    lower = repair_description.lower()

    for keyword in _ADVANCED_KEYWORDS:
        if keyword in lower:
            return SkillLevel.ADVANCED

    for keyword in _INTERMEDIATE_KEYWORDS:
        if keyword in lower:
            return SkillLevel.INTERMEDIATE

    for keyword in _BEGINNER_KEYWORDS:
        if keyword in lower:
            return SkillLevel.BEGINNER

    return SkillLevel.INTERMEDIATE


REPAIR_PROMPT = """You are MotoDiag Repair Procedure Generator — an expert motorcycle mechanic AI that produces clear, step-by-step repair instructions for professional and DIY mechanics.

Given a diagnosis and vehicle context, generate a complete repair procedure as JSON.

Requirements:
1. **Steps must be numbered and mechanic-friendly** — write as if explaining to a competent technician who hasn't done this specific job before.
2. **Include torque specs** where applicable (e.g., "Torque drain plug to 14-16 ft-lbs").
3. **Safety warnings** are MANDATORY for:
   - Fuel system work (fire risk, fuel vapor, pressure relief)
   - Brake system work (verify function before riding)
   - Electrical work (disconnect battery first, capacitor discharge)
   - Lifting/support (jack points, center stand, rear stand)
   - Hot engine/exhaust components
   - Suspension under spring load
4. **Tools list** must be specific (e.g., "10mm socket" not just "socket set").
5. **Parts list** should include quantities and note OEM vs aftermarket options where relevant.
6. **Estimated hours** should reflect a competent mechanic, not a beginner or expert speed-run.
7. **Skill level**: beginner (fluid changes, filters), intermediate (electrical, brakes, suspension), advanced (engine internals, transmission, frame).
8. **Alternative approaches**: Note if there's a simpler DIY path vs a proper shop method.
9. **Pro tips**: Include time-saving tricks, common mistakes to avoid, and "while you're in there" recommendations.

Respond with ONLY valid JSON matching this schema:
{
  "title": "Short repair title",
  "description": "What this procedure fixes and why",
  "steps": [
    {
      "step_number": 1,
      "instruction": "Detailed step text",
      "tip": "Optional pro tip or null",
      "warning": "Optional safety warning or null"
    }
  ],
  "tools_needed": ["specific tool 1", "specific tool 2"],
  "parts_needed": ["part with quantity"],
  "estimated_hours": 1.5,
  "skill_level": "beginner|intermediate|advanced",
  "safety_warnings": ["Top-level safety warning"],
  "notes": "Optional additional notes or null"
}"""


class RepairProcedureGenerator:
    """Generates structured repair procedures from diagnoses using Claude.

    Takes a diagnosis (from the AI diagnostic engine or manual input),
    vehicle context, and produces a step-by-step repair procedure with
    tools, parts, time estimates, and safety warnings.
    """

    def __init__(self, client: DiagnosticClient):
        """Initialize with a DiagnosticClient for API access.

        Args:
            client: Configured DiagnosticClient instance.
        """
        self.client = client

    def generate(
        self,
        diagnosis: str,
        make: str,
        model: str,
        year: int,
    ) -> tuple[RepairProcedure, TokenUsage]:
        """Generate a repair procedure for a given diagnosis and vehicle.

        Builds a prompt combining the diagnosis with vehicle context,
        sends it to Claude, and parses the structured JSON response.

        Args:
            diagnosis: The diagnosed problem (e.g., "Stator failure — not charging").
            make: Vehicle manufacturer (e.g., "Honda").
            model: Vehicle model (e.g., "CBR600RR").
            year: Model year.

        Returns:
            Tuple of (RepairProcedure, TokenUsage).
        """
        user_prompt = (
            f"Generate a complete repair procedure for the following:\n\n"
            f"Vehicle: {year} {make} {model}\n"
            f"Diagnosis: {diagnosis}\n\n"
            f"Provide the full step-by-step procedure as JSON."
        )

        response_text, usage = self.client.ask(
            prompt=user_prompt,
            system=REPAIR_PROMPT,
        )

        procedure = self._parse_response(response_text, diagnosis, make, model, year)
        return procedure, usage

    def _parse_response(
        self,
        response_text: str,
        diagnosis: str,
        make: str,
        model: str,
        year: int,
    ) -> RepairProcedure:
        """Parse Claude's JSON response into a RepairProcedure.

        Falls back to a minimal procedure if JSON parsing fails.
        """
        try:
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)
            return RepairProcedure(**data)
        except (json.JSONDecodeError, KeyError, ValueError, IndexError):
            # Fallback: wrap the raw text in a minimal procedure
            return RepairProcedure(
                title=f"Repair: {diagnosis[:80]}",
                description=f"Repair procedure for {year} {make} {model} — {diagnosis}",
                steps=[
                    RepairStep(
                        step_number=1,
                        instruction=response_text[:1000] if response_text else "Review diagnosis and consult service manual.",
                        warning="Procedure could not be parsed as structured JSON — review raw text carefully.",
                    )
                ],
                skill_level=assess_skill_level(diagnosis),
                safety_warnings=["Procedure generated from unstructured response — verify all steps before proceeding."],
                notes="AI response was not in structured JSON format. Raw text preserved in step 1.",
            )
