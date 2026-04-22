"""Billing provider abstraction (Phase 176).

Abstract interface + two concrete implementations:

- :class:`FakeBillingProvider` — deterministic, zero-network. Used by
  tests + local development. No stripe library needed.
- :class:`StripeBillingProvider` — real Stripe API integration. Lazy-
  imports the ``stripe`` package; raises a clean error if the
  library is not installed.

Switched via ``MOTODIAG_BILLING_PROVIDER=fake|stripe``. Factory
``get_billing_provider()`` reads Settings and returns the configured
implementation.
"""

from __future__ import annotations

import hashlib
import hmac
import json as _json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from motodiag.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CheckoutSessionResult:
    """Returned from ``create_checkout_session``."""

    checkout_url: str
    session_id: str
    stripe_customer_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BillingProviderError(Exception):
    """Base for billing-provider errors (network, config, etc.)."""


class WebhookSignatureError(BillingProviderError):
    """Raised when webhook HMAC verification fails."""


class StripeLibraryMissingError(BillingProviderError):
    """Raised when ``stripe`` lib isn't installed but ``stripe``
    provider is selected."""


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class BillingProvider(ABC):
    """Abstract contract for billing integrations."""

    @abstractmethod
    def create_checkout_session(
        self,
        user_id: int,
        email: Optional[str],
        tier: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSessionResult:
        """Start a subscription checkout flow. Returns URL + session id."""

    @abstractmethod
    def create_portal_session(
        self, stripe_customer_id: str, return_url: str,
    ) -> str:
        """Return a Stripe Customer Portal URL for the customer to
        manage their subscription (update card, cancel, etc.)."""

    @abstractmethod
    def verify_webhook_signature(
        self, payload: bytes, signature_header: str,
    ) -> dict:
        """Verify HMAC + parse the Stripe event. Raises
        :class:`WebhookSignatureError` on failure."""

    @abstractmethod
    def retrieve_subscription(self, stripe_sub_id: str) -> dict:
        """Fetch live subscription state from the provider. Used by
        `subscription sync` CLI to reconcile local + Stripe state."""

    @abstractmethod
    def cancel_subscription(
        self, stripe_sub_id: str, *, immediate: bool = False,
    ) -> dict:
        """Cancel a subscription. ``immediate=False`` means
        cancel-at-period-end; ``True`` means cancel now."""


# ---------------------------------------------------------------------------
# Fake (tests + dev)
# ---------------------------------------------------------------------------


class FakeBillingProvider(BillingProvider):
    """Zero-network deterministic implementation.

    - Checkout URLs: ``https://fake-billing.local/checkout/<user_id>/<tier>``
    - Customer IDs: ``cus_fake_<user_id>``
    - Subscription IDs: ``sub_fake_<user_id>_<counter>``
    - Signature verification: accepts the literal header value
      ``"fake_signature_ok"``; anything else raises
      :class:`WebhookSignatureError`. Tests construct events by
      crafting the payload + setting this header.
    """

    FAKE_SIGNATURE = "fake_signature_ok"

    def __init__(self) -> None:
        self._sub_counter = 0

    def create_checkout_session(
        self, user_id, email, tier, success_url, cancel_url,
    ) -> CheckoutSessionResult:
        session_id = f"cs_fake_{user_id}_{tier}"
        checkout_url = (
            f"https://fake-billing.local/checkout/{user_id}/{tier}"
        )
        return CheckoutSessionResult(
            checkout_url=checkout_url,
            session_id=session_id,
            stripe_customer_id=f"cus_fake_{user_id}",
        )

    def create_portal_session(
        self, stripe_customer_id, return_url,
    ) -> str:
        return (
            f"https://fake-billing.local/portal/"
            f"{stripe_customer_id}?return_to={return_url}"
        )

    def verify_webhook_signature(
        self, payload: bytes, signature_header: str,
    ) -> dict:
        if signature_header != self.FAKE_SIGNATURE:
            raise WebhookSignatureError(
                "fake provider: signature header must be "
                f"'{self.FAKE_SIGNATURE}'"
            )
        try:
            event = _json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, _json.JSONDecodeError) as e:
            raise WebhookSignatureError(
                f"fake provider: invalid payload: {e}"
            ) from e
        return event

    def retrieve_subscription(self, stripe_sub_id: str) -> dict:
        return {
            "id": stripe_sub_id,
            "status": "active",
            "customer": f"cus_fake_from_{stripe_sub_id}",
        }

    def cancel_subscription(
        self, stripe_sub_id: str, *, immediate: bool = False,
    ) -> dict:
        return {
            "id": stripe_sub_id,
            "status": "canceled" if immediate else "active",
            "cancel_at_period_end": not immediate,
        }


