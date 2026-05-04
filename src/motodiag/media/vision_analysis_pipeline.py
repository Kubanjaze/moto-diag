"""Real image-bytes Claude Vision pipeline for Phase 191B video diagnostic analysis.

Phase 101's media/vision_analysis.py is text-only (analyze_image takes
image_description: str + calls DiagnosticClient.ask() with text completion).
This module is the real image-bytes implementation that fulfills Phase 191's
video analysis requirement: takes a list of frame file paths (extracted by
media/ffmpeg.py per Phase 191B Commit 1), base64-encodes them as content
blocks, calls DiagnosticClient.ask_with_images() with tool-use structured
output, and parses the response into a VisualAnalysisResult populated with
frames_analyzed + model_used + cost_estimate_usd (Phase 191B fields on the
existing Phase 101 schema).

Reuses Phase 101's prompt + finding types unchanged:
  - VISION_ANALYSIS_PROMPT (the system prompt)
  - FindingType / Severity / VisualFinding / VisualAnalysisResult / VehicleContext
  - SMOKE_COLOR_GUIDE / FLUID_COLOR_GUIDE (constants)

Fulfills the contract that Phase 100's media/video_frames.py established
(metadata-only types: VideoMetadata, VideoFrame, FrameExtractionConfig) by
providing the real-bytes Vision call that consumes ffmpeg-extracted frames.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from motodiag.media.vision_analysis import (
    VISION_ANALYSIS_PROMPT,
    VehicleContext,
    VisualAnalysisResult,
)

_log = logging.getLogger(__name__)


# Sonnet for default; Haiku for cost-tier override per plan B5.
#
# Phase 191B fix-cycle-4 (2026-05-04): default reads MOTODIAG_VISION_MODEL
# env var first to allow ops-time override without a code change. Architect
# ask after the hardcoded "sonnet" alias resolved to a non-existent model
# ID at re-smoke step 7. The env var accepts an alias ("sonnet" / "haiku")
# OR a full model ID (e.g., "claude-sonnet-4-6"). Aliases route through
# engine/client.py's _resolve_model + MODEL_ALIASES table so both the
# pricing dict + the SDK call see the same resolved ID.
DEFAULT_VISION_MODEL = os.environ.get("MOTODIAG_VISION_MODEL", "sonnet")

# Defensive cap; matches media/ffmpeg.py MAX_FRAMES (Builder-A's Commit 1).
# If the caller passes more than this, we trim silently — ffmpeg's own
# extraction cap should prevent this from triggering in practice.
MAX_FRAMES_PER_CALL = 60


def _build_findings_tool() -> dict:
    """Build the tool definition that forces Claude to return structured findings.

    Tool-use structured output: define a tool the model MUST call with the
    findings; the assistant turn returns a tool_use block whose .input matches
    our VisualAnalysisResult JSON schema. Same pattern as Phase 03 + Phase 22.
    """
    return {
        "name": "report_video_findings",
        "description": (
            "Report structured visual findings extracted from the video frames "
            "of a motorcycle diagnostic capture. Call this tool exactly once "
            "with all observed findings, the overall assessment, and any "
            "suggested follow-up diagnostics."
        ),
        "input_schema": VisualAnalysisResult.model_json_schema(),
    }


def _build_user_prompt(vehicle_context: VehicleContext, frame_count: int) -> str:
    """Build the user prompt text that accompanies the image content blocks."""
    parts = []
    if vehicle_context:
        ctx = vehicle_context.to_context_string()
        parts.append(f"VEHICLE CONTEXT:\n{ctx}\n")
    parts.append(
        f"Analyzing {frame_count} frames extracted from a video diagnostic "
        f"capture of this motorcycle. Examine each frame for the diagnostic "
        f"symptoms in the system prompt and report findings via the "
        f"report_video_findings tool."
    )
    return "\n".join(parts)


class VisionPipelineError(RuntimeError):
    """Raised when the Vision pipeline can't produce a valid VisualAnalysisResult.

    Caller (analysis_worker.run_analysis_pipeline) catches this and transitions
    the video's analysis_state to 'analysis_failed' (retryable later via
    Phase 192+ admin endpoint).
    """


class VisionAnalyzer:
    """Real image-bytes Vision analyzer for Phase 191B video diagnostic pipeline.

    Distinct from Phase 101's text-only ``VisualAnalyzer`` (in
    ``motodiag.media.vision_analysis``) which takes ``image_description: str``
    and calls ``DiagnosticClient.ask()``. This class takes real frame file
    paths (JPEG), base64-encodes them as image content blocks, and calls
    the new ``DiagnosticClient.ask_with_images()`` method (Phase 191B
    Commit 1).

    Usage:
        analyzer = VisionAnalyzer(client=DiagnosticClient(model="sonnet"))
        result = analyzer.analyze_video_frames(
            frames=[Path("frame_001.jpg"), Path("frame_002.jpg"), ...],
            vehicle_context=VehicleContext(make="Honda", model="CBR600RR", year=2005),
        )
        # result.findings, result.overall_assessment, result.frames_analyzed,
        # result.model_used, result.cost_estimate_usd populated.
    """

    def __init__(self, client=None, model: str = DEFAULT_VISION_MODEL):
        """Initialize the Vision analyzer.

        Args:
            client: DiagnosticClient instance (or mock). If None, creates one
                lazily on first call.
            model: Claude model alias ("haiku", "sonnet") or full model ID.
                Defaults to Sonnet per plan B5.
        """
        self._client = client
        self._model = model

    def _get_client(self):
        """Lazy-initialize the DiagnosticClient if not provided."""
        if self._client is None:
            from motodiag.engine.client import DiagnosticClient

            self._client = DiagnosticClient(model=self._model)
        return self._client

    def analyze_video_frames(
        self,
        frames: list[Path],
        vehicle_context: Optional[VehicleContext] = None,
    ) -> VisualAnalysisResult:
        """Analyze a batch of video frames using Claude Vision via tool-use.

        Args:
            frames: List of frame file paths (JPEG). Will be capped at
                ``MAX_FRAMES_PER_CALL`` defensively.
            vehicle_context: Optional motorcycle context for prompt enrichment.

        Returns:
            VisualAnalysisResult with findings + frames_analyzed + model_used +
            cost_estimate_usd populated.

        Raises:
            ValueError: If frames list is empty.
            VisionPipelineError: On structured-output schema violation, missing
                tool_use block, or wrapped SDK exception. Caller transitions
                analysis_state to 'analysis_failed' on this signal.
        """
        if not frames:
            raise ValueError(
                "frames list is empty; analyze_video_frames requires >=1 frame"
            )

        capped = frames[:MAX_FRAMES_PER_CALL]
        client = self._get_client()
        prompt = _build_user_prompt(vehicle_context or VehicleContext(), len(capped))
        tools = [_build_findings_tool()]
        tool_choice = {"type": "tool", "name": "report_video_findings"}

        # Resolve the actual model ID for the model_used reporting field.
        # Import here (not at module level) so a unit test that mocks the
        # whole engine.client module doesn't trip on _resolve_model.
        from motodiag.engine.client import _resolve_model

        resolved_model = _resolve_model(self._model)

        try:
            response, usage = client.ask_with_images(
                prompt=prompt,
                images=capped,
                system=VISION_ANALYSIS_PROMPT,
                model=self._model,
                max_tokens=4096,
                tools=tools,
                tool_choice=tool_choice,
            )
        except VisionPipelineError:
            # Re-raise without wrapping (preserve original chain).
            raise
        except Exception as e:
            raise VisionPipelineError(f"Vision SDK call failed: {e}") from e

        # Extract the tool_use block. response.content is a list of content
        # blocks; we expect one tool_use block whose .input matches our schema.
        tool_use_input = None
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                tool_use_input = block.input
                break

        if tool_use_input is None:
            raise VisionPipelineError(
                "Claude response did not include a tool_use block; "
                "tool_choice was forced but not honored"
            )

        try:
            # Inject Phase 191B fields before validation. Defensive: if Claude
            # echoed these fields back from the schema, our values overwrite
            # them since they're authoritative.
            findings_data = dict(tool_use_input)
            findings_data["frames_analyzed"] = len(capped)
            findings_data["model_used"] = resolved_model
            findings_data["cost_estimate_usd"] = usage.cost_estimate
            return VisualAnalysisResult.model_validate(findings_data)
        except Exception as e:
            raise VisionPipelineError(
                f"tool_use block input did not match VisualAnalysisResult schema: {e}"
            ) from e
