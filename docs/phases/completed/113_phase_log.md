# MotoDiag Phase 113 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-17 | **Completed:** 2026-04-17
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 14:30 — Plan written, v1.0
Customer/CRM foundation. New crm/ package with customers + customer_bikes tables. Migration 006 seeds "unassigned" placeholder customer, retrofits customer_id FK onto vehicles. owner_user_id scopes customers per shop/user. Backward compat via DEFAULT 1 placeholder pattern.

### 2026-04-17 14:55 — Cross-phase test dependency discovered
After migration 006 added FK customers.owner_user_id → users.id, phase 112's test_rollback_drops_auth_tables started failing: rolling back migration 005 (drop users) fails when migration 006's customers table still exists. Fixed by changing that test to use rollback_to_version(4, db) instead of rollback_migration(m=005). This is the correct pattern — rolling back a migration requires rolling back all later migrations first.

Also relaxed test_schema_version_at_5 from `== 5` to `>= 5` so it survives future retrofit phase bumps.

### 2026-04-17 15:10 — Test FK issue fixed
test_list_by_owner initially used owner_user_id=2/3 directly without creating those users — FK constraint failed. Fixed by creating the users first via auth.users_repo.create_user.

### 2026-04-17 15:20 — Build complete, v1.1
- Created crm/ package: 2 Pydantic models + 1 enum + 14 repo functions across 2 files
- Migration 006: 2 new tables + 4 indexes + unassigned customer seed + vehicles.customer_id column
- Bumped SCHEMA_VERSION 5 → 6
- 35 new tests in test_phase113_crm_foundation.py (all passing in 3.45s)
- 2 existing tests fixed (phase 112) to accommodate cross-phase migration dependency
- Full regression: 1769/1769 passing in 3m 33s — zero regressions
- Ownership transfer workflow works atomically (demote old owner + assign new)
- History preserved across multiple transfers (A → B → C keeps A and B as previous_owner)
