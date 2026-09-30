"""Shared helpers for Phase 275's tests (Track O batch 2).

Every capability is reached through a `motodiag` command against a scratch
database; the CLI helpers are 274's.
"""

from __future__ import annotations

from support.phase274 import new_db, ok, refused, seed_bike, seed_customer, seed_shop, seed_user, sql

__all__ = ["new_db", "ok", "refused", "sql", "seed_booking_shop", "seed_member",
           "seed_bay_slot", "MONDAY", "TUESDAY", "WEDNESDAY"]

MONDAY = "2026-10-05"
TUESDAY = "2026-10-06"
WEDNESDAY = "2026-10-07"


def seed_member(db_path: str, shop_id: int, username: str, full_name: str | None = None,
                role: str = "tech") -> int:
    user_id = seed_user(db_path, username)
    if full_name:
        sql(db_path, "UPDATE users SET full_name = ? WHERE id = ?", (full_name, user_id))
    sql(db_path, "INSERT INTO shop_members (user_id, shop_id, role, is_active) "
                 "VALUES (?, ?, ?, 1)", (user_id, shop_id, role))
    return user_id


def seed_booking_shop(db_path: str) -> dict:
    """A shop open Monday and Tuesday 08:00-17:00, two customers, two mechanics.

    Dana (customer 2) owns bike 1; Sam (customer 3) owns bike 2.
    """
    shop = seed_shop(db_path, "Twin Peaks Moto")
    sql(db_path, "UPDATE shops SET hours_json = ?, address = ?, city = ?, state = ?, "
                 "zip = ?, phone = ? WHERE id = ?",
        ('{"mon": "08:00-17:00", "tue": "08:00-17:00"}', "12 Mill Rd", "Lowell",
         "MA", "01852", "555-0101", shop))
    dana = seed_customer(db_path, shop, "Dana Reyes", "dana@example.com")
    sam = seed_customer(db_path, shop, "Sam Ortiz", "sam@example.com")
    bike1 = seed_bike(db_path, "Honda", "CB500F", 2020)
    bike2 = seed_bike(db_path, "Yamaha", "MT-07", 2021)
    sql(db_path, "INSERT INTO customer_bikes (customer_id, vehicle_id, relationship) "
                 "VALUES (?, ?, 'owner'), (?, ?, 'owner')", (dana, bike1, sam, bike2))
    alex = seed_member(db_path, shop, "alex", "Alex Kim")
    jo = seed_member(db_path, shop, "jo", "Jo Park")
    return {"shop": shop, "dana": dana, "sam": sam, "bike1": bike1, "bike2": bike2,
            "alex": alex, "jo": jo}


def seed_bay_slot(db_path: str, shop_id: int, mechanic: int, customer: int, bike: int,
                  start: str, end: str, bay_name: str = "Lift A",
                  status: str = "planned") -> dict:
    """A work order assigned to ``mechanic`` with one slot in a bay (created if new)."""
    existing = sql(db_path, "SELECT id FROM shop_bays WHERE shop_id = ? AND name = ?",
                   (shop_id, bay_name))
    if existing:
        bay = existing[0][0]
    else:
        sql(db_path, "INSERT INTO shop_bays (shop_id, name) VALUES (?, ?)", (shop_id, bay_name))
        bay = sql(db_path, "SELECT MAX(id) FROM shop_bays")[0][0]
    sql(db_path, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title, "
                 "assigned_mechanic_user_id) VALUES (?, ?, ?, 'Valve adjust', ?)",
        (shop_id, bike, customer, mechanic))
    wo = sql(db_path, "SELECT MAX(id) FROM work_orders")[0][0]
    sql(db_path, "INSERT INTO bay_schedule_slots (bay_id, work_order_id, scheduled_start, "
                 "scheduled_end, status) VALUES (?, ?, ?, ?, ?)",
        (bay, wo, start, end, status))
    slot = sql(db_path, "SELECT MAX(id) FROM bay_schedule_slots")[0][0]
    return {"bay": bay, "wo": wo, "slot": slot}
