"""Phase 151 — service-interval repository.

CRUD + template-seeding layer for the two tables created by migration
019:

- ``service_intervals`` — per-bike maintenance schedule rows
  (oil change, valve check, chain-clean-lube, etc.), keyed by
  UNIQUE(vehicle_id, item_slug), with FK CASCADE on ``vehicle_id``.
- ``service_interval_templates`` — global OEM-recommended intervals
  catalog, loaded from ``advanced/data/service_interval_templates.json``
  via :func:`load_templates_from_json`. Natural key
  (make, model_pattern, item_slug) is UNIQUE so loader is idempotent.

Design notes
------------

* **Wildcard semantics.** ``make='*'`` matches any make;
  ``model_pattern`` is a SQL LIKE pattern (``'%'`` = all models,
  ``'Sportster%'`` = any Sportster variant). Match resolution is done
  in :func:`match_templates_for_vehicle` — the DB does the LIKE work.

* **Idempotent loader.** :func:`load_templates_from_json` uses
  ``INSERT OR IGNORE`` so re-running against the same catalog is a
  no-op. Returns the count of **newly inserted** rows.

* **seed_from_template skips existing slugs.** If a bike already has
  an ``oil-change`` interval, seeding will not duplicate it —
  UNIQUE(vehicle_id, item_slug) would reject the INSERT, but we
  check first so the caller gets an accurate "newly created" count.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Path defaults
# ---------------------------------------------------------------------------


_DEFAULT_TEMPLATES_PATH = (
    Path(__file__).parent / "data" / "service_interval_templates.json"
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ServiceIntervalError(ValueError):
    """Base error for schedule-repo misuse (empty slug, both-axes-None, etc.)."""


# ---------------------------------------------------------------------------
# service_intervals CRUD
# ---------------------------------------------------------------------------


def create_interval(
    vehicle_id: int,
    item_slug: str,
    description: str,
    *,
    every_miles: Optional[int] = None,
    every_months: Optional[int] = None,
    last_done_miles: Optional[int] = None,
    last_done_at: Optional[str] = None,
    next_due_miles: Optional[int] = None,
    next_due_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Insert a service_intervals row. Returns the new id."""
    if not item_slug or not str(item_slug).strip():
        raise ServiceIntervalError("item_slug must not be empty")
    if every_miles is None and every_months is None:
        raise ServiceIntervalError(
            "at least one of every_miles / every_months must be set"
        )
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO service_intervals ("
            "  vehicle_id, item_slug, description, every_miles, every_months, "
            "  last_done_miles, last_done_at, next_due_miles, next_due_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                vehicle_id,
                str(item_slug).strip(),
                description,
                every_miles,
                every_months,
                last_done_miles,
                last_done_at,
                next_due_miles,
                next_due_at,
            ),
        )
        return cursor.lastrowid


def get_interval(
    interval_id: int, db_path: Optional[str] = None,
) -> Optional[dict]:
    """Fetch by primary id. Returns None when absent."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM service_intervals WHERE id = ?", (interval_id,),
        ).fetchone()
    return dict(row) if row else None


def get_interval_by_slug(
    vehicle_id: int,
    item_slug: str,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """Fetch by (vehicle_id, item_slug). Returns None when absent."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM service_intervals "
            "WHERE vehicle_id = ? AND item_slug = ?",
            (vehicle_id, str(item_slug).strip()),
        ).fetchone()
    return dict(row) if row else None


