"""Phase 343, item 5: the middleware, its place in the stack, and the crash
sent from ``_unhandled_handler``."""

from __future__ import annotations

import ast
import inspect
import shutil
import threading
import time

import pytest
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.api import telemetry as api_telemetry
from motodiag.api.middleware import (
    AccessLogMiddleware,
    AuditMiddleware,
    RateLimitMiddleware,
    RequestIdMiddleware,
)
from motodiag.api.telemetry import TelemetryMiddleware, capture_crash
from motodiag.core.config import reset_settings
from motodiag.core.database import init_db
from motodiag.shop import WorkOrderNotFoundError
from motodiag.telemetry.dsn import parse_dsn
from motodiag.telemetry.sender import NullSender, Sender
from tests.support.phase343 import DSN_TEXT, FakeSender, FakeTransport

REQUEST_ID_HEADER = "X-Request-ID"


@pytest.fixture(scope="module")
def template_db(tmp_path_factory):
    """Built once: `init_db` costs about two seconds."""
    path = tmp_path_factory.mktemp("phase343") / "template.db"
    init_db(str(path))
    return path


@pytest.fixture
def api_db(template_db, tmp_path, monkeypatch):
    path = str(tmp_path / "phase343_api.db")
    shutil.copyfile(template_db, path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.delenv("MOTODIAG_SENTRY_DSN", raising=False)
    reset_settings()
    yield path
    reset_settings()


def _bench_app(api_db):
    app = create_app(db_path_override=api_db)
    bench = APIRouter(prefix="/_bench")

    @bench.get("/boom/{item_id}")
    def boom(item_id: int):
        raise RuntimeError(f"unexpected for {item_id}")

    @bench.get("/notfound")
    def notfound():
        raise WorkOrderNotFoundError("wo id=404")

    @bench.get("/number/{n}")
    def number(n: int):
        return {"n": n}

    @bench.get("/slow/{item_id}")
    def slow(item_id: int):
        time.sleep(0.05)
        return {"ok": item_id}

    app.include_router(bench)
    return app


def _client(api_db, sampled: bool = True):
    app = _bench_app(api_db)
    fake = FakeSender(sampled=sampled)
    app.state.telemetry = fake
    return TestClient(app, raise_server_exceptions=False), fake, app


class TestThePlaceInTheStack:
    def test_inside_the_request_scoped_four_and_outside_cors(self, api_db):
        stack = [m.cls for m in create_app(db_path_override=api_db).user_middleware]
        t = stack.index(TelemetryMiddleware)
        assert stack.index(CORSMiddleware) > t
        for outer in (RequestIdMiddleware, RateLimitMiddleware,
                      AccessLogMiddleware, AuditMiddleware):
            assert stack.index(outer) < t, outer
        assert stack[t - 1] is AuditMiddleware


class TestTheCrash:
    def test_one_error_event_with_the_request_id_and_template(self, api_db):
        client, fake, _ = _client(api_db, sampled=False)
        r = client.get("/_bench/boom/98765")
        assert r.status_code == 500
        body = r.json()
        assert body.get("detail") is None and "Traceback" not in r.text
        assert body["title"] == "Internal server error"
        [event] = fake.errors()
        rid = r.headers.get(REQUEST_ID_HEADER) or body["request_id"]
        assert event["tags"]["request_id"] == rid == body["request_id"]
        assert event["request"]["url"] == "/_bench/boom/{item_id}"
        assert "98765" not in event["request"]["url"]
        assert event["exception"]["values"][0]["type"] == "RuntimeError"
        assert fake.transactions() == []

    def test_the_crash_is_also_a_500_transaction(self, api_db):
        client, fake, _ = _client(api_db)
        client.get("/_bench/boom/1")
        [tx] = fake.transactions()
        assert tx["tags"]["status"] == "500"
        assert tx["contexts"]["trace"]["status"] == "internal_error"
        assert len(fake.errors()) == 1

    def test_control_without_the_catch_no_transaction(self, api_db, monkeypatch):
        async def no_catch(self, request, call_next):
            sender = api_telemetry._sender(request)
            response = await call_next(request)
            api_telemetry._time(request, sender, response.status_code, 0.0, 0.0)
            return response

        monkeypatch.setattr(TelemetryMiddleware, "dispatch", no_catch)
        client, fake, _ = _client(api_db)
        client.get("/_bench/boom/1")
        assert fake.transactions() == []

    @pytest.mark.parametrize("path, status", [("/_bench/notfound", 404),
                                              ("/_bench/number/abc", 422)])
    def test_a_mapped_error_sends_no_error_event(self, api_db, path, status):
        client, fake, _ = _client(api_db)
        assert client.get(path).status_code == status
        assert fake.errors() == []
        assert len(fake.transactions()) == 1

    def test_control_a_404_captured_on_purpose_is_seen(self, api_db):
        client, fake, app = _client(api_db)

        async def capturing(request, exc):
            from fastapi.responses import JSONResponse
            capture_crash(request, exc)
            return JSONResponse({"status": 404}, status_code=404)

        app.add_exception_handler(WorkOrderNotFoundError, capturing)
        assert client.get("/_bench/notfound").status_code == 404
        assert fake.errors() != []

    def test_without_install_the_500_path_is_as_today(self, api_db):
        client, _, app = _client(api_db)
        del app.state.telemetry
        r = client.get("/_bench/boom/1")
        assert r.status_code == 500 and r.json().get("detail") is None


class TestTheTransactions:
    def test_a_sampled_request_covers_the_route_and_names_the_template(self, api_db):
        client, fake, _ = _client(api_db)
        r = client.get("/_bench/slow/4242")
        assert r.status_code == 200
        [tx] = fake.transactions()
        assert tx["timestamp"] - tx["start_timestamp"] >= 0.05
        assert tx["transaction"] == "GET /_bench/slow/{item_id}"
        assert "4242" not in tx["transaction"]
        assert tx["tags"]["request_id"] == r.headers[REQUEST_ID_HEADER]
        assert tx["contexts"]["trace"]["status"] == "ok"

    def test_an_unsampled_request_sends_none(self, api_db):
        client, fake, _ = _client(api_db, sampled=False)
        client.get("/_bench/slow/1")
        assert fake.events == []

    @pytest.mark.parametrize("sampled", [True, False])
    def test_healthz_sends_none(self, api_db, sampled):
        client, fake, _ = _client(api_db, sampled=sampled)
        assert client.get("/healthz").status_code == 200
        assert fake.events == []

    def test_an_unmatched_path(self, api_db):
        client, fake, _ = _client(api_db)
        assert client.get("/no/such/9999").status_code == 404
        [tx] = fake.transactions()
        assert tx["transaction"] == "GET unmatched"

    def test_the_sender_is_read_at_request_time(self, api_db):
        client, first, app = _client(api_db)
        client.get("/_bench/slow/1")
        second = FakeSender()
        app.state.telemetry = second
        client.get("/_bench/slow/1")
        assert len(first.transactions()) == 1 and len(second.transactions()) == 1


PREFLIGHT = {"Origin": "http://localhost:3000",
             "Access-Control-Request-Method": "GET"}


class TestThePreflight:
    def test_cors_answers_and_nothing_is_sent(self, api_db):
        client, fake, _ = _client(api_db)
        r = client.options("/_bench/slow/1", headers=PREFLIGHT)
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert fake.events == []

    def test_control_without_the_skip_a_preflight_is_sent(self, api_db, monkeypatch):
        monkeypatch.setattr(api_telemetry, "skipped",
                            lambda request: request.url.path == "/healthz")
        client, fake, _ = _client(api_db)
        assert client.options("/_bench/slow/1", headers=PREFLIGHT).status_code == 200
        assert [tx["transaction"] for tx in fake.transactions()] == ["OPTIONS unmatched"]


class TestNoDsn:
    def test_off_with_no_thread(self, api_db):
        before = threading.active_count()
        app = create_app(db_path_override=api_db)
        assert app.state.telemetry.enabled is False
        assert threading.active_count() == before
        r = TestClient(app, raise_server_exceptions=False).get("/healthz")
        assert r.status_code == 200

    def test_the_ready_line_says_off(self, api_db, caplog):
        caplog.set_level("INFO", logger="motodiag.api")
        create_app(db_path_override=api_db)
        assert "telemetry=off" in caplog.text


def _names_read_from_sender() -> set[str]:
    """Every ``sender.<name>`` in ``motodiag.api.telemetry``'s source."""
    tree = ast.parse(inspect.getsource(api_telemetry))
    return {node.attr for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name) and node.value.id == "sender"}


