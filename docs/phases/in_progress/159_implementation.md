# MotoDiag Phase 159 — Gate 7: Advanced Diagnostics Integration Test

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

**GATE 7 — Track F closure.** Integration test proving the full advanced-diagnostics stack (phases 148-158) works end-to-end: predict → wear analyze → fleet status → schedule → history → parts → TSB → recall → compare → baseline → drift. Single new test file, zero production code. Pattern mirrors Phase 133 Gate 5 + Phase 147 Gate 6.

CLI: `python -m pytest tests/test_phase159_gate_7.py -v`.

Outputs:
- `tests/test_phase159_gate_7.py` (~500 LoC, 7-10 tests across 3 classes). Zero production code changed.
- Zero schema changes; current schema at end of Track F (v20 after 148 → v24 after 157 → v24 after 158 which adds no migration).

## Logic

### Class A — `TestAdvancedEndToEnd` (1 big workflow, ~250 LoC)

`test_full_advanced_flow`: shared DB + CliRunner + defensive mocks (3 AI boundaries defensively patched). `time.sleep` no-op on `advanced.*`, `hardware.*`. Graceful-skip each sub-step via `importlib.util.find_spec` probes.

Workflow (graceful-skip guarded):
1. `garage add 2015 Harley Road Glide` + `garage update --mileage 35000` (Phase 152).
2. `advanced predict --bike ... --horizon-days 180` (Phase 148; assert predictions include `applicable_tsbs` / `applicable_recalls` fields when 154/155 available; `parts_cost_cents` populated when 153 seeded).
3. `advanced wear --bike ... --symptoms "tick of death,dim headlight"` (Phase 149) → assert ≥1 match.
4. `advanced fleet create test-fleet` + `advanced fleet add-bike test-fleet --bike ...` + `advanced fleet status test-fleet` (Phase 150).
5. `advanced schedule init --bike ...` + `advanced schedule due --bike ...` + `advanced schedule complete --bike ... --item oil-change --at-miles 35000` (Phase 151).
6. `advanced history add --bike ... --type oil-change --at-miles 35000 --cost-cents 5000` + `advanced history list --bike ...` (Phase 152).
7. `advanced parts seed --yes` + `advanced parts search "cam tensioner"` + `advanced parts xref HD-26499-08` (Phase 153).
8. `advanced tsb list --bike ...` + `advanced tsb search "stator"` (Phase 154).
9. `advanced recall list --make harley` + `advanced recall check-vin <valid-VIN>` + `advanced recall mark-resolved --bike ... --recall-id <id>` (Phase 155).
10. Seed peer recordings for 2015 Road Glide × 5. `advanced compare bike --bike ... --pid 0x05` → non-empty peer_stats (Phase 156).
11. `advanced baseline flag-healthy --recording-id <id> --yes` + `advanced baseline show --make harley --model "Road Glide" --year 2015` (Phase 157).
12. Seed 6 monthly recordings with drifting coolant. `advanced drift bike --bike ... --pid 0x05` → detects drifting-fast (Phase 158).
13. Re-run `advanced predict --bike ...` → assert `confidence_score` includes drift bonus when drifting-fast PID overlaps issue symptom.

Final integrity asserts:
- Schema version >= 20 baseline; tiered up to 24 based on merged phases.
- Exactly 1 vehicle, 1 fleet, 1 schedule item completed, 1 history entry, 1 recording flagged as healthy, 1 recall resolution (when 155 merged).
- CSV export from `drift plot --format csv` writes >0 bytes.

### Class B — `TestAdvancedSurface` (~4 tests)

1. `test_advanced_group_registered` — `cli.commands['advanced']`; subcommands present (hard: `predict`; soft: wear, fleet, schedule, history, parts, tsb, recall, compare, baseline, drift).
2. `test_expected_subcommands_per_subgroup` — `fleet: {create,list,show,add-bike,remove-bike,rename,delete,status}`; `schedule: {init,list,due,overdue,complete,history}`; `history: {add,list,show,show-all,by-type}`; `parts: {search,xref,show,seed}`; `tsb: {list,search,show,by-make}`; `recall: {list,check-vin,lookup,mark-resolved}`; `compare: {bike,recording,fleet}`; `baseline: {show,flag-healthy,rebuild,list}`; `drift: {bike,show,recording,plot}`.
3. `test_advanced_help_exits_zero` — `motodiag advanced --help` + each subgroup `--help`.
4. `test_all_advanced_submodules_import_cleanly` — hard: `predictor`, `models`; soft-skip-with-diagnostic: `wear`, `fleet_repo`, `fleet_analytics`, `schedule_repo`, `scheduler`, `history_repo`, `parts_repo`, `parts_loader`, `tsb_repo`, `recall_repo`, `comparative`, `baseline`, `drift`.

### Class C — `TestRegression` (~3 tests)

1. `test_phase147_gate_6_still_passes` — subprocess-pytest re-run of Gate 6 (Track E closure).
2. `test_phase133_gate_5_still_passes` — subprocess-pytest re-run of Gate 5.
3. `test_schema_version_tiered` — baseline `>= 20`; aspirational `>= 24`; actual depends on merged phases.

## Key Concepts

- **Gate 7 is a checkpoint, not a feature.** Same contract as Gates R/5/6. Zero production code. One test file.
- **Graceful-skip across all Track F phases.** Each sub-step guarded by `importlib.util.find_spec` or `advanced_group.commands` check. Missing phase → `skipped_substeps.append(...)`, outer test continues.
- **End-to-end state flows across steps.** Garage add → predict → wear → fleet → schedule → history → parts → TSB → recall → compare → baseline → drift. State from each step feeds the next.
- **Three defensive AI mocks** (Phase 147 pattern) + time.sleep no-ops on `advanced.*` / `hardware.*`.
- **Tiered schema floor** 20/21/22/23/24 depending on which Phase 149-157 migrations landed.
- **Zero new CLI commands.** Pure observation over Phase 148-158 surface.
- **Textual dashboard NOT driven** from CliRunner (same as Gate 6). Only verified registered.

## Verification Checklist

- [ ] `tests/test_phase159_gate_7.py` created with 3 classes.
- [ ] Class A: big end-to-end workflow (13 steps) on shared DB with graceful-skip.
- [ ] Class A: 3 AI mocks + time.sleep no-ops.
- [ ] Class A: final integrity asserts (1 vehicle, schema tier, CSV export).
- [ ] Class B: 4 surface tests verify advanced group + all subgroup children.
- [ ] Class C: subprocess Gate 5 + Gate 6 re-runs + schema tier floor.
- [ ] 7-10 tests total.
- [ ] Zero live tokens, zero real serial, zero production code changed.
- [ ] All Phase 148-158 regressions green.

## Risks

- **Phases 149-158 not all merged at Gate 7 build time.** Graceful-skip posture. Every sub-step gated by find_spec / command probe.
- **Migration numbering dependent on prior phases.** Tiered floor handles any subset.
- **Phase 150 `--cohort fleet` in compare** requires `fleet_memberships` table; skipped if absent.
- **Phase 155 NHTSA ID lookup** requires actual campaign data from recalls.json — seed sufficient.
- **Cross-phase coupling** (drift bonus in predict; TSB/recall in predict; parts cost in predict) all additive + default-factory=[] / None; non-breaking.
- **Subprocess Gate 5 + Gate 6 re-runs** double test runtime ~20s. Acceptable — explicit closure claim.
