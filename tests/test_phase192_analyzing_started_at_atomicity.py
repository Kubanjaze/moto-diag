"""Phase 192 Commit 1 (scope-add) — analyzing_started_at atomicity tests.

Verifies Contract B: the ``pending → analyzing`` state transition in
``motodiag.core.video_repo.update_analysis_state`` is performed by a
SINGLE atomic SQL UPDATE that writes BOTH ``analysis_state`` AND
``analyzing_started_at`` simultaneously. Two-statement implementations
are forbidden because they create a race window where the row sits in
``analyzing`` with ``analyzing_started_at IS NULL`` — indistinguishable
from a pre-migration row that the mobile-side stuck-detection
(Phase 192 Commit 3) surfaces immediately as stuck.

Test-shape inspiration: Phase 191B's ``test_phase191b_video_repo.py``
seeded video rows via ``create_video`` then exercised state transitions
via ``update_analysis_state`` and asserted observable post-state.
This suite extends that shape with:

  * post-transition value asserts (``analyzing_started_at`` is set).
  * SQL-tracing-based atomicity proof (single UPDATE statement fires).
  * non-clearing assertion across subsequent state transitions.
"""

# f9-allow-ssot-constants: fixture-data — this file IS the migration-040
# atomicity-contract test file; the ``"analyzing"`` literal is the
# domain-meaningful value being tested (matches VideoAnalysisState.
# ANALYZING.value but the literal is the contract surface). Importing
# the enum value would obscure the atomicity-when-target-is-analyzing
# contract.

from __future__ import annotations

import sqlite3
from typing import Optional

import pytest

from motodiag.core.database import get_connection, init_db
from motodiag.core.video_repo import (
    create_video,
    get_video,
    set_analysis_findings,
    update_analysis_state,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    """Fresh DB at SCHEMA_VERSION (>=40)."""
    path = str(tmp_path / "phase192_atomicity.db")
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


def _make_video(db_path, session_id: int) -> int:
    return create_video(
        session_id=session_id,
        file_path=f"/tmp/v_{session_id}.mp4",
        sha256="b" * 64,
        started_at="2026-05-05T14:32:18+00:00",
        duration_ms=15000,
        width=1920,
        height=1080,
        file_size_bytes=1_500_000,
        db_path=db_path,
    )


# ---------------------------------------------------------------------------
# 1. pending → analyzing sets the timestamp
# ---------------------------------------------------------------------------


class TestPendingToAnalyzingSetsTimestamp:

    def test_pending_to_analyzing_sets_timestamp(self, db):
        """After update_analysis_state(vid, 'analyzing'), the row must
        have analysis_state == 'analyzing' AND analyzing_started_at
        IS NOT NULL — both written in the same transition."""
        sid = _make_session(db)
        vid = _make_video(db, sid)

        # Sanity: pre-transition state is 'pending' with NULL timestamp.
        row = get_video(vid, db_path=db)
        assert row["analysis_state"] == "pending"
        assert row["analyzing_started_at"] is None

        # Transition.
        assert update_analysis_state(
            vid, "analyzing", db_path=db,
        ) is True

        # Post-transition: state advanced AND timestamp set.
        row = get_video(vid, db_path=db)
        assert row["analysis_state"] == "analyzing"
        assert row["analyzing_started_at"] is not None
        # Sanity-check format: looks like an ISO 8601 timestamp string.
        # _now_iso uses datetime.now(timezone.utc).isoformat() which
        # produces 'YYYY-MM-DDTHH:MM:SS.ffffff+00:00'.
        assert "T" in row["analyzing_started_at"]
        assert "+00:00" in row["analyzing_started_at"]

    def test_pending_to_analyzing_returns_true_on_success(self, db):
        sid = _make_session(db)
        vid = _make_video(db, sid)
        assert update_analysis_state(
            vid, "analyzing", db_path=db,
        ) is True

    def test_pending_to_analyzing_on_missing_video_returns_false(
        self, db,
    ):
        """No row updated → False; preserves the pre-Phase-192 contract
        from update_analysis_state."""
        assert update_analysis_state(
            99999, "analyzing", db_path=db,
        ) is False

    def test_pending_to_analyzing_on_soft_deleted_returns_false(self, db):
        """Soft-deleted rows are excluded from the WHERE clause —
        update_analysis_state silently no-ops (returns False) and does
        NOT resurrect the row by setting analyzing_started_at."""
        from motodiag.core.video_repo import soft_delete_video

        sid = _make_session(db)
        vid = _make_video(db, sid)
        soft_delete_video(vid, db_path=db)

        assert update_analysis_state(
            vid, "analyzing", db_path=db,
        ) is False

        # Direct read (bypassing get_video's soft-delete filter): the
        # column should still be NULL, AND analysis_state should still
        # be 'pending'. Soft-deleted rows are immutable from the
        # state-transition path.
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT analysis_state, analyzing_started_at "
                "FROM videos WHERE id = ?",
                (vid,),
            ).fetchone()
        assert row is not None
        assert row[0] == "pending"
        assert row[1] is None


