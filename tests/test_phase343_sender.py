"""Phase 343, item 4: the envelope, the queue, its thread and the wire."""

from __future__ import annotations

import http.client
import http.server
import json
import logging
import threading
import time

import pytest

from motodiag.core.config import Settings
from motodiag.telemetry.dsn import parse_dsn
from motodiag.telemetry.envelope import envelope
from motodiag.telemetry.events import message_event
from motodiag.telemetry.sender import (
    CONTENT_TYPE,
    NullSender,
    Sender,
    make_sender,
    urllib_transport,
)
from tests.support.phase343 import DSN_TEXT, PLANTED_KEY, FakeTransport

CTX = {"release": "9.9.9", "environment": "test", "server_name": "h"}
DSN = parse_dsn(DSN_TEXT)


def _event(text: str = "hello") -> dict:
    return message_event(text, clock=lambda: "T", **CTX)


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def senders():
    made: list[Sender] = []

    def make(transport, **kw) -> Sender:
        s = Sender(DSN, transport=transport, **kw)
        made.append(s)
        return s

    yield make
    for s in made:
        s._stop.set()
    for s in made:
        s._thread.join(2)


class TestTheEnvelope:
    def _lines(self, ev: dict) -> list[bytes]:
        raw = envelope(ev, DSN, "2026-11-01T00:00:00.000+00:00")
        assert raw.endswith(b"\n")
        return raw.split(b"\n")[:-1]

    def test_three_lines_parse_back(self):
        ev = _event()
        header, item, payload = self._lines(ev)
        h = json.loads(header)
        assert h == {"event_id": ev["event_id"],
                     "sent_at": "2026-11-01T00:00:00.000+00:00",
                     "dsn": DSN_TEXT}
        assert json.loads(item) == {"type": "event", "length": len(payload)}
        assert json.loads(payload) == ev

    def test_the_length_is_bytes_with_non_ascii(self):
        ev = _event("Kawasaki Z900 — fault ✓ ü")
        _, item, payload = self._lines(ev)
        assert json.loads(item)["length"] == len(payload)
        assert len(payload) > len(payload.decode("utf-8"))

    def test_a_transaction_item(self):
        ev = {"event_id": "a" * 32, "type": "transaction"}
        _, item, _ = self._lines(ev)
        assert json.loads(item)["type"] == "transaction"


class TestTheSender:
    def test_the_fake_receives_auth_and_content_type(self, senders):
        fake = FakeTransport()
        s = senders(fake)
        assert s.capture(_event()) is True
        assert s.flush(5) is True
        url, headers, body = fake.requests[0]
        assert url == DSN.envelope_url
        assert headers["Content-Type"] == CONTENT_TYPE
        assert headers["X-Sentry-Auth"].endswith(f"sentry_key={PLANTED_KEY}")
        assert s.sent == 1 and s.last_status == 200

    @pytest.mark.parametrize("rate, roll, expected", [
        (0.1, 0.05, True), (0.1, 0.5, False), (0.0, 0.0, False),
        (0.0, 0.5, False), (1.0, 0.0, True), (1.0, 0.999999, True),
    ])
    def test_sampled(self, senders, rate, roll, expected):
        s = senders(FakeTransport(), traces_sample_rate=rate, rng=lambda: roll)
        assert s.sampled() is expected

    def test_a_429_pauses_and_the_clock_ends_it(self, senders):
        clock = _Clock()
        fake = FakeTransport(status=429, reason="Too Many Requests",
                             headers={"Retry-After": "3"})
        s = senders(fake, clock=clock)
        assert s.capture(_event()) is True
        assert s.flush(5)
        assert s.last_status == 429
        assert s.capture(_event()) is False
        assert s.dropped == 1
        clock.now += 2.9
        assert s.capture(_event()) is False and s.dropped == 2
        fake.status = 200
        clock.now += 0.2
        assert s.capture(_event()) is True
        assert s.flush(5) and s.sent == 1 and len(fake.requests) == 2

    def test_a_429_without_a_number_pauses_at_most_60(self, senders):
        clock = _Clock()
        s = senders(FakeTransport(status=429, headers={"Retry-After": "soon"}),
                    clock=clock)
        s.capture(_event())
        s.flush(5)
        clock.now += 59
        assert s.capture(_event()) is False
        clock.now += 1.5
        assert s.capture(_event()) is True

    def test_a_full_queue_drops_and_never_blocks(self, senders):
        fake = FakeTransport()
        fake.hold()
        s = senders(fake, queue_size=100)
        s.capture(_event("first"))
        assert fake.entered.wait(5)
        start = time.perf_counter()
        results = [s.capture(_event()) for _ in range(150)]
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1
        assert results.count(True) == 100 and s.dropped == 50
        assert s.flush(0.05) is False
        fake.release.set()
        assert s.flush(10) is True
        assert len(fake.requests) == 101

    def test_a_raising_transport_breaks_nothing_and_logs_once(self, senders, caplog):
        fake = FakeTransport()
        fake.raises = OSError("connection refused")
        s = senders(fake, clock=_Clock())
        caplog.set_level(logging.DEBUG, logger="motodiag.telemetry")
        for _ in range(3):
            assert s.capture(_event()) is True
        assert s.flush(5)
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "OSError" in warnings[0].getMessage()
        assert PLANTED_KEY not in caplog.text
        assert s.failed == 3 and s.last_error == "OSError"

    def test_a_broken_http_answer_is_a_failed_send(self, senders):
        fake = FakeTransport()
        fake.raises = http.client.RemoteDisconnected("closed")
        s = senders(fake, clock=_Clock())
        s.capture(_event())
        assert s.flush(5)
        assert s.failed == 1 and s.last_error == "RemoteDisconnected"
        fake.raises = http.client.IncompleteRead(b"")
        s.capture(_event())
        assert s.flush(5)
        assert s.failed == 2 and s.last_error == "IncompleteRead"

    def test_a_programming_error_is_not_swallowed(self, senders, monkeypatch):
        seen: list[BaseException] = []
        monkeypatch.setattr(threading, "excepthook",
                            lambda args: seen.append(args.exc_value))
        fake = FakeTransport()
        fake.raises = TypeError("bad header")
        s = senders(fake, clock=_Clock())
        s.capture(_event())
        s._thread.join(5)
        assert [type(e) for e in seen] == [TypeError]
        assert s.failed == 0 and s.last_error is None

    def test_a_non_2xx_is_logged_naming_status_and_host(self, senders, caplog):
        s = senders(FakeTransport(status=401, reason="Unauthorized"), clock=_Clock())
        caplog.set_level(logging.WARNING, logger="motodiag.telemetry")
        s.capture(_event())
        s.flush(5)
        assert "401" in caplog.text and DSN.host in caplog.text
        assert PLANTED_KEY not in caplog.text

    def test_close_stops_the_thread(self, senders):
        s = senders(FakeTransport())
        s.capture(_event())
        s.close()
        assert not s._thread.is_alive()
        assert s.capture(_event()) is False
        s.close()


