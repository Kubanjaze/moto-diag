"""Accounting Pydantic models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class InvoiceLineItemType(str, Enum):
    LABOR = "labor"
    PARTS = "parts"
    DIAGNOSTIC = "diagnostic"
    MISC = "misc"


class Invoice(BaseModel):
    id: Optional[int] = None
    customer_id: int
    repair_plan_id: Optional[int] = None
    invoice_number: str
    status: InvoiceStatus = InvoiceStatus.DRAFT
    subtotal: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    issued_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None


class InvoiceLineItem(BaseModel):
    id: Optional[int] = None
    invoice_id: int
    item_type: InvoiceLineItemType
    description: str
    quantity: float = Field(default=1.0, gt=0.0)
    unit_price: float = 0.0
    line_total: float = 0.0
    source_repair_plan_item_id: Optional[int] = None
    sort_order: int = 0
