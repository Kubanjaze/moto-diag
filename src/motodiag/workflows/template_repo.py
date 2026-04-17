"""Workflow template + checklist item repository.

Phase 114: CRUD operations for workflow_templates and checklist_items tables.
Track N phases (259-272) will consume these via create_template + bulk
add_checklist_item calls to populate PPI, tire service, winterization, etc.
"""

import json
from datetime import datetime
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.workflows.models import (
    WorkflowCategory, WorkflowTemplate, ChecklistItem,
)


# --- Template CRUD ---


def create_template(template: WorkflowTemplate, db_path: str | None = None) -> int:
    """Create a new workflow template. Returns the new template ID."""
    with get_connection(db_path) as conn:
        now = datetime.now().isoformat()
        cursor = conn.execute(
            """INSERT INTO workflow_templates
               (slug, name, description, category, applicable_powertrains,
                estimated_duration_minutes, required_tier, created_by_user_id,
                is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                template.slug, template.name, template.description,
                template.category.value,
                json.dumps(template.applicable_powertrains),
                template.estimated_duration_minutes,
                template.required_tier,
                template.created_by_user_id,
                1 if template.is_active else 0,
                now, now,
            ),
        )
        return cursor.lastrowid


def get_template(template_id: int, db_path: str | None = None) -> dict | None:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM workflow_templates WHERE id = ?", (template_id,)
        )
        row = cursor.fetchone()
        return _row_to_template_dict(row) if row else None


def get_template_by_slug(slug: str, db_path: str | None = None) -> dict | None:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM workflow_templates WHERE slug = ?", (slug,)
        )
        row = cursor.fetchone()
        return _row_to_template_dict(row) if row else None


def list_templates(
    db_path: str | None = None,
    category: WorkflowCategory | str | None = None,
    powertrain: str | None = None,
    is_active: bool | None = None,
) -> list[dict]:
    """List templates with optional filters.

    powertrain filter uses substring match on the JSON applicable_powertrains
    field — not perfect for all cases, but sufficient when values are simple
    slugs like 'ice', 'electric', 'hybrid'.
    """
    query = "SELECT * FROM workflow_templates WHERE 1=1"
    params: list = []
    if category is not None:
        cat_val = category.value if isinstance(category, WorkflowCategory) else category
        query += " AND category = ?"
        params.append(cat_val)
    if powertrain is not None:
        query += " AND applicable_powertrains LIKE ?"
        params.append(f"%\"{powertrain}\"%")
    if is_active is not None:
        query += " AND is_active = ?"
        params.append(1 if is_active else 0)
    query += " ORDER BY category, name"

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [_row_to_template_dict(row) for row in cursor.fetchall()]


def update_template(template_id: int, updates: dict, db_path: str | None = None) -> bool:
    allowed = {
        "slug", "name", "description", "category", "applicable_powertrains",
        "estimated_duration_minutes", "required_tier", "is_active",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return False

    # Convert enums/lists for SQLite
    if "category" in filtered and isinstance(filtered["category"], WorkflowCategory):
        filtered["category"] = filtered["category"].value
    if "applicable_powertrains" in filtered and isinstance(filtered["applicable_powertrains"], list):
        filtered["applicable_powertrains"] = json.dumps(filtered["applicable_powertrains"])
    if "is_active" in filtered and isinstance(filtered["is_active"], bool):
        filtered["is_active"] = 1 if filtered["is_active"] else 0

    filtered["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [template_id]

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE workflow_templates SET {set_clause} WHERE id = ?", values,
        )
        return cursor.rowcount > 0


def deactivate_template(template_id: int, db_path: str | None = None) -> bool:
    return update_template(template_id, {"is_active": False}, db_path)


def count_templates(
    db_path: str | None = None,
    category: WorkflowCategory | str | None = None,
    is_active: bool | None = None,
) -> int:
    query = "SELECT COUNT(*) FROM workflow_templates WHERE 1=1"
    params: list = []
    if category is not None:
        cat_val = category.value if isinstance(category, WorkflowCategory) else category
        query += " AND category = ?"
        params.append(cat_val)
    if is_active is not None:
        query += " AND is_active = ?"
        params.append(1 if is_active else 0)
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchone()[0]


# --- Checklist item CRUD ---


def add_checklist_item(item: ChecklistItem, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO checklist_items
               (template_id, sequence_number, title, description,
                instruction_text, expected_pass, expected_fail, diagnosis_if_fail,
                required, tools_needed, estimated_minutes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.template_id, item.sequence_number, item.title, item.description,
                item.instruction_text, item.expected_pass, item.expected_fail,
                item.diagnosis_if_fail,
                1 if item.required else 0,
                json.dumps(item.tools_needed),
                item.estimated_minutes,
            ),
        )
        return cursor.lastrowid


def get_checklist_items(template_id: int, db_path: str | None = None) -> list[dict]:
    """Return all checklist items for a template, ordered by sequence_number."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM checklist_items WHERE template_id = ? ORDER BY sequence_number",
            (template_id,),
        )
        return [_row_to_checklist_dict(row) for row in cursor.fetchall()]


def update_checklist_item(item_id: int, updates: dict, db_path: str | None = None) -> bool:
    allowed = {
        "sequence_number", "title", "description", "instruction_text",
        "expected_pass", "expected_fail", "diagnosis_if_fail",
        "required", "tools_needed", "estimated_minutes",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return False

    if "required" in filtered and isinstance(filtered["required"], bool):
        filtered["required"] = 1 if filtered["required"] else 0
    if "tools_needed" in filtered and isinstance(filtered["tools_needed"], list):
        filtered["tools_needed"] = json.dumps(filtered["tools_needed"])

    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [item_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE checklist_items SET {set_clause} WHERE id = ?", values,
        )
        return cursor.rowcount > 0


def delete_checklist_item(item_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))
        return cursor.rowcount > 0


# --- Helpers ---


def _row_to_template_dict(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    if d.get("applicable_powertrains"):
        try:
            d["applicable_powertrains"] = json.loads(d["applicable_powertrains"])
        except (json.JSONDecodeError, TypeError):
            d["applicable_powertrains"] = []
    else:
        d["applicable_powertrains"] = []
    return d


def _row_to_checklist_dict(row) -> dict:
    d = dict(row)
    if d.get("tools_needed"):
        try:
            d["tools_needed"] = json.loads(d["tools_needed"])
        except (json.JSONDecodeError, TypeError):
            d["tools_needed"] = []
    else:
        d["tools_needed"] = []
    return d
