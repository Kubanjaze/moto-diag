# MotoDiag Phase 146 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-18 | **Completed:** 2026-04-18
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 11:30 — Plan written, v1.0

Planner-146 drafted v1.0 for Phase 146 — connection troubleshooting + recovery. Second-to-last Track E phase before Gate 6. Turns Phase 140's bare HardwareSession lifecycle into a production-grade resilience substrate and adds a mechanic-facing `motodiag hardware diagnose` troubleshooter.

**Scope:**
- Library resilience across three layers:
  1. `RetryPolicy` Pydantic model + retry-loop integration in `HardwareSession.__enter__` (transient connect failures).
  2. `ResilientAdapter` decorator wrapping ProtocolAdapter to retry transient wire-op failures. `UnsupportedCommandError` + `NoECUDetectedError` never retried. `clear_dtcs` never retried even when wrapped (destructive-op protection).
  3. `auto_reconnect=True` session kwarg + `try_reconnect()` helper for long-running streams/recordings.
- `motodiag hardware diagnose` five-step interactive troubleshooter:
  1. Open serial port? (SerialException → OS remediation; short-circuit)
  2. ATZ response? (silence → power/pin16/BT guidance, WARN not FAIL)
  3. Negotiate protocol? (AutoDetector verbose + callback; on fail, Phase 145 compat hints if --bike)
  4. Read VIN? (WARN for pre-2008 Mode 09 limit — "frame neck sticker")
  5. Full-stack DTC scan.
  Rendered as numbered Rich panels with OK/WARN/FAIL icons. Summary lists failed steps + remediation pointers.
- Extend `AutoDetector` with `verbose: bool = False` + `on_attempt: Optional[Callable] = None` kwargs. Backward-compat — defaults preserve Phase 139.
- Extend `MockAdapter` with `flaky_rate: float = 0.0` + `flaky_seed: Optional[int] = None` kwargs. Backward-compat — `flaky_rate=0.0` short-circuits every roll.
- CLI: `--retry`/`--no-retry` on scan (default on), info (default on), clear (**default off**). `--auto-reconnect`/`--no-auto-reconnect` on stream (default on, conditional on Phase 141 merge).
- No migration. No new DB tables. No AI. No new pyproject deps.
- ~50 tests across 7 classes.

**Design non-negotiables:**
1. Library-level ops keep raw-failure semantics. `HardwareSession(port)` without retry kwargs is byte-identical to Phase 140. Zero drift.
2. Default-on for safe ops, default-off for destructive. `clear` never silently retries.
3. Every retry observable. INFO logs per attempt + summary. `scan`/`info` surface retry count in footer.
4. Diagnose output mechanic-readable. No tracebacks ever leak. Plain-English remediation with shop-floor vocabulary.
5. Deterministic tests. `time.sleep` patched. `random.Random(seed=42)` pinned.
6. Phase 140 backward-compat load-bearing. All new kwargs optional with safe defaults.

**Explicit overlap + dependency warnings:**
- `hardware/connection.py` extended (+~180 LoC on existing 255). Additive only; Phase 140 unchanged when `retry_policy=None`.
- `hardware/ecu_detect.py` one new kwarg + one new callback kwarg. Defaults preserve Phase 139 exactly.
- `hardware/mock.py` two new kwargs. `flaky_rate=0.0` preserves Phase 140.
- `cli/hardware.py` additive `diagnose` + new flags on existing subcommands. Phase 140's 40 tests unchanged.
- Phase 145 compat DB soft dep — `diagnose` uses `from motodiag.hardware.compat import lookup_compat` if importable; graceful fallback message otherwise.
- Phase 141 stream soft dep — `--auto-reconnect` flag only registers if `"stream" in hardware_group.commands`.

**Test plan:**
- `TestRetryPolicy` (5) — defaults, backoff computation, retry_on filter, exhausted re-raise, max_delay clamp.
- `TestHardwareSessionRetry` (10) — no-retry preserves Phase 140, retry wraps adapter, 3-fails raises, 2-fail-1-success 3rd, backoff timing observed, non-retryable immediate raise, disabled default, auto_reconnect-without-policy ValueError, exception type preserved, mock-path retry works.
- `TestResilientAdapter` (12) — wraps 4 read methods, TimeoutError retried, ConnectionError mid-read retried, Unsupported NOT retried, NoECUDetected NOT retried, logs, exhausted raises last, clear_dtcs NOT retried, disconnect pass-through no retry.
- `TestAutoReconnect` (8) — single-success, 3-consecutive-fails returns False, 2nd-attempt success, requires retry_policy, respects max_attempts, uses port/baud, preserves adapter identity, logs each attempt.
- `TestMockAdapterFlaky` (4) — flaky=0 never raises, flaky=0.5 seeded deterministic + pinned count, different seeds differ, disconnect/protocol_name unaffected.
- `TestDiagnoseCommand` (15) — all 5 steps render mock, step 1 fail OS remediation + short-circuit, step 2 fail adapter-power remediation, step 3 fail AutoDetector breakdown, step 3 with --bike compat DB hits (skippable), step 4 VIN-None/VIN-unsupported WARN, step 5 fail DTC-scan remediation, summary lists failed steps, pass/fail ratio, --verbose dumps + off hides, --help.

