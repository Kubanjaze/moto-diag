"""Phase 244M — the erase path, which ships with the store rather than after it.

A compiled memory is an inference drawn about a person to build a profile. It
is deletable on request, and it is **not** in the set of records a repair shop
is required to retain -- California BAR's mandate covers invoices, estimates
and work orders, and nothing else. So the memory has no retention
justification, while the work orders it was compiled *from* have a mandatory
one.

That asymmetry is the whole design of this module:

    the compiled fact is deleted; the record it came from is not touched.

Erasing the origin row would destroy a mandated record to satisfy a request
that never reached it. Keeping the compiled fact would refuse a request that
does.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from motodiag.core.database import get_connection

# `customers` row 1 is named "Unassigned" -- it is a sentinel meaning "no
# customer", not a person. Migration 046 already encodes this convention.
SENTINEL_CUSTOMER_ID = 1


@dataclass
class ErasePlan:
    """What an erasure request would remove, before it removes it."""

    customer_id: int
    refused: bool
    reason: str = ""
    vehicle_ids: list[int] = None  # type: ignore[assignment]
    fact_count: int = 0

    def __post_init__(self) -> None:
        if self.vehicle_ids is None:
            self.vehicle_ids = []


def erase_plan(customer_id: int, db_path: Optional[str] = None) -> ErasePlan:
    """Resolve customer -> vehicles -> facts, without deleting anything.

    Refuses the sentinel. Every vehicle in the database carries
    ``customer_id = 1`` by default, so accepting it would match the entire
    shop's memory under the banner of one person's erasure request -- a
    deletion nobody asked for, justified by a key that means "unknown".
    """
    if customer_id == SENTINEL_CUSTOMER_ID:
        return ErasePlan(
            customer_id=customer_id,
            refused=True,
            reason=(
                "Customer 1 is the `Unassigned` sentinel, not a person. Every "
                "vehicle carries it by default, so erasing it would delete "
                "the memory of every machine in the shop. Assign real "
                "ownership with `motodiag memory attach` first."
            ),
        )

    with get_connection(db_path) as conn:
        vehicle_ids = [
            r[0]
            for r in conn.execute(
                "SELECT id FROM vehicles WHERE customer_id = ?", (customer_id,)
            )
        ]
        # customer_bikes is the junction the schema intends for ownership and
        # is empty today. Read it anyway: an erasure request must not miss a
        # machine because the link lives in the other table.
        try:
            vehicle_ids.extend(
                r[0]
                for r in conn.execute(
                    "SELECT vehicle_id FROM customer_bikes WHERE customer_id = ?",
                    (customer_id,),
                )
            )
        except Exception:
            pass

        vehicle_ids = sorted(set(vehicle_ids))
        if not vehicle_ids:
            return ErasePlan(customer_id=customer_id, refused=False, fact_count=0)

        placeholders = ", ".join("?" for _ in vehicle_ids)
        count = conn.execute(
            f"SELECT COUNT(*) FROM memory_facts WHERE vehicle_id IN ({placeholders})",
            vehicle_ids,
        ).fetchone()[0]
        # --dry-run must report what --no-dry-run deletes. Counting only
        # memory_facts while the delete also removes interactions would make
        # the preview a lie in exactly the situation it exists to prevent.
        try:
            count += conn.execute(
                "SELECT COUNT(*) FROM guidance_interactions "
                f"WHERE vehicle_id IN ({placeholders})",
                vehicle_ids,
            ).fetchone()[0]
        except Exception:
            pass

    return ErasePlan(
        customer_id=customer_id,
        refused=False,
        vehicle_ids=vehicle_ids,
        fact_count=count,
    )


def erase_customer(customer_id: int, db_path: Optional[str] = None) -> int:
    """Hard-delete one customer's compiled memory. Returns ROWS DELETED.

    Hard, not soft. A tombstoned row is still the personal data, and a
    deletion request that leaves the data in place with a flag set is not a
    deletion. Origin rows -- work orders, sessions, invoices -- are untouched.
    """
    plan = erase_plan(customer_id, db_path=db_path)
    if plan.refused or not plan.vehicle_ids:
        return 0

    placeholders = ", ".join("?" for _ in plan.vehicle_ids)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"DELETE FROM memory_facts WHERE vehicle_id IN ({placeholders})",
            plan.vehicle_ids,
        )
        deleted = cursor.rowcount

        # Phase 244N: a guidance question is a person's own words about their
        # machine -- free text that will eventually contain a name or a phone
        # number, whatever the technician typed. As deletable as a compiled
        # fact, and deleted by the same request.
        try:
            cursor = conn.execute(
                "DELETE FROM guidance_interactions "
                f"WHERE vehicle_id IN ({placeholders})",
                plan.vehicle_ids,
            )
            deleted += cursor.rowcount
        except Exception:
            # Table absent at this install's schema version.
            pass

        conn.commit()
        return deleted


def attach_vehicle(
    vehicle_id: int, customer_id: int, db_path: Optional[str] = None
) -> None:
    """Give a machine a real owner, so erasure can ever resolve to a person.

    Refuses the sentinel as a *target*: writing `customer_id = 1` is how the
    database got into the state where ownership data looks present and is not.
    """
    if customer_id == SENTINEL_CUSTOMER_ID:
        raise ValueError(
            "Customer 1 is the `Unassigned` sentinel. Attaching a machine to "
            "it records no ownership -- create the customer first."
        )

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"No customer with id {customer_id}")
        if conn.execute(
            "SELECT id FROM vehicles WHERE id = ?", (vehicle_id,)
        ).fetchone() is None:
            raise ValueError(f"No vehicle with id {vehicle_id}")

        conn.execute(
            "UPDATE vehicles SET customer_id = ? WHERE id = ?",
            (customer_id, vehicle_id),
        )
        # ON CONFLICT DO NOTHING, not INSERT OR REPLACE / OR IGNORE: the
        # OR-forms suppress CHECK violations too, which is how a typo'd value
        # gets silently dropped (Phase 244D, caught by Phases 211/235B).
        conn.execute(
            "INSERT INTO customer_bikes "
            "(customer_id, vehicle_id, relationship) VALUES (?, ?, 'owner') "
            "ON CONFLICT DO NOTHING",
            (customer_id, vehicle_id),
        )
        conn.commit()
