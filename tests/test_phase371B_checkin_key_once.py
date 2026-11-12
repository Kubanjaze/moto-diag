"""Phase 371B — the alarm's check-in sends the Sentry key once (F273).

From live payments' first night (2026-11-11), Sentry refused every
check-in with 401: the check-in carried the DSN's key in its URL and again
in ``X-Sentry-Auth``, and Sentry's ingest server, Relay, refuses a request
that carries the key twice. 371's tests could not see it, because their
transport took any post.

The stand-in is a server on loopback with Relay's rule, as
``auth_from_parts`` applies it (relay-server/src/extractors/request_meta.rs,
read 2026-11-11). It looks for the key in ``X-Sentry-Auth``, then in
``Authorization``, then in a query holding ``sentry_``, then in the path.
A second source gets 401 and Relay's words. None gets 401. One is
accepted: 202 on the cron route, 200 on the envelope route.

The check-in goes through the real ``urllib_transport``. The controls show
the stand-in refusing 371's request and a request with no key, and
accepting the error reports, which send the header alone to an address
with no key in it.
"""

from __future__ import annotations

import http.server
import json
import threading
import urllib.error
import urllib.request
from urllib.parse import urlsplit

import pytest

from motodiag.telemetry import monitor
from motodiag.telemetry.dsn import parse_dsn
from motodiag.telemetry.events import message_event
from motodiag.telemetry.sender import Sender

KEY = "planted371BpublicKey"
SLUG = "motodiag-payments-feed"
PROJECT = "42"
MULTIPLE = "multiple authorization payloads detected"
MISSING = "missing authorization information"


def _sentry_scheme(value: str | None) -> bool:
    return value is not None and value[:7].lower() == "sentry "


class RelayStandIn(http.server.BaseHTTPRequestHandler):
    """Relay's rule for where the key may come from; each post is kept on the server."""

    def do_POST(self):  # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        url = urlsplit(self.path)
        parts = [p for p in url.path.split("/") if p]
        cron = len(parts) in (4, 5) and parts[0] == "api" and parts[2] == "cron"
        envelope = parts[-1:] == ["envelope"]
        sources = []
        if _sentry_scheme(self.headers.get("X-Sentry-Auth")):
            sources.append("x-sentry-auth")
        if _sentry_scheme(self.headers.get("Authorization")):
            sources.append("authorization")
        if "sentry_" in url.query:
            sources.append("query")
        if cron and len(parts) == 5:
            sources.append("path")
        self.server.posts.append({"path": url.path, "sources": sources, "body": body})
        if not (cron or envelope):
            self._answer(404, None)
        elif len(sources) > 1:
            self._answer(401, {"detail": MULTIPLE})
        elif not sources:
            self._answer(401, {"detail": MISSING})
        elif cron:
            self._answer(202, None)
        else:
            self._answer(200, {"id": "0" * 32})

    def _answer(self, status: int, payload: dict | None) -> None:
        raw = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


@pytest.fixture
def relay():
    server = http.server.HTTPServer(("127.0.0.1", 0), RelayStandIn)
    server.posts = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def _dsn(server):
    return parse_dsn(f"http://{KEY}@127.0.0.1:{server.server_address[1]}/{PROJECT}")


def _post(url: str, headers: dict) -> tuple[int, dict]:
    request = urllib.request.Request(url, data=b"{}", headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, {}
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}")


def test_the_check_in_sends_the_key_once_and_is_accepted(relay):
    assert monitor.checkin(_dsn(relay), SLUG, interval_minutes=5) is True
    (post,) = relay.posts
    assert post["path"] == f"/api/{PROJECT}/cron/{SLUG}/{KEY}/"
    assert post["sources"] == ["path"]
    sent = json.loads(post["body"])
    assert sent["status"] == "ok"
    assert sent["monitor_config"]["checkin_margin"] == monitor.MARGIN_MINUTES


def test_control_371s_request_with_the_key_twice_is_refused(relay):
    dsn = _dsn(relay)
    status, answer = _post(monitor.checkin_url(dsn, SLUG),
                           {"Content-Type": "application/json",
                            "X-Sentry-Auth": dsn.auth_header})
    assert (status, answer) == (401, {"detail": MULTIPLE})
    assert relay.posts[-1]["sources"] == ["x-sentry-auth", "path"]


def test_control_a_request_with_no_key_is_refused(relay):
    url = monitor.checkin_url(_dsn(relay), SLUG).replace(f"{KEY}/", "")
    status, answer = _post(url, {"Content-Type": "application/json"})
    assert (status, answer) == (401, {"detail": MISSING})
    assert relay.posts[-1]["sources"] == []


def test_the_error_reports_send_the_header_alone_and_are_accepted(relay):
    sender = Sender(_dsn(relay), environment="test", server_name="bench")
    try:
        assert sender.capture(message_event("371B", release="t", environment="test",
                                            server_name="bench")) is True
        assert sender.flush(10) is True
    finally:
        sender.close()
    assert sender.last_status == 200
    (post,) = relay.posts
    assert post["path"] == f"/api/{PROJECT}/envelope/"
    assert post["sources"] == ["x-sentry-auth"]
