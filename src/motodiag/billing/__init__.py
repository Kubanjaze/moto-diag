"""Billing package — subscriptions + payments + Stripe integration.

Phase 118 (Retrofit): schema + basic CRUD.
Phase 176 (Track H): adds Stripe billing-cycle columns, BillingProvider
ABC with Fake + Stripe implementations, webhook dispatch with event-id
idempotency.
"""

from motodiag.billing.models import (
    SubscriptionTier, SubscriptionStatus, PaymentStatus,
    Subscription, Payment,
)
from motodiag.billing.subscription_repo import (
    ActiveSubscription,
    create_subscription, get_subscription, get_subscription_by_user,
    get_active_subscription, get_subscription_by_stripe_id,
    list_subscriptions, update_subscription, delete_subscription,
    upsert_from_stripe,
)
from motodiag.billing.payment_repo import (
    record_payment, get_payment, list_payments,
    update_payment_status, delete_payment,
)

# Phase 176 additions: provider ABC + webhook dispatch
from motodiag.billing.providers import (
    BillingProvider,
    BillingProviderError,
    CheckoutSessionResult,
    FakeBillingProvider,
    StripeBillingProvider,
    StripeLibraryMissingError,
    WebhookSignatureError,
    get_billing_provider,
)
from motodiag.billing.webhook_handlers import (
    HANDLERS,
    WebhookDispatchResult,
    dispatch_event,
)


__all__ = [
    # Models (Phase 118)
    "SubscriptionTier", "SubscriptionStatus", "PaymentStatus",
    "Subscription", "Payment",
    # Subscription repo (Phase 118 + 176 extensions)
    "ActiveSubscription",
    "create_subscription", "get_subscription", "get_subscription_by_user",
    "get_active_subscription", "get_subscription_by_stripe_id",
    "list_subscriptions", "update_subscription", "delete_subscription",
    "upsert_from_stripe",
    # Payment repo (Phase 118)
    "record_payment", "get_payment", "list_payments",
    "update_payment_status", "delete_payment",
    # Providers (Phase 176)
    "BillingProvider",
    "BillingProviderError",
    "CheckoutSessionResult",
    "FakeBillingProvider",
    "StripeBillingProvider",
    "StripeLibraryMissingError",
    "WebhookSignatureError",
    "get_billing_provider",
    # Webhook dispatch (Phase 176)
    "HANDLERS",
    "WebhookDispatchResult",
    "dispatch_event",
]