class TestTheNullSender:
    def test_no_dsn_gives_a_null_sender_and_no_thread(self):
        before = threading.active_count()
        s = make_sender(Settings(sentry_dsn=""))
        assert isinstance(s, NullSender) and s.enabled is False
        assert threading.active_count() == before
        assert s.capture(_event()) is False and s.sampled() is False
        assert s.flush() is True and s.close() is None

    def test_a_bad_dsn_is_logged_once_and_is_off(self, caplog):
        caplog.set_level(logging.ERROR, logger="motodiag.telemetry")
        s = make_sender(Settings(sentry_dsn=f"https://{PLANTED_KEY}@host.example/"))
        assert isinstance(s, NullSender)
        assert len(caplog.records) == 1
        assert "project id" in caplog.text and PLANTED_KEY not in caplog.text

    def test_a_good_dsn_gives_a_sender(self):
        s = make_sender(Settings(sentry_dsn=DSN_TEXT, telemetry_traces_sample_rate=0.5,
                                 telemetry_environment="shop"),
                        transport=FakeTransport())
        try:
            assert isinstance(s, Sender) and s.enabled
            assert s.traces_sample_rate == 0.5 and s.environment == "shop"
        finally:
            s.close()


class TestTheDefaultTransport:
    def test_urllib_round_trip_on_loopback(self):
        got: dict = {}

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                n = int(self.headers["Content-Length"])
                got["body"] = self.rfile.read(n)
                got["auth"] = self.headers["X-Sentry-Auth"]
                got["path"] = self.path
                status = 200 if self.path.endswith("/envelope/") else 403
                self.send_response(status)
                self.send_header("Retry-After", "7")
                self.end_headers()
                self.wfile.write(b'{"id":"x"}')

            def log_message(self, *a):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            dsn = parse_dsn(f"http://{PLANTED_KEY}@127.0.0.1:{server.server_address[1]}/5")
            body = envelope(_event(), dsn, "T")
            status, reason, headers = urllib_transport(
                dsn.envelope_url, {"X-Sentry-Auth": dsn.auth_header,
                                   "Content-Type": CONTENT_TYPE}, body, timeout=5)
            assert status == 200 and headers["Retry-After"] == "7"
            assert got["body"] == body and got["path"] == "/api/5/envelope/"
            assert PLANTED_KEY in got["auth"]
            status, _, _ = urllib_transport(
                dsn.envelope_url.replace("envelope/", "other"), {}, b"x", timeout=5)
            assert status == 403
        finally:
            server.shutdown()
            server.server_close()
