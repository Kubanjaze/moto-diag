"""Recall repository."""

from typing import Optional

from motodiag.core.severity import SEVERITY_RANK_SQL
from motodiag.core.database import get_connection




def list_recalls_for_vehicle(
    make: str,
    model: Optional[str] = None,
    year: Optional[int] = None,
    db_path: str | None = None,
) -> list[dict]:
    """List recalls applicable to a specific make/model/year.

    Rows stored as before (``source`` NULL) match on their own make, model and
    year. Campaigns fetched from NHTSA (Phase 281) match through the vehicles
    NHTSA listed for them; see ``advanced.recall_repo.fetched_coverage_sql``.
    """
    from motodiag.advanced.recall_repo import fetched_coverage_sql

    query = "SELECT * FROM recalls WHERE ((source IS NULL AND make = ?"
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
    fetched_sql, fetched_params = fetched_coverage_sql("recalls", make, model, year)
    query += f") OR {fetched_sql})"
    params.extend(fetched_params)
    query += " ORDER BY " + SEVERITY_RANK_SQL + " DESC, campaign_number"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]



