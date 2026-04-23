"""Phase 181 — WebSocket live data endpoint tests.

Five classes, ~18 tests. Zero AI, zero network.

Tests use FastAPI TestClient's synchronous ``websocket_connect``
context manager. The route's auth/tier/ownership gates are checked
via custom 4xxx close codes; the streaming body is exercised against
a :class:`FakeLiveProvider` with ``max_frames`` capped low so tests
run in <1s.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from motodiag.api import create_app
from motodiag.api.routes.live import (
    DEFAULT_INTERVAL_MS,
    MAX_INTERVAL_MS,
    MIN_INTERVAL_MS,
    ConnectionManager,
    FakeLiveProvider,
    LiveReadingProvider,
    ProviderUnavailableError,
    WS_CLOSE_INVALID_KEY,
    WS_CLOSE_NORMAL,
    WS_CLOSE_PROVIDER_ERROR,
    WS_CLOSE_SESSION_NOT_FOUND,
    WS_CLOSE_SUBSCRIPTION_REQUIRED,
    _clamp_interval,
    get_connection_manager,
    get_live_provider,
)
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.core.session_repo import create_session_for_owner


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase181.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("MOTODIAG_LIVE_PROVIDER", "fake")
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username="bob"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, 'b@ex.com', 'individual', 1)",
            (username,),
        )
        return cursor.lastrowid


def _make_sub(db_path, user_id, tier="individual"):
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, current_period_end)
               VALUES (?, ?, 'active', datetime('now', '+30 days'))""",
            (user_id, tier),
        )


def _make_session(db_path, user_id):
    return create_session_for_owner(
        owner_user_id=user_id,
        vehicle_make="Honda", vehicle_model="CBR600",
        vehicle_year=2005, db_path=db_path,
    )


# ===========================================================================
# 1. FakeLiveProvider unit tests
# ===========================================================================


class TestFakeProvider:

    def test_deterministic_same_seed(self):
        a = FakeLiveProvider(interval_ms=10, max_frames=5, seed=7)
        b = FakeLiveProvider(interval_ms=10, max_frames=5, seed=7)

        async def drain(p):
            await p.open()
            frames = []
            while True:
                f = await p.read_frame()
                if f is None:
                    break
                frames.append({k: v for k, v in f.items() if k != "ts"})
            await p.close()
            return frames

        fa = asyncio.run(drain(a))
        fb = asyncio.run(drain(b))
        assert fa == fb
        assert len(fa) == 5

    def test_different_seeds_diverge(self):
        a = FakeLiveProvider(interval_ms=10, max_frames=3, seed=1)
        b = FakeLiveProvider(interval_ms=10, max_frames=3, seed=2)

        async def drain(p):
            await p.open()
            out = []
            while True:
                f = await p.read_frame()
                if f is None:
                    break
                out.append(f)
            await p.close()
            return out

        fa = asyncio.run(drain(a))
        fb = asyncio.run(drain(b))
        # At least one frame should differ
        diff = any(
            fa[i]["rpm"] != fb[i]["rpm"]
            or fa[i]["throttle_pct"] != fb[i]["throttle_pct"]
            for i in range(min(len(fa), len(fb)))
        )
        assert diff

    def test_frames_stop_after_max_frames(self):
        p = FakeLiveProvider(interval_ms=5, max_frames=3, seed=0)

        async def run():
            await p.open()
            count = 0
            while True:
                f = await p.read_frame()
                if f is None:
                    break
                count += 1
            await p.close()
            return count

        assert asyncio.run(run()) == 3

    def test_set_interval_clamps(self):
        p = FakeLiveProvider(interval_ms=500, max_frames=1, seed=0)
        asyncio.run(p.set_interval_ms(1))  # below MIN → clamps up
        assert p._interval_ms == MIN_INTERVAL_MS
        asyncio.run(p.set_interval_ms(99_999))  # above MAX → clamps down
        assert p._interval_ms == MAX_INTERVAL_MS
        asyncio.run(p.set_interval_ms(250))
        assert p._interval_ms == 250

    def test_close_idempotent(self):
        p = FakeLiveProvider(max_frames=1, seed=0)

        async def run():
            await p.open()
            await p.close()
            await p.close()  # must not raise
            # after close read_frame returns None
            return await p.read_frame()

        assert asyncio.run(run()) is None


