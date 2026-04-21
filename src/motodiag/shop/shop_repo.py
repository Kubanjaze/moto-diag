"""Shop profile repository — CRUD over the ``shops`` table.

Phase 160. First Track G phase. Establishes the shop-identity layer that
every downstream track-G object (intake_visits now; work orders, line
items, invoices later) attaches to via ``shop_id``. Solo mechanics run a
single shop; franchises run many. ``UNIQUE(owner_user_id, name)`` scopes
names per user so two owners can both have a shop called "Main Street
Cycles."

Design notes
------------

- **FK delete semantics.** The ``shops`` table itself has
  ``owner_user_id -> users(id) ON DELETE SET DEFAULT`` (preserves
  orphaned shops attributed to system user id=1). Downstream children
  (``intake_visits.shop_id``) use CASCADE — deleting a shop wipes its
  intake history. This is deliberate: shop deletion is rare, explicit,
  and should prompt the caller; retaining orphan intakes pointing at a
  dead shop_id produces more confusion than value.

- **Soft delete via ``deactivate_shop``.** The default deletion path is
  ``is_active=0`` (soft). Hard delete via ``delete_shop`` exists for
  cases where a shop was created in error — tests cover both paths.

- **Update whitelist.** ``update_shop`` accepts a ``updates: dict`` but
  filters keys against ``_UPDATABLE_FIELDS`` before building the SQL.
  Anything outside the whitelist is silently dropped; callers can
  whitelist-check first if strict-mode is needed.

- **Owner scoping with default-id=1.** Mirrors the Phase 113 customer
  and Phase 150 fleet patterns. Real session-threading lands when Phase
  112's auth layer wires into the CLI runtime.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Optional

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ShopNotFoundError(ValueError):
    """Raised when a shop identifier (int id or str name) does not resolve."""


class ShopNameExistsError(ValueError):
    """Raised when ``create_shop`` would violate UNIQUE(owner_user_id, name)."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


# Whitelist of fields ``update_shop`` is allowed to mutate. Timestamps,
# id, owner_user_id, and is_active are managed by dedicated functions.
_UPDATABLE_FIELDS: frozenset[str] = frozenset({
    "name",
    "address",
    "city",
    "state",
    "zip",
    "phone",
    "email",
    "tax_id",
    "hours_json",
})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_hours_json(hours_json: Optional[str]) -> Optional[str]:
    """Sanity-check hours_json.

    None / empty → returned as-is. Non-empty must parse as a JSON object
    mapping day keys to "HH:MM-HH:MM" ranges. We do NOT enforce day-key
    names strictly (shops may use locale variants); we only enforce that
    the payload parses and is an object.
    """
    if hours_json is None or str(hours_json).strip() == "":
        return None
    try:
        parsed = json.loads(hours_json)
    except (ValueError, TypeError) as e:
        raise ValueError(f"hours_json must be valid JSON: {e}") from e
    if not isinstance(parsed, dict):
        raise ValueError(
            f"hours_json must be a JSON object, got {type(parsed).__name__}"
        )
    return str(hours_json)


