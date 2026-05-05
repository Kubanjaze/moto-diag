"""Phase 192 Commit 1 (scope-add) — Migration 040 (videos.analyzing_started_at) tests.

Mirrors the test shape of ``tests/test_phase191b_migration_039.py``: schema
apply + rollback, column shape, idempotency, plus the migration-040-specific
nullability contract (existing rows from Phase 191B stay with
``analyzing_started_at IS NULL`` after the migration — NO BACKFILL).

Why migration 040 exists: Phase 192 Section D needs to compute stuck-
duration for each video whose ``analysis_state == 'analyzing'`` to power
the mobile diagnostic-report viewer's stuck-in-analyzing surface
(5-min threshold per plan v1.0.1). The column is added as a separate
migration rather than retrofitting migration 039 because migration 039
is sealed history (Phase 191B already shipped).
"""

# f9-allow-ssot-constants: fixture-data — this file IS the migration-040
# test file, so the literal `40` (and adjacent boundary literals like 39)
# are deliberately fixture-meaningful. The whole file's purpose is
# "verify migration 040 applies / rolls back / behaves at the v39↔v40
# boundary"; replacing those literals with imports from
# motodiag.core.database.SCHEMA_VERSION would be tautological (the test
# would assert the SSOT against itself, which is exactly the F9 anti-
# pattern in reverse). Phase 191D 5b: file-level fixture-data opt-out
# is more accurate for this file's nature than the contract-pin opt-out.

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
    """Fresh DB at SCHEMA_VERSION (>=40)."""
    path = str(tmp_path / "phase192_m040.db")
    init_db(path)
    return path


def _insert_session(db_path) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO diagnostic_sessions
               (vehicle_make, vehicle_model, vehicle_year, status)
               VALUES (?, ?, ?, 'open')""",
            ("Honda", "CBR600", 2005),
        )
        return int(cursor.lastrowid)


def _insert_video_at_v39_shape(db_path, session_id: int) -> int:
    """Insert a video row using ONLY the columns that existed at
    migration 039's shape. Used to seed pre-migration-040 rows for the
    nullability contract test — even after migration 040 lands, this
    insert path produces a row with ``analyzing_started_at IS NULL``.
    """
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


# ---------------------------------------------------------------------------
# 1. Schema version + apply
# ---------------------------------------------------------------------------


class TestSchemaVersionAndRegistry:

    def test_schema_version_bumped_to_40(self, db):
        """SCHEMA_VERSION constant matches migration 040's version."""
        assert SCHEMA_VERSION == 40

    def test_get_current_version_at_least_40(self, db):
        assert get_current_version(db) >= 40

    def test_migration_040_in_registry(self):
        versions = {m.version for m in MIGRATIONS}
        assert 40 in versions
        v40 = next(m for m in MIGRATIONS if m.version == 40)
        assert v40.name == "videos_analyzing_started_at"
        assert v40.rollback_sql.strip()  # non-empty rollback


# ---------------------------------------------------------------------------
# 2. Column shape (additive, nullable, no default)
# ---------------------------------------------------------------------------


class TestMigration040AddsColumn:

    def test_migration_040_adds_column(self, db):
        """``analyzing_started_at`` exists in the videos table after migration."""
        with get_connection(db) as conn:
            cols = {
                r[1]
                for r in conn.execute(
                    "PRAGMA table_info(videos)"
                ).fetchall()
            }
        assert "analyzing_started_at" in cols

    def test_analyzing_started_at_is_nullable(self, db):
        """Column added with NO NOT NULL constraint per Contract A."""
        with get_connection(db) as conn:
            rows = conn.execute("PRAGMA table_info(videos)").fetchall()
        notnull_map = {r[1]: r[3] for r in rows}  # name → notnull flag
        assert notnull_map["analyzing_started_at"] == 0

    def test_analyzing_started_at_has_no_default(self, db):
        """Column added with NO DEFAULT value per Contract A — fresh
        inserts that don't supply the column get NULL, not a synthetic
        backfill value."""
        with get_connection(db) as conn:
            rows = conn.execute("PRAGMA table_info(videos)").fetchall()
        defaults = {r[1]: r[4] for r in rows}
        assert defaults["analyzing_started_at"] is None


# ---------------------------------------------------------------------------
# 3. Nullability contract — pre-migration rows stay NULL (no backfill)
# ---------------------------------------------------------------------------


