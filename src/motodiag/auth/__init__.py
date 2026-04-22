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

# Phase 176 additions: API keys, rate limiting, FastAPI deps
from motodiag.auth.api_key_repo import (
    ApiKey,
    ApiKeyNotFoundError,
    InvalidApiKeyError,
    create_api_key,
    generate_api_key,
    get_api_key_by_id,
    get_api_key_by_prefix,
    hash_api_key,
    key_prefix,
    list_api_keys,
    revoke_api_key,
    verify_api_key,
)
from motodiag.auth.rate_limiter import (
    RateLimitExceededError,
    RateLimitState,
    RateLimiter,
    get_rate_limiter,
    reset_rate_limiter,
)
from motodiag.auth.deps import (
    API_KEY_HEADER,
    AuthedUser,
    SUBSCRIPTION_TIERS,
    SubscriptionRequiredError,
    SubscriptionTier,
    SubscriptionTierInsufficientError,
    get_api_key,
    get_current_user,
    require_api_key,
    require_tier,
    tier_meets,
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
    # Phase 176: API keys
    "ApiKey", "ApiKeyNotFoundError", "InvalidApiKeyError",
    "create_api_key", "generate_api_key",
    "get_api_key_by_id", "get_api_key_by_prefix",
    "hash_api_key", "key_prefix",
    "list_api_keys", "revoke_api_key", "verify_api_key",
    # Phase 176: rate limiter
    "RateLimitExceededError", "RateLimitState", "RateLimiter",
    "get_rate_limiter", "reset_rate_limiter",
    # Phase 176: FastAPI deps
    "API_KEY_HEADER", "AuthedUser", "SUBSCRIPTION_TIERS",
    "SubscriptionRequiredError", "SubscriptionTier",
    "SubscriptionTierInsufficientError",
    "get_api_key", "get_current_user",
    "require_api_key", "require_tier", "tier_meets",
]
