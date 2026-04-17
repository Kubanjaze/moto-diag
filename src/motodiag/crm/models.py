"""CRM Pydantic models.

Phase 113: Customer and CustomerBike models, CustomerRelationship enum for
ownership history tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class CustomerRelationship(str, Enum):
    """Relationship between a customer and a vehicle.

    Captures ownership history: a bike may have a current owner, previous
    owners (useful for pre-purchase inspections, warranty claims, recall
    outreach), and interested parties (prospects who test-rode).
    """
    OWNER = "owner"                    # Current owner
    PREVIOUS_OWNER = "previous_owner"  # Historical owner
    INTERESTED = "interested"          # Prospect (test ride, shopping)


class Customer(BaseModel):
    """A customer of a shop.

    Customers are scoped to a shop/user via owner_user_id — a solo mechanic
    sees only their customers, a shop sees the shop's customers. This
    prevents customer data leakage in multi-tenant deployments (Track H).
    """
    id: Optional[int] = Field(None, description="Primary key")
    owner_user_id: int = Field(
        default=1,
        description="User (shop owner) who owns this customer relationship. Defaults to system user for placeholder.",
    )
    name: str = Field(..., description="Customer's full name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number (free-form — international OK)")
    address: Optional[str] = Field(None, description="Street address for invoicing / parts shipping")
    notes: Optional[str] = Field(None, description="Shop-private notes about this customer")
    is_active: bool = Field(default=True, description="Whether the customer relationship is active")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CustomerBike(BaseModel):
    """A customer-vehicle link with relationship type and optional metadata."""
    customer_id: int = Field(..., description="Customer ID")
    vehicle_id: int = Field(..., description="Vehicle ID")
    relationship: CustomerRelationship = Field(
        default=CustomerRelationship.OWNER,
        description="Ownership relationship (owner / previous_owner / interested)",
    )
    assigned_at: Optional[datetime] = Field(None, description="When this relationship was recorded")
    notes: Optional[str] = Field(None, description="Optional notes (e.g., 'traded up to larger bike')")
