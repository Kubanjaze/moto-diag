# Track G — Shop Management & Optimization (Phases 160-173) — Closure Summary

**Status:** ✅ Closed via Phase 174 Gate 8 | **Closed:** 2026-04-22
**Version:** 0.11.0 package / v36 schema

---

## One-Line Summary

Built a complete motorcycle-shop management console — **16 subgroups,
123 subcommands** under `motodiag shop *` — covering every step from
a bike rolling onto the lot through a paid invoice, with audit
trails, multi-mechanic support, template-rendered customer
communications, read-only analytics dashboards, and JSON-authored
automation rules. All on local-first SQLite, zero runtime AI except
in three dedicated AI phases that share a single composition pattern.

---

## Phase Inventory

| Phase | Title | Kind | Key Deliverable |
|------:|-------|------|-----------------|
| 160 | Shop profile + intake | data | `shops`, `intake_visits` |
| 161 | Work orders | data | `work_orders` + 7-state guarded lifecycle |
| 162 | Issues | data | `issues` + 12-category taxonomy + crosswalk |
| 162.5 | Shared AI client (micro) | infra | `shop/ai_client.py` + rule-of-three extract |
| 163 | Priority scoring | AI | First ShopAIClient consumer + canonical pattern |
| 164 | Triage queue | data | `shops.triage_weights` + deterministic scoring |
| 165 | Parts needs | data | `work_order_parts` + consolidation + audit |
| 166 | Parts sourcing | AI | Second ShopAIClient consumer + vendor taxonomy |
| 167 | Labor estimation | AI | Third ShopAIClient consumer + reconcile arithmetic |
| 168 | Bay scheduling | data | `shop_bays`, `bay_schedule_slots` + greedy scheduler |
| 169 | Invoicing | data | Reuses Phase 118 substrate + micro-migration 033 |
| 170 | Notifications | data | `customer_notifications` + 23 template catalog |
| 171 | Analytics dashboard | read-only | 10 rollups + `dashboard_snapshot` composer |
| 172 | Multi-mechanic RBAC | data | `shop_members`, `work_order_assignments` |
| 173 | Automation rules | engine | JSON rules + 12 conditions × 8 actions registry |
| 174 | Gate 8 integration test | coverage | End-to-end CLI walkthrough + this doc |

**14 phases total** (13 scope phases + 1 micro-phase 162.5 + 1 gate phase 174). **~650-700 targeted regression tests GREEN** at Gate 8 close.

---

## Database Schema

Track G added **14 net-new tables + 12 migrations (025-036)**:

| Table | Owner Phase | Purpose |
|-------|------------:|---------|
| `shops` | 160 | Per-owner shop identity, hours, address, tax id |
| `intake_visits` | 160 | Bike-arrival event log |
| `work_orders` | 161 | Central WO record with 7-state lifecycle |
| `issues` | 162 | Structured per-WO issue log (12 categories × 4 severities) |
| `work_order_parts` | 165 | Per-WO parts junction with 5-state lifecycle |
| `parts_requisitions` | 165 | Immutable shop-scoped shopping-list snapshots |
| `parts_requisition_items` | 165 | Frozen per-part snapshot rows |
| `sourcing_recommendations` | 166 | AI sourcing audit log |
| `labor_estimates` | 167 | AI labor-time audit with full breakdown |
| `shop_bays` | 168 | Bay inventory (lift/flat/specialty/tire/dyno/wash) |
| `bay_schedule_slots` | 168 | Per-slot reservations with overrun detection |
| `customer_notifications` | 170 | Audit-log + queue for workflow-event messages |
| `shop_members` | 172 | Per-shop role (stacked on Phase 112 global RBAC) |
| `work_order_assignments` | 172 | Mechanic reassignment audit trail |
| `workflow_rules` | 173 | JSON rule definitions |
| `workflow_rule_runs` | 173 | Every rule firing (matched or not) |

