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


def search_dtcs(
    query: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    make: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Search DTCs with optional filters."""
    sql = "SELECT * FROM dtc_codes WHERE 1=1"
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

    sql += " ORDER BY code"

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [_row_to_dict(row) for row in cursor.fetchall()]


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
