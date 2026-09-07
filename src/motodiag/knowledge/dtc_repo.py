"""DTC (Diagnostic Trouble Code) repository — CRUD and query operations.

Phase 111 (Retrofit): extended with dtc_category field for HV/battery/motor/
regen/TPMS/emissions taxonomy. Existing code using only `category` continues
to work; new code should set `dtc_category` for proper classification.
"""

import json
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.core.models import DTCCode, DTCCategory, SymptomCategory, Severity


def add_dtc(dtc: DTCCode, db_path: str | None = None) -> None:
    """Add or update a DTC code in the database.

    Phase 111: persists dtc_category column alongside existing category.
    """
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO dtc_codes
               (code, description, category, dtc_category, severity, make, common_causes, fix_summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dtc.code,
                dtc.description,
                dtc.category.value,
                dtc.dtc_category.value,
                dtc.severity.value,
                dtc.make,
                json.dumps(dtc.common_causes) if dtc.common_causes else None,
                dtc.fix_summary,
            ),
        )


def get_dtc(code: str, make: str | None = None, db_path: str | None = None) -> dict | None:
    """Get a DTC by code, optionally filtered by make.

    If make is specified, tries manufacturer-specific first, falls back to generic.
    """
    with get_connection(db_path) as conn:
        if make:
            # Try manufacturer-specific first
            cursor = conn.execute(
                "SELECT * FROM dtc_codes WHERE code = ? AND make = ?",
                (code.upper(), make),
            )
            row = cursor.fetchone()
            if row:
                return _row_to_dict(row)

        # Fall back to generic (make IS NULL)
        cursor = conn.execute(
            "SELECT * FROM dtc_codes WHERE code = ? AND make IS NULL",
            (code.upper(),),
        )
        row = cursor.fetchone()
        if row:
            return _row_to_dict(row)

        # Last resort: any match
        cursor = conn.execute(
            "SELECT * FROM dtc_codes WHERE code = ?", (code.upper(),)
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None


def get_dtcs(
    codes: list[str],
    make: str | None = None,
    db_path: str | None = None,
) -> dict[str, dict]:
    """Resolve many DTCs in ONE query. Keys are upper-cased codes.

    Phase 206: ``reporting/builders.py`` called :func:`get_dtc` once per
    fault code inside a loop — a textbook N+1, and up to THREE queries
    per code because of the fallback chain below.

    The resolution order is reproduced exactly, because the report's
    content depends on it:
      1. manufacturer-specific row (``make`` matches), when ``make`` given
      2. generic row (``make IS NULL``)
      3. any row for that code

    Codes with no row at all are simply absent from the result, so
    callers keep using ``.get(code)`` and the None-branch they already
    have.
    """
    wanted = [str(c).upper() for c in codes]
    if not wanted:
        return {}

    placeholders = ",".join("?" for _ in wanted)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM dtc_codes WHERE UPPER(code) IN ({placeholders})",
            wanted,
        ).fetchall()

    by_code: dict[str, list[dict]] = {}
    for row in rows:
        d = _row_to_dict(row)
        by_code.setdefault(str(d.get("code", "")).upper(), []).append(d)

    resolved: dict[str, dict] = {}
    for code in wanted:
        candidates = by_code.get(code)
        if not candidates:
            continue
        chosen = None
        if make:
            chosen = next(
                (c for c in candidates if c.get("make") == make), None,
            )
        if chosen is None:
            chosen = next(
                (c for c in candidates if c.get("make") is None), None,
            )
        if chosen is None:
            chosen = candidates[0]
        resolved[code] = chosen
    return resolved


def _dtc_filters(
    query: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    make: str | None = None,
) -> tuple[str, list]:
    """Shared WHERE clause for search + count (Phase 206).

    One definition so a bounded page and its total can never disagree.
    """
    sql = " WHERE 1=1"
    params: list = []

    if query:
        sql += " AND (code LIKE ? OR description LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])
    if category:
        sql += " AND category = ?"
        params.append(category)
    if severity:
        sql += " AND severity = ?"
        params.append(severity)
    if make:
        sql += " AND (make = ? OR make IS NULL)"
        params.append(make)

    return sql, params


def search_dtcs(
    query: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    make: str | None = None,
    db_path: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Search DTCs with optional filters.

    Phase 206: ``limit``/``offset`` push pagination into SQL; the route
    used to fetch everything and slice in Python. ``limit=None`` keeps
    the original unbounded behaviour for callers that want it.
    """
    where, params = _dtc_filters(query, category, severity, make)
    sql = "SELECT * FROM dtc_codes" + where + " ORDER BY code"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [_row_to_dict(row) for row in cursor.fetchall()]


def count_dtcs_matching(
    query: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    make: str | None = None,
    db_path: str | None = None,
) -> int:
    """Total rows matching the same filters ``search_dtcs`` uses."""
    where, params = _dtc_filters(query, category, severity, make)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM dtc_codes" + where, params,
        ).fetchone()
    return int(row[0])


def list_dtcs_by_make(make: str, db_path: str | None = None) -> list[dict]:
    """List all DTCs for a specific manufacturer."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM dtc_codes WHERE make = ? ORDER BY code", (make,)
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def count_dtcs(db_path: str | None = None) -> int:
    """Get total DTC count."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM dtc_codes")
        return cursor.fetchone()[0]


# --- Phase 111: DTC category operations ---

def get_dtcs_by_category(
    dtc_category: DTCCategory | str,
    make: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Query DTCs filtered by dtc_category (HV_BATTERY, MOTOR, REGEN, etc.).

    Phase 111: enables electric motorcycle diagnostic queries like
    "show all HV battery DTCs for this bike" without knowing specific codes.
    """
    cat_val = dtc_category.value if isinstance(dtc_category, DTCCategory) else dtc_category

    query = "SELECT * FROM dtc_codes WHERE dtc_category = ?"
    params: list = [cat_val]
    if make:
        query += " AND (make = ? OR make IS NULL)"
        params.append(make)
    query += " ORDER BY code"

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [_row_to_dict(row) for row in cursor.fetchall()]


def get_category_meta(dtc_category: DTCCategory | str, db_path: str | None = None) -> dict | None:
    """Get metadata for a DTC category (description, applicable powertrains, default severity).

    Phase 111: metadata populated by migration 004 for all DTCCategory members.
    """
    cat_val = dtc_category.value if isinstance(dtc_category, DTCCategory) else dtc_category
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT category, description, applicable_powertrains, severity_default "
            "FROM dtc_category_meta WHERE category = ?",
            (cat_val,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        try:
            result["applicable_powertrains"] = json.loads(result["applicable_powertrains"])
        except (json.JSONDecodeError, TypeError):
            result["applicable_powertrains"] = []
        return result


def list_all_categories(db_path: str | None = None) -> list[dict]:
    """List all DTC categories with their metadata."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT category, description, applicable_powertrains, severity_default "
            "FROM dtc_category_meta ORDER BY category"
        )
        results = []
        for row in cursor.fetchall():
            d = dict(row)
            try:
                d["applicable_powertrains"] = json.loads(d["applicable_powertrains"])
            except (json.JSONDecodeError, TypeError):
                d["applicable_powertrains"] = []
            results.append(d)
        return results


def _row_to_dict(row) -> dict:
    """Convert a database row to a dict, parsing JSON fields."""
    d = dict(row)
    if d.get("common_causes"):
        try:
            d["common_causes"] = json.loads(d["common_causes"])
        except (json.JSONDecodeError, TypeError):
            d["common_causes"] = []
    else:
        d["common_causes"] = []
    return d
