"""Phase 114 — Workflow template substrate tests.

Tests cover:
- Migration 007 creates workflow_templates + checklist_items tables
- 2 built-in templates seeded (PPI + winterization) with starter checklist items
- WorkflowCategory enum has 13 members
- Template CRUD
- Checklist item CRUD
- Query by category/powertrain filters
- All 1769 existing tests still pass
"""

import pytest

from motodiag.core.database import (
    init_db, get_schema_version, SCHEMA_VERSION, get_connection,
)
from motodiag.core.migrations import get_migration_by_version, rollback_migration
from motodiag.workflows.models import (
    WorkflowCategory, WorkflowTemplate, ChecklistItem,
)
from motodiag.workflows.template_repo import (
    create_template, get_template, get_template_by_slug,
    list_templates, update_template, deactivate_template,
    add_checklist_item, get_checklist_items, update_checklist_item,
    delete_checklist_item, count_templates,
)


# --- Migration 007 ---


class TestMigration007:
    def test_migration_007_exists(self):
        m = get_migration_by_version(7)
        assert m is not None
        assert "workflow_templates" in m.upgrade_sql.lower()
        assert "checklist_items" in m.upgrade_sql.lower()

    def test_tables_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('workflow_templates', 'checklist_items')"
            )
            tables = {row[0] for row in cursor.fetchall()}
        assert tables == {"workflow_templates", "checklist_items"}

    def test_ppi_template_seeded(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        t = get_template_by_slug("generic_ppi_v1", db)
        assert t is not None
        assert t["category"] == "ppi"
        assert "ice" in t["applicable_powertrains"]
        assert "electric" in t["applicable_powertrains"]

    def test_winterization_template_seeded(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        t = get_template_by_slug("generic_winterization_v1", db)
        assert t is not None
        assert t["category"] == "winterization"
        # Winterization only applies to ICE/hybrid
        assert "electric" not in t["applicable_powertrains"]

    def test_ppi_has_5_checklist_items(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        t = get_template_by_slug("generic_ppi_v1", db)
        items = get_checklist_items(t["id"], db)
        assert len(items) == 5
        titles = [i["title"] for i in items]
        assert "VIN verification" in titles
        assert "Engine compression test" in titles

    def test_winterization_has_4_checklist_items(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        t = get_template_by_slug("generic_winterization_v1", db)
        items = get_checklist_items(t["id"], db)
        assert len(items) == 4
        titles = [i["title"] for i in items]
        assert "Add fuel stabilizer" in titles
        assert "Connect battery tender" in titles

    def test_checklist_items_ordered_by_sequence(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        t = get_template_by_slug("generic_ppi_v1", db)
        items = get_checklist_items(t["id"], db)
        sequences = [i["sequence_number"] for i in items]
        assert sequences == sorted(sequences)

    def test_tools_needed_parsed_as_list(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        t = get_template_by_slug("generic_ppi_v1", db)
        items = get_checklist_items(t["id"], db)
        # First item is VIN verification
        vin_item = next(i for i in items if i["title"] == "VIN verification")
        assert isinstance(vin_item["tools_needed"], list)
        assert "flashlight" in vin_item["tools_needed"]

    def test_schema_version_at_7(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        # >= for forward compat with future retrofit phases
        assert get_schema_version(db) >= 7

    def test_rollback_drops_workflow_tables(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        m = get_migration_by_version(7)
        rollback_migration(m, db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('workflow_templates', 'checklist_items')"
            )
            assert cursor.fetchall() == []


# --- WorkflowCategory enum ---


class TestWorkflowCategoryEnum:
    def test_13_categories(self):
        assert len(list(WorkflowCategory)) == 13

    def test_track_n_categories(self):
        assert WorkflowCategory.PPI.value == "ppi"
        assert WorkflowCategory.TIRE_SERVICE.value == "tire_service"
        assert WorkflowCategory.WINTERIZATION.value == "winterization"
        assert WorkflowCategory.BREAK_IN.value == "break_in"
        assert WorkflowCategory.EMISSIONS.value == "emissions"
        assert WorkflowCategory.VALVE_SERVICE.value == "valve_service"
        assert WorkflowCategory.BRAKE_SERVICE.value == "brake_service"

    def test_diagnostic_category_exists(self):
        assert WorkflowCategory.DIAGNOSTIC.value == "diagnostic"


# --- Models ---


class TestWorkflowTemplateModel:
    def test_minimal(self):
        t = WorkflowTemplate(slug="test_v1", name="Test", category=WorkflowCategory.PPI)
        assert t.slug == "test_v1"
        assert t.applicable_powertrains == ["ice", "electric", "hybrid"]
        assert t.required_tier == "individual"
        assert t.is_active is True

    def test_full(self):
        t = WorkflowTemplate(
            slug="custom_v1", name="Custom", category=WorkflowCategory.BRAKE_SERVICE,
            applicable_powertrains=["ice"], required_tier="shop",
            estimated_duration_minutes=90, created_by_user_id=5,
        )
        assert t.required_tier == "shop"
        assert t.created_by_user_id == 5


class TestChecklistItemModel:
    def test_minimal(self):
        item = ChecklistItem(
            template_id=1, sequence_number=1,
            title="Check something",
            instruction_text="Do this",
        )
        assert item.required is True
        assert item.tools_needed == []

    def test_full(self):
        item = ChecklistItem(
            template_id=1, sequence_number=2,
            title="Compression test",
            description="Warm engine first",
            instruction_text="Use gauge, crank, record",
            expected_pass="Within spec",
            expected_fail="Low compression",
            diagnosis_if_fail="Valves or rings",
            tools_needed=["gauge", "socket"],
            estimated_minutes=15,
        )
        assert item.diagnosis_if_fail == "Valves or rings"
        assert "gauge" in item.tools_needed


# --- Template CRUD ---


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "workflow_test.db")
    init_db(path)
    return path


class TestTemplateCRUD:
    def test_create_custom_template(self, db):
        tid = create_template(
            WorkflowTemplate(
                slug="shop_custom_ppi",
                name="My Shop's PPI",
                category=WorkflowCategory.PPI,
                required_tier="shop",
                created_by_user_id=1,
            ),
            db,
        )
        t = get_template(tid, db)
        assert t["name"] == "My Shop's PPI"
        assert t["required_tier"] == "shop"

    def test_get_by_slug(self, db):
        t = get_template_by_slug("generic_ppi_v1", db)
        assert t is not None

    def test_get_nonexistent(self, db):
        assert get_template(99999, db) is None
        assert get_template_by_slug("ghost", db) is None

    def test_list_all(self, db):
        templates = list_templates(db)
        # 2 seeded templates
        assert len(templates) >= 2

    def test_list_by_category(self, db):
        ppi_templates = list_templates(db, category=WorkflowCategory.PPI)
        assert len(ppi_templates) >= 1
        assert all(t["category"] == "ppi" for t in ppi_templates)

    def test_list_by_powertrain(self, db):
        # Winterization is ICE/hybrid only — electric should not match
        electric = list_templates(db, powertrain="electric")
        winterization_in_electric = [t for t in electric if t["category"] == "winterization"]
        assert winterization_in_electric == []

    def test_update_template(self, db):
        tid = create_template(
            WorkflowTemplate(slug="test_update", name="Original", category=WorkflowCategory.DIAGNOSTIC),
            db,
        )
        ok = update_template(tid, {"name": "Updated", "estimated_duration_minutes": 120}, db)
        assert ok is True
        t = get_template(tid, db)
        assert t["name"] == "Updated"
        assert t["estimated_duration_minutes"] == 120

    def test_deactivate_template(self, db):
        tid = create_template(
            WorkflowTemplate(slug="test_deactivate", name="T", category=WorkflowCategory.DIAGNOSTIC),
            db,
        )
        deactivate_template(tid, db)
        t = get_template(tid, db)
        assert t["is_active"] == 0

    def test_count_templates(self, db):
        before = count_templates(db)
        create_template(
            WorkflowTemplate(slug="count_a", name="A", category=WorkflowCategory.DIAGNOSTIC), db,
        )
        create_template(
            WorkflowTemplate(slug="count_b", name="B", category=WorkflowCategory.DIAGNOSTIC), db,
        )
        assert count_templates(db) == before + 2

    def test_count_by_category(self, db):
        ppi_count = count_templates(db, category=WorkflowCategory.PPI)
        winter_count = count_templates(db, category=WorkflowCategory.WINTERIZATION)
        assert ppi_count >= 1
        assert winter_count >= 1


# --- Checklist item CRUD ---


class TestChecklistItemCRUD:
    def test_add_checklist_item(self, db):
        tid = create_template(
            WorkflowTemplate(slug="checklist_test", name="T", category=WorkflowCategory.DIAGNOSTIC),
            db,
        )
        iid = add_checklist_item(
            ChecklistItem(
                template_id=tid,
                sequence_number=1,
                title="Step 1",
                instruction_text="Do the first thing",
                tools_needed=["wrench"],
                estimated_minutes=5,
            ),
            db,
        )
        items = get_checklist_items(tid, db)
        assert len(items) == 1
        assert items[0]["title"] == "Step 1"

    def test_items_ordered_by_sequence(self, db):
        tid = create_template(
            WorkflowTemplate(slug="order_test", name="T", category=WorkflowCategory.DIAGNOSTIC),
            db,
        )
        # Add out of order
        add_checklist_item(ChecklistItem(template_id=tid, sequence_number=3, title="Third", instruction_text="3rd"), db)
        add_checklist_item(ChecklistItem(template_id=tid, sequence_number=1, title="First", instruction_text="1st"), db)
        add_checklist_item(ChecklistItem(template_id=tid, sequence_number=2, title="Second", instruction_text="2nd"), db)

        items = get_checklist_items(tid, db)
        assert [i["title"] for i in items] == ["First", "Second", "Third"]

    def test_update_checklist_item(self, db):
        tid = create_template(
            WorkflowTemplate(slug="update_item_test", name="T", category=WorkflowCategory.DIAGNOSTIC),
            db,
        )
        iid = add_checklist_item(
            ChecklistItem(template_id=tid, sequence_number=1, title="Orig", instruction_text="Orig text"),
            db,
        )
        ok = update_checklist_item(iid, {"title": "Updated", "estimated_minutes": 30}, db)
        assert ok is True
        items = get_checklist_items(tid, db)
        assert items[0]["title"] == "Updated"
        assert items[0]["estimated_minutes"] == 30

    def test_delete_checklist_item(self, db):
        tid = create_template(
            WorkflowTemplate(slug="delete_item_test", name="T", category=WorkflowCategory.DIAGNOSTIC),
            db,
        )
        iid = add_checklist_item(
            ChecklistItem(template_id=tid, sequence_number=1, title="Will be deleted", instruction_text="x"),
            db,
        )
        ok = delete_checklist_item(iid, db)
        assert ok is True
        assert get_checklist_items(tid, db) == []

    def test_cascade_delete_on_template(self, db):
        tid = create_template(
            WorkflowTemplate(slug="cascade_test", name="T", category=WorkflowCategory.DIAGNOSTIC),
            db,
        )
        add_checklist_item(
            ChecklistItem(template_id=tid, sequence_number=1, title="Item", instruction_text="x"),
            db,
        )
        # Deleting the template should cascade-delete its checklist items
        with get_connection(db) as conn:
            conn.execute("DELETE FROM workflow_templates WHERE id = ?", (tid,))
        assert get_checklist_items(tid, db) == []
