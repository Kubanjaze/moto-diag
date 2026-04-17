"""Parts diagrams repository.

Phase 117: CRUD for exploded views, schematics, wiring, assembly diagrams.
"""

from typing import Optional

from motodiag.core.database import get_connection
from motodiag.reference.models import PartsDiagram, DiagramType


def add_diagram(diagram: PartsDiagram, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO parts_diagrams
               (make, model, year_start, year_end, diagram_type, section,
                title, image_ref, source_manual_id, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                diagram.make, diagram.model, diagram.year_start, diagram.year_end,
                diagram.diagram_type.value, diagram.section, diagram.title,
                diagram.image_ref, diagram.source_manual_id, diagram.notes,
            ),
        )
        return cursor.lastrowid


def get_diagram(diagram_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM parts_diagrams WHERE id = ?", (diagram_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_diagrams(
    diagram_type: DiagramType | str | None = None,
    make: Optional[str] = None,
    model: Optional[str] = None,
    target_year: Optional[int] = None,
    section: Optional[str] = None,
    db_path: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM parts_diagrams WHERE 1=1"
    params: list = []
    if diagram_type is not None:
        dval = diagram_type.value if isinstance(diagram_type, DiagramType) else diagram_type
        query += " AND diagram_type = ?"
        params.append(dval)
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
    if section is not None:
        query += " AND section = ?"
        params.append(section)
    query += " ORDER BY diagram_type, section, title"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def update_diagram(diagram_id: int, db_path: str | None = None, **fields) -> bool:
    if not fields:
        return False
    if "diagram_type" in fields and isinstance(fields["diagram_type"], DiagramType):
        fields["diagram_type"] = fields["diagram_type"].value
    keys = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [diagram_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE parts_diagrams SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def delete_diagram(diagram_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM parts_diagrams WHERE id = ?", (diagram_id,),
        )
        return cursor.rowcount > 0
