"""Text-only image-DESCRIPTION analyzer (SUPERSEDED, tests only).

``VisualAnalyzer`` here takes an ``image_description: str`` (a text description
of what an image shows) and calls ``DiagnosticClient.ask()`` with a text
completion — it never sees real image bytes. It is SUPERSEDED by the real
image-bytes pipeline:

    motodiag.media.vision_analysis_pipeline.VisionAnalyzer.analyze_video_frames
        -> DiagnosticClient.ask_with_images(...)

which base64-encodes actual ffmpeg-extracted frames and returns structured
tool-use output. This text-sim analyzer is NOT used by any production path
(audit-verified); it is retained ONLY for the Phase 101 test suite.

Shared Vision data types live in ``motodiag.media.vision_types``; this module
imports exactly what the analyzer body needs from there.
"""

from __future__ import annotations

from typing import Optional

from motodiag.media.vision_types import (
    VISION_ANALYSIS_PROMPT,
    VehicleContext,
    VisualAnalysisResult,
    SMOKE_COLOR_GUIDE,
    FLUID_COLOR_GUIDE,
    Severity,
)


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