**Dependencies flagged:**
- Hard: Phases 134, 139, 140 (built).
- Soft: Phase 145 (compat DB — graceful ImportError fallback).
- Soft: Phase 141 (stream — conditional flag registration).

**Open questions:**
1. Parallel-planning ordering with 141-145 — plan defensively handles via feature detection. Confirm acceptable vs blocking.
2. `--auto-reconnect` default on stream — up to 15s of retries. Some mechanics prefer fail fast. Plan: on per spec, flagged risk.
3. `clear --retry` opt-in — mechanic who wants retry-on-Mode-04 could hit duplicated-clear if first silently succeeded. Plan: opt-in, documented risk.
4. `time.sleep` at `motodiag.hardware.connection.time.sleep` — tests patch one location covering session + ResilientAdapter.
5. Flaky-mock pinned count — Builder computes empirically at build time on target Python version.
6. `diagnose` persistence — ephemeral console-only. Phase 147 Gate 6 may reconsider.

**Next:** build — recommend agent-delegated Builder-A. Architect trust-but-verify on completion. Phase 147 (Gate 6) natural consumer — integration test exercises both bare and resilient HardwareSession paths end-to-end.

### 2026-04-18 16:15 — Build complete (Builder-146 + Architect trust-but-verify)

Fifteenth agent-delegated phase. Builder-146 shipped three-layer resilience:
- `hardware/connection.py` +446 LoC — RetryPolicy Pydantic model + ResilientAdapter wrapper + HardwareSession `retry_policy`/`auto_reconnect` kwargs + `try_reconnect()` method + `_enter_once()` refactor.
- `hardware/ecu_detect.py` +62 LoC — `verbose=False` + `on_attempt=None` kwargs AFTER `compat_repo` (Phase 145 kwarg ordering preserved).
- `hardware/mock.py` +91 LoC — `flaky_rate=0.0` + `flaky_seed=None` additive kwargs + `_roll_flaky()` helper. `flaky_rate=0.0` short-circuits → Phase 140 behavior byte-preserved.
- `cli/hardware.py` +1089 LoC — `--retry/--no-retry` on scan (default on), info (default on), clear (default off). New `diagnose` subcommand with 5-step troubleshooter (port open / ATZ probe / AutoDetector negotiation / VIN read / DTC scan) + Rich panels with mechanic-readable remediation.
- `tests/test_phase146_recovery.py` new 941 LoC, 56 tests across 7 classes.

Sandbox blocked Python for Builder. Architect ran trust-but-verify.

### 2026-04-18 16:20 — Bug fix #1: MockAdapter missing import in diagnose command

**Issue:** 9 tests in TestDiagnoseCommand failed with `NameError: name 'MockAdapter' is not defined`. `_diagnose_step3_protocol` referenced MockAdapter in the `--mock` branch but never imported it.

**Root cause:** `cli/hardware.py` module-level imports didn't include `MockAdapter`. Other subcommands instantiate it via `HardwareSession(mock=True)` which imports internally; diagnose constructs it directly.

**Fix:** Added lazy import `from motodiag.hardware.mock import MockAdapter` inside the `if mock:` branch of `_diagnose_step3_protocol`. Avoids pulling mock into module-level imports.

**Files:** `src/motodiag/cli/hardware.py` line 3266 area.

**Verified:** `pytest tests/test_phase146_recovery.py -q` → 56 passed in 16.80s.

### 2026-04-18 16:25 — Bug fix #2: `--retry`/`--simulator` mutex too strict

**Issue:** Phase 144's `test_scan_with_simulator_prints_sim_badge` regressed. Test invoked `scan --port X --simulator healthy_idle` (no explicit `--retry`); Click exited 2 with UsageError "—retry and --simulator are incompatible".

**Root cause:** Builder-146 added a hard mutex `if simulator and retry: raise UsageError(...)`, but `--retry` defaults to True on scan/info — so users passing ONLY `--simulator` tripped the mutex silently-by-default-value. Click doesn't expose "was this explicitly set" without sentinel defaults.

**Fix:** Replaced the 3 raise-UsageError blocks (in scan/clear/info command bodies) with silent retry-disable: `if simulator and retry: retry = False`. Simulator has no transient failure modes — retry-wrapping is a no-op in that path, so silent skip is the correct semantic. One-line automation via regex sub across all 3 sites.

**Files:** `src/motodiag/cli/hardware.py` lines ~1022, ~1148, ~1265 (3 blocks).

**Verified:** `pytest tests/test_phase144_simulator.py tests/test_phase146_recovery.py -q` → 137 passed in 41.44s.

**Build-complete sign-off:** Phase 146 GREEN. 56/56 own tests + 81/81 Phase 144 regression clean + 351/352 broader regression clean (then 352/352 after fix #2). Three-layer resilience substrate complete.
