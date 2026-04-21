# MotoDiag Phase 161 — Work Order System

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-21

## Goal

Second Track G phase. Introduces `work_orders` — the mechanic's unit of work on a specific bike. Each work order attaches to an `intake_visits` row (or can be created standalone for walk-in quick services without a formal intake record), carries title + description + estimated hours + actual hours + priority, and moves through a guarded lifecycle: `draft → open → in_progress → (on_hold | completed | cancelled) → (reopen) → open`. Phase 161 deliberately does NOT introduce structured issue lists (Phase 162), parts linkage (Phase 165), or invoicing (Phase 169) — those layer on top of this row.

CLI — appended to the existing `motodiag shop` top-level group from Phase 160, under a new `work-order` subgroup:

- `shop work-order {create, list, show, update, start, pause, resume, complete, cancel, reopen, assign, unassign}` — 12 subcommands.

**Design rule:** zero AI, zero tokens, one migration (026). Additive-only to `cli/shop.py` (new `@shop_group.group("work-order")` with subcommands). No modification to `shop/shop_repo.py` or `shop/intake_repo.py`. No change to `cli/main.py` — `register_shop` already wired from Phase 160.

Outputs:

- Migration 026 (~120 LoC): `work_orders` table + 4 indexes.
- `shop/work_order_repo.py` (~440 LoC) — 14 functions + 3 exceptions + guarded status-lifecycle helpers.
- `shop/__init__.py` +18 LoC — re-export new names.
- `cli/shop.py` +560 LoC — `work-order` subgroup + 12 subcommands + Rich panel/table helpers.
- `src/motodiag/core/database.py` — `SCHEMA_VERSION` 25 → 26.
- `tests/test_phase161_work_orders.py` (~45 tests, 4 classes).

## Logic

### Migration 026

```sql
CREATE TABLE work_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL,
    intake_visit_id INTEGER,                    -- nullable: quick walk-in service without formal intake
    vehicle_id INTEGER NOT NULL,                -- denormalized for query performance; FK to vehicles
    customer_id INTEGER NOT NULL,               -- denormalized for query performance; FK to customers
    title TEXT NOT NULL,
    description TEXT,
    priority INTEGER NOT NULL DEFAULT 3
        CHECK (priority BETWEEN 1 AND 5),       -- 1=critical, 5=low. AI ranking in Phase 163.
    estimated_hours REAL,                       -- mechanic estimate at open
    actual_hours REAL,                          -- sum of timer-tracked work; populated on complete
    estimated_parts_cost_cents INTEGER,         -- optional — set by Phase 165/166 parts optimization
    assigned_mechanic_user_id INTEGER,          -- nullable until Phase 172 multi-mechanic RBAC
    created_by_user_id INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','open','in_progress','on_hold','completed','cancelled')),
    on_hold_reason TEXT,                        -- populated on on_hold transition
    cancellation_reason TEXT,                   -- populated on cancel
    opened_at TIMESTAMP,                        -- set when draft -> open
    started_at TIMESTAMP,                       -- set when open/on_hold -> in_progress (latest)
    completed_at TIMESTAMP,                     -- set when in_progress -> completed
    closed_at TIMESTAMP,                        -- set when completed OR cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
    FOREIGN KEY (intake_visit_id) REFERENCES intake_visits(id) ON DELETE SET NULL,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE RESTRICT,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    FOREIGN KEY (assigned_mechanic_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
);
CREATE INDEX idx_wo_shop_status ON work_orders(shop_id, status);
CREATE INDEX idx_wo_vehicle ON work_orders(vehicle_id);
CREATE INDEX idx_wo_customer ON work_orders(customer_id);
CREATE INDEX idx_wo_intake_visit ON work_orders(intake_visit_id);
```

Rollback: drop indexes then `DROP TABLE work_orders`.

