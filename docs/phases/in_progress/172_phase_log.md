# MotoDiag Phase 172 — Phase Log

**Status:** 🟡 In Progress | **Started:** 2026-04-22
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
