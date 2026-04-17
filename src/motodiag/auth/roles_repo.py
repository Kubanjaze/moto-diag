"""Role + permission repository — RBAC operations.

Phase 112: role creation, permission grants, user-role assignments,
permission checking. Tables created by migration 005.
"""

from datetime import datetime

from motodiag.core.database import get_connection
from motodiag.auth.models import Role, Permission


def create_role(role: Role, db_path: str | None = None) -> int:
    """Create a new role. Returns the new role ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO roles (name, description) VALUES (?, ?)",
            (role.name, role.description),
        )
        return cursor.lastrowid


def get_role(role_id: int, db_path: str | None = None) -> dict | None:
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_role_by_name(name: str, db_path: str | None = None) -> dict | None:
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM roles WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_roles(db_path: str | None = None) -> list[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM roles ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]


def assign_role(user_id: int, role_id: int, db_path: str | None = None) -> None:
    """Assign a role to a user. Idempotent — re-assigning does nothing."""
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
            (user_id, role_id, datetime.now().isoformat()),
        )


def remove_role(user_id: int, role_id: int, db_path: str | None = None) -> bool:
    """Remove a role assignment from a user. Returns True if anything was removed."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM user_roles WHERE user_id = ? AND role_id = ?",
            (user_id, role_id),
        )
        return cursor.rowcount > 0


def list_user_roles(user_id: int, db_path: str | None = None) -> list[dict]:
    """List all roles assigned to a user."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT r.* FROM roles r
               INNER JOIN user_roles ur ON ur.role_id = r.id
               WHERE ur.user_id = ?
               ORDER BY r.name""",
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def grant_permission(role_id: int, permission_id: int, db_path: str | None = None) -> None:
    """Grant a permission to a role. Idempotent."""
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
            (role_id, permission_id),
        )


def revoke_permission(role_id: int, permission_id: int, db_path: str | None = None) -> bool:
    """Revoke a permission from a role. Returns True if anything was removed."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM role_permissions WHERE role_id = ? AND permission_id = ?",
            (role_id, permission_id),
        )
        return cursor.rowcount > 0


def list_role_permissions(role_id: int, db_path: str | None = None) -> list[dict]:
    """List all permissions granted to a role."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT p.* FROM permissions p
               INNER JOIN role_permissions rp ON rp.permission_id = p.id
               WHERE rp.role_id = ?
               ORDER BY p.name""",
            (role_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def user_has_permission(user_id: int, permission_name: str, db_path: str | None = None) -> bool:
    """Check whether a user has a specific permission via any of their roles.

    Returns True if any role the user holds grants the named permission.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT COUNT(*) FROM role_permissions rp
               INNER JOIN user_roles ur ON ur.role_id = rp.role_id
               INNER JOIN permissions p ON p.id = rp.permission_id
               WHERE ur.user_id = ? AND p.name = ?""",
            (user_id, permission_name),
        )
        return cursor.fetchone()[0] > 0


def list_user_permissions(user_id: int, db_path: str | None = None) -> list[str]:
    """Return a deduped list of permission names a user has via all roles."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT DISTINCT p.name FROM permissions p
               INNER JOIN role_permissions rp ON rp.permission_id = p.id
               INNER JOIN user_roles ur ON ur.role_id = rp.role_id
               WHERE ur.user_id = ?
               ORDER BY p.name""",
            (user_id,),
        )
        return [row[0] for row in cursor.fetchall()]
