"""Known issues repository — common problems, causes, fixes by make/model/year."""

import json
from datetime import datetime

from motodiag.core.database import get_connection


def add_known_issue(
    title: str,
    description: str,
    make: str | None = None,
    model: str | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    severity: str = "medium",
    symptoms: list[str] | None = None,
    dtc_codes: list[str] | None = None,
    causes: list[str] | None = None,
    fix_procedure: str | None = None,
    parts_needed: list[str] | None = None,
    estimated_hours: float | None = None,
    db_path: str | None = None,
) -> int:
    """Add a known issue to the database. Returns issue ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO known_issues
               (title, description, make, model, year_start, year_end, severity,
                symptoms, dtc_codes, causes, fix_procedure, parts_needed,
                estimated_hours, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                title, description, make, model, year_start, year_end, severity,
                json.dumps(symptoms or []),
                json.dumps(dtc_codes or []),
                json.dumps(causes or []),
                fix_procedure,
                json.dumps(parts_needed or []),
                estimated_hours,
                datetime.now().isoformat(),
            ),
        )
        return cursor.lastrowid


def get_known_issue(issue_id: int, db_path: str | None = None) -> dict | None:
    """Get a known issue by ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM known_issues WHERE id = ?", (issue_id,))
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None


def search_known_issues(
    query: str | None = None,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    severity: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Search known issues with optional filters."""
    sql = "SELECT * FROM known_issues WHERE 1=1"
    params: list = []

    if query:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])
    if make:
        sql += " AND make LIKE ?"
        params.append(f"%{make}%")
    if model:
        sql += " AND model LIKE ?"
        params.append(f"%{model}%")
    if year:
        sql += " AND (year_start IS NULL OR year_start <= ?) AND (year_end IS NULL OR year_end >= ?)"
        params.extend([year, year])
    if severity:
        sql += " AND severity = ?"
        params.append(severity)

    sql += " ORDER BY severity DESC, title"

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [_row_to_dict(row) for row in cursor.fetchall()]


def find_issues_by_symptom(symptom: str, db_path: str | None = None) -> list[dict]:
    """Find known issues that list a given symptom."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM known_issues WHERE symptoms LIKE ? ORDER BY severity DESC",
            (f"%{symptom}%",),
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def find_issues_by_dtc(code: str, db_path: str | None = None) -> list[dict]:
    """Find known issues that list a given DTC code."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM known_issues WHERE dtc_codes LIKE ? ORDER BY severity DESC",
            (f"%{code}%",),
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def count_known_issues(make: str | None = None, db_path: str | None = None) -> int:
    """Count known issues, optionally filtered by make."""
    sql = "SELECT COUNT(*) FROM known_issues"
    params: list = []
    if make:
        sql += " WHERE make LIKE ?"
        params.append(f"%{make}%")
    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return cursor.fetchone()[0]


def _row_to_dict(row) -> dict:
    """Convert a database row to a dict, parsing JSON fields."""
    d = dict(row)
    for field in ("symptoms", "dtc_codes", "causes", "parts_needed"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = []
        else:
            d[field] = []
    return d
