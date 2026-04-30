"""Phase 191B — Migration 039 (videos table) tests.

Covers schema apply + rollback, cascade-delete from diagnostic_sessions,
column shapes/defaults, index presence, and idempotency of
``apply_pending_migrations``.

The FK target is ``diagnostic_sessions(id)`` (the canonical session
table in this codebase). Plan v1.0.1 documents this — the v1.0 plan's
``sessions`` shorthand maps to the actual table name.
"""

from __future__ import annotations

import pytest

from motodiag.core.database import (
    SCHEMA_VERSION,
    get_connection,
    init_db,
    table_exists,
)
from motodiag.core.migrations import (
    MIGRATIONS,
    apply_pending_migrations,
    get_current_version,
    rollback_to_version,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    """Fresh DB at SCHEMA_VERSION (>=39)."""
    path = str(tmp_path / "phase191b.db")
    init_db(path)
    return path


# ---------------------------------------------------------------------------
# 1. Schema version + apply
# ---------------------------------------------------------------------------


class TestMigration039Apply:

    def test_schema_version_at_least_39(self, db):
        assert SCHEMA_VERSION >= 39

    def test_get_current_version_returns_at_least_39(self, db):
        assert get_current_version(db) >= 39

    def test_videos_table_exists(self, db):
        assert table_exists("videos", db) is True

    def test_apply_pending_idempotent(self, db):
        # Already at SCHEMA_VERSION; re-applying should be a no-op.
        applied = apply_pending_migrations(db)
        assert applied == []
        # Schema version unchanged.
        assert get_current_version(db) >= 39

    def test_migration_039_in_registry(self):
        versions = {m.version for m in MIGRATIONS}
        assert 39 in versions
        v39 = next(m for m in MIGRATIONS if m.version == 39)
        assert v39.name == "videos_table"
        assert v39.rollback_sql.strip()  # non-empty rollback


# ---------------------------------------------------------------------------
# 2. Column shape + defaults
# ---------------------------------------------------------------------------


class TestVideoTableColumns:

    EXPECTED_COLUMNS = {
        "id", "session_id", "started_at", "duration_ms",
        "width", "height", "file_size_bytes", "format",
        "codec", "interrupted", "file_path", "sha256",
        "upload_state", "analysis_state", "analysis_findings",
        "analyzed_at", "created_at", "deleted_at",
    }

    def test_all_expected_columns_present(self, db):
        with get_connection(db) as conn:
            cols = {
                r[1]
                for r in conn.execute(
                    "PRAGMA table_info(videos)"
                ).fetchall()
            }
        assert self.EXPECTED_COLUMNS.issubset(cols)

    def test_session_id_not_null(self, db):
        with get_connection(db) as conn:
            rows = conn.execute("PRAGMA table_info(videos)").fetchall()
        notnull_map = {r[1]: r[3] for r in rows}  # name → notnull flag
        assert notnull_map["session_id"] == 1

    def test_default_format_is_mp4(self, db):
        with get_connection(db) as conn:
            rows = conn.execute("PRAGMA table_info(videos)").fetchall()
        defaults = {r[1]: r[4] for r in rows}
        # Default values come back as the SQL literal as text.
        assert "'mp4'" in (defaults["format"] or "")

    def test_default_analysis_state_is_pending(self, db):
        with get_connection(db) as conn:
            rows = conn.execute("PRAGMA table_info(videos)").fetchall()
        defaults = {r[1]: r[4] for r in rows}
        assert "'pending'" in (defaults["analysis_state"] or "")


# ---------------------------------------------------------------------------
# 3. Indexes
# ---------------------------------------------------------------------------


class TestVideoIndexes:

    def test_idx_videos_session_present(self, db):
        with get_connection(db) as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='index' AND tbl_name='videos'"
                ).fetchall()
            }
        assert "idx_videos_session" in names

    def test_idx_videos_analysis_state_present(self, db):
        with get_connection(db) as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='index' AND tbl_name='videos'"
                ).fetchall()
            }
        assert "idx_videos_analysis_state" in names

    def test_idx_videos_sha256_present(self, db):
        with get_connection(db) as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='index' AND tbl_name='videos'"
                ).fetchall()
            }
        assert "idx_videos_sha256" in names


# ---------------------------------------------------------------------------
# 4. Rollback (39 → 38) and re-apply
# ---------------------------------------------------------------------------


class TestMigration039Rollback:

    def test_rollback_drops_videos_table(self, tmp_path):
        path = str(tmp_path / "rb.db")
        init_db(path)
        assert table_exists("videos", path) is True
        rollback_to_version(38, path)
        assert table_exists("videos", path) is False

    def test_rollback_then_reapply(self, tmp_path):
        path = str(tmp_path / "rb_reapply.db")
        init_db(path)
        rollback_to_version(38, path)
        assert table_exists("videos", path) is False
        applied = apply_pending_migrations(path)
        assert 39 in applied
        assert table_exists("videos", path) is True


# ---------------------------------------------------------------------------
# 5. Cascade delete from diagnostic_sessions
# ---------------------------------------------------------------------------


class TestCascadeDelete:

    def _insert_session(self, db_path) -> int:
        with get_connection(db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO diagnostic_sessions
                   (vehicle_make, vehicle_model, vehicle_year, status)
                   VALUES (?, ?, ?, 'open')""",
                ("Honda", "CBR600", 2005),
            )
            return int(cursor.lastrowid)

    def _insert_video(self, db_path, session_id: int) -> int:
        with get_connection(db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO videos (
                       session_id, started_at, duration_ms,
                       width, height, file_size_bytes,
                       file_path, sha256
                   )
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    "2026-04-29T12:00:00",
                    15000,
                    1920, 1080,
                    1_500_000,
                    f"/tmp/v_{session_id}.mp4",
                    "a" * 64,
                ),
            )
            return int(cursor.lastrowid)

    def test_delete_session_cascades_videos(self, db):
        sid = self._insert_session(db)
        vid = self._insert_video(db, sid)
        # Sanity: video exists.
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT * FROM videos WHERE id = ?", (vid,),
            ).fetchone()
        assert row is not None

        # Delete the session.
        with get_connection(db) as conn:
            conn.execute(
                "DELETE FROM diagnostic_sessions WHERE id = ?",
                (sid,),
            )

        # Video should be gone (cascade).
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT * FROM videos WHERE id = ?", (vid,),
            ).fetchone()
        assert row is None
