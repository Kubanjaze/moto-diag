"""F9 wiring guard — real extracted frames must flow into the Vision analyzer.

Regression guard against a placeholder-vs-real drift in the media analysis
pipeline (integration-gap class F9). ``run_analysis_pipeline`` is supposed to
hand the frames produced by ``media/ffmpeg.py`` (real, on-disk JPEG frames)
straight to ``VisionAnalyzer.analyze_video_frames``. If a future refactor
accidentally swaps in a placeholder frame source (e.g. the simulated
``motodiag.media.sim.video_frames`` extractor, or a hardcoded stub list) while
still calling ffmpeg for show, the wiring would silently analyze the wrong
frames.

This test pins the wiring by identity: it makes ``extract_frames`` return a
SENTINEL list and asserts that the very same object reaches
``analyze_video_frames``. No live ffmpeg, no live Vision call — both boundaries
are mocked.
"""

from __future__ import annotations

from unittest import mock

import pytest

import motodiag.media.analysis_worker as worker_mod
from motodiag.core.database import init_db
from motodiag.core.session_repo import create_session_for_owner
from motodiag.core.video_repo import create_video, get_video
from motodiag.media.vision_types import VisualAnalysisResult


# --- Helpers ---


def _make_user(db_path: str, username: str = "wiring_guard_user") -> int:
    """Insert a user row + return its id (mirrors test_phase191b's helper)."""
    from motodiag.core.database import get_connection

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, ?, 1)",
            (username, f"{username}@example.com", "shop"),
        )
        return int(cursor.lastrowid)


def _make_video_row(db_path: str) -> int:
    """Create an owner + session + one 'pending' video row; return video id."""
    uid = _make_user(db_path)
    sid = create_session_for_owner(
        owner_user_id=uid,
        vehicle_make="Honda",
        vehicle_model="CBR600",
        vehicle_year=2005,
        db_path=db_path,
    )
    return create_video(
        session_id=sid,
        file_path="/tmp/wiring_guard_source_video.mp4",
        sha256="d" * 64,
        started_at="2026-04-29T10:00:00Z",
        duration_ms=5000,
        width=1920,
        height=1080,
        file_size_bytes=1000,
        db_path=db_path,
    )


class TestMediaPipelineWiringGuard:
    """F9 guard: the frames ffmpeg extracts are the frames Vision analyzes."""

    def test_extracted_frames_flow_into_vision_analyzer(self, tmp_path):
        db_path = str(tmp_path / "wiring_guard.db")
        init_db(db_path)
        video_id = _make_video_row(db_path)

        # SENTINEL: the exact list ffmpeg "returns". Fake frame objects — the
        # pipeline should pass them through untouched, not regenerate them.
        sentinel_frames = [object(), object(), object()]

        # Capture the frames handed to analyze_video_frames.
        captured = {}

        def _fake_analyze_video_frames(frames, vehicle_context=None):
            captured["frames"] = frames
            return VisualAnalysisResult(
                overall_assessment="wiring-guard stub result",
                frames_analyzed=len(frames),
                model_used="stub-model",
                cost_estimate_usd=0.0,
            )

        fake_analyzer = mock.MagicMock()
        fake_analyzer.analyze_video_frames.side_effect = _fake_analyze_video_frames

        with mock.patch.object(
            worker_mod.ffmpeg_module,
            "extract_frames",
            return_value=sentinel_frames,
        ) as mock_extract, mock.patch.object(
            worker_mod, "VisionAnalyzer", return_value=fake_analyzer,
        ):
            worker_mod.run_analysis_pipeline(video_id, db_path=db_path)

        # extract_frames called exactly once.
        assert mock_extract.call_count == 1

        # analyze_video_frames received the EXACT sentinel ffmpeg produced —
        # identity check proves real extracted frames flow through, not a
        # placeholder swapped in behind ffmpeg's back.
        fake_analyzer.analyze_video_frames.assert_called_once()
        assert captured["frames"] is sentinel_frames

        # Sanity: the pipeline ran to completion and persisted findings.
        row = get_video(video_id, db_path=db_path)
        assert row is not None
        assert row["analysis_state"] == "analyzed"
