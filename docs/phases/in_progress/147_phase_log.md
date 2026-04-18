# MotoDiag Phase 147 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 12:00 — Plan written, v1.0

Gate 6 integration test — closes Track E (hardware interface, phases 134-147). Single new test file `tests/test_phase147_gate_6.py` with 7-10 consolidated tests across 3 classes. Pattern mirrors Phase 133 Gate 5 (which mirrored Phase 121 Gate R): one big end-to-end workflow test via `CliRunner` on shared DB fixture + CLI-surface breadth suite + regression re-run of Gate R + Gate 5 + tiered schema floor assertion.

**Scope:**
- **Class A** `TestHardwareEndToEnd` (1 big test): `garage add` 2015 Road Glide → `compat seed`/`recommend` (145) → `hardware info --simulator healthy_idle` → `hardware scan --simulator overheat` → `hardware log start/list/show/replay/export` round-trip (142) → `hardware stream --simulator charging_fault --duration 2 --hz 2` (141) → `hardware diagnose --port COM3 --mock` 5-step troubleshooter (146) → `hardware clear --simulator healthy_idle --yes` (140). Shared DB, three defensive AI mocks, zero live tokens, zero real serial.
- **Class B** `TestHardwareSurface` (~4 tests): group registered with 7-8 subcommands; subgroup children verified (log/simulate/compat); `hardware --help` exits 0; every `motodiag.hardware.*` submodule imports cleanly.
- **Class C** `TestRegression` (2-3 tests): Gate 5's `test_full_mechanic_flow` still passes; Gate R's `test_full_workflow` still passes; `SCHEMA_VERSION >= 15` tiered floor.

**Non-negotiables:**
- Zero new production code — pure observation over Phase 140-146 CLI surface.
- Zero schema changes.
- Zero live API tokens — defensive mocks at the 3 AI boundaries.
- Zero real serial ports — every sub-step uses `--simulator` (primary, Phase 144) or `--mock` (fallback, Phase 140).
- `time.sleep` monkey-patched on `cli.hardware._time`, `hardware.connection.time`, `hardware.simulator.time` — workflow runs in <2s wall-clock total.
- CliRunner over subprocess for workflow; subprocess reserved for Gate R + Gate 5 re-run.
- 7-10 tests total (Gate 5 consolidation pattern, NOT 20+).

**Dependencies:**
- Hard: Phase 140 (scan/clear/info, HardwareSession, MockAdapter) — shipped.
- Soft graceful-skip: Phases 141 (stream), 142 (log+migration 016), 143 (dashboard), 144 (simulator+YAMLs), 145 (compat+migration 017), 146 (retry+diagnose).

Every soft sub-step guarded by `importlib.util.find_spec` or `hardware_group.commands` probe. Missing → `pytest.skip` for just that sub-step; outer test runs everything else. When all six Track E phases merge, every probe passes and full workflow runs end-to-end.

**Gate 6 PASS criteria:** all 7-10 tests pass; zero regressions against Gate R + Gate 5; `SCHEMA_VERSION >= 15` (preferred `>= 17`); every `motodiag.hardware.*` submodule imports cleanly; no production code modified; zero live API tokens; zero real serial ports.

**Next:** Build after Phases 141-146 finalize (or while they're landing, with graceful-skip posture). Runs as the Track E closure checkpoint.