def _resolve_shop_id(
    identifier: int | str,
    owner_user_id: int = 1,
    db_path: Optional[str] = None,
) -> int:
    """Resolve a shop identifier (int id OR str name) to its integer id.

    Raises :class:`ShopNotFoundError` on miss.
    """
    if identifier is None:
        raise ShopNotFoundError("shop identifier must not be None")
    if isinstance(identifier, bool):
        raise ShopNotFoundError(
            f"shop identifier must be int or str (got bool {identifier!r})"
        )
    with get_connection(db_path) as conn:
        if isinstance(identifier, int):
            row = conn.execute(
                "SELECT id FROM shops WHERE id = ?", (identifier,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id FROM shops WHERE name = ? AND owner_user_id = ?",
                (str(identifier), owner_user_id),
            ).fetchone()
    if row is None:
        raise ShopNotFoundError(f"shop not found: {identifier!r}")
    return int(row["id"])


# ---------------------------------------------------------------------------
# Shop CRUD
# ---------------------------------------------------------------------------


def create_shop(
    name: str,
    address: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    tax_id: Optional[str] = None,
    hours_json: Optional[str] = None,
    owner_user_id: int = 1,
    db_path: Optional[str] = None,
) -> int:
    """Create a shop. Returns the new shop id.

    Raises :class:`ShopNameExistsError` on UNIQUE(owner_user_id, name)
    violation; re-thrown from SQLite's IntegrityError so the CLI can
    render a clean message.

    ``hours_json`` is validated as JSON if supplied.
    """
    if not name or not str(name).strip():
        raise ValueError("shop name must not be empty")
    hours_json = _validate_hours_json(hours_json)
    with get_connection(db_path) as conn:
        try:
            cursor = conn.execute(
                """INSERT INTO shops
                   (owner_user_id, name, address, city, state, zip, phone,
                    email, tax_id, hours_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    owner_user_id, str(name).strip(), address, city, state,
                    zip, phone, email, tax_id, hours_json,
                ),
            )
        except sqlite3.IntegrityError as e:
            raise ShopNameExistsError(
                f"shop name already exists for owner_user_id={owner_user_id}: "
                f"{name!r}"
            ) from e
        return int(cursor.lastrowid)


def get_shop(shop_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    """Fetch a shop row by id. Returns None when missing."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM shops WHERE id = ?", (shop_id,),
        ).fetchone()
        return dict(row) if row else None


def get_shop_by_name(
    name: str,
    owner_user_id: int = 1,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """Fetch a shop row by (owner_user_id, name). Returns None when missing."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM shops WHERE name = ? AND owner_user_id = ?",
            (str(name), owner_user_id),
        ).fetchone()
        return dict(row) if row else None


def list_shops(
    owner_user_id: Optional[int] = 1,
    include_inactive: bool = False,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List shops with LEFT JOIN open_intake_count. Ordered by name.

    ``owner_user_id=None`` lists every shop regardless of owner.
    ``include_inactive=False`` filters out soft-deleted shops.
    """
    query = (
        "SELECT s.*, "
        "       COALESCE(SUM(CASE WHEN iv.status = 'open' THEN 1 ELSE 0 END), 0) "
        "         AS open_intake_count, "
        "       COUNT(iv.id) AS total_intake_count "
        "FROM shops s "
        "LEFT JOIN intake_visits iv ON iv.shop_id = s.id "
    )
    conditions: list[str] = []
    params: list = []
    if owner_user_id is not None:
        conditions.append("s.owner_user_id = ?")
        params.append(owner_user_id)
    if not include_inactive:
        conditions.append("s.is_active = 1")
    if conditions:
        query += "WHERE " + " AND ".join(conditions) + " "
    query += "GROUP BY s.id ORDER BY s.name, s.id"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_shop(
    shop_id: int,
    updates: dict,
    db_path: Optional[str] = None,
) -> bool:
    """Update whitelisted fields on a shop row. Returns True on success.

    Raises :class:`ShopNotFoundError` when the row does not exist.
    Raises :class:`ShopNameExistsError` when a rename collides with an
    existing (owner, name) pair. ``hours_json`` if present is validated.
    """
    if not isinstance(updates, dict):
        raise TypeError(f"updates must be a dict, got {type(updates).__name__}")
    # Filter to the whitelist; silently drop unknown keys.
    filtered = {k: v for k, v in updates.items() if k in _UPDATABLE_FIELDS}
    if not filtered:
        return False
    if "hours_json" in filtered:
        filtered["hours_json"] = _validate_hours_json(filtered["hours_json"])
    if "name" in filtered:
        new_name = str(filtered["name"]).strip()
        if not new_name:
            raise ValueError("shop name must not be empty")
        filtered["name"] = new_name

    set_clauses = ", ".join(f"{k} = ?" for k in filtered.keys())
    params: list = list(filtered.values())
    params.append(datetime.now().isoformat())
    params.append(shop_id)

    with get_connection(db_path) as conn:
        # Verify shop exists; cheap guard with a clean error.
        row = conn.execute(
            "SELECT id, owner_user_id FROM shops WHERE id = ?", (shop_id,),
        ).fetchone()
        if row is None:
            raise ShopNotFoundError(f"shop not found: id={shop_id}")
        try:
            cursor = conn.execute(
                f"UPDATE shops SET {set_clauses}, updated_at = ? WHERE id = ?",
                params,
            )
        except sqlite3.IntegrityError as e:
            raise ShopNameExistsError(
                f"shop name already exists for owner_user_id="
                f"{row['owner_user_id']}: {filtered.get('name')!r}"
            ) from e
        return cursor.rowcount > 0


def deactivate_shop(shop_id: int, db_path: Optional[str] = None) -> bool:
    """Soft-delete a shop by setting ``is_active = 0``. Preserves history."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM shops WHERE id = ?", (shop_id,),
        ).fetchone()
        if row is None:
            raise ShopNotFoundError(f"shop not found: id={shop_id}")
        cursor = conn.execute(
            "UPDATE shops SET is_active = 0, updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), shop_id),
        )
        return cursor.rowcount > 0


def reactivate_shop(shop_id: int, db_path: Optional[str] = None) -> bool:
    """Reverse :func:`deactivate_shop`."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM shops WHERE id = ?", (shop_id,),
        ).fetchone()
        if row is None:
            raise ShopNotFoundError(f"shop not found: id={shop_id}")
        cursor = conn.execute(
            "UPDATE shops SET is_active = 1, updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), shop_id),
        )
        return cursor.rowcount > 0


def delete_shop(shop_id: int, db_path: Optional[str] = None) -> bool:
    """Hard-delete a shop. CASCADE drops its intake_visits.

    Caller is responsible for user confirmation (CLI handles this).
    Raises :class:`ShopNotFoundError` when the row does not exist.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM shops WHERE id = ?", (shop_id,),
        ).fetchone()
        if row is None:
            raise ShopNotFoundError(f"shop not found: id={shop_id}")
        # Foreign-key cascade must be armed for the delete to remove
        # intake_visits children. The connection manager enables it
        # globally; this is belt-and-suspenders for callers that bypass
        # the manager.
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.execute("DELETE FROM shops WHERE id = ?", (shop_id,))
        return cursor.rowcount > 0
