"""Repair plan builder — CRUD for per-bike repair plans with line items."""

import json
from datetime import datetime

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Repair Plan CRUD
# ---------------------------------------------------------------------------

def create_plan(
    title: str,
    vehicle_id: int | None = None,
    session_id: int | None = None,
    labor_rate: float | None = None,
    customer_name: str | None = None,
    customer_phone: str | None = None,
    notes: str | None = None,
    db_path: str | None = None,
) -> int:
    """Create a new repair plan. Returns plan ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO repair_plans
               (vehicle_id, session_id, title, status, labor_rate_used,
                customer_name, customer_phone, notes, created_at)
               VALUES (?, ?, ?, 'draft', ?, ?, ?, ?, ?)""",
            (
                vehicle_id, session_id, title, labor_rate,
                customer_name, customer_phone, notes,
                datetime.now().isoformat(),
            ),
        )
        return cursor.lastrowid


def get_plan(plan_id: int, db_path: str | None = None) -> dict | None:
    """Get a repair plan by ID, including its line items."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM repair_plans WHERE id = ?", (plan_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        plan = dict(row)

        # Attach line items
        items_cursor = conn.execute(
            """SELECT * FROM repair_plan_items
               WHERE plan_id = ? ORDER BY sort_order, id""",
            (plan_id,),
        )
        plan["items"] = [dict(r) for r in items_cursor.fetchall()]
        return plan


def update_plan(plan_id: int, updates: dict, db_path: str | None = None) -> bool:
    """Update repair plan fields. Returns True if updated."""
    allowed = {
        "title", "status", "labor_rate_used", "customer_name",
        "customer_phone", "notes",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return False

    filtered["updated_at"] = datetime.now().isoformat()

    # Handle status transitions with timestamps
    if filtered.get("status") == "approved":
        filtered["approved_at"] = datetime.now().isoformat()
    elif filtered.get("status") == "completed":
        filtered["completed_at"] = datetime.now().isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [plan_id]

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE repair_plans SET {set_clause} WHERE id = ?", values
        )
        return cursor.rowcount > 0


def delete_plan(plan_id: int, db_path: str | None = None) -> bool:
    """Delete a repair plan and all its items (CASCADE). Returns True if deleted."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM repair_plans WHERE id = ?", (plan_id,)
        )
        return cursor.rowcount > 0


def list_plans(
    status: str | None = None,
    vehicle_id: int | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """List repair plans with optional filters."""
    sql = "SELECT * FROM repair_plans WHERE 1=1"
    params: list = []

    if status:
        sql += " AND status = ?"
        params.append(status)
    if vehicle_id:
        sql += " AND vehicle_id = ?"
        params.append(vehicle_id)

    sql += " ORDER BY created_at DESC"

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Line Item CRUD
# ---------------------------------------------------------------------------

def add_item(
    plan_id: int,
    item_type: str,
    title: str,
    description: str | None = None,
    quantity: float = 1.0,
    unit_cost: float = 0.0,
    labor_hours: float = 0.0,
    source_issue_id: int | None = None,
    sort_order: int = 0,
    db_path: str | None = None,
) -> int:
    """Add a line item to a repair plan. Auto-computes line_total. Returns item ID."""
    # Compute line total based on item type
    if item_type == "parts":
        line_total = quantity * unit_cost
    else:
        # Labor items: get rate from plan
        plan = get_plan(plan_id, db_path)
        rate = plan["labor_rate_used"] if plan and plan["labor_rate_used"] else 0.0
        line_total = labor_hours * rate

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO repair_plan_items
               (plan_id, item_type, title, description, quantity,
                unit_cost, labor_hours, line_total, source_issue_id, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                plan_id, item_type, title, description, quantity,
                unit_cost, labor_hours, line_total, source_issue_id, sort_order,
            ),
        )
        item_id = cursor.lastrowid

    # Recalculate plan totals
    _recalculate_plan_totals(plan_id, db_path)
    return item_id


def update_item(item_id: int, updates: dict, db_path: str | None = None) -> bool:
    """Update a line item. Recalculates line_total and plan totals."""
    allowed = {
        "item_type", "title", "description", "quantity",
        "unit_cost", "labor_hours", "sort_order",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return False

    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [item_id]

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE repair_plan_items SET {set_clause} WHERE id = ?", values
        )
        if cursor.rowcount == 0:
            return False

        # Get plan_id for recalculation
        cursor = conn.execute(
            "SELECT plan_id, item_type, quantity, unit_cost, labor_hours FROM repair_plan_items WHERE id = ?",
            (item_id,),
        )
        row = cursor.fetchone()
        if row:
            item = dict(row)
            # Recompute line_total
            if item["item_type"] == "parts":
                line_total = item["quantity"] * item["unit_cost"]
            else:
                plan = get_plan(item["plan_id"], db_path)
                rate = plan["labor_rate_used"] if plan and plan["labor_rate_used"] else 0.0
                line_total = item["labor_hours"] * rate

            conn.execute(
                "UPDATE repair_plan_items SET line_total = ? WHERE id = ?",
                (line_total, item_id),
            )

    # Recalculate plan totals
    if row:
        _recalculate_plan_totals(item["plan_id"], db_path)
    return True


def remove_item(item_id: int, db_path: str | None = None) -> bool:
    """Remove a line item from a repair plan. Returns True if removed."""
    # Get plan_id before deleting
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT plan_id FROM repair_plan_items WHERE id = ?", (item_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False
        plan_id = row[0]

        conn.execute("DELETE FROM repair_plan_items WHERE id = ?", (item_id,))

    _recalculate_plan_totals(plan_id, db_path)
    return True


