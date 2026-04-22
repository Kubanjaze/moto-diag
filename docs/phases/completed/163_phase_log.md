# MotoDiag Phase 163 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-21 | **Completed:** 2026-04-21
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-21 — Plan written via Planner-163 agent (10-agent pool)

Plan v1.0 produced by Planner-163 in Stage A wave. Persisted to `docs/phases/in_progress/163_implementation.md`. Three Track G AI planners (163, 166, 167) converged on the "extract shared AI client helper" recommendation — that became Phase 162.5 (shipped 23:40 today before this phase).

### 2026-04-21 23:55 — Build complete

Architect-direct serial build. **First Track G phase to spend AI tokens** — composes against the Phase 162.5 `shop/ai_client.py` substrate.

Files shipped:
- **`shop/priority_models.py`** (82 LoC) — `PriorityScorerInput` + `PriorityScoreResponse` + `PriorityScore` Pydantic models. Separated from priority_scorer so tests can import schemas without pulling the SDK seam.
- **`shop/priority_scorer.py`** (311 LoC) — `score_work_order` + `rescore_all_open` + `priority_budget` + `get_latest_priority_score` + 4 helper functions (`_wait_time_penalty`, `_priority_from_rubric`, `_should_apply`, `_load_issues_safe`, `_find_kb_matches_safe`, `_customer_prior_ticket_count`) + 3 exceptions (`PriorityScorerError`, `PriorityCostCapExceeded`, `PriorityBudgetExhausted`). Constants: `CONFIDENCE_APPLY_THRESHOLD=0.75`, `PER_CALL_COST_CAP_CENTS=3`, `DEFAULT_SESSION_BUDGET_CENTS=50`, `DEFAULT_RESCORE_LIMIT=10`. Full system prompt baked from research-brief 4-tier rubric (CRITICAL/HIGH/MEDIUM/LOW) + wait-time aging + customer-history bonus + ceiling rules.
- **`shop/__init__.py`** +29 LoC re-exports 13 names.
- **`cli/shop.py`** +188 LoC — `priority` subgroup with 4 subcommands (`score / rescore-all / show / budget`) + Rich panel renderer. Total `cli/shop.py` now 2530 LoC.
- **`tests/test_phase163_priority_scoring.py`** (414 LoC, 26 tests across 5 classes including anti-regression grep-test).

**Mechanic-intent preservation:** AI-proposed priority only overwrites `work_orders.priority` when `confidence > 0.75`. Below threshold, score is logged via Phase 131 `ai_response_cache` (kind='priority_score') but DB priority untouched. Safety override (`safety_risk=true AND priority=1`) bypasses the threshold. `--force` CLI flag is the explicit human override.

**Write-back routing:** Calls `update_work_order(wo_id, {"priority": int})` from Phase 161 — never raw SQL. Inherits `_validate_priority` (1-5 range CHECK) + lifecycle guard for free.

**Anti-regression grep test:** `test_priority_scorer_does_not_import_anthropic_directly` scans `priority_scorer.py` source for direct `import anthropic` / `from anthropic` lines and fails the test if found. Phase 162.5 contract enforcement.

**Tests:** 26 GREEN across 5 classes in 10.74s:
- `TestPureHelpers` (9): `_wait_time_penalty` boundaries (0/24/72), `_priority_from_rubric` clamps to 1 and 5, `_should_apply` covers safety override / low-confidence / force / no-change branches.
- `TestScoreSingle` (7): high-confidence applies + writes back, low-confidence logs only + preserves mechanic priority, safety overrides low-confidence, no-change skips apply, force overrides threshold, terminal WO raises, returns full PriorityScore with metadata.
- `TestRescoreAll` (5): iterates open WOs, budget exhausted raises with partial results, dry-run rolls back write-back, limit caps candidates, no-open-WOs returns empty.
- `TestPriorityCLI` (4): help lists 4 subcommands, score JSON, rescore-all JSON, budget empty.
- `TestAntiRegression` (1): grep test enforces no direct anthropic import.

All AI calls injected via `_default_scorer_fn` seam — zero live tokens.

**Targeted regression:** 209 GREEN in 111.76s covering Phase 131 (ai_response_cache — direct dependency) + all Track G phases 160-163 + Phase 162.5. Zero regressions.

Build deviations:
- 26 tests vs ~35 planned — pure helper + CLI coverage trimmed because formula is straightforward and mock injection seam is exercised heavily by score-single. Anti-regression grep test added.
- One iteration on test fixture: PriorityScoreResponse rationale field has `min_length=8`; initial test fixtures used "meh"/"same" (3-4 chars) which failed Pydantic validation; bumped to "ambiguous evidence" / "no change needed" — passed first retry.
- `get_latest_priority_score` lookup is best-effort: SHA256 cache key doesn't preserve wo_id (input is hashed), so retrieval scans 50 most-recent cache rows. CLI `show` subcommand exists but doesn't have a test (mechanics rerun `score` for guaranteed-fresh result).

### 2026-04-22 00:00 — Documentation finalization

`implementation.md` promoted to v1.1 — Verification Checklist all `[x]`, Deviations + Results sections appended. Key finding: Phase 162.5 extraction paid off exactly as predicted (5-line composition vs ~80 LoC duplication); injection seam pattern is the load-bearing test convention every Track G AI phase will use.

`phase_log.md` carries this entry.

Project-level updates:
- `implementation.md` Phase History: append Phase 163 row with rollout details + key finding
- `implementation.md` Shop CLI Commands: bumped 46 → 50 subcommands; added `motodiag shop priority` row
- `phase_log.md` project-level: Phase 163 closure entry — first Track G AI phase ships; injection seam pattern documented as canonical
- Project version 0.9.4 → 0.9.5 (first Track G AI phase milestone)
- 163_implementation.md + 163_phase_log.md moved to docs/phases/completed/

**Key finding:** The Phase 162.5 → Phase 163 progression validates the rule-of-three extract decision. Phase 163 ships with a tight, focused module (393 LoC across two files) that delegates all Anthropic/cache/cost machinery to `shop.ai_client`. Subsequent AI phases (166 sourcing, 167 labor) will follow this exact composition shape — Pydantic models in their own file, scorer module with `_default_scorer_fn` injection seam + grep-test, CLI subgroup composing on the scorer. Pattern is now canonical. Mechanic-intent preservation via the 0.75 confidence threshold is the load-bearing safety property — without it, the AI could silently drift mechanic priorities on every batch run.
