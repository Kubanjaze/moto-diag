"""Recall repository."""

from typing import Optional

from motodiag.core.database import get_connection
from motodiag.inventory.models import Recall


def add_recall(recall: Recall, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO recalls
               (campaign_number, make, model, year_start, year_end,
                description, severity, remedy, notification_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                recall.campaign_number, recall.make, recall.model,
                recall.year_start, recall.year_end, recall.description,
                recall.severity, recall.remedy, recall.notification_date,
            ),
        )
        return cursor.lastrowid


def get_recall(recall_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM recalls WHERE id = ?", (recall_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_recalls_for_vehicle(
    make: str,
    model: Optional[str] = None,
    year: Optional[int] = None,
    db_path: str | None = None,
) -> list[dict]:
    """List recalls applicable to a specific make/model/year."""
    query = "SELECT * FROM recalls WHERE make = ?"
    params: list = [make]
    if model is not None:
        query += " AND (model IS NULL OR model = ?)"
        params.append(model)
    if year is not None:
        query += (
            " AND (year_start IS NULL OR year_start <= ?)"
            " AND (year_end IS NULL OR year_end >= ?)"
        )
        params.extend([year, year])
    query += " ORDER BY severity DESC, campaign_number"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def list_recalls(
    severity: Optional[str] = None, db_path: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM recalls WHERE 1=1"
    params: list = []
    if severity is not None:
        query += " AND severity = ?"
        params.append(severity)
    query += " ORDER BY campaign_number"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def delete_recall(recall_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM recalls WHERE id = ?", (recall_id,),
        )
        return cursor.rowcount > 0
