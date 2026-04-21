# MotoDiag Phase 146 — Connection Troubleshooting + Recovery

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Second-to-last Track E phase before Gate 6. Turns Phase 140's lifecycle wrapper into a resilience substrate: transient failures retry with backoff, mid-session disconnects auto-reconnect, and a new `diagnose` subcommand walks mechanics through 5-step interactive troubleshooting with plain-English remediation ("power-cycle adapter, check 12V on OBD pin 16") — no raw tracebacks.

**Three layers:**
1. Retry with backoff on transient connect/read failures.
2. Auto-reconnect during long-running streams/recordings when ECU goes silent.
3. `motodiag hardware diagnose` five-step troubleshooter.

**Design stance:**
- Default-on for safe ops (scan/info/stream), default-off for destructive (clear).
- Library-level preserves Phase 140 raw-failure semantics exactly when `retry_policy=None`.
- Every retry observable (INFO log with op + attempt + reason).

No migration, no new DB tables, no AI, no new pyproject deps.

## Outputs

- `src/motodiag/hardware/connection.py` +~180 LoC: `RetryPolicy` Pydantic model, `retry_policy`/`auto_reconnect` kwargs on HardwareSession, `ResilientAdapter` wrapper, `try_reconnect()` helper.
- `src/motodiag/hardware/ecu_detect.py` +~25 LoC: `verbose: bool = False` + `on_attempt: Optional[Callable] = None` kwargs on AutoDetector.
- `src/motodiag/hardware/mock.py` +~40 LoC: `flaky_rate: float = 0.0` + `flaky_seed: Optional[int] = None` kwargs.
- `src/motodiag/cli/hardware.py` +~260 LoC: new `diagnose` subcommand + `--retry`/`--no-retry` on scan/info/clear + `--auto-reconnect`/`--no-auto-reconnect` on stream (conditional on Phase 141 merge).
- `tests/test_phase146_recovery.py` (~850 LoC, ~50 tests across 7 classes). Zero real `time.sleep`, zero live hardware, zero tokens.

## Logic

### RetryPolicy (Pydantic model)

```python
class RetryPolicy(BaseModel):
    max_attempts: int = 3
    initial_delay_s: float = 0.5
    backoff_factor: float = 2.0
    max_delay_s: float = 5.0
    retry_on: list[type[Exception]] = Field(
        default_factory=lambda: [ProtocolConnectionError, ProtocolTimeoutError]
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def delay_for_attempt(self, attempt_idx: int) -> float:
        raw = self.initial_delay_s * (self.backoff_factor ** attempt_idx)
        return min(raw, self.max_delay_s)

    def should_retry(self, exc) -> bool:
        return any(isinstance(exc, cls) for cls in self.retry_on)
```

Defaults: 0.5s → 1.0s → 2.0s → 4.0s → 5.0s clamp. Max 3 attempts = 2 sleeps = 1.5s total backoff worst case. Domain-shadowed `ConnectionError`/`TimeoutError` imported with aliases to avoid colliding with Python built-ins.

### HardwareSession retry extension

New kwargs:
```python
def __init__(self, port, ..., 
             retry_policy: Optional[RetryPolicy] = None,   # NEW
             auto_reconnect: bool = False):                # NEW
    if auto_reconnect and retry_policy is None:
        raise ValueError("auto_reconnect requires a retry_policy")
```

`__enter__` extension:
- `retry_policy=None` → Phase 140 path unchanged (byte-identical).
- `retry_policy != None` → retry loop:
  ```python
  for attempt in range(self.retry_policy.max_attempts):
      try:
          raw = self._enter_once()
      except Exception as exc:
          if not self.retry_policy.should_retry(exc):
              raise
          last_exc = exc
          logger.info("HardwareSession connect attempt %d/%d failed: %s", ...)
          if attempt + 1 < max_attempts:
              time.sleep(self.retry_policy.delay_for_attempt(attempt))
          continue
      self._adapter = ResilientAdapter(raw, self.retry_policy)
      return self._adapter
  raise last_exc
  ```