Plus **one column added via micro-migration 033** (Phase 169): `invoices.work_order_id` — Phase 118 `invoices` + `invoice_line_items` + `accounting.invoice_repo` substrate reused unchanged.

**Zero Phase 112 schema changes.** Phase 172's shop-scoped RBAC stacks on Phase 112 global RBAC by joining `shop_members.role → roles.name` — the permission catalog stays single-source-of-truth.

---

## Design Pillars

These patterns emerged during the Track G build and hardened as each subsequent phase adopted them. They're the load-bearing conventions any future Track should inherit.

### 1. Write-back-through-whitelist

Every mutation to `work_orders` goes through Phase 161 `update_work_order(wo_id, {<allowed field>: value})` — **never raw `UPDATE work_orders` SQL**. Phase 163 (priority), Phase 165 (parts cost), Phase 167 (labor estimate), Phase 172 (reassignment), Phase 173 (rule actions) all comply. Enforced by **per-module anti-regression grep tests** (`test_no_raw_update_work_orders_in_*`) that strip comments + docstrings before checking.

**Why it matters:** `_UPDATABLE_FIELDS` frozenset in `work_order_repo.py` excludes status + all `*_at` timestamps + all `*_reason` fields. Guarded lifecycle functions (`start_work`, `pause_work`, `complete_work_order`, etc.) are the only way to change those. If a downstream contributor bypasses the whitelist, CI catches it before code review.

### 2. Canonical AI composition pattern (Phase 162.5)

All three Track G AI phases (163, 166, 167) compose against a single shared `shop/ai_client.py` module instead of re-implementing Anthropic SDK + cost math + cache integration three times. The pattern:

```
load context → build prompt → ShopAIClient.ask() → parse JSON → persist audit → write-back via whitelist → return
```

Each AI phase:
- Has a dedicated audit table (`priority_scores`, `sourcing_recommendations`, `labor_estimates`)
- Ships a `_default_scorer_fn=None` injection seam for zero-token tests
- Anti-regression greps for `import anthropic` in the module (must be absent)
- Uses Phase 131 `ai_response_cache` via `kind=<phase_name>`

**Why it matters:** Phase 162.5 is a 30-minute, zero-token rule-of-three extract that saved ~250 LoC of duplication + avoided three independent SDK-setup bugs. Pattern now baked into `ai_client.py`; future AI phases inherit it for free.

### 3. Guarded status lifecycles

Every stateful entity in Track G uses a `_VALID_TRANSITIONS` dict gated by dedicated transition functions. Generic `update_<entity>` cannot change status.

Examples:
- **WOs** (Phase 161): `draft→open→in_progress→(on_hold|completed|cancelled)→(reopen)→open`
- **Issues** (Phase 162): `open→(resolved|duplicate|wont_fix)→(reopen)→open`
- **Parts** (Phase 165): `open→ordered→received→installed|cancelled`
- **Slots** (Phase 168): `planned→active→(completed|overrun|cancelled)`
- **Notifications** (Phase 170): `pending→(sent|failed|cancelled)`

Resend / re-open flows create new rows rather than reviving dead ones — preserves audit trails.

### 4. Compose existing rollups, don't duplicate (Phase 171)

`dashboard_snapshot` delegates revenue to Phase 169 `revenue_rollup`, per-day utilization to Phase 168 `utilization_for_day`, and issue stats to Phase 162 — Phase 171 owns only the cross-phase aggregations (turnaround, overrun rate, mechanic performance, top parts/issues, customer repeat). ~520 LoC of analytics shipped without touching any prior module.

### 5. Rules are data, engine is code (Phase 173)

JSON rule definitions in DB columns + fixed dispatcher over frozen `CONDITION_TYPES` + `ACTION_TYPES` registries. Operators author rules without Python changes. Adding a new condition/action type is a 5-line registry entry + validator shape-check + docstring.