# ---------------------------------------------------------------------------
# 2. Atomicity proof — single SQL UPDATE statement, both columns set
# ---------------------------------------------------------------------------


class TestPendingToAnalyzingAtomicSingleUpdate:

    def test_pending_to_analyzing_atomic_single_update(self, db):
        """Patch sqlite3.Connection.execute to record every SQL call
        during the transition; assert exactly ONE UPDATE statement
        fires that mentions BOTH analysis_state AND
        analyzing_started_at in the SET clause.

        Contract B forbids two-statement implementations. This test
        catches a regression where someone splits the UPDATE into
        ``UPDATE state`` followed by ``UPDATE timestamp`` (which would
        create a race window indistinguishable from a pre-migration
        row).
        """
        sid = _make_session(db)
        vid = _make_video(db, sid)

        # Capture all SQL executed on connections opened during the
        # transition. Python 3.13's sqlite3.Connection is immutable, so
        # we can't monkey-patch .execute directly — use the supported
        # set_trace_callback path via wrapping sqlite3.connect.
        captured: list[str] = []
        original_connect = sqlite3.connect

        def tracing_connect(*args, **kwargs):
            conn = original_connect(*args, **kwargs)
            conn.set_trace_callback(lambda sql: captured.append(sql))
            return conn

        sqlite3.connect = tracing_connect  # type: ignore[assignment]
        try:
            update_analysis_state(vid, "analyzing", db_path=db)
        finally:
            sqlite3.connect = original_connect  # type: ignore[assignment]

        # Find UPDATE statements that touch the videos table.
        update_stmts = [
            s for s in captured
            if "UPDATE VIDEOS" in s.upper().replace("\n", " ")
        ]

        # Contract B: exactly ONE UPDATE statement against videos
        # during the transition (no splitting).
        assert len(update_stmts) == 1, (
            f"expected single UPDATE, got {len(update_stmts)}: "
            f"{update_stmts!r}"
        )

        # That single UPDATE must mention BOTH columns in the SET clause.
        stmt = update_stmts[0]
        assert "analysis_state" in stmt, (
            f"UPDATE missing analysis_state: {stmt!r}"
        )
        assert "analyzing_started_at" in stmt, (
            f"UPDATE missing analyzing_started_at: {stmt!r}"
        )

    def test_non_analyzing_transitions_do_not_touch_timestamp_column(
        self, db,
    ):
        """Transitions to states OTHER than 'analyzing' must remain
        single-column UPDATEs (not touching analyzing_started_at).
        This preserves the existing column value across
        ``analyzing → analyzed`` / ``analyzing → analysis_failed``
        transitions for post-completion debugging.
        """
        sid = _make_session(db)
        vid = _make_video(db, sid)

        # First transition into analyzing (sets the timestamp).
        update_analysis_state(vid, "analyzing", db_path=db)

        # Capture transitions OUT of analyzing via set_trace_callback
        # (Python 3.13 sqlite3.Connection is immutable; can't patch
        # .execute directly).
        captured: list[str] = []
        original_connect = sqlite3.connect

        def tracing_connect(*args, **kwargs):
            conn = original_connect(*args, **kwargs)
            conn.set_trace_callback(lambda sql: captured.append(sql))
            return conn

        sqlite3.connect = tracing_connect  # type: ignore[assignment]
        try:
            # Transition to analysis_failed (the typical retryable
            # terminal state from the worker error paths).
            update_analysis_state(
                vid, "analysis_failed", db_path=db,
            )
        finally:
            sqlite3.connect = original_connect  # type: ignore[assignment]

        update_stmts = [
            s for s in captured
            if "UPDATE VIDEOS" in s.upper().replace("\n", " ")
        ]
        assert len(update_stmts) == 1
        stmt = update_stmts[0]
        # Single-column UPDATE — analyzing_started_at MUST NOT appear.
        assert "analysis_state" in stmt
        assert "analyzing_started_at" not in stmt, (
            f"non-analyzing transition should not touch "
            f"analyzing_started_at: {stmt!r}"
        )


