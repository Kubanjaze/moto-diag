# MotoDiag Phase 147 — Gate 6: Hardware Integration Test

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Gate 6 is the integration checkpoint that closes **Track E** (hardware interface, phases 134-147). Proves the full mechanic-at-a-bench hardware workflow works end-to-end across every Track E command — from `hardware info` through live streaming, recording, replay, export, dashboard (registration only), compat DB, diagnose troubleshooter, and retry/recover — wired together on one shared DB fixture via Click's `CliRunner`. Pattern mirrors Phase 133's Gate 5: **one big integration test file with 7-10 consolidated tests**, zero new production code, pure observation over the Phase 140-146 CLI surface.

CLI: `python -m pytest tests/test_phase147_gate_6.py -v` — **test-only phase.** No new CLI commands, no new modules, no migrations.

Outputs:
- `tests/test_phase147_gate_6.py` — ONE new test file, 7-10 tests across 3 classes.
- Zero production code (`git diff src/motodiag/` empty).
- Zero schema changes. Tiered floor `>= 15` with preferred `>= 17` when Phase 145 lands.

## Logic

### Class A — `TestHardwareEndToEnd` (1 big workflow test, ~220 LoC)

Single test `test_full_hardware_flow` on shared `CliRunner`-driven DB fixture. Defensive mocks: `_default_diagnose_fn`, `_default_interpret_fn`, `_default_vision_call` all patched closed even though the hardware workflow doesn't intentionally call AI. `time.sleep` no-op patches on `cli.hardware._time`, `hardware.connection.time`, `hardware.simulator.time`.

**Workflow (12-13 CLI invocations, each with graceful-skip probe):**

1. `garage add --make Harley-Davidson --model "Road Glide" --year 2015 --vin 1HD1KHM19FB123456 --protocol can --powertrain ice` — capture vehicle ID + slug.
2. **(Phase 145)** `compat seed --yes` → `compat recommend --bike 2015-harley-road-glide`.
3. **(Phase 140+144)** `hardware info --simulator healthy_idle` — VIN + protocol badge visible.
4. **(Phase 140+144)** `hardware scan --simulator overheat` — tolerant assertion (either DTC row or "no codes" friendly message).
5. **(Phase 142+144)** `hardware log start --simulator misfire --duration 5` — capture recording_id via stdout regex.
6. **(Phase 142)** `hardware log list` — captured ID appears in table.
7. **(Phase 142)** `hardware log show <id>` — protocol name + sample_count > 0.
8. **(Phase 142)** `hardware log replay <id> --speed 0` — instant dump.
9. **(Phase 142)** `hardware log export <id> --format csv --output <tmp>/rec.csv` — file exists, >0 bytes, header row present.
10. **(Phase 141+144)** `hardware stream --simulator charging_fault --duration 2 --hz 2` — Rich table column headers visible.
11. **(Phase 146)** `hardware diagnose --port COM3 --mock` — 5-step troubleshooter, `"5/5 checks passed"` or equivalent summary.
12. **(Phase 140)** `hardware clear --simulator healthy_idle --yes` (fallback `--mock --yes` if Phase 144 absent).

**Final integrity asserts:**
- Schema version tiered: `>= 15` baseline, `>= 16` if Phase 142 merged, `>= 17` if Phase 145 merged.
- Exactly 1 vehicle row.
- 1 recording row with `sample_count > 0` and `stopped_at IS NOT NULL` (if Phase 142 present).
- CSV export file persisted >0 bytes.

**Graceful-skip posture:** Each sub-step wrapped in `importlib.util.find_spec` or `hardware_group.commands` probe. Missing phase → `pytest.skip` for that one sub-step; outer test still runs every other assertion.

### Class B — `TestHardwareSurface` (~4 tests, fast, no DB)

1. `test_hardware_group_registered` — hard-require `{scan, clear, info}`; soft-expect `{stream, log, dashboard, simulate, compat, diagnose}` (per-subcommand sub-assertions for precise failures).
2. `test_expected_subcommands_per_subgroup` — `log` children (`{start, stop, list, show, replay, diff, export, prune}`, tolerant ≥ 6/8); `simulate` (`{list, run, validate}`); `compat` (`{list, recommend, check, show, note, seed}` with nested `note add`/`note list`).
3. `test_hardware_help_exits_zero` — `motodiag hardware --help` exits 0 with scan/info/clear visible.
4. `test_all_hardware_submodules_import_cleanly` — hard-require `connection`, `mock`, `ecu_detect`; soft-skip-with-diagnostic `recorder`, `sensors`, `simulator`, `dashboard`, `compat_repo`.

