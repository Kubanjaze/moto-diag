# MotoDiag Phase 172 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-22 | **Completed:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written

Plan v1.0 authored in-session. Scope: shop-scoped RBAC + work-order
reassignment with audit-logged history. Reuses Phase 112 users / roles /
permissions tables; adds `shop_members` + `work_order_assignments` via
migration 035.

Key design decisions:
- Shop-scoped RBAC sits on top of Phase 112 global RBAC — a user has a
  per-shop role (owner / tech / service_writer / apprentice) that's
  independent from their `users.tier` subscription tier.
- Reassignment is additive history — `work_order_assignments` rows get
  `unassigned_at` stamped when closed; `work_orders.
  assigned_mechanic_user_id` remains the fast-path current pointer.
- `reassign_work_order` writes back via Phase 161's `update_work_order`
  whitelist (no raw `UPDATE work_orders` SQL) — same discipline as
  Phase 163/167. Anti-regression grep test enforces.
- `has_shop_permission(shop_id, user_id, perm)` walks
  `shop_members.role → roles → role_permissions → permissions.name`.
- Phase 160 `create_shop` doesn't auto-seed an owner member; Phase 172
  provides `seed_first_owner` + CLI `member add --role owner` for
  backfill + new-shop cases.
- Mechanic-not-in-shop guard on reassignment prevents cross-shop
  mis-assignment.

Migration 035 creates two tables + 4 indexes; rollback drops cleanly.
No Phase 112 schema touched.

### 2026-04-22 — Build complete

Files shipped:

1. **Migration 035** (schema v34→v35): `shop_members` (user_id + shop_id
   composite PK; role CHECK ∈ {owner, tech, service_writer, apprentice};
   is_active soft-delete flag; user + shop CASCADE) + `work_order_
   assignments` (id PK; wo_id CASCADE; mechanic_user_id SET NULL so
   history survives user deletion; assigned_by_user_id SET NULL;
   assigned_at + unassigned_at + reason for audit). 4 indexes.

2. **`shop/rbac.py`** (~475 LoC):
   - 3 Pydantic models: `ShopMember`, `WorkOrderAssignment`,
     `MechanicWorkload`
   - 4 exceptions: `ShopMembershipNotFoundError`, `InvalidRoleError`,
     `PermissionDenied`, `MechanicNotInShopError`
   - 14 public functions across membership CRUD (`add_shop_member`,
     `get_shop_member`, `list_shop_members`, `set_member_role`,
     `deactivate_member`, `reactivate_member`, `list_shops_for_user`,
     `seed_first_owner`, `list_shop_mechanics`), shop-scoped permission
     checks (`has_shop_permission`, `require_shop_permission`), and
     work-order reassignment flow (`reassign_work_order`,
     `list_work_order_assignments`, `current_assignment`,
     `mechanic_workload`)

3. **`shop/__init__.py`** +26 re-exports.

4. **`cli/shop.py`** +234 LoC:
   - New `member` subgroup with **5 subcommands** (`add`, `list`,
     `set-role`, `deactivate`, `reactivate`) + new table renderer
   - `work-order` subgroup extended with **2 new subcommands**
     (`reassign`, `assignments`) — total work-order subgroup now 14
     subcommands (was 12)
   - Total shop CLI: **15 subgroups, 113 subcommands**

5. **`tests/test_phase172_rbac.py`** (32 tests across 6 classes):
   - `TestMigration035` (4): schema version, tables, CHECK, rollback
   - `TestMembership` (10): add/reactivate/list/filter/inactive/set-role/
     deactivate/seed_first_owner idempotent
   - `TestShopPermissions` (5): owner/tech/apprentice checks + inactive-
     member denial + require_shop_permission raises
   - `TestReassignment` (7): history logging, prior-row closure, mock-
     patch audit of Phase 161 whitelist use, unassign preserves history,
     non-shop/apprentice/terminal-WO rejection
   - `TestRbacCLI` (5): member add/list/set-role/deactivate + work-order
     reassign/assignments CLI round-trip
   - `TestAntiRegression` (1): grep no raw `UPDATE work_orders` SQL
     (with comment/docstring strip)

**Bug fixes during build:**
- **Bug fix #1: anti-regression grep false-positive**. First pass of
  `test_no_raw_update_work_orders_in_rbac` matched `UPDATE work_orders`
  inside the module docstring (which explicitly mentions the forbidden
  pattern as documentation). Fixed by stripping `#`-line-comments and
  `"""..."""` docstrings before applying the regex, and adding a `\b`
  word boundary after `work_orders` to prevent false matches against
  hypothetical `work_orders_foo` columns.
- **Bug fix #2: Phase 171 anti-regression widened.** Phase 171's
  `test_no_migration_added` asserted `SCHEMA_VERSION == 34` exactly,
  which breaks on every downstream migration. Widened to `>= 34`. The
  semantic intent (Phase 171 is read-only) is still captured because
  the test lives in Phase 171's file — no migration entry was added
  by Phase 171's commits.

Single-pass-after-fix: **32 GREEN in 22.65s.**

**Targeted regression: 605 GREEN in 384.10s (6m 24s)** covering Phase
113 + 118 + 131 + 153 + Track G 160-172 + 162.5. Zero regressions after
widening the one brittle Phase 171 assertion.

Build deviations vs plan:
- Anti-regression grep strips comments/docstrings.
- Phase 171 test widened (brittle exact-version assertion → inequality).
- Dropped CLI `list_shops_for_user` subcommand (data-model tool, not
  mechanic workflow — retained as public function for Phase 173 +
  transport consumers).
- 32 tests vs ~31 planned.

### 2026-04-22 — Documentation finalization

`implementation.md` promoted to v1.1. Verification Checklist all `[x]`.
Deviations section lists the three build-time changes. Results table
populated.

Project-level updates:
- `implementation.md` schema_version footnote v34 → v35
- `implementation.md` Database Tables: append `shop_members` +
  `work_order_assignments`
- `implementation.md` Phase History: append Phase 172 row
- `implementation.md` Shop CLI Commands: 106 → 113 subcommands; added
  `motodiag shop member` row (15th subgroup); `motodiag shop
  work-order` row bumped from 12 → 14 subcommands
- `phase_log.md` project-level: Phase 172 closure entry
- `docs/ROADMAP.md`: Phase 172 row → ✅
- Project version 0.10.3 → **0.10.4**

**Key finding:** Phase 172 validates that shop-scoped RBAC stacks cleanly
on Phase 112 global RBAC without schema duplication. `has_shop_permission`
walks `shop_members.role → roles → role_permissions → permissions` —
the same catalog Phase 112 populated. Phase 161's write-back-through-
whitelist discipline extends naturally to reassignment: `reassign_work_
order` calls `update_work_order(wo_id, {"assigned_mechanic_user_id":
...})` rather than raw SQL, keeping the anti-regression grep tests
happy. Pattern recommendation: any future Phase that mutates
`work_orders` should duplicate the grep test in its own test file —
cheap, catches entire classes of drift before CI.
