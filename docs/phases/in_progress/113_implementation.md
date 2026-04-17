# MotoDiag Phase 113 — Customer/CRM Foundation

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
New `src/motodiag/crm/` package with `customers` table, `customer_bikes` join table, and CRUD operations. Retrofit `customer_id` FK onto `vehicles` with a placeholder "unassigned" customer (id=1) so existing vehicles remain valid. Customers belong to users (FK `owner_user_id` → users.id) so shop owners scope their own customer lists.

CLI: `python -m pytest tests/test_phase113_crm_foundation.py -v`

Outputs: `src/motodiag/crm/` package, migration 006, tests

## Logic
1. **Migration 006**:
   - `CREATE TABLE customers` — id, owner_user_id (FK users), name, email, phone, address, notes, is_active, created_at, updated_at
   - `CREATE TABLE customer_bikes` — customer_id (FK), vehicle_id (FK), relationship ('owner'/'previous_owner'/'interested'), assigned_at, notes
   - Seed "unassigned" customer (id=1) owned by system user (id=1)
   - `ALTER TABLE vehicles ADD COLUMN customer_id INTEGER DEFAULT 1`
   - Existing vehicles → customer_id=1 (unassigned)

2. **`src/motodiag/crm/models.py`** — `Customer`, `CustomerBike`, `CustomerRelationship` enum

3. **`src/motodiag/crm/customer_repo.py`** — CRUD + search (by name/email/phone)

4. **`src/motodiag/crm/customer_bikes_repo.py`** — link/unlink customers to vehicles, list bikes for customer, list customers for bike (for previous-owner tracking)

## Key Concepts
- Placeholder "unassigned" customer preserves referential integrity — same pattern as system user
- owner_user_id scopes customers to shops: solo mechanic sees their own customers, shop sees shop's customers
- customer_bikes is a many-to-many: a customer can own multiple bikes, a bike can have multiple historical owners
- CustomerRelationship enum captures ownership history (owner, previous_owner, interested)
- Backward compat: existing vehicle rows auto-assigned to placeholder customer

## Verification Checklist
- [ ] Migration 006 creates customers + customer_bikes tables
- [ ] Unassigned placeholder customer seeded at id=1
- [ ] customer_id column added to vehicles, defaults to 1
- [ ] Existing vehicles get customer_id=1 after migration
- [ ] Customer CRUD (create, get, list, search by email/phone, update, deactivate)
- [ ] customer_bikes linking/unlinking works
- [ ] Ownership history tracked (owner/previous_owner/interested)
- [ ] All 1734 existing tests still pass