class TestPreMigrationRowsStayNull:

    def test_existing_video_row_has_null_analyzing_started_at_after_migration(
        self, tmp_path,
    ):
        """Insert a video row, roll back to v39, re-apply migration 040;
        verify the existing row still has ``analyzing_started_at IS NULL``.
        Simulates the production scenario where Phase 191B shipped first
        and migration 040 lands later — pre-existing rows stay NULL per
        Contract A (no backfill)."""
        path = str(tmp_path / "preexisting.db")
        init_db(path)

        # Seed a video row at the v40 schema (column already exists).
        sid = _insert_session(path)
        vid = _insert_video_at_v39_shape(path, sid)

        # Roll back the migration (drops the column).
        rollback_to_version(39, path)
        # Re-apply migration 040 (re-adds the column NULL).
        applied = apply_pending_migrations(path)
        assert 40 in applied

        # Pre-existing row's analyzing_started_at should be NULL.
        with get_connection(path) as conn:
            row = conn.execute(
                "SELECT analyzing_started_at FROM videos WHERE id = ?",
                (vid,),
            ).fetchone()
        assert row is not None
        assert row[0] is None

    def test_other_columns_preserved_after_migration_re_apply(
        self, tmp_path,
    ):
        """Re-applying migration 040 to a DB with existing rows must
        preserve all other column values (only adds the new column).
        Defends against accidental table-recreate that drops data."""
        path = str(tmp_path / "preserve.db")
        init_db(path)
        sid = _insert_session(path)
        vid = _insert_video_at_v39_shape(path, sid)

        # Roll back + re-apply.
        rollback_to_version(39, path)
        apply_pending_migrations(path)

        with get_connection(path) as conn:
            row = conn.execute(
                "SELECT id, session_id, file_size_bytes, sha256 "
                "FROM videos WHERE id = ?",
                (vid,),
            ).fetchone()
        assert row is not None
        assert row[0] == vid
        assert row[1] == sid
        assert row[2] == 1_500_000
        assert row[3] == "a" * 64


# ---------------------------------------------------------------------------
# 4. Rollback (40 → 39) drops column; existing rows otherwise preserved
# ---------------------------------------------------------------------------


class TestMigration040Rollback:

    def test_rollback_drops_column(self, tmp_path):
        path = str(tmp_path / "rb.db")
        init_db(path)

        # Sanity: column present at v40.
        with get_connection(path) as conn:
            cols = {
                r[1]
                for r in conn.execute(
                    "PRAGMA table_info(videos)"
                ).fetchall()
            }
        assert "analyzing_started_at" in cols

        rollback_to_version(39, path)

        with get_connection(path) as conn:
            cols = {
                r[1]
                for r in conn.execute(
                    "PRAGMA table_info(videos)"
                ).fetchall()
            }
        assert "analyzing_started_at" not in cols
        # Videos table itself still exists (only the column was dropped).
        assert table_exists("videos", path) is True

    def test_rollback_preserves_existing_rows_otherwise(self, tmp_path):
        """Rollback uses the rename-recreate pattern (SQLite pre-3.35
        can't DROP COLUMN); existing rows must round-trip through the
        recreate with all other columns intact."""
        path = str(tmp_path / "rb_data.db")
        init_db(path)
        sid = _insert_session(path)
        vid = _insert_video_at_v39_shape(path, sid)

        rollback_to_version(39, path)

        with get_connection(path) as conn:
            row = conn.execute(
                "SELECT id, session_id, file_size_bytes, sha256 "
                "FROM videos WHERE id = ?",
                (vid,),
            ).fetchone()
        assert row is not None
        assert row[0] == vid
        assert row[1] == sid
        assert row[2] == 1_500_000
        assert row[3] == "a" * 64

    def test_rollback_then_reapply(self, tmp_path):
        path = str(tmp_path / "rb_reapply.db")
        init_db(path)
        rollback_to_version(39, path)

        with get_connection(path) as conn:
            cols = {
                r[1]
                for r in conn.execute(
                    "PRAGMA table_info(videos)"
                ).fetchall()
            }
        assert "analyzing_started_at" not in cols

        applied = apply_pending_migrations(path)
        assert 40 in applied

        with get_connection(path) as conn:
            cols = {
                r[1]
                for r in conn.execute(
                    "PRAGMA table_info(videos)"
                ).fetchall()
            }
        assert "analyzing_started_at" in cols

    def test_rollback_preserves_indexes(self, tmp_path):
        """The rename-recreate rollback recreates the v39 indexes;
        verify they're present after rollback."""
        path = str(tmp_path / "rb_idx.db")
        init_db(path)
        rollback_to_version(39, path)

        with get_connection(path) as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='index' AND tbl_name='videos'"
                ).fetchall()
            }
        # All three Phase 191B indexes should be back.
        assert "idx_videos_session" in names
        assert "idx_videos_analysis_state" in names
        assert "idx_videos_sha256" in names


# ---------------------------------------------------------------------------
# 5. Idempotent apply (re-running apply_pending_migrations is a no-op)
# ---------------------------------------------------------------------------


class TestMigration040Idempotent:

    def test_migration_040_idempotent_apply(self, db):
        """Already at SCHEMA_VERSION; re-applying should be a no-op
        (returns empty list, schema version unchanged)."""
        applied = apply_pending_migrations(db)
        assert applied == []
        assert get_current_version(db) >= 40

    def test_apply_pending_twice_does_not_duplicate(self, db):
        """Calling apply_pending_migrations twice in a row must not
        re-run migration 040 (which would fail with a duplicate-column
        error from SQLite)."""
        # First call: nothing to do (db fixture already at v40).
        apply_pending_migrations(db)
        # Second call: also nothing to do.
        apply_pending_migrations(db)
        # Column still present.
        with get_connection(db) as conn:
            cols = {
                r[1]
                for r in conn.execute(
                    "PRAGMA table_info(videos)"
                ).fetchall()
            }
        assert "analyzing_started_at" in cols
