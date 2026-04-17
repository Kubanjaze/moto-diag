# MotoDiag Phase 112 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-17 | **Completed:** 2026-04-17
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 13:50 — Plan written, v1.0
User/auth layer introduction. New auth/ package with users/roles/permissions RBAC model. Migration 005 creates user/role/permission tables, adds user_id FK to diagnostic_sessions/repair_plans/known_issues, seeds "system" user (id=1) to own all existing rows. 4 predefined roles (owner/tech/service_writer/apprentice), 12 base permissions. Soft enforcement only — Track H will wire real authentication.

### 2026-04-17 14:05 — Rollback SQL simplified
Initial rollback tried to CREATE-COPY-DROP-RENAME for all 3 modified tables. Realized the placeholder column lists didn't match real schema (diagnostic_sessions has 18 columns, not the 13 I guessed). Simplified to drop auth tables only — the user_id columns left behind are harmless (nullable with DEFAULT 1) and full removal would be brittle.

### 2026-04-17 14:25 — Build complete, v1.1
- Created `auth/` package: models.py (5 Pydantic models + 2 enums), users_repo.py, roles_repo.py, __init__.py exports
- Added migration 005: 5 auth tables, seeds system user + 4 roles + 12 permissions + 31 role-permission mappings, adds user_id columns to 3 existing tables
- Bumped SCHEMA_VERSION 4 → 5
- 40 new tests in test_phase112_auth_layer.py (all passing in 3.40s)
- Full regression: 1734/1734 passing in 3m 13s — zero regressions
- All 3 existing table INSERTs confirmed to default to system user (id=1)
