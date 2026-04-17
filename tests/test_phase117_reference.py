"""Phase 117 — Reference data tables tests.

Tests cover:
- Migration 010 creates 4 tables + 8 indexes
- 4 enums (ManualSource, DiagramType, FailureCategory, SkillLevel) with correct counts
- CRUD round-trips for all 4 repos (manual, diagram, photo, video)
- Year-range filter: year_start <= target_year <= year_end, NULL = universal
- JSON columns (section_titles, topic_tags) round-trip correctly
- parts_diagrams.source_manual_id SET NULL when manual deleted
- failure_photos defaults submitted_by to system user (id=1)
- Rollback drops all 4 tables
- Forward-compat schema version (>= 10)
"""

import pytest

from motodiag.core.database import (
    init_db, get_schema_version, SCHEMA_VERSION, get_connection,
)
from motodiag.core.migrations import (
    get_migration_by_version, rollback_migration,
)
from motodiag.reference import (
    ManualSource, DiagramType, FailureCategory, SkillLevel,
    ManualReference, PartsDiagram, FailurePhoto, VideoTutorial,
    add_manual, get_manual, list_manuals, update_manual, delete_manual,
    add_diagram, get_diagram, list_diagrams, update_diagram, delete_diagram,
    add_photo, get_photo, list_photos, update_photo, delete_photo,
    add_video, get_video, list_videos, update_video, delete_video,
)


# --- Migration 010 ---


