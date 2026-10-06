"""A shop's Terminal location and simulated reader (Phase 273).

Server-driven: no reader SDK runs here. With direct charges the shop owns
its locations and readers, so every request is made on the shop's account
(Stripe, C7). Only Stripe's simulated reader is registered by this phase;
a physical reader needs a live account (row 371).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from motodiag.core.config import Settings, get_settings
from motodiag.core.database import get_connection
from motodiag.payments import stripe_api
from motodiag.payments.connect import ConnectError, require_payable_account
from motodiag.shop.shop_repo import get_shop

ADDRESS_FIELDS = ("line1", "city", "state", "postal_code")


@dataclass(frozen=True)
class Reader:
    id: int
    shop_id: int
    stripe_reader_id: str
    label: str
    simulated: bool
    stripe_location_id: str


def get_reader(shop_id: int, db_path: Optional[str] = None) -> Optional[Reader]:
    """The shop's newest reader."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT r.id, r.shop_id, r.stripe_reader_id, r.label, r.simulated, "
            "l.stripe_location_id FROM terminal_readers r "
            "JOIN terminal_locations l ON l.id = r.location_id "
            "WHERE r.shop_id = ? ORDER BY r.id DESC LIMIT 1",
            (shop_id,),
        ).fetchone()
    if row is None:
        return None
    return Reader(row["id"], row["shop_id"], row["stripe_reader_id"],
                  row["label"], bool(row["simulated"]), row["stripe_location_id"])


def _address(shop: dict, country: str, given: dict) -> dict:
    from_shop = {
        "line1": shop.get("address"),
        "city": shop.get("city"),
        "state": shop.get("state"),
        "postal_code": shop.get("zip"),
    }
    address = {k: (given.get(k) or from_shop.get(k)) for k in ADDRESS_FIELDS}
    missing = [k for k, v in address.items() if not v]
    if missing:
        raise ConnectError(
            "a Terminal location needs the shop's address; missing "
            + ", ".join(missing)
            + " (pass --line1, --city, --state, --postal-code, or record them on the shop)"
        )
    address["country"] = country.upper()
    return address


def setup_simulated_reader(shop_id: int, *, address: Optional[dict] = None,
                           label: Optional[str] = None,
                           settings: Optional[Settings] = None,
                           db_path: Optional[str] = None) -> Reader:
    """Create a location on the shop's account and register Stripe's
    simulated reader at it. Test mode only."""
    s = settings or get_settings()
    if not stripe_api.is_test_key(s.stripe_api_key):
        raise ConnectError("the simulated reader exists only in test mode")
    shop = get_shop(shop_id, db_path=db_path)
    if shop is None:
        raise ConnectError(f"shop not found: id={shop_id}")
    acct = require_payable_account(shop_id, db_path=db_path)
    addr = _address(shop, acct.country, address or {})
    opts = {"stripe_account": acct.stripe_account_id}
    sc = stripe_api.client(s)
    location = stripe_api.as_dict(stripe_api.call(
        "create a Terminal location",
        lambda: sc.v1.terminal.locations.create(
            {"display_name": shop["name"], "address": addr}, opts),
    ))
    reader_label = label or f"{shop['name']} simulated reader"
    reader = stripe_api.as_dict(stripe_api.call(
        "register the simulated reader",
        lambda: sc.v1.terminal.readers.create({
            "registration_code": stripe_api.SIMULATED_READER_CODE,
            "label": reader_label,
            "location": location["id"],
        }, opts),
    ))
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO terminal_locations
               (shop_id, stripe_account_id, stripe_location_id, display_name,
                address_json, livemode) VALUES (?, ?, ?, ?, ?, ?)""",
            (shop_id, acct.stripe_account_id, location["id"], shop["name"],
             json.dumps(addr, sort_keys=True), 1 if location.get("livemode") else 0),
        )
        conn.execute(
            """INSERT INTO terminal_readers
               (shop_id, location_id, stripe_reader_id, label, device_type,
                simulated, livemode) VALUES (?, ?, ?, ?, ?, 1, ?)""",
            (shop_id, cur.lastrowid, reader["id"], reader.get("label") or reader_label,
             reader.get("device_type"), 1 if reader.get("livemode") else 0),
        )
    return get_reader(shop_id, db_path=db_path)