### ResilientAdapter wrapper

Transparent `ProtocolAdapter` subclass wrapping `inner: ProtocolAdapter` + `_policy: RetryPolicy`. Implements all 8 ABC methods.

Pass-through (NO retry): `connect`, `disconnect`, `get_protocol_name`, `is_connected` property. Lifecycle ops explicitly bare.

Retried via `_with_retry` helper: `send_command`, `read_dtcs`, `read_pid`, `read_vin`. Each:
```python
def _with_retry(self, op_name, fn):
    for attempt in range(max_attempts):
        try:
            return fn()
        except UnsupportedCommandError: raise   # never retry
        except NoECUDetectedError: raise        # never retry
        except Exception as exc:
            if not self._policy.should_retry(exc): raise
            logger.info("ResilientAdapter.%s attempt %d/%d failed: %s", ...)
            if attempt + 1 < max_attempts:
                time.sleep(self._policy.delay_for_attempt(attempt))
    raise last_exc
```

**`clear_dtcs` pass-through NOT retried** even when wrapped. Duplicated Mode 04 on a Harley is a mechanic-surprise hazard. CLI's `clear` defaults `--no-retry` and doesn't construct a ResilientAdapter for clear flows; this branch exists only for ABC compliance.

### Auto-reconnect

`session.try_reconnect() -> bool`:
- Returns True on reconnect success, False after `max_attempts` fail.
- Uses stored `self.port` + `self.baud`.
- Calls `self._inner_adapter.connect(port, baud or _DEFAULT_BAUD)` per attempt (idempotent per ABC).
- Sleeps `retry_policy.delay_for_attempt(i)` between.
- Logs INFO per attempt.

Called from Phase 141 streaming / Phase 142 recording loops:
```python
with HardwareSession(port, retry_policy=RetryPolicy(), auto_reconnect=True) as adapter:
    while running:
        try: value = adapter.read_pid(0x0C)
        except ConnectionError:
            if not session.try_reconnect(): raise
            continue
        yield value
```

### AutoDetector verbose + on_attempt

```python
def __init__(self, port, baud=None, make_hint=None, timeout_s=5.0,
             verbose=False, on_attempt=None):   # NEW
```

Inside `detect()`, at each protocol try:
- `if self.verbose: logger.info("AutoDetector trying %s", protocol)`.
- On success: `if self.on_attempt: self.on_attempt(protocol, None)`.
- On exception: `if self.on_attempt: self.on_attempt(protocol, err)`.

Defaults preserve Phase 139 exactly. `diagnose` step 3 passes both: callback drives Rich live progress display.

### MockAdapter.flaky_rate

```python
def __init__(self, ..., flaky_rate: float = 0.0, flaky_seed: Optional[int] = None):
    self._flaky_rate = max(0.0, min(1.0, flaky_rate))
    self._flaky_rng = random.Random(flaky_seed)

def _roll_flaky(self, method_name):
    if self._flaky_rate > 0.0 and self._flaky_rng.random() < self._flaky_rate:
        raise TimeoutError(f"mock flaky failure in {method_name}")
```

Call at top of `connect`, `send_command`, `read_dtcs`, `clear_dtcs`, `read_pid`, `read_vin`. NOT in `disconnect` (ABC says never raises) or `get_protocol_name` (no wire).

`flaky_rate=0.0` short-circuits every roll — Phase 140 behavior preserved.

### CLI `diagnose` subcommand (5 steps)

Signature: `motodiag hardware diagnose --port PORT [--bike SLUG] [--make MAKE] [--mock] [--verbose]`.

Each step renders numbered Rich panel with ICON_OK/WARN/FAIL + observation + remediation (if WARN/FAIL).

**Step 1 — Serial port open?**
- `serial.Serial(port)` in try/except. On SerialException/PermissionError/FileNotFoundError → FAIL panel with OS-specific remediation:
  > "Could not open `{port}`. Windows: `python -m serial.tools.list_ports` → Device Manager → Ports (COM & LPT). Linux/macOS: `ls /dev/tty*` + `usermod -aG dialout $USER`. Bluetooth: pair first in OS settings. USB-serial driver missing: common chipsets CH340/FTDI/CP210x — install manufacturer driver."
