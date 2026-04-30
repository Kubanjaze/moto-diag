"""Phase 191B — Video repository tests.

CRUD + soft-delete + analysis-state transitions + quota math + owner-
aware variants. Mirrors the test shape used by Phase 177 vehicle repo
tests + Phase 178 session repo tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest

from motodiag.core.database import get_connection, init_db
from motodiag.core.video_repo import (
    VideoOwnershipError,
    count_bytes_in_session,
    count_videos_in_session,
    count_videos_this_month_for_owner,
    create_video,
    create_video_for_owner,
    get_video,
    get_video_for_owner,
    list_session_videos,
    list_session_videos_for_owner,
    set_analysis_findings,
    soft_delete_video,
    soft_delete_video_for_owner,
    update_analysis_state,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase191b_repo.db")
    init_db(path)
    return path


def _make_session(db_path, user_id: int = 1) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO diagnostic_sessions
               (vehicle_make, vehicle_model, vehicle_year,
                status, user_id)
               VALUES (?, ?, ?, 'open', ?)""",
            ("Honda", "CBR600", 2005, user_id),
        )
        return int(cursor.lastrowid)


def _make_video(
    db_path,
    session_id: int,
    *,
    sha_seed: str = "a",
    bytes: int = 1_000_000,
) -> int:
    return create_video(
        session_id=session_id,
        file_path=f"/tmp/v_{session_id}_{sha_seed}.mp4",
        sha256=sha_seed * 64,
        started_at="2026-04-29T12:00:00",
        duration_ms=15000,
        width=1920,
        height=1080,
        file_size_bytes=bytes,
        db_path=db_path,
    )


# ---------------------------------------------------------------------------
# 1. Core CRUD
# ---------------------------------------------------------------------------


class TestCoreCRUD:

    def test_create_returns_id(self, db):
        sid = _make_session(db)
        vid = _make_video(db, sid)
        assert isinstance(vid, int)
        assert vid > 0

    def test_get_returns_dict(self, db):
        sid = _make_session(db)
        vid = _make_video(db, sid)
        row = get_video(vid, db_path=db)
        assert row is not None
        assert row["id"] == vid
        assert row["session_id"] == sid
        assert row["analysis_state"] == "pending"
        assert row["upload_state"] == "uploaded"
        assert row["interrupted"] is False  # bool coerced

    def test_get_returns_none_when_missing(self, db):
        assert get_video(99999, db_path=db) is None

    def test_get_returns_none_when_soft_deleted(self, db):
        sid = _make_session(db)
        vid = _make_video(db, sid)
        soft_delete_video(vid, db_path=db)
        assert get_video(vid, db_path=db) is None

    def test_list_session_videos_orders_newest_first(self, db):
        sid = _make_session(db)
        v1 = _make_video(db, sid, sha_seed="a")
        v2 = _make_video(db, sid, sha_seed="b")
        v3 = _make_video(db, sid, sha_seed="c")
        rows = list_session_videos(sid, db_path=db)
        assert len(rows) == 3
        # Newest first: v3, v2, v1.
        assert [r["id"] for r in rows] == [v3, v2, v1]

    def test_list_excludes_soft_deleted(self, db):
        sid = _make_session(db)
        v1 = _make_video(db, sid, sha_seed="a")
        v2 = _make_video(db, sid, sha_seed="b")
        soft_delete_video(v1, db_path=db)
        rows = list_session_videos(sid, db_path=db)
        assert len(rows) == 1
        assert rows[0]["id"] == v2


# ---------------------------------------------------------------------------
# 2. Soft delete + state transitions
# ---------------------------------------------------------------------------


class TestSoftDeleteAndState:

    def test_soft_delete_returns_true_first_time(self, db):
        sid = _make_session(db)
        vid = _make_video(db, sid)
        assert soft_delete_video(vid, db_path=db) is True

    def test_soft_delete_idempotent_second_call(self, db):
        sid = _make_session(db)
        vid = _make_video(db, sid)
        soft_delete_video(vid, db_path=db)
        # Second call returns False (no row updated) — route still
        # returns 204 idempotently regardless.
        assert soft_delete_video(vid, db_path=db) is False

    def test_soft_delete_returns_false_for_missing(self, db):
        assert soft_delete_video(99999, db_path=db) is False

    def test_update_analysis_state(self, db):
        sid = _make_session(db)
        vid = _make_video(db, sid)
        assert update_analysis_state(vid, "analyzing", db_path=db) is True
        assert get_video(vid, db_path=db)["analysis_state"] == "analyzing"

    def test_set_analysis_findings_marks_analyzed(self, db):
        sid = _make_session(db)
        vid = _make_video(db, sid)
        findings = {
            "findings": [],
            "overall_assessment": "looks fine",
            "suggested_diagnostics": [],
            "image_quality_note": "",
        }
        assert set_analysis_findings(
            vid, findings,
            model_used="claude-sonnet-4-5-20241022",
            cost_usd=0.085,
            db_path=db,
        ) is True
        row = get_video(vid, db_path=db)
        assert row["analysis_state"] == "analyzed"
        assert row["analyzed_at"] is not None
        assert row["analysis_findings"] is not None
        assert row["analysis_findings"]["overall_assessment"] == "looks fine"
        # model_used + cost_estimate_usd were folded in.
        assert row["analysis_findings"]["model_used"] == \
            "claude-sonnet-4-5-20241022"
        assert row["analysis_findings"]["cost_estimate_usd"] == 0.085


# ---------------------------------------------------------------------------
# 3. Quota math
# ---------------------------------------------------------------------------


