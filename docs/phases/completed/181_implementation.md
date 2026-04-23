# MotoDiag Phase 181 — WebSocket Live Data

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-22

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

Outputs (462 LoC route + 498 LoC tests = 960 total):
- `src/motodiag/api/routes/live.py` (462 LoC) — `LiveReadingProvider`
  ABC + `FakeLiveProvider` (deterministic test stub) +
  `ConnectionManager` + WebSocket handler + `get_live_provider`
  factory. Custom 4xxx close codes as module-level constants.
- `src/motodiag/api/app.py` — mount the live router (WS route
  declares the full `/v1/live/...` path so it is included without a
  prefix).
- `src/motodiag/api/middleware.py` — exempt `/v1/live` from rate
  limiter (defensive — `BaseHTTPMiddleware` does not run on WS
  connections anyway, but the exempt list documents the intent and
  covers any future HTTP endpoint under the same prefix).
- `tests/test_phase181_live_ws.py` (498 LoC, 24 tests across 6
  classes).
- No migration. SCHEMA_VERSION stays at 38.

## Logic

### `WebSocket /v1/live/{session_id}` flow

1. Server picks a subprotocol from the client's offered list (if a
   `bearer.<key>` protocol is offered, echo it so the handshake
   succeeds), then `accept()`s the connection.
2. Server extracts the API key from either `?api_key=...` query
   param or `Sec-WebSocket-Protocol: bearer.<key>` subprotocol
   header. Invalid / missing → close 4401.
3. Server resolves the caller's active subscription tier. No sub →
   close 4402 (live streaming is a paid-tier feature).
4. Server verifies the session belongs to the caller (Phase 178
   `get_session_for_owner`). Missing / cross-user → close 4404.
5. Server constructs a `LiveReadingProvider` via the
   `get_live_provider` factory. Tests monkey-patch this symbol on
   the module to inject deterministic fakes.
6. Stream loop: every iteration, (a) non-blockingly poll for a
   client action via `asyncio.wait_for(receive_text, 1ms)`; (b)
   honor pause/resume/set_interval_ms; (c) read one frame from the
   provider and send it as JSON. `provider.read_frame()` returning
   `None` is the "stream ended" signal → close 1000.
7. Any unhandled provider exception logs + closes 4500.
8. `finally` block always unregisters from the connection manager
   and calls `provider.close()` — even on `WebSocketDisconnect`
   from client-side — so hardware handles never leak.

### Close codes

| Code  | Meaning                                          |
|------:|--------------------------------------------------|
| 4401  | Invalid / missing API key                        |
| 4402  | Subscription required                            |
| 4404  | Session not found / cross-user                   |
| 4429  | Rate-limit exceeded (provider-internal throttle) |
| 4500  | Provider error (hardware unreachable)            |
| 1000  | Normal close (stream ended, client disconnect)   |

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

Generates deterministic synthetic frames every `interval_ms`
(default 500ms, clamped to [50, 10000] via `_clamp_interval`):
RPM walks 1000-3000, coolant 80-95°C, throttle 0-100%, voltage
13.5-14.5V. Ends after `max_frames` (default 100 — tests set
lower for quick completion). Seeded `random.Random(seed)` →
same seed produces identical sequences (verified by
`test_deterministic_same_seed`).

### Provider factory

`get_live_provider(session_id, *, provider_override=None)` returns:
- `provider_override` if explicitly passed (convenience for unit
  tests).
- `FakeLiveProvider` when `MOTODIAG_LIVE_PROVIDER=fake` (default).
- Raises `ProviderUnavailableError` for `=obd` — Phase 140 adapter
  wiring is deferred (hooks are in place; the factory just needs a
  constructor wired when real hardware is integrated).

**Important:** the route calls `get_live_provider(session_id)` at
module scope, so tests patch by `monkeypatch.setattr(live_mod,
"get_live_provider", ...)`. The route function itself no longer
takes a `provider_override` kwarg — FastAPI attempted to treat the
annotated ABC as a query-parameter Pydantic field at startup and
raised `FastAPIError: Invalid args for response field`. Moving the
override seam to the module-level factory cleared the startup error
and is strictly cleaner (deviation logged below).

### Connection manager

`ConnectionManager` tracks active WS connections keyed by
`session_id` so server-side shutdowns could broadcast in the
future. Lightweight in-memory dict; multi-worker deployments would
need shared state (Track J scope). `register` / `unregister` /
`count` are all idempotent — `unregister` on an unknown connection
is a no-op.

### Client → server actions

| Action                                     | Effect                                    |
|--------------------------------------------|-------------------------------------------|
| `{"action": "pause"}`                      | Halt frame emission until resume          |
| `{"action": "resume"}`                     | Resume frame emission                     |
| `{"action": "set_interval_ms", ...}`       | Change cadence (clamped to [50, 10000])   |

Invalid JSON / unknown actions are silently ignored — the stream
keeps flowing.

## Key Concepts

- **`@router.websocket(path)`** — FastAPI WebSocket routing decorator.
  Unlike HTTP routes, WS routes cannot declare Pydantic-serializable
  function parameters beyond the `WebSocket` object + path params.
- **`WebSocket.accept(subprotocol=...)`** — must be awaited before any
  receive/send; `subprotocol` echoes back the chosen protocol string
  per RFC 6455.
- **`WebSocket.close(code=, reason=)`** — custom codes in the 4000-4999
  range are app-level (not reserved by the RFC). Clients can
  inspect `exc.code` on `WebSocketDisconnect` to differentiate.
- **`asyncio.wait_for(receive_text, timeout=0.001)`** — non-blocking
  poll for client messages in the stream loop. `asyncio.TimeoutError`
  is the "no message yet" signal.
