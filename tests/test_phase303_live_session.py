"""Phase 303 — a session on the live socket (Logic item 5; the operator's
K56 requirement 3).

A session opens `/v1/live/{id}` through the `bearer.<token>` subprotocol
only. A query string is written to the server's logs, so a session token
there is refused with the socket's no-credential close, 4401, while an
`mdk_` key keeps the query parameter as `test_phase181_live_ws.py` uses it.
Across a login, a REST call, the subprotocol open and the refused query
attempt, no in-process log record carries "mds_".
"""

from __future__ import annotations

import logging

import pytest
from starlette.websockets import WebSocketDisconnect

from motodiag.api.routes import live as live_mod
from motodiag.api.routes.live import (
    FakeLiveProvider, WS_CLOSE_INVALID_KEY, WS_CLOSE_SESSION_NOT_FOUND,
    WS_CLOSE_SUBSCRIPTION_REQUIRED,
)
from motodiag.core.session_repo import create_session_for_owner

from support.phase303 import (
    add_member, auth, client, login, make_key, make_shop, make_sub, make_user,
    new_db,
)

LOGGERS = ("motodiag.api.access", "motodiag.api.routes.live", "motodiag.api.errors",
           "motodiag.api.routes.auth", "motodiag.auth.sessions_repo",
           "motodiag.auth.api_key_repo", "motodiag.api")


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = new_db(tmp_path, monkeypatch)
    monkeypatch.setattr(live_mod, "get_live_provider",
                        lambda session_id: FakeLiveProvider(interval_ms=10, max_frames=2, seed=1))
    return path


def _bike_session(db, owner):
    return create_session_for_owner(owner_user_id=owner, vehicle_make="Honda",
                                    vehicle_model="CBR600", vehicle_year=2005, db_path=db)


def _close_code(c, path, **kw):
    with pytest.raises(WebSocketDisconnect) as exc:
        with c.websocket_connect(path, **kw) as ws:
            while True:
                ws.receive_json()
    return exc.value.code


def _tech_at_a_shop(db):
    olga = make_user(db, "olga")
    make_sub(db, olga, "shop")
    a = make_shop(db, "Shop A", olga)
    tess = make_user(db, "tess")
    add_member(db, a, tess)
    return tess


class TestTheSocketTakesASession:
    def test_a_session_opens_its_own_session_through_the_subprotocol(self, db):
        tess = _tech_at_a_shop(db)
        sid = _bike_session(db, tess)
        c = client(db)
        token = login(c, "tess")
        with c.websocket_connect(f"/v1/live/{sid}", subprotocols=[f"bearer.{token}"]) as ws:
            assert "rpm" in ws.receive_json()

    def test_a_session_in_the_query_string_is_refused_4401(self, db):
        tess = _tech_at_a_shop(db)
        sid = _bike_session(db, tess)
        c = client(db)
        token = login(c, "tess")
        assert _close_code(c, f"/v1/live/{sid}?api_key={token}") == WS_CLOSE_INVALID_KEY

    def test_the_query_string_session_is_refused_even_beside_a_good_subprotocol(self, db):
        tess = _tech_at_a_shop(db)
        sid = _bike_session(db, tess)
        c = client(db)
        token = login(c, "tess")
        assert _close_code(c, f"/v1/live/{sid}?api_key={token}",
                           subprotocols=[f"bearer.{token}"]) == WS_CLOSE_INVALID_KEY

    def test_the_control_a_key_keeps_the_query_parameter(self, db):
        uid = make_user(db, "kim")
        make_sub(db, uid, "individual")
        sid = _bike_session(db, uid)
        c = client(db)
        with c.websocket_connect(f"/v1/live/{sid}?api_key={make_key(db, uid)}") as ws:
            assert "rpm" in ws.receive_json()

    def test_no_subscription_closes_4402_as_for_a_key(self, db):
        uid = make_user(db, "loner")
        sid = _bike_session(db, uid)
        c = client(db)
        token = login(c, "loner")
        assert _close_code(c, f"/v1/live/{sid}", subprotocols=[f"bearer.{token}"]
                           ) == WS_CLOSE_SUBSCRIPTION_REQUIRED

    def test_another_users_session_closes_4404_as_for_a_key(self, db):
        _tech_at_a_shop(db)
        other_bike = _bike_session(db, make_user(db, "other"))
        c = client(db)
        token = login(c, "tess")
        assert _close_code(c, f"/v1/live/{other_bike}", subprotocols=[f"bearer.{token}"]
                           ) == WS_CLOSE_SESSION_NOT_FOUND

    def test_a_revoked_session_closes_4401(self, db):
        tess = _tech_at_a_shop(db)
        sid = _bike_session(db, tess)
        c = client(db)
        token = login(c, "tess")
        c.post("/v1/auth/logout", headers=auth(token))
        assert _close_code(c, f"/v1/live/{sid}", subprotocols=[f"bearer.{token}"]
                           ) == WS_CLOSE_INVALID_KEY

    def test_resolve_tier_is_the_function_it_called(self, db, monkeypatch):
        tess = _tech_at_a_shop(db)
        sid = _bike_session(db, tess)
        calls = []
        real = live_mod.resolve_tier
        monkeypatch.setattr(live_mod, "resolve_tier",
                            lambda cred, db_path=None: calls.append(cred.kind) or real(cred, db_path))
        c = client(db)
        token = login(c, "tess")
        with c.websocket_connect(f"/v1/live/{sid}", subprotocols=[f"bearer.{token}"]) as ws:
            ws.receive_json()
        assert calls == ["session"]
        assert not hasattr(live_mod, "_resolve_tier")


def _session_text_in(records) -> list[str]:
    """Every captured record whose message or arguments carry "mds_"."""
    out = []
    for r in records:
        text = f"{r.msg} {r.args!r} {r.getMessage()}"
        if "mds_" in text:
            out.append(f"{r.name}: {text}")
    return out


class TestNoSessionTokenInTheLogsK56:
    def _capture(self, caplog):
        caplog.set_level(logging.DEBUG)
        for name in LOGGERS:
            caplog.set_level(logging.DEBUG, logger=name)

    def test_login_rest_socket_and_refused_query_log_no_token(self, db, caplog):
        self._capture(caplog)
        tess = _tech_at_a_shop(db)
        sid = _bike_session(db, tess)
        c = client(db)
        token = login(c, "tess")
        assert c.get("/v1/shop/profile/list", headers=auth(token)).status_code == 200
        with c.websocket_connect(f"/v1/live/{sid}", subprotocols=[f"bearer.{token}"]) as ws:
            ws.receive_json()
        assert _close_code(c, f"/v1/live/{sid}?api_key={token}") == WS_CLOSE_INVALID_KEY
        assert c.post("/v1/auth/login", json={"username": "tess", "password": token}
                      ).status_code == 401
        names = {r.name for r in caplog.records}
        assert "motodiag.api.access" in names and "motodiag.api.routes.auth" in names
        assert _session_text_in(caplog.records) == []

    def test_the_control_a_planted_line_is_seen(self, db, caplog):
        self._capture(caplog)
        _tech_at_a_shop(db)
        token = login(client(db), "tess")
        logging.getLogger("motodiag.api.routes.live").info("opened with %s", token)
        assert len(_session_text_in(caplog.records)) == 1
