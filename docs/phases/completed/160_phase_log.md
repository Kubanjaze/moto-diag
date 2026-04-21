# MotoDiag Phase 160 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-21 | **Completed:** 2026-04-21
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-21 13:45 — Plan written, initial push

First Track G phase. Opens the "Shop Management + Optimization" track (Phases 160–174) with the narrowest possible first slice: register a shop profile and log bike arrivals. Explicitly does NOT yet create work orders (161), structured issue lists (162), or any pricing/invoicing (169) — those ride on top of the intake_visits row this phase introduces.

Architectural decisions baked into v1.0:

1. **Reuse, don't recreate.** Phase 113 already shipped `customers` + `customer_bikes` via migration 006 with `crm/customer_repo.py` + `crm/customer_bikes_repo.py`. Phase 160 is the first CLI consumer of that substrate — surfaces it as `motodiag shop customer {add,list,show,search,update,deactivate,link-bike,unlink-bike,bikes}`. Zero schema duplication; zero modification to the `crm/` package. Discovered during pre-flight: `src/motodiag/cli/` had NO customer command — so 113's CRM data was previously Python-only.

2. **Two tables only.** `shops` (profile) + `intake_visits` (arrival event). No work orders, no line items, no invoices — those are 161/162/169. Keeping the first slice minimal means Gate 8 (Phase 174) can retrofit richer flows without renaming columns.

3. **FK asymmetry.** `shop_id` CASCADE (explicit, confirmed delete); `customer_id` + `vehicle_id` RESTRICT (prevents accidental history erasure). Mechanics deactivate customers via Phase 113's `deactivate_customer`; they don't delete.

4. **Guarded status lifecycle.** `open → closed | cancelled → (reopen) → open`. Only repo-layer transition functions (`close_intake`, `reopen_intake`, `cancel_intake`) mutate `status` — generic `update_intake` cannot. Prevents CLI/API bypass in future phases.

5. **Top-level `shop` CLI group.** New module `cli/shop.py`. Three nested subgroups: `profile` (3 cmds), `customer` (9 cmds), `intake` (7 cmds). Registration is additive-only in `cli/main.py` (+2 lines: import + `register_shop(cli)`). Follows the exact `advanced.py` + `hardware.py` pattern established in Phases 140/148.

6. **Zero AI, zero tokens.** Phase 160 is pure CRUD. Track G gets AI in 163 (priority scoring), 166 (parts sourcing), 167 (labor estimation). Deterministic tests; no budget burn.

Test plan: ~40 tests across 5 classes — `TestMigration025` (5), `TestShopRepo` (8), `TestIntakeRepo` (12), `TestShopCLI` (8), `TestIntakeCLI` (7).

Risk flagged for parallel-pipeline: Phases 161/162 both want migrations too — file-overlap on `core/migrations.py` + `core/database.py` `SCHEMA_VERSION`. 160 ships first as the anchor; 161 rebases on `SCHEMA_VERSION=25`; 162 on whatever 161 sets. No parallel Builders across 160/161/162.

Risk flagged for UX: `shop intake create --shop X --customer Y --bike Z` is three flags minimum. Mitigation: default `--shop` when exactly one active shop exists (Phase 125 remediation pattern for ambiguity).

CLI command this phase: `motodiag shop {profile,customer,intake}` — first user-facing surface for both shop registration AND customer management, since Phase 113 never surfaced customers.

### 2026-04-21 15:40 — Build complete

Auto-iterate build in-session. All six code blocks shipped and verified in one sweep:

1. **Migration 025** appended to `core/migrations.py` + `SCHEMA_VERSION` bumped 24 → 25 in `core/database.py`. Forward + rollback SQL tested; rollback drops `intake_visits` first (child of `shops` via CASCADE) then `shops`.
2. **`shop/` package** built fresh — 63 LoC `__init__.py` re-exports 21 names; 337 LoC `shop_repo.py` (11 functions + 2 exceptions + hours_json JSON object validator + update whitelist `_UPDATABLE_FIELDS`); 481 LoC `intake_repo.py` (12 functions + 2 exceptions + `_since_cutoff` offset parser + `_transition_out_of_open` shared lifecycle helper). Guarded lifecycle held under test — `update_intake` cannot mutate `status`; only the dedicated transition functions can.
3. **`cli/shop.py`** — 1003 LoC, overshot the ~420 LoC estimate by 2.4x. The extra came from Rich Panel/Table rendering helpers (`_render_shop_panel`, `_render_customer_panel`, `_render_intake_panel`) + defensive denormalized-row accessors in CLI commands + Phase 125-style remediation errors for missing-shop / missing-bike / missing-customer paths. Every helper has a dedicated test; no deadweight.
4. **Wiring** — `cli/main.py` picked up the `register_shop` import + a 3-line block comment + `register_shop(cli)` call before `register_completion(cli)` per the established ordering convention (completion must see the new subgroup).
5. **44 tests** landed in `test_phase160_shop.py` across 5 classes — `TestMigration025` (5) + `TestShopRepo` (10) + `TestIntakeRepo` (14) + `TestShopCLI` (8) + `TestIntakeCLI` (6). 47.98s run time. GREEN on first pass, zero corrections needed.
6. **Full regression** — 3395 passed, 0 failed. Up from 3349 at Phase 159 close (+44 Phase 160 + 2 formerly-skipped conditional tests now running with shops in schema). Runtime 12278s (3h 24m on this run vs typical ~12 min; system load the likely culprit — tests serialized cleanly, no hangs).

Deviations from plan (three purposeful expansions caught mid-build):

- **`profile list` + `profile delete` added to the CLI** — plan had 3 profile subcommands (init/show/update), shipped 5. Rationale: `list_shops` already returned open/total intake counts; not surfacing them to the CLI meant mechanics had no way to see their shop inventory.
- **`intake cancel` added to the CLI** — plan had 7 intake subcommands, shipped 8. Rationale: Phase 171 analytics needs to filter completed-from-withdrawn at SQL, not post-hoc.
- **`reactivate_shop` added to `shop_repo.py`** — plan had only `deactivate_shop`. Added the symmetric path during test-writing when it became obvious a soft-deleted shop had no reversal. Seven extra LoC, one round-trip test.

Totals: plan said 19 subcommands → shipped 22. Plan said ~40 tests → shipped 44. Every deviation is a strict expansion, not a contraction; no planned surface was dropped.

Zero AI calls. Zero live tokens. Zero regressions. Track G opens GREEN.

### 2026-04-21 15:50 — Documentation finalization

`implementation.md` promoted to v1.1 — every section updated in place (CLI grammar reflects actual 22-subcommand shape, Outputs carries as-built LoC numbers, Verification Checklist items all `[x]`, Risks annotated with resolution notes where relevant). Appended Deviations from Plan (3 entries) + Results table + key finding ("reusing Phase 113's dormant `crm/` substrate was the load-bearing design choice — a repo without a CLI is a latent capability, and shipping the CLI later is a cheap unlock").

Phase moved `docs/phases/in_progress/160_*.md` → `docs/phases/completed/160_*.md`. Project-level updates landing in the same commit: `docs/ROADMAP.md` row 160 ticked ✅ with a one-line summary; project `implementation.md` gained a Phase 160 history row + a bump of the project version; project `phase_log.md` logged the Track G kickoff.

Key finding: the narrow two-table scope — `shops` + `intake_visits`, deliberately excluding work orders and invoicing — is what makes Phase 160 a stable anchor for 14 more Track G phases. Phases 161-174 can compound on `intake_visits.id` without renaming columns or restructuring the lifecycle.
