# MotoDiag Phase 145 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 11:00 — Plan written, v1.0

Planner-145 drafted v1.0 for Phase 145 — adapter compatibility database. Fifth Track E parallel-planning phase. Foundation for Phase 146 `diagnose --bike` hints and knowledge-base layer answering "will my $30 ELM327 clone actually work on my 2011 Road Glide?" → `partial — Mode 03 works via CAN, bi-directional + HD-proprietary PIDs do not. Dynojet Power Vision ($400) gives full bidirectional.`

**Scope:**
- Migration 017 (schema v16 → v17) — 3 tables (`obd_adapters`, `adapter_compatibility`, `compat_notes`) + 6 indexes. CHECK on status enum, note_type enum, reliability 1-5, price ≥ 0. FK-safe rollback.
- New `src/motodiag/hardware/compat_repo.py` (~280 LoC) — CRUD + queries. `list_compatible_adapters(make, model, year)` returns ranked list (status tier → reliability DESC → price ASC → id ASC). `check_compatibility` with specificity-aware match selection. `protocols_to_skip_for_make` is AutoDetector filter hook.
- New `src/motodiag/hardware/compat_loader.py` (~120 LoC) — idempotent JSON loader with line-aware error reporting.
- New seed data (`compat_data/adapters.json` + `compat_matrix.json` + `compat_notes.json`) — 20-30 real adapters (OBDLink MX+, Vgate iCar Pro, generic ELM327 v1.5, Dynojet PV3, Daytona Twin Tec TCFI, ScanGauge II, HD Digital Tech II), 100+ matrix rows across target bike fleet, ~10 curated notes.
- Extend `cli/hardware.py` (~350 LoC) — new `compat` subgroup with 7 subcommands (list/recommend/check/show/note add/note list/seed).
- Extend `hardware/ecu_detect.py` — one `compat_repo=None` kwarg on AutoDetector.__init__ + filter hook. Backward-compatible (Phase 139's 31 tests unchanged).

**Design non-negotiables:**
1. **Real data, not fake.** Adapters + matrix reflect actual public product specs. Dynojet PV ranks highly on Harley because that's what actually works — not a fantasy.
2. **Price integer cents.** Phase 131 pattern. Float raises TypeError.
3. **Reliability 1-5 is shop-floor opinion.** We document what we know; `compat note add` accumulates institutional knowledge.
4. **SQL LIKE model patterns.** One `CBR%` row covers all CBRs — avoids 1000-row explosion.
5. **Year range doubly-nullable.** NULL+NULL = all years. No sentinel years.
6. **No live API, no scraping.** Curated from public specs. Forum-sourced rows cite URL in `verified_by`.

**Test plan (~57 tests, 7 classes):**
- `TestMigration017` (4) — tables + indexes + SCHEMA_VERSION + rollback.
- `TestAdapterRepo` (10) — CRUD + duplicate-slug idempotency + reliability clamp + price type.
- `TestCompatibilityRepo` (12) — LIKE matching, year filter, ranking, min_status, wildcards, check specificity.
- `TestCompatNotes` (6) — CRUD, wildcard `*`, cascade delete.
- `TestLoader` (6) — JSON parsing, idempotency, error line numbers.
- `TestCompatCLI` (15) — all 7 subcommands happy/error paths.
- `TestAutoDetectorIntegration` (4) — filter-hook + backward-compat regression.

Temp-DB fixture (Phase 128 pattern). Autouse `init_db` monkey-patch for CLI tests (Phase 140 pattern).

**File-overlap warnings:**
- `cli/hardware.py` shared with 141/142/143/144. Additive via distinct subgroups — merge-conflict risk at subgroup registration list only.
- `hardware/ecu_detect.py` — exactly one optional kwarg at end of `__init__`. Phase 139 tests guaranteed untouched.
- Migration 017 assumes 142 ships 016 first. If 142 slips, Phase 145 takes 016; SQL migration-number-independent.
- FK `submitted_by_user_id` → users.id (Migration 005 / Phase 112). Safe.

**Open questions:**
1. Migration 016 status — before Builder runs 017, re-read MIGRATIONS and confirm highest committed version.
2. `cli/hardware.py` file size policy — monolithic (~900 LoC) or extract to `cli/hardware_compat.py`. Builder judgment.
3. Seed data curation ownership — ~5-8 hours of research. Builder does full curation per CLAUDE.md quality rules.
4. Central note-sharing extension — plan scopes local-only; `synced_at` column not pre-added. Flag for future Phase 150+.
5. `protocols_to_skip_for_make` data-density threshold — 3 as cutoff. Phase 146 may tune.
6. `compat seed` auto-run on first `compat` subcommand — plan requires explicit. Open to one-time auto-prompt.

**Next:** parallel wait for 141-144 to land; confirm Phase 142 migration 016 before Builder runs 017. Builder delegation choice deferred — Architect may build directly given JSON curation is part of Builder burden and quality-critical.
