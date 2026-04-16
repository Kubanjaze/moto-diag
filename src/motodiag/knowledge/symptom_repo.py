"""Symptom repository — CRUD and search for mechanic-reported symptoms."""

import json
from motodiag.core.database import get_connection


def add_symptom(
    name: str,
    description: str,
    category: str,
    related_systems: list[str] | None = None,
    db_path: str | None = None,
) -> None:
    """Add a symptom to the database."""
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO symptoms (name, description, category, related_systems)
               VALUES (?, ?, ?, ?)""",
            (name, description, category,
             json.dumps(related_systems) if related_systems else None),
        )


def get_symptom(name: str, db_path: str | None = None) -> dict | None:
    """Get a symptom by exact name."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM symptoms WHERE name = ?", (name,)
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None


def search_symptoms(
    query: str | None = None,
    category: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Search symptoms by keyword and/or category."""
    sql = "SELECT * FROM symptoms WHERE 1=1"
    params: list = []

    if query:
        sql += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])
    if category:
        sql += " AND category = ?"
        params.append(category)

    sql += " ORDER BY category, name"

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [_row_to_dict(row) for row in cursor.fetchall()]


def list_symptoms_by_category(category: str, db_path: str | None = None) -> list[dict]:
    """List all symptoms in a category."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM symptoms WHERE category = ? ORDER BY name",
            (category,),
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def count_symptoms(db_path: str | None = None) -> int:
    """Get total symptom count."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM symptoms")
        return cursor.fetchone()[0]


def _row_to_dict(row) -> dict:
    """Convert a database row to a dict, parsing JSON fields."""
    d = dict(row)
    if d.get("related_systems"):
        try:
            d["related_systems"] = json.loads(d["related_systems"])
        except (json.JSONDecodeError, TypeError):
            d["related_systems"] = []
    else:
        d["related_systems"] = []
    return d
