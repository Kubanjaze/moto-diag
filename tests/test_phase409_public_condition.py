"""Phase 409: the launch check's ninth condition, the public address.

``public_condition`` reads three paths on the one https name the settings
hold: ``/healthz`` healthy, ``/docs`` 404 (the operator's answer 3) and
``/v1/shops/1`` 401 with no credential (answer 6, F309). Every case here
uses a stand-in: either ``check.public_status`` replaced, or a real https
server on loopback with a certificate the default trust store does not
know, for the certificate case. No case reaches the internet.
"""

from __future__ import annotations

import http.server
import ssl
import subprocess
import threading
import urllib.error

import pytest

from motodiag.core.config import Settings
from motodiag.launch import check

PUBLIC = "https://api.getmekno.com"
GOOD = {"/healthz": (200, b'{"status":"ok","schema_version":92}'),
        "/docs": (404, b'{"detail":"Not Found"}'),
        "/v1/shops/1": (401, b"{}")}


def _settings(url: str = PUBLIC) -> Settings:
    return Settings(public_base_url=url)


@pytest.fixture
def answers(monkeypatch):
    table = dict(GOOD)
    seen: list[str] = []

    def fake(settings, path, timeout=None):
        seen.append(path)
        got = table[path]
        if isinstance(got, BaseException):
            raise got
        return got

    monkeypatch.setattr(check, "public_status", fake)
    return table, seen


# ---------------------------------------------------------------- ready
def test_ready_when_the_three_answers_are_right(answers):
    c = check.public_condition(_settings())
    assert c.ready, c.detail
    assert c.name == "the public address answers over https"
    assert c.detail == ("certificate valid, healthy, API pages off, "
                        "a shop's details need signing in")
    assert answers[1] == ["/healthz", "/docs", "/v1/shops/1"]


def test_it_is_the_ninth_condition_after_210s_eight():
    import inspect
    src = inspect.getsource(check.run_conditions)
    order = ["schema_condition", "stripe_condition", "feed_condition", "backup_condition",
             "terms_condition", "reviewer_condition", "smoke_shop_condition",
             "disk_condition", "public_condition"]
    positions = [src.index(name + "(") for name in order]
    assert positions == sorted(positions)


# ---------------------------------------------------------------- not ready: the address
@pytest.mark.parametrize("url, reason", [
    ("", "no public address is set (MOTODIAG_PUBLIC_BASE_URL is empty)"),
    ("http://api.getmekno.com", "the public address is not https"),
    ("api.getmekno.com", "the public address is not https"),
    ("https://127.0.0.1:8000", "loopback, private or local name"),
    ("https://localhost", "loopback, private or local name"),
    ("https://192.168.1.20", "loopback, private or local name"),
    ("https://100.75.113.50", "loopback, private or local name"),
    ("https://desktop.local", "loopback, private or local name"),
])
def test_an_address_no_stranger_can_reach_is_not_ready(answers, url, reason):
    c = check.public_condition(_settings(url))
    assert not c.ready
    assert reason in c.detail
    assert answers[1] == [], "nothing is read for an address that cannot be public"


# ---------------------------------------------------------------- not ready: the answers
@pytest.mark.parametrize("path, answer, reason", [
    ("/healthz", (503, b'{"status":"degraded"}'), "/healthz answered 503, not healthy"),
    ("/healthz", (200, b'{"status":"degraded"}'), "/healthz answered 200, not healthy"),
    ("/healthz", (200, b"<html>not json</html>"), "/healthz answered 200, not healthy"),
    ("/docs", (200, b"<html>"), "the API pages are open (/docs answered 200, not 404)"),
    ("/v1/shops/1", (200, b'{"id":1}'),
     "a shop's details answer without signing in (/v1/shops/1 answered 200, not 401)"),
    ("/v1/shops/1", (400, b"Invalid host header"),
     "a shop's details answer without signing in (/v1/shops/1 answered 400, not 401)"),
])
def test_each_wrong_answer_is_its_own_reason(answers, path, answer, reason):
    answers[0][path] = answer
    c = check.public_condition(_settings())
    assert not c.ready
    assert c.detail == reason


def test_no_answer_is_did_not_answer(answers):
    answers[0]["/healthz"] = urllib.error.URLError(ConnectionRefusedError(111, "refused"))
    c = check.public_condition(_settings())
    assert (c.ready, c.detail) == (False, "the public address did not answer")


def test_a_timeout_is_did_not_answer(answers):
    answers[0]["/docs"] = TimeoutError("timed out")
    c = check.public_condition(_settings())
    assert (c.ready, c.detail) == (False, "the public address did not answer")


def test_a_certificate_failure_says_so(answers):
    answers[0]["/healthz"] = urllib.error.URLError(
        ssl.SSLCertVerificationError(1, "certificate verify failed"))
    c = check.public_condition(_settings())
    assert (c.ready, c.detail) == (False, "the certificate is not valid")


