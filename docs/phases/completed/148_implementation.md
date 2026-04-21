# MotoDiag Phase 148 — Predictive Maintenance (mileage/age-based failure prediction)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

First user-facing Track F phase. Promotes the `advanced` package from Scaffold to Active. Given a bike (garage slug OR `--make/--model/--year/--current-miles` direct args), cross-reference the `known_issues` table against the vehicle's current mileage + age and rank likely upcoming failures with time/miles-to-onset, confidence score, and preventive action.

CLI (new `advanced` top-level group, one subcommand in Phase 148; 149-159 extend):
- `motodiag advanced predict --bike SLUG [--current-miles N] [--horizon-days 180] [--min-severity medium] [--json]`
- `motodiag advanced predict --make MAKE --model MODEL --year YEAR --current-miles MI [--horizon-days 180] [--min-severity medium] [--json]`

**Design rule:** zero AI calls, zero migration, zero token budget. Pure SW + SQL on existing `known_issues` + `vehicles` tables.

Outputs:
- `src/motodiag/advanced/__init__.py` — promoted from scaffold, exports `FailurePrediction`, `PredictionConfidence`, `predict_failures`.
- `src/motodiag/advanced/models.py` (~80 LoC) — Pydantic v2 `FailurePrediction` + `PredictionConfidence` enum.
- `src/motodiag/advanced/predictor.py` (~300 LoC) — core function + ranking/scoring helpers.
- `src/motodiag/cli/advanced.py` (~250 LoC) — `register_advanced(cli)` + `predict` subcommand.
- `src/motodiag/cli/main.py` +~3 LoC — register between `register_hardware` and `register_completion`.
- `tests/test_phase148_predict.py` (~35 tests across 4 classes).

**Schema decision:** SHIP WITHOUT migration 018. Use heuristic fallback from existing `severity` + `year_start/year_end` + `fix_procedure` text. Migration 018 (add `typical_onset_mi/years`, `preventive_action`, `parts_cost_cents`, `verified_by` columns) deferred to Phase 149. Phase 148's `FailurePrediction` model already shapes these fields; Phase 149 populates real values without API churn.

## Logic

### 1. Schema posture

Current `known_issues` columns: id, title, description, make, model, year_start, year_end, severity, symptoms, dtc_codes, causes, fix_procedure, parts_needed, estimated_hours, created_at, created_by_user_id. No `typical_onset_mi`, `preventive_action`, `parts_cost_cents`, `verified_by`. Phase 148 ships working prediction today using only existing columns; Phase 149 upgrades data layer.

### 2. `FailurePrediction` (Pydantic v2)

```python
class PredictionConfidence(str, Enum):
    HIGH = "high"        # exact model + narrow year + mileage in onset band
    MEDIUM = "medium"    # family/make match or broad year
    LOW = "low"          # make-only or weak signal

class FailurePrediction(BaseModel):
    issue_id: int
    issue_title: str
    severity: str
    make: str | None
    model: str | None
    year_range: tuple[int | None, int | None]
    typical_onset_miles: int | None
    typical_onset_years: int | None
    miles_to_onset: int | None        # negative = past onset
    years_to_onset: float | None
    confidence: PredictionConfidence
    confidence_score: float           # 0.0-1.0
    preventive_action: str
    parts_cost_cents: int | None
    verified_by: str | None           # "forum"/"service_manual"/null
    match_tier: str                   # "exact_model"/"family"/"make"/"generic"
```

### 3. `predict_failures()` flow

Signature: `predict_failures(vehicle: dict, horizon_days: int | None = 180, min_severity: str | None = None, db_path: str | None = None) -> list[FailurePrediction]`

1. **Candidate retrieval:** `search_known_issues(make, model, year)` → then `search_known_issues(make, year)` (model=None) → dedupe by id.
2. **Age derivation:** `age_years = current_year - vehicle["year"]`.
3. **Match tier + score:**
   - `exact_model` (1.0): issue.model == vehicle.model case-insensitive.
   - `family` (0.75): issue.model is null AND make matches AND year in range.
   - `make` (0.5): issue.model null, make matches, year out of range.
   - `generic` (0.3): otherwise.
4. **Year-range tightness:** narrower range → `+ min(0.2, (30 - width) / 150)` clamped.
5. **Mileage scoring** (if `vehicle.get("mileage")`): onset_miles heuristic by severity (critical=15k, high=30k, medium=50k, low=80k). `current >= onset * 0.8` → `+0.1`; `current >= onset` → `+0.2`.
6. **Age gap scoring:** onset_years heuristic (critical=3, high=5, medium=8, low=12) with same ±0.1/0.2 bonus logic.
7. **Confidence enum:** `>=0.75` HIGH, `>=0.5` MEDIUM, else LOW.
8. **Horizon filter:** drop predictions where `years_to_onset > horizon_days/365`.
9. **Severity filter:** if `min_severity` set, drop rows below.
10. **Sort:** severity_weight DESC → miles_to_onset_urgency → confidence_score DESC. Tiebreak issue_id.
11. **Return** max 50 `FailurePrediction` models.

### 4. `preventive_action` extraction (heuristic)

- Split on "Forum tip:" — use what follows (actionable).
- Else split on first numbered step ("1.") — use preamble or step 1.
- Else first 200 chars of `description`.
- Trim whitespace; collapse double-spaces.

