"""Phase 191B — Vision analysis pipeline tests.

Tests for ``motodiag.media.vision_analysis_pipeline.VisionAnalyzer`` (the
NEW real-image-bytes Vision wrapper added in Phase 191B Commit 2) and the
non-breaking ``VisualAnalysisResult`` extension (3 new optional fields).

Mocking strategy: ``DiagnosticClient.ask_with_images`` (NEW from Phase 191B
Commit 1, written in parallel by Builder-A) is mocked. Mock fixtures
synthesize the Anthropic SDK ``Message`` + ``ToolUseBlock`` shape from
``anthropic.types`` definitions — they are NOT recorded from real API
calls. Architect can regenerate higher-fidelity fixtures via
``tests/fixtures/anthropic_responses/_regen.py`` post-API-key configuration.

Cross-Commit-1 dependencies (mocked here; verify integration once
Builder-A's commit lands):
  - ``DiagnosticClient.ask_with_images`` (returns ``(Message, TokenUsage)``)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import pytest

from motodiag.engine.models import TokenUsage
from motodiag.media.vision_analysis import (
    FindingType,
    Severity,
    VehicleContext,
    VisualAnalysisResult,
    VisualFinding,
    VISION_ANALYSIS_PROMPT,
)
from motodiag.media.vision_analysis_pipeline import (
    DEFAULT_VISION_MODEL,
    MAX_FRAMES_PER_CALL,
    VisionAnalyzer,
    VisionPipelineError,
    _build_findings_tool,
    _build_user_prompt,
)


# --- Test helpers (synthetic SDK fixtures) -------------------------------


def _make_fake_tool_use_block(input_dict: dict):
    """Return an object resembling anthropic.types.ToolUseBlock.

    The pipeline reads ``block.type`` and ``block.input`` only; we don't
    need the full SDK typing for unit tests.
    """
    return SimpleNamespace(
        type="tool_use",
        id="toolu_01synthetic",
        name="report_video_findings",
        input=input_dict,
    )


def _make_fake_text_block(text: str):
    """Return an object resembling anthropic.types.TextBlock."""
    return SimpleNamespace(type="text", text=text)


def _make_fake_message(blocks: list):
    """Return an object resembling anthropic.types.Message.

    The pipeline reads ``response.content`` (a list of blocks) only.
    """
    return SimpleNamespace(
        id="msg_synthetic_01",
        type="message",
        role="assistant",
        content=blocks,
        model="claude-sonnet-4-6",
        stop_reason="tool_use",
    )


def _valid_findings_input(extra: dict | None = None) -> dict:
    """Build a valid VisualAnalysisResult-shaped tool_use input.

    Phase 191B fields (frames_analyzed, model_used, cost_estimate_usd) are
    intentionally omitted because the pipeline overwrites them with
    authoritative values from the SDK call.
    """
    base = {
        "findings": [
            {
                "finding_type": "smoke",
                "description": "Blue smoke from exhaust during throttle blip",
                "confidence": 0.85,
                "location_in_image": "lower right, exhaust pipe",
                "severity": "high",
            },
            {
                "finding_type": "wear",
                "description": "Chain shows visible elongation and rust",
                "confidence": 0.7,
                "location_in_image": "left side, drive chain",
                "severity": "medium",
            },
            {
                "finding_type": "gauge_reading",
                "description": "Coolant temp gauge reads in normal range",
                "confidence": 0.95,
                "location_in_image": "dashboard cluster",
                "severity": "info",
            },
        ],
        "overall_assessment": "Likely worn piston rings or valve seals; chain due for replacement.",
        "suggested_diagnostics": [
            "Compression test on all cylinders",
            "Leakdown test if compression is borderline",
            "Measure chain elongation against service-limit spec",
        ],
        "image_quality_note": "Frames are well-lit and in focus.",
    }
    if extra:
        base.update(extra)
    return base


def _make_mock_client_with_response(
    tool_use_input: dict | None = None,
    cost_estimate: float = 0.075,
    model_resolved: str = "claude-sonnet-4-6",
    extra_blocks: list | None = None,
) -> MagicMock:
    """Build a mock DiagnosticClient whose ask_with_images returns a synthetic Message."""
    client = MagicMock()
    blocks: list = []
    if extra_blocks:
        blocks.extend(extra_blocks)
    if tool_use_input is not None:
        blocks.append(_make_fake_tool_use_block(tool_use_input))
    fake_message = _make_fake_message(blocks)
    fake_usage = TokenUsage(
        input_tokens=1500,
        output_tokens=400,
        model=model_resolved,
        cost_estimate=cost_estimate,
        latency_ms=4200,
    )
    client.ask_with_images.return_value = (fake_message, fake_usage)
    return client


# --- VisualAnalysisResult extension (non-breaking) -----------------------


class TestVisualAnalysisResultExtension:
    """Phase 101 callers must continue to work after Phase 191B's 3-field extension."""

    def test_visualanalysisresult_extension_is_non_breaking(self):
        """A Phase-101-style construction (no new fields) still validates with safe defaults."""
        result = VisualAnalysisResult(
            findings=[],
            overall_assessment="Bike looks clean.",
            suggested_diagnostics=[],
            image_quality_note="",
        )
        assert result.frames_analyzed == 0
        assert result.model_used == ""
        assert result.cost_estimate_usd == 0.0

    def test_visualanalysisresult_extension_round_trips_when_supplied(self):
        """All 3 new fields survive model_dump -> model_validate."""
        result = VisualAnalysisResult(
            findings=[
                VisualFinding(
                    finding_type=FindingType.SMOKE,
                    description="Blue smoke from header",
                    confidence=0.9,
                    severity=Severity.HIGH,
                ),
            ],
            overall_assessment="Likely worn rings.",
            frames_analyzed=42,
            model_used="claude-sonnet-4-6",
            cost_estimate_usd=0.0823,
        )
        dumped = result.model_dump()
        assert dumped["frames_analyzed"] == 42
        assert dumped["model_used"] == "claude-sonnet-4-6"
        assert dumped["cost_estimate_usd"] == 0.0823

        reloaded = VisualAnalysisResult.model_validate(dumped)
        assert reloaded.frames_analyzed == 42
        assert reloaded.model_used == "claude-sonnet-4-6"
        assert reloaded.cost_estimate_usd == 0.0823
        assert len(reloaded.findings) == 1