### Class C — `TestRegression` (2-3 tests)

1. `test_phase133_gate_5_mechanic_flow_still_passes` — subprocess-pytest re-run of Gate 5's workflow test.
2. `test_phase121_gate_r_still_passes` — subprocess-pytest re-run of Gate R.
3. `test_schema_version_tiered` — tiered floor assertion.

### Fixture

```python
@pytest.fixture
def gate6_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "phase147.db")
    monkeypatch.setenv("MOTODIAG_DB_PATH", db_path)
    reset_settings()
    init_db(db_path)
    import motodiag.cli.hardware as _hw_cli
    monkeypatch.setattr(_hw_cli, "init_db", lambda: init_db(db_path))
    # Also patch RecordingManager default recordings_dir to tmp_path/recordings
    yield db_path
    reset_settings()
```

## Key Concepts

- **Gate 6 is a checkpoint, not a feature.** Same contract as Gates R and 5: no new code, no new packages, no migrations. One test file integrating the whole Track E CLI.
- **One cohesive scenario, not 12 disconnected tests.** State flows across steps — siloed tests wouldn't catch record-then-replay-then-export bugs.
- **Graceful-skip, not hard-fail** for non-landed phases. Phases 141-146 land in parallel; Gate 6 probes what's present.
- **CliRunner over subprocess.** 10-100× faster. Subprocess reserved for Gate R + Gate 5 regression re-run.
- **Three defensive AI mocks.** Patch even though hardware workflow doesn't call AI — guards against any Phase 146 `diagnose` accidentally wiring to Track D AI.
- **`--simulator` primary, `--mock` fallback.** Phase 144 scenarios canonical; Phase 140 mock fallback. Never mix both (mutex per Phase 144).
- **No real serial, no pyserial.Serial() instance.** Every sub-step uses `--mock` or `--simulator` or `adapter_override`.
- **Tiered schema floor.** `>= 15` baseline, aspirational `>= 17` when 145 lands.
- **Import canary for hardware submodules.** Module-level side effects, circular imports, broken lazy optional-deps → surface immediately in Class B.
- **Textual is optional, not a Gate 6 dep.** Dashboard subcommand verified REGISTERED; not driven from CliRunner (async TUI blocks).

## Verification Checklist

- [x] `tests/test_phase147_gate_6.py` created with exactly 3 classes.
- [x] Class A drives 12-13 CLI invocations on one shared DB fixture.
- [x] Class A: 3 AI mocks + 3 time.sleep no-op patches active.
- [x] Each sub-step gracefully skips if its phase absent.
- [x] CSV export file persisted, header row present, >0 bytes.
- [x] Final asserts: tiered schema, 1 vehicle, 1 recording (if 142), CSV on disk.
- [x] Class B: 4 surface tests pass.
- [x] Class C: Gate 5 + Gate R subprocess-pytest re-runs pass.
- [x] 7-10 tests total (matches Gate 5 consolidation).
- [x] Zero live tokens, zero real serial, zero production code changed.

## Risks

- **Phases 141-146 not all merged at Gate 6 build time.** Gate 6 graceful-skip posture. Every soft sub-step probes via `find_spec` / command registration.
- **Phase 144 `--simulator` + `--mock` mutex.** Workflow picks ONE flag per sub-step. Fall-back logic documented.
- **Phase 141 stream + Phase 142 log `--duration N`** burn wall-clock without patches. `time.sleep` no-op patches on all three locations.
- **Phase 143 Textual can't run in CliRunner.** Dashboard only verified registered, not driven.
- **Subprocess Gate R + Gate 5 re-run doubles runtime ~10s.** Acceptable — explicit closure claim.
- **Schema drift 142/145 independent.** Tiered floor handles every combination.
- **`MOTODIAG_DB_PATH` not honored by RecordingManager default recordings_dir.** Fixture also monkeypatches recordings_dir to tmp_path.
- **Rich Live ANSI noise in CliRunner captures.** Assert on stable markers only (PID hex, column headers, `"Polled"`/`"Hz"`).
- **Gate 5 / Gate R regression must stay green.** If either fails, stop — don't skip.