- On FAIL, **short-circuit** — skip steps 2-5 (they all require open port). Render summary immediately.

**Step 2 — Adapter responds to ATZ?**
- Write `b"ATZ\r"`, read 50 bytes, 2s timeout.
- Printable reply → OK "Adapter responded to ATZ (appears ELM327-compatible)."
- Silence → WARN (not FAIL — non-ELM327 adapters legitimately don't speak AT):
  > "Check power: adapter typically powered off OBD pin 16 (+12V). Verify with multimeter. No power → check OBD fuse. Power-cycle adapter: unplug 10s, replug. Bluetooth pairing stale: unpair + re-pair. Ignition state: some bikes power OBD only with ignition ON."
- Continue to step 3 regardless.

**Step 3 — Negotiate protocol?**
- Construct `AutoDetector(port, make_hint, timeout_s, verbose=True, on_attempt=callback)`. Callback updates Rich table: "J1850 · FAIL · TimeoutError", "CAN · FAIL · ConnectionError", "ELM327 · OK".
- Success → OK "Negotiated protocol: `{name}`."
- `NoECUDetectedError` → FAIL:
  - If `--bike` + Phase 145 compat DB importable: show top-3 ranked compat hits.
  - Else: generic guidance ("Harleys: J1850 pre-2011 or CAN 2011+. Japanese: K-line pre-2010 or CAN 2010+.").
- On FAIL, skip steps 4-5.

**Step 4 — Read VIN?**
- `adapter.read_vin()`. 17-char → OK. `None` → WARN "ECU did not respond to Mode 09 PID 02. Many pre-2008 bikes don't implement VIN. Use frame neck sticker." `UnsupportedCommandError` → WARN with same frame-neck-sticker guidance.
- Does not block step 5.

**Step 5 — Full-stack DTC scan.**
- `adapter.read_dtcs()`. Returns list → OK with inline Code/Description table via `resolve_dtc_info`.
- `ProtocolError` → FAIL:
  > "Mode 03 scan failed: `{exc}`. Adapter connected but ECU refused DTC read. Typical causes: ECU in security lockout (try ignition-off 30s then on); or bike uses Mode 13/17 for enhanced DTCs instead of Mode 03."

**Summary panel** after 5 steps: "3/5 checks passed. Issues found: (2) WARN — Adapter did not respond to ATZ; (4) WARN — VIN not available. Next steps: If step 3 failed → `motodiag hardware compat --bike SLUG`; if 1-3 passed but higher failed → hardware is fine, ECU is the blocker."

**`--mock` path:** steps 1+2 auto-pass (no real serial); step 3 runs MockAdapter("Mock Protocol"); steps 4+5 normal. Green happy-path rehearsal for training + demos.

**`--verbose`:** raises `motodiag.hardware` logger to DEBUG; all `send_command` traffic echoed to dim-grey side panel.

### CLI retry flags

- `scan` / `info`: `--retry`/`--no-retry`, default **on**. Retry → `RetryPolicy()` with defaults passed to HardwareSession. Footer "Operation succeeded after 2 retries (transient timeout)" when retries occurred.
- `clear`: `--retry`/`--no-retry`, default **off**. Opt-in for destructive ops.
- `stream` (conditional on Phase 141): `--auto-reconnect`/`--no-auto-reconnect`, default on.

## Key Concepts

- **Backoff formula** exponential-with-clamp — AWS-SDK pattern. No jitter (single mechanic, single bike, tests need determinism).
- **`retry_on: list[type[Exception]]`** — type list, not string match. Extensible.
- **Non-retryable:** UnsupportedCommandError (semantic-negative), NoECUDetectedError (terminal), KeyboardInterrupt (user-initiated).
- **`time.sleep` module-scoped patch** — tests patch `motodiag.hardware.connection.time.sleep` (NOT global `time.sleep`).
- **Deterministic flaky mock** — `flaky_seed=42` + pinned count in tests.
- **ResilientAdapter is decorator** — wraps ANY ProtocolAdapter (real or mock) transparently.
- **Rich Panel pattern** — reuses Phase 129 `theme.ICON_OK/WARN/FAIL` + `get_console()`.
- **Mechanic-readable remediation** — no tracebacks, imperative plain English with shop-floor vocabulary ("power-cycle", "pin 16", "frame neck sticker").

## Verification Checklist

- [x] `RetryPolicy()` defaults correct.
- [x] `delay_for_attempt` monotonic non-decreasing with clamp.
- [x] `should_retry` False for `UnsupportedCommandError` + `NoECUDetectedError`.
- [x] `HardwareSession(port, adapter_override=mock)` no-retry preserves Phase 140 exactly.
- [x] `HardwareSession(..., retry_policy=RetryPolicy())` returns `ResilientAdapter`-wrapped.
- [x] Retry loop logs at INFO per attempt + summary on success/exhaust.
- [x] `ResilientAdapter` passes `UnsupportedCommandError`/`NoECUDetectedError` without retry.
- [x] `ResilientAdapter.clear_dtcs` does NOT retry (destructive).
- [x] `MockAdapter(flaky_rate=0.0)` byte-identical to Phase 140.
- [x] `MockAdapter(flaky_rate=0.5, flaky_seed=42)` deterministic across two constructions.
- [x] `AutoDetector(verbose=False, on_attempt=None)` behaves identically to Phase 139.
- [x] `motodiag hardware diagnose --port X --mock` prints 5 green panels + "5/5 checks passed".
- [x] `diagnose` with bad port short-circuits at step 1 with OS remediation.
- [x] `scan --no-retry` behaves as Phase 140 did.
- [x] `scan --retry` (default) survives 2-attempt transient failure.
- [x] `clear` defaults `--no-retry` — single-attempt only.
- [x] Phase 134-140 tests pass unchanged.
- [x] No raw Python traceback leaks from `diagnose` under any failure mode.

## Risks

- **Parallel-planning ordering with 141-145.** Spec refers to `stream`/`log`/`dashboard`/`compat` as "existing" but at plan time only scan/clear/info exist. Phase 146 defensively checks `if "stream" in hardware_group.commands` and `if importlib.util.find_spec("motodiag.hardware.compat")` — graceful degradation. Build-time deviation noted if triggered.
- **Pydantic `arbitrary_types_allowed=True` on `retry_on`.** Exception-class validation loose — a caller passing `retry_on=[str]` compiles but never retries. Accepted risk; no real caller passes garbage.
- **`time` module import shadowing.** `hardware/connection.py` adds `import time`; tests patch at `motodiag.hardware.connection.time.sleep`.
- **`ResilientAdapter` ABC compliance** — all 8 abstract methods covered. If ABC grows 9th method, wrapper breaks — regression test `test_instantiable` covers.
- **Flaky mock RNG determinism** across Python versions. Historical stable but not contractually. Pinned test counts computed on 3.11+; `sys.version_info` gate skips older.
- **`serial.Serial` patching for step 1 vs step 2** — separate mocks, same symbol. Lazy `import serial` inside command body. `monkeypatch` at command-module scope.
- **Rich Live during step 3** — ANSI noise in CliRunner captures. Plan uses separate `console.print` calls per attempt (not Live context). Test assertions stay clean; UX slightly less polished (acceptable for troubleshooter).
- **Observer effect on backward-compat.** `retry_policy: Optional[RetryPolicy] = None` explicit, not default_factory.
- **Mechanic-facing text is load-bearing UX.** Review checkpoint: non-developer must follow every remediation without questions. Imperative, shop-floor vocabulary, specific values (pin 16, 12V, 17-char VIN).

## Dependencies flagged

- **Hard:** Phases 134, 139, 140 (shipped).
- **Soft:** Phase 145 (compat DB) — graceful ImportError fallback.
- **Soft:** Phase 141 (stream) — conditional `--auto-reconnect` registration.
