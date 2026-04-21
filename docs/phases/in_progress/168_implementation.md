# MotoDiag Phase 168 — Bay/Lift Scheduling

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-21

## Goal

Seventh Track G phase. Deterministic AI-free scheduling engine placing `work_orders` (Phase 161) onto physical `shop_bays` with guarded slot lifecycle (`planned → active → completed | cancelled | overrun`). Supports manual reservation, auto-assignment (first compatible bay), conflict detection (sweep-line), and a greedy + simulated-annealing optimizer targeting 80-90% utilization. Stdlib only — no scipy, no numpy, no network.

CLI — appended to `motodiag shop`:
- `shop bay {add, list, show, deactivate, schedule, reschedule, conflicts, optimize, utilization, calendar}` — 10 subcommands.

**Design rule:** zero AI, zero tokens, migration 032. Additive-only to cli/shop.py. Pure algorithmic module; all scheduling state in `shop_bays` + `bay_schedule_slots` tables. Does NOT modify Phase 118 `scheduling/` (customer-facing appointments) package.

Outputs:
- Migration 032 (~110 LoC): 2 tables + 4 indexes.
- `src/motodiag/shop/bay_scheduler.py` (~560 LoC).
- `src/motodiag/shop/__init__.py` +12 LoC.
- `src/motodiag/cli/shop.py` +480 LoC.
- `src/motodiag/core/database.py` SCHEMA_VERSION 31 → 32 (assumes 162=027, 164=028, 165=029, 166=030, 167=031).
- `tests/test_phase168_bay_scheduling.py` (~40 tests, 4 classes).

## Logic

### Migration 032

```sql
CREATE TABLE shop_bays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    bay_type TEXT NOT NULL DEFAULT 'lift'
        CHECK (bay_type IN ('lift','flat','specialty','tire','dyno','wash')),
    is_active INTEGER NOT NULL DEFAULT 1,
    max_bike_weight_lbs INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
    UNIQUE (shop_id, name)
);

CREATE TABLE bay_schedule_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bay_id INTEGER NOT NULL,
    work_order_id INTEGER,                        -- SET NULL on WO delete (history survives)
    scheduled_start TIMESTAMP NOT NULL,
    scheduled_end   TIMESTAMP NOT NULL,
    actual_start    TIMESTAMP,
    actual_end      TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned','active','completed','cancelled','overrun')),
    created_by_user_id INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bay_id) REFERENCES shop_bays(id) ON DELETE CASCADE,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT,
    CHECK (scheduled_end > scheduled_start)
);

CREATE INDEX idx_bays_shop_active      ON shop_bays(shop_id, is_active);
CREATE INDEX idx_slots_bay_start       ON bay_schedule_slots(bay_id, scheduled_start);
CREATE INDEX idx_slots_wo              ON bay_schedule_slots(work_order_id);
CREATE INDEX idx_slots_status_start    ON bay_schedule_slots(status, scheduled_start);
```

Rollback: drop indexes, drop bay_schedule_slots (child of shop_bays), drop shop_bays.

**FK asymmetry:** shop_id CASCADE (physical asset deletion); bay_id CASCADE (same); work_order_id SET NULL (preserves utilization history when WO deleted); created_by_user_id SET DEFAULT.

### bay_scheduler.py — function inventory

Exceptions (ValueError subclasses):
- `BayNotFoundError`
- `SlotNotFoundError`
- `InvalidSlotTransition`
- `SlotOverlapError`

Slot status lifecycle:
- `planned → active | cancelled`
- `active → completed | overrun | cancelled`
- `completed`, `cancelled`, `overrun` (terminal)

Transition functions:
- `start_slot(slot_id, db_path=None) -> bool` — planned → active; sets `actual_start = now()`.
- `complete_slot(slot_id, db_path=None) -> bool` — active → completed OR overrun. Sets `actual_end = now()`. If `actual_end > scheduled_end + 0.25 * (scheduled_end - scheduled_start)`, status becomes overrun.
- `cancel_slot(slot_id, reason=None, db_path=None) -> bool` — planned|active → cancelled; sets actual_end.

