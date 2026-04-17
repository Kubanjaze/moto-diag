"""Inventory package — parts inventory + vendors + recalls + warranties.

Phase 118 (Retrofit): schema + CRUD only. Track O phases 282-287 wire up
vendor order integrations, NHTSA recall lookups, and warranty claim tracking.
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
    add_recall, get_recall, list_recalls_for_vehicle, list_recalls,
    delete_recall,
)
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
    "add_recall", "get_recall", "list_recalls_for_vehicle", "list_recalls",
    "delete_recall",
    "add_warranty", "get_warranty", "list_warranties_for_vehicle",
    "increment_claim_count", "delete_warranty",
]