- **`WebSocketDisconnect`** — raised by Starlette when the peer
  closes. Route wraps the loop in `try/except/finally` so cleanup
  always runs.
- **FastAPI TestClient `websocket_connect`** — sync context manager
  using `httpx` internally. `ws.receive_json()` / `ws.send_text()` /
  `ws.receive_text()`. A close code is surfaced by raising
  `WebSocketDisconnect(code=...)` on the next receive.
- **`subprotocols=[...]`** param on `websocket_connect` — sets the
  `Sec-WebSocket-Protocol` header; server must echo one back or the
  handshake fails.

## Verification Checklist

- [x] WS connect with valid key + own session → frames stream.
- [x] WS connect with no key → 4401 close.
- [x] WS connect with bogus key → 4401 close.
- [x] WS connect with valid key but no subscription → 4402 close.
- [x] WS connect to cross-user session → 4404 close.
- [x] WS connect to nonexistent session → 4404 close.
- [x] `bearer.<key>` subprotocol auth works.
- [x] `{"action": "set_interval_ms": N}` action accepted end-to-end.
- [x] Invalid JSON client message does not crash the stream.
- [x] Provider `close()` called on client disconnect (connection
      manager unregisters; tested via count before/after).
- [x] Provider `read_frame` exception → 4500 close.
- [x] `ProviderUnavailableError` at factory → 4500 close.
- [x] Rate limiter exempts `/v1/live/*` paths (prefix in
      `_RATE_LIMIT_EXEMPT_PATHS`).
- [x] FakeProvider determinism: same seed → identical sequence.
- [x] Clamp interval: below 50 → 50, above 10000 → 10000.
- [x] Phase 175-180 still GREEN (215/215 across Track H).
- [x] Zero AI calls, zero network.

## Risks

- **WebSocket testing in pytest** — resolved. FastAPI's TestClient
  supports `websocket_connect` synchronously; `FakeLiveProvider`
  with small `max_frames` + small `interval_ms` keeps tests fast
  (24 tests in 23s).
- **Frame-rate flooding** — resolved. `_clamp_interval` caps
  `set_interval_ms` to [50, 10000]. A client cannot cause the
  server to spin faster than 20 Hz.
- **Connection leaks** — resolved. WS handler's `finally` block
  always calls `provider.close()` and `manager.unregister()` even
  on `WebSocketDisconnect`.
- **Multi-process state** — acknowledged, deferred. The connection-
  manager dict is per-process. A multi-worker uvicorn deploy would
  split state arbitrarily across workers. Acceptable for Phase 181
  (single-worker is the default `motodiag serve` setup); Track J
  adds Redis-backed state.
- **Route signature gotcha** — caught during build. FastAPI treats
  non-Pydantic-compatible type annotations on WS route functions as
  query-parameter fields. Keeping the route signature to just
  `websocket: WebSocket, session_id: int` is mandatory; any
  additional parameter must be resolved via the factory/module-level
  seam, never through the route kwargs.

## Deviations from Plan

1. **Route signature — `provider_override` removed from the route.**
   The plan wrote the route as `async def live_session_ws(ws,
   session_id, provider_override=None)` for test injection. FastAPI
   rejected this at module-import time with `FastAPIError: Invalid
   args for response field!` because it tried to treat
   `Optional[LiveReadingProvider]` as a query-parameter Pydantic
   field. Fix: removed `provider_override` from the route, kept the
   kwarg on `get_live_provider` itself, and tests inject fakes by
   `monkeypatch.setattr(live_mod, "get_live_provider", ...)`. The
   `provider_override=` kwarg on the factory is still useful for
   unit tests that call `get_live_provider` directly.
2. **Test count — 24 (planned 18).** 6 additional tests emerged
   during build: `test_no_subscription_closes_4402` (the 4402 path
   wasn't in the original plan checklist but fell naturally out of
   the "any paid tier" requirement), `test_different_seeds_diverge`,
   `test_set_interval_clamps` (in addition to the module-level
   clamp test), `test_close_idempotent`, `test_connection_manager_
   register_unregister`, and `test_get_live_provider_override`.
3. **Rate-limit exemption is defensive.** Starlette's
   `BaseHTTPMiddleware` does not execute on WebSocket connections —
   the WS handshake bypasses it entirely. Adding `/v1/live` to
   `_RATE_LIMIT_EXEMPT_PATHS` is a no-op today but documents intent
   and covers any future HTTP endpoint under `/v1/live/*`.

## Results

| Metric                            | Value                      |
|-----------------------------------|----------------------------|
| Route LoC                         | 462                        |
| Test LoC                          | 498                        |
| Total LoC                         | 960                        |
| Tests                             | 24 GREEN                   |
| Phase 181 test runtime            | 23.09s                     |
| Track H regression (175-181)      | 215 / 215 GREEN (5m 19s)   |
| Schema version                    | 38 (unchanged)             |
| Migration                         | None                       |
| AI calls                          | 0                          |
| Network calls                     | 0                          |
| Close codes implemented           | 6 (1000, 4401/02/04/29/00) |
| Subscription tier required        | individual (≥ any paid)    |
| Track H endpoint count            | 51 HTTP + 1 WS             |

**Key finding:** WebSocket transports collapse cleanly into the
Track H shape once two gotchas are handled — (1) FastAPI's WS route
signature cannot hold anything that isn't a `WebSocket` or path
param without tripping query-param coercion, and (2) auth must flow
through query param or subprotocol (browser WebSocket clients
cannot set arbitrary headers). The `LiveReadingProvider` ABC gives
Track E's Phase 140 adapter an easy insertion point — Phase 181
ships the contract and deterministic fake; real hardware wiring
lands when it's needed, with no transport-layer rework.
