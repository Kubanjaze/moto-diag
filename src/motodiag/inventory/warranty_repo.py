"""Warranty repository."""

from typing import Optional

from motodiag.core.database import get_connection
from motodiag.inventory.models import Warranty, CoverageType


def add_warranty(warranty: Warranty, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO warranties
               (vehicle_id, coverage_type, provider, start_date, end_date,
                mileage_limit, terms, claim_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                warranty.vehicle_id, warranty.coverage_type.value,
                warranty.provider, warranty.start_date, warranty.end_date,
                warranty.mileage_limit, warranty.terms, warranty.claim_count,
            ),
        )
        return cursor.lastrowid


def get_warranty(warranty_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM warranties WHERE id = ?", (warranty_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_warranties_for_vehicle(
    vehicle_id: int,
    coverage_type: CoverageType | str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM warranties WHERE vehicle_id = ?"
    params: list = [vehicle_id]
    if coverage_type is not None:
        c = coverage_type.value if isinstance(coverage_type, CoverageType) else coverage_type
        query += " AND coverage_type = ?"
        params.append(c)
    query += " ORDER BY start_date DESC, id DESC"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def increment_claim_count(warranty_id: int, db_path: str | None = None) -> Optional[int]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT claim_count FROM warranties WHERE id = ?",
            (warranty_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        new_count = row[0] + 1
        conn.execute(
            "UPDATE warranties SET claim_count = ? WHERE id = ?",
            (new_count, warranty_id),
        )
        return new_count


def delete_warranty(warranty_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM warranties WHERE id = ?", (warranty_id,),
        )
        return cursor.rowcount > 0
