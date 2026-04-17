"""Phase 119 — Photo annotation layer tests.

Tests cover:
- Migration 012 creates photo_annotations table + 3 indexes
- AnnotationShape enum (4 members)
- PhotoAnnotation model validation (coords, hex color, size bounds)
- CRUD round trips
- list_annotations_for_image and list_annotations_for_failure_photo
- bulk_import_annotations
- FK CASCADE: deleting failure_photo deletes its annotations
- Orphan annotations (image_ref only) survive failure_photo delete
- created_by_user_id defaults to system user (id=1)
- Rollback drops table
- Forward-compat schema version (>= 12)
"""

import pytest
from pydantic import ValidationError

from motodiag.core.database import (
    init_db, get_schema_version, SCHEMA_VERSION, get_connection,
)
from motodiag.core.migrations import (
    get_migration_by_version, rollback_migration,
)
from motodiag.media import (
    AnnotationShape, PhotoAnnotation,
    add_annotation, get_annotation,
    list_annotations_for_image, list_annotations_for_failure_photo,
    count_annotations_for_image,
    update_annotation, delete_annotation, bulk_import_annotations,
)
from motodiag.reference import add_photo, FailurePhoto, FailureCategory


# --- Migration 012 ---


class TestMigration012:
    def test_migration_exists(self):
        m = get_migration_by_version(12)
        assert m is not None
        assert "photo_annotations" in m.upgrade_sql.lower()

    def test_table_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='photo_annotations'"
            )
            assert cursor.fetchone() is not None

    def test_indexes_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_photo_ann%'"
            )
            names = {row[0] for row in cursor.fetchall()}
        for expected in ("idx_photo_ann_image", "idx_photo_ann_photo", "idx_photo_ann_user"):
            assert expected in names

    def test_rollback(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        m = get_migration_by_version(12)
        rollback_migration(m, db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='photo_annotations'"
            )
            assert cursor.fetchone() is None


# --- Enums and models ---


class TestEnumAndModel:
    def test_shape_has_4(self):
        assert len(AnnotationShape) == 4
        assert {s.value for s in AnnotationShape} == {"circle", "rectangle", "arrow", "text"}

    def test_valid_annotation(self):
        a = PhotoAnnotation(
            image_ref="/photos/stator.jpg",
            shape=AnnotationShape.CIRCLE,
            x=0.3, y=0.5, width=0.1, height=0.1,
            color="#ff0000",
        )
        assert a.color == "#FF0000"  # validator upper-cases

    def test_invalid_coord_rejected(self):
        with pytest.raises(ValidationError):
            PhotoAnnotation(
                image_ref="/i", shape=AnnotationShape.RECTANGLE,
                x=1.5, y=0.5,  # x > 1.0
            )

    def test_invalid_color_rejected(self):
        with pytest.raises(ValidationError):
            PhotoAnnotation(
                image_ref="/i", shape=AnnotationShape.CIRCLE,
                x=0.5, y=0.5, color="red",
            )

    def test_invalid_size_rejected(self):
        with pytest.raises(ValidationError):
            PhotoAnnotation(
                image_ref="/i", shape=AnnotationShape.RECTANGLE,
                x=0.1, y=0.1, width=1.5, height=0.2,
            )

    def test_negative_arrow_ok(self):
        # Arrows can have negative width/height to point up/left
        a = PhotoAnnotation(
            image_ref="/i", shape=AnnotationShape.ARROW,
            x=0.5, y=0.5, width=-0.3, height=-0.2,
        )
        assert a.width == -0.3


# --- CRUD ---


class TestCRUD:
    def test_add_and_get(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        aid = add_annotation(PhotoAnnotation(
            image_ref="/photos/stator.jpg",
            shape=AnnotationShape.CIRCLE,
            x=0.3, y=0.5, width=0.15, height=0.15,
            color="#FF0000",
            label="Burnt winding",
        ), db)
        row = get_annotation(aid, db)
        assert row["shape"] == "circle"
        assert row["label"] == "Burnt winding"

    def test_defaults_system_user(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        aid = add_annotation(PhotoAnnotation(
            image_ref="/i", shape=AnnotationShape.TEXT,
            x=0.1, y=0.1, text="See manual p.42",
        ), db)
        assert get_annotation(aid, db)["created_by_user_id"] == 1

    def test_list_for_image(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        for i in range(3):
            add_annotation(PhotoAnnotation(
                image_ref="/i", shape=AnnotationShape.CIRCLE,
                x=0.1 * i, y=0.2,
            ), db)
        add_annotation(PhotoAnnotation(
            image_ref="/other", shape=AnnotationShape.CIRCLE,
            x=0.5, y=0.5,
        ), db)
        rows = list_annotations_for_image("/i", db)
        assert len(rows) == 3

    def test_count(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        for _ in range(4):
            add_annotation(PhotoAnnotation(
                image_ref="/i", shape=AnnotationShape.CIRCLE, x=0.1, y=0.1,
            ), db)
        assert count_annotations_for_image("/i", db) == 4
        assert count_annotations_for_image("/none", db) == 0

    def test_update(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        aid = add_annotation(PhotoAnnotation(
            image_ref="/i", shape=AnnotationShape.CIRCLE,
            x=0.1, y=0.1, label="Orig",
        ), db)
        assert update_annotation(aid, db_path=db, label="Updated",
                                 shape=AnnotationShape.RECTANGLE)
        row = get_annotation(aid, db)
        assert row["label"] == "Updated"
        assert row["shape"] == "rectangle"

    def test_delete(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        aid = add_annotation(PhotoAnnotation(
            image_ref="/i", shape=AnnotationShape.CIRCLE, x=0.1, y=0.1,
        ), db)
        assert delete_annotation(aid, db)
        assert get_annotation(aid, db) is None

    def test_bulk_import(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        anns = [
            PhotoAnnotation(
                image_ref="/i", shape=AnnotationShape.CIRCLE,
                x=0.1 * i, y=0.2, label=f"Mark {i}",
            )
            for i in range(1, 6)
        ]
        count = bulk_import_annotations(anns, db)
        assert count == 5
        assert count_annotations_for_image("/i", db) == 5


# --- FK cascade + orphan handling ---


class TestCascade:
    def test_cascade_on_failure_photo_delete(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        pid = add_photo(FailurePhoto(
            title="Stator", failure_category=FailureCategory.ELECTRICAL_FAILURE,
            image_ref="/photos/stator.jpg",
        ), db)
        aid = add_annotation(PhotoAnnotation(
            image_ref="/photos/stator.jpg", failure_photo_id=pid,
            shape=AnnotationShape.CIRCLE, x=0.3, y=0.5,
        ), db)
        assert list_annotations_for_failure_photo(pid, db)

        with get_connection(db) as conn:
            conn.execute("DELETE FROM failure_photos WHERE id = ?", (pid,))

        assert get_annotation(aid, db) is None

    def test_orphan_annotation_survives(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        pid = add_photo(FailurePhoto(
            title="x", failure_category=FailureCategory.OTHER,
            image_ref="/photos/standalone.jpg",
        ), db)
        # Orphan annotation has image_ref but no failure_photo_id
        aid = add_annotation(PhotoAnnotation(
            image_ref="/photos/standalone.jpg",  # same ref but no FK
            shape=AnnotationShape.RECTANGLE,
            x=0.1, y=0.1, width=0.2, height=0.2,
        ), db)
        with get_connection(db) as conn:
            conn.execute("DELETE FROM failure_photos WHERE id = ?", (pid,))
        # Orphan annotation survives because failure_photo_id was NULL
        assert get_annotation(aid, db) is not None

    def test_list_for_failure_photo_filters(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        pid = add_photo(FailurePhoto(
            title="x", failure_category=FailureCategory.OTHER,
            image_ref="/p.jpg",
        ), db)
        # 2 FK-linked, 1 orphan
        add_annotation(PhotoAnnotation(
            image_ref="/p.jpg", failure_photo_id=pid,
            shape=AnnotationShape.CIRCLE, x=0.1, y=0.1,
        ), db)
        add_annotation(PhotoAnnotation(
            image_ref="/p.jpg", failure_photo_id=pid,
            shape=AnnotationShape.ARROW, x=0.5, y=0.5, width=0.1, height=0.0,
        ), db)
        add_annotation(PhotoAnnotation(
            image_ref="/p.jpg",  # no FK
            shape=AnnotationShape.TEXT, x=0.2, y=0.2, text="Note",
        ), db)
        fk_linked = list_annotations_for_failure_photo(pid, db)
        assert len(fk_linked) == 2
        all_by_image = list_annotations_for_image("/p.jpg", db)
        assert len(all_by_image) == 3


# --- Forward compat ---


class TestSchemaVersionForwardCompat:
    def test_schema_version_at_least_12(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_schema_version(db) >= 12

    def test_schema_version_constant_at_least_12(self):
        assert SCHEMA_VERSION >= 12