Action executors are thin wrappers over existing repos — `set_priority` calls Phase 161 `update_work_order`; `trigger_notification` calls Phase 170; `reassign_to_user` calls Phase 172. Anti-regression grep enforces no raw SQL in `workflow_actions.py`.

### 6. Fail-one-continue-rest action semantics

When a Phase 173 rule fires N actions and one raises, sibling actions still execute. The first error is captured in the run row's `error` column; the full per-action outcome array lives in `actions_log` JSON. Strict nested-savepoint rollback was rejected as disproportionate complexity for a local-first CLI — the audit log gives the mechanic enough information to manually compensate.

### 7. Reuse existing substrate across phase gaps

Phase 169 (invoicing) validated this across a 50+ phase gap: Phase 118's `invoices` + `invoice_line_items` + `accounting.invoice_repo` shipped untouched; Phase 169 added one column + an orchestration module and got a complete revenue-tracking console. Three substrate vocabulary mismatches (enum values, dollars vs cents, NOT NULL customer_id) were reconciled at the new module's boundary rather than by renaming old fields. Zero Phase 118 test regressions.

Phase 172 repeated this pattern with Phase 112 (RBAC).

### 8. Plumbing before transport (Phase 170)

Notifications persist as `status='pending'` rows; actual email/SMS delivery is deferred to a future transport layer (Phase 181+ supervised worker or operator integration). `string.Template` over f-strings for safer placeholder substitution with user-derived content; unresolved placeholders raise `NotificationContextError` at render rather than leaking `$customer_name` to live customers.

---

## The Mechanic Workflow

The full end-to-end flow that Gate 8 exercises:

```
shop profile init           →   shop/profile
shop member add (owner)     →   shop/member (RBAC)
shop member add (tech)
shop customer add + link
shop intake create          →   Track G kickoff — bike on the lot
shop work-order create      →   WO lifecycle starts
shop issue add              →   Structured issue logging
shop priority score         →   AI-ranked priority (optional)
shop triage queue           →   Deterministic ordering across WOs
shop parts-needs add        →   Parts workflow starts
shop parts-needs requisition create
shop sourcing recommend     →   AI sourcing (optional)
shop labor estimate         →   AI labor estimate (optional)
shop bay schedule           →   Bay reservation
shop work-order start       →   Lifecycle: draft → open → in_progress
shop bay start              →   Slot becomes active
shop work-order reassign    →   Mechanic swap mid-repair (if needed)
shop notify trigger wo_in_progress  →   Customer update
shop parts-needs mark-installed     →   Install complete
shop bay complete                   →   Slot terminal
shop work-order complete            →   WO terminal (completed)
shop invoice generate               →   Invoice from WO + labor + parts
shop notify trigger invoice_issued  →   Customer gets invoice link
shop invoice mark-paid              →   Revenue realized
shop analytics snapshot             →   Dashboard includes this WO
shop rule fire <wo_completed rule>  →   Automation follow-up
```

23 CLI steps × 16 subgroups × deterministic audit everywhere.

---

## Known Limitations (Track G → Track H)

- **CLI lifecycle transitions don't auto-fire Phase 173 rules.** `motodiag shop work-order complete` mutates status but doesn't call `trigger_rules_for_event('wo_completed', ...)`. Gate 8's integration test invokes the trigger manually. Track H (Phase 175+) will wire event dispatch into the CLI + repo layer.
- **Notifications queue has no worker.** Rows persist as `status='pending'`; operators must manually `notify mark-sent <id>` or build an external transport. Track J will ship a supervised worker + Twilio/SendGrid integrations.
- **No cross-shop analytics.** `dashboard_snapshot(shop_id=X)` is single-shop-scoped. Multi-shop operators (Phase 118 `company` tier subscribers) need a separate rollup — Track H will add.
- **No permission enforcement on CLI paths.** `has_shop_permission` / `require_shop_permission` (Phase 172) exist as public helpers but the CLI doesn't invoke them yet — any user with DB access can run any command. Track H will wire session-based auth + CLI guards.
- **Rule scheduling is event-only.** No cron-style "run every Monday at 9am" rules. Phase 173's `event_trigger='manual'` + external scheduler is the workaround; Track H may add a lightweight scheduler.

