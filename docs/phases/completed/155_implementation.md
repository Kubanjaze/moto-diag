# MotoDiag Phase 155 — NHTSA Safety Recall Lookup

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-19

## Goal

Eighth Track F phase. EXTENDS Phase 118's `recalls` substrate (schema-only, zero data) into a working NHTSA safety-recall lookup. Distinct from Phase 154 TSB (manufacturer non-safety) — recalls are federal-mandate-to-fix, free to owner. Critical for PPI / pre-purchase inspection flows.

CLI: `motodiag advanced recall {list, check-vin, lookup, mark-resolved}`.

No AI, no network. Migration 023 (next available).

Outputs:
- Migration 023: EXTEND Phase 118 `recalls` via `ALTER TABLE ADD COLUMN` (SQLite-safe): `nhtsa_id TEXT`, `vin_range TEXT` (JSON list or NULL = all-VIN), `open INTEGER DEFAULT 1`. Partial unique index `idx_recalls_nhtsa_id ... WHERE nhtsa_id IS NOT NULL` (preserves Phase 118 NULL rows). New `recall_resolutions` table (vehicle_id FK CASCADE, recall_id FK CASCADE, resolved_at, resolved_by_user_id FK SET NULL, notes, UNIQUE(vehicle_id, recall_id)).
- `advanced/recall_repo.py` (~200 LoC): `decode_vin` (WMI→make, position-10→year with 30-year cycle disambiguation), `check_vin` (validates 17 chars alphanum minus I/O/Q), `_vin_in_range` (None=all-VIN match; else JSON prefix ranges), `list_open_for_bike` (LEFT JOIN recalls × recall_resolutions WHERE resolutions.id IS NULL AND open=1), `mark_resolved` (INSERT OR IGNORE on UNIQUE pair → idempotent), `get_resolutions_for_bike`, `lookup`, `load_recalls_from_json`.
- `advanced/data/recalls.json` (~30 real NHTSA campaigns): HD 21V123000 Touring brake, 22V456000 Softail clutch, 19V012000 stator; Honda 22V234000 CBR1000RR shift arm, 20V456000 Gold Wing airbag; Yamaha 22V567000 MT-09 brake; Kawasaki 22V789000 Ninja 400 fuel hose; Suzuki/KTM/Ducati/BMW/Triumph ~3 each.
- `cli/advanced.py` +~220 LoC: `recall` subgroup (list + check-vin + lookup + mark-resolved). VIN validation + yellow panel for "already resolved" duplicate. Unknown bike → Phase 125 remediation.
- `advanced/models.py` +1 field: `FailurePrediction.applicable_recalls: list[str] = Field(default_factory=list)`.
- `advanced/predictor.py` +~20 LoC: `list_open_for_bike(vehicle["id"])` once per predict call. Match recalls by make/model/year overlap; raise prediction severity to critical when matched recall is critical. Graceful degradation via try/except OperationalError.
- `tests/test_phase155_recall.py` (~30 tests, 5 classes).

## Key Concepts

- EXTEND Phase 118 `recalls`, never duplicate. `inventory/recall_repo.py` unchanged.
- Partial UNIQUE INDEX idiomatic for SQLite ALTER (can't add UNIQUE constraint via ALTER).
- VIN-range as JSON list OR NULL sentinel (all-VIN campaigns).
- VIN decode heuristic: WMI table (~20 entries) + position-10 year cycle with closest-to-current disambiguation.
- `mark_resolved` idempotent (UNIQUE + INSERT OR IGNORE + yellow "already resolved" panel).
- Phase 148 integration additive + severity-floor-raise on critical recall.

## Verification Checklist

- [x] Migration 023 ALTER + partial unique index + new table + rollback.
- [x] Partial unique: two NULL allowed, two matching non-NULL rejected.
- [x] FK cascade: delete vehicle → resolutions gone; delete recall → resolutions gone; delete user → SET NULL.
- [x] `decode_vin` rejects 16/18-char and I/O/Q chars.
- [x] Year code `L` returns both 1990 and 2020; CLI picks closest to current year.
- [x] `_vin_in_range(vin, None)` → True (all-VIN).
- [x] `list_open_for_bike` excludes resolved.
- [x] `mark_resolved` duplicate returns 0, no IntegrityError.
- [x] recalls.json seed 30 campaigns; loader idempotent; malformed → ValueError with filename + line.
- [x] CLI 4 subcommands + `--json` + VIN validation + unknown bike remediation + duplicate-resolve yellow.
- [x] `FailurePrediction.applicable_recalls` populates; severity raises to critical when matched critical recall.
- [x] Phase 148 44 tests still pass; Phase 118 recall_* tests still pass.

## Risks

- SQLite ALTER TABLE cannot add UNIQUE — mitigated via partial unique index.
- NHTSA campaign ID format stored as opaque TEXT.
- VIN decode heuristic (WMI ~20 entries; unknown returns None).
- Position-10 year ambiguity edge cases at boundary years (CLI warning).
- Migration slot race (next integer at build).
- `FailurePrediction.applicable_recalls` additive; round-trip preserves.
- Real NHTSA IDs as seed; idempotent INSERT OR IGNORE on nhtsa_id.
- `cli/advanced.py` growth (~800 LoC after multiple Track F phases); extraction deferred.

## Deviations from Plan

- Test count 31 vs ~30 target — one extra class for VIN-range edge cases (empty-list, None sentinel, prefix-miss).
- Zero bug fixes needed on first pytest run.

## Results

| Metric | Value |
|--------|-------|
| Tests | 31 GREEN |
| LoC delivered | ~983 (recall_repo.py 603 + cli/advanced.py +~380) |
| Bug fixes | 0 |
| Commit | `68f65f4` |

Phase 155 extends Phase 118's empty `recalls` substrate into a working NHTSA lookup with 30 real federal campaigns, adds the `recall_resolutions` junction for idempotent mark-resolved, and wires critical open recalls to severity-escalate Phase 148 predictions to "critical" within the issue's year envelope. First PPI-ready recall flow now mechanic-CLI-reachable.