# ---------------------------------------------------------------------------
# 3. analyzing → analyzed preserves the timestamp (post-completion debug)
# ---------------------------------------------------------------------------


class TestAnalyzingToAnalyzedDoesNotClearTimestamp:

    def test_analyzing_to_analyzed_preserves_timestamp(self, db):
        """When the worker completes analysis (transition
        analyzing → analyzed via set_analysis_findings),
        analyzing_started_at must NOT be cleared. Useful for
        post-completion debugging — diagnosing why a video took
        unexpectedly long to analyze requires the start timestamp
        even after the analyzed_at end timestamp is recorded.
        """
        sid = _make_session(db)
        vid = _make_video(db, sid)

        # pending → analyzing (sets analyzing_started_at).
        update_analysis_state(vid, "analyzing", db_path=db)
        before = get_video(vid, db_path=db)
        analyzing_ts_before = before["analyzing_started_at"]
        assert analyzing_ts_before is not None

        # analyzing → analyzed (via set_analysis_findings).
        findings = {
            "findings": [],
            "overall_assessment": "looks fine",
            "suggested_diagnostics": [],
            "image_quality_note": "",
        }
        set_analysis_findings(vid, findings, db_path=db)

        after = get_video(vid, db_path=db)
        assert after["analysis_state"] == "analyzed"
        assert after["analyzed_at"] is not None
        # Critical: analyzing_started_at preserved (NOT nulled out).
        assert after["analyzing_started_at"] == analyzing_ts_before

    def test_analyzing_to_failed_preserves_timestamp(self, db):
        """Same preservation guarantee for the failed-path transition
        (analyzing → analysis_failed). The timestamp is useful for
        diagnosing how long a doomed analysis took before failing."""
        sid = _make_session(db)
        vid = _make_video(db, sid)

        update_analysis_state(vid, "analyzing", db_path=db)
        before = get_video(vid, db_path=db)
        analyzing_ts_before = before["analyzing_started_at"]
        assert analyzing_ts_before is not None

        update_analysis_state(vid, "analysis_failed", db_path=db)

        after = get_video(vid, db_path=db)
        assert after["analysis_state"] == "analysis_failed"
        assert after["analyzing_started_at"] == analyzing_ts_before

    def test_analyzing_to_unsupported_preserves_timestamp(self, db):
        """Same guarantee for the unsupported terminal transition."""
        sid = _make_session(db)
        vid = _make_video(db, sid)

        update_analysis_state(vid, "analyzing", db_path=db)
        before = get_video(vid, db_path=db)
        analyzing_ts_before = before["analyzing_started_at"]

        update_analysis_state(vid, "unsupported", db_path=db)

        after = get_video(vid, db_path=db)
        assert after["analysis_state"] == "unsupported"
        assert after["analyzing_started_at"] == analyzing_ts_before


# ---------------------------------------------------------------------------
# 4. Re-entering analyzing (e.g., retry path) refreshes the timestamp
# ---------------------------------------------------------------------------


class TestReentryRefreshesTimestamp:

    def test_re_transition_to_analyzing_refreshes_timestamp(self, db):
        """If a row transitions analyzing → analysis_failed → analyzing
        (e.g., Phase 192+ retry-analysis admin endpoint), the second
        analyzing transition refreshes analyzing_started_at to the new
        attempt's start time. Stuck-detection is meaningful only for
        the CURRENT analyzing attempt, not the original first attempt.
        """
        import time

        sid = _make_session(db)
        vid = _make_video(db, sid)

        update_analysis_state(vid, "analyzing", db_path=db)
        first = get_video(vid, db_path=db)["analyzing_started_at"]
        assert first is not None

        update_analysis_state(vid, "analysis_failed", db_path=db)

        # Brief sleep to ensure the second timestamp differs (the
        # microsecond resolution of datetime.utcnow.isoformat is fine
        # for the assertion, but on very fast machines two adjacent
        # calls can produce the same string).
        time.sleep(0.01)

        update_analysis_state(vid, "analyzing", db_path=db)
        second = get_video(vid, db_path=db)["analyzing_started_at"]

        assert second is not None
        assert second != first, (
            "re-entry into analyzing should refresh the timestamp; "
            f"first={first!r} second={second!r}"
        )