# ---------------------------------------------------------------------------
# Stripe (prod)
# ---------------------------------------------------------------------------


class StripeBillingProvider(BillingProvider):
    """Real Stripe API integration.

    Lazy-imports :pypi:`stripe` inside each method so the module
    imports cleanly even when the library is not installed (tests
    never exercise this class).
    """

    def __init__(
        self, api_key: str, webhook_secret: str,
        settings: Optional[Settings] = None,
    ) -> None:
        if not api_key:
            raise BillingProviderError(
                "Stripe api_key is empty; set MOTODIAG_STRIPE_API_KEY"
            )
        self._api_key = api_key
        self._webhook_secret = webhook_secret
        self._settings = settings or get_settings()

    def _stripe(self):
        try:
            import stripe  # type: ignore[import-not-found]
        except ImportError as e:
            raise StripeLibraryMissingError(
                "Stripe library not installed; run "
                "`pip install stripe` to use StripeBillingProvider"
            ) from e
        stripe.api_key = self._api_key
        return stripe

    def _price_id_for_tier(self, tier: str) -> str:
        s = self._settings
        mapping = {
            "individual": s.stripe_price_individual,
            "shop": s.stripe_price_shop,
            "company": s.stripe_price_company,
        }
        price = mapping.get(tier, "")
        if not price:
            raise BillingProviderError(
                f"no Stripe price id configured for tier {tier!r}; "
                f"set MOTODIAG_STRIPE_PRICE_{tier.upper()}"
            )
        return price

    def create_checkout_session(
        self, user_id, email, tier, success_url, cancel_url,
    ) -> CheckoutSessionResult:
        stripe = self._stripe()
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{
                "price": self._price_id_for_tier(tier),
                "quantity": 1,
            }],
            customer_email=email or None,
            client_reference_id=str(user_id),
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(user_id), "tier": tier},
        )
        return CheckoutSessionResult(
            checkout_url=session.url,
            session_id=session.id,
            stripe_customer_id=session.get("customer"),
        )

    def create_portal_session(
        self, stripe_customer_id, return_url,
    ) -> str:
        stripe = self._stripe()
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        return session.url

    def verify_webhook_signature(
        self, payload: bytes, signature_header: str,
    ) -> dict:
        stripe = self._stripe()
        try:
            event = stripe.Webhook.construct_event(
                payload, signature_header, self._webhook_secret,
            )
        except Exception as e:
            raise WebhookSignatureError(
                f"Stripe signature verification failed: {e}"
            ) from e
        return event if isinstance(event, dict) else dict(event)

    def retrieve_subscription(self, stripe_sub_id: str) -> dict:
        stripe = self._stripe()
        sub = stripe.Subscription.retrieve(stripe_sub_id)
        return dict(sub) if not isinstance(sub, dict) else sub

    def cancel_subscription(
        self, stripe_sub_id: str, *, immediate: bool = False,
    ) -> dict:
        stripe = self._stripe()
        if immediate:
            result = stripe.Subscription.delete(stripe_sub_id)
        else:
            result = stripe.Subscription.modify(
                stripe_sub_id, cancel_at_period_end=True,
            )
        return dict(result) if not isinstance(result, dict) else result


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_billing_provider(
    settings: Optional[Settings] = None,
) -> BillingProvider:
    """Return the configured BillingProvider singleton.

    Respects ``settings.billing_provider`` (``"fake"`` | ``"stripe"``).
    Tests typically call ``FakeBillingProvider()`` directly and inject
    via dependency override; this factory is for prod + CLI.
    """
    s = settings or get_settings()
    provider_name = (s.billing_provider or "fake").lower()
    if provider_name == "stripe":
        return StripeBillingProvider(
            api_key=s.stripe_api_key,
            webhook_secret=s.stripe_webhook_secret,
            settings=s,
        )
    # default: fake
    return FakeBillingProvider()
