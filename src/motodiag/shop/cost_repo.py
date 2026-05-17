"""Cloud-API cost ledger repository — Phase 195B (Commit 0).

Function-based repo over the `cost_events` table (migration 043),
mirroring the `transcript_repo` / `video_repo` shape (plain sqlite3
row dicts via `get_connection`).

`cost_events` is the granular ledger backing Phase 195B's cost
monitoring (Risk 8 from the Phase 195 pre-plan): one row per cloud-
API call — OpenAI Whisper transcription + Claude-rich extraction.
The repo provides the write path (`record_cost_event`) + the
aggregation read path (`aggregate_costs`, `shop_cost_this_month`)
that the `motodiag costs report` CLI + the soft per-shop cap
consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

from motodiag.core.database import get_connection


# Mirrors the migration-043 `kind` CHECK constraint. Literal from
# day one per F37 Track 1 discipline (Phase 195B plan §7).
CostEventKind = Literal["whisper", "claude_extraction"]


def _now_iso() -> str:
    """UTC now in SQLite `datetime('now')`-compatible format
    (space-separated, no microseconds/tz — lex-comparable against
    `created_at`). Same convention as `transcript_repo`."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _month_start_iso() -> str:
    """First instant of the current UTC calendar month, in the same
    SQLite-comparable format. Matches `transcript_repo._month_start_iso`
    (the 2026-05-01 boundary-bug fix shape)."""
    now = datetime.now(timezone.utc)
    return now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    ).strftime("%Y-%m-%d %H:%M:%S")


def record_cost_event(
    kind: CostEventKind,
    model: str,
    cost_usd_cents: int,
    *,
    transcript_id: Optional[int] = None,
    shop_id: Optional[int] = None,
    units_label: Optional[str] = None,
    units_value: Optional[int] = None,
    db_path: Optional[str] = None,
) -> int:
    """Insert one cost-ledger row; return its id.

    `units_label` / `units_value` are the kind-polymorphic measure —
    `('duration_ms', N)` for Whisper, `('tokens', N)` for Claude.
    `shop_id` is denormalized onto the row (not joined through the
    transcript) so per-shop rollups survive transcript deletion +
    aggregate fast.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO cost_events (
                   kind, model, transcript_id, shop_id,
                   units_label, units_value, cost_usd_cents,
                   created_at
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                kind, model, transcript_id, shop_id,
                units_label, units_value, cost_usd_cents,
                _now_iso(),
            ),
        )
        return int(cursor.lastrowid)


@dataclass(frozen=True)
class CostRollup:
    """Aggregated cost figures over a window.

    `by_kind` / `by_model` map the discriminator to total cents.
    `total_usd_cents` is the grand total; `event_count` is the row
    count over the window.
    """

    total_usd_cents: int
    event_count: int
    by_kind: dict[str, int]
    by_model: dict[str, int]


def aggregate_costs(
    *,
    since: Optional[str] = None,
    shop_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> CostRollup:
    """Roll up `cost_events` over an optional window + optional shop.

    `since` is an inclusive lower bound on `created_at` (SQLite-
    comparable string, e.g. `'2026-05-01 00:00:00'`); `None` means
    all-time. `shop_id` filters to one shop; `None` means all shops.
    """
    where: list[str] = []
    params: list = []
    if since is not None:
        where.append("created_at >= ?")
        params.append(since)
    if shop_id is not None:
        where.append("shop_id = ?")
        params.append(shop_id)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"""SELECT kind, model, cost_usd_cents
                FROM cost_events {clause}""",
            tuple(params),
        ).fetchall()

    total = 0
    count = 0
    by_kind: dict[str, int] = {}
    by_model: dict[str, int] = {}
    for r in rows:
        cents = int(r["cost_usd_cents"])
        total += cents
        count += 1
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + cents
        by_model[r["model"]] = by_model.get(r["model"], 0) + cents
    return CostRollup(
        total_usd_cents=total,
        event_count=count,
        by_kind=by_kind,
        by_model=by_model,
    )


def shop_cost_this_month(
    shop_id: int, db_path: Optional[str] = None,
) -> int:
    """Total USD cents a shop has accrued so far this calendar month.

    Used by the soft per-shop cap check: callers compare this against
    `Settings.cost_cap_monthly_usd_cents` + log/alert on exceed (the
    cap does NOT block — hard enforcement is a Track H billing
    concern).
    """
    rollup = aggregate_costs(
        since=_month_start_iso(), shop_id=shop_id, db_path=db_path,
    )
    return rollup.total_usd_cents