class TestTheDoubleMatchesTheSender:
    def test_the_names_the_api_reads(self):
        assert _names_read_from_sender() == {
            "enabled", "sampled", "capture", "release", "environment",
            "server_name", "dsn"}

    @pytest.mark.parametrize("name", sorted(_names_read_from_sender() - {"dsn"}))
    def test_the_fake_has_each_as_the_real_sender_does(self, name):
        real = Sender(parse_dsn(DSN_TEXT), transport=FakeTransport())
        try:
            for other in (FakeSender(), NullSender()):
                assert hasattr(other, name), (type(other).__name__, name)
                assert callable(getattr(other, name)) == callable(getattr(real, name))
        finally:
            real.close()

    def test_a_crash_through_a_real_sender(self, api_db):
        app = _bench_app(api_db)
        transport = FakeTransport()
        real = Sender(parse_dsn(DSN_TEXT), transport=transport, rng=lambda: 0.0,
                      release="motodiag@test", environment="test",
                      server_name="test-host")
        app.state.telemetry = real
        try:
            client = TestClient(app, raise_server_exceptions=False)
            r = client.get("/_bench/boom/98765")
            assert r.status_code == 500
            assert real.flush(5) and transport.wait_for(2)
        finally:
            real.close()
        payloads = transport.payloads()
        [error] = [p for p in payloads if p.get("type") != "transaction"]
        [tx] = [p for p in payloads if p.get("type") == "transaction"]
        assert error["tags"]["request_id"] == r.json()["request_id"]
        assert error["request"]["url"] == "/_bench/boom/{item_id}"
        assert error["release"] == tx["release"] == "motodiag@test"
        assert error["server_name"] == "test-host"
        assert tx["tags"]["status"] == "500"
