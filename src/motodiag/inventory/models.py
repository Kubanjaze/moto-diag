"""Inventory Pydantic models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CoverageType(str, Enum):
    POWERTRAIN = "powertrain"
    COMPREHENSIVE = "comprehensive"
    EXTENDED = "extended"
    AFTERMARKET = "aftermarket"


class InventoryItem(BaseModel):
    id: Optional[int] = None
    sku: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    make: Optional[str] = None
    model_applicable: list[str] = Field(default_factory=list)
    quantity_on_hand: int = 0
    reorder_point: int = 0
    unit_cost: float = 0.0
    unit_price: float = 0.0
    vendor_id: Optional[int] = None
    location: Optional[str] = None


class Vendor(BaseModel):
    id: Optional[int] = None
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class Recall(BaseModel):
    id: Optional[int] = None
    campaign_number: str
    make: str
    model: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    description: str
    severity: str = "medium"
    remedy: Optional[str] = None
    notification_date: Optional[str] = None


class Warranty(BaseModel):
    id: Optional[int] = None
    vehicle_id: int
    coverage_type: CoverageType
    provider: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    mileage_limit: Optional[int] = None
    terms: Optional[str] = None
    claim_count: int = 0
