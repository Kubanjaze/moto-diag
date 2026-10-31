"""The object store: an S3 client in the standard library (Phase 345, K62).

The fleet's venv has no ``boto3``, and a test that skipped for it would be a
new skip, so the four calls this phase needs are written here: ``put``,
``get``, ``list`` and ``exists``. There is no delete: nothing offsite is ever
removed (the operator's answer at 345's stop).

Requests are signed with AWS Signature Version 4 (service ``s3``), path-style
(``https://<endpoint>/<bucket>/<key>``), the region read from the endpoint's
host (``s3.<region>.backblazeb2.com``). ``list`` takes no delimiter and
returns every key under the prefix; grouping keys into folders is the
caller's.

The network is one callable, ``transport(method, url, headers, body) ->
(status, headers, body)``, where the returned body is a binary file object.
The default is :func:`urllib_transport`; tests pass an in-process fake, so
no test opens a socket.
"""

from __future__ import annotations

import hashlib
import hmac
import shutil
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any, Callable, Protocol
from urllib.parse import quote

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
UNSIGNED = "UNSIGNED-PAYLOAD"
ALGORITHM = "AWS4-HMAC-SHA256"
TIMEOUT_S = 60

Transport = Callable[[str, str, dict[str, str], Any], tuple[int, dict[str, str], IO[bytes]]]


class StoreError(Exception):
    """The store answered with an error, or could not be reached. The text
    carries the status and the store's code and message, never a header."""


@dataclass(frozen=True)
class ObjectInfo:
    key: str
    size: int
    last_modified: str


class ObjectStore(Protocol):
    def put(self, key: str, path: Path, sha256: str) -> None: ...
    def get(self, key: str, path: Path) -> None: ...
    def list(self, prefix: str) -> list[ObjectInfo]: ...
    def exists(self, key: str) -> bool: ...


# --- Signature Version 4 -------------------------------------------------

def uri_encode(text: str, *, keep_slash: bool) -> str:
    """SigV4's encoding: every byte but ``A-Z a-z 0-9 - _ . ~`` (and ``/`` in a
    path) as ``%XX``."""
    return quote(text, safe="-_.~/" if keep_slash else "-_.~")


def canonical_query(params: dict[str, str]) -> str:
    """The query string, each name and value encoded, sorted by name."""
    pairs = sorted((uri_encode(k, keep_slash=False), uri_encode(v, keep_slash=False))
                   for k, v in params.items())
    return "&".join(f"{k}={v}" for k, v in pairs)


def canonical_request(method: str, path: str, params: dict[str, str],
                      headers: dict[str, str], payload_hash: str) -> tuple[str, str]:
    """The canonical request and its signed-headers list; every header given
    is signed."""
    lowered = sorted((k.lower().strip(), " ".join(str(v).split())) for k, v in headers.items())
    signed = ";".join(k for k, _ in lowered)
    lines = [method, uri_encode(path, keep_slash=True), canonical_query(params),
             "".join(f"{k}:{v}\n" for k, v in lowered), signed, payload_hash]
    return "\n".join(lines), signed


def string_to_sign(amz_date: str, scope: str, canonical: str) -> str:
    return "\n".join([ALGORITHM, amz_date, scope,
                      hashlib.sha256(canonical.encode("utf-8")).hexdigest()])


