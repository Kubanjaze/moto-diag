"""Labor rate lookups and management."""

import json
from pathlib import Path

from motodiag.core.database import get_connection


def add_labor_rate(
    region: str,
    rate_type: str,
    hourly_rate: float,
    state: str | None = None,
    source: str | None = None,
    effective_date: str | None = None,
    db_path: str | None = None,
) -> int:
    """Add a labor rate to the database. Returns rate ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO labor_rates
               (region, state, rate_type, hourly_rate, source, effective_date)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (region, state, rate_type, hourly_rate, source, effective_date),
        )
        return cursor.lastrowid


def get_labor_rate(
    region: str = "national",
    rate_type: str = "independent",
    state: str | None = None,
    db_path: str | None = None,
) -> dict | None:
    """Get the best matching labor rate.

    Resolution order: state-specific > regional > national.
    """
    with get_connection(db_path) as conn:
        # Try state-specific first
        if state:
            cursor = conn.execute(
                """SELECT * FROM labor_rates
                   WHERE state = ? AND rate_type = ?
                   ORDER BY effective_date DESC LIMIT 1""",
                (state, rate_type),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)

        # Try regional
        cursor = conn.execute(
            """SELECT * FROM labor_rates
               WHERE region = ? AND state IS NULL AND rate_type = ?
               ORDER BY effective_date DESC LIMIT 1""",
            (region, rate_type),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)

        # Fall back to national
        cursor = conn.execute(
            """SELECT * FROM labor_rates
               WHERE region = 'national' AND rate_type = ?
               ORDER BY effective_date DESC LIMIT 1""",
            (rate_type,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_rate_comparison(
    region: str = "national",
    state: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Get all rate types for a region for comparison display.

    Returns rates for independent, dealership, and mobile in one call.
    """
    results = []
    for rate_type in ("independent", "dealership", "mobile"):
        rate = get_labor_rate(region, rate_type, state, db_path)
        if rate:
            results.append(rate)
    return results


def list_all_rates(db_path: str | None = None) -> list[dict]:
    """List all labor rates in the database."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM labor_rates ORDER BY region, state, rate_type"
        )
        return [dict(row) for row in cursor.fetchall()]


def load_labor_rates_file(file_path: str | Path, db_path: str | None = None) -> int:
    """Load labor rates from a JSON file into the database. Returns count loaded."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Labor rates file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for item in data:
        add_labor_rate(
            region=item["region"],
            rate_type=item["rate_type"],
            hourly_rate=item["hourly_rate"],
            state=item.get("state"),
            source=item.get("source"),
            effective_date=item.get("effective_date"),
            db_path=db_path,
        )
        count += 1
    return count
