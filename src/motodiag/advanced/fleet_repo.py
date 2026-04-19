"""Fleet management repository — CRUD over ``fleets`` + ``fleet_bikes``.

Phase 150. Third Track F phase. Extends the advanced-diagnostics surface
area with a named-grouping layer over the existing vehicles table so
mechanics can manage rental fleets, demo lineups, race teams, and shop
customer rosters as first-class objects.

Design notes
------------

- **Junction PK** ``(fleet_id, vehicle_id)`` enforces non-duplicate
  (bike, fleet) pairs while still allowing one bike to belong to
  multiple fleets. :class:`BikeAlreadyInFleetError` is raised on the
  IntegrityError; the CLI catches it to render a clean message.

- **CASCADE asymmetry.** Deleting a fleet drops its junction rows but
  vehicles survive (non-negotiable spec #3 — fleet deletion never
  destroys the mechanic's bike records). Deleting a vehicle drops its
  junction rows but fleets survive.

- **Owner scoping with default-id=1.** ``owner_user_id`` defaults to
  1 (the system user seeded by Phase 112 migration 005), mirroring the
  Phase 115/116/145 pattern. Real session-threading lands when Phase
  112's auth layer gets wired into the CLI runtime; until then every
  write is attributed to system user.

- **UNIQUE (owner_user_id, name)** scopes fleet names per user. Two
  different mechanics can each have a fleet called "Summer rentals"
  without collision.

- **_resolve_fleet accepts int or str.** CLI and repo callers can pass
  either the fleet id or its name interchangeably. Matches the
  ergonomic contract of Phase 148's ``--bike SLUG`` resolver.
"""

from __future__ import annotations

import sqlite3
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FleetNotFoundError(ValueError):
    """Raised when a fleet identifier (int id or str name) does not resolve."""


class FleetNameExistsError(ValueError):
    """Raised when `create_fleet` would violate UNIQUE(owner_user_id, name)."""


class BikeAlreadyInFleetError(ValueError):
    """Raised when `add_bike_to_fleet` hits the (fleet_id, vehicle_id) PK."""


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class FleetRole(str, Enum):
    """Per-assignment role for a bike in a fleet.

    Drives downstream analytics (rental utilization differs from race
    prep cadence) and the CHECK constraint on `fleet_bikes.role`.
    """

    RENTAL = "rental"
    DEMO = "demo"
    RACE = "race"
    CUSTOMER = "customer"


# Canonical valid-values tuple for CLI click.Choice + validation.
FLEET_ROLES: tuple[str, ...] = tuple(r.value for r in FleetRole)


class Fleet(BaseModel):
    """Pydantic view of a `fleets` row."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    description: Optional[str] = None
    owner_user_id: int = Field(default=1)
    created_at: Optional[str] = None
    bike_count: Optional[int] = None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_role(role: str) -> str:
    """Return normalized role or raise ValueError."""
    if role is None:
        raise ValueError("role must not be None")
    normalized = str(role).strip().lower()
    if normalized not in FLEET_ROLES:
        raise ValueError(
            f"role must be one of {FLEET_ROLES} (got {role!r})"
        )
    return normalized


def _resolve_fleet(
    identifier: int | str,
    owner_user_id: int = 1,
    db_path: Optional[str] = None,
) -> dict:
    """Resolve a fleet identifier (int id OR str name) to a row dict.

    Raises :class:`FleetNotFoundError` when the lookup misses. Name
    lookup is scoped to ``owner_user_id`` since the same name can
    appear under multiple owners.
    """
    if identifier is None:
        raise FleetNotFoundError("fleet identifier must not be None")
    if isinstance(identifier, bool):
        raise FleetNotFoundError(
            f"fleet identifier must be int or str (got bool {identifier!r})"
        )
    with get_connection(db_path) as conn:
        if isinstance(identifier, int):
            row = conn.execute(
                "SELECT * FROM fleets WHERE id = ?", (identifier,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM fleets WHERE name = ? AND owner_user_id = ?",
                (str(identifier), owner_user_id),
            ).fetchone()
    if row is None:
        raise FleetNotFoundError(f"fleet not found: {identifier!r}")
    return dict(row)


# ---------------------------------------------------------------------------
# Fleet CRUD
# ---------------------------------------------------------------------------


def create_fleet(
    name: str,
    description: Optional[str] = None,
    owner_user_id: int = 1,
    db_path: Optional[str] = None,
) -> int:
    """Create a fleet. Returns the new fleet id.

    Raises :class:`FleetNameExistsError` on UNIQUE(owner_user_id, name)
    violation — re-thrown from SQLite's IntegrityError for a clean CLI
    message.
    """
    if not name or not str(name).strip():
        raise ValueError("fleet name must not be empty")
    with get_connection(db_path) as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO fleets (name, description, owner_user_id) "
                "VALUES (?, ?, ?)",
                (str(name).strip(), description, owner_user_id),
            )
        except sqlite3.IntegrityError as e:
            raise FleetNameExistsError(
                f"fleet name already exists for owner_user_id={owner_user_id}: "
                f"{name!r}"
            ) from e
        return cursor.lastrowid


def get_fleet(fleet_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    """Fetch a fleet row by id. Returns None when missing."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM fleets WHERE id = ?", (fleet_id,),
        ).fetchone()
        return dict(row) if row else None


