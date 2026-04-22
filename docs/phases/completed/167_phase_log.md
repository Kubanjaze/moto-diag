# MotoDiag Phase 167 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-22 | **Completed:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-21 — Plan written via Planner-167 agent (10-agent pool)

Plan v1.0 produced by Planner-167. Persisted to `docs/phases/in_progress/167_implementation.md`.

### 2026-04-22 01:55 — Build complete

Architect-direct serial build. Third Track G AI phase. Composes against Phase 162.5 `shop/ai_client.py` — zero direct `anthropic` imports (enforced) + zero raw `UPDATE work_orders` SQL (also enforced via grep test).

Files shipped:

1. **Migration 031** — `labor_estimates` audit history table: wo_id FK CASCADE + skill_tier CHECK (apprentice/journeyman/master) + base_hours + adjusted_hours + skill_adjustment + mileage_adjustment + confidence CHECK 0-1 + rationale + breakdown_json + alternatives_json + environment_notes + ai_model + tokens_in/out + cost_cents + prompt_cache_hit + user_prompt_snapshot (8KB cap). 3 indexes (wo_id, generated_at, ai_model). Append-only; reopened WOs spawn new estimate rows.

2. **`shop/labor_models.py`** (60 LoC) — `LaborEstimate` + `LaborStep` + `AlternativeEstimate` + `ReconciliationReport` Pydantic + `SkillTier`/`ReconcileBucket` Literals. Separated so tests + Phase 169 can import without SDK seam.

3. **`shop/labor_estimator.py`** (466 LoC) — `estimate_labor` + `bulk_estimate_open_wos` + `reconcile_with_actual` + `list_labor_estimates` + `labor_budget` + 3 exceptions (`LaborEstimatorError`, `LaborEstimateMathError`, `ReconcileMissingDataError`) + 4 helpers (`_validate_skill_tier`, `_load_issues_safe`, `_build_user_prompt`, `_check_math`, `_parse_estimate`, `_persist_labor_estimate`). Constants: `DEFAULT_SKILL_ADJUSTMENTS`, `MATH_TOLERANCE_HOURS=0.01`, `RECONCILE_DELTA_THRESHOLD_PCT=20.0`.

4. **`shop/__init__.py`** +45 LoC re-exports 18 names.

5. **`cli/shop.py`** +255 LoC — `labor` subgroup with 6 subcommands (`estimate`, `bulk`, `show`, `history`, `reconcile`, `budget`) + Rich panel renderer with breakdown + alternatives + environment notes. Total `cli/shop.py` now ~3810 LoC across 10 subgroups.

6. **`tests/test_phase167_labor_estimator.py`** (646 LoC, 33 tests across 6 classes including 2 anti-regression grep tests).

**System prompt baked from Domain-Researcher pricing brief** (`_research/track_g_pricing_brief.md`):
- Labor norms rubric (oil change 0.5h, valve adjust 2-3h, brake pad per wheel 1-1.5h, top-end rebuild 8-14h, etc.)
- Per-platform adjustments (HD Twin Cam/M8 pushrod 1.5h vs Honda/Yamaha/Suzuki/Kawasaki I4 shim 5-6h vs dual-sport screw 2h)
- Skill tier multipliers (apprentice +25%, journeyman 0%, master -15%)
- Mileage/environment adjustments (>50k +10%, >100k +20%, coastal salt +30-50%)

**Math-consistency guard:** After parsing AI response, verify `adjusted_hours ≈ base_hours * (1 + skill_adjustment) * (1 + mileage_adjustment)` within 0.01h. On mismatch, retry once at temperature 0.1; second failure raises `LaborEstimateMathError`. Defensive against AI hallucinating adjusted values that don't match stated multipliers. Tests cover the raise-immediately path via injected fake scorer.

**Write-back discipline (canonical Track G AI rule):** `estimate_labor(wo_id, ..., write_back=True)` writes back `estimated_hours` via Phase 161 `update_work_order(wo_id, {"estimated_hours": est.adjusted_hours})` — NEVER raw SQL. Inherits `_validate_hours` (non-negative check) for free. Two grep-test guarantees in `tests/test_phase167_labor_estimator.py`:
- `test_labor_estimator_does_not_import_anthropic_directly` — no direct SDK imports.
- `test_labor_estimator_does_not_write_raw_sql_to_work_orders` — no raw UPDATE/INSERT/DELETE against work_orders.

**Reconciliation:** `reconcile_with_actual(wo_id)` compares the most recent estimate against completed WO's actual_hours. Pure arithmetic, no AI call. Buckets delta at ±20%: "within" / "under" (actual > estimated by >20%) / "over" (actual < estimated by >20%). Raises `ReconcileMissingDataError` on non-completed WO, missing actual_hours, or no prior estimate.

**Tests:** 33 GREEN across 6 classes (TestMigration031×4 + TestEstimateLabor×11 + TestReconcile×5 + TestBulkEstimate×4 + TestLaborCLI×6 + 2 anti-regression grep) in 50.32s. All AI calls via `_default_scorer_fn` injection seam — zero live tokens.

**Targeted regression: 370 GREEN in 542s (9m 2s)** covering Phase 131 (ai_response_cache) + Phase 153 (parts catalog) + Track G phases 160-167 + Phase 162.5. Zero regressions across all dependencies.

Build deviations:
- Test fixture closure pattern bug: `make_fake_scorer`'s inner function used default-parameter signatures for `model`/`skill_tier` that got overridden by `estimate_labor`'s call-site kwargs. Fixed by renaming closure captures + `**_call_kwargs` sink. One iteration.
- Math guard retry path skipped when `_default_scorer_fn` is present (no live client to retry against). Fake scorer with math-inconsistent output immediately raises `LaborEstimateMathError`. Tests cover both paths.
- 33 tests vs ~32 planned (+1 grep test for raw-SQL audit).

### 2026-04-22 02:00 — Documentation finalization

`implementation.md` promoted to v1.1. Verification Checklist all `[x]`. Deviations + Results sections appended. Key finding: third Track G AI phase validates the canonical composition pattern fully generalizes — `estimate_labor` is structurally identical to `recommend_source` (166) and `score_work_order` (163). Two anti-regression grep tests form the Track G AI discipline audit: no direct anthropic imports, no raw SQL to shared tables.

`phase_log.md` carries this entry. Both files moved to `docs/phases/completed/`.

Project-level updates:
- `implementation.md` schema_version footnote v30 → v31
- `implementation.md` Database Tables: append `labor_estimates` row
- `implementation.md` Phase History: append Phase 167 row
- `implementation.md` Shop CLI Commands: bumped 66 → 72 subcommands; added `motodiag shop labor` row
- `phase_log.md` project-level: Phase 167 closure entry; third AI phase locks canonical pattern
- `docs/ROADMAP.md`: Phase 167 row → ✅
- Project version 0.9.8 → 0.9.9

**Key finding:** The two anti-regression grep tests are now the structural promise of Track G AI: (1) `shop/ai_client.py` is the single Anthropic SDK entry point for the Track; (2) Phase 161's `update_work_order` whitelist is the single write path to `work_orders`. Both guarantees survive future refactors because the tests fail loudly on drift. This is the same audit discipline Phase 165 locked for the parts-cost recompute path, now generalized across all write-back AI phases.
