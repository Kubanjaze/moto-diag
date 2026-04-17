# MotoDiag Phase 112 — User/Auth Layer Introduction

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Introduce the foundational RBAC (role-based access control) layer that all multi-user features (Track G shop management, Track Q multi-user auth, Track H API authentication) will build on. New `src/motodiag/auth/` package with users/roles/permissions. Migration 005 creates the tables, seeds the "system" user (id=1) as fallback owner for all pre-retrofit data, 4 baseline roles, 12 baseline permissions, and default role-permission mappings. Soft enforcement during retrofit — real authentication wires up in Track H.

CLI: `python -m pytest tests/test_phase112_auth_layer.py -v`

Outputs: `src/motodiag/auth/` package (`__init__.py`, `models.py`, `users_repo.py`, `roles_repo.py`), migration 005, 40 tests

## Logic
1. **Migration 005**:
   - 5 new tables: `users`, `roles`, `permissions`, `user_roles` (junction), `role_permissions` (junction)
   - Seeds "system" user (id=1, tier='company', password_hash=NULL) — owns all pre-retrofit data
   - Seeds 4 roles: OWNER, TECH, SERVICE_WRITER, APPRENTICE
   - Seeds 12 permissions: read/write garage, read/write session, run_diagnose, read/write repair_plan, export/share report, manage_users/billing/shop
   - Seeds default role-permission mappings: owner→all 12, tech→8 (diagnostic focus), service_writer→7 (customer-facing), apprentice→4 (read-mostly + supervised diagnose)
   - `ALTER TABLE diagnostic_sessions ADD COLUMN user_id INTEGER DEFAULT 1`
   - `ALTER TABLE repair_plans ADD COLUMN user_id INTEGER DEFAULT 1`
   - `ALTER TABLE known_issues ADD COLUMN created_by_user_id INTEGER DEFAULT 1`
   - Rollback drops auth tables; retrofit columns left in place (harmless, nullable-with-default)

2. **`auth/models.py`**: Pydantic models
   - `User`: id, username, email, full_name, password_hash (nullable), tier, is_active, created_at
   - `Role`: id, name, description
   - `Permission`: id, name, description
   - `UserRole`, `RolePermission` junction models
   - `RoleName` enum (4 members), `PermissionName` enum (12 members)

3. **`auth/users_repo.py`**:
   - `create_user`, `get_user`, `get_user_by_username`, `list_users` (with tier/is_active filters), `update_user`, `deactivate_user`, `count_users`, `get_system_user`
   - `SYSTEM_USER_ID = 1`, `SYSTEM_USERNAME = "system"`
   - `update_user`/`deactivate_user` raise ValueError if attempting to deactivate the system user — protects referential integrity

4. **`auth/roles_repo.py`**:
   - `create_role`, `get_role`, `get_role_by_name`, `list_roles`
   - `assign_role`, `remove_role` (idempotent via `INSERT OR IGNORE`), `list_user_roles`
   - `grant_permission`, `revoke_permission`, `list_role_permissions`
   - `user_has_permission(user_id, permission_name)` — joins user_roles + role_permissions + permissions
   - `list_user_permissions(user_id)` — deduped list across all roles

## Key Concepts
- System user (id=1) pattern solves the "who owns pre-retrofit data" problem without forcing the user to pick
- Password hashing explicitly deferred — system user has NULL password_hash; real password hashing ships with Track H (API phase 176)
- RBAC vs ABAC: chose RBAC (roles as intermediate) for simplicity; Track H may add attribute-based checks (tier, owner-of-resource)
- Permission seed covers core operations; later tracks add domain-specific permissions (work_orders, inventory, billing ops)
- Tier field on User allows per-user override of shop-level tier (e.g., owner at company tier, apprentice at individual tier)
- Deferred FK constraint: DEFAULT 1 on `user_id` columns ensures existing tests that INSERT without user_id still work
- Rollback pragmatism: migration 005 rollback only drops auth tables — leaves the user_id columns on existing tables. Full column removal would require CREATE-COPY-DROP-RENAME and provides no test value
- Idempotent assigns: `assign_role` uses `INSERT OR IGNORE` — re-assigning is a no-op, not an error

