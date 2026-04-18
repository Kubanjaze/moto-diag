# MotoDiag Phase 148 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 12:30 — Plan written, v1.0

**First Track F phase.** Promotes `advanced` package Scaffold → Active. Ships mileage/age-based failure prediction: given a bike (garage slug OR direct args), cross-reference `known_issues` against current mileage + age, rank likely upcoming failures with time/miles-to-onset + confidence + preventive action. The phase that turns 50+ seed rows from passive reference data into actionable forecast.

**Scope:**
- `advanced/__init__.py` (promoted), `advanced/models.py` (~80 LoC FailurePrediction + PredictionConfidence), `advanced/predictor.py` (~300 LoC).
- `cli/advanced.py` (~250 LoC register_advanced + predict subcommand, two-mode grammar).
- `cli/main.py` +3 LoC registration between `register_hardware` + `register_completion`.
- `implementation.md` package inventory: `advanced` Scaffold → Active.
- No migration. No new DB tables. No AI. Zero live tokens.
- ~35 tests across 4 classes (TestFailurePrediction×5, TestPredictor×12, TestPredictCommand×15, TestRegression×3).

**Design non-negotiables:**
1. **Zero migration.** Migration 018 (add typical_onset_mi/preventive_action/parts_cost_cents/verified_by to known_issues) deferred to Phase 149. Rationale: (a) coupling to 142/145 in-progress migrations blocks Track F on Track E; (b) adopting new columns requires seed-data regeneration belonging in 149; (c) FailurePrediction model shaped for future columns — Phase 149 populates without API churn.
2. **Heuristic severity-to-mileage-onset.** critical=15k, high=30k, medium=50k, low=80k — calibrated against TC88/CCT/KLR seed rows. Heuristic-sourced predictions demoted to MEDIUM/LOW confidence deliberately. Phase 149 replaces with real per-issue onset data.
3. **`verified_by = "forum"` substring heuristic** honors user-memory priority. Scans description+fix_procedure for forum markers. Surfaced as footer count + JSON field. NOT a filter (would hide service-manual predictions); Phase 149 adds `--only-verified`.
4. **No `vehicles.mileage` persistence.** `--current-miles N` CLI flag: required in direct-args, optional in `--bike`. Persistence deferred to roadmap phase 152 service history tracking.
5. **Two-mode CLI grammar** reuses Phase 140 `hardware scan --bike | --make` pattern.

**Test plan (~35):**
- TestFailurePrediction (5): Pydantic round-trip, mode="json" enum serialization (Phase 131 lesson), confidence score range, year_range tuple stability.
- TestPredictor (12): fixture matching, exact/family/make/generic tiering, horizon filter, severity filter, mileage bonus, mileage=None graceful degradation, dedup, "Forum tip:" extraction, verified_by forum flagging, empty/nonsense safety, stable sort.
- TestPredictCommand (15): CliRunner all paths — --bike happy, --bike + --current-miles, direct args, --json parseable, empty result yellow, unknown bike remediation, --bike + --make conflict, missing --current-miles direct mode error, empty garage hint, validation errors on horizon/severity, --help.
- TestRegression (3): Phase 140 hardware scan; Phase 12 Gate 1; Phase 08 knowledge base.

**Dependencies:**
- Phase 147 Gate 6 (Track E closure) is the conventional gate before Track F opens. Phase 148 has NO hard code dependencies on 141-146 — pure SW + SQL on existing tables.
- No migration dependency (016/017 still in-progress; Phase 148 doesn't need them).
- No hardware dependency — `advanced predict` works offline after `motodiag db init` + `motodiag garage add`.

**Open questions:**
1. Mileage persistence timing — Phase 149 vs roadmap 152? Plan defers, open to earlier adoption.
2. Migration 018 scope if adopted later — single column vs bundle.
3. Severity-to-onset calibration — initial draft needs validation against canonical rows.
4. `match_tier` column visibility — Rich Table dim vs --json only. Plan: --json only.
5. Agent delegation — Builder-A same as Phase 140 is appropriate for this pure-SW phase.

**Next:** build — agent-delegated Builder-A after Phase 147 Gate 6 passes. Architect trust-but-verify reproduces 35-test run.

### 2026-04-18 17:00 — Build complete (Builder-148 + Architect trust-but-verify)

Seventeenth agent-delegated phase. First Track F phase. Builder-148 shipped:
- `advanced/__init__.py` promoted from Scaffold → Active (5 LoC, exports `FailurePrediction`/`PredictionConfidence`/`predict_failures`).
- `advanced/models.py` (82 LoC) — frozen Pydantic v2 `FailurePrediction` + `PredictionConfidence` enum.
- `advanced/predictor.py` (395 LoC) — `predict_failures(vehicle, horizon_days, min_severity, db_path)` with 4-pass candidate retrieval, match-tier scoring (exact_model=1.0 / family=0.75 / make=0.5 / generic=0.3), severity-keyed heuristic onset (critical=15k/high=30k/medium=50k/low=80k mi), mileage + age scoring bonuses, preventive_action extraction with Forum-tip precedence, verified_by substring heuristic, horizon/severity filters, stable sort cap 50.
- `cli/advanced.py` (281 LoC) — `register_advanced(cli)` + `predict` subcommand with two-mode grammar (`--bike` XOR direct-args), Rich Table output, `--json` output, Phase 125-style remediation.
- `cli/main.py` +6 LoC — `register_advanced(cli)` between `register_hardware` and `register_completion`.
- `tests/test_phase148_predict.py` (720 LoC, 44 tests across 5 classes: `TestFailurePrediction` (5) + `TestPredictor` (15) + `TestExtractionHelpers` (6) + `TestPredictCommand` (15) + `TestRegression` (3)).

Sandbox blocked Python for Builder. Architect ran trust-but-verify: 44/44 passing.

**Zero migrations. No new DB tables. No AI calls. Zero live tokens.** `advanced` package status flips Scaffold → Active in implementation.md.

Deviations from plan:
1. 4-pass retrieval (spec said 2) — covers generic rows where both make and model are NULL.
2. Numbered-step extraction regex relaxed to handle single-line `fix_procedure` content.
3. Match-tier `generic` (not `make`) when issue has a non-null model that doesn't match the vehicle's.
4. Mileage-bonus test re-keyed to generic medium-severity fixture row (stator row saturates at 1.0, no headroom for +0.1 bonus observation).
5. Test count 44 vs ~35 target (extra 6 extraction-helper units + 3 regression).

**Phase 148 GREEN.** Track F kickoff complete; Phases 149-159 (wear analysis, fleet mgmt, etc.) queued for future sessions.