**FK delete semantics:**
- `shop_id` CASCADE — same pattern as `intake_visits`. Shop delete is rare and explicit.
- `intake_visit_id` SET NULL — a work order survives if its parent intake is deleted (e.g. accidental intake wipe; work history shouldn't vanish).
- `vehicle_id` + `customer_id` RESTRICT — prevent history erasure, same as `intake_visits`.
- `assigned_mechanic_user_id` SET NULL — if a mechanic account is deleted, work orders they owned remain but become unassigned (Phase 172 re-assignment flow).

### work_order_repo.py

Guarded lifecycle — `update_work_order` CANNOT mutate `status`, `opened_at`, `started_at`, `completed_at`, `closed_at`, or any `*_reason` field. Only the dedicated transition functions can.

Functions:

- `create_work_order(shop_id, vehicle_id, customer_id, title, description=None, priority=3, estimated_hours=None, intake_visit_id=None, assigned_mechanic_user_id=None, created_by_user_id=1, db_path=None) -> int` — explicit pre-checks on shop/vehicle/customer (ValueError with named field on miss); `intake_visit_id` pre-check if supplied. Starts in `draft` status.
- `get_work_order(wo_id, db_path=None) -> Optional[dict]` — JOINs shops + customers + vehicles + (optional) intake_visits + (optional) assigned_mechanic for denormalized display fields.
- `require_work_order(wo_id, db_path=None) -> dict` — raises `WorkOrderNotFoundError`.
- `list_work_orders(shop_id=None, vehicle_id=None, customer_id=None, assigned_mechanic_user_id=None, status=None, priority=None, since=None, intake_visit_id=None, limit=100, db_path=None) -> list[dict]` — composable filters, most-recent first, denormalized display columns included.
- `count_work_orders(shop_id=None, status=None, assigned_mechanic_user_id=None, db_path=None) -> int` — dashboard helper.
- `update_work_order(wo_id, updates: dict, db_path=None) -> bool` — whitelist: title, description, priority, estimated_hours, estimated_parts_cost_cents, actual_hours. Raises `WorkOrderNotFoundError` if missing.
- `assign_mechanic(wo_id, user_id, db_path=None) -> bool` — sets assigned_mechanic_user_id.
- `unassign_mechanic(wo_id, db_path=None) -> bool` — clears assigned_mechanic_user_id.

Lifecycle transition functions (each raises `InvalidWorkOrderTransition` on invalid transition + `WorkOrderNotFoundError` on missing id):

- `open_work_order(wo_id, db_path=None) -> bool` — draft → open. Sets `opened_at`.
- `start_work(wo_id, db_path=None) -> bool` — open | on_hold → in_progress. Sets `started_at` to latest start time.
- `pause_work(wo_id, reason=None, db_path=None) -> bool` — in_progress → on_hold. Sets `on_hold_reason`.
- `resume_work(wo_id, db_path=None) -> bool` — alias for `start_work` when prior status is `on_hold`; clears `on_hold_reason`.
- `complete_work_order(wo_id, actual_hours=None, db_path=None) -> bool` — in_progress → completed. Sets `completed_at`, `closed_at`, optionally `actual_hours`.
- `cancel_work_order(wo_id, reason="customer-withdrew", db_path=None) -> bool` — any non-terminal → cancelled. Sets `cancellation_reason`, `closed_at`.
- `reopen_work_order(wo_id, db_path=None) -> bool` — completed | cancelled → open. Clears `completed_at`, `closed_at`, `cancellation_reason`, `on_hold_reason`.

Exceptions (all `ValueError` subclasses):
- `WorkOrderNotFoundError`
- `InvalidWorkOrderTransition` — wraps the from→to state mismatch with descriptive message.
- `WorkOrderFKError` — optional: wraps IntegrityError from FK violations with cleaner message.

Valid transitions table (the `_VALID_TRANSITIONS` constant drives the guard):

```
draft        → open | cancelled
open         → in_progress | cancelled | on_hold
in_progress  → on_hold | completed | cancelled
on_hold      → in_progress | cancelled
completed    → open          (via reopen)
cancelled    → open          (via reopen)
```

### cli/shop.py additions — `work-order` subgroup

Appended inside the existing `register_shop` function (no refactor of Phase 160 surface). Alias: `shop wo` NOT added this phase — we reserve three-letter slugs for the hidden-alias pass like Phase 130.

12 subcommands each with `init_db()` → resolve refs → call repo → render Rich:

- `create --shop --intake INTAKE_ID --title --description --priority --estimated-hours --bike --customer --mechanic` — `--intake` auto-fills shop/bike/customer from the intake visit; providing both `--intake` AND `--bike/--customer/--shop` raises mutex error. If `--intake` is missing, all three (shop/bike/customer) are required.
- `list --shop --status --priority --mechanic --since --limit --json` — default filter `status=draft,open,in_progress,on_hold` (exclude terminal); `--status all` to include.
- `show WO_ID [--json]` — Rich panel with denormalized display.
- `update WO_ID --set key=value [--set key=value ...]` — whitelist.
- `start WO_ID` — explicit status transition subcommand.
- `pause WO_ID --reason "parts back-ordered"` — sets on_hold with reason.
- `resume WO_ID` — on_hold → in_progress.
- `complete WO_ID --actual-hours 2.5` — in_progress → completed.
- `cancel WO_ID --reason "customer-withdrew"` — from any non-terminal to cancelled. Confirm prompt unless `--yes`.
- `reopen WO_ID [--yes]` — completed | cancelled → open. Confirm prompt.
- `assign WO_ID --mechanic USER_ID` — sets mechanic.
- `unassign WO_ID` — clears mechanic.

## Key Concepts

- **Denormalized shop_id / vehicle_id / customer_id.** A work order can exist without an intake (quick walk-in; `intake_visit_id=NULL`). Denormalizing the three foreign keys onto the work order itself — even when an intake supplies them — makes the dominant "list work orders for shop X" / "for bike Y" queries single-index lookups. The cost is modest storage + a consistency check (repo asserts `intake.vehicle_id == work_order.vehicle_id` when both are present).
- **Guarded status lifecycle.** Same pattern as Phase 160's `intake_visits` — the transition functions own `status` mutations; the generic `update_work_order` cannot. Prevents CLI/future-API bypass of the lifecycle.
- **Composable filters on `list_work_orders`.** Every query shape Phase 163-172 will need (by shop, by status, by mechanic, by bike, by customer, by intake, by priority, by time window) is a single repo call with kwargs. Avoids growing a zoo of `list_by_X` variants.
- **Priority as 1-5 integer with CHECK constraint.** Phase 163 AI scoring will bucket its outputs into 1-5 and write via `update_work_order({priority: N})`. Phase 164 triage queue joins on priority ASC. No decimals — mechanics want a grid-sortable integer.
- **Reopen clears terminal timestamps.** A work order reopened after being completed loses `completed_at` / `closed_at`. This is the correct audit semantics — if the work wasn't actually done, the completion timestamp was a lie and should not persist. Downstream Phase 169 invoicing reads `completed_at` as the invoice trigger; cleanly clearing it on reopen prevents double-invoicing.
- **Intake → work order is 1:N.** A single intake visit may spawn multiple work orders (customer brings bike in with brake squeal + oil leak + new tires: three work orders, one intake). `intake_visits` does not back-reference work orders; work orders link via `intake_visit_id`. Phase 164 triage queue surfaces the 1:N grouping.

## Verification Checklist

- [ ] Migration 026 registered; `SCHEMA_VERSION` 25 → 26.
- [ ] Fresh `init_db()` creates `work_orders` + 4 indexes.
- [ ] `rollback_migration(26)` drops them; lower-numbered migrations untouched.
- [ ] `status` CHECK rejects invalid values (direct SQL INSERT).
- [ ] `priority` CHECK rejects values outside 1-5.
- [ ] `create_work_order` with missing shop/vehicle/customer raises ValueError naming the field.
- [ ] `create_work_order` with supplied `intake_visit_id` but mismatched vehicle_id rejects with clear error.
- [ ] `update_work_order` whitelist drops unknown keys and cannot mutate `status`, `opened_at`, `completed_at`, or `*_reason` fields.
- [ ] `open_work_order` transitions draft → open and sets `opened_at`.
- [ ] `start_work` transitions open → in_progress and sets `started_at`.
- [ ] `pause_work` transitions in_progress → on_hold with reason persisted.
- [ ] `resume_work` transitions on_hold → in_progress and clears `on_hold_reason`.
- [ ] `complete_work_order` transitions in_progress → completed, sets `completed_at`, `closed_at`, optional `actual_hours`.
- [ ] `cancel_work_order` transitions from any non-terminal to cancelled and sets `cancellation_reason`, `closed_at`.
- [ ] Invalid transitions raise `InvalidWorkOrderTransition` (e.g. draft → completed, completed → in_progress).
- [ ] `reopen_work_order` clears `completed_at`, `closed_at`, `cancellation_reason`, `on_hold_reason` and returns status to open.
- [ ] Delete shop CASCADE-drops work orders for that shop.
- [ ] Delete intake sets `intake_visit_id = NULL` on dependent work orders; the orders survive.
- [ ] Delete vehicle / customer with active work orders raises FK RESTRICT error.
- [ ] `list_work_orders` composable filters return correct subsets for each kwarg.
- [ ] CLI `shop work-order create --intake INTAKE_ID --title ...` auto-fills shop/customer/vehicle from the intake.
- [ ] CLI `shop work-order create` without `--intake` requires all three (shop/bike/customer) or raises.
- [ ] CLI `shop work-order list` default excludes completed/cancelled; `--status all` includes.
- [ ] CLI `shop work-order show --json` emits valid JSON with denormalized display fields.
- [ ] CLI `shop work-order update WO_ID --set priority=1 --set description="New"` works.
- [ ] CLI `shop work-order start/pause/resume/complete/cancel/reopen` all surface clean errors on invalid transitions.
- [ ] CLI `shop work-order assign WO_ID --mechanic USER_ID` / `unassign WO_ID` round-trip.
- [ ] Phase 160 shop tests still GREEN post-migration.
- [ ] Full regression (~3395 tests) still GREEN.
- [ ] Zero live API tokens this phase.

## Risks

- **Denormalization consistency.** If a work order's `intake_visit_id` is set but its `vehicle_id` doesn't match the intake's `vehicle_id`, state is inconsistent. Mitigation: `create_work_order` validates at creation; `update_work_order` does not touch any of those FKs (whitelist excludes them). `reassign_work_order_to_intake` is deliberately NOT exposed — if the mechanic captured the wrong intake, cancel and recreate.
- **`on_hold` without reason.** Phase 162 issue logging may want mandatory reasons on pause; for Phase 161 we accept `reason=None` (freetext field can stay empty). Mitigation: CLI `pause` prompts for reason interactively if `--reason` is not supplied; programmatic callers can pass None.
- **Cancel from `draft` status.** Is that valid? We allow it (draft → cancelled is in the transitions table) because a mechanic might draft an order, realize the customer changed their mind mid-intake, and cancel cleanly. Tests cover this path.
- **Reopen semantics clear terminal timestamps.** If Phase 169 downstream invoicing already happened against a completed work order and the order is then reopened, the invoice stays (an invoice is its own row). Mitigation: Phase 169 will read `completed_at` for the invoice_generated_at timestamp, not for logic decisions; reopen unlocking is sound.
- **SCHEMA_VERSION bump + in-flight Phase 162.** Phase 162 will bump to 27; the sequence is strictly serial this track.
- **Priority default = 3.** Neutral middle. AI ranking (Phase 163) will only overwrite priority when its confidence exceeds a threshold, to prevent shifting mechanic-set priorities without cause.
- **CLI flag sprawl on create.** `shop work-order create --shop X --bike Y --customer Z --title ... --priority ...` is verbose. Mitigation: `--intake INTAKE_ID` collapses three flags into one; Phase 164 triage queue will provide a "create WO from intake" interactive wizard. For this phase, verbose is acceptable.
