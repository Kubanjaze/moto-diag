"""Manual references repository.

Phase 117: CRUD for service manual citations (Clymer/Haynes/OEM/forum).
"""

import json
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.reference.models import ManualReference, ManualSource


def _row_to_manual(row) -> dict:
    d = dict(row)
    if d.get("section_titles"):
        try:
            d["section_titles"] = json.loads(d["section_titles"])
        except (json.JSONDecodeError, TypeError):
            d["section_titles"] = []
    else:
        d["section_titles"] = []
    return d


def add_manual(manual: ManualReference, db_path: str | None = None) -> int:
    """Insert a manual reference. Returns row id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO manual_references
               (source, title, publisher, isbn, make, model,
                year_start, year_end, page_count, section_titles, url, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                manual.source.value, manual.title, manual.publisher, manual.isbn,
                manual.make, manual.model, manual.year_start, manual.year_end,
                manual.page_count, json.dumps(manual.section_titles),
                manual.url, manual.notes,
            ),
        )
        return cursor.lastrowid


def get_manual(manual_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM manual_references WHERE id = ?", (manual_id,),
        )
        row = cursor.fetchone()
        return _row_to_manual(row) if row else None


def list_manuals(
    source: ManualSource | str | None = None,
    make: Optional[str] = None,
    model: Optional[str] = None,
    target_year: Optional[int] = None,
    db_path: str | None = None,
) -> list[dict]:
    """List manuals with optional filters. target_year matches year_start <= Y <= year_end
    (NULL year_start means universal)."""
    query = "SELECT * FROM manual_references WHERE 1=1"
    params: list = []
    if source is not None:
        sval = source.value if isinstance(source, ManualSource) else source
        query += " AND source = ?"
        params.append(sval)
    if make is not None:
        query += " AND (make IS NULL OR make = ?)"
        params.append(make)
    if model is not None:
        query += " AND (model IS NULL OR model = ?)"
        params.append(model)
    if target_year is not None:
        query += (
            " AND (year_start IS NULL OR year_start <= ?)"
            " AND (year_end IS NULL OR year_end >= ?)"
        )
        params.extend([target_year, target_year])
    query += " ORDER BY title"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [_row_to_manual(r) for r in cursor.fetchall()]


def update_manual(manual_id: int, db_path: str | None = None, **fields) -> bool:
    """Update arbitrary fields on a manual. Returns True if a row was updated."""
    if not fields:
        return False
    if "section_titles" in fields and isinstance(fields["section_titles"], list):
        fields["section_titles"] = json.dumps(fields["section_titles"])
    if "source" in fields and isinstance(fields["source"], ManualSource):
        fields["source"] = fields["source"].value
    keys = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [manual_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE manual_references SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def delete_manual(manual_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM manual_references WHERE id = ?", (manual_id,),
        )
        return cursor.rowcount > 0
