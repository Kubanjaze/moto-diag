"""Phase 273 — Stripe without the network.

- :class:`FixtureHTTP` is an ``http_client`` for the SDK's own
  ``StripeClient``: each request must match the next expected
  ``(method, path)`` and is answered from a fixture in
  ``tests/fixtures/phase273/``. The requests are kept for assertions.
- :func:`load` reads a fixture. Each carries ``_fixture.kind``:
  ``recorded`` (a test-mode response from the smoke calls, ids kept) or
  ``built`` (written from Stripe's documented shape; says from where).
- :func:`signed` signs an event at test time with :data:`TEST_SECRET`, a
  secret that exists only here, at :data:`FROZEN_AT`; :func:`freeze_webhook_clock`
  makes the SDK's 300 s tolerance read that instant.
- :func:`stripe_settings` is a ``Settings`` with a test-only key.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional
from urllib.parse import parse_qs, urlsplit

import stripe

from motodiag.core.config import Environment, Settings

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "phase273"

# Shaped like Stripe's values so the code's prefix checks see them, and
# exist nowhere but in this file.
TEST_KEY = "sk_test_" + "only0for0tests0phase273"
TEST_SECRET = "whsec_" + "only0for0tests0phase273"
LIVE_KEY_PLANTED = "sk_live_" + "planted0control0phase273"

# 2026-10-06T12:00:00Z: every signature and every check of one reads this.
FROZEN_AT = 1791288000

SHOP_ACCOUNT = "acct_1TestShop273"


def load(name: str) -> dict:
    data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    assert data["_fixture"]["kind"] in ("recorded", "built"), name
    return data


def body(name: str) -> dict:
    return copy.deepcopy(load(name)["body"])


class FixtureHTTP(stripe.HTTPClient):
    """Answers each expected request in order; anything else fails."""

    name = "fixture"

    def __init__(self, expected: list[tuple[str, str, Any]]) -> None:
        super().__init__()
        self.expected = list(expected)
        self.requests: list[SimpleNamespace] = []

    def request(self, method, url, headers, post_data=None, **kwargs):
        path = urlsplit(url).path
        headers = dict(headers or {})
        if isinstance(post_data, bytes):
            post_data = post_data.decode("utf-8")
        if headers.get("Content-Type", "").startswith("application/json"):
            params = json.loads(post_data) if post_data else {}
        else:
            query = post_data if post_data else urlsplit(url).query
            params = {k: v[-1] for k, v in parse_qs(query or "").items()}
        self.requests.append(SimpleNamespace(
            method=method.upper(), path=path, params=params, headers=headers))
        assert self.expected, f"unexpected Stripe request: {method.upper()} {path}"
        want_method, want_path, answer = self.expected.pop(0)
        assert method.upper() == want_method and re.fullmatch(want_path, path), (
            f"Stripe request {method.upper()} {path}, expected {want_method} {want_path}"
        )
        if isinstance(answer, str):
            fx = load(answer)
            status, payload = fx["status"], fx["body"]
        else:
            status, payload = answer
        return json.dumps(payload), status, {"Request-Id": "req_fixture"}

    def close(self):
        pass


def stripe_settings(**overrides: Any) -> Settings:
    values = dict(
        env=Environment.DEV,
        billing_provider="stripe",
        stripe_api_key=TEST_KEY,
        stripe_webhook_secret=TEST_SECRET,
        stripe_price_individual="price_test_individual",
        stripe_price_shop="price_test_shop",
        stripe_price_company="price_test_company",
    )
    values.update(overrides)
    return Settings(**values)


def signature(payload: bytes, secret: str = TEST_SECRET,
              timestamp: int = FROZEN_AT) -> str:
    """Stripe's scheme: ``t=<ts>,v1=HMAC-SHA256(secret, "<ts>.<payload>")``."""
    signed = f"{timestamp}.".encode() + payload
    mac = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={mac}"


def signed(event: dict, secret: str = TEST_SECRET,
           timestamp: int = FROZEN_AT) -> tuple[bytes, str]:
    payload = json.dumps(event).encode()
    return payload, signature(payload, secret, timestamp)


def freeze_webhook_clock(monkeypatch, at: int = FROZEN_AT) -> None:
    """The SDK checks the signature's age against ``time.time()`` in
    ``stripe._webhook``; only that module's clock is replaced."""
    import stripe._webhook as wh

    monkeypatch.setattr(wh, "time", SimpleNamespace(time=lambda: float(at)))


def event(event_type: str, obj: dict, *, event_id: str,
          account: Optional[str] = None, livemode: bool = False) -> dict:
    """An event as Stripe sends it (built: docs.stripe.com/api/events/object)."""
    evt = {
        "id": event_id,
        "object": "event",
        "api_version": "2026-09-30.endive",
        "created": FROZEN_AT,
        "type": event_type,
        "livemode": livemode,
        "pending_webhooks": 1,
        "request": {"id": None, "idempotency_key": None},
        "data": {"object": obj},
    }
    if account is not None:
        evt["account"] = account
    return evt