### 5. `verified_by` substring heuristic

Scan `description + fix_procedure`:
- "forum consensus" / "forum tip" / "reddit" / "forum-level" → `verified_by = "forum"`.
- "service manual" / "OEM procedure" / "TSB" → `verified_by = "service_manual"`.
- Else `None`.

Honors user-memory priority — forum provenance surfaced as footer note in Rich Table + `--json` field. NOT a filter in Phase 148; Phase 149 adds `--only-verified`.

### 6. Vehicle mileage — no `vehicles.mileage` column

`--current-miles N` CLI flag: required in direct-args mode, optional in `--bike` mode (absent → age-only scoring). Persistence deferred to Phase 149+ or roadmap phase 152 (service history).

### 7. CLI command

Mutex: `--bike` XOR `(--make + --model + --year + --current-miles)`. Red panel on conflict.

`--bike` path: `_resolve_bike_slug(bike)` (imported from `cli.diagnose`). Unknown → Phase 125-style remediation. `--current-miles` if given merges into `vehicle["mileage"]`.

Direct-args path: synthesizes vehicle dict `{make, model: model_name, year, mileage: current_miles}`. Requires all four.

Empty predictions → yellow "No predicted failures within horizon" panel + hint.

### 8. Rich Table

Columns: Issue (45 chars) | Typical onset (mi/yr) | Gap to onset (red if past) | Confidence (color) | Preventive action (60 chars) | Parts $ (`—` in Phase 148) | Severity (color via theme).

Footer: total / bike label / mileage / horizon + "X of Y predictions verified by forum sources" (from `verified_by == "forum"`) + hint to `kb search` or `--json`.

### 9. `cli/main.py` registration

```python
from motodiag.cli.advanced import register_advanced
# ... after register_hardware(cli):
register_advanced(cli)
# register_completion(cli) stays last
```

## Key Concepts

- **Promotion pattern.** `advanced/__init__.py` scaffold → real package (mirrors Phase 134 hardware activation).
- **CLI group lifecycle.** New top-level `advanced` group; Phases 149-159 append subcommands to same group via `register_advanced` idempotency (actually Click @cli.group raises on re-register — later phases `advanced_group.command` on the returned group).
- **Heuristic prediction over schema extension.** Ships working prediction today; Phase 149 upgrades without API churn.
- **Two-mode CLI** reuses Phase 140 `hardware scan --bike | --make` grammar.
- **Rich Table + `--json`** dual output (Phase 124+ standard).
- **Forum provenance footer, not filter** — surfaces user-memory priority without hiding service-manual predictions.
- **Zero AI, zero migration** — pure SW + SQL; trivial to review, cannot corrupt DB, zero $.
- **Match tier as provenance** — `match_tier` on every prediction informs mechanic trust decisions.
- **Horizon filter** — `--horizon-days 180` biases toward "next service interval"; widen for pre-purchase inspection.

## Verification Checklist

- [x] `advanced/__init__.py` exports FailurePrediction, PredictionConfidence, predict_failures.
- [x] `implementation.md` flips `advanced` Scaffold → Active.
- [x] Pydantic round-trip stable (enum serialization `mode="json"`).
- [x] `predict_failures(vehicle)` with `mileage=None` returns age-only predictions without crash.
- [x] Dedupes across model-specific + make-wide queries.
- [x] Match tier ordering reflected in confidence_score.
- [x] `horizon_days` filter drops predictions beyond horizon.
- [x] `min_severity` filter drops lower severities.
- [x] `preventive_action` extraction picks "Forum tip:" when present.
- [x] `verified_by = "forum"` flagged on stator + TC88 + CCT + KLR canonical rows.
- [x] `motodiag advanced predict --bike ...` returns ≥1 prediction against seed data.
- [x] Direct args path works without garage entry.
- [x] `--bike` + `--make` → red error + exit 1.
- [x] Unknown bike → Phase 125 remediation.
- [x] Empty predictions → yellow panel with widen-horizon hint.
- [x] `--json` round-trips through `model_validate`.
- [x] `--horizon-days 0` → Click validation error.
- [x] `register_advanced` placed correctly in `cli/main.py`.
- [x] Phase 140 + Phase 12 Gate 1 + Phase 08 regressions still pass.
- [x] Zero live AI tokens, zero migration.

## Risks

- **No `vehicles.mileage` column** — `--current-miles` flag. Age-only fallback when absent. Phase 149 adds persistence.
- **Heuristic severity-to-mileage onset rough.** Calibrated against TC88/CCT/KLR; Phase 149 replaces with real data.
- **Seed data coverage varies.** Harley 10+/model; Japanese 3-10; European less. Content-completeness issue, not a bug.
- **Migration 018 sequencing** — if ever needed, takes next after 142's 016 and 145's 017. Mitigated by NOT introducing migration in Phase 148.
- **`_resolve_bike_slug` cross-module import** — same pattern as Phase 140.
- **Rich Table 7-col width** — borderline at 80 cols. Truncation on Issue/Preventive action. `--json` available for programmatic use.
- **Prediction accuracy ≤ seed data quality.** `verified_by` heuristic surfaces this.
- **`advanced` package inventory churn** — flip Scaffold → Active in implementation.md Phase History + ROADMAP Track F row.
