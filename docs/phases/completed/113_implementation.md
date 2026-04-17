# MotoDiag Phase 113 — Customer/CRM Foundation

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
New `src/motodiag/crm/` package with `customers` table, `customer_bikes` many-to-many join table (with ownership relationships), and full CRUD + ownership transfer operations. Migration 006 retrofits `customer_id` FK onto `vehicles` with a placeholder "unassigned" customer (id=1) owned by the system user, so all pre-retrofit vehicles remain valid. Foundation for Track G (shop intake with customer info), Track O (full CRM), and Track H (customer-scoped API queries).

CLI: `python -m pytest tests/test_phase113_crm_foundation.py -v`

Outputs: `src/motodiag/crm/` package (3 source files + `__init__.py`), migration 006, 35 tests

## Logic
1. **Migration 006**:
   - `CREATE TABLE customers` — id, owner_user_id (FK users), name, email, phone, address, notes, is_active, created_at, updated_at, with indexes on owner/name/email
   - `CREATE TABLE customer_bikes` (composite PK: customer_id + vehicle_id + relationship) — FKs to customers + vehicles, relationship column, assigned_at, notes
   - Seed "Unassigned" customer (id=1) owned by system user (id=1)
   - `ALTER TABLE vehicles ADD COLUMN customer_id INTEGER DEFAULT 1`
   - Rollback drops the CRM tables (customer_id column on vehicles left intact — harmless, default 1)

2. **`crm/models.py`** — Pydantic models:
   - `CustomerRelationship` enum: OWNER, PREVIOUS_OWNER, INTERESTED
   - `Customer`: id, owner_user_id, name, email, phone, address, notes, is_active, timestamps
   - `CustomerBike`: customer_id, vehicle_id, relationship, assigned_at, notes

3. **`crm/customer_repo.py`** — 8 functions:
   - `create_customer`, `get_customer`, `get_unassigned_customer`
   - `list_customers(owner_user_id, is_active)` — scoped queries
   - `search_customers(query, owner_user_id)` — LIKE match on name/email/phone
   - `update_customer` — protects unassigned customer from rename
   - `deactivate_customer` — raises ValueError for unassigned
   - `count_customers(owner_user_id, is_active)`
   - Constants: `UNASSIGNED_CUSTOMER_ID = 1`, `UNASSIGNED_CUSTOMER_NAME = "Unassigned"`

4. **`crm/customer_bikes_repo.py`** — 6 functions:
   - `link_customer_bike(customer, vehicle, relationship)` — idempotent per-relationship
   - `unlink_customer_bike(customer, vehicle, relationship=None)` — specific or all
   - `list_bikes_for_customer(customer, relationship=None)` — joined query
   - `list_customers_for_bike(vehicle, relationship=None)` — joined query
   - `get_current_owner(vehicle)` — returns single owner or None
   - `transfer_ownership(vehicle, from, to, notes)` — atomic demote + assign

## Key Concepts
- Placeholder pattern (same as system user): "Unassigned" customer id=1 owns pre-retrofit vehicles, preserves referential integrity without forcing UX decisions
- Customers scoped to user (shop) via `owner_user_id` — multi-tenant by design, prevents cross-shop customer data leakage
- Many-to-many junction with composite PK including `relationship`: a customer can simultaneously be `previous_owner` AND `interested` in the same bike (common real-world case: customer sold bike, now shopping for the next one)
- Ownership history tracking: `transfer_ownership` atomically demotes old owner → previous_owner and creates new owner link, preserving full ownership chain
- `get_current_owner` returns the single OWNER-relationship customer (returns most recent if multiple exist due to bug)
- Indexes on owner_user_id, name, email, customer_bikes.vehicle_id enable sub-second search on shop-scoped customer lists
- FK with `ON DELETE CASCADE` on customer_bikes means deleting a customer or vehicle also removes junction rows — clean data model

