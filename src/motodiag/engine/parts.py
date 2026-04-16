"""Parts + tools recommendation engine — suggests parts, part numbers, and tools for repairs.

Given a diagnosis, vehicle make/model/year, recommends specific parts (OEM, aftermarket, used)
with cross-references, price ranges, and the tools needed to perform the repair. Uses Claude
for intelligent recommendations grounded in real motorcycle mechanic knowledge.
"""

import json
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from motodiag.engine.client import DiagnosticClient
from motodiag.engine.models import TokenUsage


class PartSource(str, Enum):
    """Where a part comes from."""
    OEM = "oem"                # Original equipment manufacturer
    AFTERMARKET = "aftermarket"  # Third-party replacement (EBC, NGK, DID, etc.)
    USED = "used"              # Salvage / second-hand
    GENERIC = "generic"        # Universal / non-brand-specific


class PartRecommendation(BaseModel):
    """A single recommended part for a repair."""
    part_name: str = Field(..., description="Descriptive name (e.g., 'Stator assembly')")
    part_number: Optional[str] = Field(None, description="OEM or aftermarket part number when known")
    brand: str = Field(..., description="Manufacturer or brand (e.g., 'Rick's Motorsport Electrics')")
    price_range_low: float = Field(..., ge=0.0, description="Low end of price range in USD")
    price_range_high: float = Field(..., ge=0.0, description="High end of price range in USD")
    source: PartSource = Field(..., description="OEM, aftermarket, used, or generic")
    notes: Optional[str] = Field(None, description="Additional guidance (fitment notes, version differences, etc.)")
    cross_references: list[str] = Field(
        default_factory=list,
        description="Equivalent parts from other brands (e.g., 'Denso IU27 = NGK CR9EIA-9')",
    )


class ToolRecommendation(BaseModel):
    """A tool needed for the repair."""
    tool_name: str = Field(..., description="Tool name (e.g., 'Torque wrench')")
    specification: str = Field(..., description="Size/spec (e.g., '10mm socket, 3/8 drive')")
    price_range: str = Field(..., description="Approximate price range (e.g., '$15-25')")
    essential: bool = Field(..., description="True if the repair cannot be done without this tool")
    alternative: Optional[str] = Field(
        None,
        description="What to use if you don't have this tool (e.g., 'adjustable wrench in a pinch')",
    )


PARTS_PROMPT = """You are an expert motorcycle parts specialist and tool advisor.

Given a diagnosis and vehicle information, recommend specific parts and tools needed for the repair.

## Parts Requirements
- Include specific part numbers where available (OEM and aftermarket)
- Provide OEM vs aftermarket guidance — when aftermarket is equal or better, say so
- Recommend trusted brands: NGK/Denso (spark plugs, O2 sensors), DID/RK/EK (chains),
  EBC (brake pads/rotors), All Balls Racing (bearings, seals, linkage kits),
  Rick's Motorsport Electrics (stators, regulators), Shindy (cables),
  K&L Supply (carb rebuild kits), Motion Pro (tools, cables),
  Barnett (clutch plates, cables), Vesrah (gaskets), Cometic (head gaskets),
  Moose Racing (dual-sport parts), Trail Tech (electronics)
- Include price ranges in USD (low to high estimate)
- List cross-references: equivalent parts from other brands that fit the same application
- Mark source as oem, aftermarket, used, or generic
- For each part, note any fitment caveats (year range differences, sub-model variations)

## Tool Requirements
- List every tool needed, from common (socket set) to specialized (flywheel puller)
- Include exact specifications: socket sizes, drive sizes, torque specs
- Mark each tool as essential (repair impossible without it) or nice-to-have
- For specialty tools, suggest alternatives or workarounds when possible
- Include consumables as tools when applicable (threadlocker, dielectric grease, torque stripe)

## Response Format
Return valid JSON with this structure:
{
  "parts": [
    {
      "part_name": "...",
      "part_number": "OEM-12345 or null",
      "brand": "...",
      "price_range_low": 25.00,
      "price_range_high": 45.00,
      "source": "aftermarket",
      "notes": "Fits 2003-2006 only; 2007+ uses revised connector",
      "cross_references": ["Brand2 P/N ABC-123", "Brand3 P/N DEF-456"]
    }
  ],
  "tools": [
    {
      "tool_name": "...",
      "specification": "...",
      "price_range": "$15-25",
      "essential": true,
      "alternative": "... or null"
    }
  ]
}

Return ONLY the JSON object. No markdown fences, no commentary outside the JSON."""


class PartsRecommender:
    """Recommends parts and tools for motorcycle repairs using Claude.

    Takes a diagnosis string plus vehicle identification and returns
    structured part and tool recommendations with pricing and cross-references.
    """

    def __init__(self, client: DiagnosticClient) -> None:
        """Initialize with a DiagnosticClient for API access.

        Args:
            client: Configured DiagnosticClient instance.
        """
        self.client = client

    def recommend(
        self,
        diagnosis: str,
        make: str,
        model: str,
        year: int,
    ) -> tuple[list[PartRecommendation], list[ToolRecommendation], TokenUsage]:
        """Get parts and tools recommendations for a diagnosis.

        Args:
            diagnosis: The diagnostic finding (e.g., "Stator failure — no AC output").
            make: Vehicle manufacturer (e.g., "Honda").
            model: Vehicle model (e.g., "CBR600RR").
            year: Model year.

        Returns:
            Tuple of (part_recommendations, tool_recommendations, token_usage).
        """
        prompt = (
            f"Diagnosis: {diagnosis}\n"
            f"Vehicle: {year} {make} {model}\n\n"
            f"Recommend parts and tools needed for this repair."
        )

        response_text, usage = self.client.ask(
            prompt=prompt,
            system=PARTS_PROMPT,
        )

        parts, tools = self._parse_recommendations(response_text)
        return parts, tools, usage

    def _parse_recommendations(
        self, response_text: str
    ) -> tuple[list[PartRecommendation], list[ToolRecommendation]]:
        """Parse JSON response into part and tool recommendation lists.

        Attempts JSON extraction with graceful fallback on parse failure.

        Args:
            response_text: Raw text response from Claude.

        Returns:
            Tuple of (part_list, tool_list). Returns empty lists on parse failure.
        """
        try:
            text = response_text.strip()
            # Handle markdown code fences
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)

            parts = []
            for p in data.get("parts", []):
                try:
                    parts.append(PartRecommendation(**p))
                except (ValueError, TypeError):
                    continue

            tools = []
            for t in data.get("tools", []):
                try:
                    tools.append(ToolRecommendation(**t))
                except (ValueError, TypeError):
                    continue

            return parts, tools

        except (json.JSONDecodeError, KeyError, IndexError, AttributeError):
            return [], []