# ===========================================================================
# 2. Module-level helpers
# ===========================================================================


class TestModuleHelpers:

    def test_clamp_interval(self):
        assert _clamp_interval(0) == MIN_INTERVAL_MS
        assert _clamp_interval(1_000_000) == MAX_INTERVAL_MS
        assert _clamp_interval(500) == 500

    def test_default_interval_is_500ms(self):
        assert DEFAULT_INTERVAL_MS == 500

    def test_connection_manager_register_unregister(self):
        m = ConnectionManager()

        class _FakeWS:
            pass
        ws1, ws2 = _FakeWS(), _FakeWS()
        m.register(7, ws1)
        m.register(7, ws2)
        assert m.count(7) == 2
        m.unregister(7, ws1)
        assert m.count(7) == 1
        m.unregister(7, ws2)
        assert m.count(7) == 0
        # Removing from empty is a no-op
        m.unregister(7, ws1)
        assert m.count(7) == 0

    def test_get_live_provider_override(self):
        """An explicit override wins over env config."""
        override = FakeLiveProvider(max_frames=1, seed=0)
        got = get_live_provider(1, provider_override=override)
        assert got is override

    def test_get_live_provider_obd_raises(self, monkeypatch):
        monkeypatch.setenv("MOTODIAG_LIVE_PROVIDER", "obd")
        with pytest.raises(ProviderUnavailableError):
            get_live_provider(1)

    def test_get_live_provider_fake_default(self, monkeypatch):
        monkeypatch.delenv("MOTODIAG_LIVE_PROVIDER", raising=False)
        p = get_live_provider(1)
        assert isinstance(p, FakeLiveProvider)


# ===========================================================================
# 3. WebSocket auth & authorization
# ===========================================================================