Constant: `OVERRUN_BUFFER_FRACTION = 0.25`.

Pydantic models:
- `Bay` (id, shop_id, name, bay_type, is_active, max_bike_weight_lbs, notes, created_at)
- `BayScheduleSlot` (id, bay_id, work_order_id, scheduled_start/end, actual_start/end, status, created_by_user_id, notes)
- `ScheduleConflict` (slot_a_id, slot_b_id, bay_id, overlap_minutes, severity: 'warning' <15min / 'error' >=15min, description)
- `OptimizationReport` (shop_id, date, utilization_before, utilization_after, moves: list[dict], warnings: list[str], iterations_run, accepted_moves, rejected_moves)

Core functions:

```python
def add_bay(shop_id, name, bay_type='lift', *, max_bike_weight_lbs=None, notes=None, db_path=None) -> int: ...
def list_bays(shop_id, include_inactive=False, db_path=None) -> list[dict]: ...
def get_bay(bay_id, db_path=None) -> Optional[dict]: ...
def deactivate_bay(bay_id, db_path=None) -> bool: ...

def schedule_wo(
    wo_id: int, *, bay_id: Optional[int] = None,
    scheduled_start: Optional[str] = None,
    duration_hours: Optional[float] = None,    # falls back to WO.estimated_hours or 1.0
    created_by_user_id: int = 1,
    db_path: Optional[str] = None,
) -> int:
    """Place WO on bay. Validates: WO exists + not terminal, bay active,
    no overlap, duration > 0. Auto-assign (bay_id=None): greedy — pick
    bay within WO's shop whose first-free-window >= requested start can
    hold duration; tie-break by fewer slots already scheduled that day
    (level-loading)."""

def reschedule_slot(slot_id, *, new_start=None, new_bay_id=None, db_path=None) -> bool:
    """Move planned slot. Preserves duration. Rejects if status != 'planned'
    or if new placement overlaps."""

def detect_conflicts(
    shop_id, *, date_range: Optional[tuple[str, str]] = None,
    db_path: Optional[str] = None,
) -> list[ScheduleConflict]:
    """Sweep-line overlap detector. O(N log N)."""

def optimize_shop_day(
    shop_id, date, *, annealing_iterations=500, random_seed=None,
    db_path=None,
) -> OptimizationReport:
    """Greedy + SA reshuffle of planned slots only. Active/completed
    slots are fixed constraints. Returns proposed moves; does NOT
    mutate DB (caller applies via reschedule_slot).
    random_seed default: hash((shop_id, date)) for reproducibility."""

def utilization_for_day(shop_id, date, db_path=None) -> dict: ...
```

### Greedy scheduling (inside schedule_wo auto-assign path)

```
INPUT: wo_id (for shop_id + duration)
       active_bays for that shop, sorted by current-day slot count ASC
       existing_slots indexed by bay_id, sorted by scheduled_start

ALGORITHM:
1. Compute duration_hours from kwargs / WO.estimated_hours / 1.0 fallback
2. Compute earliest_start from kwargs / now()
3. For each bay (in ascending load order):
     Find first-free-window on bay >= earliest_start
     candidate_end = candidate_start + duration
     If no overlap with existing slots on this bay:
       return (bay_id, candidate_start)
4. If no bay accommodates: raise SlotOverlapError (or queue at end-of-day?)
```

### Simulated annealing (optimize_shop_day)

```
INITIAL_TEMP = 1.0
FINAL_TEMP   = 0.01
COOLING_RATE = 0.995
ITERATIONS   = 500 default

ENERGY(state) = 1.0 - utilization(state)  # lower = better

best_state = current
for i in 1..ITERATIONS:
    temp = INITIAL_TEMP * (COOLING_RATE ** i)
    if temp < FINAL_TEMP: break
    neighbor = random_move(current)    # swap-two or slide-one
    if neighbor has conflicts: reject; continue
    delta_e = energy(neighbor) - energy(current)
    if delta_e < 0 OR random.random() < exp(-delta_e / temp):
        current = neighbor
        if energy(current) < energy(best_state):
            best_state = current

return best_state moves, utilization metrics
```

