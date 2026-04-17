"""Billing package — subscriptions + payments substrate.

Phase 118 (Retrofit): schema + CRUD only. Track O phases 273-277 wire up
Stripe integration; Track S phases 328-329 build the customer-facing
billing portal.
"""

from motodiag.billing.models import (
    SubscriptionTier, SubscriptionStatus, PaymentStatus,
    Subscription, Payment,
)
from motodiag.billing.subscription_repo import (
    create_subscription, get_subscription, get_subscription_by_user,
    list_subscriptions, update_subscription, delete_subscription,
)
from motodiag.billing.payment_repo import (
    record_payment, get_payment, list_payments,
    update_payment_status, delete_payment,
)

__all__ = [
    "SubscriptionTier", "SubscriptionStatus", "PaymentStatus",
    "Subscription", "Payment",
    "create_subscription", "get_subscription", "get_subscription_by_user",
    "list_subscriptions", "update_subscription", "delete_subscription",
    "record_payment", "get_payment", "list_payments",
    "update_payment_status", "delete_payment",
]