class TestWebSocketAuth:

    def test_missing_key_closes_4401(self, api_db):
        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, "individual")
        sid = _make_session(api_db, user_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/v1/live/{sid}") as ws:
                ws.receive_text()
        assert exc.value.code == WS_CLOSE_INVALID_KEY

    def test_bogus_key_closes_4401(self, api_db):
        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, "individual")
        sid = _make_session(api_db, user_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(
                f"/v1/live/{sid}?api_key=mdk_live_not_a_real_key"
            ) as ws:
                ws.receive_text()
        assert exc.value.code == WS_CLOSE_INVALID_KEY

    def test_no_subscription_closes_4402(self, api_db):
        """Valid key but no active subscription — live streaming is a
        paid-tier feature so close with 4402."""
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = _make_session(api_db, user_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(
                f"/v1/live/{sid}?api_key={plaintext}"
            ) as ws:
                ws.receive_text()
        assert exc.value.code == WS_CLOSE_SUBSCRIPTION_REQUIRED

    def test_cross_user_session_closes_4404(self, api_db):
        me = _make_user(api_db, "me")
        _make_sub(api_db, me, "individual")
        other = _make_user(api_db, "other")
        _, plaintext = create_api_key(me, db_path=api_db)
        sid = _make_session(api_db, other)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(
                f"/v1/live/{sid}?api_key={plaintext}"
            ) as ws:
                ws.receive_text()
        assert exc.value.code == WS_CLOSE_SESSION_NOT_FOUND

    def test_nonexistent_session_closes_4404(self, api_db):
        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, "individual")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(
                f"/v1/live/99999?api_key={plaintext}"
            ) as ws:
                ws.receive_text()
        assert exc.value.code == WS_CLOSE_SESSION_NOT_FOUND

    def test_subprotocol_bearer_auth_accepted(
        self, api_db, patched_provider,
    ):
        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, "individual")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = _make_session(api_db, user_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        with client.websocket_connect(
            f"/v1/live/{sid}",
            subprotocols=[f"bearer.{plaintext}"],
        ) as ws:
            frame = ws.receive_json()
            assert "rpm" in frame


# ===========================================================================
# 4. Frame streaming + client actions
# ===========================================================================


@pytest.fixture
def patched_provider(monkeypatch):
    """Patch the live route's provider factory with a short-lived
    FakeLiveProvider for streaming tests."""
    from motodiag.api.routes import live as live_mod

    def _factory(session_id):
        return FakeLiveProvider(
            interval_ms=10, max_frames=3, seed=42,
        )
    monkeypatch.setattr(live_mod, "get_live_provider", _factory)
    yield


class TestFrameStreaming:

    def test_happy_path_streams_then_normal_close(
        self, api_db, patched_provider,
    ):
        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, "individual")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = _make_session(api_db, user_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        with client.websocket_connect(
            f"/v1/live/{sid}?api_key={plaintext}"
        ) as ws:
            frames = []
            try:
                while True:
                    frames.append(ws.receive_json())
            except WebSocketDisconnect as e:
                assert e.code == WS_CLOSE_NORMAL
        assert len(frames) == 3
        for frame in frames:
            assert set(frame) == {
                "ts", "rpm", "coolant_c", "throttle_pct", "voltage_v",
            }
            assert 1000 <= frame["rpm"] <= 3000
            assert 80.0 <= frame["coolant_c"] <= 95.0
            assert 0.0 <= frame["throttle_pct"] <= 100.0
            assert 13.5 <= frame["voltage_v"] <= 14.5

    def test_client_disconnect_unregisters(
        self, api_db, patched_provider,
    ):
        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, "individual")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = _make_session(api_db, user_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        before = get_connection_manager().count(sid)
        with client.websocket_connect(
            f"/v1/live/{sid}?api_key={plaintext}"
        ) as ws:
            ws.receive_json()
        # After context exit, connection unregisters.
        assert get_connection_manager().count(sid) == before

    def test_set_interval_action_accepted(
        self, api_db, patched_provider,
    ):
        """Sending a set_interval_ms action should not crash the
        stream. Exact cadence change is validated in unit tests —
        this is the round-trip integration."""
        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, "individual")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = _make_session(api_db, user_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        with client.websocket_connect(
            f"/v1/live/{sid}?api_key={plaintext}"
        ) as ws:
            ws.send_text(json.dumps({
                "action": "set_interval_ms", "interval_ms": 10,
            }))
            # At least one frame should arrive
            f = ws.receive_json()
            assert "rpm" in f

    def test_invalid_json_action_ignored(
        self, api_db, patched_provider,
    ):
        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, "individual")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = _make_session(api_db, user_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        with client.websocket_connect(
            f"/v1/live/{sid}?api_key={plaintext}"
        ) as ws:
            ws.send_text("not-json")
            f = ws.receive_json()  # Still streams despite bogus msg
            assert "rpm" in f


# ===========================================================================
# 5. Error paths: provider failure
# ===========================================================================


class _ExplodingProvider(LiveReadingProvider):
    async def open(self):
        pass

    async def read_frame(self):
        raise RuntimeError("hardware unplugged")

    async def close(self):
        pass


class TestProviderErrors:

    def test_provider_read_error_closes_4500(self, api_db, monkeypatch):
        from motodiag.api.routes import live as live_mod

        def _factory(session_id):
            return _ExplodingProvider()
        monkeypatch.setattr(live_mod, "get_live_provider", _factory)

        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, "individual")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = _make_session(api_db, user_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(
                f"/v1/live/{sid}?api_key={plaintext}"
            ) as ws:
                ws.receive_text()
        assert exc.value.code == WS_CLOSE_PROVIDER_ERROR

    def test_provider_unavailable_closes_4500(
        self, api_db, monkeypatch,
    ):
        from motodiag.api.routes import live as live_mod

        def _factory(session_id):
            raise ProviderUnavailableError("no hardware")
        monkeypatch.setattr(live_mod, "get_live_provider", _factory)

        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, "individual")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = _make_session(api_db, user_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(
                f"/v1/live/{sid}?api_key={plaintext}"
            ) as ws:
                ws.receive_text()
        assert exc.value.code == WS_CLOSE_PROVIDER_ERROR


# ===========================================================================
# 6. Rate-limit exemption
# ===========================================================================


class TestRateLimitExemption:

    def test_live_path_prefix_is_exempt(self):
        from motodiag.api.middleware import _RATE_LIMIT_EXEMPT_PATHS
        assert "/v1/live" in _RATE_LIMIT_EXEMPT_PATHS
