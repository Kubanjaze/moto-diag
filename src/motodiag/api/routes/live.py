"""Live data WebSocket endpoint (Phase 181).

First non-CRUD surface on Track H — streams live OBD sensor readings
from a :class:`LiveReadingProvider` (default :class:`FakeLiveProvider`
for dev/test) over a WebSocket keyed to a Phase 07 diagnostic
session.

Mechanic-facing use case: a tech connects their phone to a bike via
OBD adapter, opens the app (Track I), and watches RPM / coolant temp
/ throttle position scroll in real time while the bike warms up or
during a test ride. The actual hardware adapter integration is
Phase 134-147 — Phase 181 only owns the **transport layer** and the
auth / session-scoping / close-code contract.

## Close codes

| Code | Meaning                                          |
| ---: | ------------------------------------------------ |
| 4401 | Invalid / missing API key                        |
| 4402 | Subscription required (any paid tier)            |
| 4404 | Session not found / cross-user                   |
| 4429 | Provider-internal rate limit                     |
| 4500 | Provider error (hardware unreachable, etc.)      |
| 1000 | Normal close (client disconnect or server stop)  |

## Auth

Keys can be supplied via query param ``?api_key=mdk_live_...`` (works
in any browser / EventSource-style tool) OR the
``Sec-WebSocket-Protocol: bearer.<key>`` subprotocol header (preferred
for native WebSocket clients that can't set arbitrary headers). Both
are accepted; query param wins on conflict.

## Client → server messages (JSON)

- ``{"action": "pause"}`` — halt frame stream until ``resume``.
- ``{"action": "resume"}`` — resume streaming.
- ``{"action": "set_interval_ms", "interval_ms": 500}`` — change the
  cadence on the fly (clamped to ``[50, 10000]``).

## Server → client frames (JSON)

``{"ts": "2026-04-22T...", "rpm": 1200, "coolant_c": 85.5,
"throttle_pct": 0.0, "voltage_v": 14.1}``
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from motodiag.api.deps import get_db_path
from motodiag.auth.api_key_repo import verify_api_key
from motodiag.auth.deps import tier_meets
from motodiag.core.session_repo import get_session_for_owner


logger = logging.getLogger(__name__)
router = APIRouter(tags=["live"])


# ---------------------------------------------------------------------------
# Close codes (custom 4xxx range, outside WS spec-reserved 1000-2999)
# ---------------------------------------------------------------------------


WS_CLOSE_INVALID_KEY = 4401
WS_CLOSE_SUBSCRIPTION_REQUIRED = 4402
WS_CLOSE_SESSION_NOT_FOUND = 4404
WS_CLOSE_RATE_LIMIT = 4429
WS_CLOSE_PROVIDER_ERROR = 4500
WS_CLOSE_NORMAL = 1000


# ---------------------------------------------------------------------------
# Interval clamp (prevents a misconfigured client from DOSing the server)
# ---------------------------------------------------------------------------


MIN_INTERVAL_MS = 50
MAX_INTERVAL_MS = 10_000
DEFAULT_INTERVAL_MS = 500


def _clamp_interval(interval_ms: int) -> int:
    return max(MIN_INTERVAL_MS, min(MAX_INTERVAL_MS, int(interval_ms)))


# ---------------------------------------------------------------------------
# Provider ABC + fake implementation
# ---------------------------------------------------------------------------


class LiveReadingProvider(ABC):
    """Abstract source of live sensor frames.

    Concrete implementations: :class:`FakeLiveProvider` (dev/test),
    ``OBDLiveProvider`` (Phase 140 wiring — constructed on demand when
    ``MOTODIAG_LIVE_PROVIDER=obd``).
    """

    @abstractmethod
    async def open(self) -> None:
        """Acquire any underlying resource (hardware handle, socket)."""

    @abstractmethod
    async def read_frame(self) -> Optional[dict]:
        """Return the next frame or ``None`` when the stream ends."""

    @abstractmethod
    async def close(self) -> None:
        """Release underlying resources. Must be idempotent."""

    async def set_interval_ms(self, interval_ms: int) -> None:
        """Change frame cadence. Default implementation is a no-op; concrete
        providers override to honor the new rate."""
        return None


class FakeLiveProvider(LiveReadingProvider):
    """Deterministic synthetic frame generator for dev / tests.

    Walks RPM 1000-3000, coolant 80-95°C, throttle 0-100%, voltage
    13.5-14.5V. Seeded :class:`random.Random` → same seed produces
    identical sequences (tests depend on this).
    """

    def __init__(
        self,
        interval_ms: int = DEFAULT_INTERVAL_MS,
        max_frames: int = 100,
        seed: int = 42,
    ) -> None:
        self._interval_ms = _clamp_interval(interval_ms)
        self._max_frames = max_frames
        self._rng = random.Random(seed)
        self._emitted = 0
        self._opened = False
        self._closed = False

    async def open(self) -> None:
        self._opened = True

    async def read_frame(self) -> Optional[dict]:
        if not self._opened or self._closed:
            return None
        if self._emitted >= self._max_frames:
            return None
        # Tests sleep by advancing monotonic clock — asyncio.sleep(0)
        # avoids spinning when the test harness patches sleep.
        if self._emitted > 0:
            await asyncio.sleep(self._interval_ms / 1000.0)
        frame = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "rpm": self._rng.randint(1000, 3000),
            "coolant_c": round(80 + self._rng.random() * 15, 1),
            "throttle_pct": round(self._rng.random() * 100, 1),
            "voltage_v": round(13.5 + self._rng.random(), 2),
        }
        self._emitted += 1
        return frame

    async def close(self) -> None:
        self._closed = True

    async def set_interval_ms(self, interval_ms: int) -> None:
        self._interval_ms = _clamp_interval(interval_ms)


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------


def get_live_provider(
    session_id: int,
    *,
    provider_override: Optional[LiveReadingProvider] = None,
) -> LiveReadingProvider:
    """Pick the right provider for the current environment.

    Tests inject ``provider_override``; dev / CI defaults to
    :class:`FakeLiveProvider`; production sets
    ``MOTODIAG_LIVE_PROVIDER=obd`` to use the Phase 140 adapter
    (implementation deferred — Phase 181 only ships the hook).
    """
    if provider_override is not None:
        return provider_override
    kind = os.environ.get("MOTODIAG_LIVE_PROVIDER", "fake").lower()
    if kind == "obd":
        raise ProviderUnavailableError(
            "OBDLiveProvider wiring is Phase 140+ — not yet hooked up"
        )
    return FakeLiveProvider()


class ProviderUnavailableError(Exception):
    """Raised when a requested provider cannot be constructed."""


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Per-process registry of active WebSocket connections by session.

    Multi-worker deployments would need shared state (Redis); Phase
    181 is single-worker (default ``motodiag serve`` layout) so an
    in-memory dict suffices. Track J addresses the multi-worker case.
    """

    def __init__(self) -> None:
        self._by_session: dict[int, set[WebSocket]] = {}

    def register(self, session_id: int, ws: WebSocket) -> None:
        self._by_session.setdefault(session_id, set()).add(ws)

    def unregister(self, session_id: int, ws: WebSocket) -> None:
        bucket = self._by_session.get(session_id)
        if bucket is None:
            return
        bucket.discard(ws)
        if not bucket:
            self._by_session.pop(session_id, None)

    def count(self, session_id: Optional[int] = None) -> int:
        if session_id is None:
            return sum(len(b) for b in self._by_session.values())
        return len(self._by_session.get(session_id, ()))


