"""Warranty repository."""

from typing import Optional

from motodiag.core.database import get_connection
from motodiag.inventory.models import Warranty, CoverageType


def add_warranty(warranty: Warranty, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO warranties
               (vehicle_id, coverage_type, provider, start_date, end_date,
                mileage_limit, terms, claim_count, repair_payer, deductible_cents)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                warranty.vehicle_id, warranty.coverage_type.value,
                warranty.provider, warranty.start_date, warranty.end_date,
                warranty.mileage_limit, warranty.terms, warranty.claim_count,
                warranty.repair_payer, warranty.deductible_cents,
            ),
        )
        return cursor.lastrowid


def update_warranty(warranty_id: int, repair_payer: Optional[str] = None,
                    provider: Optional[str] = None,
                    deductible_cents: Optional[int] = None,
                    db_path: str | None = None) -> bool:
    """Record who owes a repair under a warranty, who gives it, and its
    deductible, where given. False when the warranty does not exist."""
    with get_connection(db_path) as conn:
        if conn.execute("SELECT 1 FROM warranties WHERE id = ?",
                        (warranty_id,)).fetchone() is None:
            return False
        if repair_payer is not None:
            conn.execute("UPDATE warranties SET repair_payer = ? WHERE id = ?",
                         (repair_payer, warranty_id))
        if provider is not None:
            conn.execute("UPDATE warranties SET provider = ? WHERE id = ?",
                         (provider, warranty_id))
        if deductible_cents is not None:
            conn.execute("UPDATE warranties SET deductible_cents = ? WHERE id = ?",
                         (deductible_cents, warranty_id))
        return True


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


def coverage_status(
    warranty: dict, on_date: str, mileage: Optional[int],
) -> tuple[str, list[str]]:
    """Whether one recorded coverage applies on ``on_date`` at ``mileage``.

    Returns ``(verdict, reasons)``, the verdict one of ``valid``,
    ``not valid`` or ``cannot tell``. A figure that is not recorded is never
    read as a pass: with no start date, end date or mileage limit on record,
    or no mileage for the bike, the lookup cannot tell, and says which. A
    failed test outranks a missing figure: a coverage that has ended is not
    valid, whatever else is missing.
    """
    failed: list[str] = []
    unknown: list[str] = []
    start, end = warranty.get("start_date"), warranty.get("end_date")
    if not start:
        unknown.append("no start date recorded")
    elif on_date < start:
        failed.append(f"starts {start}")
    if not end:
        unknown.append("no end date recorded")
    elif on_date > end:
        failed.append(f"ended {end}")
    limit = warranty.get("mileage_limit")
    if limit is None:
        unknown.append("no mileage limit recorded")
    elif mileage is None:
        unknown.append(f"the bike's mileage is not known (limit {limit:,} mi)")
    elif mileage > limit:
        failed.append(f"{mileage:,} mi is over the {limit:,} mi limit")
    if failed:
        return "not valid", failed
    if unknown:
        return "cannot tell", unknown
    return "valid", [f"{start} to {end}", f"{mileage:,} of {limit:,} mi"]
