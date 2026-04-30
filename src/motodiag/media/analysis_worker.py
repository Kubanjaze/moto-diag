"""Analysis worker for Phase 191B — orchestrates ffmpeg + Vision pipeline.

POST /v1/sessions/{id}/videos returns 201 with analysis_state='pending'
immediately and queues run_analysis_pipeline(video_id) on FastAPI's
BackgroundTasks. This module is the worker entry point.

State machine (per Phase 191B v1.0 plan):
    pending -> analyzing -> analyzed | analysis_failed | unsupported

  - 'unsupported' is TERMINAL (file genuinely un-analyzable; ffmpeg failed)
  - 'analysis_failed' is RETRYABLE via Phase 192+ admin endpoint

Phase 191B Commit 3 wires this up via FastAPI's BackgroundTasks.add_task.
For Phase 207 (Track J multi-worker uvicorn), this swaps to a real
worker queue (redis-rq / Celery); the function signature stays the same.

Cross-Commit-1 dependencies (created by Builder-A):
  - motodiag.core.video_repo (get_video, update_analysis_state,
    set_analysis_findings)
  - motodiag.core.models.VideoAnalysisState enum
  - motodiag.media.ffmpeg (extract_frames, FFmpegMissing, FFmpegFailed)
  - motodiag.engine.client.DiagnosticClient.ask_with_images
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional

from motodiag.core import video_repo
from motodiag.core.models import VideoAnalysisState
from motodiag.media import ffmpeg as ffmpeg_module
from motodiag.media.vision_analysis import VehicleContext
from motodiag.media.vision_analysis_pipeline import (
    VisionAnalyzer,
    VisionPipelineError,
)

_log = logging.getLogger(__name__)


def run_analysis_pipeline(video_id: int, db_path: Optional[str] = None) -> None:
    """Orchestrate the full Vision analysis pipeline for one video.

    Steps:
      1. Read video row + vehicle context from DB
      2. Transition state pending -> analyzing
      3. Extract frames via media/ffmpeg.py (FFmpegMissing -> analysis_failed
         + log; FFmpegFailed on real video -> unsupported)
      4. Call VisionAnalyzer.analyze_video_frames (VisionPipelineError ->
         analysis_failed)
      5. Persist findings + cost + model via video_repo.set_analysis_findings
         (also transitions state to 'analyzed')
      6. On any unexpected exception, transition to 'analysis_failed' + log

    Args:
        video_id: ID of the video row to analyze.
        db_path: Optional DB path override (test injection point).

    Returns:
        None. State is observed via subsequent DB reads.
    """
    video = video_repo.get_video(video_id, db_path=db_path)
    if video is None:
        _log.error("run_analysis_pipeline: video_id=%d not found", video_id)
        return

    # Transition: pending -> analyzing
    video_repo.update_analysis_state(
        video_id,
        VideoAnalysisState.ANALYZING.value,
        db_path=db_path,
    )

    output_dir = Path(tempfile.mkdtemp(prefix=f"video_{video_id}_frames_"))

    try:
        # 1. Extract frames
        try:
            frames = ffmpeg_module.extract_frames(
                video_path=Path(video["file_path"]),
                output_dir=output_dir,
            )
        except ffmpeg_module.FFmpegMissing:
            _log.error(
                "ffmpeg missing; transitioning video %d to analysis_failed",
                video_id,
            )
            video_repo.update_analysis_state(
                video_id,
                VideoAnalysisState.ANALYSIS_FAILED.value,
                db_path=db_path,
            )
            return
        except ffmpeg_module.FFmpegFailed as e:
            _log.warning(
                "ffmpeg failed for video %d (%s); transitioning to unsupported",
                video_id,
                e,
            )
            video_repo.update_analysis_state(
                video_id,
                VideoAnalysisState.UNSUPPORTED.value,
                db_path=db_path,
            )
            return

        if not frames:
            _log.warning(
                "ffmpeg produced 0 frames for video %d; unsupported", video_id
            )
            video_repo.update_analysis_state(
                video_id,
                VideoAnalysisState.UNSUPPORTED.value,
                db_path=db_path,
            )
            return

        # 2. Build vehicle context (best-effort; future: JOIN against sessions)
        vc = _build_vehicle_context(video, db_path=db_path)

        # 3. Call Vision pipeline
        try:
            analyzer = VisionAnalyzer(model="sonnet")
            result = analyzer.analyze_video_frames(frames, vehicle_context=vc)
        except VisionPipelineError as e:
            _log.warning(
                "Vision pipeline error for video %d: %s", video_id, e
            )
            video_repo.update_analysis_state(
                video_id,
                VideoAnalysisState.ANALYSIS_FAILED.value,
                db_path=db_path,
            )
            return
        except Exception as e:
            _log.exception(
                "Unexpected error in Vision pipeline for video %d: %s",
                video_id,
                e,
            )
            video_repo.update_analysis_state(
                video_id,
                VideoAnalysisState.ANALYSIS_FAILED.value,
                db_path=db_path,
            )
            return

        # 4. Persist findings (also transitions state to 'analyzed')
        video_repo.set_analysis_findings(
            video_id,
            findings_dict=result.model_dump(),
            model_used=result.model_used,
            cost_usd=result.cost_estimate_usd,
            db_path=db_path,
        )

    finally:
        # Cleanup temp frame dir. Tolerant of partial cleanup — frames may
        # have been deleted already by the Vision pipeline if it streamed
        # them; missing files are not an error here.
        try:
            for f in output_dir.glob("*"):
                try:
                    f.unlink()
                except OSError:
                    pass
            output_dir.rmdir()
        except OSError:
            pass


def _build_vehicle_context(
    video_row: dict, db_path: Optional[str] = None
) -> VehicleContext:
    """Build VehicleContext from the session's vehicle (best-effort).

    Phase 191B Commit 2 returns a stub VehicleContext (empty); Commit 3 + 4
    will JOIN against sessions/vehicles for richer context. Don't block on
    missing data — the analysis still runs.
    """
    return VehicleContext()
