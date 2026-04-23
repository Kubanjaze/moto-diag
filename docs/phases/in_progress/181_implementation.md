# MotoDiag Phase 181 — WebSocket Live Data

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

First non-CRUD endpoint type on Track H — WebSocket streams for live
sensor data. Mechanic-facing use case: a tech connects their phone
(Track I) to a bike via OBD adapter, opens the app, and watches RPM
+ coolant temp + throttle position scroll in real time during a
test ride or warm-up.

The actual hardware adapter integration is Phase 134-147 (Track E,
already complete). Phase 181 is the **transport layer** — a
WebSocket endpoint that forwards live readings from a Phase 140
hardware adapter (or a fake one for tests) to authenticated web /
mobile clients.

CLI — none. Pure HTTP/WS surface.

Outputs (~280 LoC + ~18 tests):
- `src/motodiag/api/routes/live.py` (~280 LoC) — WebSocket endpoint
  + `LiveReadingProvider` ABC + `FakeLiveProvider` (test) + connection
  manager.
- `src/motodiag/api/app.py` — mount the WS endpoint.
- `src/motodiag/api/middleware.py` — exempt WS paths from rate limit
  (rate limit doesn't make sense for an open stream; per-message
  throttling is provider-side).
- `tests/test_phase181_live_ws.py` (~18 tests).
- No migration. SCHEMA_VERSION stays at 38.

## Logic

### `WebSocket /v1/live/{session_id}` flow

1. Client opens WS connection with `?api_key=mdk_live_...` query
   param (or `Sec-WebSocket-Protocol: bearer.<key>` header — both
   accepted for browser-vs-native compat).
2. Server validates the key + checks the session belongs to the
   caller (Phase 178 `get_session_for_owner`). On failure → close
   with code 4401 (custom).
3. Server checks `require_tier("individual")` — any paid tier can
   stream. Anonymous = 4402.
4. Server creates a `LiveReadingProvider` per-connection (default
   `FakeLiveProvider` in dev/test; Phase 140 `OBDAdapter` wired in
   prod when `MOTODIAG_LIVE_PROVIDER=obd`).
5. Server reads sensor frames from the provider in a background task
   and pushes JSON messages: `{"ts": ISO, "rpm": int, "coolant_c":
   float, "throttle_pct": float, "voltage_v": float}`.
6. Client can send messages to the server: `{"action": "pause"}`,
   `{"action": "resume"}`, `{"action": "set_interval_ms": 500}` —
   change stream cadence on the fly.
7. On client disconnect or session close → provider cleanup.

### Close codes

| Code  | Meaning                                          |
|------:|--------------------------------------------------|
| 4401  | Invalid / missing API key                        |
| 4402  | Subscription required                            |
| 4404  | Session not found / cross-user                   |
| 4429  | Rate-limit exceeded (provider-internal throttle) |
| 4500  | Provider error (hardware unreachable)            |
| 1000  | Normal close (client disconnect or server stop)  |

### `LiveReadingProvider` ABC

```python
class LiveReadingProvider(ABC):
    @abstractmethod
    async def open(self) -> None: ...

    @abstractmethod
    async def read_frame(self) -> dict | None:
        """Return next frame or None when stream ends."""

    @abstractmethod
    async def close(self) -> None: ...

    async def set_interval_ms(self, interval_ms: int) -> None:
        """Optional — providers can ignore."""
```

### `FakeLiveProvider`

Generates deterministic synthetic frames every `interval_ms` (default
500ms): RPM walks 1000-3000, coolant 80-95, throttle 0-100,
voltage 13.5-14.5. Ends after `max_frames` (default 100) — tests can
set lower.

### Provider factory

`get_live_provider(settings)` returns:
- `FakeLiveProvider` when `MOTODIAG_LIVE_PROVIDER=fake` (default).
- `OBDLiveProvider` when `=obd` — wraps Phase 140 adapter; raises
  if hardware not available.

### Connection manager

Tracks active WS connections by `session_id` so server-side
shutdowns can broadcast. Lightweight in-memory dict; multi-worker
deployments would need shared state (Track J scope).

## Verification Checklist

- [ ] WS connect with valid key + own session → frames stream.
- [ ] WS connect with no key → 4401 close.
- [ ] WS connect to cross-user session → 4404 close.
- [ ] Individual tier OK (no quota for streaming).
- [ ] Client `{"action": "pause"}` halts frames; resume continues.
- [ ] Client `{"action": "set_interval_ms": 100}` changes cadence.
- [ ] Provider `close()` called on client disconnect.
- [ ] Rate limiter exempts `/v1/live/*` paths.
- [ ] FakeProvider determinism: same seed → identical sequence.
- [ ] Phase 175-180 still GREEN.
- [ ] Zero AI calls.

## Risks

- **WebSocket testing in pytest**. FastAPI's TestClient supports
  `websocket_connect` synchronously — tests use that. Async
  generator code in routes uses `asyncio.sleep`; tests use `time.
  sleep` / monotonic-clock checks.
- **Frame-rate flooding**. A misconfigured client could ask for
  `interval_ms=1` and DOS the server. Mitigation: clamp to [50,
  10000] in `set_interval_ms`.
- **Connection leaks**. If a client drops without close, the
  provider task could leak. Mitigation: every WS handler wraps in
  try/finally that always calls `provider.close()`.
- **Multi-process state**. The connection-manager dict is per-
  process. A multi-worker uvicorn deploy splits state arbitrarily
  across workers. Acceptable for Phase 181 (single-worker is the
  default `motodiag serve` setup); Track J adds Redis-backed state.
