# MotoDiag Phase 160 — Shop Profile + Multi-Bike Intake

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-21

## Goal

First Track G phase. Stands up the "front desk" of a shop: register a shop profile (name, address, hours, tax ID) and log bike arrivals as **intake visits** pairing a customer with one of their vehicles at a given timestamp with reported problems. Reuses the Phase 113 `crm/` substrate (`customers` + `customer_bikes`) — no duplicate customer schema. Surfaces customer CRUD to the CLI for the first time so mechanics can actually enter a new walk-in without dropping to Python.

CLI — new top-level group `motodiag shop` with three subgroups (as-built totals: 5 + 9 + 8 = **22 subcommands** — overshot the plan's 19):

- `shop profile {init, show, list, update, delete}` — shop identity + contact + hours + tax ID. Added `list` and `delete` during build; three-command plan expanded to five once it became clear multi-shop installations need a listing + hard-delete path.
- `shop customer {add, list, show, search, update, deactivate, link-bike, unlink-bike, bikes}` — thin wrapper over `crm/customer_repo.py` + `crm/customer_bikes_repo.py`. Nine subcommands as planned.
- `shop intake {create, list, show, update, close, cancel, reopen, open-for-bike}` — the visit log. Added `cancel` during build distinct from `close` so future Phase 171 analytics can filter completed from withdrawn visits at the SQL layer, not post-hoc.

**Design rule:** zero AI, zero tokens, one migration (025). Reuses existing `crm/` package — does not modify it. Additive-only to `cli/main.py` (`register_shop(cli)`).

Outputs (as-built LoC):

- Migration 025 (~100 LoC): `shops` + `intake_visits` + 4 indexes (idx_shops_owner_name + 3 intake indexes).
- `shop/__init__.py` — 63 LoC (public re-exports of 21 names from both repos).
- `shop/shop_repo.py` — 337 LoC (11 functions incl. `reactivate_shop` added during build + 2 exceptions + hours_json JSON validator + update-whitelist).
- `shop/intake_repo.py` — 481 LoC (12 functions incl. `_since_cutoff` offset parser + `require_intake` helper + `_transition_out_of_open` shared lifecycle helper + 2 exceptions).
- `cli/shop.py` — 1003 LoC, new module (expanded from ~420 LoC estimate — Rich Panel/Table rendering helpers for shops/customers/intakes + defensive denormalized-row accessors + Phase 125-style remediation errors ate more lines than projected).
- `cli/main.py` +6 LoC (import + block-comment + `register_shop(cli)` line).
- `src/motodiag/core/database.py` — `SCHEMA_VERSION` 24 → 25 with Phase 160 comment.
- `tests/test_phase160_shop.py` — 735 LoC, **44 tests** (slight overshoot of plan's ~40 — four extra coverage points added for lifecycle guards, hours_json rejection paths, and customer-deactivate Unassigned guard).

## Logic

### Migration 025

```sql
-- Shop profile. One installation can host multiple shops (solo mechanic with
-- mobile + brick-and-mortar; franchise with locations). UNIQUE (owner_user_id, name)
-- keeps names scoped per user — same pattern as fleets.name in migration 018.
CREATE TABLE shops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER NOT NULL DEFAULT 1,
    name TEXT NOT NULL,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    phone TEXT,
    email TEXT,
    tax_id TEXT,
    hours_json TEXT,                    -- JSON blob: {"mon":"08:00-17:00", ...}
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET DEFAULT,
    UNIQUE (owner_user_id, name)
);
CREATE INDEX idx_shops_owner_name ON shops(owner_user_id, name);

-- Intake visit. Each time a bike comes in, one row. Links the existing
-- customers (Phase 113) and vehicles tables. reported_problems is mechanic
-- freetext — structured issue logging lands in Phase 162.
CREATE TABLE intake_visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    vehicle_id INTEGER NOT NULL,
    intake_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    mileage_at_intake INTEGER,          -- nullable — not always known at intake
    reported_problems TEXT,             -- mechanic-captured freetext
    intake_user_id INTEGER NOT NULL DEFAULT 1,  -- who logged the intake
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed','cancelled')),
    closed_at TIMESTAMP,                -- set when status transitions out of open
    close_reason TEXT,                  -- 'completed' | 'customer-withdrew' | 'no-fault-found'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE RESTRICT,
    FOREIGN KEY (intake_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
);
CREATE INDEX idx_intake_shop_status ON intake_visits(shop_id, status);
CREATE INDEX idx_intake_vehicle ON intake_visits(vehicle_id);
CREATE INDEX idx_intake_customer ON intake_visits(customer_id);
```

Rollback: DROP intake_visits first (FK), then DROP shops.

**FK asymmetry is deliberate:**
- `ON DELETE CASCADE` for `shop_id` — deleting a shop cascades its intake history (but `shop delete` prompts + `--force` required; see `shop_repo.delete_shop`).
- `ON DELETE RESTRICT` for `customer_id` and `vehicle_id` — cannot delete a customer or vehicle that has intake history. Mechanics deactivate customers instead (`crm.customer_repo.deactivate_customer` already exists).

**Why mileage_at_intake is nullable:** walk-in carburetor rebuild on a '78 CB750 with a broken speedo. `advanced/history_repo.py` (Phase 152) monotonic-mileage rules do NOT apply to intake_visits — it's an at-arrival snapshot, not a service record.

### shop_repo.py

Shop profile CRUD — same shape as `advanced/fleet_repo.py`:

- `create_shop(name, address=None, city=None, state=None, zip=None, phone=None, email=None, tax_id=None, hours_json=None, owner_user_id=1, db_path=None) -> int` — raises `ShopNameExistsError` on `UNIQUE` violation.
- `get_shop(shop_id, db_path=None) -> dict | None`
- `get_shop_by_name(name, owner_user_id=1, db_path=None) -> dict | None`
- `list_shops(owner_user_id=1, include_inactive=False, db_path=None) -> list[dict]` — LEFT JOIN `intake_visits` to add `open_intake_count` per row.
- `update_shop(shop_id, updates: dict, db_path=None) -> bool` — whitelist of updatable fields; bumps `updated_at`.
- `deactivate_shop(shop_id, db_path=None) -> bool` — soft delete; preserves history.
- `delete_shop(shop_id, db_path=None) -> bool` — hard delete; CASCADE drops intake_visits. Caller must confirm.
- `_resolve_shop(identifier: int | str, owner_user_id=1, db_path=None) -> int` — accepts id or name → returns id, raises `ShopNotFoundError`.

Exceptions: `ShopNotFoundError`, `ShopNameExistsError` (both `ValueError` subclasses).

### intake_repo.py

Intake lifecycle — status transitions are guarded, not free-form:

- `create_intake(shop_id, customer_id, vehicle_id, reported_problems=None, mileage_at_intake=None, intake_user_id=1, db_path=None) -> int` — validates FK targets exist (explicit pre-check → friendlier error than raw `IntegrityError`). Defaults `intake_at = CURRENT_TIMESTAMP`, `status = 'open'`.
- `get_intake(intake_id, db_path=None) -> dict | None` — JOINs customers + vehicles + shops so the row comes back with denormalized display names.
- `list_intakes(shop_id=None, customer_id=None, vehicle_id=None, status=None, since=None, limit=100, db_path=None) -> list[dict]` — composable filters; `status='open'` is the default daily-queue query.
- `list_open_for_bike(vehicle_id, db_path=None) -> list[dict]` — UX helper for "is this bike already checked in?" duplicate-intake prevention.
- `update_intake(intake_id, updates: dict, db_path=None) -> bool` — whitelist: `reported_problems`, `mileage_at_intake`. Cannot mutate `status` here (use `close_intake`/`reopen_intake`).
- `close_intake(intake_id, close_reason='completed', db_path=None) -> bool` — raises `IntakeAlreadyClosedError` if not `open`. Sets `status`, `closed_at`, `close_reason`.
- `reopen_intake(intake_id, db_path=None) -> bool` — `closed`/`cancelled` → `open`, clears `closed_at` + `close_reason`. Mechanics reopen when "fixed" turns out to be "not fixed."
- `cancel_intake(intake_id, reason='customer-withdrew', db_path=None) -> bool` — same as close but sets `status='cancelled'`; distinct from close so analytics (Phase 171) can filter completed from withdrawn.
- `count_intakes(shop_id=None, status=None, since=None, db_path=None) -> int` — for dashboard roll-ups.
- `_resolve_intake(identifier: int, db_path=None) -> int` — passthrough for now; accepts future slug-style IDs.

Exceptions: `IntakeNotFoundError`, `IntakeAlreadyClosedError` (both `ValueError` subclasses).

### cli/shop.py — new module

One top-level `@click.group("shop")` with three subgroups. Follows the `advanced.py` pattern exactly:

```python
@click.group("shop")
def shop_group():
    """Shop management: profile, customers, intake."""

@shop_group.group("profile")
def profile_group(): ...

@shop_group.group("customer")
def customer_group(): ...

@shop_group.group("intake")
def intake_group(): ...

def register_shop(cli: click.Group) -> None:
    cli.add_command(shop_group)
```

**`shop profile`** (3 subcommands) — `init`, `show [--shop]`, `update --shop [field=value ...]`. `init` is first-time wizard: prompts name/address/phone/email; idempotent via `get_shop_by_name` pre-check. `show` renders a Rich Panel. `update` takes repeated `--set key=value` flags (whitelist enforced in repo).

**`shop customer`** (9 subcommands) — wraps `crm/customer_repo.py`:
- `add --name --phone --email --address --notes` → `create_customer`.
- `list [--inactive] [--limit N]` → Rich Table.
- `show CUSTOMER_ID` → Panel + linked-bike list.
- `search QUERY [--field name|phone|email]` → Rich Table.
- `update CUSTOMER_ID --set key=value` → `update_customer` (whitelist).
- `deactivate CUSTOMER_ID` → `deactivate_customer` (Phase 113 soft-delete; cannot deactivate id=1 Unassigned).
- `link-bike CUSTOMER_ID --bike SLUG [--relationship owner|rider|guardian]` → `link_customer_bike`.
- `unlink-bike CUSTOMER_ID --bike SLUG [--relationship owner]` → `unlink_customer_bike`.
- `bikes CUSTOMER_ID` → `list_bikes_for_customer` Rich Table.

**`shop intake`** (7 subcommands):
- `create --shop --customer --bike [--mileage N] [--notes "..."]` — prompts interactively if `--notes` omitted (multi-line input). Pre-checks: FK targets exist; Phase 125 remediation style for missing bike (`motodiag garage add` hint).
- `list [--shop NAME] [--status open|closed|cancelled] [--since 7d] [--limit N]` — default shows today's open queue.
- `show INTAKE_ID` — Rich Panel with denormalized customer/bike/shop.
- `update INTAKE_ID [--mileage N] [--notes "..."]`.
- `close INTAKE_ID [--reason completed|customer-withdrew|no-fault-found]` — default `completed`.
- `reopen INTAKE_ID` — confirms via `click.confirm` unless `--yes`.
- `open-for-bike SLUG` — UX helper: "is this bike already checked in?" before creating a duplicate intake.

All commands: `init_db()` first, resolve inputs, call repo, render Rich. `--json` flag on `list`/`show` for machine-readable output. `ClickException` on bad inputs (no raw Python tracebacks).

### Wiring to cli/main.py

Two-line additive change:

```python
# Near the other imports
from motodiag.cli.shop import register_shop

# In the init block after register_completion(cli):
register_shop(cli)
```

No refactoring of existing registrations. No new short aliases this phase (Phase 128-style alias work can come later if needed).

### Bumping SCHEMA_VERSION

`src/motodiag/core/database.py`: `SCHEMA_VERSION = 24` → `SCHEMA_VERSION = 25`. Comment bumped to reference Phase 160.

## Key Concepts

- **Reuse existing CRM substrate.** Phase 113 shipped `customers` + `customer_bikes` in migration 006 with `customer_repo.py` + `customer_bikes_repo.py`. Phase 160 is the first CLI consumer — no schema duplication.
- **Shop as the organizational unit.** Every intake visit and every future work order (Phase 161) attaches to a `shop_id`. Solo mechanics have one shop; multi-location shops have many. Multi-user/per-shop roles come in Phase 172.
- **Intake visit is the "arrived on lot" event.** It is NOT a work order (161), NOT an issue list (162), NOT an invoice (169). Keeping it narrow lets downstream phases layer without renaming.
- **FK delete asymmetry.** `shop_id` CASCADEs (shop deletion is rare, explicit, confirmed), but `customer_id` and `vehicle_id` RESTRICT (prevents accidental history erasure via unrelated deletes). Mechanics deactivate; they don't delete.
- **Status lifecycle is closed-set + guarded.** `open → closed | cancelled → (reopen) → open`. Only the repo-layer transition functions can mutate `status`; the generic `update_intake` cannot. Prevents future CLI or API code from bypassing the lifecycle.
- **Click nested groups.** Third Track to adopt this shape (`advanced fleet` from 150, `hardware scan` from 140). Pattern is now stable.
- **No AI this phase.** Phase 160 is pure CRUD. Track G adds AI in 163 (priority scoring), 166 (parts sourcing), 167 (labor estimation). Keeping 160 AI-free = cheap + deterministic tests.

## Verification Checklist

- [x] Migration 025 registered in `MIGRATIONS`; `SCHEMA_VERSION` 24 → 25.
- [x] Fresh `init_db()` creates both `shops` and `intake_visits` with 3 indexes.
- [x] `rollback_migration(25)` drops both tables; `SCHEMA_VERSION` decrements.
- [x] Existing Phase 113 `customers` table untouched; `UNASSIGNED_CUSTOMER_ID=1` still present post-migration.
- [x] `UNIQUE (owner_user_id, name)` on `shops` → `ShopNameExistsError` on duplicate.
- [x] `intake_visits.status` CHECK rejects invalid values.
- [x] Creating intake with missing `customer_id`/`vehicle_id` → explicit repo error (not raw `IntegrityError`).
- [x] `close_intake` on already-closed intake → `IntakeAlreadyClosedError`.
- [x] `reopen_intake` clears `closed_at` + `close_reason`.
- [x] `cancel_intake` sets status to `'cancelled'`, not `'closed'`.
- [x] Deleting shop CASCADE-drops its intakes; deleting customer with intake history → `RESTRICT` error.
- [x] `list_intakes(status='open')` returns only open intakes.
- [x] `list_open_for_bike(vehicle_id)` UX helper works; returns empty when none open.
- [x] `shop profile init` idempotent when same name re-run (prompts confirm-overwrite or exits cleanly).
- [x] `shop customer add/list/search/update/deactivate` round-trip cleanly through the existing `crm/` layer.
- [x] `shop customer link-bike/unlink-bike/bikes` delegate to `crm/customer_bikes_repo.py` without duplicating logic.
- [x] `shop customer deactivate 1` refuses to touch the Unassigned placeholder.
- [x] `shop intake create` missing-bike → Phase 125-style remediation hint (`motodiag garage add`).
- [x] `shop intake create --shop X --customer Y --bike Z` wires a row with correct FKs.
- [x] `shop intake list --status open --since 7d` returns last-7-day open queue.
- [x] `shop intake show INTAKE_ID` renders denormalized shop+customer+bike.
- [x] `shop intake close/reopen` round-trip, guarded by `IntakeAlreadyClosedError` and `IntakeNotFoundError`.
- [x] `shop intake reopen --yes` skips confirmation prompt.
- [x] `--json` on list/show returns valid JSON (schema-checked in tests).
- [x] New top-level group `motodiag shop --help` lists three subgroups.
- [x] Phase 113 + Phase 150 (fleet) regression still GREEN.
- [x] Full regression (~3349 tests) still GREEN post-migration.
- [x] Zero live API tokens this phase.

## Risks

- **customers FK = RESTRICT could surprise users.** A mechanic who deactivates-then-reactivates via the CRM CLI should still be able to delete with no intake history. Tests must cover: delete-customer-with-zero-intakes succeeds; delete-customer-with-one-intake raises friendly error. Raw SQLite errors → `ClickException` with remediation ("deactivate instead, or delete the intakes first").
- **`reported_problems` freetext is unstructured.** Phase 162 will want to parse into categorized issues. Risk: mechanics write inconsistent/unsearchable notes. Mitigation: Phase 162 can migrate unstructured text into structured issue rows without schema change here.
- **Shop+customer+vehicle cross-ownership leakage.** Multi-user shops aren't scoped yet — any user sees any shop's intakes. Phase 172 (multi-mechanic) is where per-shop RBAC lands. Until then, `owner_user_id=1` is placeholder (same pattern as fleets).
- **CLI flag sprawl.** `shop intake create --shop X --customer Y --bike Z` is three flags minimum. Mitigation: default `--shop` to the only active shop if exactly one exists; prompt if multiple (Phase 125 remediation pattern).
- **SCHEMA_VERSION bump + in-flight parallel Builders.** Track G Phases 161/162 each want a migration too. File-overlap rules apply — 160 merges first, 161 rebases on new SCHEMA_VERSION, 162 on 161's.
- **Hours JSON is schemaless.** `hours_json` stored as opaque TEXT. Risks malformed input. Mitigation resolved: repo-layer `_validate_hours_json` enforces parseability + object-shape (tests cover malformed strings and list-type payloads). Day-key names remain locale-flexible — shops may use locale variants.

## Deviations from Plan

Three purposeful expansions, all caught during build and kept because they strengthen the Track G foundation:

1. **`profile list` + `profile delete` subcommands added.** Plan had 3 profile subcommands (init/show/update); shipped 5. Rationale: once `list_shops` returns `open_intake_count` + `total_intake_count` roll-ups, not surfacing that to the CLI meant mechanics had no way to see their own shop inventory without a direct repo call. And hard-delete is a legitimate need when a shop was created under a typo'd name — soft-deactivate alone is ergonomic for active shops but useless for typos. Both ship with confirm-prompt + `--force` escape per Phase 148 precedent.

2. **`intake cancel` subcommand added.** Plan's intake lifecycle called out `open → closed | cancelled → (reopen) → open` but only wired `close` + `reopen` in the CLI. Shipped with a distinct `cancel` subcommand delegating to `intake_repo.cancel_intake`. Reason: Phase 171 shop analytics needs to filter completed-from-withdrawn at the SQL layer (`WHERE status='closed' AND close_reason != 'customer-withdrew'`), not post-hoc. Having a dedicated CLI entry point pairs with the repo split naturally.

3. **`reactivate_shop` symmetric counterpart added to `shop_repo.py`.** Plan had only `deactivate_shop`. Shipped `reactivate_shop` alongside because the tests immediately exposed the asymmetry — a shop soft-deleted by mistake had no repo-layer reversal path. Seven extra lines, one test covering the round-trip. Not surfaced to CLI this phase (no user has reported the need); can promote later trivially.

Scope held for later phases as planned:
- No AI wiring (Phase 163 adds priority scoring, 166 parts sourcing, 167 labor estimation).
- No work-order layer (Phase 161).
- No structured issue logging (Phase 162).
- No invoicing (Phase 169).
- No multi-user/per-shop RBAC (Phase 172).

## Results

| Metric | Value |
|---|---|
| Phase-specific tests | 44 passed in 47.98s (planned ~40) |
| Full regression | **3395 passed, 0 failed** (was 3349 at Phase 159 close) |
| Production code shipped | 1,884 LoC across `shop/` (881) + `cli/shop.py` (1003) |
| Test code shipped | 735 LoC (test_phase160_shop.py) |
| New DB tables | 2 (`shops`, `intake_visits`) |
| New DB indexes | 4 (`idx_shops_owner_name`, `idx_intake_shop_status`, `idx_intake_vehicle`, `idx_intake_customer`) |
| Schema version | 24 → 25 |
| New top-level CLI group | `motodiag shop` with 22 subcommands across 3 subgroups |
| Live API tokens burned | 0 |
| AI calls | 0 |
| Migrations added | 1 (025) |
| Existing packages modified | `cli/main.py` (+6 LoC additive-only), `core/database.py` (SCHEMA_VERSION bump only), `core/migrations.py` (migration 025 appended) — zero changes to `crm/`, zero changes to any existing repo |

**Key finding:** reusing Phase 113's dormant `crm/` substrate was the load-bearing design choice. Phase 113 shipped `customers` + `customer_bikes` tables and repos in March but never wired a CLI, so the data model existed but wasn't discoverable. Phase 160 promoted it to user-facing — `motodiag shop customer {add,list,search,...}` is the first CLI surface for a code path that's been in the codebase for 47 phases. This validates the "build substrate first, surface later" rhythm that Phases 150 (fleets) and 157 (baselines) also used: a repo without a CLI is a latent capability, and shipping the CLI later is a cheap unlock. Track G phases 161-174 can compound on this — work orders (161) will attach to the same `intake_visits.id`, issues (162) will link to work orders, and the invoicing loop (169) closes back on the intake row created here. The narrow two-table scope of 160 keeps that chain renameable if downstream phases need to refactor.
