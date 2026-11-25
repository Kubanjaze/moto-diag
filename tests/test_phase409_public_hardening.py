"""Phase 409 prebuild: the server made ready for the public internet.

What an anonymous caller on the internet reaches, and the guards that
hold it:

- :class:`TestAnonymousSurface` — the exact list of routes that answer
  without a credential, so a new one cannot appear unnoticed.
- :class:`TestLoginThrottle` — failed logins per name and address, 429
  with Retry-After, a good login clears only its own pair.
- :class:`TestSecurityHeaders` — nosniff, no framing, no referrer on
  every answer; HSTS only over https (as uvicorn's trusted proxy sets it).
- :class:`TestAllowedHosts` — off by default; on, any other Host is 400.
- :class:`TestApiDocsSwitch` — on by default; off, the three pages 404.
- :class:`TestBodySizeLimit` — a body over 1 MiB that is not a file
  upload is 413 before a route reads it.
- :class:`TestHealthzLeaksNothing` — a broken database is named in the
  log, never in the answer.
- :class:`TestProxyClientAddress` — behind a proxy on loopback (cloudflared,
  ``tailscale serve``), each caller is counted by its own address.

A scratch database per test, as Phase 303's tests make it. No test reads
the live database.
"""

from __future__ import annotations

import logging

import pytest
from fastapi.routing import APIRoute, APIWebSocketRoute
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.core.config import reset_settings
from tests.support.phase303 import PASSWORD, make_user, new_db

# Routes that answer with no credential. Each line is a decision: adding
# one here is a change a reviewer reads.
ANONYMOUS_ROUTES = {
    ("GET", "/healthz"),
    ("GET", "/v1/version"),
    ("POST", "/v1/auth/login"),
    ("GET", "/v1/terms"),  # the current terms; a key, if sent, adds acceptance
    ("POST", "/v1/billing/webhooks/stripe"),  # Stripe's signature checks it
    ("GET", "/v1/share/{token}"),  # off on live (K74); the token is the key
}
AUTH_DEPS = {"require_api_key", "get_current_user"}


def _dep_names(dependant, acc):
    for sub in dependant.dependencies:
        acc.add(getattr(sub.call, "__name__", ""))
        qual = getattr(sub.call, "__qualname__", "")
        if qual.startswith("require_tier"):
            acc.add("get_current_user")
        _dep_names(sub, acc)
    return acc


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = new_db(tmp_path, monkeypatch)
    yield path
    reset_settings()


def _client(db_path):
    return TestClient(create_app(db_path_override=db_path),
                      raise_server_exceptions=False)


class TestAnonymousSurface:

    def test_only_the_named_routes_answer_without_a_credential(self, db):
        app = create_app(db_path_override=db)
        open_routes = set()
        for r in app.routes:
            if isinstance(r, APIRoute):
                if not (_dep_names(r.dependant, set()) & AUTH_DEPS):
                    for m in r.methods:
                        open_routes.add((m, r.path))
        assert open_routes == ANONYMOUS_ROUTES

    def test_the_live_socket_checks_its_own_key(self, db):
        app = create_app(db_path_override=db)
        ws = [r for r in app.routes if isinstance(r, APIWebSocketRoute)]
        assert [r.path for r in ws] == ["/v1/live/{session_id}"]
        c = _client(db)
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect) as e:
            with c.websocket_connect("/v1/live/1") as s:
                s.receive_text()
        assert 4000 <= e.value.code < 5000

    def test_shop_smoke_route_refuses_anonymous(self, db):
        r = _client(db).get("/v1/shops/1")
        assert r.status_code == 401


