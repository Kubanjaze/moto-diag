"""Phase 244M — the fact row, its key, and the only two ways in and out.

A "fact" here is deliberately small: one thing established about one machine at
one time, carrying where it came from. Facts are never mutated. A later fact
supersedes an earlier one by setting ``superseded_at`` on it, so the record of
what the shop believed and when survives being wrong.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional, Sequence

from motodiag.core.database import get_connection

# Kept in lockstep with migration 058's CHECK constraints. The tests assert
# they match the database rather than each other, so a divergence fails
# loudly instead of producing rows the database will reject at insert time.
FACT_KINDS: tuple[str, ...] = (
    "complaint",
    "observation",
    "repair",
    "part-replaced",
    "measurement",
    "correction",
)

SOURCES: tuple[str, ...] = (
    "mechanic-verified",
    "model-generated",
    "customer-reported",
    "service-record",
)


@dataclass(frozen=True)
class MemoryFact:
    """One established thing about one machine.

    ``established_at`` is when the fact became true in the shop's world -- the
    date of the repair, the session, the observation -- and NOT when the row
    was written. Recall displays it, so conflating the two would show a
    ten-year-old repair as today's news.
    """

    vehicle_id: int
    fact_kind: str
    subject: str
    source: str
    origin_table: str
    established_at: str
    value: str = ""
    origin_id: Optional[int] = None
    at_miles: Optional[int] = None
    superseded_at: Optional[str] = None
    id: Optional[int] = field(default=None, compare=False)

    def key(self) -> str:
        return fact_key(
            vehicle_id=self.vehicle_id,
            fact_kind=self.fact_kind,
            subject=self.subject,
            origin_table=self.origin_table,
            origin_id=self.origin_id,
        )


def fact_key(
    *,
    vehicle_id: int,
    fact_kind: str,
    subject: str,
    origin_table: str,
    origin_id: Optional[int],
) -> str:
    """Deterministic identity for a fact, so re-compiling inserts nothing.

    ``origin_id`` is nullable, and that is the whole reason this function
    exists rather than a plain UNIQUE constraint over the columns. **SQLite
    treats NULLs as DISTINCT in a UNIQUE constraint**, so two facts differing
    only by a NULL ``origin_id`` would both be accepted and every re-compile
    would duplicate them. Phase 244D hit exactly this on `known_issues` and
    proved it with a three-insert probe before trusting it.

    The fix is to COALESCE the nullable component into the hashed material, so
    "no origin id" is a value like any other.
    """
    material = "\x1f".join(
        (
            str(vehicle_id),
            fact_kind,
            subject.strip().lower(),
            origin_table,
            # COALESCE, spelled in Python. The sentinel must not collide with
            # a real id, which is why it is not "" or "0".
            "\x00none\x00" if origin_id is None else str(origin_id),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def insert_facts(
    facts: Sequence[MemoryFact],
    db_path: Optional[str] = None,
) -> int:
    """Insert facts, skipping ones already present. Returns ROWS INSERTED.

    Two things this function refuses to do, both learned the hard way:

    It does not use ``INSERT OR IGNORE``. That form suppresses **CHECK**
    violations as well as uniqueness ones, so a typo'd ``source`` would be
    silently dropped rather than raising -- the corpus loader shipped that bug
    at Phase 244D and Phases 211/235B caught it. ``ON CONFLICT DO NOTHING``
    narrows the suppression to the conflict that is actually expected.

    It does not report the number of facts it walked. Phase 244D's loader
    reported items walked and a re-seed cheerfully announced "970 inserted"
    while inserting nothing. ``cursor.rowcount`` is summed instead, so the
    number returned is the number of rows that landed.
    """
    if not facts:
        return 0

    inserted = 0
    with get_connection(db_path) as conn:
        for fact in facts:
            cursor = conn.execute(
                """
                INSERT INTO memory_facts
                    (vehicle_id, fact_kind, subject, value, source,
                     origin_table, origin_id, at_miles, established_at,
                     superseded_at, fact_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fact_key) DO NOTHING
                """,
                (
                    fact.vehicle_id,
                    fact.fact_kind,
                    fact.subject,
                    fact.value,
                    fact.source,
                    fact.origin_table,
                    fact.origin_id,
                    fact.at_miles,
                    fact.established_at,
                    fact.superseded_at,
                    fact.key(),
                ),
            )
            inserted += cursor.rowcount if cursor.rowcount > 0 else 0
        conn.commit()
    return inserted


def list_facts(
    vehicle_id: int,
    *,
    kinds: Optional[Sequence[str]] = None,
    include_superseded: bool = False,
    db_path: Optional[str] = None,
) -> list[MemoryFact]:
    """Return one machine's facts, newest established first.

    Ordering is by ``established_at`` and then ``id``, because two facts
    compiled from the same day's work share a date and would otherwise come
    back in an order SQLite is free to change between runs.
    """
    sql = [
        "SELECT id, vehicle_id, fact_kind, subject, value, source,",
        "       origin_table, origin_id, at_miles, established_at,",
        "       superseded_at",
        "FROM memory_facts WHERE vehicle_id = ?",
    ]
    params: list[object] = [vehicle_id]

    if not include_superseded:
        sql.append("AND superseded_at IS NULL")
    if kinds:
        placeholders = ", ".join("?" for _ in kinds)
        sql.append(f"AND fact_kind IN ({placeholders})")
        params.extend(kinds)
    sql.append("ORDER BY established_at DESC, id DESC")

    with get_connection(db_path) as conn:
        rows = conn.execute(" ".join(sql), params).fetchall()

    return [
        MemoryFact(
            id=r[0],
            vehicle_id=r[1],
            fact_kind=r[2],
            subject=r[3],
            value=r[4],
            source=r[5],
            origin_table=r[6],
            origin_id=r[7],
            at_miles=r[8],
            established_at=r[9],
            superseded_at=r[10],
        )
        for r in rows
    ]
