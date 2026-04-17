"""Photo annotation repository.

Phase 119: CRUD for photo_annotations. Track Q phase 307 renders the
actual canvas overlay using this metadata.
"""

from typing import Optional

from motodiag.core.database import get_connection
from motodiag.media.photo_annotation import PhotoAnnotation, AnnotationShape


def add_annotation(annotation: PhotoAnnotation, db_path: str | None = None) -> int:
    """Insert a photo annotation. Returns new row id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO photo_annotations
               (image_ref, failure_photo_id, shape, x, y, width, height,
                text, color, stroke_width, label, created_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                annotation.image_ref, annotation.failure_photo_id,
                annotation.shape.value,
                annotation.x, annotation.y, annotation.width, annotation.height,
                annotation.text, annotation.color, annotation.stroke_width,
                annotation.label, annotation.created_by_user_id,
            ),
        )
        return cursor.lastrowid


def get_annotation(annotation_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM photo_annotations WHERE id = ?", (annotation_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_annotations_for_image(image_ref: str, db_path: str | None = None) -> list[dict]:
    """All annotations for an image, ordered chronologically (render order)."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM photo_annotations WHERE image_ref = ? "
            "ORDER BY created_at, id",
            (image_ref,),
        )
        return [dict(r) for r in cursor.fetchall()]


def list_annotations_for_failure_photo(
    failure_photo_id: int, db_path: str | None = None,
) -> list[dict]:
    """All annotations explicitly FKed to a failure_photo row."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM photo_annotations WHERE failure_photo_id = ? "
            "ORDER BY created_at, id",
            (failure_photo_id,),
        )
        return [dict(r) for r in cursor.fetchall()]


def count_annotations_for_image(image_ref: str, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM photo_annotations WHERE image_ref = ?",
            (image_ref,),
        )
        return cursor.fetchone()[0]


def update_annotation(
    annotation_id: int, db_path: str | None = None, **fields,
) -> bool:
    if not fields:
        return False
    if "shape" in fields and isinstance(fields["shape"], AnnotationShape):
        fields["shape"] = fields["shape"].value
    fields["updated_at"] = "CURRENT_TIMESTAMP"  # handled as literal below
    keys = ", ".join(
        f"{k} = CURRENT_TIMESTAMP" if k == "updated_at" else f"{k} = ?"
        for k in fields
    )
    params = [v for k, v in fields.items() if k != "updated_at"] + [annotation_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE photo_annotations SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def delete_annotation(annotation_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM photo_annotations WHERE id = ?", (annotation_id,),
        )
        return cursor.rowcount > 0


def bulk_import_annotations(
    annotations: list[PhotoAnnotation], db_path: str | None = None,
) -> int:
    """Bulk insert; returns count imported. Used by Track Q when rehydrating."""
    count = 0
    with get_connection(db_path) as conn:
        for a in annotations:
            conn.execute(
                """INSERT INTO photo_annotations
                   (image_ref, failure_photo_id, shape, x, y, width, height,
                    text, color, stroke_width, label, created_by_user_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    a.image_ref, a.failure_photo_id, a.shape.value,
                    a.x, a.y, a.width, a.height,
                    a.text, a.color, a.stroke_width, a.label,
                    a.created_by_user_id,
                ),
            )
            count += 1
    return count