class TestLoginThrottle:

    def _fail(self, c, name="mech", ip_client=None, n=1):
        codes = []
        for _ in range(n):
            r = (ip_client or c).post(
                "/v1/auth/login", json={"username": name, "password": "nope"})
            codes.append(r.status_code)
        return codes

    def test_ten_failures_then_429_even_with_the_right_password(
            self, db, monkeypatch):
        make_user(db, "mech")
        c = _client(db)
        assert self._fail(c, n=10) == [401] * 10
        r = c.post("/v1/auth/login",
                   json={"username": "mech", "password": PASSWORD})
        assert r.status_code == 429
        assert int(r.headers["Retry-After"]) >= 1
        assert r.json()["type"].endswith("rate-limit-exceeded")
        assert "token" not in r.text

    def test_good_login_clears_its_own_pair(self, db):
        make_user(db, "mech")
        c = _client(db)
        assert self._fail(c, n=9) == [401] * 9
        r = c.post("/v1/auth/login",
                   json={"username": "mech", "password": PASSWORD})
        assert r.status_code == 200
        assert self._fail(c, n=9) == [401] * 9

    def test_other_names_are_not_held(self, db):
        make_user(db, "mech")
        make_user(db, "owner")
        c = _client(db)
        self._fail(c, "mech", n=10)
        r = c.post("/v1/auth/login",
                   json={"username": "owner", "password": PASSWORD})
        assert r.status_code == 200

    def test_name_case_does_not_reset_the_count(self, db):
        make_user(db, "mech")
        c = _client(db)
        self._fail(c, "mech", n=5)
        self._fail(c, "MECH", n=5)
        assert self._fail(c, "Mech") == [429]

    def test_window_passes_and_the_name_answers_again(self):
        from motodiag.auth.login_throttle import (
            LoginThrottle,
            LoginThrottledError,
        )
        from motodiag.core.config import Settings
        now = [1_700_000_000.0]
        t = LoginThrottle(Settings(login_failure_limit=2,
                                   login_failure_window_s=60),
                          clock=lambda: now[0])
        t.record_failure("a", "1.1.1.1")
        t.record_failure("a", "1.1.1.1")
        with pytest.raises(LoginThrottledError) as e:
            t.check("a", "1.1.1.1")
        assert 1 <= e.value.retry_after_s <= 61
        now[0] += 61
        t.check("a", "1.1.1.1")

    def test_many_addresses_hold_the_name_at_five_times(self):
        from motodiag.auth.login_throttle import (
            LoginThrottle,
            LoginThrottledError,
        )
        from motodiag.core.config import Settings
        t = LoginThrottle(Settings(login_failure_limit=2,
                                   login_failure_window_s=60),
                          clock=lambda: 1_700_000_000.0)
        for i in range(10):
            t.record_failure("a", f"10.0.0.{i}")
        with pytest.raises(LoginThrottledError):
            t.check("a", "10.0.0.99")
        # A success from one address does not clear the name's total.
        t.record_success("a", "10.0.0.99")
        with pytest.raises(LoginThrottledError):
            t.check("a", "10.0.0.99")


class TestSecurityHeaders:

    def test_on_every_answer_including_errors(self, db):
        c = _client(db)
        for path in ("/healthz", "/v1/shops/1", "/no-such-route"):
            r = c.get(path)
            assert r.headers["X-Content-Type-Options"] == "nosniff"
            assert r.headers["X-Frame-Options"] == "DENY"
            assert r.headers["Referrer-Policy"] == "no-referrer"

    def test_hsts_only_over_https(self, db):
        app = create_app(db_path_override=db)
        assert "Strict-Transport-Security" not in (
            TestClient(app).get("/healthz").headers)
        https = TestClient(app, base_url="https://testserver")
        assert https.get("/healthz").headers[
            "Strict-Transport-Security"].startswith("max-age=")

    def test_switch_off(self, db, monkeypatch):
        monkeypatch.setenv("MOTODIAG_SECURITY_HEADERS_ENABLED", "false")
        reset_settings()
        r = _client(db).get("/healthz")
        assert "X-Frame-Options" not in r.headers


class TestAllowedHosts:

    def test_off_by_default(self, db):
        c = TestClient(create_app(db_path_override=db),
                       base_url="http://anything.example")
        assert c.get("/healthz").status_code == 200

    def test_on_other_hosts_are_400(self, db, monkeypatch):
        monkeypatch.setenv("MOTODIAG_API_ALLOWED_HOSTS",
                           "api.example.com, 127.0.0.1,localhost")
        reset_settings()
        app = create_app(db_path_override=db)
        ok = TestClient(app, base_url="https://api.example.com")
        assert ok.get("/healthz").status_code == 200
        local = TestClient(app, base_url="http://127.0.0.1:8000")
        assert local.get("/healthz").status_code == 200
        bad = TestClient(app, base_url="http://evil.example")
        assert bad.get("/healthz").status_code == 400


