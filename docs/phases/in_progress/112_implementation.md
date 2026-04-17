# MotoDiag Phase 112 — User/Auth Layer Introduction

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Introduce the foundational user/auth layer that all multi-user features (Track G shop management, Track Q multi-user auth, Track H API authentication) will build on. New `src/motodiag/auth/` package. Retroactively add `user_id` foreign keys to `diagnostic_sessions`, `repair_plans`, and `known_issues` tables with a migration that creates a "system" placeholder user to own all existing rows. No breaking changes to existing CLI — auth is passive/advisory at this stage.

CLI: `python -m pytest tests/test_phase112_auth_layer.py -v`

Outputs: `src/motodiag/auth/` package (users, roles, permissions, users_repo, roles_repo), Migration 005, updated `core/models.py`, tests

## Logic
1. **Migration 005** (`core/migrations.py`):
   - `CREATE TABLE users` — id, username (unique), email, full_name, password_hash (nullable for system/placeholder), tier (individual/shop/company), is_active, created_at
   - `CREATE TABLE roles` — id, name (unique), description
   - `CREATE TABLE user_roles` — user_id FK, role_id FK, assigned_at (junction table)
   - `CREATE TABLE permissions` — id, name (unique), description
   - `CREATE TABLE role_permissions` — role_id FK, permission_id FK (junction)
   - Insert seed data: "system" user (id=1, placeholder for orphaned rows), 4 roles (owner/tech/service_writer/apprentice), 12 base permissions
   - `ALTER TABLE diagnostic_sessions ADD COLUMN user_id INTEGER DEFAULT 1`
   - `ALTER TABLE repair_plans ADD COLUMN user_id INTEGER DEFAULT 1`
   - `ALTER TABLE known_issues ADD COLUMN created_by_user_id INTEGER DEFAULT 1`
   - Existing rows → all owned by "system" user

2. **`src/motodiag/auth/models.py`** — Pydantic models:
   - `User`: id, username, email, full_name, tier, is_active, created_at
   - `Role`: id, name, description
   - `Permission`: id, name, description
   - `UserRole` / `RolePermission` junction models
   - Predefined role names: OWNER, TECH, SERVICE_WRITER, APPRENTICE
   - Predefined permission enum: read_garage, write_garage, read_session, write_session, diagnose, export_report, manage_users, manage_billing, etc.

3. **`src/motodiag/auth/users_repo.py`** — User CRUD:
   - `create_user(user)`, `get_user(user_id)`, `get_user_by_username(username)`, `list_users()`, `update_user()`, `deactivate_user()`, `get_system_user()`

4. **`src/motodiag/auth/roles_repo.py`** — Role + permission CRUD:
   - `create_role()`, `get_role()`, `assign_role()`, `remove_role()`, `user_has_permission()`, `list_user_permissions()`

5. **`src/motodiag/auth/__init__.py`** — Package exports

## Key Concepts
- System user (id=1) owns all existing rows — preserves data integrity without requiring user choice
- Password_hash nullable at this stage — actual authentication arrives with Track H (API phase 176)
- Role-based access control (RBAC): users → roles → permissions
- 4 predefined roles: owner (everything), tech (diagnose/repair), service_writer (customer-facing), apprentice (limited write)
- 12 seed permissions covering major operations; more added as tracks mature
- Soft enforcement during retrofit: auth module exists, but CLI commands don't check it yet (enforcement happens in Track H)
- Tier field on User allows per-user tier override (relevant for shop tier where owner = shop, techs = individual)
- Foreign keys use SET DEFAULT to 1 (system user) if user is deleted — prevents orphans

## Verification Checklist
- [ ] Migration 005 creates users/roles/permissions/junction tables
- [ ] System user seeded with id=1
- [ ] 4 roles seeded (owner, tech, service_writer, apprentice)
- [ ] 12 permissions seeded
- [ ] user_id column added to diagnostic_sessions, repair_plans, known_issues
- [ ] Existing rows default to user_id=1 (system user)
- [ ] users_repo CRUD works
- [ ] roles_repo assignment and permission lookup works
- [ ] All 1694 existing tests still pass
- [ ] New tests cover user creation, role assignment, permission checks
- [ ] No existing CLI command broken

## Risks
- Migration adds user_id to 3 existing tables — must verify all existing tests continue to work
- FK constraints could break INSERT statements in existing tests if not defaulted
- Password hashing not implemented yet — models must accept nullable password_hash for system user
