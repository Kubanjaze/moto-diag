"""Auth package — users, roles, permissions, RBAC.

Phase 112 (Retrofit): introduces the foundational auth layer that all
multi-user features (Track G shop management, Track Q multi-user auth,
Track H API authentication) will build on. Enforcement is soft at this
stage — auth module exists, but CLI commands don't check it yet. Real
authentication wiring happens when Track H adds the API and Stripe billing.

System user (id=1) owns all pre-retrofit rows via migration 005 defaults.
"""

from motodiag.auth.models import (
    User, Role, Permission,
    UserRole, RolePermission,
    RoleName, PermissionName,
)
from motodiag.auth.users_repo import (
    create_user, get_user, get_user_by_username, list_users,
    update_user, deactivate_user, get_system_user, count_users,
)
from motodiag.auth.roles_repo import (
    create_role, get_role, get_role_by_name, list_roles,
    assign_role, remove_role, list_user_roles,
    grant_permission, revoke_permission, list_role_permissions,
    user_has_permission, list_user_permissions,
)

__all__ = [
    # Models
    "User", "Role", "Permission", "UserRole", "RolePermission",
    "RoleName", "PermissionName",
    # Users repo
    "create_user", "get_user", "get_user_by_username", "list_users",
    "update_user", "deactivate_user", "get_system_user", "count_users",
    # Roles repo
    "create_role", "get_role", "get_role_by_name", "list_roles",
    "assign_role", "remove_role", "list_user_roles",
    "grant_permission", "revoke_permission", "list_role_permissions",
    "user_has_permission", "list_user_permissions",
]