def test_no_detail_names_the_host(answers):
    for path, answer in (("/healthz", (503, b"{}")), ("/docs", (200, b"")),
                         ("/v1/shops/1", (200, b""))):
        answers[0].update(GOOD)
        answers[0][path] = answer
        c = check.public_condition(_settings())
        assert "getmekno" not in c.detail and "getmekno" not in c.line()
    answers[0].update(GOOD)
    assert "getmekno" not in check.public_condition(_settings()).line()


# ---------------------------------------------------------------- the reader
@pytest.mark.parametrize("url, path", [
    (PUBLIC, "/v1/auth/login"),
    (PUBLIC, "/healthz?x=1"),
    (PUBLIC, "//evil.example/healthz"),
    ("http://api.getmekno.com", "/healthz"),
    ("https://127.0.0.1:8000", "/healthz"),
    ("", "/healthz"),
])
def test_the_reader_refuses_anything_but_its_three_paths_on_the_public_name(url, path):
    with pytest.raises(check.NotPublicName):
        check.public_status(_settings(url), path)


def test_the_reader_reaches_only_the_settings_host(monkeypatch):
    opened: list[str] = []

    class Opener:
        def open(self, url, timeout=None):
            opened.append(url)
            raise urllib.error.URLError("stopped here")

    handlers: list = []

    def build(*hs):
        handlers.extend(hs)
        return Opener()

    monkeypatch.setattr(check.urllib.request, "build_opener", build)
    with pytest.raises(urllib.error.URLError):
        check.public_status(_settings("https://api.getmekno.com/some/path"), "/docs")
    assert opened == ["https://api.getmekno.com/docs"]
    proxies = [h for h in handlers if isinstance(h, check.urllib.request.ProxyHandler)]
    assert proxies and proxies[0].proxies == {}, "never through a proxy"


def test_an_error_status_is_an_answer_not_an_exception(monkeypatch):
    class Opener:
        def open(self, url, timeout=None):
            raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(check.urllib.request, "build_opener", lambda *h: Opener())
    code, _ = check.public_status(_settings(), "/v1/shops/1")
    assert code == 401


# ---------------------------------------------------------------- a real certificate failure
@pytest.fixture
def self_signed_https(tmp_path):
    key, cert = tmp_path / "key.pem", tmp_path / "cert.pem"
    made = subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
         "-subj", "/CN=127.0.0.1", "-keyout", str(key), "-out", str(cert)],
        capture_output=True)
    if made.returncode != 0:
        pytest.skip("openssl could not make a certificate here")

    class Healthy(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        def log_message(self, *a):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Healthy)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(cert), str(key))
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def test_a_certificate_the_trust_store_does_not_know_is_not_valid(self_signed_https,
                                                                   monkeypatch):
    """The real reader, the real default context, a real TLS server whose
    certificate nobody signed: refused as an invalid certificate. The host
    check is moved aside for this one case only, since the stand-in can only
    listen on loopback."""
    monkeypatch.setattr(check, "_host_is_unreachable_publicly", lambda host: None)
    c = check.public_condition(_settings(f"https://127.0.0.1:{self_signed_https}"))
    assert (c.ready, c.detail) == (False, "the certificate is not valid")


# ---------------------------------------------------------------- what the reader sends (bug fix #2)
@pytest.fixture
def recording_https(tmp_path):
    """A real TLS server on loopback that records each request's headers."""
    key, cert = tmp_path / "key.pem", tmp_path / "cert.pem"
    made = subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
         "-subj", "/CN=127.0.0.1", "-keyout", str(key), "-out", str(cert)],
        capture_output=True)
    if made.returncode != 0:
        pytest.skip("openssl could not make a certificate here")
    seen: list[dict[str, str]] = []

    class Recording(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            seen.append({k.lower(): v for k, v in self.headers.items()})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        def log_message(self, *a):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Recording)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(cert), str(key))
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_address[1], str(cert), seen
    httpd.shutdown()
    httpd.server_close()


def test_the_reader_names_itself_not_python_urllib(recording_https, monkeypatch):
    """Cloudflare answers urllib's default "Python-urllib/3.x" with 403
    (error 1010), measured from the Mac against getmekno.com on 2026-11-27.
    The real reader, on the wire, sends its own name and never urllib's.
    Only the trust store (this certificate) and the host check (loopback)
    are moved aside."""
    port, cert, seen = recording_https
    real = ssl.create_default_context

    def trusting():
        ctx = real(cafile=cert)
        ctx.check_hostname = False
        return ctx

    monkeypatch.setattr(check.ssl, "create_default_context", trusting)
    monkeypatch.setattr(check, "_host_is_unreachable_publicly", lambda host: None)
    code, _ = check.public_status(_settings(f"https://127.0.0.1:{port}"), "/healthz")
    assert code == 200
    assert len(seen) == 1
    agent = seen[0].get("user-agent", "")
    assert agent == check.PUBLIC_USER_AGENT == "motodiag-launch-check/409"
    assert "python-urllib" not in " ".join(seen[0].values()).lower()