---

## File Inventory

| Location | LoC | Purpose |
|----------|----:|---------|
| `src/motodiag/shop/` | ~4700 | 16 modules (repos, engines, helpers) |
| `src/motodiag/cli/shop.py` | ~5500 | 16 subgroups, 123 subcommands |
| `tests/test_phase16{0-8}_*.py` + `test_phase17{0-4}_*.py` | ~6500 | ~471 phase-specific tests |
| `src/motodiag/core/migrations.py` | +1000 (net) | Migrations 025-036 |
| `docs/phases/completed/16{0-8}_*.md` + `17{0-4}_*.md` | ~35KB | Per-phase implementation + log docs |

Per-phase `implementation.md` files (v1.1) + `phase_log.md` files in `docs/phases/completed/` are the canonical source for each phase's detailed design, build, and test record.

---

## What Track H Should Build On Top

1. **Auto-fire rules on CLI transitions.** Wire Phase 173 `trigger_rules_for_event` into `cli/shop.py` lifecycle subcommands + repo transition functions. Use a thin dispatch decorator (`@fires_event('wo_completed')`).
2. **Session auth + permission guards.** `motodiag login <user>` sets a session; every CLI command calls `require_shop_permission` via a Click callback before executing. Phase 172 helpers exist; Track H wires them.
3. **Transport worker for Phase 170 queue.** `motodiag shop notify drain` subcommand that polls `status='pending'` + dispatches to configured transports (email via SMTP, SMS via Twilio). Failures mark `status='failed'` with `failure_reason`.
4. **Cross-shop analytics for company tier.** `motodiag company analytics` subgroup summing across multiple `shop_id`s owned by the same `users.owner_user_id`.
5. **Scheduled rule triggers.** Cron-style rules (`event_trigger='scheduled_daily'` / `'scheduled_weekly'`) with a `motodiag shop rule schedule` subcommand that records next-fire time; external cron / `motodiag shop rule tick` command drains due rules.
6. **Rule chain protection.** Currently a rule firing an action that triggers another event doesn't cascade re-fire. Track H may add a depth-limited cascade with cycle detection.
7. **Multi-shop membership UI (mobile/web).** Phase 122+ Track I ships a mobile app; it'll consume the existing Phase 172 membership APIs for the "which shop am I at today" UX.

---

## Track G in One Chart

```
                                  Phase 160 (shops, intake)
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 │                      │                      │
       Phase 161 (work_orders) ←────────┘                      │
                 │                                             │
       Phase 162 (issues)                                      │
       Phase 164 (triage)                                      │
       Phase 165 (parts)                                       │
       Phase 168 (bay schedule)                                │
                 │                                             │
         ┌───────┴───────┐                                     │
         │               │                                     │
       Phase 162.5 (shared ShopAIClient)                       │
         │                                                     │
         ├─→ Phase 163 (priority — AI)                         │
         ├─→ Phase 166 (sourcing — AI)                         │
         └─→ Phase 167 (labor — AI)                            │
                                                               │
                                                    Phase 118 substrate
                                                               │
                                                    Phase 169 (invoicing)
                                                               │
                                 Phase 170 (notifications) ────┤
                                 Phase 171 (analytics) ────────┤
                                 Phase 172 (RBAC) ─────────────┤
                                 Phase 173 (rules) ────────────┘
                                                               │
                                                     Phase 174 Gate 8
```

14 phases landed in a single auto-iterate session. Serial discipline
held throughout ("complete each in entirety before moving on").
471+ phase-specific tests shipped. 648+ targeted regression GREEN at
Track G close.

— end of summary —
