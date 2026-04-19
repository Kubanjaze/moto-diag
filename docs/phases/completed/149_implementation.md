# MotoDiag Phase 149 — Wear Pattern Analysis

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-19

## Goal

Second Track F phase. Distinct from Phase 148 (mileage/age forecasting): Phase 149 answers "mechanic reports observed symptoms → rank which worn components best match". Output: ranked `WearMatch` list with confidence, matched/unmatched symptom breakdown, inspection checklist, forum citation.

CLI (appended to Phase 148's `advanced` Click group):
- `motodiag advanced wear --bike SLUG --symptoms "knocking,dim headlight,rough idle" [--min-confidence 0.5] [--json]`
- `motodiag advanced wear --make MAKE --model MODEL --year YEAR --symptoms "..." [--min-confidence 0.5] [--json]`

No AI, no migration, zero tokens. File-based seed.

Outputs:
- `src/motodiag/advanced/wear.py` (~250 LoC) — `WearPattern` + `WearMatch` Pydantic v2 models + `analyze_wear()` + `_load_wear_patterns()` lru-cached.
- `src/motodiag/advanced/wear_patterns.json` (~30 real mechanic-vocabulary entries, curated with forum citations).
- `src/motodiag/advanced/__init__.py` +3 LoC exports.
- `cli/advanced.py` +~150 LoC — `wear_cmd` appended inside existing `register_advanced`.
- `tests/test_phase149_wear.py` (~30 tests, 4 classes).

## Logic

### wear_patterns.json schema

```json
{
  "id": "tc88-cam-tensioner",
  "component": "cam chain tensioner",
  "make": "harley",
  "model_pattern": "%",
  "year_min": 1999, "year_max": 2006,
  "symptoms": ["tick of death", "valvetrain noise at 2000 rpm", "metallic grinding"],
  "inspection_steps": [
    "Pull primary cover, inspect both front + rear CCT shoes for cracks/missing chunks",
    "Use feeler gauge on cam chain slack — spec is 0.030 max over stock",
    "Check oil galley for metal fragments on magnetic drain plug"
  ],
  "confidence_hint": 0.9,
  "verified_by": "hdforums consensus + service manual 99500-00"
}
```

**Required 5 anchor entries** (Builder fleshes to 30 total):
1. `tc88-cam-tensioner` — Harley 1999-2006 tick of death.
2. `sportster-stator-undercharge` — Harley 2004-2021 dim headlight + charging voltage < 13.5V.
3. `chain-stretch-sprocket` — all makes (null make), chain slap + hooked sprocket.
4. `fork-seal-leak-upper` — all makes, oil film + clunk over bumps.
5. `wheel-bearing-whine-rear` — all makes, speed-proportional whine.

Additional 25: KLR doohickey, CBR600RR CCT, clutch basket judder, steering head notchy, HD compensator, primary chain tensioner, intake air leak, R/R overcharge, brake rotor warp, injector clog, TB sync drift, starter clutch slip, shift fork wear, flat-tappet cam lobe, valve lash tight, ring blowby, crank seal weep, header crack, clutch cable stretch, grip weight wear, swingarm bearing slop, countershaft seal leak, final drive splines, turn signal relay click-death, coolant weep at water pump.

### Pydantic models

```python
class WearPattern(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    component: str
    make: Optional[str]
    model_pattern: str
    year_min: Optional[int]
    year_max: Optional[int]
    symptoms: tuple[str, ...]
    inspection_steps: tuple[str, ...]
    confidence_hint: float = Field(ge=0.0, le=1.0)
    verified_by: str

class WearMatch(BaseModel):
    model_config = ConfigDict(frozen=True)
    pattern_id: str
    component: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    symptoms_matched: tuple[str, ...]
    symptoms_unmatched: tuple[str, ...]
    bike_match_tier: str   # "exact" | "family" | "make" | "generic"
    inspection_steps: tuple[str, ...]
    verified_by: str
```

### analyze_wear() flow

`analyze_wear(vehicle: dict, symptoms: list[str] | str, min_confidence: float = 0.5, db_path: str | None = None, patterns_path: str | None = None) -> list[WearMatch]`

1. **Tokenize symptoms** — split on `,` or `;`, lowercase + strip + dedupe preserving order.
2. **Load patterns** via `@functools.lru_cache` on path (default `Path(__file__).parent / "wear_patterns.json"`).
3. **For each pattern, compute bike_match_tier**:
   - `exact` (bonus 1.0): make matches (CI) AND `fnmatch(model, model_pattern.replace("%","*"))` matches AND year in `[year_min, year_max]`.
   - `family` (bonus 0.7): make + model match, year out of range.
   - `make` (bonus 0.4): make matches only.
   - `generic` (bonus 0.3): pattern.make is None.
   - **DROP** pattern if make is set AND mismatched (Kawasaki pattern must never score against Sportster).
4. **Overlap scoring**: `matched = [s for s in pattern.symptoms if any(u in s or s in u for u in user_symptoms)]` (substring-either-direction). `overlap = len(matched)/len(pattern.symptoms)`. `raw = overlap*0.7 + bike_bonus*0.3`. Floor by `overlap * confidence_hint`. Clamp [0,1].
5. **Skip** patterns with `overlap == 0`.
6. **Filter** by `min_confidence`.
7. **Sort** `confidence DESC → matched_count DESC → pattern_id ASC`.

### CLI `wear` subcommand

Appended inside `register_advanced` (no new `register_*` function — Phase 148 owns the group):
```python
@advanced_group.command("wear")
@click.option("--bike", default=None)
@click.option("--make", default=None)
@click.option("--model", "model_name", default=None)
@click.option("--year", type=int, default=None)
@click.option("--symptoms", required=True)
@click.option("--min-confidence", type=float, default=0.5, show_default=True)
@click.option("--json", "json_output", is_flag=True, default=False)
def wear_cmd(bike, make, model_name, year, symptoms, min_confidence, json_output): ...
```

Mutex: `--bike` XOR `--make`+`--model`+`--year`. Validate `0.0 <= min_confidence <= 1.0`. Unknown bike → reuse Phase 148's `_render_bike_not_found`. Rich Table: Component / Confidence (color via `_format_confidence`) / Matched symptoms / Unmatched (dim) / Inspection steps (55-char fold) / Verified by (dim). Empty → yellow panel with vocabulary hint. `--json` standard Phase 131 pattern (mode="json").

### __init__.py update
```python
from motodiag.advanced.models import FailurePrediction, PredictionConfidence
from motodiag.advanced.predictor import predict_failures
from motodiag.advanced.wear import WearPattern, WearMatch, analyze_wear
__all__ = ["FailurePrediction", "PredictionConfidence", "predict_failures",
           "WearPattern", "WearMatch", "analyze_wear"]
```

## Key Concepts

- **File-seeded editorial, not DB-backed.** Wear patterns are curated content with forum citations. User-authored patterns are roadmap Phase 155+.
- **Substring-either-direction match** handles mechanic vocabulary drift ("tick of death" vs "valvetrain tick").
- **`confidence_hint` floor** keeps forum-gold patterns ranking high on partial symptom coverage.
- **Click group append, not new group.** Phase 148 owns `register_advanced`; Phase 149 adds `wear_cmd` inside it via `@advanced_group.command("wear")`.
- **Helper reuse from Phase 148**: `_render_bike_not_found`, `_format_confidence`, `_list_garage_summary`.
- **No `--current-miles`.** Symptom set is the signal.

## Verification Checklist

- [x] `wear_patterns.json` loads without error (30 entries, all fields present, all `confidence_hint ∈ [0,1]`).
- [x] `WearPattern` + `WearMatch` Pydantic round-trip via `model_validate(model_dump(mode="json"))`.
- [x] `analyze_wear(vehicle, "")` returns `[]`.
- [x] `analyze_wear(tc88_bike, "tick of death")` → `cam chain tensioner` top match, confidence ≥ 0.6.
- [x] Comma AND semicolon symptom splitting both work.
- [x] Substring-either-direction match fires on "dim headlight" vs "headlight dim".
- [x] Non-matching explicit make drops pattern (Kawasaki never scores for Sportster).
- [x] Generic patterns (make=null) score against all bikes.
- [x] `min_confidence` filter: 0.0 returns all, 1.0 only perfect.
- [x] CLI Rich table 6 columns + footer; `--json` parseable.
- [x] `--bike` + `--make` → ClickException.
- [x] `--symptoms` missing → Click required-field error.
- [x] `--min-confidence 1.5` → ClickException.
- [x] Unknown bike → Phase 125 remediation panel.
- [x] `advanced/__init__.py` exports both Phase 148 + 149 names.
- [x] Phase 148 predict + Phase 140 hardware regressions still pass.
- [x] Zero AI, zero migration, zero tokens.

## Risks

- **Seed quality drift.** 30 patterns is starter; user feedback identifies gaps; Phase 155+ adds user-authored.
- **Substring-either-direction false positives** ("tick" in "ticket"). Multi-word tokens in seed mitigate.
- **fnmatch vs SQL LIKE semantics.** `%` → `*` translation, no `_` wildcard; seed uses only `%`.
- **Click group re-entry collision.** Phase 148 owns `register_advanced`; Phase 149 appends commands inside that function. Single registration invariant.
- **Windows cmd.exe quote handling** on `--symptoms`. Help string shows exact form; tests use CliRunner (bypasses shell).
- **`confidence_hint` floor can't overrule `min_confidence` intent.** Floor only helps; partial-match + high-hint patterns still gated by default 0.5 threshold.

## Deviations from Plan

- Test count 33 vs ~30 target — extra edge-case coverage on bike_match_tier transitions and vocabulary-drift substring matching.
- Zero bug fixes needed on first pytest run.

## Results

| Metric | Value |
|--------|-------|
| Tests | 33 GREEN |
| LoC delivered | ~670 (wear.py 309 + wear_patterns.json 662 lines + cli/advanced.py +180) |
| Bug fixes | 0 |
| Commit | `68f65f4` |

Phase 149 opens the Track F advanced-diagnostics Click group for symptom-driven wear-pattern ranking, with 30 real forum-cited patterns serving as the editorial seed that subsequent phases build on. Zero-migration, zero-token wear triage is now mechanic-CLI-reachable.