def get_plan_items(plan_id: int, db_path: str | None = None) -> list[dict]:
    """Get all line items for a repair plan."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT * FROM repair_plan_items
               WHERE plan_id = ? ORDER BY sort_order, id""",
            (plan_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Plan from diagnosed issues — the "click through" workflow
# ---------------------------------------------------------------------------

def create_plan_from_issues(
    title: str,
    issue_ids: list[int],
    labor_rate: float,
    vehicle_id: int | None = None,
    session_id: int | None = None,
    include_diagnostic: bool = True,
    include_test_ride: bool = True,
    db_path: str | None = None,
) -> int:
    """Create a repair plan from a list of known issue IDs.

    This is the core "click through diagnosed issues" workflow:
    1. Creates the plan with the labor rate
    2. Adds a diagnostic line item (optional)
    3. For each issue: adds repair labor + parts as line items
    4. Adds a final test ride item (optional)
    5. Recalculates all totals

    Returns plan ID.
    """
    plan_id = create_plan(
        title=title,
        vehicle_id=vehicle_id,
        session_id=session_id,
        labor_rate=labor_rate,
        db_path=db_path,
    )

    sort = 0

    # Optional: initial diagnostic
    if include_diagnostic:
        add_item(
            plan_id=plan_id,
            item_type="diagnostic",
            title="Initial diagnostic scan and inspection",
            description="Visual inspection, DTC scan, symptom verification, and assessment.",
            labor_hours=0.5,
            sort_order=sort,
            db_path=db_path,
        )
        sort += 1

    # Add each issue as repair labor + parts
    from motodiag.knowledge.issues_repo import get_known_issue

    for issue_id in issue_ids:
        issue = get_known_issue(issue_id, db_path)
        if not issue:
            continue

        # Repair labor line item
        hours = issue.get("estimated_hours") or 1.0
        add_item(
            plan_id=plan_id,
            item_type="repair_labor",
            title=issue["title"],
            description=issue.get("fix_procedure", "")[:500],
            labor_hours=hours,
            source_issue_id=issue_id,
            sort_order=sort,
            db_path=db_path,
        )
        sort += 1

        # Parts line items (each part as a separate line)
        parts = issue.get("parts_needed") or []
        for part in parts:
            add_item(
                plan_id=plan_id,
                item_type="parts",
                title=part,
                quantity=1.0,
                unit_cost=0.0,  # Mechanic fills in actual cost
                source_issue_id=issue_id,
                sort_order=sort,
                db_path=db_path,
            )
            sort += 1

    # Optional: final test ride
    if include_test_ride:
        add_item(
            plan_id=plan_id,
            item_type="repair_labor",
            title="Final inspection and test ride",
            description="Post-repair safety check: fluid levels, fastener torque, brake test, road test.",
            labor_hours=0.5,
            sort_order=sort,
            db_path=db_path,
        )

    return plan_id


# ---------------------------------------------------------------------------
# Prep labor helpers
# ---------------------------------------------------------------------------

def add_prep_labor_to_plan(
    plan_id: int,
    prep_name: str,
    prep_hours: float,
    prep_description: str | None = None,
    sort_order: int = 0,
    db_path: str | None = None,
) -> int:
    """Add a prep labor item (e.g., 'Remove fairings') to a plan."""
    return add_item(
        plan_id=plan_id,
        item_type="prep_labor",
        title=prep_name,
        description=prep_description,
        labor_hours=prep_hours,
        sort_order=sort_order,
        db_path=db_path,
    )


def load_prep_labor_file(file_path, db_path: str | None = None) -> int:
    """Load prep labor catalog from JSON into prep_labor table. Returns count."""
    from pathlib import Path

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Prep labor file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    with get_connection(db_path) as conn:
        for item in data:
            conn.execute(
                """INSERT INTO prep_labor
                   (name, description, category, estimated_hours, applies_to)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    item["name"],
                    item.get("description"),
                    item["category"],
                    item["estimated_hours"],
                    json.dumps(item.get("applies_to")),
                ),
            )
            count += 1
    return count


def list_prep_labor(category: str | None = None, db_path: str | None = None) -> list[dict]:
    """List available prep labor items from the catalog."""
    sql = "SELECT * FROM prep_labor WHERE 1=1"
    params: list = []
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY category, name"

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            d = dict(row)
            if d.get("applies_to"):
                try:
                    d["applies_to"] = json.loads(d["applies_to"])
                except (json.JSONDecodeError, TypeError):
                    d["applies_to"] = None
            return_val = d
            results.append(return_val)
        return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _recalculate_plan_totals(plan_id: int, db_path: str | None = None) -> None:
    """Recalculate total_parts_cost, total_labor_hours, total_labor_cost, total_estimate."""
    with get_connection(db_path) as conn:
        # Sum parts
        cursor = conn.execute(
            """SELECT COALESCE(SUM(line_total), 0)
               FROM repair_plan_items
               WHERE plan_id = ? AND item_type = 'parts'""",
            (plan_id,),
        )
        parts_cost = cursor.fetchone()[0]

        # Sum labor hours and cost (all non-parts items)
        cursor = conn.execute(
            """SELECT COALESCE(SUM(labor_hours), 0), COALESCE(SUM(line_total), 0)
               FROM repair_plan_items
               WHERE plan_id = ? AND item_type != 'parts'""",
            (plan_id,),
        )
        row = cursor.fetchone()
        labor_hours = row[0]
        labor_cost = row[1]

        total = parts_cost + labor_cost

        conn.execute(
            """UPDATE repair_plans
               SET total_parts_cost = ?, total_labor_hours = ?,
                   total_labor_cost = ?, total_estimate = ?,
                   updated_at = ?
               WHERE id = ?""",
            (parts_cost, labor_hours, labor_cost, total,
             datetime.now().isoformat(), plan_id),
        )
