"""Shared helpers for Phase 345's tests (offsite backups).

- :class:`FakeS3`, a transport for ``S3Store`` that answers in process: it
  recomputes each request's SigV4 signature from the secret it holds and
  refuses a request whose signature or signed headers differ, or that signs
  no ``host``; it checks a PUT's payload hash; it pages a listing at
  ``page`` keys. Its ``list`` has no delimiter, like the real one.
- :class:`MemoryStore`, an ``ObjectStore`` over a dict.
- a key file with planted values, a live-shaped folder on a temp path, a
  fixed clock, and a cheap scrypt cost.

No test reads the live database and none opens a socket.
"""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit
from xml.sax.saxutils import escape

from motodiag.backup import crypt
from motodiag.backup.settings import BUCKET, ENDPOINT, KEY_ID, PASSPHRASE, SECRET
from motodiag.backup.store import ObjectInfo, authorization
from motodiag.core.database import get_connection, init_db

HOST = "s3.us-west-004.backblazeb2.com"
FAKE_VALUES = {
    ENDPOINT: f"https://{HOST}",
    BUCKET: "motodiag-test-bucket",
    KEY_ID: "PLANTEDKEYID0345",
    SECRET: "planted-secret-value-0345",
    PASSPHRASE: "planted-passphrase-value-0345",
}
NS = "http://s3.amazonaws.com/doc/2006-03-01/"
#: The module's own cost, read before any test patches it.
REAL_LOG2_COST = crypt.DEFAULT_LOG2_COST


def _xml_error(status: int, code: str, message: str):
    body = (f'<?xml version="1.0" encoding="UTF-8"?><Error><Code>{code}</Code>'
            f"<Message>{escape(message)}</Message></Error>").encode()
    return status, {}, io.BytesIO(body)


def _auth_parts(auth: str) -> dict[str, str]:
    _, rest = auth.split(" ", 1)
    return dict(p.strip().split("=", 1) for p in rest.split(","))


class FakeS3:
    """An S3 service in process, for ``S3Store(transport=...)``."""

    def __init__(self, *, key_id: str = FAKE_VALUES[KEY_ID],
                 secret: str = FAKE_VALUES[SECRET], page: int = 1000) -> None:
        self.key_id, self.secret, self.page = key_id, secret, page
        self.objects: dict[str, bytes] = {}
        self.requests: list[tuple[str, str]] = []
        self.fail: tuple[int, str, str] | None = None

    def _refused(self, method: str, url: str, headers: dict[str, str]):
        parts = urlsplit(url)
        auth = _auth_parts(headers.get("Authorization", "x x=y"))
        signed = auth.get("SignedHeaders", "").split(";")
        given = {k.lower(): v for k, v in headers.items() if k != "Authorization"}
        if not {"host", "x-amz-date", "x-amz-content-sha256"} <= set(signed):
            return _xml_error(403, "AccessDenied", "host, x-amz-date and the payload hash "
                                                   "must be signed")
        if given.get("host") != parts.netloc or not set(signed) <= set(given):
            return _xml_error(403, "AccessDenied", "a signed header is missing")
        if not auth.get("Credential", "").startswith(self.key_id + "/"):
            return _xml_error(403, "InvalidAccessKeyId", "The key is not valid.")
        region = auth["Credential"].split("/")[2]
        expected = authorization(
            self.key_id, self.secret, region, method, unquote(parts.path),
            dict(parse_qsl(parts.query, keep_blank_values=True)),
            {k: given[k] for k in signed}, given["x-amz-content-sha256"])
        if expected != headers["Authorization"]:
            return _xml_error(403, "SignatureDoesNotMatch", "The signature does not match.")
        return None

    def __call__(self, method: str, url: str, headers: dict[str, str], body):
        self.requests.append((method, url))
        if self.fail:
            return _xml_error(*self.fail)
        refused = self._refused(method, url, headers)
        if refused:
            return refused
        parts = urlsplit(url)
        _, _bucket, *rest = unquote(parts.path).split("/", 2)
        key = rest[0] if rest else None
        if method == "PUT":
            data = body.read()
            if hashlib.sha256(data).hexdigest() != headers["x-amz-content-sha256"]:
                return _xml_error(400, "XAmzContentSHA256Mismatch", "payload hash")
            self.objects[key] = data
            return 200, {}, io.BytesIO(b"")
        if key is None:
            return self._list(dict(parse_qsl(parts.query)))
        if key not in self.objects:
            return _xml_error(404, "NoSuchKey", "The specified key does not exist.")
        return 200, {}, io.BytesIO(b"" if method == "HEAD" else self.objects[key])

    def _list(self, params: dict[str, str]):
        keys = sorted(k for k in self.objects if k.startswith(params.get("prefix", "")))
        after = params.get("continuation-token")
        if after:
            keys = [k for k in keys if k > after]
        page, more = keys[: self.page], len(keys) > self.page
        contents = "".join(
            f"<Contents><Key>{escape(k)}</Key><Size>{len(self.objects[k])}</Size>"
            "<LastModified>2026-10-31T03:00:00.000Z</LastModified></Contents>" for k in page)
        token = f"<NextContinuationToken>{escape(page[-1])}</NextContinuationToken>" if more else ""
        body = (f'<?xml version="1.0" encoding="UTF-8"?><ListBucketResult xmlns="{NS}">'
                f"<IsTruncated>{'true' if more else 'false'}</IsTruncated>{token}"
                f"{contents}</ListBucketResult>").encode()
        return 200, {}, io.BytesIO(body)


class MemoryStore:
    """An ``ObjectStore`` over a dict; ``list`` has no delimiter."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.puts: list[str] = []

    def put(self, key: str, path: Path, sha256: str) -> None:
        data = Path(path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == sha256
        self.objects[key] = data
        self.puts.append(key)

    def get(self, key: str, path: Path) -> None:
        Path(path).write_bytes(self.objects[key])

    def list(self, prefix: str) -> list[ObjectInfo]:
        return [ObjectInfo(k, len(v), "") for k, v in sorted(self.objects.items())
                if k.startswith(prefix)]

    def exists(self, key: str) -> bool:
        return key in self.objects


def write_env(path: Path, values: dict[str, str] | None = None, *, mode: int = 0o600) -> Path:
    vals = FAKE_VALUES if values is None else values
    path.write_text("".join(f"{k}={v}\n" for k, v in vals.items()), encoding="utf-8")
    os.chmod(path, mode)
    return path


def cheap_crypto(monkeypatch) -> None:
    """scrypt at 2**10, not 2**17: the cost is in each header, so decryption
    reads it back."""
    monkeypatch.setattr(crypt, "DEFAULT_LOG2_COST", 10)


def make_live(root: Path, media: dict[str, bytes] | None = None) -> tuple[Path, Path]:
    """A live-shaped folder: ``motodiag.db`` (``init_db``) and media files."""
    data_dir = root / "live"
    data_dir.mkdir(parents=True)
    db = data_dir / "motodiag.db"
    init_db(str(db))
    for rel, data in (media if media is not None else {
        "videos/shop_1/session_1/1.mp4": b"video one" * 100,
        "photos/shop_1/work_order_1/1.jpg": b"photo one" * 50,
        "audio/shop_1/1.m4a": b"audio one" * 70,
    }).items():
        path = data_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return db, data_dir


def add_row(db: Path, name: str) -> None:
    """One row a restore can be told apart by."""
    with get_connection(str(db)) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS phase345_marker (name TEXT)")
        conn.execute("INSERT INTO phase345_marker (name) VALUES (?)", (name,))


def clock_at(iso: str):
    return lambda: iso