# --- analyze_video_frames tests -----------------------------------------


class TestAnalyzeVideoFrames:

    def test_analyze_video_frames_happy_path(self):
        """End-to-end: SDK call returns valid tool_use; pipeline extracts findings + injects 191B fields."""
        client = _make_mock_client_with_response(tool_use_input=_valid_findings_input())
        analyzer = VisionAnalyzer(client=client, model="sonnet")
        frames = [Path(f"frame_{i:03d}.jpg") for i in range(1, 6)]

        result = analyzer.analyze_video_frames(frames=frames)

        assert isinstance(result, VisualAnalysisResult)
        assert len(result.findings) == 3
        assert result.findings[0].finding_type == FindingType.SMOKE
        assert result.findings[0].severity == Severity.HIGH
        assert result.frames_analyzed == 5
        # model_used is the resolved full model ID, not the alias.
        assert result.model_used == "claude-sonnet-4-6"
        assert result.cost_estimate_usd == pytest.approx(0.075)

    def test_analyze_video_frames_empty_frames_raises_ValueError(self):
        client = _make_mock_client_with_response(tool_use_input=_valid_findings_input())
        analyzer = VisionAnalyzer(client=client, model="sonnet")

        with pytest.raises(ValueError, match="frames list is empty"):
            analyzer.analyze_video_frames(frames=[])

        # SDK was never called.
        client.ask_with_images.assert_not_called()

    def test_analyze_video_frames_caps_at_60_frames(self):
        """80 input frames -> SDK receives only the first 60; result.frames_analyzed == 60."""
        client = _make_mock_client_with_response(tool_use_input=_valid_findings_input())
        analyzer = VisionAnalyzer(client=client, model="sonnet")
        frames = [Path(f"frame_{i:03d}.jpg") for i in range(1, 81)]

        result = analyzer.analyze_video_frames(frames=frames)

        assert MAX_FRAMES_PER_CALL == 60
        kwargs = client.ask_with_images.call_args.kwargs
        assert len(kwargs["images"]) == 60
        assert kwargs["images"][0] == Path("frame_001.jpg")
        assert kwargs["images"][-1] == Path("frame_060.jpg")
        assert result.frames_analyzed == 60

    def test_analyze_video_frames_passes_tool_choice_correctly(self):
        client = _make_mock_client_with_response(tool_use_input=_valid_findings_input())
        analyzer = VisionAnalyzer(client=client, model="sonnet")

        analyzer.analyze_video_frames(frames=[Path("a.jpg")])

        kwargs = client.ask_with_images.call_args.kwargs
        assert kwargs["tool_choice"] == {
            "type": "tool",
            "name": "report_video_findings",
        }

    def test_analyze_video_frames_passes_tool_definition(self):
        """tools[0] is the report_video_findings tool with the VisualAnalysisResult schema."""
        client = _make_mock_client_with_response(tool_use_input=_valid_findings_input())
        analyzer = VisionAnalyzer(client=client, model="sonnet")

        analyzer.analyze_video_frames(frames=[Path("a.jpg")])

        kwargs = client.ask_with_images.call_args.kwargs
        tools = kwargs["tools"]
        assert len(tools) == 1
        assert tools[0]["name"] == "report_video_findings"
        assert tools[0]["input_schema"] == VisualAnalysisResult.model_json_schema()

    def test_analyze_video_frames_no_tool_use_block_raises_VisionPipelineError(self):
        """If Claude returns only text content (no tool_use), pipeline raises."""
        client = MagicMock()
        # Build a Message with only a text block — no tool_use.
        fake_message = _make_fake_message([_make_fake_text_block("I cannot analyze that.")])
        fake_usage = TokenUsage(
            input_tokens=100,
            output_tokens=20,
            model="claude-sonnet-4-6",
            cost_estimate=0.001,
        )
        client.ask_with_images.return_value = (fake_message, fake_usage)
        analyzer = VisionAnalyzer(client=client, model="sonnet")

        with pytest.raises(VisionPipelineError, match="did not include a tool_use block"):
            analyzer.analyze_video_frames(frames=[Path("a.jpg")])

    def test_analyze_video_frames_invalid_schema_in_tool_use_raises_VisionPipelineError(self):
        """tool_use input that doesn't match VisualAnalysisResult schema -> VisionPipelineError."""
        # severity must be one of the Severity enum values; "extreme" is invalid.
        bogus_input = {
            "findings": [
                {
                    "finding_type": "smoke",
                    "description": "Smoke",
                    "confidence": 0.9,
                    "severity": "extreme",  # invalid Severity value
                }
            ],
            "overall_assessment": "Test",
        }
        client = _make_mock_client_with_response(tool_use_input=bogus_input)
        analyzer = VisionAnalyzer(client=client, model="sonnet")

        with pytest.raises(
            VisionPipelineError,
            match="tool_use block input did not match VisualAnalysisResult schema",
        ):
            analyzer.analyze_video_frames(frames=[Path("a.jpg")])

    def test_analyze_video_frames_sdk_exception_wraps_in_VisionPipelineError(self):
        """A generic Exception from the SDK is wrapped + chained as VisionPipelineError."""
        client = MagicMock()
        client.ask_with_images.side_effect = RuntimeError("network hiccup")
        analyzer = VisionAnalyzer(client=client, model="sonnet")

        with pytest.raises(VisionPipelineError, match="Vision SDK call failed") as exc_info:
            analyzer.analyze_video_frames(frames=[Path("a.jpg")])

        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert str(exc_info.value.__cause__) == "network hiccup"

    def test_analyze_video_frames_vehicle_context_interpolated(self):
        """make / model / year from VehicleContext appear in the prompt sent to the SDK."""
        client = _make_mock_client_with_response(tool_use_input=_valid_findings_input())
        analyzer = VisionAnalyzer(client=client, model="sonnet")
        vc = VehicleContext(make="Honda", model="CBR600RR", year=2005)

        analyzer.analyze_video_frames(frames=[Path("a.jpg")], vehicle_context=vc)

        kwargs = client.ask_with_images.call_args.kwargs
        prompt = kwargs["prompt"]
        assert "Honda" in prompt
        assert "CBR600RR" in prompt
        assert "2005" in prompt

    def test_analyze_video_frames_default_model_is_sonnet(self):
        """No-arg VisionAnalyzer() -> model='sonnet' -> SDK call uses 'sonnet' alias."""
        assert DEFAULT_VISION_MODEL == "sonnet"
        client = _make_mock_client_with_response(tool_use_input=_valid_findings_input())
        analyzer = VisionAnalyzer(client=client)  # no model override

        analyzer.analyze_video_frames(frames=[Path("a.jpg")])

        kwargs = client.ask_with_images.call_args.kwargs
        assert kwargs["model"] == "sonnet"

    def test_analyze_video_frames_haiku_override_works(self):
        """Instantiating VisionAnalyzer(model='haiku') propagates to the SDK call + resolved model."""
        client = _make_mock_client_with_response(
            tool_use_input=_valid_findings_input(),
            model_resolved="claude-haiku-4-5-20251001",
            cost_estimate=0.012,
        )
        analyzer = VisionAnalyzer(client=client, model="haiku")

        result = analyzer.analyze_video_frames(frames=[Path("a.jpg")])

        kwargs = client.ask_with_images.call_args.kwargs
        assert kwargs["model"] == "haiku"
        assert result.model_used == "claude-haiku-4-5-20251001"
        assert result.cost_estimate_usd == pytest.approx(0.012)

    def test_analyze_video_frames_uses_VISION_ANALYSIS_PROMPT_as_system(self):
        """The system prompt sent to Claude is Phase 101's VISION_ANALYSIS_PROMPT verbatim."""
        client = _make_mock_client_with_response(tool_use_input=_valid_findings_input())
        analyzer = VisionAnalyzer(client=client, model="sonnet")

        analyzer.analyze_video_frames(frames=[Path("a.jpg")])

        kwargs = client.ask_with_images.call_args.kwargs
        assert kwargs["system"] == VISION_ANALYSIS_PROMPT

    def test_analyze_video_frames_max_tokens_is_4096(self):
        """max_tokens passed to SDK is 4096 (per plan; image content is token-heavy)."""
        client = _make_mock_client_with_response(tool_use_input=_valid_findings_input())
        analyzer = VisionAnalyzer(client=client, model="sonnet")

        analyzer.analyze_video_frames(frames=[Path("a.jpg")])

        kwargs = client.ask_with_images.call_args.kwargs
        assert kwargs["max_tokens"] == 4096

    def test_analyze_video_frames_preserves_text_block_when_tool_use_present(self):
        """A response with both text + tool_use blocks should still extract from tool_use."""
        client = _make_mock_client_with_response(
            tool_use_input=_valid_findings_input(),
            extra_blocks=[_make_fake_text_block("Here are the findings:")],
        )
        analyzer = VisionAnalyzer(client=client, model="sonnet")

        result = analyzer.analyze_video_frames(frames=[Path("a.jpg")])

        assert len(result.findings) == 3
        assert result.frames_analyzed == 1


# --- Tool definition + prompt builder unit tests -------------------------


class TestToolDefinition:

    def test_build_findings_tool_has_correct_name(self):
        tool = _build_findings_tool()
        assert tool["name"] == "report_video_findings"

    def test_build_findings_tool_input_schema_matches_VisualAnalysisResult(self):
        tool = _build_findings_tool()
        assert tool["input_schema"] == VisualAnalysisResult.model_json_schema()

    def test_build_user_prompt_includes_frame_count(self):
        prompt = _build_user_prompt(VehicleContext(), 7)
        assert "7 frames" in prompt
        assert "report_video_findings" in prompt

    def test_build_user_prompt_includes_vehicle_context_when_present(self):
        vc = VehicleContext(make="Yamaha", model="R6", year=2008)
        prompt = _build_user_prompt(vc, 5)
        assert "Yamaha" in prompt
        assert "R6" in prompt
        assert "2008" in prompt
        assert "VEHICLE CONTEXT" in prompt
