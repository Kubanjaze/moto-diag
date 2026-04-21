# MotoDiag Phase 160 — Phase Log

**Status:** Planned | **Started:** 2026-04-21 | **Completed:** —
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