**CRITICAL:** return best_state seen, NOT final-iteration state. SA accepts worsening moves mid-run to escape local optima; final state can be worse than best-seen. Tests verify this.

Utilization formula: `sum(scheduled_durations) / (active_bays * shop_day_hours)`. Default shop_day_hours = 8.

### Conflict detection (sweep-line, O(N log N))

```
FOR each bay_id:
    events = []
    for slot in bay.slots_in_range:
        events.append(('start', slot.scheduled_start, slot.id))
        events.append(('end',   slot.scheduled_end,   slot.id))
    sort events by (timestamp, 'end'-before-'start' so touching slots don't conflict)
    active = set()
    for event in events:
        if event.type == 'start':
            for other_slot_id in active:
                overlap = compute_overlap(...)
                severity = 'error' if overlap_minutes >= 15 else 'warning'
                conflicts.append(ScheduleConflict(...))
            active.add(event.id)
        else:
            active.discard(event.id)
```

### cli/shop.py additions — `bay` subgroup

10 subcommands inside `@shop_group.group("bay")`:

```python
@shop_group.group("bay")
def bay_group(): ...

@bay_group.command("add")       # --shop --name --type --max-weight-lbs --notes
@bay_group.command("list")      # --shop --include-inactive --json
@bay_group.command("show")      # BAY_ID --json
@bay_group.command("deactivate") # BAY_ID --yes
@bay_group.command("schedule")  # WO_ID --bay --start --duration-hours --notes
@bay_group.command("reschedule") # SLOT_ID --start --bay
@bay_group.command("conflicts") # --shop --from --to --json
@bay_group.command("optimize")  # --shop --date --iterations --apply --yes --json
@bay_group.command("utilization") # --shop --date --json
@bay_group.command("calendar")  # --shop --from --to --bay (filter)
```

Rich calendar renderer: Table per day, columns = bays, rows = hours 07:00-19:00, cells color-coded by status (planned cyan, active yellow, completed green, cancelled dim, overrun red).

## Key Concepts

- **Separate from `scheduling/` package.** Phase 118 owns customer-facing `appointments` (front-desk bookings). Phase 168 owns resource-side bay allocation. Different lifecycles (no_show vs overrun), different consumers, different analytics in Phase 171.
- **Guarded slot lifecycle + generic update forbidden.** Only `start_slot`/`complete_slot`/`cancel_slot` mutate status; `reschedule_slot` only for `planned` rows. Prevents CLI typos from retroactively moving in-progress work.
- **Overrun as first-class terminal state.** 25% buffer grace (4h job → 5h is ordinary, 5h01m is overrun). Phase 171 analytics tracks overrun rate per mechanic.
- **Stdlib-only optimizer.** ≤20 bays × ≤50 slots/day is small combinatorial; hand-rolled greedy + SA runs in ~50ms. Avoids scipy/numpy footprint across all moto-diag installs.
- **Greedy first, SA second.** Greedy produces a legal schedule always. SA reshuffles to reduce gaps. If SA yields no improvement, greedy output stands — no regression risk from stochastic pass.
- **Level-loading tie-break in auto-assign.** Two bays can host same WO → pick bay with fewer scheduled slots that day. Prevents "favorite bay" overload.
- **work_order_id SET NULL preserves analytics.** Phase 171 `utilization_by_bay` sums `actual_end - actual_start` across all slots including orphaned ones.
- **Conflict severity threshold = 15 minutes.** Under 15 is mechanic-set buffer or minor overrun clip; ≥15 is scheduling error that cascades.
- **Utilization target 80-90%.** <80% = slack; >90% = one sick mechanic cascades. Optimizer emits warning when utilization_after > 0.90.
- **random_seed default = hash((shop_id, date)).** Reproducible optimizer output; tests pass explicit seed. CLI doesn't expose seed (operators don't care).
- **Best-state tracking in SA, not last-state.** Prevents late-run escape moves from regressing final output.

## Verification Checklist