class TestMigration010:
    def test_migration_exists(self):
        m = get_migration_by_version(10)
        assert m is not None
        assert "manual_references" in m.upgrade_sql.lower()
        assert "parts_diagrams" in m.upgrade_sql.lower()
        assert "failure_photos" in m.upgrade_sql.lower()
        assert "video_tutorials" in m.upgrade_sql.lower()

    def test_all_4_tables_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        expected = {
            "manual_references", "parts_diagrams",
            "failure_photos", "video_tutorials",
        }
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                f"AND name IN ({','.join('?' * len(expected))})",
                tuple(expected),
            )
            tables = {row[0] for row in cursor.fetchall()}
        assert tables == expected

    def test_8_indexes_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND ("
                "name LIKE 'idx_manuals%' OR name LIKE 'idx_diagrams%' "
                "OR name LIKE 'idx_photos%' OR name LIKE 'idx_videos%')"
            )
            names = {row[0] for row in cursor.fetchall()}
        for expected in (
            "idx_manuals_make_model", "idx_manuals_source",
            "idx_diagrams_make_model", "idx_diagrams_type",
            "idx_photos_make_model", "idx_photos_category",
            "idx_videos_make_model", "idx_videos_source",
        ):
            assert expected in names

    def test_rollback_drops_all(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        m = get_migration_by_version(10)
        rollback_migration(m, db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
                "('manual_references','parts_diagrams','failure_photos','video_tutorials')"
            )
            assert cursor.fetchall() == []


# --- Enums ---


class TestEnums:
    def test_manual_source_5(self):
        assert len(ManualSource) == 5

    def test_diagram_type_4(self):
        assert len(DiagramType) == 4

    def test_failure_category_7(self):
        assert len(FailureCategory) == 7

    def test_skill_level_4(self):
        assert len(SkillLevel) == 4


# --- Manual CRUD ---


class TestManualCRUD:
    def test_add_and_get(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        m = ManualReference(
            source=ManualSource.CLYMER,
            title="Clymer Harley-Davidson Sportster 1986-2013",
            publisher="Clymer",
            isbn="978-1620923085",
            make="Harley-Davidson", model="Sportster",
            year_start=1986, year_end=2013,
            page_count=680,
            section_titles=["Engine", "Transmission", "Electrical"],
        )
        mid = add_manual(m, db)
        row = get_manual(mid, db)
        assert row["source"] == "clymer"
        assert row["year_start"] == 1986
        assert row["section_titles"] == ["Engine", "Transmission", "Electrical"]

    def test_list_by_target_year(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        add_manual(ManualReference(
            source=ManualSource.CLYMER, title="Sportster 86-13",
            make="Harley-Davidson", model="Sportster",
            year_start=1986, year_end=2013,
        ), db)
        add_manual(ManualReference(
            source=ManualSource.HAYNES, title="Honda CBR 2001",
            make="Honda", model="CBR929RR",
            year_start=2000, year_end=2001,
        ), db)
        results = list_manuals(target_year=2001, db_path=db)
        assert len(results) == 2
        # 2015 is out of range for Sportster and Honda
        results = list_manuals(target_year=2015, db_path=db)
        assert len(results) == 0

    def test_list_universal_year_null(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        add_manual(ManualReference(
            source=ManualSource.OEM, title="Universal troubleshooting guide",
        ), db)
        results = list_manuals(target_year=2025, db_path=db)
        assert len(results) == 1

    def test_update(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        mid = add_manual(ManualReference(
            source=ManualSource.CLYMER, title="Original",
        ), db)
        assert update_manual(mid, db_path=db, title="Updated") is True
        row = get_manual(mid, db)
        assert row["title"] == "Updated"

    def test_delete(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        mid = add_manual(ManualReference(
            source=ManualSource.CLYMER, title="Temp",
        ), db)
        assert delete_manual(mid, db) is True
        assert get_manual(mid, db) is None


# --- Diagram CRUD ---


class TestDiagramCRUD:
    def test_add_and_get(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        did = add_diagram(PartsDiagram(
            make="Honda", model="CBR929RR",
            year_start=2000, year_end=2001,
            diagram_type=DiagramType.EXPLODED_VIEW,
            section="Engine",
            title="Cylinder head exploded view",
            image_ref="/refs/cbr929/engine_head.png",
        ), db)
        row = get_diagram(did, db)
        assert row["diagram_type"] == "exploded_view"
        assert row["image_ref"] == "/refs/cbr929/engine_head.png"

    def test_source_manual_fk_set_null(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        mid = add_manual(ManualReference(
            source=ManualSource.CLYMER, title="Manual",
        ), db)
        did = add_diagram(PartsDiagram(
            diagram_type=DiagramType.SCHEMATIC, title="D", image_ref="/r",
            source_manual_id=mid,
        ), db)
        assert delete_manual(mid, db) is True
        row = get_diagram(did, db)
        assert row["source_manual_id"] is None

    def test_list_filters(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        for dt in (DiagramType.EXPLODED_VIEW, DiagramType.WIRING):
            add_diagram(PartsDiagram(
                make="Harley-Davidson", model="Sportster",
                year_start=2000, year_end=2010,
                diagram_type=dt, title=f"{dt.value}_d", image_ref="/r",
            ), db)
        exploded = list_diagrams(diagram_type=DiagramType.EXPLODED_VIEW, db_path=db)
        assert len(exploded) == 1

    def test_update_and_delete(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        did = add_diagram(PartsDiagram(
            diagram_type=DiagramType.WIRING, title="Orig", image_ref="/a",
        ), db)
        assert update_diagram(did, db_path=db, title="New") is True
        assert get_diagram(did, db)["title"] == "New"
        assert delete_diagram(did, db) is True
        assert get_diagram(did, db) is None


# --- Photo CRUD ---


class TestPhotoCRUD:
    def test_add_and_default_user(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        pid = add_photo(FailurePhoto(
            title="Burnt stator", failure_category=FailureCategory.ELECTRICAL_FAILURE,
            make="Harley-Davidson", image_ref="/photos/stator_burn.jpg",
        ), db)
        row = get_photo(pid, db)
        assert row["submitted_by_user_id"] == 1
        assert row["failure_category"] == "electrical_failure"

    def test_list_by_category(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        add_photo(FailurePhoto(
            title="A", failure_category=FailureCategory.CORROSION,
            image_ref="/r",
        ), db)
        add_photo(FailurePhoto(
            title="B", failure_category=FailureCategory.MECHANICAL_WEAR,
            image_ref="/r",
        ), db)
        rows = list_photos(failure_category=FailureCategory.CORROSION, db_path=db)
        assert len(rows) == 1
        assert rows[0]["title"] == "A"

    def test_list_by_make_year(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        add_photo(FailurePhoto(
            title="Old", failure_category=FailureCategory.CORROSION,
            make="Honda", year_start=2000, year_end=2005, image_ref="/r",
        ), db)
        add_photo(FailurePhoto(
            title="Newer", failure_category=FailureCategory.CORROSION,
            make="Honda", year_start=2010, year_end=2015, image_ref="/r",
        ), db)
        rows = list_photos(make="Honda", target_year=2003, db_path=db)
        assert len(rows) == 1
        assert rows[0]["title"] == "Old"

    def test_update_and_delete(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        pid = add_photo(FailurePhoto(
            title="Orig", failure_category=FailureCategory.CRASH_DAMAGE,
            image_ref="/r",
        ), db)
        assert update_photo(pid, db_path=db, title="Updated",
                            failure_category=FailureCategory.COSMETIC_DAMAGE) is True
        row = get_photo(pid, db)
        assert row["title"] == "Updated"
        assert row["failure_category"] == "cosmetic_damage"
        assert delete_photo(pid, db) is True


# --- Video CRUD ---


class TestVideoCRUD:
    def test_add_and_get_json(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        vid = add_video(VideoTutorial(
            title="Harley Sportster stator replacement",
            source="youtube",
            source_video_id="abc123xyz",
            url="https://youtube.com/watch?v=abc123xyz",
            duration_seconds=1230,
            make="Harley-Davidson", model="Sportster",
            year_start=1999, year_end=2017,
            skill_level=SkillLevel.INTERMEDIATE,
            topic_tags=["charging system", "stator", "electrical"],
        ), db)
        row = get_video(vid, db)
        assert row["source"] == "youtube"
        assert row["topic_tags"] == ["charging system", "stator", "electrical"]
        assert row["skill_level"] == "intermediate"

    def test_list_filter_by_topic(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        add_video(VideoTutorial(
            title="Stator video", source="youtube",
            topic_tags=["stator", "charging"],
        ), db)
        add_video(VideoTutorial(
            title="Brake video", source="youtube",
            topic_tags=["brakes", "hydraulics"],
        ), db)
        rows = list_videos(topic="stator", db_path=db)
        assert len(rows) == 1
        assert rows[0]["title"] == "Stator video"

    def test_list_filter_by_skill_level(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        add_video(VideoTutorial(
            title="Begin", source="youtube", skill_level=SkillLevel.BEGINNER,
        ), db)
        add_video(VideoTutorial(
            title="Expert", source="youtube", skill_level=SkillLevel.EXPERT,
        ), db)
        rows = list_videos(skill_level=SkillLevel.EXPERT, db_path=db)
        assert len(rows) == 1
        assert rows[0]["title"] == "Expert"

    def test_update_topic_tags(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        vid = add_video(VideoTutorial(
            title="T", source="youtube", topic_tags=["old"],
        ), db)
        assert update_video(vid, db_path=db, topic_tags=["new", "tags"]) is True
        row = get_video(vid, db)
        assert row["topic_tags"] == ["new", "tags"]

    def test_delete(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        vid = add_video(VideoTutorial(title="Temp", source="youtube"), db)
        assert delete_video(vid, db) is True
        assert get_video(vid, db) is None


# --- Forward compat ---


class TestSchemaVersionForwardCompat:
    def test_schema_version_at_least_10(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_schema_version(db) >= 10

    def test_schema_version_constant_at_least_10(self):
        assert SCHEMA_VERSION >= 10
