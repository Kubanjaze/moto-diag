"""Failure photos repository.

Phase 117: CRUD for failure-mode photographic library.
"""

from typing import Optional

from motodiag.core.database import get_connection
from motodiag.reference.models import FailurePhoto, FailureCategory


def add_photo(photo: FailurePhoto, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO failure_photos
               (title, description, failure_category, make, model,
                year_start, year_end, part_affected, image_ref,
                submitted_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                photo.title, photo.description, photo.failure_category.value,
                photo.make, photo.model, photo.year_start, photo.year_end,
                photo.part_affected, photo.image_ref, photo.submitted_by_user_id,
            ),
        )
        return cursor.lastrowid


def get_photo(photo_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM failure_photos WHERE id = ?", (photo_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_photos(
    failure_category: FailureCategory | str | None = None,
    make: Optional[str] = None,
    model: Optional[str] = None,
    target_year: Optional[int] = None,
    part_affected: Optional[str] = None,
    db_path: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM failure_photos WHERE 1=1"
    params: list = []
    if failure_category is not None:
        cval = (
            failure_category.value if isinstance(failure_category, FailureCategory)
            else failure_category
        )
        query += " AND failure_category = ?"
        params.append(cval)
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
    if part_affected is not None:
        query += " AND part_affected = ?"
        params.append(part_affected)
    query += " ORDER BY failure_category, title"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def update_photo(photo_id: int, db_path: str | None = None, **fields) -> bool:
    if not fields:
        return False
    if "failure_category" in fields and isinstance(fields["failure_category"], FailureCategory):
        fields["failure_category"] = fields["failure_category"].value
    keys = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [photo_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE failure_photos SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def delete_photo(photo_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM failure_photos WHERE id = ?", (photo_id,),
        )
        return cursor.rowcount > 0
