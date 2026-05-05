"""Phase 192 Commit 1 — videos + Vision findings section extension tests.

Boundary-decoupling gate per plan v1.0.1 Section A: composer's pytest
suite tests ``build_session_report_doc(session_id, user_id)`` directly
without HTTP layer. If a test required HTTP-layer concerns to set up,
that would be a coupling smell — none of these tests touch FastAPI.

Coverage matrix:

* :class:`TestVideosSection` — composer behavior:
  - Omit-when-empty (Pattern 1, mirrors symptoms / fault_codes).
  - Present + ``findings`` absent for non-analyzed states.
  - Present + ``findings`` present for analyzed state.
  - Mixed analysis-state shape (per-card correctness).
  - Required metadata fields per card.
  - Findings shape mirrors ``VisualAnalysisResult.model_dump()``.

* :class:`TestVideosRenderers` — text + PDF renderer extension
  smoke. Byte-for-byte determinism is 192B's concern; this suite
  only verifies render-without-crash + presence of expected
  metadata fragments.

Phase 191B fixtures use ``video_repo.create_video()`` +
``video_repo.set_analysis_findings()`` to seed; no mocking.
"""

from __future__ import annotations

import pytest

from motodiag.core.database import get_connection, init_db
from motodiag.engine.client import MODEL_ALIASES
from motodiag.core.session_repo import create_session_for_owner
from motodiag.core.video_repo import (
    create_video, set_analysis_findings, update_analysis_state,
)
from motodiag.media.vision_analysis import VisualAnalysisResult
from motodiag.reporting.builders import build_session_report_doc
from motodiag.reporting.renderers import (
    PDF_AVAILABLE, PdfReportRenderer, TextReportRenderer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Phase 192 fixture mirrors phase182_reports' ``api_db`` shape but
    drops the rate-limit env work (no HTTP here)."""
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase192.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username="bob"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        )
        return cursor.lastrowid


def _make_video(
    db_path, session_id,
    file_path="/tmp/recording-2026-05-05-1432.mp4",
    duration_ms=5200, file_size_bytes=1572864,
    interrupted=False,
):
    """Insert a video row in the canonical Phase 191B shape (analysis
    starts in ``pending`` per the SQL default; tests transition state
    via ``update_analysis_state`` / ``set_analysis_findings``)."""
    return create_video(
        session_id=session_id,
        file_path=file_path,
        sha256="0" * 64,
        started_at="2026-05-05T14:32:18+00:00",
        duration_ms=duration_ms,
        width=1280, height=720,
        file_size_bytes=file_size_bytes,
        interrupted=interrupted,
        db_path=db_path,
    )


def _sample_findings_payload() -> dict:
    """Round-trip a ``VisualAnalysisResult`` through ``model_dump()`` so
    the seeded findings have the exact shape Phase 191B's writer would
    produce. Keeps the test fixture aligned with the Pydantic source of
    truth."""
    result = VisualAnalysisResult(
        findings=[
            {
                "finding_type": "smoke",
                "description": (
                    "Blue smoke from exhaust during throttle blip"
                ),
                "confidence": 0.85,
                "severity": "high",
                "location_in_image": "lower right, exhaust pipe",
            },
        ],
        overall_assessment="Likely worn piston rings or valve seals.",
        suggested_diagnostics=["Compression test", "Leakdown test"],
        image_quality_note="Frames are well-lit and in focus.",
        frames_analyzed=5,
        model_used=MODEL_ALIASES["sonnet"],
        cost_estimate_usd=0.0354,
    )
    return result.model_dump()


def _videos_section(doc) -> dict | None:
    for s in doc.get("sections") or []:
        if "videos" in s:
            return s
    return None


# ===========================================================================
# 1. Composer behavior — videos section
# ===========================================================================


class TestVideosSection:

    def test_videos_section_omitted_when_zero_videos(self, db_path):
        """Pattern 1: omit-when-empty (mirrors symptoms / fault_codes)."""
        user_id = _make_user(db_path)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR600", 2005, db_path=db_path,
        )
        doc = build_session_report_doc(sid, user_id, db_path=db_path)
        headings = [s.get("heading") for s in doc["sections"]]
        assert "Videos" not in headings
        assert _videos_section(doc) is None

    def test_videos_section_present_with_one_video_no_analysis(
        self, db_path,
    ):
        """analysis_state == 'pending'; ``findings`` key absent (not
        present-with-None) per shape doc Variant 5 contract."""
        user_id = _make_user(db_path)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR600", 2005, db_path=db_path,
        )
        vid = _make_video(db_path, sid)
        doc = build_session_report_doc(sid, user_id, db_path=db_path)
        videos_sec = _videos_section(doc)
        assert videos_sec is not None
        assert videos_sec["heading"] == "Videos"
        assert len(videos_sec["videos"]) == 1
        card = videos_sec["videos"][0]
        assert card["video_id"] == vid
        assert card["analysis_state"] == "pending"
        # Absent-vs-None distinction matters per shape doc.
        assert "findings" not in card

    def test_videos_section_present_with_one_video_analyzed(
        self, db_path,
    ):
        """analysis_state == 'analyzed'; ``findings`` key present with
        full ``VisualAnalysisResult.model_dump()`` shape."""
        user_id = _make_user(db_path)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR600", 2005, db_path=db_path,
        )
        vid = _make_video(db_path, sid)
        set_analysis_findings(
            vid, _sample_findings_payload(), db_path=db_path,
        )
        doc = build_session_report_doc(sid, user_id, db_path=db_path)
        videos_sec = _videos_section(doc)
        assert videos_sec is not None
        cards = videos_sec["videos"]
        assert len(cards) == 1
        card = cards[0]
        assert card["analysis_state"] == "analyzed"
        assert "findings" in card
        findings = card["findings"]
        # Findings come from VisualAnalysisResult.model_dump() — the
        # inner list-of-findings field name is ``findings`` (matches
        # the Pydantic model's ``findings: list[VisualFinding]``).
        assert "findings" in findings
        assert len(findings["findings"]) == 1
        assert findings["overall_assessment"] == (
            "Likely worn piston rings or valve seals."
        )
        assert findings["model_used"] == MODEL_ALIASES["sonnet"]
        assert findings["frames_analyzed"] == 5

    def test_videos_section_mixed_analysis_states(self, db_path):
        """3 videos in pending / analyzing / analyzed mix; verify each
        card has correct ``findings`` presence/absence."""
        user_id = _make_user(db_path)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR600", 2005, db_path=db_path,
        )
        # video_repo.list_session_videos orders by created_at DESC, id
        # DESC — so video inserted last appears first. Insert in known
        # sequence so we can assert position-independent.
        v_pending = _make_video(
            db_path, sid, file_path="/tmp/v1.mp4",
        )
        v_analyzing = _make_video(
            db_path, sid, file_path="/tmp/v2.mp4",
        )
        update_analysis_state(v_analyzing, "analyzing", db_path=db_path)
        v_analyzed = _make_video(
            db_path, sid, file_path="/tmp/v3.mp4",
        )
        set_analysis_findings(
            v_analyzed, _sample_findings_payload(), db_path=db_path,
        )

        doc = build_session_report_doc(sid, user_id, db_path=db_path)
        videos_sec = _videos_section(doc)
        assert videos_sec is not None
        cards = videos_sec["videos"]
        assert len(cards) == 3

        # Index by video_id so list-order doesn't affect the assertion.
        by_id = {c["video_id"]: c for c in cards}
        assert by_id[v_pending]["analysis_state"] == "pending"
        assert "findings" not in by_id[v_pending]

        assert by_id[v_analyzing]["analysis_state"] == "analyzing"
        assert "findings" not in by_id[v_analyzing]

        assert by_id[v_analyzed]["analysis_state"] == "analyzed"
        assert "findings" in by_id[v_analyzed]

    def test_videos_section_per_video_required_fields(self, db_path):
        """Every video card has all required metadata fields per shape
        doc Variant 5 (regardless of analysis state)."""
        user_id = _make_user(db_path)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR600", 2005, db_path=db_path,
        )
        _make_video(db_path, sid)
        doc = build_session_report_doc(sid, user_id, db_path=db_path)
        videos_sec = _videos_section(doc)
        assert videos_sec is not None
        card = videos_sec["videos"][0]
        required = {
            "video_id", "filename", "captured_at",
            "duration_ms", "size_bytes", "interrupted",
            "analysis_state", "analyzing_started_at",
        }
        missing = required - set(card.keys())
        assert not missing, f"missing required fields: {missing}"
        # Spot-check derived field: filename is the file_path basename.
        assert card["filename"] == "recording-2026-05-05-1432.mp4"

    def test_videos_section_findings_shape_matches_visual_analysis_result(
        self, db_path,
    ):
        """Findings dict structurally matches
        ``VisualAnalysisResult.model_dump()`` — round-trippable back
        through the Pydantic model."""
        user_id = _make_user(db_path)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR600", 2005, db_path=db_path,
        )
        vid = _make_video(db_path, sid)
        set_analysis_findings(
            vid, _sample_findings_payload(), db_path=db_path,
        )
        doc = build_session_report_doc(sid, user_id, db_path=db_path)
        videos_sec = _videos_section(doc)
        card = videos_sec["videos"][0]
        # Round-trip through Pydantic — if the shape doesn't match the
        # model, this raises ValidationError.
        rehydrated = VisualAnalysisResult(**card["findings"])
        assert rehydrated.overall_assessment == (
            "Likely worn piston rings or valve seals."
        )
        assert rehydrated.frames_analyzed == 5
        assert len(rehydrated.findings) == 1


# ===========================================================================
# 2. Renderer extension smoke
# ===========================================================================


class TestVideosRenderers:

    def _doc_with_one_analyzed_video(self, db_path):
        user_id = _make_user(db_path)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR600", 2005, db_path=db_path,
        )
        vid = _make_video(db_path, sid)
        set_analysis_findings(
            vid, _sample_findings_payload(), db_path=db_path,
        )
        return build_session_report_doc(sid, user_id, db_path=db_path)

    def test_text_renderer_handles_videos_section(self, db_path):
        doc = self._doc_with_one_analyzed_video(db_path)
        out = TextReportRenderer().render(doc).decode("utf-8")
        # Heading + filename + analyzed-state surfaced in text body.
        assert "Videos" in out
        assert "Recording 1" in out
        assert "recording-2026-05-05-1432.mp4" in out
        assert "Analysis state: analyzed" in out
        # Findings nested block surfaces the overall assessment +
        # the finding's description.
        assert "Findings:" in out
        assert "Likely worn piston rings" in out
        assert "Blue smoke from exhaust" in out

    def test_text_renderer_skips_findings_when_absent(self, db_path):
        """Pending video renders metadata block but no Findings: block
        — exercises the ``if "findings" in video`` guard."""
        user_id = _make_user(db_path)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR600", 2005, db_path=db_path,
        )
        _make_video(db_path, sid)
        doc = build_session_report_doc(sid, user_id, db_path=db_path)
        out = TextReportRenderer().render(doc).decode("utf-8")
        assert "Recording 1" in out
        assert "Analysis state: pending" in out
        assert "Findings:" not in out

    @pytest.mark.skipif(
        not PDF_AVAILABLE, reason="reportlab not installed",
    )
    def test_pdf_renderer_handles_videos_section(self, db_path):
        doc = self._doc_with_one_analyzed_video(db_path)
        body = PdfReportRenderer().render(doc)
        # Smoke: PDF magic header + non-trivial body.
        assert body[:5] == b"%PDF-"
        assert len(body) > 500

    @pytest.mark.skipif(
        not PDF_AVAILABLE, reason="reportlab not installed",
    )
    def test_pdf_renderer_skips_findings_when_absent(self, db_path):
        """Video with analysis_state == 'pending' renders without
        finding-block; doesn't crash on missing ``findings`` key."""
        user_id = _make_user(db_path)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR600", 2005, db_path=db_path,
        )
        _make_video(db_path, sid)
        doc = build_session_report_doc(sid, user_id, db_path=db_path)
        body = PdfReportRenderer().render(doc)
        assert body[:5] == b"%PDF-"
        assert len(body) > 500
