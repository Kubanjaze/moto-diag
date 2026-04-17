"""Auth layer Pydantic models.

Phase 112: User/Role/Permission/junction models + predefined role/permission
name enums. Password hashing is NOT implemented yet — the `password_hash`
field is nullable so the seed "system" user (id=1) can exist without a
password, and real authentication wiring arrives with Track H (API).
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RoleName(str, Enum):
    """Predefined role names.

    Used as canonical role slugs in the `roles` table. Additional custom
    roles can be added via `create_role()`, but these four cover the
    baseline RBAC needs for shops.
    """
    OWNER = "owner"                  # Shop owner — full access
    TECH = "tech"                    # Certified mechanic — diagnose/repair
    SERVICE_WRITER = "service_writer"  # Customer-facing, scheduling, invoicing
    APPRENTICE = "apprentice"        # Limited write access, read-mostly


class PermissionName(str, Enum):
    """Predefined permission slugs.

    Phase 112 seed covers the core CRUD + domain operations. Additional
    permissions added by later tracks (Track G shop mgmt adds work_order
    permissions, Track O adds billing/inventory, etc.).
    """
    # Garage (vehicles)
    READ_GARAGE = "read_garage"
    WRITE_GARAGE = "write_garage"
    # Diagnostic sessions
    READ_SESSION = "read_session"
    WRITE_SESSION = "write_session"
    # AI diagnosis
    RUN_DIAGNOSE = "run_diagnose"
    # Repair plans
    READ_REPAIR_PLAN = "read_repair_plan"
    WRITE_REPAIR_PLAN = "write_repair_plan"
    # Reports
    EXPORT_REPORT = "export_report"
    SHARE_REPORT = "share_report"
    # Admin
    MANAGE_USERS = "manage_users"
    MANAGE_BILLING = "manage_billing"
    MANAGE_SHOP = "manage_shop"


class User(BaseModel):
    """A user/account in the system.

    System user: id=1, username='system', no password. Owns all pre-retrofit
    data for referential integrity. Real users are created via create_user().
    """
    id: Optional[int] = Field(None, description="Primary key")
    username: str = Field(..., description="Unique username / login handle")
    email: Optional[str] = Field(None, description="Email address (optional for placeholder users)")
    full_name: Optional[str] = Field(None, description="Display name")
    password_hash: Optional[str] = Field(
        None,
        description="Password hash (argon2/bcrypt). NULL for system/placeholder users.",
    )
    tier: str = Field(
        default="individual",
        description="Per-user subscription tier override (individual/shop/company). Usually matches shop-level tier.",
    )
    is_active: bool = Field(default=True, description="Whether the user can log in")
    created_at: Optional[datetime] = Field(None, description="Account creation timestamp")


class Role(BaseModel):
    """A role in the RBAC system — groups permissions."""
    id: Optional[int] = None
    name: str = Field(..., description="Role slug (e.g., 'owner', 'tech')")
    description: Optional[str] = Field(None, description="Human-readable role description")


class Permission(BaseModel):
    """A permission in the RBAC system — represents an allowed action."""
    id: Optional[int] = None
    name: str = Field(..., description="Permission slug (e.g., 'write_garage')")
    description: Optional[str] = Field(None, description="Human-readable permission description")


class UserRole(BaseModel):
    """Junction record: a user has a role."""
    user_id: int
    role_id: int
    assigned_at: Optional[datetime] = None


class RolePermission(BaseModel):
    """Junction record: a role grants a permission."""
    role_id: int
    permission_id: int
