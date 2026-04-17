"""Phase 101 — Visual symptom analysis tests.

Tests VisualFinding, VisualAnalysisResult, VehicleContext, VisualAnalyzer
(analyze_image, analyze_smoke, analyze_fluid_leak), SMOKE_COLOR_GUIDE,
FLUID_COLOR_GUIDE, prompt building, and response parsing.

All API calls are fully mocked — no live Claude Vision calls.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from motodiag.media.vision_analysis import (
    FindingType,
    Severity,
    VisualFinding,
    VisualAnalysisResult,
    VehicleContext,
    VisualAnalyzer,
    SMOKE_COLOR_GUIDE,
    FLUID_COLOR_GUIDE,
    VISION_ANALYSIS_PROMPT,
)
from motodiag.engine.models import TokenUsage


# --- Helpers ---


def _make_mock_client(response_text: str = "{}") -> MagicMock:
    """Create a mock DiagnosticClient that returns the given response text."""
    client = MagicMock()
    client.ask.return_value = (
        response_text,
        TokenUsage(input_tokens=100, output_tokens=50, model="haiku", cost_estimate=0.001),
    )
    return client


def _make_json_response(**kwargs) -> str:
    """Build a JSON response string for VisualAnalysisResult."""
    data = {
        "findings": kwargs.get("findings", []),
        "overall_assessment": kwargs.get("overall_assessment", "Test assessment"),
        "suggested_diagnostics": kwargs.get("suggested_diagnostics", []),
        "image_quality_note": kwargs.get("image_quality_note", ""),
    }
    return json.dumps(data)


# --- VisualFinding ---


class TestVisualFinding:
    def test_basic_finding(self):
        finding = VisualFinding(
            finding_type=FindingType.SMOKE,
            description="Blue smoke from exhaust",
            confidence=0.85,
            location_in_image="lower right",
            severity=Severity.HIGH,
        )
        assert finding.finding_type == FindingType.SMOKE
        assert finding.confidence == 0.85
        assert finding.severity == Severity.HIGH

    def test_finding_defaults(self):
        finding = VisualFinding(
            finding_type=FindingType.WEAR,
            description="Worn chain",
            confidence=0.7,
        )
        assert finding.location_in_image == ""
        assert finding.severity == Severity.MEDIUM

    def test_all_finding_types(self):
        for ft in FindingType:
            finding = VisualFinding(
                finding_type=ft,
                description=f"Test {ft.value}",
                confidence=0.5,
            )
            assert finding.finding_type == ft


# --- VisualAnalysisResult ---


class TestVisualAnalysisResult:
    def test_empty_result(self):
        result = VisualAnalysisResult()
        assert result.finding_count == 0
        assert result.critical_findings == []
        assert result.average_confidence == 0.0

    def test_finding_count(self):
        result = VisualAnalysisResult(
            findings=[
                VisualFinding(finding_type=FindingType.SMOKE, description="smoke", confidence=0.8),
                VisualFinding(finding_type=FindingType.LEAK, description="leak", confidence=0.6),
            ]
        )
        assert result.finding_count == 2

    def test_critical_findings_filter(self):
        result = VisualAnalysisResult(
            findings=[
                VisualFinding(finding_type=FindingType.DAMAGE, description="cracked frame", confidence=0.9, severity=Severity.CRITICAL),
                VisualFinding(finding_type=FindingType.WEAR, description="worn tire", confidence=0.7, severity=Severity.LOW),
            ]
        )
        assert len(result.critical_findings) == 1
        assert result.critical_findings[0].description == "cracked frame"

    def test_high_severity_filter(self):
        result = VisualAnalysisResult(
            findings=[
                VisualFinding(finding_type=FindingType.DAMAGE, description="a", confidence=0.9, severity=Severity.CRITICAL),
                VisualFinding(finding_type=FindingType.SMOKE, description="b", confidence=0.8, severity=Severity.HIGH),
                VisualFinding(finding_type=FindingType.WEAR, description="c", confidence=0.5, severity=Severity.LOW),
            ]
        )
        assert len(result.high_severity_findings) == 2

    def test_average_confidence(self):
        result = VisualAnalysisResult(
            findings=[
                VisualFinding(finding_type=FindingType.SMOKE, description="a", confidence=0.6),
                VisualFinding(finding_type=FindingType.LEAK, description="b", confidence=0.8),
            ]
        )
        assert abs(result.average_confidence - 0.7) < 0.001

    def test_findings_by_type(self):
        result = VisualAnalysisResult(
            findings=[
                VisualFinding(finding_type=FindingType.SMOKE, description="smoke1", confidence=0.8),
                VisualFinding(finding_type=FindingType.LEAK, description="leak1", confidence=0.6),
                VisualFinding(finding_type=FindingType.SMOKE, description="smoke2", confidence=0.7),
            ]
        )
        smoke_findings = result.findings_by_type(FindingType.SMOKE)
        assert len(smoke_findings) == 2
        assert all(f.finding_type == FindingType.SMOKE for f in smoke_findings)


# --- VehicleContext ---


class TestVehicleContext:
    def test_full_context(self):
        ctx = VehicleContext(
            make="Honda",
            model="CBR600RR",
            year=2005,
            mileage=45000,
            reported_symptoms=["blue smoke", "oil consumption"],
        )
        text = ctx.to_context_string()
        assert "Honda" in text
        assert "CBR600RR" in text
        assert "2005" in text
        assert "45,000" in text
        assert "blue smoke" in text

    def test_empty_context(self):
        ctx = VehicleContext()
        text = ctx.to_context_string()
        assert "No vehicle context provided" in text

    def test_partial_context(self):
        ctx = VehicleContext(make="Harley", model="Sportster")
        text = ctx.to_context_string()
        assert "Harley" in text
        assert "Sportster" in text


# --- SMOKE_COLOR_GUIDE ---


class TestSmokeColorGuide:
    def test_white_smoke_cause(self):
        assert "coolant" in SMOKE_COLOR_GUIDE["white"]["cause"].lower()

    def test_blue_smoke_cause(self):
        assert "oil" in SMOKE_COLOR_GUIDE["blue"]["cause"].lower()

    def test_black_smoke_cause(self):
        assert "rich" in SMOKE_COLOR_GUIDE["black"]["cause"].lower()

    def test_all_colors_have_common_sources(self):
        for color, info in SMOKE_COLOR_GUIDE.items():
            assert len(info["common_sources"]) > 0, f"{color} has no common sources"


# --- FLUID_COLOR_GUIDE ---


class TestFluidColorGuide:
    def test_green_is_coolant(self):
        assert "coolant" in FLUID_COLOR_GUIDE["green"]["fluid"].lower()

    def test_red_is_transmission(self):
        assert "transmission" in FLUID_COLOR_GUIDE["red"]["fluid"].lower()

    def test_all_colors_have_action(self):
        for color, info in FLUID_COLOR_GUIDE.items():
            assert len(info["action"]) > 0


# --- VisualAnalyzer: analyze_smoke ---


class TestAnalyzeSmoke:
    def test_known_color(self):
        analyzer = VisualAnalyzer(client=MagicMock())
        result = analyzer.analyze_smoke("blue")
        assert result["color"] == "blue"
        assert "oil" in result["cause"].lower()

    def test_case_insensitive(self):
        analyzer = VisualAnalyzer(client=MagicMock())
        result = analyzer.analyze_smoke("WHITE")
        assert result["color"] == "white"

    def test_unknown_color(self):
        analyzer = VisualAnalyzer(client=MagicMock())
        result = analyzer.analyze_smoke("purple")
        assert "unknown" in result["cause"].lower()


# --- VisualAnalyzer: analyze_fluid_leak ---


class TestAnalyzeFluidLeak:
    def test_known_fluid_color(self):
        analyzer = VisualAnalyzer(client=MagicMock())
        result = analyzer.analyze_fluid_leak("green")
        assert "coolant" in result["fluid"].lower()

    def test_unknown_fluid_color(self):
        analyzer = VisualAnalyzer(client=MagicMock())
        result = analyzer.analyze_fluid_leak("pink")
        assert "unknown" in result["fluid"].lower()


# --- VisualAnalyzer: analyze_image ---


class TestAnalyzeImage:
    def test_analyze_image_with_json_response(self):
        response = _make_json_response(
            findings=[{
                "finding_type": "smoke",
                "description": "Blue smoke from exhaust on startup",
                "confidence": 0.85,
                "location_in_image": "lower right",
                "severity": "high",
            }],
            overall_assessment="Possible valve seal wear",
            suggested_diagnostics=["Compression test", "Leak-down test"],
        )
        client = _make_mock_client(response)
        analyzer = VisualAnalyzer(client=client)
        result = analyzer.analyze_image(
            image_description="Photo showing blue smoke from exhaust during startup",
            vehicle_context=VehicleContext(make="Honda", model="CBR600RR", year=2005),
        )
        assert result.finding_count == 1
        assert result.findings[0].finding_type == FindingType.SMOKE
        assert result.findings[0].confidence == 0.85

    def test_analyze_image_empty_description(self):
        client = _make_mock_client()
        analyzer = VisualAnalyzer(client=client)
        result = analyzer.analyze_image(image_description="")
        assert result.finding_count == 0
        assert "No image description" in result.overall_assessment
        client.ask.assert_not_called()

    def test_analyze_image_unparseable_response(self):
        client = _make_mock_client("This is not JSON at all, just plain text analysis.")
        analyzer = VisualAnalyzer(client=client)
        result = analyzer.analyze_image(image_description="Photo of exhaust")
        assert result.finding_count == 0
        assert "structured JSON" in result.image_quality_note

    def test_analyze_image_calls_client_with_system_prompt(self):
        client = _make_mock_client(_make_json_response())
        analyzer = VisualAnalyzer(client=client)
        analyzer.analyze_image(image_description="test image")
        client.ask.assert_called_once()
        call_kwargs = client.ask.call_args
        assert call_kwargs[1]["system"] == VISION_ANALYSIS_PROMPT

    def test_analyze_image_no_vehicle_context(self):
        response = _make_json_response(
            overall_assessment="General motorcycle inspection",
        )
        client = _make_mock_client(response)
        analyzer = VisualAnalyzer(client=client)
        result = analyzer.analyze_image(image_description="Photo of a motorcycle")
        assert "General motorcycle inspection" in result.overall_assessment

    def test_analyze_image_whitespace_description(self):
        client = _make_mock_client()
        analyzer = VisualAnalyzer(client=client)
        result = analyzer.analyze_image(image_description="   \n  ")
        assert "No image description" in result.overall_assessment

    def test_analyze_image_markdown_json_response(self):
        json_body = _make_json_response(
            overall_assessment="Parsed from markdown",
        )
        response = f"```json\n{json_body}\n```"
        client = _make_mock_client(response)
        analyzer = VisualAnalyzer(client=client)
        result = analyzer.analyze_image(image_description="test")
        assert "Parsed from markdown" in result.overall_assessment


# --- VISION_ANALYSIS_PROMPT ---


class TestVisionPrompt:
    def test_prompt_mentions_smoke(self):
        assert "smoke" in VISION_ANALYSIS_PROMPT.lower()

    def test_prompt_mentions_leak(self):
        assert "leak" in VISION_ANALYSIS_PROMPT.lower()

    def test_prompt_mentions_gauge(self):
        assert "gauge" in VISION_ANALYSIS_PROMPT.lower()

    def test_prompt_mentions_wear(self):
        assert "wear" in VISION_ANALYSIS_PROMPT.lower()
