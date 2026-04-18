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
