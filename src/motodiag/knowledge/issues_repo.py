"""Known issues repository — common problems, causes, fixes by make/model/year."""

import json
from datetime import datetime

from motodiag.core.severity import SEVERITY_RANK_SQL
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
    source: str = "unverified",
) -> int:
    """Add a known issue to the database. Returns issue ID.

    `source` (Phase 211) records provenance and is CHECK-constrained by
    migration 051: `unverified` · `model-generated` · `forum` ·
    `service-manual` · `mechanic-verified`, plus `regulation` from
    migration 052 (Phase 235B) for primary legal text. It is last and
    defaulted so every existing caller — 31 of them — is unaffected.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO known_issues
               (title, description, make, model, year_start, year_end, severity,
                symptoms, dtc_codes, causes, fix_procedure, parts_needed,
                estimated_hours, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                title, description, make, model, year_start, year_end, severity,
                json.dumps(symptoms or []),
                json.dumps(dtc_codes or []),
                json.dumps(causes or []),
                fix_procedure,
                json.dumps(parts_needed or []),
                estimated_hours,
                source,
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


def _known_issue_filters(
    query: str | None = None,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    severity: str | None = None,
) -> tuple[str, list]:
    """Build the shared WHERE clause for search + count.

    Phase 206: extracted so the count and the page cannot drift. The
    route needs both a bounded page AND an honest total, and computing
    the total by len()-ing an unbounded fetch is what this phase is
    fixing — so the clause has exactly one definition.
    """
    sql = " WHERE 1=1"
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

    return sql, params


def search_known_issues(
    query: str | None = None,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    severity: str | None = None,
    db_path: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Search known issues with optional filters.

    Phase 206: ``limit``/``offset`` push pagination into SQL. The API
    route previously fetched EVERY row and sliced in Python
    (``rows[:limit]``), so asking for 50 issues materialised all 660.
    ``limit=None`` preserves the original unbounded behaviour for
    callers that genuinely want everything.
    """
    where, params = _known_issue_filters(query, make, model, year, severity)
    sql = "SELECT * FROM known_issues" + where + " ORDER BY " + SEVERITY_RANK_SQL + " DESC, title"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [_row_to_dict(row) for row in cursor.fetchall()]


def count_known_issues_matching(
    query: str | None = None,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    severity: str | None = None,
    db_path: str | None = None,
) -> int:
    """Total rows matching the same filters ``search_known_issues`` uses.

    Phase 206: lets a route report an honest ``total`` alongside a
    bounded page, without fetching the rows to count them.
    """
    where, params = _known_issue_filters(query, make, model, year, severity)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM known_issues" + where, params,
        ).fetchone()
    return int(row[0])


def find_issues_by_symptom(symptom: str, db_path: str | None = None) -> list[dict]:
    """Find known issues that list a given symptom."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM known_issues WHERE symptoms LIKE ? "
            "ORDER BY " + SEVERITY_RANK_SQL + " DESC",
            (f"%{symptom}%",),
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def find_issues_by_dtc(code: str, db_path: str | None = None) -> list[dict]:
    """Find known issues that list a given DTC code."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM known_issues WHERE dtc_codes LIKE ? "
            "ORDER BY " + SEVERITY_RANK_SQL + " DESC",
            (f"%{code}%",),
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def search_known_issues_text(
    query: str,
    limit: int | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Free-text search across title, description, and symptoms (JSON text).

    Case-insensitive LIKE substring match. Returns rows matching ANY of the
    three columns. Unlike :func:`search_known_issues` (which is structured
    by-field filtering with exact-match semantics on make/model/severity),
    this is a broad browse-search tailored for the `motodiag kb search`
    CLI — a mechanic investigating "stator" should see hits whether the
    word lives in the title, the description, or a symptom string.

    Empty / whitespace-only query returns [] immediately (avoids the "LIKE
    '%%' matches everything" trap that would dump the whole KB).

    Args:
        query: Substring to search for. Whitespace is stripped; empty
            query returns [].
        limit: Optional max rows. None = no cap.
        db_path: Override default DB path (used by tests).

    Returns:
        List of issue dicts (via :func:`_row_to_dict`), newest first by
        created_at then id.
    """
    if not query or not query.strip():
        return []
    pattern = f"%{query.strip()}%"
    sql = (
        "SELECT * FROM known_issues "
        "WHERE LOWER(title) LIKE LOWER(?) "
        "   OR LOWER(description) LIKE LOWER(?) "
        "   OR LOWER(symptoms) LIKE LOWER(?) "
        "ORDER BY created_at DESC, id DESC"
    )
    params: list = [pattern, pattern, pattern]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
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