_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    return _manager


# ---------------------------------------------------------------------------
# Auth helper — pick the key out of query params or subprotocol
# ---------------------------------------------------------------------------


_SUBPROTO_PREFIX = "bearer."


def _extract_ws_key(websocket: WebSocket) -> Optional[str]:
    key = websocket.query_params.get("api_key")
    if key:
        return key.strip()
    # Sec-WebSocket-Protocol can be comma-separated: "bearer.<key>, json"
    protocols = websocket.headers.get("sec-websocket-protocol", "")
    for raw in protocols.split(","):
        part = raw.strip()
        if part.startswith(_SUBPROTO_PREFIX):
            candidate = part[len(_SUBPROTO_PREFIX):].strip()
            if candidate:
                return candidate
    return None


def _accept_with_subprotocol(
    websocket: WebSocket,
) -> Optional[str]:
    """Return the subprotocol to echo back (per RFC 6455 — if a
    client offers a subprotocol we pick one and echo it, else
    connection is rejected). We always pick ``bearer.<key>`` when
    offered so the handshake succeeds."""
    protocols = websocket.headers.get("sec-websocket-protocol", "")
    for raw in protocols.split(","):
        part = raw.strip()
        if part.startswith(_SUBPROTO_PREFIX):
            return part
    return None


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.websocket("/v1/live/{session_id}")
async def live_session_ws(
    websocket: WebSocket,
    session_id: int,
) -> None:
    """Stream live sensor frames for ``session_id`` to the caller.

    Auth → subscription check → ownership check → provider loop.
    All failures close with a custom 4xxx code so clients can
    disambiguate without parsing bodies.
    """
    subproto = _accept_with_subprotocol(websocket)
    await websocket.accept(subprotocol=subproto)

    db_path = _resolve_db_path(websocket)

    # --- 1. API key ---
    plaintext = _extract_ws_key(websocket)
    if not plaintext:
        await websocket.close(
            code=WS_CLOSE_INVALID_KEY, reason="missing API key",
        )
        return
    api_key = verify_api_key(plaintext, db_path=db_path)
    if api_key is None:
        await websocket.close(
            code=WS_CLOSE_INVALID_KEY, reason="invalid API key",
        )
        return

    # --- 2. Subscription tier ---
    sub_tier = _resolve_tier(api_key.user_id, db_path=db_path)
    if not tier_meets(sub_tier, "individual"):
        await websocket.close(
            code=WS_CLOSE_SUBSCRIPTION_REQUIRED,
            reason="active subscription required",
        )
        return

    # --- 3. Session ownership (cross-user → 4404) ---
    session_row = get_session_for_owner(
        session_id, api_key.user_id, db_path=db_path,
    )
    if session_row is None:
        await websocket.close(
            code=WS_CLOSE_SESSION_NOT_FOUND,
            reason="session not found",
        )
        return

    # --- 4. Provider ---
    try:
        provider = get_live_provider(session_id)
    except ProviderUnavailableError as e:
        logger.exception(
            "live provider unavailable for session %d", session_id,
        )
        await websocket.close(
            code=WS_CLOSE_PROVIDER_ERROR, reason=str(e),
        )
        return

    _manager.register(session_id, websocket)
    paused = False

    try:
        await provider.open()
        while True:
            # Read any pending client action non-blockingly.
            try:
                msg = await asyncio.wait_for(
                    websocket.receive_text(), timeout=0.001,
                )
                action = _parse_action(msg)
                if action is not None:
                    paused, _ = await _apply_action(
                        action, provider, paused,
                    )
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break

            if paused:
                await asyncio.sleep(0.05)
                continue

            try:
                frame = await provider.read_frame()
            except Exception as e:
                logger.exception(
                    "provider read_frame failed for session %d: %s",
                    session_id, e,
                )
                await websocket.close(
                    code=WS_CLOSE_PROVIDER_ERROR,
                    reason="provider error",
                )
                return

            if frame is None:
                # Stream ended — normal close.
                await websocket.close(code=WS_CLOSE_NORMAL)
                return
            try:
                await websocket.send_json(frame)
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    finally:
        _manager.unregister(session_id, websocket)
        try:
            await provider.close()
        except Exception as e:
            logger.warning(
                "provider close failed for session %d: %s",
                session_id, e,
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_action(raw: str) -> Optional[dict]:
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


async def _apply_action(
    action: dict,
    provider: LiveReadingProvider,
    paused: bool,
) -> tuple[bool, bool]:
    """Apply a client action. Returns ``(new_paused, ok)``."""
    name = action.get("action")
    if name == "pause":
        return True, True
    if name == "resume":
        return False, True
    if name == "set_interval_ms":
        new = action.get("interval_ms")
        if isinstance(new, (int, float)):
            await provider.set_interval_ms(int(new))
            return paused, True
    return paused, False


def _resolve_db_path(websocket: WebSocket) -> str:
    """Pick up the app-level db_path override (tests) or fall back to
    Settings. Mirrors the HTTP middleware's lookup."""
    app = websocket.app
    override = app.dependency_overrides.get(get_db_path)
    if override is not None:
        return override()
    return get_db_path()


def _resolve_tier(user_id: int, db_path: str) -> Optional[str]:
    from motodiag.billing.subscription_repo import (
        get_active_subscription,
    )
    sub = get_active_subscription(user_id, db_path=db_path)
    return sub.tier if sub is not None else None
