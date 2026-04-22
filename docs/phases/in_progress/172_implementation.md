# MotoDiag Phase 172 — Multi-Mechanic Assignment + Shop-Scoped RBAC

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Shop-scoped membership + role management on top of Phase 112's existing
`users` / `roles` / `permissions` substrate. A user can be a member of
multiple shops with a different role per shop (owner at one, tech at
another). Work-order assignment gets an audit trail
(`work_order_assignments`) so a WO that moves between mechanics over
its lifetime preserves history — load-bearing for Phase 171 per-
mechanic analytics and Phase 173 rule conditions like "reassign when
mechanic overrun rate exceeds X".

CLI — `motodiag shop member {add, list, set-role, deactivate,
reactivate}` + `work-order {reassign, assignments}` (2 new
subcommands on the existing work-order subgroup) — **7 new
subcommands**.

**Design rule:** zero AI, zero tokens. Pure SQL + permission math.
Reuses Phase 112 `users`/`roles`/`permissions` tables; does NOT touch
Phase 112 schema. Adds `shop_members` + `work_order_assignments`
tables (migration 035).

Outputs:
- Migration 035 (~60 LoC): 2 new tables + 4 indexes + seed first-shop-
  owner on shop creation (trigger-free — caller responsibility).
- `src/motodiag/shop/rbac.py` (~450 LoC) — member CRUD, role checks,
  permission resolution, reassignment flow, assignment history.
- `src/motodiag/shop/__init__.py` +18 LoC re-exports.
- `src/motodiag/cli/shop.py` +260 LoC — `member` subgroup (5 subcommands)
  + 2 `work-order` additions (`reassign`, `assignments`).
- `src/motodiag/core/database.py` SCHEMA_VERSION 34 → 35.
- `tests/test_phase172_rbac.py` (~30 tests across 5 classes).

## Logic

### Migration 035

```sql
CREATE TABLE IF NOT EXISTS shop_members (
    user_id INTEGER NOT NULL,
    shop_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN (
        'owner', 'tech', 'service_writer', 'apprentice'
    )),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMP,
    PRIMARY KEY (user_id, shop_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
);
CREATE INDEX idx_shop_members_shop_role ON shop_members(shop_id, role, is_active);
CREATE INDEX idx_shop_members_user ON shop_members(user_id);

CREATE TABLE IF NOT EXISTS work_order_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    mechanic_user_id INTEGER,            -- NULL = unassigned event
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    unassigned_at TIMESTAMP,
    assigned_by_user_id INTEGER,
    reason TEXT,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (mechanic_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX idx_wo_assignments_wo ON work_order_assignments(work_order_id, assigned_at DESC);
CREATE INDEX idx_wo_assignments_mechanic ON work_order_assignments(mechanic_user_id, assigned_at DESC);
```

Rollback drops tables + indexes.

### `shop/rbac.py` — function inventory