## Verification Checklist
- [x] Migration 006 creates customers + customer_bikes tables (2 tests)
- [x] Unassigned customer seeded at id=1 owned by system user (1 test)
- [x] customer_id column added to vehicles, defaults to 1 (2 tests)
- [x] Schema version bumped to 6 (1 test)
- [x] Rollback drops CRM tables (1 test)
- [x] CustomerRelationship enum has 3 members (1 test)
- [x] Customer model with minimal + full fields (2 tests)
- [x] Customer CRUD: create, get, list (with filters), search by email/phone/name, update, deactivate, count (11 tests)
- [x] Unassigned customer cannot be renamed or deactivated (2 tests)
- [x] customer_bikes: link as owner, idempotent, multiple relationships same customer+bike (3 tests)
- [x] Unlink specific relationship vs all relationships (2 tests)
- [x] List bikes for customer / customers for bike, with filtering (3 tests)
- [x] get_current_owner returns owner or None (2 tests)
- [x] Ownership transfer demotes old owner, assigns new owner, preserves full history (2 tests)
- [x] Backward compat: existing vehicle INSERTs default to customer_id=1, vehicles/registry CRUD unchanged (2 tests)
- [x] All 1734 pre-phase-113 tests still pass (full regression)
- [x] All 35 new Phase 113 tests pass (3.45s)

## Risks
- FK constraint on customers.owner_user_id → users.id means a test that creates customers with a non-existent owner_user_id fails. **Discovered + fixed:** test_list_by_owner now creates the users first. Same pattern applies to any future customer test.
- Migration 005 rollback became dependent on migration 006 being rolled back first (FK). **Fixed:** test_rollback_drops_auth_tables now uses `rollback_to_version(4, db)` to roll back 006 then 005. This is the correct migration-dependency ordering.
- Schema version hardcoded in test_schema_version_at_5 — fragile across retrofit phases. **Fixed:** changed to `>=5` instead of `==5`. Pattern for future phases: test lower bounds, not exact values.

## Deviations from Plan
- Added ownership history (`transfer_ownership`, preserved `previous_owner` chain) — not strictly in plan but natural fit with the data model and useful for Track O warranty/recall workflows.
- Indexed `customer_bikes.vehicle_id` for `list_customers_for_bike` performance (Track O phase 281 NHTSA recall lookup will benefit).
- Discovered cross-phase test dependency: when Phase 113's migration 006 adds FK to users, it made Phase 112's rollback test break. This is the expected behavior of layered migrations, and the fix (rollback_to_version(4)) is cleaner than the original direct rollback.

## Results
| Metric | Value |
|--------|-------|
| Files created | 4 (crm/__init__.py, crm/models.py, crm/customer_repo.py, crm/customer_bikes_repo.py) |
| Files modified | 3 (migrations.py, database.py, tests/test_phase112_auth_layer.py) |
| New Pydantic models | 2 (Customer, CustomerBike) |
| New enums | 1 (CustomerRelationship with 3 members) |
| New DB tables | 2 (customers, customer_bikes) |
| New DB columns | 1 (vehicles.customer_id) |
| New indexes | 4 (idx_customers_owner, idx_customers_name, idx_customers_email, idx_customer_bikes_vehicle) |
| New repo functions | 14 (8 customer + 6 customer-bike) |
| Tests added | 35/35 passing in 3.45s |
| Tests fixed | 2 (test_schema_version_at_5 relaxed, test_rollback_drops_auth_tables uses rollback_to_version) |
| Full regression | 1769/1769 passing in 3m 33s (zero regressions) |
| Schema version | 5 → 6 |

Key finding: The cross-phase migration dependency issue (phase 113's FK broke phase 112's rollback test) is exactly the kind of subtle integration issue the retrofit track exists to catch. Fixed once, the pattern (use `rollback_to_version(target)` not `rollback_migration(single)`) becomes standard for all future retrofit phases that add FKs to earlier migrations' tables. The ownership history capability (transfer_ownership preserving full chain) is a pleasant side effect of the many-to-many design — Track O's warranty/recall phases can now query "all customers who ever owned this bike" for outreach without additional schema work.
