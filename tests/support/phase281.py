"""Shared helpers for Phase 281's tests (Track O batch 3).

Every capability is reached through a `motodiag` command against a scratch
database (the CLI helpers are 274's). The services are never called: `serve`
swaps `core.outbound._open` for the recorded fixtures in
`tests/fixtures/phase281/`, and the network guard would fail any test that
tried. `on_day` fixes the one clock every validity check reads.
"""

from __future__ import annotations

import urllib.error
from datetime import date
from pathlib import Path

from support.phase274 import new_db, ok, refused, seed_bike, seed_customer, seed_shop, sql

__all__ = ["new_db", "ok", "refused", "sql", "seed_bike", "seed_customer", "seed_shop",
           "fixture", "serve", "on_day", "UNREACHABLE", "FIXTURES"]

FIXTURES = Path(__file__).parent.parent / "fixtures" / "phase281"

UNREACHABLE = urllib.error.URLError("[Errno 8] nodename nor servname provided, or not known")


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def serve(monkeypatch, routes: dict) -> list[str]:
    """Answer requests from fixtures. ``routes`` maps a URL substring to
    ``(status, body_bytes)`` or to an exception to raise. Returns the list of
    URLs requested, so a test can assert what was (and was not) asked."""
    from motodiag.core import outbound

    asked: list[str] = []

    def fake_open(url, headers, timeout):
        asked.append(url)
        assert headers["User-Agent"].startswith("motodiag/"), headers
        for key, answer in routes.items():
            if key in url:
                if isinstance(answer, BaseException):
                    raise answer
                return answer
        raise AssertionError(f"no fixture for {url}")

    monkeypatch.setattr(outbound, "_open", fake_open)
    return asked


def on_day(monkeypatch, day: str) -> None:
    from motodiag.accounting import tax

    fixed = date.fromisoformat(day)
    monkeypatch.setattr(tax, "today", lambda: fixed)
