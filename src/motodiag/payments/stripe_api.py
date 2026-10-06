"""The one gateway to Stripe (Phase 273).

Every call this app makes to Stripe goes through :func:`client`, which
refuses a live key outside production, pins the API version, and maps
the SDK's errors to :class:`StripeUnavailable`. 176's
``StripeBillingProvider`` uses it too.

The ``stripe`` package is the ``payments`` extra and is imported lazily,
so an install without it still imports this module.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from motodiag.core.config import Environment, Settings, get_settings


# Pinned with the SDK (`stripe==16.0.0` sends this version). A test
# requires the two to agree, so an SDK bump is a deliberate change.
API_VERSION = "2026-09-30.endive"

LIVE_KEY_PREFIXES = ("sk_live_", "rk_live_")
TEST_KEY_PREFIXES = ("sk_test_", "rk_test_")

# Stripe's own registration code for a server-driven simulated reader.
SIMULATED_READER_CODE = "simulated-wpe"

T = TypeVar("T")


class StripeNotConfigured(RuntimeError):
    """No usable Stripe key, or the provider is not ``stripe``."""


class StripeLibraryMissing(StripeNotConfigured):
    """The ``payments`` extra is not installed."""


class LiveKeyRefused(RuntimeError):
    """A live key outside ``env=prod``."""


class StripeUnavailable(RuntimeError):
    """A Stripe request did not succeed. ``kind`` is one of
    ``unreachable``, ``refused``, ``busy``, ``rejected``, ``error``."""

    def __init__(self, what: str, kind: str, detail: str) -> None:
        self.what = what
        self.kind = kind
        self.detail = detail
        super().__init__(self.message)

    @property
    def message(self) -> str:
        lead = {
            "unreachable": "Stripe could not be reached",
            "refused": "Stripe refused the key",
            "busy": "Stripe is rate-limiting requests",
            "rejected": "Stripe rejected the request",
            "error": "Stripe returned an error",
        }.get(self.kind, "Stripe returned an error")
        return f"{lead} ({self.what}): {self.detail}"


def refuse_live_key(key: str, env: Environment) -> None:
    """Raise :class:`LiveKeyRefused` for a live key unless ``env`` is prod."""
    if key.startswith(LIVE_KEY_PREFIXES) and env != Environment.PROD:
        raise LiveKeyRefused(
            f"A live Stripe key is set but env is {env.value!r}. Live keys are "
            "used only with MOTODIAG_ENV=prod; use a test-mode key (sk_test_…)."
        )


def is_test_key(key: str) -> bool:
    return key.startswith(TEST_KEY_PREFIXES)


@dataclass(frozen=True)
class KeyStatus:
    """What ``payments check`` may print: never any part of a value."""

    provider: str
    api_key_set: bool
    test_mode: bool
    webhook_secret_set: bool
    prices_set: int
    prices_are_placeholders: bool


def key_status(settings: Optional[Settings] = None) -> KeyStatus:
    s = settings or get_settings()
    prices = (s.stripe_price_individual, s.stripe_price_shop,
              s.stripe_price_company)
    return KeyStatus(
        provider=(s.billing_provider or "fake").lower(),
        api_key_set=bool(s.stripe_api_key),
        test_mode=is_test_key(s.stripe_api_key),
        webhook_secret_set=bool(s.stripe_webhook_secret),
        prices_set=sum(1 for p in prices if p),
        prices_are_placeholders=s.stripe_prices_are_placeholders,
    )


# ---------------------------------------------------------------------------
# The HTTP client: the SDK's own, unless a test sets one, logged on request
# ---------------------------------------------------------------------------

# Tests answer Stripe's requests from fixtures by setting this to an
# ``http_client`` for the SDK (tests/support/stripe_fixtures.FixtureHTTP).
_test_http_client: Optional[Any] = None
_log_lock = threading.Lock()


def _logging_client(inner: Any, log_path: str) -> Any:
    import stripe

    class _CallLog(stripe.HTTPClient):
        name = "motodiag-call-log"

        def request(self, method, url, headers, post_data=None, **kwargs):
            body, status, resp_headers = inner.request(
                method, url, headers, post_data
            )
            _append_call(log_path, method, url, status, body, resp_headers,
                         headers)
            return body, status, resp_headers

        def close(self):
            inner.close()

    return _CallLog()


def _append_call(log_path: str, method: str, url: str, status: int,
                 body: Any, resp_headers: Any, req_headers: Any) -> None:
    from urllib.parse import urlsplit

    size = len(body) if isinstance(body, (bytes, str)) else None
    request_id = None
    if resp_headers is not None:
        request_id = resp_headers.get("Request-Id") or resp_headers.get("request-id")
    line = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": method.upper(),
        "path": urlsplit(url).path,
        "status": status,
        "bytes": size,
        "request_id": request_id,
        "stripe_version": (req_headers or {}).get("Stripe-Version"),
        "connected_account": bool((req_headers or {}).get("Stripe-Account")),
    }
    with _log_lock:
        with open(Path(log_path).expanduser(), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(line) + "\n")


def client(settings: Optional[Settings] = None) -> Any:
    """A ``stripe.StripeClient`` for this app's key, at :data:`API_VERSION`.

    Raises :class:`StripeNotConfigured` or :class:`LiveKeyRefused` before
    any request is made.
    """
    s = settings or get_settings()
    if (s.billing_provider or "fake").lower() != "stripe":
        raise StripeNotConfigured(
            "Stripe is not configured (billing provider is "
            f"{s.billing_provider!r}). Run `motodiag payments check`."
        )
    if not s.stripe_api_key:
        raise StripeNotConfigured(
            "No Stripe key is set (MOTODIAG_STRIPE_API_KEY). "
            "Run `motodiag payments check`."
        )
    return make_client(s.stripe_api_key, s)


def make_client(api_key: str, settings: Settings) -> Any:
    """The client for ``api_key``: the live-key refusal, the pinned
    version, the call log. :func:`client` and 176's provider both use it."""
    refuse_live_key(api_key, settings.env)
    try:
        import stripe
    except ImportError as e:
        raise StripeLibraryMissing(
            "The Stripe library is not installed; install motodiag[payments]."
        ) from e
    http = _test_http_client
    if settings.stripe_call_log:
        http = _logging_client(http or stripe.new_default_http_client(),
                               settings.stripe_call_log)
    return stripe.StripeClient(
        api_key,
        stripe_version=API_VERSION,
        http_client=http,
    )