```python
# --- Membership CRUD ---

def add_shop_member(
    shop_id: int, user_id: int, role: ShopRole,
    db_path: Optional[str] = None,
) -> bool:
    """Insert or reactivate. Idempotent."""

def list_shop_members(
    shop_id: int, role: Optional[str] = None,
    active_only: bool = True, db_path: Optional[str] = None,
) -> list[ShopMember]:
    """List members of a shop, optionally filtered by role."""

def get_shop_member(
    shop_id: int, user_id: int, db_path: Optional[str] = None,
) -> Optional[ShopMember]:
    """Fetch one membership row."""

def set_member_role(
    shop_id: int, user_id: int, role: ShopRole,
    db_path: Optional[str] = None,
) -> bool:
    """Change a member's shop-scoped role. Raises if no membership."""

def deactivate_member(
    shop_id: int, user_id: int,
    db_path: Optional[str] = None,
) -> bool:
    """Soft-delete membership. Preserves audit trail."""

def reactivate_member(
    shop_id: int, user_id: int,
    db_path: Optional[str] = None,
) -> bool:
    """Reverse deactivate_member."""

def list_shops_for_user(
    user_id: int, active_only: bool = True,
    db_path: Optional[str] = None,
) -> list[ShopMember]:
    """All shops a user belongs to."""


# --- Shop-scoped permission checks ---

def has_shop_permission(
    shop_id: int, user_id: int, permission: str,
    db_path: Optional[str] = None,
) -> bool:
    """Resolve: does (user_id, shop_id) grant `permission`?

    Rule: user's shop_members.role → roles.id → role_permissions →
    permissions.name. If user is not an active member of shop_id,
    returns False.
    """

def require_shop_permission(
    shop_id: int, user_id: int, permission: str,
    db_path: Optional[str] = None,
) -> None:
    """Raises PermissionDenied if not authorized."""

def list_shop_mechanics(
    shop_id: int, active_only: bool = True,
    db_path: Optional[str] = None,
) -> list[ShopMember]:
    """Members with role='tech' (and 'owner' optionally) eligible for
    WO assignment."""


# --- Work-order assignment with history ---

def reassign_work_order(
    wo_id: int, new_mechanic_user_id: Optional[int],
    assigned_by_user_id: Optional[int] = None,
    reason: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Change WO assignment + log to work_order_assignments.

    If WO already had a mechanic, closes that row (sets unassigned_at).
    Opens a new row with mechanic_user_id (or NULL if unassigning).
    Updates work_orders.assigned_mechanic_user_id via Phase 161
    update_work_order whitelist — no raw SQL.

    If new_mechanic_user_id is None, treats as unassign.
    Returns new assignment_id.
    """

def list_work_order_assignments(
    wo_id: int, db_path: Optional[str] = None,
) -> list[WorkOrderAssignment]:
    """Full assignment history for a WO, most-recent first."""

def current_assignment(
    wo_id: int, db_path: Optional[str] = None,
) -> Optional[WorkOrderAssignment]:
    """Open assignment (unassigned_at IS NULL), or None if currently
    unassigned."""

def mechanic_workload(
    mechanic_user_id: int,
    shop_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> MechanicWorkload:
    """Count open/in-progress WOs currently assigned to mechanic."""
```

Pydantic models:
- `ShopMember`: `user_id`, `shop_id`, `role`, `joined_at`, `is_active`, `username`, `full_name` (LEFT JOINed)
- `WorkOrderAssignment`: `id`, `work_order_id`, `mechanic_user_id`, `mechanic_username`, `assigned_at`, `unassigned_at`, `assigned_by_user_id`, `reason`
- `MechanicWorkload`: `mechanic_user_id`, `open_count`, `in_progress_count`, `on_hold_count`, `total_open`