## Verification Checklist
- [x] Migration 005 creates 5 auth tables (1 test)
- [x] System user seeded at id=1 (1 test)
- [x] 4 roles seeded with correct names (1 test)
- [x] 12 permissions seeded (1 test)
- [x] Owner role has all 12 permissions (1 test)
- [x] Tech role has diagnostic permissions, not billing (1 test)
- [x] Apprentice role is read-mostly (1 test)
- [x] user_id columns added to diagnostic_sessions, repair_plans, known_issues (1 test)
- [x] Rollback drops auth tables cleanly (1 test)
- [x] RoleName/PermissionName enums have correct members (2 tests)
- [x] User model with minimal + full fields (2 tests)
- [x] users_repo CRUD: create, get, list, update, deactivate, count, system user (9 tests)
- [x] System user cannot be deactivated — raises ValueError (1 test)
- [x] roles_repo: assign/remove/list roles, idempotent assign, multi-role (4 tests)
- [x] Permission checks: user_has_permission via role, without role, dedup across roles (4 tests)
- [x] Specific role permissions: owner has manage_billing, apprentice can't write_garage (2 tests)
- [x] Custom role creation + permission grant/revoke (2 tests)
- [x] Backward compat: existing INSERT statements default to system user (3 tests)
- [x] All 1694 pre-phase-112 tests still pass (full regression)
- [x] All 40 new Phase 112 tests pass (3.40s)

## Risks
- Migration adds columns to 3 existing tables. **Mitigated:** DEFAULT 1 on all three means legacy INSERTs continue working; verified by tests.
- FK constraints not enabled (would require ON DELETE SET DEFAULT 1 style rules). **Deferred:** adding FK enforcement ships with Track H.
- Password hashing not implemented. **Documented:** password_hash field is nullable; Track H (phase 176) adds argon2/bcrypt.
- Rollback leaves orphan columns on existing tables. **Accepted:** pragmatic choice — full column removal requires complex multi-table CREATE-COPY-DROP-RENAME and orphan columns with DEFAULT 1 are harmless.

## Deviations from Plan
- Added role-permission seeding to migration 005 (not in original plan) — tests need default RBAC wiring to verify user_has_permission end-to-end.
- Skipped full column rollback in migration 005 rollback_sql — simpler to drop auth tables only; verified by test_rollback_drops_auth_tables.
- Added `count_users(is_active=None)` filter parameter (beyond plan) — useful for admin UI in Track Q.

## Results
| Metric | Value |
|--------|-------|
| Files created | 4 (auth/__init__.py, auth/models.py, auth/users_repo.py, auth/roles_repo.py) |
| Files modified | 2 (migrations.py, database.py) |
| New Pydantic models | 5 (User, Role, Permission, UserRole, RolePermission) |
| New enums | 2 (RoleName with 4 members, PermissionName with 12 members) |
| New DB tables | 5 (users, roles, permissions, user_roles, role_permissions) |
| New DB columns | 3 (user_id × 2 + created_by_user_id × 1) |
| Seeded data | 1 system user, 4 roles, 12 permissions, 31 role-permission mappings |
| Tests added | 40/40 passing in 3.40s |
| Full regression | 1734/1734 passing in 3m 13s (zero regressions) |
| Schema version | 4 → 5 |

Key finding: The auth layer sits cleanly alongside the existing schema without breaking anything. The "system user owns everything" pattern is elegant — later tracks (Track H billing, Track G shop ownership) can migrate ownership to real users as users sign up, without needing to deal with NULL user_ids. The RBAC structure is intentionally simple (user → roles → permissions) — Track H can layer ABAC on top (resource-owner checks, tier gates) without restructuring.
