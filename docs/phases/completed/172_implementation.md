# MotoDiag Phase 172 — Multi-Mechanic Assignment + Shop-Scoped RBAC

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-22

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

- [x] Migration 035 creates `shop_members` + `work_order_assignments`
      with CHECK + FK + indexes.
- [x] SCHEMA_VERSION 34 → 35.
- [x] Rollback to 34 drops tables cleanly.
- [x] `add_shop_member` is idempotent; reactivates deactivated rows.
- [x] `set_member_role` rejects unknown role strings.
- [x] `deactivate_member` + `reactivate_member` preserve audit trail.
- [x] `has_shop_permission` returns True for owner role on any known
      permission; False for apprentice on `manage_shop`; inactive
      member denied.
- [x] `list_shop_mechanics` filters by role IN ('tech', 'owner').
- [x] `reassign_work_order` opens new row, closes old row, updates
      work_orders.assigned_mechanic_user_id via Phase 161 whitelist
      (mock-patch audit test enforces).
- [x] Reassigning to NULL (unassign) works; preserves history.
- [x] Reassigning to non-member raises `MechanicNotInShopError`.
- [x] Reassigning to apprentice raises (not in ELIGIBLE_ASSIGN_ROLES).
- [x] Reassigning terminal WO raises `InvalidWorkOrderTransition`.
- [x] `list_work_order_assignments` returns full audit trail in
      reverse chronological order.
- [x] `mechanic_workload` counts open + in_progress + on_hold.
- [x] CLI `member {add,list,set-role,deactivate,reactivate}` +
      `work-order {reassign, assignments}` round-trip.
- [x] Phase 113/118/131/153/160-171 tests still GREEN (605/605 after
      widening Phase 171's anti-regression `SCHEMA_VERSION == 34`
      assertion to `>= 34`).
- [x] Zero AI calls.
- [x] Anti-regression grep: no raw `UPDATE work_orders` SQL in rbac.py
      (reuses Phase 161 whitelist).

## Deviations from Plan

- **Phase 171 anti-regression test widened**. The Phase 171 test
  `test_no_migration_added` asserted `SCHEMA_VERSION == 34` exactly,
  which now fails because Phase 172 legitimately bumps to 35. Updated
  that test to `SCHEMA_VERSION >= 34` — the intent ("Phase 171 itself
  is read-only") is preserved, but the assertion no longer drifts on
  every downstream migration. Tracked under Phase 172 because the
  update was a Phase-172-introduced requirement, not a Phase 171
  rework.
- **Anti-regression grep strips comments + docstrings before checking.**
  First run failed because the module docstring explicitly documents
  "never raw SQL" by mentioning `UPDATE work_orders` as a forbidden
  pattern. Regex now strips `#...` line comments + `"""..."""`
  docstrings before applying `UPDATE\s+work_orders\b`. The `\b` word
  boundary also prevents false matches against `work_order_assignments`
  (which was never the risk but good defense).
- **No separate `list_shops_for_user` CLI command** — plan had it but
  it's a data-model tool, not a mechanic workflow step. Kept as a
  public function (useful for Phase 173 automation rules / Phase 181+
  transport worker) but omitted from the 7 CLI subcommands to avoid
  CLI sprawl. `shop member list` already serves the primary use case.

## Results

| Metric | Value |
|--------|-------|
| Phase 172 tests landed | 32 GREEN (6 classes) |
| Targeted regression | 605/605 GREEN in 384.10s (6m 24s) after Phase 171 widening fix |
| Coverage range | Phase 113 + 118 + 131 + 153 + Track G 160-172 + 162.5 |
| Migration LoC | 67 LoC (2 tables + 4 indexes + CHECK constraints) |
| `shop/rbac.py` LoC | 475 (14 public functions + 3 Pydantic + 4 exceptions) |
| `cli/shop.py` addition | +234 LoC (`member` subgroup 5 subcmds + `work-order` 2 added subcmds) |
| `shop/__init__.py` addition | +26 re-exports |
| Total `cli/shop.py` | ~5080 LoC, **15 subgroups** (new `member`), **113 subcommands** (+7) |
| SCHEMA_VERSION | 34 → **35** |
| AI calls | 0 (zero tokens spent) |

**Key finding:** Phase 172 validates that shop-scoped RBAC can layer
cleanly on top of Phase 112 global RBAC without touching Phase 112
schema. `shop_members.role` maps to `roles.name` (Phase 112) and the
permission lookup walks `roles → role_permissions → permissions` —
zero duplication of the permission catalog. The reassignment flow's
write-back-through-whitelist discipline (Phase 161) caught no issues
here (rbac.py ships clean) but the anti-regression grep test
future-proofs the module: any downstream contributor tempted to do a
raw `UPDATE work_orders` gets a test failure before CI. Pattern
recommendation for Phase 173 automation rules: when a rule action
needs to mutate a WO (set priority, reassign, change status), it
should go through the Phase 161 whitelist + the appropriate dedicated
function (update_work_order, reassign_work_order, etc.) — the grep
test pattern should be duplicated in any future write-heavy module.

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