def signature(secret: str, day: str, region: str, service: str, to_sign: str) -> str:
    def _hmac(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    key = _hmac(("AWS4" + secret).encode("utf-8"), day)
    for part in (region, service, "aws4_request"):
        key = _hmac(key, part)
    return hmac.new(key, to_sign.encode("utf-8"), hashlib.sha256).hexdigest()


def authorization(key_id: str, secret: str, region: str, method: str, path: str,
                  params: dict[str, str], headers: dict[str, str], payload_hash: str) -> str:
    """The ``Authorization`` header for a request whose headers already hold
    ``x-amz-date``."""
    amz_date = next(v for k, v in headers.items() if k.lower() == "x-amz-date")
    day = amz_date[:8]
    scope = f"{day}/{region}/s3/aws4_request"
    canonical, signed = canonical_request(method, path, params, headers, payload_hash)
    sig = signature(secret, day, region, "s3", string_to_sign(amz_date, scope, canonical))
    return f"{ALGORITHM} Credential={key_id}/{scope}, SignedHeaders={signed}, Signature={sig}"


# --- the network ---------------------------------------------------------

def urllib_transport(method: str, url: str, headers: dict[str, str],
                     body: Any) -> tuple[int, dict[str, str], IO[bytes]]:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(request, timeout=TIMEOUT_S)  # noqa: S310
        return response.status, dict(response.headers), response
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e
    except urllib.error.URLError as e:
        raise StoreError(f"could not reach the store: {e.reason}") from e


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _error_text(body: bytes) -> str:
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return ""
    found = {_local(el.tag): (el.text or "") for el in root}
    return ": ".join(t for t in (found.get("Code", ""), found.get("Message", "")) if t)


class S3Store:
    """An :class:`ObjectStore` over one bucket of an S3-compatible service."""

    def __init__(self, endpoint: str, bucket: str, key_id: str, secret: str,
                 transport: Transport = urllib_transport,
                 clock: Callable[[], datetime] | None = None) -> None:
        host = endpoint.split("://", 1)[-1].strip("/")
        parts = host.split(".")
        if len(parts) < 3 or parts[0] != "s3":
            raise StoreError(f"cannot read a region from the endpoint {host!r} "
                             "(expected s3.<region>.backblazeb2.com)")
        self.host, self.region, self.bucket = host, parts[1], bucket
        self._key_id, self._secret = key_id, secret
        self._transport = transport
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"S3Store(host={self.host!r}, bucket={self.bucket!r})"

    def _request(self, method: str, key: str | None, params: dict[str, str],
                 payload_hash: str, body: Any = None,
                 extra: dict[str, str] | None = None) -> tuple[int, dict[str, str], IO[bytes]]:
        path = f"/{self.bucket}" + (f"/{key}" if key is not None else "")
        headers = {"host": self.host, "x-amz-content-sha256": payload_hash,
                   "x-amz-date": self._clock().strftime("%Y%m%dT%H%M%SZ"), **(extra or {})}
        headers["Authorization"] = authorization(self._key_id, self._secret, self.region,
                                                 method, path, params, headers, payload_hash)
        query = canonical_query(params)
        url = f"https://{self.host}{uri_encode(path, keep_slash=True)}" + (
            f"?{query}" if query else "")
        return self._transport(method, url, headers, body)

    def _check(self, what: str, status: int, body: IO[bytes]) -> None:
        if not 200 <= status < 300:
            with closing(body):
                detail = _error_text(body.read())
            raise StoreError(f"{what}: HTTP {status}" + (f" {detail}" if detail else ""))

    def put(self, key: str, path: Path, sha256: str) -> None:
        size = Path(path).stat().st_size
        with open(path, "rb") as fin:
            status, _, body = self._request("PUT", key, {}, sha256, fin,
                                            {"content-length": str(size)})
        self._check(f"PUT {key}", status, body)
        body.close()

    def get(self, key: str, path: Path) -> None:
        status, _, body = self._request("GET", key, {}, UNSIGNED)
        self._check(f"GET {key}", status, body)
        with closing(body), open(path, "wb") as fout:
            shutil.copyfileobj(body, fout, 1 << 20)

    def exists(self, key: str) -> bool:
        status, _, body = self._request("HEAD", key, {}, UNSIGNED)
        if status == 404:
            body.close()
            return False
        self._check(f"HEAD {key}", status, body)
        body.close()
        return True

    def list(self, prefix: str) -> list[ObjectInfo]:
        out: list[ObjectInfo] = []
        token: str | None = None
        while True:
            params = {"list-type": "2", "prefix": prefix}
            if token:
                params["continuation-token"] = token
            status, _, body = self._request("GET", None, params, UNSIGNED)
            self._check(f"LIST {prefix}", status, body)
            with closing(body):
                root = ET.fromstring(body.read())
            fields = {_local(el.tag): el for el in root}
            for el in root:
                if _local(el.tag) == "Contents":
                    item = {_local(c.tag): (c.text or "") for c in el}
                    out.append(ObjectInfo(item["Key"], int(item.get("Size") or 0),
                                          item.get("LastModified", "")))
            truncated = fields.get("IsTruncated")
            if truncated is None or (truncated.text or "").lower() != "true":
                return out
            nxt = fields.get("NextContinuationToken")
            token = nxt.text if nxt is not None else None
            if not token:
                raise StoreError(f"LIST {prefix}: truncated with no continuation token")
