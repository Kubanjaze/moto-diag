"""User repository — CRUD operations on the users table.

Phase 112: users are stored in the `users` table created by migration 005.
The "system" user (id=1) is seeded by the migration and owns all pre-retrofit
data. Do not delete the system user — it's referenced by diagnostic_sessions,
repair_plans, and known_issues as the fallback/default owner.
"""

from datetime import datetime
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.auth.models import User


SYSTEM_USER_ID = 1
SYSTEM_USERNAME = "system"


def create_user(user: User, db_path: str | None = None) -> int:
    """Create a new user. Returns the new user ID.

    password_hash can be None for non-login users (API service accounts, etc.).
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO users
               (username, email, full_name, password_hash, tier, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user.username, user.email, user.full_name,
                user.password_hash, user.tier,
                1 if user.is_active else 0,
                datetime.now().isoformat(),
            ),
        )
        return cursor.lastrowid


def get_user(user_id: int, db_path: str | None = None) -> dict | None:
    """Get a user by ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str, db_path: str | None = None) -> dict | None:
    """Get a user by username."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_users(
    db_path: str | None = None,
    tier: str | None = None,
    is_active: bool | None = None,
) -> list[dict]:
    """List users with optional filters."""
    query = "SELECT * FROM users WHERE 1=1"
    params: list = []
    if tier is not None:
        query += " AND tier = ?"
        params.append(tier)
    if is_active is not None:
        query += " AND is_active = ?"
        params.append(1 if is_active else 0)
    query += " ORDER BY id"

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def update_user(user_id: int, updates: dict, db_path: str | None = None) -> bool:
    """Update a user's fields. Returns True if any row was updated.

    Protects the system user (id=1) from tier/is_active changes that could
    break referential integrity.
    """
    allowed = {"username", "email", "full_name", "password_hash", "tier", "is_active"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return False

    # Convert bool to int for SQLite
    if "is_active" in filtered and isinstance(filtered["is_active"], bool):
        filtered["is_active"] = 1 if filtered["is_active"] else 0

    # Protect the system user from deactivation
    if user_id == SYSTEM_USER_ID and filtered.get("is_active") == 0:
        raise ValueError("Cannot deactivate the system user (id=1)")

    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [user_id]

    with get_connection(db_path) as conn:
        cursor = conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        return cursor.rowcount > 0


def deactivate_user(user_id: int, db_path: str | None = None) -> bool:
    """Soft-delete a user by setting is_active=0.

    Raises ValueError if attempting to deactivate the system user.
    """
    return update_user(user_id, {"is_active": False}, db_path)


def count_users(db_path: str | None = None, is_active: bool | None = None) -> int:
    """Count users, optionally filtered by active state."""
    if is_active is None:
        query = "SELECT COUNT(*) FROM users"
        params: tuple = ()
    else:
        query = "SELECT COUNT(*) FROM users WHERE is_active = ?"
        params = (1 if is_active else 0,)

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchone()[0]


def get_system_user(db_path: str | None = None) -> dict | None:
    """Return the seeded 'system' user (id=1) that owns pre-retrofit data."""
    return get_user(SYSTEM_USER_ID, db_path)