class TestQuotaMath:

    def test_count_videos_in_session_excludes_soft_deleted(self, db):
        sid = _make_session(db)
        v1 = _make_video(db, sid, sha_seed="a")
        _make_video(db, sid, sha_seed="b")
        _make_video(db, sid, sha_seed="c")
        assert count_videos_in_session(sid, db_path=db) == 3
        soft_delete_video(v1, db_path=db)
        assert count_videos_in_session(sid, db_path=db) == 2

    def test_count_bytes_in_session_sums_correctly(self, db):
        sid = _make_session(db)
        _make_video(db, sid, sha_seed="a", bytes=1_000_000)
        _make_video(db, sid, sha_seed="b", bytes=2_500_000)
        assert count_bytes_in_session(sid, db_path=db) == 3_500_000

    def test_count_bytes_excludes_soft_deleted(self, db):
        sid = _make_session(db)
        v1 = _make_video(db, sid, sha_seed="a", bytes=1_000_000)
        _make_video(db, sid, sha_seed="b", bytes=2_500_000)
        soft_delete_video(v1, db_path=db)
        assert count_bytes_in_session(sid, db_path=db) == 2_500_000

    def test_count_bytes_zero_for_empty_session(self, db):
        sid = _make_session(db)
        assert count_bytes_in_session(sid, db_path=db) == 0

    def test_monthly_count_for_owner(self, db):
        # Two sessions owned by user 7.
        sid1 = _make_session(db, user_id=7)
        sid2 = _make_session(db, user_id=7)
        # One session owned by user 9.
        sid3 = _make_session(db, user_id=9)
        _make_video(db, sid1, sha_seed="a")
        _make_video(db, sid2, sha_seed="b")
        _make_video(db, sid3, sha_seed="c")
        assert count_videos_this_month_for_owner(7, db_path=db) == 2
        assert count_videos_this_month_for_owner(9, db_path=db) == 1
        assert count_videos_this_month_for_owner(11, db_path=db) == 0

    def test_monthly_count_includes_soft_deleted(self, db):
        # Soft-deleted videos count toward the monthly aggregate
        # because the API call (and cost) already happened.
        sid = _make_session(db, user_id=7)
        v = _make_video(db, sid, sha_seed="a")
        soft_delete_video(v, db_path=db)
        assert count_videos_this_month_for_owner(7, db_path=db) == 1


# ---------------------------------------------------------------------------
# 4. Owner-aware variants
# ---------------------------------------------------------------------------


class TestOwnerVariants:

    def test_create_for_owner_happy(self, db):
        sid = _make_session(db, user_id=1)
        vid = create_video_for_owner(
            user_id=1,
            session_id=sid,
            file_path="/tmp/x.mp4",
            sha256="d" * 64,
            started_at="2026-04-29T12:00:00",
            duration_ms=15000,
            width=1920,
            height=1080,
            file_size_bytes=1_000_000,
            db_path=db,
        )
        assert vid is not None and vid > 0

    def test_create_for_owner_returns_none_when_session_missing(self, db):
        result = create_video_for_owner(
            user_id=1,
            session_id=99999,
            file_path="/tmp/x.mp4",
            sha256="d" * 64,
            started_at="2026-04-29T12:00:00",
            duration_ms=15000,
            width=1920,
            height=1080,
            file_size_bytes=1_000_000,
            db_path=db,
        )
        assert result is None

    def test_create_for_owner_raises_on_cross_owner(self, db):
        sid = _make_session(db, user_id=1)
        with pytest.raises(VideoOwnershipError):
            create_video_for_owner(
                user_id=2,
                session_id=sid,
                file_path="/tmp/x.mp4",
                sha256="d" * 64,
                started_at="2026-04-29T12:00:00",
                duration_ms=15000,
                width=1920,
                height=1080,
                file_size_bytes=1_000_000,
                db_path=db,
            )

    def test_get_for_owner_returns_none_when_cross_owner(self, db):
        sid = _make_session(db, user_id=1)
        vid = _make_video(db, sid)
        # User 2 cannot see user 1's video.
        assert get_video_for_owner(2, vid, db_path=db) is None

    def test_get_for_owner_returns_row_when_owner_matches(self, db):
        sid = _make_session(db, user_id=1)
        vid = _make_video(db, sid)
        row = get_video_for_owner(1, vid, db_path=db)
        assert row is not None and row["id"] == vid

    def test_list_for_owner_returns_none_when_session_missing(self, db):
        assert list_session_videos_for_owner(1, 99999, db_path=db) is None

    def test_list_for_owner_raises_on_cross_owner(self, db):
        sid = _make_session(db, user_id=1)
        with pytest.raises(VideoOwnershipError):
            list_session_videos_for_owner(2, sid, db_path=db)

    def test_list_for_owner_returns_videos_on_match(self, db):
        sid = _make_session(db, user_id=1)
        _make_video(db, sid, sha_seed="a")
        _make_video(db, sid, sha_seed="b")
        rows = list_session_videos_for_owner(1, sid, db_path=db)
        assert rows is not None
        assert len(rows) == 2

    def test_soft_delete_for_owner_happy(self, db):
        sid = _make_session(db, user_id=1)
        vid = _make_video(db, sid)
        assert soft_delete_video_for_owner(1, vid, db_path=db) is True
        assert get_video(vid, db_path=db) is None

    def test_soft_delete_for_owner_false_on_cross_owner(self, db):
        sid = _make_session(db, user_id=1)
        vid = _make_video(db, sid)
        # Cross-owner returns False without raising — DELETE
        # idempotency at the route level treats the video as
        # already-gone from the caller's perspective.
        assert soft_delete_video_for_owner(2, vid, db_path=db) is False
        # Original owner can still see it.
        assert get_video(vid, db_path=db) is not None
