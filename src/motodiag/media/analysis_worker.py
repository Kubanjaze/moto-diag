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
import json

from motodiag.media.vision_types import VehicleContext
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

        # 2. Build vehicle context (best-effort; JOINs sessions since Phase 244B)
        vc = _build_vehicle_context(video, db_path=db_path)

        # 3. Call Vision pipeline
        try:
            analyzer = VisionAnalyzer(model="sonnet")
            result = analyzer.analyze_video_frames(
                frames, vehicle_context=vc, video_id=video_id, db_path=db_path,
            )
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

        # Phase 199 — best-effort push to the session owner (suppressed
        # exceptions inside; the analysis result is already persisted).
        from motodiag.push.events import notify_analysis_complete

        notify_analysis_complete(
            session_id=int(video.get("session_id", 0)),
            video_id=video_id,
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
    """Build VehicleContext from the session's vehicle.

    Phase 244B: this was a stub returning an empty ``VehicleContext()``. Its
    docstring said Commit 3 + 4 would "JOIN against sessions/vehicles for
    richer context" — that never landed, so every video analysis since Phase
    191B has run with make, model, year and mileage blank.

    The consequence was not subtle. ``VehicleContext.to_context_string()``
    emits the literal string "No vehicle context provided." when the context is
    empty, so the model was told, on every analysis, that nothing was known
    about the machine — and then shown pixels. Guessing the make and model was
    the only thing left to it, and that is exactly what a user observed it
    doing while the session already held the answer.

    Same integration-gap family as ``SafetyChecker`` at Phase 241: implemented
    as a stub, completion deferred to a later commit, wiring never landed, and
    nothing failed loudly in the meantime.

    Still best-effort by design — a missing session or vehicle must not stop
    the analysis, it just returns what it can.
    """
    session_id = video_row.get("session_id")
    if not session_id:
        return VehicleContext()

    try:
        from motodiag.core.session_repo import get_session

        session = get_session(session_id, db_path=db_path)
    except Exception:
        return VehicleContext()
    if not session:
        return VehicleContext()

    symptoms = session.get("symptoms") or []
    if isinstance(symptoms, str):
        try:
            symptoms = json.loads(symptoms)
        except (ValueError, TypeError):
            symptoms = [symptoms] if symptoms else []

    # The session denormalizes make/model/year at creation AND keeps a
    # vehicle_id. Nothing re-syncs them, so editing the bike in the garage
    # leaves the session's copy stale — a user hit exactly this: they
    # corrected "Homda" to "Honda" in the garage and the session kept
    # reporting the typo. The live vehicle row is the source of truth for
    # what the machine IS; the session snapshot is only a fallback for rows
    # with no vehicle_id, or whose vehicle has since been deleted.
    mileage = None
    make = session.get("vehicle_make") or ""
    model = session.get("vehicle_model") or ""
    year = session.get("vehicle_year")

    vehicle_id = session.get("vehicle_id")
    if vehicle_id:
        try:
            from motodiag.core.database import get_connection

            with get_connection(db_path) as conn:
                row = conn.execute(
                    "SELECT make, model, year, mileage FROM vehicles WHERE id = ?",
                    (vehicle_id,),
                ).fetchone()
            if row is not None:
                keyed = not isinstance(row, tuple)
                mileage = row["mileage"] if keyed else row[3]
                live_make = (row["make"] if keyed else row[0]) or ""
                live_model = (row["model"] if keyed else row[1]) or ""
                live_year = row["year"] if keyed else row[2]
                # Only override with a live value that actually says something;
                # a blank garage field must not erase the session's snapshot.
                make = live_make or make
                model = live_model or model
                year = live_year if live_year is not None else year
        except Exception:
            mileage = None

    # Phase 244C: resolve the name against the corpus vocabulary. A user typed
    # "Homda cbrf4i" and every knowledge lookup returned zero rows while the
    # corpus held entries for the Honda CBR600F4i — silently, with no way for
    # anything downstream to tell an unmatched name from a machine nobody has
    # documented. Corrections are reported in the context, never applied
    # quietly: the technician wrote something, and swapping it without saying
    # so would just be a different kind of guessing.
    identity_note = ""
    try:
        from motodiag.knowledge.vehicle_resolver import resolve_vehicle

        identity = resolve_vehicle(make, model, db_path=db_path)
        if identity.make.applied:
            make = identity.resolved_make()
        if identity.model.applied:
            model = identity.resolved_model()
        notes_parts = identity.corrections() + identity.suggestions()
        if notes_parts:
            identity_note = "Vehicle identity: " + "; ".join(notes_parts)
    except Exception:
        identity_note = ""

    # Phase 244M: the machine's own compiled history. Best-effort like
    # everything else here -- a memory that cannot be read must not stop an
    # analysis that would otherwise run.
    history = ""
    if vehicle_id:
        try:
            from motodiag.memory.recall import recall_summary

            history = recall_summary(vehicle_id, db_path=db_path)
        except Exception:
            history = ""

    return VehicleContext(
        make=make,
        model=model,
        year=year,
        mileage=mileage,
        reported_symptoms=[s for s in symptoms if s],
        identity_note=identity_note,
        notes=session.get("notes") or "",
        history=history,
    )
