"""Inventory package — parts inventory + vendors + recalls + warranties.

Phase 118 (Retrofit): schema + CRUD. Phase 274 wired it: reorder points and
local purchase orders (``purchase_orders``, row 279) and warranty validity
and claim records (``warranty_claims``, row 280), reached through ``motodiag
shop inventory`` and ``motodiag shop warranty``. Row 281 is NHTSA recall
processing; rows 282-286, the supplier integrations, and row 362, claim
submission to a maker, are paused.
"""

from motodiag.inventory.models import (
    CoverageType, InventoryItem, Vendor, Recall, Warranty,
)
from motodiag.inventory.item_repo import (
    add_item, get_item, get_item_by_sku, list_items, update_item,
    delete_item, adjust_quantity, items_below_reorder,
)
from motodiag.inventory.vendor_repo import (
    add_vendor, get_vendor, get_vendor_by_name, list_vendors,
    update_vendor, delete_vendor,
)
from motodiag.inventory.recall_repo import (
    list_recalls_for_vehicle, )
from motodiag.inventory.warranty_repo import (
    add_warranty, get_warranty, list_warranties_for_vehicle,
    increment_claim_count, delete_warranty,
)

__all__ = [
    "CoverageType", "InventoryItem", "Vendor", "Recall", "Warranty",
    "add_item", "get_item", "get_item_by_sku", "list_items", "update_item",
    "delete_item", "adjust_quantity", "items_below_reorder",
    "add_vendor", "get_vendor", "get_vendor_by_name", "list_vendors",
    "update_vendor", "delete_vendor",
    "list_recalls_for_vehicle", "add_warranty", "get_warranty", "list_warranties_for_vehicle",
    "increment_claim_count", "delete_warranty",
]
