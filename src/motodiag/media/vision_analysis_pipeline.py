"""Real image-bytes Claude Vision pipeline for Phase 191B video diagnostic analysis.

The Phase 101 text-only analyzer (now motodiag.media.sim.vision_analyzer_textsim;
its analyze_image takes image_description: str + calls DiagnosticClient.ask()
with text completion) is superseded by this module — the real image-bytes
implementation that fulfills Phase 191's video analysis requirement: takes a
list of frame file paths (extracted by media/ffmpeg.py per Phase 191B Commit 1),
base64-encodes them as content blocks, calls DiagnosticClient.ask_with_images()
with tool-use structured output, and parses the response into a
VisualAnalysisResult populated with frames_analyzed + model_used +
cost_estimate_usd (Phase 191B fields on the shared schema).

Reuses the shared Phase 101 prompt + finding types (now in
motodiag.media.vision_types) unchanged:
  - VISION_ANALYSIS_PROMPT (the system prompt)
  - FindingType / Severity / VisualFinding / VisualAnalysisResult / VehicleContext
  - SMOKE_COLOR_GUIDE / FLUID_COLOR_GUIDE (constants)

Fulfills the metadata-only contract that Phase 100 established (VideoMetadata,
VideoFrame, FrameExtractionConfig — simulated in motodiag.media.sim.video_frames)
by providing the real-bytes Vision call that consumes ffmpeg-extracted frames.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from motodiag.media.vision_costs import (
    KIND_GUIDANCE,
    KIND_SWEEP,
    record_vision_cost,
)
from motodiag.media.vision_types import (
    VISION_ANALYSIS_PROMPT,
    VehicleContext,
    VisualAnalysisResult,
    GUIDANCE_PROMPT,
    GuidanceResponse,
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


def _format_known_issues(known_issues: Optional[list[dict]]) -> str:
    """Render corpus rows for the grounding block of a guidance prompt.

    Titles and a short description only. The point is to let the model cite an
    entry by title in ``grounding_detail`` so a technician can go and read it —
    not to inline the whole corpus into a prompt.
    """
    if not known_issues:
        return ""

    # Phase 244E: the tier is rendered, not dropped. Retrieval now fills the
    # request with same-make entries for other models, because 30% of the
    # corpus carries prose in its `model` column and an equality filter reaches
    # almost none of it. An unlabelled near-neighbour row is worse than no row:
    # it would license a machine-specific claim built on another machine's
    # evidence. Labelling is what lets a row inform an answer without being
    # mistaken for proof about THIS machine.
    tier_label = {
        "model": "[this model]",
        "make_wide": "[this make, all models]",
        "make_other_model": "[SAME MAKE, DIFFERENT MODEL — not established for this machine]",
    }
    lines = []
    for row in known_issues[:12]:
        title = (row.get("title") or "").strip()
        if not title:
            continue
        desc = (row.get("description") or "").strip().replace("\n", " ")
        label = tier_label.get(row.get("match_tier", "make_other_model"), "")
        model = (row.get("model") or "").strip()
        suffix = f" (corpus model: {model[:60]})" if row.get("match_tier") == "make_other_model" and model else ""
        lines.append(f"- {label} {title}{suffix}: {desc[:220]}")
    return "\n".join(lines)


def _build_user_prompt(
    vehicle_context: VehicleContext,
    frame_count: int,
    question: Optional[str] = None,
    corpus_context: Optional[str] = None,
) -> str:
    """Build the user prompt text that accompanies the image content blocks.

    Phase 244B: ``question`` is new and is the point of that phase. Before it,
    this function took only the vehicle context and a frame count, so a
    technician's question could not reach the model at all — a request to find
    where a leak was coming from returned a full six-category sweep, because a
    sweep was the only thing the prompt ever asked for. The question was not
    drifted from; it was never an input.

    When a question is supplied the prompt is built for GUIDANCE: answer that
    question, ground each candidate, and say what cannot be established. When
    it is not, the original sweep prompt is produced unchanged, so the existing
    pipeline behaves exactly as before.
    """
    parts = []
    if vehicle_context:
        ctx = vehicle_context.to_context_string()
        parts.append(f"VEHICLE CONTEXT:\n{ctx}\n")

    if question:
        parts.append(
            f"THE TECHNICIAN'S QUESTION — answer this, and only this:\n"
            f"{question.strip()}\n"
        )
        if corpus_context:
            parts.append(
                "KNOWN ISSUES FOR THIS MACHINE. Ground your candidates in these "
                "where they apply, and cite the entry title in grounding_detail. "
                "Where none applies, mark the candidate general_reasoning and say "
                "so — do not present reasoning as documentation.\n"
                f"{corpus_context}\n"
            )
        else:
            parts.append(
                "NO CORPUS ENTRIES were supplied for this machine. Every candidate "
                "you give is therefore general_reasoning at best; mark them so, and "
                "say plainly in not_established that nothing documented was "
                "available for this machine.\n"
            )
        parts.append(
            f"You are looking at {frame_count} frames from a video capture of "
            f"this motorcycle. Use them as evidence for the question above. "
            f"Report through the provide_guidance tool."
        )
        return "\n".join(parts)

    parts.append(
        f"Analyzing {frame_count} frames extracted from a video diagnostic "
        f"capture of this motorcycle. Examine each frame for the diagnostic "
        f"symptoms in the system prompt and report findings via the "
        f"report_video_findings tool."
    )
    return "\n".join(parts)


def _build_guidance_tool() -> dict:
    """Tool schema for guidance mode.

    Deliberately separate from ``report_video_findings`` rather than replacing
    it. The sweep tool is correct for a sweep request and its forced
    ``tool_choice`` is what makes the sweep reliable; the failure was applying
    that shape to a question. Both tools exist, and the caller picks by whether
    a question was asked.
    """
    schema = GuidanceResponse.model_json_schema()
    schema.pop("$defs", None)
    full = GuidanceResponse.model_json_schema()
    return {
        "name": "provide_guidance",
        "description": (
            "Answer the technician's specific question with candidate origins "
            "and the observations that tell them apart. Not a diagnosis: no "
            "root cause, no repair steps, no parts, no costs."
        ),
        "input_schema": full,
    }


class VisionPipelineError(RuntimeError):
    """Raised when the Vision pipeline can't produce a valid VisualAnalysisResult.

    Caller (analysis_worker.run_analysis_pipeline) catches this and transitions
    the video's analysis_state to 'analysis_failed' (retryable later via
    Phase 192+ admin endpoint).
    """


class VisionAnalyzer:
    """Real image-bytes Vision analyzer for Phase 191B video diagnostic pipeline.

    Distinct from Phase 101's text-only ``VisualAnalyzer`` (now in
    ``motodiag.media.sim.vision_analyzer_textsim``) which takes
    ``image_description: str`` and calls ``DiagnosticClient.ask()``. This class
    takes real frame file
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

    def answer_question_about_frames(
        self,
        frames: list[Path],
        question: str,
        vehicle_context: Optional[VehicleContext] = None,
        known_issues: Optional[list[dict]] = None,
        video_id: Optional[int] = None,
        shop_id: Optional[int] = None,
        db_path: Optional[str] = None,
    ) -> GuidanceResponse:
        """Answer a technician's question about a machine, using the frames as
        evidence.

        Phase 244B. This is deliberately a SEPARATE entry point from
        :meth:`analyze_video_frames` rather than a flag on it. The sweep is
        correct for a sweep request, and its forced ``tool_choice`` is what
        makes it reliable; the failure was applying that shape to a question.
        Keeping them apart means the sweep path is provably unchanged.

        Args:
            frames: Frame file paths (JPEG), capped at ``MAX_FRAMES_PER_CALL``.
            question: What the technician actually asked. Required — this method
                has no meaning without one.
            vehicle_context: Motorcycle context for the prompt.
            known_issues: Corpus rows for this machine, used to ground
                candidates. When empty the model is told so explicitly and must
                mark its candidates as general reasoning.

        Returns:
            A :class:`GuidanceResponse` — candidates and discriminators, never
            a diagnosis.

        Raises:
            ValueError: if ``frames`` is empty or ``question`` is blank.
            VisionPipelineError: if the SDK call or tool extraction fails.
        """
        if not frames:
            raise ValueError(
                "frames list is empty; answer_question_about_frames requires >=1 frame"
            )
        if not question or not question.strip():
            raise ValueError(
                "question is required; use analyze_video_frames for an unprompted sweep"
            )

        capped = frames[:MAX_FRAMES_PER_CALL]
        client = self._get_client()
        corpus_context = _format_known_issues(known_issues)
        prompt = _build_user_prompt(
            vehicle_context or VehicleContext(),
            len(capped),
            question=question,
            corpus_context=corpus_context,
        )
        tools = [_build_guidance_tool()]
        tool_choice = {"type": "tool", "name": "provide_guidance"}

        try:
            response, usage = client.ask_with_images(
                prompt=prompt,
                images=capped,
                system=GUIDANCE_PROMPT,
                model=self._model,
                max_tokens=4096,
                tools=tools,
                tool_choice=tool_choice,
            )
        except VisionPipelineError:
            raise
        except Exception as e:
            raise VisionPipelineError(f"Vision SDK call failed: {e}") from e

        tool_use_input = None
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                tool_use_input = block.input
                break
        if tool_use_input is None:
            raise VisionPipelineError(
                "no tool_use block in guidance response; expected provide_guidance"
            )
        try:
            answer = GuidanceResponse(**tool_use_input)
            # Phase 244L: this is the call that used to be free as far as the
            # ledger was concerned — the usage was bound to `_usage` and
            # discarded, so a request costing a vision call recorded nothing.
            record_vision_cost(
                usage, KIND_GUIDANCE,
                video_id=video_id, shop_id=shop_id, db_path=db_path,
            )
            return answer
        except Exception as e:
            raise VisionPipelineError(f"guidance payload did not validate: {e}") from e

    def analyze_video_frames(
        self,
        frames: list[Path],
        vehicle_context: Optional[VehicleContext] = None,
        video_id: Optional[int] = None,
        shop_id: Optional[int] = None,
        db_path: Optional[str] = None,
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
            # Phase 244L: the ledger, not only the JSON blob on the video row.
            # A blob per video cannot answer "what did today cost".
            record_vision_cost(
                usage, KIND_SWEEP,
                video_id=video_id, shop_id=shop_id, db_path=db_path,
            )
            return VisualAnalysisResult.model_validate(findings_data)
        except Exception as e:
            raise VisionPipelineError(
                f"tool_use block input did not match VisualAnalysisResult schema: {e}"
            ) from e
