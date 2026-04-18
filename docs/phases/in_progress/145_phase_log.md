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

### 2026-04-18 — Bug fix #1: TestCompatCLI fixture db_path routing

**Issue:** All 16 tests in `TestCompatCLI` erroring during fixture setup / CLI invocation. Root symptom per Builder-145's deviation note: the CLI subcommands call repo functions without an explicit `db_path=` kwarg (e.g. `_cr.list_adapters(chipset=chipset, transport=transport)`, `_cr.get_adapter(adapter_slug)`, `_cr.check_compatibility(...)`), so the resolved DB path flows through `get_connection(None)` → `get_db_path()` → `get_settings().db_path`. The original `cli_runner_with_db` fixture relied on `monkeypatch.setenv("MOTODIAG_DB_PATH", path) + get_settings.cache_clear() + assert get_settings().db_path == path`. On the assert-failure branch — or on any Windows case where pydantic-settings' re-read didn't pick up the monkeypatched env var before a module-cached `Settings()` was consulted — the CLI would read from the developer's real shop DB instead of the tmp DB, and the CLI would find either no seeded rows (causing "No adapters" panels and `len(data) >= 20` assertions to fail) or the wrong seed set.

**Root cause:** Single-layer env-var redirection was fragile for this phase because:
1. The assertion `assert cfg_mod.get_settings().db_path == path` inside the fixture could raise AssertionError on any Settings resolution quirk, cascading into ERRORS (not FAILs) across the entire `TestCompatCLI` class.
2. Some repo calls inside the CLI use `get_connection()` with no args, and the `get_db_path()` indirection goes through the full pydantic-settings pipeline each time — any transient cache-state mismatch between fixture setup and CLI invocation routes the call to the wrong DB.
3. Unlike Phase 140 (which patches only `init_db` at the hardware-module level and then has each test patch the specific repo function call), Phase 145 has ~15 CLI tests each exercising multiple repo calls, so per-test per-call patching was not feasible.

**Fix:** Three-layer redirect, installed in dependency order:
1. `monkeypatch.setenv("MOTODIAG_DB_PATH", path)` + `reset_settings()` — covers the normal `get_settings()` path (mirrors Phase 131 `cli_db` pattern which passes).
2. `monkeypatch.setattr(db_mod, "get_db_path", lambda: path)` — belt-and-braces bypass of settings entirely. `get_connection(None)` inside `motodiag.core.database` resolves `get_db_path` via the module's own globals, so patching at the module attribute level routes every subsequent `get_connection(None)` call to the tmp DB regardless of what state the pydantic-settings cache is in.
3. `monkeypatch.setattr(hw_mod, "init_db", _patched_init)` — retained from the original fixture. Matches Phase 140 / 141 / 142 / 144 pattern for `init_db()` (no args) calls inside CLI command bodies.

Seeding now runs AFTER layers 1-2 are installed, so the explicit `db_path=path` kwarg on `seed_all` and the implicit `db_path=None` paths inside `add_adapter` both land in the same tmp file.

Removed the brittle `assert cfg_mod.get_settings().db_path == path` line — `reset_settings()` returns the fresh Settings without asserting. Layer 2 makes the assertion redundant since `get_db_path` is pinned directly.

Wrapped the `yield` in `try/finally` to guarantee `get_settings.cache_clear()` runs on teardown even if a test raises.

**Files:** `tests/test_phase145_compat.py` lines 637-701 (`cli_runner_with_db` fixture body).

**Verified:** unable to execute pytest from the sandboxed Builder-145-Fix runtime (bash/PowerShell permission denied for the agent session). Fix applied by inspection of:
- `motodiag/core/database.py:221-223` — `get_connection(db_path=None)` uses `path = db_path or get_db_path()` where `get_db_path` resolves via the module's own globals at call time. `monkeypatch.setattr(db_mod, "get_db_path", ...)` therefore takes effect for every `get_connection(None)` call the CLI makes.
- `motodiag/hardware/compat_repo.py:54` — imports only `get_connection`, not `get_db_path`. The direct patch on `db_mod.get_db_path` flows through transparently to every `compat_repo` function that passes `db_path=None`.
- `motodiag/hardware/compat_loader.py:30-34` — imports only from `compat_repo`. Same flow.

Architect runs `.venv/Scripts/python.exe -m pytest tests/test_phase145_compat.py -q` as trust-but-verify. Target: 57/57 pass with zero regressions on Phase 139's 31 AutoDetector tests and Phase 134/140/141 smoke.

### 2026-04-18 15:00 — Bug fix #2 (Architect): compat_notes.json slug mismatch

**Issue:** After Builder-145-Fix's three-layer fixture redirect landed, 15 TestCompatCLI tests still ERRORed with `ValueError: add_compat_note: unknown adapter_slug 'obdlink-cx'`. The fixture fix worked; a deeper seed-data bug remained.

**Root cause:** `compat_data/compat_notes.json` referenced `"adapter_slug": "obdlink-cx"` on line 59, but `compat_data/adapters.json` line 273 defines the slug as `"scantool-obdlink-cx"` (ScanTool's OBDLink CX Bluetooth 5 adapter). One-token typo in Builder-145's seed data — slug drift between adapters.json and compat_notes.json.

**Fix:** `sed -i 's/"adapter_slug": "obdlink-cx"/"adapter_slug": "scantool-obdlink-cx"/' src/motodiag/hardware/compat_data/compat_notes.json`. Verified all 9 distinct slugs in compat_notes.json now match actual entries in adapters.json.

**Files:** `src/motodiag/hardware/compat_data/compat_notes.json` line 59.

**Verified:** `.venv/Scripts/python.exe -m pytest tests/test_phase145_compat.py -q` → `57 passed in 51.12s`.

**Build-complete sign-off:** Phase 145 moves from YELLOW → GREEN. Both Builder-145-Fix's fixture fix (bug #1) AND Architect's slug fix (bug #2) needed to reach green. Docs ready to finalize to v1.1 + move to `completed/`.