- [ ] Migration 032 registered; SCHEMA_VERSION bumped (verify current max at build time).
- [ ] Fresh init_db creates shop_bays + bay_schedule_slots + 4 indexes.
- [ ] rollback_migration(032) drops both child-first; lower migrations untouched.
- [ ] bay_type CHECK rejects invalid values.
- [ ] slot status CHECK rejects invalid values.
- [ ] CHECK (scheduled_end > scheduled_start) rejects inverted/zero slots.
- [ ] UNIQUE(shop_id, name) rejects duplicate bay names per shop.
- [ ] add_bay / list_bays / show_bay / deactivate_bay round-trip.
- [ ] schedule_wo with explicit bay + start succeeds when no conflict.
- [ ] schedule_wo with omitted bay auto-assigns to first compatible active bay.
- [ ] schedule_wo level-loads (ties broken by fewer slots that day).
- [ ] schedule_wo with conflicting explicit start raises SlotOverlapError.
- [ ] schedule_wo with terminal WO rejects.
- [ ] schedule_wo with inactive bay rejects.
- [ ] schedule_wo default duration = WO.estimated_hours; falls back to 1.0.
- [ ] reschedule_slot moves planned slot + preserves duration.
- [ ] reschedule_slot on active/completed slot raises InvalidSlotTransition.
- [ ] reschedule_slot into conflict raises SlotOverlapError.
- [ ] start_slot planned → active + sets actual_start.
- [ ] complete_slot within buffer → completed; past buffer → overrun.
- [ ] cancel_slot from planned + from active both transition to cancelled.
- [ ] detect_conflicts finds single-pair overlap with correct severity.
- [ ] detect_conflicts finds 3-way pileup (3 conflict rows).
- [ ] detect_conflicts respects date_range.
- [ ] optimize_shop_day dry-run produces report + makes zero DB writes.
- [ ] optimize_shop_day utilization_after >= utilization_before (never regresses).
- [ ] optimize_shop_day random_seed makes output reproducible.
- [ ] optimize_shop_day active/completed slots never moved.
- [ ] optimize_shop_day emits over-commit warning when > 0.90.
- [ ] Delete shop CASCADE-drops bays + slots.
- [ ] Delete bay CASCADE-drops slots.
- [ ] Delete WO sets slot.work_order_id=NULL; slot survives.
- [ ] CLI shop bay add/list/show/deactivate round-trip.
- [ ] CLI shop bay schedule WO_ID without --bay auto-assigns.
- [ ] CLI shop bay reschedule SLOT_ID --start ISO moves planned slot.
- [ ] CLI shop bay conflicts --shop X renders table.
- [ ] CLI shop bay optimize --shop X --date D --apply --yes applies moves.
- [ ] CLI shop bay utilization --shop X --date D --json emits valid JSON.
- [ ] CLI shop bay calendar --shop X --from D --to D renders Rich tables.
- [ ] All Phase 160-167 tests still GREEN.
- [ ] Full regression GREEN.

## Risks

- **Migration number drift.** Plan assumes 162=027, 164=028, 165=029, 166=030, 167=031 → 168=032. Builder re-verifies SCHEMA_VERSION at dispatch time.
- **SA non-determinism in tests.** random_seed kwarg fixes this; default derived from hash((shop_id, date)).
- **SA can accept worsening moves mid-run.** Return best-seen, not final — tests verify.
- **Calendar on narrow terminals.** 20-bay × 13-hour table exceeds 80 cols. Mitigate with --bay filter and adaptive pagination.
- **Manual reschedule races.** SQLite serialized mode OK for single-writer; Phase 172 adds WAL + optimistic locking.
- **Planned slots on deactivated bay.** Not auto-cancelled; surface as new severity in detect_conflicts ('warning: inactive_bay').
- **Bay weight limit unenforced.** `max_bike_weight_lbs` stored but not yet validated against bike weight (coverage in vehicles table not uniform). Deferred to future phase.

## Build Notes

- Plan is v1.0. Builder: follow CLAUDE.md 15-step checklist. Pattern template: Phase 161 `work_order_repo.py`.
- Architect runs phase-specific tests after Builder returns.
- Do NOT commit or push from worktree.
- Report files created/modified + test count + deviations in final message.