class TestApiDocsSwitch:

    def test_on_by_default(self, db):
        c = _client(db)
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert c.get(path).status_code == 200

    def test_off_takes_all_three_away(self, db, monkeypatch):
        monkeypatch.setenv("MOTODIAG_API_DOCS_ENABLED", "false")
        reset_settings()
        c = _client(db)
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert c.get(path).status_code == 404
        assert c.get("/healthz").status_code == 200


class TestBodySizeLimit:

    def test_big_json_body_is_413_before_the_route(self, db):
        r = _client(db).post(
            "/v1/auth/login", content=b"{" + b" " * 1_100_000 + b"}",
            headers={"Content-Type": "application/json"})
        assert r.status_code == 413
        assert r.json()["type"].endswith("payload-too-large")
        assert "request_id" in r.json()

    def test_small_body_and_file_uploads_pass_through(self, db):
        c = _client(db)
        r = c.post("/v1/auth/login",
                   json={"username": "nobody", "password": "x"})
        assert r.status_code == 401
        # A multipart body over the limit reaches the route (401 here, as
        # no key was sent), whose own bound applies.
        r = c.post("/v1/shop/1/manuals",
                   files={"file": ("m.pdf", b"%PDF" + b"0" * 1_100_000,
                                   "application/pdf")})
        assert r.status_code != 413

    def test_switch_off(self, db, monkeypatch):
        monkeypatch.setenv("MOTODIAG_API_MAX_BODY_BYTES", "0")
        reset_settings()
        r = _client(db).post(
            "/v1/auth/login", content=b"{" + b" " * 1_100_000 + b"}",
            headers={"Content-Type": "application/json"})
        assert r.status_code != 413


class TestHealthzLeaksNothing:

    def test_broken_database_named_only_in_the_log(
            self, db, monkeypatch, caplog):
        from motodiag.api.routes import meta

        def boom(_path):
            raise OSError("unable to open /home/secret-dir/live.db")
        monkeypatch.setattr(meta, "get_schema_version", boom)
        with caplog.at_level(logging.WARNING):
            r = _client(db).get("/healthz")
        assert r.status_code == 503
        assert r.json() == {"status": "degraded", "schema_version": None,
                            "detail": "db unreachable"}
        assert "secret-dir" not in r.text
        assert "secret-dir" in caplog.text


class TestProxyClientAddress:
    """uvicorn's proxy headers (on by default, trusted from 127.0.0.1) give
    each caller behind cloudflared its own address. Pinned here because a
    tunnel run anywhere but loopback, or ``--no-proxy-headers``, would put
    every caller on the internet in one anonymous bucket."""

    def test_serve_keeps_uvicorns_proxy_headers(self, db):
        from unittest.mock import patch

        from click.testing import CliRunner

        from motodiag.cli.main import cli
        with patch("uvicorn.run") as mocked:
            r = CliRunner().invoke(cli, ["serve", "--skip-migrations"])
        assert r.exit_code == 0, r.output
        kwargs = mocked.call_args.kwargs
        assert kwargs.get("proxy_headers", True) is True
        assert kwargs.get("forwarded_allow_ips") in (None, "127.0.0.1")

    def test_each_forwarded_address_has_its_own_bucket(self, db, monkeypatch):
        from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

        from motodiag.auth.rate_limiter import reset_rate_limiter
        monkeypatch.setenv("MOTODIAG_RATE_LIMIT_ANONYMOUS_PER_MINUTE", "2")
        reset_settings()
        app = create_app(db_path_override=db)
        reset_rate_limiter(clock=lambda: 1_700_000_000.0)
        wrapped = ProxyHeadersMiddleware(app, trusted_hosts="127.0.0.1")
        c = TestClient(wrapped, client=("127.0.0.1", 50000))

        def get(ip):
            return c.get("/v1/terms",
                         headers={"X-Forwarded-For": ip}).status_code

        assert [get("203.0.113.7") for _ in range(3)] == [200, 200, 429]
        assert get("198.51.100.9") == 200
