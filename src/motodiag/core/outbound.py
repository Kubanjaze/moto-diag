"""Outbound requests to public data services (Phase 281).

One small client for the three services Track O batch 3 calls: NHTSA's
recall service, NHTSA vPIC and the ECB's reference rates. Standard library
only: the core dependencies carry no HTTP library.

The rule this module exists for (F103): **a failure is never an empty
result.** A caller gets the body, or `ServiceUnavailable` naming the
service and what went wrong. NHTSA's recall service answers "no result"
with HTTP 400 and a valid JSON body, so a caller may name statuses it
accepts; everything else outside 2xx is an error.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

from motodiag import __version__

TIMEOUT_S = 20
USER_AGENT = f"motodiag/{__version__} (+https://github.com/Kubanjaze/moto-diag)"


class ServiceUnavailable(Exception):
    """A service could not answer. `kind` is unreachable, blocked, error or malformed."""

    def __init__(self, service: str, kind: str, detail: str, status: Optional[int] = None):
        self.service = service
        self.kind = kind
        self.detail = detail
        self.status = status
        super().__init__(self.message)

    @property
    def message(self) -> str:
        what = {
            "unreachable": "could not be reached",
            "blocked": "refused the request",
            "error": "answered with an error",
            "malformed": "sent an answer that could not be read",
        }[self.kind]
        return f"{self.service} {what}: {self.detail}"


@dataclass(frozen=True)
class Response:
    service: str
    url: str
    status: int
    body: bytes
    fetched_at: str

    def json(self):
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise ServiceUnavailable(self.service, "malformed", f"not JSON ({exc})",
                                     self.status) from exc


def _open(url: str, headers: dict, timeout: float) -> tuple[int, bytes]:
    """The transport. Tests replace this with a recorded fixture."""
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read() or b""


def _looks_like_html(body: bytes) -> bool:
    head = body.lstrip()[:200].lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def fetch(service: str, url: str, *, expect: str,
          accept_statuses: Iterable[int] = ()) -> Response:
    """GET `url` once. `expect` is "json" or "xml"."""
    accept = {int(s) for s in accept_statuses}
    accept_header = "application/json" if expect == "json" else "application/xml"
    try:
        status, body = _open(url, {"User-Agent": USER_AGENT, "Accept": accept_header},
                             TIMEOUT_S)
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as exc:
        reason = getattr(exc, "reason", exc)
        raise ServiceUnavailable(service, "unreachable", str(reason)) from exc
    except OSError as exc:
        raise ServiceUnavailable(service, "unreachable", str(exc)) from exc

    if status == 403:
        raise ServiceUnavailable(service, "blocked", f"HTTP 403, {len(body)} bytes", status)
    if not (200 <= status < 300) and status not in accept:
        raise ServiceUnavailable(service, "error", f"HTTP {status}", status)
    if _looks_like_html(body):
        raise ServiceUnavailable(service, "blocked",
                                 f"HTTP {status} with a web page, not {expect.upper()}",
                                 status)
    if not body.strip():
        raise ServiceUnavailable(service, "malformed", f"HTTP {status} with an empty body",
                                 status)
    return Response(service=service, url=url, status=status, body=body,
                    fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