Exceptions:
- `ShopMembershipNotFoundError`
- `InvalidRoleError`
- `PermissionDenied`
- `MechanicNotInShopError` (raised by `reassign_work_order` when new
  mechanic is not an active tech in the WO's shop)

### Reassignment integration with Phase 161

`reassign_work_order` updates `work_orders.assigned_mechanic_user_id`
via Phase 161's `update_work_order(wo_id, {...})` whitelist — same
pattern as Phase 163/167 enforce. This preserves the "no raw
UPDATE work_orders SQL" discipline that anti-regression grep tests
enforce. The history table is owned by Phase 172 and inserted into
directly (no write-through to work_orders for history rows).

### CLI subgroup

```
shop member add --shop X --user Y --role tech|owner|service_writer|apprentice
shop member list [--shop X] [--role tech] [--include-inactive] [--json]
shop member set-role --shop X --user Y --role apprentice
shop member deactivate --shop X --user Y
shop member reactivate --shop X --user Y
shop work-order reassign WO_ID --to USER_ID [--by USER_ID] [--reason X]
shop work-order assignments WO_ID [--json]
```

## Key Concepts

- **Shop-scoped RBAC** sits on top of Phase 112 global RBAC, not
  replacing it. A user has a single `users.tier` (individual / shop /
  company — subscription tier) and a global role-set via
  `user_roles`. Phase 172 adds a *per-shop* role layer so a user can
  be "owner" of their own shop AND "tech" at a collaborator's shop.
- **Reassignment is additive history.** Every assignment change
  writes a new `work_order_assignments` row; the old row gets
  `unassigned_at` stamped. `work_orders.assigned_mechanic_user_id`
  stays as the fast-path "current assignment" pointer.
- **Mechanic-not-in-shop guard.** `reassign_work_order` verifies the
  target mechanic is an active `tech` (or `owner`) member of the WO's
  shop before allowing assignment. Prevents cross-shop mis-assignment.
- **First-shop owner seeding.** When a new shop is created (Phase 160
  `create_shop`), caller is responsible for then calling
  `add_shop_member(shop_id, owner_user_id, 'owner')`. Phase 160 doesn't
  know about Phase 172 yet — this phase adds a `seed_first_owner`
  helper that's idempotent so existing shops can be backfilled.
- **Permission resolution** walks `shop_members.role → roles.id →
  role_permissions.permission_id → permissions.name`. Same data the
  Phase 112 global RBAC uses, scoped to the current shop.
- **No AI.** Pure SQL joins + role math.

## Verification Checklist

- [ ] Migration 035 creates `shop_members` + `work_order_assignments`
      with CHECK + FK + indexes.
- [ ] SCHEMA_VERSION 34 → 35.
- [ ] Rollback to 34 drops tables cleanly.
- [ ] `add_shop_member` is idempotent; reactivates deactivated rows.
- [ ] `set_member_role` rejects unknown role strings.
- [ ] `deactivate_member` + `reactivate_member` preserve audit trail.
- [ ] `has_shop_permission` returns True for owner role on any known
      permission; False for apprentice on `manage_shop`.
- [ ] `list_shop_mechanics` filters by role='tech' (or 'owner').
- [ ] `reassign_work_order` opens new row, closes old row, updates
      work_orders.assigned_mechanic_user_id via Phase 161 whitelist.
- [ ] Reassigning to NULL (unassign) works; preserves history.
- [ ] Reassigning to non-member mechanic raises `MechanicNotInShopError`.
- [ ] `list_work_order_assignments` returns full audit trail in
      reverse chronological order.
- [ ] `mechanic_workload` counts open + in_progress + on_hold.
- [ ] CLI `member {add,list,set-role,deactivate,reactivate}` +
      `work-order {reassign, assignments}` round-trip.
- [ ] Phase 113/118/131/153/160-171 tests still GREEN.
- [ ] Zero AI calls.
- [ ] Anti-regression grep: no raw `UPDATE work_orders` SQL in rbac.py
      (reuses Phase 161 whitelist).

## Risks

- **Phase 160 doesn't seed first owner.** New shops created before
  Phase 172 have no member rows; an owner must call
  `add_shop_member(shop_id, owner_user_id, 'owner')` after
  `create_shop`. Mitigation: `seed_first_owner` helper is idempotent
  and CLI `member add --user` with `--role owner` covers the backfill
  case; tests assert both flows work. Future Phase could wire
  `create_shop` to auto-seed if a `owner_user_id` kwarg is passed.
- **`mechanic_user_id` SET NULL on user deletion** leaves historical
  rows pointing at NULL. This is the intended FK rule (preserves
  attribution via `assigned_by_user_id` + `reason`), but tests need
  to cover the "deleted user" case so the UI falls back to
  "(deleted user)" rather than crashing.
- **Reassignment on a terminal WO.** A completed/cancelled WO should
  probably not accept new assignments. `reassign_work_order` checks
  `work_orders.status` and raises `InvalidWorkOrderTransition` (reuses
  Phase 161 exception) if terminal — the history table is read-only
  post-terminal.
- **`manage_shop` permission ambiguity.** Phase 112 granted
  `manage_shop` to owner and service_writer; Phase 172's shop-scoped
  lookup respects that. Tests cover owner (has it) and tech (doesn't).
