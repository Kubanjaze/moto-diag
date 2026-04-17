"""Billing Pydantic models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SubscriptionTier(str, Enum):
    """Mirrors Phase 109 MOTODIAG_SUBSCRIPTION_TIER env var."""
    INDIVIDUAL = "individual"
    SHOP = "shop"
    COMPANY = "company"


class SubscriptionStatus(str, Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class Subscription(BaseModel):
    id: Optional[int] = None
    user_id: int
    tier: SubscriptionTier = SubscriptionTier.INDIVIDUAL
    status: SubscriptionStatus = SubscriptionStatus.TRIALING
    started_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None


class Payment(BaseModel):
    id: Optional[int] = None
    user_id: int
    subscription_id: Optional[int] = None
    amount: float = Field(..., ge=0.0)
    currency: str = "USD"
    status: PaymentStatus = PaymentStatus.PENDING
    stripe_payment_intent_id: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