def call(what: str, fn: Callable[[], T]) -> T:
    """Run one Stripe request, mapping the SDK's errors."""
    import stripe

    try:
        return fn()
    except stripe.APIConnectionError as e:
        raise StripeUnavailable(what, "unreachable", _short(e)) from e
    except (stripe.AuthenticationError, stripe.PermissionError) as e:
        raise StripeUnavailable(what, "refused", _short(e)) from e
    except stripe.RateLimitError as e:
        raise StripeUnavailable(what, "busy", _short(e)) from e
    except (stripe.InvalidRequestError, stripe.CardError,
            stripe.IdempotencyError) as e:
        raise StripeUnavailable(what, "rejected", _short(e)) from e
    except stripe.StripeError as e:
        raise StripeUnavailable(what, "error", _short(e)) from e


_SECRET_SHAPED = re.compile(r"\b(?:sk|rk|pk|whsec)_[A-Za-z0-9_*]+")


def scrub(text: str) -> str:
    """Remove anything shaped like a key or a webhook secret. Stripe's
    invalid-key error quotes the key's last characters."""
    return _SECRET_SHAPED.sub("[redacted]", text)


def _short(e: Exception) -> str:
    msg = getattr(e, "user_message", None) or str(e) or type(e).__name__
    return scrub(" ".join(str(msg).split()))[:300]


def as_dict(obj: Any) -> dict:
    """A Stripe object as a plain dict."""
    if isinstance(obj, dict) and not hasattr(obj, "to_dict"):
        return obj
    return obj.to_dict()
