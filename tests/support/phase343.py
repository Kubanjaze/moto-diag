"""Shared helpers for Phase 343's tests (crash reports to Sentry).

- a made-up DSN holding a planted key, which no output may carry;
- :class:`FakeTransport`, the sender's transport answered in process: it
  keeps every request, answers a set status, can be held on an event, and
  can raise;
- :class:`FakeSender`, for ``app.state.telemetry``: ``sampled()`` answers
  a fixed value and ``capture`` keeps every event in a list.

No test opens a socket beyond loopback, and none sends to Sentry.
"""

from __future__ import annotations

import json
import threading

PLANTED_KEY = "k343plantedkey"
HOST = "o343.ingest.example.test"
PROJECT_ID = "7343"
DSN_TEXT = f"https://{PLANTED_KEY}@{HOST}/{PROJECT_ID}"


class FakeTransport:
    """``(url, headers, body) -> (status, reason, headers)``, in process."""

    def __init__(self, status: int = 200, reason: str = "OK",
                 headers: dict[str, str] | None = None) -> None:
        self.status, self.reason = status, reason
        self.headers = dict(headers or {})
        self.requests: list[tuple[str, dict[str, str], bytes]] = []
        self.release = threading.Event()
        self.release.set()
        self.entered = threading.Event()
        self.raises: BaseException | None = None
        self.received = threading.Condition()

    def hold(self) -> None:
        self.release.clear()

    def __call__(self, url: str, headers: dict[str, str], body: bytes):
        self.entered.set()
        self.release.wait(10)
        if self.raises is not None:
            raise self.raises
        with self.received:
            self.requests.append((url, dict(headers), body))
            self.received.notify_all()
        return self.status, self.reason, dict(self.headers)

    def wait_for(self, n: int, timeout: float = 5.0) -> bool:
        with self.received:
            return self.received.wait_for(lambda: len(self.requests) >= n,
                                          timeout)

    def payloads(self) -> list[dict]:
        """The JSON payload (third line) of every envelope received."""
        return [json.loads(body.split(b"\n")[2]) for _, _, body in self.requests]


class FakeSender:
    """A sender that sends nothing and keeps what it was given."""

    enabled = True

    def __init__(self, sampled: bool = True) -> None:
        self._sampled = sampled
        self.events: list[dict] = []
        self.release = "motodiag@test"
        self.environment = "test"
        self.server_name = "test-host"

    def sampled(self) -> bool:
        return self._sampled

    def capture(self, event: dict) -> bool:
        self.events.append(event)
        return True

    def errors(self) -> list[dict]:
        return [e for e in self.events if e.get("type") != "transaction"]

    def transactions(self) -> list[dict]:
        return [e for e in self.events if e.get("type") == "transaction"]