def get_fleet_by_name(
    name: str,
    owner_user_id: int = 1,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """Fetch a fleet row by (owner_user_id, name). Returns None when missing."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM fleets WHERE name = ? AND owner_user_id = ?",
            (str(name), owner_user_id),
        ).fetchone()
        return dict(row) if row else None


def list_fleets(
    owner_user_id: Optional[int] = 1,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List fleets with LEFT JOIN bike_count. Ordered by name.

    ``owner_user_id=None`` lists every fleet regardless of owner (admin
    path; CLI always passes the scoped default).
    """
    query = (
        "SELECT f.id, f.name, f.description, f.owner_user_id, f.created_at, "
        "       COUNT(fb.vehicle_id) AS bike_count "
        "FROM fleets f "
        "LEFT JOIN fleet_bikes fb ON fb.fleet_id = f.id "
    )
    params: list = []
    if owner_user_id is not None:
        query += "WHERE f.owner_user_id = ? "
        params.append(owner_user_id)
    query += "GROUP BY f.id ORDER BY f.name, f.id"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def rename_fleet(
    fleet_id: int,
    new_name: str,
    db_path: Optional[str] = None,
) -> bool:
    """Rename a fleet. Returns True on success.

    Raises :class:`FleetNameExistsError` when the new name collides with
    an existing fleet under the same owner.
    """
    if not new_name or not str(new_name).strip():
        raise ValueError("new_name must not be empty")
    with get_connection(db_path) as conn:
        try:
            cursor = conn.execute(
                "UPDATE fleets SET name = ? WHERE id = ?",
                (str(new_name).strip(), fleet_id),
            )
        except sqlite3.IntegrityError as e:
            raise FleetNameExistsError(
                f"cannot rename fleet id={fleet_id}: name already "
                f"exists for this owner: {new_name!r}"
            ) from e
        return cursor.rowcount > 0


def update_fleet_description(
    fleet_id: int,
    description: Optional[str],
    db_path: Optional[str] = None,
) -> bool:
    """Update the description. Returns True when a row was updated."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE fleets SET description = ? WHERE id = ?",
            (description, fleet_id),
        )
        return cursor.rowcount > 0


def delete_fleet(fleet_id: int, db_path: Optional[str] = None) -> bool:
    """Delete a fleet. CASCADE drops junction rows; vehicles survive."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM fleets WHERE id = ?", (fleet_id,),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Junction: fleet_bikes
# ---------------------------------------------------------------------------


def add_bike_to_fleet(
    fleet_id: int,
    vehicle_id: int,
    role: str = "customer",
    db_path: Optional[str] = None,
) -> None:
    """Add a bike to a fleet with the given role.

    Raises :class:`BikeAlreadyInFleetError` on PRIMARY KEY violation,
    :class:`ValueError` on invalid role, and re-raises
    :class:`sqlite3.IntegrityError` if the FK to fleets/vehicles fails
    (unknown fleet_id or vehicle_id).
    """
    normalized_role = _validate_role(role)
    with get_connection(db_path) as conn:
        try:
            conn.execute(
                "INSERT INTO fleet_bikes (fleet_id, vehicle_id, role) "
                "VALUES (?, ?, ?)",
                (fleet_id, vehicle_id, normalized_role),
            )
        except sqlite3.IntegrityError as e:
            msg = str(e).lower()
            if "primary key" in msg or "unique" in msg:
                raise BikeAlreadyInFleetError(
                    f"bike vehicle_id={vehicle_id} already in fleet "
                    f"id={fleet_id}"
                ) from e
            raise


def remove_bike_from_fleet(
    fleet_id: int,
    vehicle_id: int,
    db_path: Optional[str] = None,
) -> bool:
    """Remove a bike from a fleet. Returns True if a row was deleted."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM fleet_bikes WHERE fleet_id = ? AND vehicle_id = ?",
            (fleet_id, vehicle_id),
        )
        return cursor.rowcount > 0


def set_bike_role(
    fleet_id: int,
    vehicle_id: int,
    role: str,
    db_path: Optional[str] = None,
) -> bool:
    """Set the role for a (fleet, bike) pair. Returns True if updated."""
    normalized_role = _validate_role(role)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE fleet_bikes SET role = ? "
            "WHERE fleet_id = ? AND vehicle_id = ?",
            (normalized_role, fleet_id, vehicle_id),
        )
        return cursor.rowcount > 0


def list_bikes_in_fleet(
    fleet_id: int,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Return all bikes in a fleet as vehicle-dict + role + added_at.

    Each row is a vehicles-table dict extended with ``role`` and
    ``added_at`` from the junction. Ordered by ``added_at`` then
    vehicle_id for determinism.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT v.*, fb.role AS role, fb.added_at AS added_at "
            "FROM fleet_bikes fb "
            "JOIN vehicles v ON v.id = fb.vehicle_id "
            "WHERE fb.fleet_id = ? "
            "ORDER BY fb.added_at, v.id",
            (fleet_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_fleets_for_bike(
    vehicle_id: int,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Return all fleets that contain a given bike.

    Used by the `fleet show` command's "also appears in" footer and by
    future analytics that roll up across fleets for a single vehicle.
    Each row carries the fleet dict plus the junction `role` and
    `added_at` for reverse-lookup convenience.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT f.*, fb.role AS role, fb.added_at AS added_at "
            "FROM fleet_bikes fb "
            "JOIN fleets f ON f.id = fb.fleet_id "
            "WHERE fb.vehicle_id = ? "
            "ORDER BY f.name, f.id",
            (vehicle_id,),
        ).fetchall()
        return [dict(r) for r in rows]
