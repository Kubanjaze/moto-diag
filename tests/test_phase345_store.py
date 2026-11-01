"""Phase 345 — the S3 client, SigV4, over an in-process transport.

Two published known-answer signatures (AWS's S3 Signature Version 4 worked
examples: the GET of ``test.txt`` and the bucket listing ``max-keys=2&
prefix=J``, both for ``examplebucket`` on 24 May 2013), the fake transport's
recomputed signature and its unsigned-host control, put/get/list/exists, a
three-page listing, and a ``StoreError`` that holds no key id.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest
from support.phase345 import FAKE_VALUES, HOST, FakeS3

from motodiag.backup.settings import BUCKET, KEY_ID, SECRET
from motodiag.backup.store import (
    EMPTY_SHA256,
    S3Store,
    StoreError,
    authorization,
    canonical_query,
    canonical_request,
)

AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
AWS_HOST = "examplebucket.s3.amazonaws.com"
AWS_DATE = "20130524T000000Z"


def _sig(auth: str) -> str:
    return auth.rsplit("Signature=", 1)[1]


class TestPublishedVectors:
    def test_get_object(self):
        headers = {"Host": AWS_HOST, "Range": "bytes=0-9",
                   "x-amz-content-sha256": EMPTY_SHA256, "x-amz-date": AWS_DATE}
        auth = authorization(AWS_KEY, AWS_SECRET, "us-east-1", "GET", "/test.txt", {},
                             headers, EMPTY_SHA256)
        assert "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date" in auth
        assert _sig(auth) == "f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"

    def test_list_objects_with_a_query_string(self):
        headers = {"Host": AWS_HOST, "x-amz-content-sha256": EMPTY_SHA256,
                   "x-amz-date": AWS_DATE}
        auth = authorization(AWS_KEY, AWS_SECRET, "us-east-1", "GET", "/",
                             {"prefix": "J", "max-keys": "2"}, headers, EMPTY_SHA256)
        assert _sig(auth) == "34b48302e7b5fa45bde8084f4b7868a86f0a534bc59db6670ed5711ef69dc6f7"

    def test_the_query_string_is_encoded_and_sorted(self):
        assert canonical_query({"prefix": "media/a b", "list-type": "2",
                                "continuation-token": "x/y+z="}) == (
            "continuation-token=x%2Fy%2Bz%3D&list-type=2&prefix=media%2Fa%20b")

    def test_every_given_header_is_signed(self):
        _, signed = canonical_request("GET", "/b/k", {}, {"host": "h", "x-amz-date": "d",
                                                          "x-amz-content-sha256": "p"}, "p")
        assert signed == "host;x-amz-content-sha256;x-amz-date"


@pytest.fixture
def fake():
    return FakeS3()


@pytest.fixture
def store(fake):
    return S3Store(FAKE_VALUES["MOTODIAG_BACKUP_S3_ENDPOINT"], FAKE_VALUES[BUCKET],
                   FAKE_VALUES[KEY_ID], FAKE_VALUES[SECRET], transport=fake,
                   clock=lambda: datetime(2026, 10, 31, 3, 0, tzinfo=timezone.utc))


def _file(tmp_path, name, data):
    path = tmp_path / name
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


class TestTheFakeChecksSignatures:
    def test_a_request_the_client_signed_is_accepted(self, store, fake, tmp_path):
        path, digest = _file(tmp_path, "a", b"hello")
        store.put("media/a.enc", path, digest)
        method, url = fake.requests[-1]
        assert (method, url) == ("PUT", f"https://{HOST}/motodiag-test-bucket/media/a.enc")

    def _signed(self, headers, method="GET", path="/motodiag-test-bucket/k"):
        return authorization(FAKE_VALUES[KEY_ID], FAKE_VALUES[SECRET], "us-west-004", method,
                             path, {}, headers, EMPTY_SHA256)

    def test_the_control_a_request_with_the_host_left_unsigned_is_refused(self, fake):
        unsigned = {"x-amz-content-sha256": EMPTY_SHA256, "x-amz-date": "20261031T030000Z"}
        headers = {**unsigned, "Authorization": self._signed(unsigned), "host": HOST}
        status, _, body = fake("GET", f"https://{HOST}/motodiag-test-bucket/k", headers, None)
        assert status == 403 and b"AccessDenied" in body.read()
        # ...and the same request with the host signed is answered (404: no object).
        signed = {**unsigned, "host": HOST}
        headers = {**signed, "Authorization": self._signed(signed)}
        status, _, _ = fake("GET", f"https://{HOST}/motodiag-test-bucket/k", headers, None)
        assert status == 404

    def test_a_wrong_secret_is_refused(self, fake, tmp_path):
        bad = S3Store(HOST, FAKE_VALUES[BUCKET], FAKE_VALUES[KEY_ID], "not-the-secret",
                      transport=fake)
        with pytest.raises(StoreError, match="403 SignatureDoesNotMatch"):
            bad.exists("k")

    def test_a_changed_signed_header_is_refused(self, fake):
        signed = {"host": HOST, "x-amz-content-sha256": EMPTY_SHA256,
                  "x-amz-date": "20261031T030000Z"}
        headers = {**signed, "Authorization": self._signed(signed)}
        headers["x-amz-date"] = "20261031T030001Z"
        status, _, _ = fake("GET", f"https://{HOST}/motodiag-test-bucket/k", headers, None)
        assert status == 403


class TestRoundTrips:
    def test_put_get_exists(self, store, fake, tmp_path):
        path, digest = _file(tmp_path, "a", b"x" * 5000)
        assert store.exists("snapshots/1/a") is False
        store.put("snapshots/1/a", path, digest)
        assert store.exists("snapshots/1/a") is True
        store.get("snapshots/1/a", tmp_path / "back")
        assert (tmp_path / "back").read_bytes() == b"x" * 5000

    def test_a_put_whose_hash_is_wrong_is_refused(self, store, tmp_path):
        path, _ = _file(tmp_path, "a", b"abc")
        with pytest.raises(StoreError, match="400"):
            store.put("k", path, hashlib.sha256(b"other").hexdigest())

    def test_a_get_of_a_missing_key_raises(self, store, tmp_path):
        with pytest.raises(StoreError, match="404 NoSuchKey"):
            store.get("absent", tmp_path / "x")

    def test_list_returns_every_key_under_the_prefix_with_no_delimiter(self, store, fake):
        fake.objects.update({"snapshots/a/db": b"1", "snapshots/a/m": b"22",
                             "snapshots/b/db": b"333", "media/x.enc": b"4"})
        got = store.list("snapshots/")
        assert [(o.key, o.size) for o in got] == [
            ("snapshots/a/db", 1), ("snapshots/a/m", 2), ("snapshots/b/db", 3)]
        assert all("delimiter" not in url for _, url in fake.requests)

    def test_a_listing_of_2500_keys_comes_back_whole_in_three_pages(self, store, fake):
        fake.objects.update({f"media/{i:05d}.enc": b"" for i in range(2500)})
        got = store.list("media/")
        assert [o.key for o in got] == sorted(fake.objects)
        lists = [u for m, u in fake.requests if "list-type=2" in u]
        assert len(lists) == 3
        assert "continuation-token=media%2F00999.enc" in lists[1]


class TestErrors:
    def test_a_403_names_the_status_and_code_and_never_the_key_id(self, store, fake, tmp_path):
        fake.fail = (403, "AccessDenied", "bucket-only key cannot do that")
        path, digest = _file(tmp_path, "a", b"abc")
        with pytest.raises(StoreError) as e:
            store.put("media/a.enc", path, digest)
        text = str(e.value)
        assert "403" in text and "AccessDenied" in text
        assert FAKE_VALUES[KEY_ID] not in text and FAKE_VALUES[SECRET] not in text

    def test_an_endpoint_without_a_region_is_refused(self):
        with pytest.raises(StoreError, match="region"):
            S3Store("https://example.com", "b", "k", "s")

    def test_the_repr_has_no_key(self, store):
        assert FAKE_VALUES[KEY_ID] not in repr(store)
        assert FAKE_VALUES[SECRET] not in repr(store)

    def test_the_urllib_transport_on_loopback(self, tmp_path):
        """The default transport, against a server on 127.0.0.1 (the network
        guard allows loopback): a PUT's body and length arrive, a 2xx body
        streams back, and a 404 comes back as a status, not an exception."""
        import http.server
        import threading

        from motodiag.backup.store import urllib_transport

        seen: dict = {}

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_PUT(self):
                n = int(self.headers["Content-Length"])
                seen["put"] = (self.path, self.rfile.read(n), self.headers["x-amz-date"])
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_GET(self):
                found = self.path == "/b/k"
                body = b"object bytes" if found else b"<Error><Code>NoSuchKey</Code></Error>"
                self.send_response(200 if found else 404)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            path, _ = _file(tmp_path, "a", b"payload")
            with open(path, "rb") as fin:
                status, _, body = urllib_transport(
                    "PUT", base + "/b/k", {"content-length": "7", "x-amz-date": "D"}, fin)
            body.close()
            assert status == 200 and seen["put"] == ("/b/k", b"payload", "D")
            status, _, body = urllib_transport("GET", base + "/b/k", {}, None)
            assert (status, body.read()) == (200, b"object bytes")
            status, _, body = urllib_transport("GET", base + "/b/none", {}, None)
            assert status == 404 and b"NoSuchKey" in body.read()
        finally:
            server.shutdown()
            server.server_close()

    def test_an_unreachable_store_raises_store_error(self, monkeypatch):
        import urllib.error

        from motodiag.backup import store as store_mod

        def refuse(*a, **k):
            raise urllib.error.URLError("no network in the fence")

        monkeypatch.setattr(store_mod.urllib.request, "urlopen", refuse)
        with pytest.raises(StoreError, match="could not reach"):
            store_mod.urllib_transport("GET", "https://s3.x.example/b", {}, None)
