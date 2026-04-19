# MotoDiag Phase 154 — Technical Service Bulletin (TSB) Database

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Seventh Track F phase. Track OEM-issued Technical Service Bulletins — official fixes for known issues. Distinct from Phase 155 recalls (federal/safety) and Phase 08 known_issues (forum-consensus). Mechanic looks up 2012 Dyna stator issue → sees HD M-1287 official bulletin alongside forum-sourced prediction.

CLI: `motodiag advanced tsb {list, search, show, by-make}`.

No AI, no network. Migration 022 (next available).

Outputs:
- Migration 022: `technical_service_bulletins` (id / tsb_number UNIQUE / make / model_pattern SQL LIKE / year_min/max / title / description / fix_procedure / severity CHECK / issued_date ISO / source_url / verified_by / created_at) + 3 indexes (make+model_pattern, tsb_number, issued_date DESC).
- `advanced/tsb_repo.py` (~200 LoC): add_tsb (INSERT OR IGNORE on UNIQUE), get_tsb, list_tsbs, list_tsbs_for_bike (SQL LIKE + year range), search_tsbs (LIKE across title+description+fix_procedure), count_tsbs, tsb_numbers_for_vehicle (Phase 148 hook).
- `advanced/data/tsbs.json` (~40 real TSBs): 12 HD M-series, 10 Honda MC, 8 Yamaha TB, 6 Kawasaki SB, 4 KTM SB — cited with public source_urls (service.h-d.com, powersports.honda.com, forum archives).
- `cli/advanced.py` +~220 LoC: `tsb` subgroup. list/search/by-make Rich Table (TSB# | Make | Model pattern | Years | Severity | Title | Issued); `show` Rich Panel (title + description + "Official fix:" + fix_procedure + source_url footer).
- `advanced/models.py` +1 field: `FailurePrediction.applicable_tsbs: list[str] = Field(default_factory=list)`.
- `advanced/predictor.py` +~30 LoC: single TSB lookup per predict call (no N+1), keyword-overlap filter (≥1 shared token of length ≥4), severity bucket-adjacent match, graceful degradation on missing table (try/except OperationalError → empty list).
- `tests/test_phase154_tsb.py` (~30 tests, 5 classes).

## Key Concepts

- TSB ≠ recall ≠ known_issue (three independent provenance layers).
- UNIQUE tsb_number with INSERT OR IGNORE for idempotent seed.
- Seed-on-init via `init_db()` post-hook guarded by `count_tsbs()==0` (no user-facing `tsb seed` subcommand).
- Phase 148 integration additive (default_factory=list; graceful degradation).
- Single query per predict + Python-side keyword filter (no N+1).
- Zero network; Architect spot-checks 10 source_urls pre-merge.

## Verification Checklist

- [ ] Migration 022 + 3 indexes + rollback.
- [ ] UNIQUE tsb_number with INSERT OR IGNORE.
- [ ] `list_tsbs_for_bike("harley","Dyna Super Glide",2012)` matches `Dyna%` + year range.
- [ ] `search_tsbs("throttle body","harley")` hits all 3 text columns.
- [ ] Empty query → `[]`.
- [ ] Severity/date/empty-tsb_number validation ValueError.
- [ ] Case-insensitive make.
- [ ] tsbs.json ≥40 real TSBs spanning 5 OEMs.
- [ ] Loader idempotent; malformed JSON → ValueError with line:col.
- [ ] CLI 4 subcommands + `--json`.
- [ ] `FailurePrediction.applicable_tsbs` defaults `[]`; round-trip preserves.
- [ ] `predict_failures` against pre-migration-022 DB → `applicable_tsbs=[]` no crash.
- [ ] Phase 148 44 tests still pass (additive field).

## Risks

- Migration slot race; SQL body independent.
- Public TSB URL rot — mitigate with forum-archive mirror URLs where service.h-d.com requires dealer auth.
- TSB number format heterogeneity (HD "M-1234" / Honda "MC-19-123" / Yamaha "TB-YYYY-NNN") — normalize by stripping spaces at lookup.
- N+1 risk avoided (one query per predict).
- Keyword-overlap false positives — 4-char minimum + shared-token rule.
- Pydantic frozen + default_factory=list sanctioned.