def list_intervals(
    vehicle_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """List all intervals for a bike, ordered by item_slug for determinism."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM service_intervals WHERE vehicle_id = ? "
            "ORDER BY item_slug, id",
            (vehicle_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_interval(
    interval_id: int,
    *,
    description: Optional[str] = None,
    every_miles: Optional[int] = None,
    every_months: Optional[int] = None,
    last_done_miles: Optional[int] = None,
    last_done_at: Optional[str] = None,
    next_due_miles: Optional[int] = None,
    next_due_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Partial update. Returns True when the row was touched.

    Only non-None kwargs are written — pass ``description=None`` to leave
    the description unchanged. Use :func:`delete_interval` to remove.
    """
    fields: list[str] = []
    params: list = []
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if every_miles is not None:
        fields.append("every_miles = ?")
        params.append(every_miles)
    if every_months is not None:
        fields.append("every_months = ?")
        params.append(every_months)
    if last_done_miles is not None:
        fields.append("last_done_miles = ?")
        params.append(last_done_miles)
    if last_done_at is not None:
        fields.append("last_done_at = ?")
        params.append(last_done_at)
    if next_due_miles is not None:
        fields.append("next_due_miles = ?")
        params.append(next_due_miles)
    if next_due_at is not None:
        fields.append("next_due_at = ?")
        params.append(next_due_at)
    if not fields:
        return False
    params.append(interval_id)
    sql = (
        f"UPDATE service_intervals SET {', '.join(fields)} WHERE id = ?"
    )
    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return cursor.rowcount > 0


def delete_interval(
    interval_id: int, db_path: Optional[str] = None,
) -> bool:
    """Delete by id. Returns True if a row was deleted."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM service_intervals WHERE id = ?", (interval_id,),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# service_interval_templates
# ---------------------------------------------------------------------------


def load_templates_from_json(
    path: Optional[str | Path] = None,
    db_path: Optional[str] = None,
) -> int:
    """Load the template catalog. Returns count of **newly inserted** rows.

    Uses ``INSERT OR IGNORE`` against the natural-key UNIQUE
    (make, model_pattern, item_slug) so calling this twice inserts zero
    rows the second time. Missing file raises FileNotFoundError.
    """
    p = Path(path) if path is not None else _DEFAULT_TEMPLATES_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"service-interval templates catalog not found at {p}"
        )
    with p.open("r", encoding="utf-8") as fh:
        rows = json.load(fh)
    inserted = 0
    with get_connection(db_path) as conn:
        for entry in rows:
            if entry.get("every_miles") is None and entry.get("every_months") is None:
                # Skip malformed rows — CHECK would reject anyway.
                continue
            cursor = conn.execute(
                "INSERT OR IGNORE INTO service_interval_templates ("
                "  make, model_pattern, item_slug, description, "
                "  every_miles, every_months, notes"
                ") VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    entry["make"],
                    entry["model_pattern"],
                    entry["item_slug"],
                    entry["description"],
                    entry.get("every_miles"),
                    entry.get("every_months"),
                    entry.get("notes"),
                ),
            )
            if cursor.rowcount > 0:
                inserted += 1
    return inserted


def list_templates(db_path: Optional[str] = None) -> list[dict]:
    """List all templates ordered by (make, model_pattern, item_slug)."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM service_interval_templates "
            "ORDER BY make, model_pattern, item_slug, id"
        ).fetchall()
    return [dict(r) for r in rows]


def _normalize_make(value: Optional[str]) -> str:
    """Lowercase + normalize Harley spelling variants for template matching.

    Template catalog uses ``harley-davidson`` — vehicles often land as
    ``Harley-Davidson`` or ``Harley Davidson``. Normalize to the slug
    form so make='*' + the specific-make branch both match.
    """
    if not value:
        return ""
    normalized = str(value).strip().lower()
    normalized = normalized.replace(" ", "-")
    return normalized


def match_templates_for_vehicle(
    vehicle: dict,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Return templates whose (make, model_pattern) matches a vehicle.

    Matching rules:
      * ``make='*'`` always matches (universal templates).
      * Otherwise template make must equal the normalized vehicle make.
      * ``model_pattern`` is applied with SQL LIKE against the vehicle's
        model (so ``'%'`` matches everything, ``'Sportster%'`` matches
        any Sportster).
    """
    vmake = _normalize_make(vehicle.get("make"))
    vmodel = str(vehicle.get("model") or "")
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM service_interval_templates "
            "WHERE (make = '*' OR LOWER(make) = ?) "
            "  AND ? LIKE model_pattern "
            "ORDER BY make, model_pattern, item_slug, id",
            (vmake, vmodel),
        ).fetchall()
    return [dict(r) for r in rows]


def seed_from_template(
    vehicle_id: int,
    db_path: Optional[str] = None,
) -> int:
    """Materialize template rows as per-bike service_intervals.

    Reads the vehicle's make/model, matches templates, and inserts one
    service_intervals row per unique item_slug. Skips slugs the bike
    already has — returns the count of **newly created** rows.
    """
    with get_connection(db_path) as conn:
        vrow = conn.execute(
            "SELECT id, make, model, year FROM vehicles WHERE id = ?",
            (vehicle_id,),
        ).fetchone()
    if vrow is None:
        raise ServiceIntervalError(
            f"vehicle_id={vehicle_id} not found in vehicles table"
        )
    vehicle = dict(vrow)
    templates = match_templates_for_vehicle(vehicle, db_path=db_path)
    if not templates:
        return 0

    existing = {
        row["item_slug"] for row in list_intervals(vehicle_id, db_path=db_path)
    }

    created = 0
    # Dedup templates by item_slug in iteration order — first template
    # wins if multiple templates cover the same slug (make-specific
    # tends to sort before universal '*' because '*' < letters in ASCII,
    # but order isn't strictly needed for correctness).
    seen_slugs: set[str] = set()
    with get_connection(db_path) as conn:
        for tpl in templates:
            slug = tpl["item_slug"]
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            if slug in existing:
                continue
            try:
                conn.execute(
                    "INSERT INTO service_intervals ("
                    "  vehicle_id, item_slug, description, "
                    "  every_miles, every_months"
                    ") VALUES (?, ?, ?, ?, ?)",
                    (
                        vehicle_id,
                        slug,
                        tpl["description"],
                        tpl.get("every_miles"),
                        tpl.get("every_months"),
                    ),
                )
                created += 1
            except sqlite3.IntegrityError:
                # Defensive: another process raced us, or the CHECK rejected.
                continue
    return created
