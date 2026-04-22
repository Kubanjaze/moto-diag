"""Billing routes — checkout + portal + Stripe webhook (Phase 176)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict

from motodiag.api.deps import get_db_path, get_settings
from motodiag.auth.deps import (
    AuthedUser, get_current_user, require_api_key,
)
from motodiag.billing.providers import (
    BillingProvider, get_billing_provider,
)
from motodiag.billing.subscription_repo import get_active_subscription
from motodiag.billing.webhook_handlers import dispatch_event
from motodiag.core.config import Settings


logger = logging.getLogger(__name__)
router = APIRouter(tags=["billing"])


# ---------------------------------------------------------------------------
# Dependencies (billing-specific)
# ---------------------------------------------------------------------------


def get_provider(
    settings: Settings = Depends(get_settings),
) -> BillingProvider:
    return get_billing_provider(settings=settings)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CheckoutSessionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tier: str  # "individual" | "shop" | "company"


class CheckoutSessionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    checkout_url: str
    session_id: str


class PortalSessionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    portal_url: str


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tier: Optional[str] = None
    status: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False


class WebhookResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    received: bool
    processed: bool
    event_id: str
    event_type: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/billing/checkout-session",
    response_model=CheckoutSessionResponse,
    summary="Start a subscription checkout flow",
)
def create_checkout_session(
    req: CheckoutSessionRequest,
    user: AuthedUser = Depends(get_current_user),
    provider: BillingProvider = Depends(get_provider),
    settings: Settings = Depends(get_settings),
) -> CheckoutSessionResponse:
    """Returns a checkout URL. Client redirects user to this URL to
    complete payment. On success, Stripe sends
    ``customer.subscription.created`` to the webhook endpoint and
    the subscription row is populated."""
    from motodiag.auth.deps import SUBSCRIPTION_TIERS
    if req.tier not in SUBSCRIPTION_TIERS:
        from motodiag.auth.api_key_repo import InvalidApiKeyError
        raise InvalidApiKeyError(
            f"tier must be one of {SUBSCRIPTION_TIERS}"
        )
    result = provider.create_checkout_session(
        user_id=user.id,
        email=user.email,
        tier=req.tier,
        success_url=settings.checkout_success_url,
        cancel_url=settings.checkout_cancel_url,
    )
    return CheckoutSessionResponse(
        checkout_url=result.checkout_url,
        session_id=result.session_id,
    )


@router.post(
    "/billing/portal-session",
    response_model=PortalSessionResponse,
    summary="Get a Stripe Customer Portal URL",
)
def create_portal_session(
    user: AuthedUser = Depends(get_current_user),
    provider: BillingProvider = Depends(get_provider),
    settings: Settings = Depends(get_settings),
    db_path: str = Depends(get_db_path),
) -> PortalSessionResponse:
    """Generate a temporary portal URL where the user can update
    their payment method, download invoices, or cancel."""
    sub = get_active_subscription(user.id, db_path=db_path)
    if sub is None or not sub.stripe_customer_id:
        from motodiag.auth.deps import SubscriptionRequiredError
        raise SubscriptionRequiredError("any")
    url = provider.create_portal_session(
        stripe_customer_id=sub.stripe_customer_id,
        return_url=settings.billing_portal_return_url,
    )
    return PortalSessionResponse(portal_url=url)


@router.get(
    "/billing/subscription",
    response_model=SubscriptionResponse,
    summary="Current active subscription",
)
def get_subscription(
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> SubscriptionResponse:
    sub = get_active_subscription(user.id, db_path=db_path)
    if sub is None:
        return SubscriptionResponse()
    return SubscriptionResponse(
        tier=sub.tier,
        status=sub.status,
        stripe_customer_id=sub.stripe_customer_id,
        stripe_subscription_id=sub.stripe_subscription_id,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
    )


@router.post(
    "/billing/webhooks/stripe",
    response_model=WebhookResponse,
    summary="Stripe webhook endpoint",
    include_in_schema=False,  # don't expose to OpenAPI clients
)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(
        None, alias="Stripe-Signature",
    ),
    provider: BillingProvider = Depends(get_provider),
    db_path: str = Depends(get_db_path),
) -> WebhookResponse:
    """Stripe delivers events here on subscription lifecycle changes.

    Verifies HMAC signature; dispatches to the handler registry;
    returns 200 regardless of handler outcome (Stripe retries on 5xx
    which we don't want for idempotent handler failures).
    """
    raw_body = await request.body()
    # Verify signature — raises WebhookSignatureError on failure
    # (mapped to 400 by the global error handler).
    event = provider.verify_webhook_signature(
        raw_body, stripe_signature or "",
    )
    result = dispatch_event(event, db_path=db_path)
    return WebhookResponse(
        received=result.received,
        processed=result.processed,
        event_id=result.event_id,
        event_type=result.event_type,
    )
