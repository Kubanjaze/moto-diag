"""Shop analytics dashboard (Phase 171).

Read-only deterministic rollups over existing Track G state. Zero new
tables, zero migrations, zero AI. Each rollup is a stateless pure
function returning a Pydantic summary; :func:`dashboard_snapshot`
composes them + the Phase 169 revenue rollup into one view. Phase 274
adds :func:`financial_report` (a gross-margin P&L on the costs
``shop/shop_costs.py`` records, migration 076) and
:func:`estimate_variance`; neither changes the models the API serves.

Timestamp comparisons parse both sides: ``datetime(col) >= ?`` against
:func:`_parse_date_window`'s UTC cutoff, because the shop's columns hold
SQLite's ``CURRENT_TIMESTAMP`` shape beside ``core/timestamps``' format
(Phase 377, F186). Days, months and display are the shop's local time,
which is the server's zone (F192).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from statistics import mean, median
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from motodiag.core.database import get_connection
from motodiag.core.timestamps import (
    local_day, local_day_start, stored_instant, utc_cutoff,
)
from motodiag.shop.bay_scheduler import utilization_for_day
from motodiag.shop.invoicing import RevenueRollup, revenue_rollup
from motodiag.shop.shop_costs import (
    cost_rate_on,
    list_expenses,
    list_mechanic_cost_rates,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


UTILIZATION_OVER_THRESHOLD = 0.90
P90_MIN_SAMPLE = 5
WINDOW_PATTERN = re.compile(r"^(\d+)([dhm])$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


def _parse_date_window(since: str) -> str:
    """``Nd``/``Nh``/``Nm`` or an ISO date or time, as :func:`utc_cutoff`'s
    UTC ``YYYY-MM-DD HH:MM:SS``, compared with ``datetime(col) >= ?``.

    A typed time with no zone is the shop's (local) time (Phase 377).
    """
    if since is None:
        raise ValueError("since cannot be None")
    since = str(since).strip()
    if not since:
        raise ValueError("since cannot be empty")
    if WINDOW_PATTERN.match(since):
        since = since.lower()
    return utc_cutoff(since)


def _open_to_complete_hours(row) -> float:
    """Hours from a work order's ``opened_at`` to its ``completed_at``.

    Both are parsed by one rule (``stored_instant``), so a value written
    before Phase 377 subtracts from one written after. A value that is not a
    time raises, naming the work order: it is never skipped in silence.
    """
    try:
        opened = stored_instant(row["opened_at"])
        completed = stored_instant(row["completed_at"])
    except ValueError as e:
        raise ValueError(
            f"work order {row['id']}: a lifecycle time is not a time "
            f"(opened_at={row['opened_at']!r}, completed_at={row['completed_at']!r})"
        ) from e
    return (completed - opened).total_seconds() / 3600.0


def _daterange(start: str, end: str) -> list[str]:
    """Inclusive day-by-day range of YYYY-MM-DD strings."""
    s = datetime.fromisoformat(start).date()
    e = datetime.fromisoformat(end).date()
    if e < s:
        raise ValueError(f"end {end!r} before start {start!r}")
    out = []
    cur = s
    while cur <= e:
        out.append(cur.isoformat())
        cur = cur + timedelta(days=1)
    return out


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class DayBucket(BaseModel):
    model_config = ConfigDict(extra="ignore")
    date: str
    count: int


class ThroughputRollup(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shop_id: int
    since: str
    by_status: dict[str, int] = Field(default_factory=dict)
    completed_total: int = 0
    completions_by_day: list[DayBucket] = Field(default_factory=list)


class TurnaroundRollup(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shop_id: int
    since: str
    sample_size: int
    mean_hours: Optional[float]
    median_hours: Optional[float]
    p90_hours: Optional[float]


class DayUtilization(BaseModel):
    model_config = ConfigDict(extra="ignore")
    date: str
    utilization: float


class UtilizationRollup(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shop_id: int
    from_date: str
    to_date: str
    days: list[DayUtilization] = Field(default_factory=list)
    mean_pct: float = 0.0
    over_threshold_days: int = 0


class OverrunRateRollup(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shop_id: int
    since: str
    total_slots: int
    overrun_slots: int
    rate: float
    by_mechanic: dict[str, float] = Field(default_factory=dict)


class LaborAccuracyRollup(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shop_id: int
    since: str
    sample_size: int
    within_count: int
    under_count: int
    over_count: int
    within_pct: float
    median_delta_pct: Optional[float]


class TopIssueRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    category: str
    severity: str
    count: int


class TopPartRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    part_id: int
    slug: str
    description: Optional[str]
    total_qty: int
    total_cost_cents: int


class MechanicPerformanceRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    mechanic_id: Optional[int]
    wos_completed: int
    avg_turnaround_hours: Optional[float]
    overrun_rate: Optional[float]
    labor_within_pct: Optional[float]


class CustomerRepeatRollup(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shop_id: int
    since: str
    total_wos: int
    repeat_wos: int
    repeat_rate: float


class DashboardSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shop_id: int
    since: str
    generated_at: str
    throughput: ThroughputRollup
    turnaround: TurnaroundRollup
    utilization: UtilizationRollup
    overrun: OverrunRateRollup
    labor_accuracy: LaborAccuracyRollup
    top_issues: list[TopIssueRow] = Field(default_factory=list)
    top_parts: list[TopPartRow] = Field(default_factory=list)
    mechanic_performance: list[MechanicPerformanceRow] = Field(
        default_factory=list
    )
    customer_repeat: CustomerRepeatRollup
    revenue: RevenueRollup


# ---------------------------------------------------------------------------
# Rollups
# ---------------------------------------------------------------------------


def throughput(
    shop_id: int, since: str = "30d", db_path: Optional[str] = None,
) -> ThroughputRollup:
    cutoff = _parse_date_window(since)
    with get_connection(db_path) as conn:
        by_status_rows = conn.execute(
            """SELECT status, COUNT(*) AS n FROM work_orders
               WHERE shop_id = ? AND datetime(created_at) >= ?
               GROUP BY status ORDER BY status""",
            (shop_id, cutoff),
        ).fetchall()
        comp_rows = conn.execute(
            """SELECT completed_at FROM work_orders
               WHERE shop_id = ? AND completed_at IS NOT NULL
                 AND datetime(completed_at) >= ?""",
            (shop_id, cutoff),
        ).fetchall()
    by_status = {r["status"]: int(r["n"]) for r in by_status_rows}
    # Grouped by the shop's day, not the UTC date SQLite's DATE() gives.
    per_day: dict[str, int] = {}
    for r in comp_rows:
        day = local_day(r["completed_at"])
        per_day[day] = per_day.get(day, 0) + 1
    completions_by_day = [
        DayBucket(date=d, count=n) for d, n in sorted(per_day.items())
    ]
    completed_total = sum(b.count for b in completions_by_day)
    return ThroughputRollup(
        shop_id=shop_id, since=since,
        by_status=by_status,
        completed_total=completed_total,
        completions_by_day=completions_by_day,
    )


def turnaround(
    shop_id: int, since: str = "30d", db_path: Optional[str] = None,
) -> TurnaroundRollup:
    cutoff = _parse_date_window(since)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT id, opened_at, completed_at FROM work_orders
               WHERE shop_id = ?
                 AND status = 'completed'
                 AND opened_at IS NOT NULL
                 AND completed_at IS NOT NULL
                 AND datetime(completed_at) >= ?""",
            (shop_id, cutoff),
        ).fetchall()
    hours: list[float] = []
    for r in rows:
        h = _open_to_complete_hours(r)
        if h < 0:
            continue
        hours.append(h)
    n = len(hours)
    mean_h = round(mean(hours), 2) if hours else None
    median_h = round(median(hours), 2) if hours else None
    p90_h: Optional[float] = None
    if n >= P90_MIN_SAMPLE:
        sorted_h = sorted(hours)
        idx = int(round(0.9 * (n - 1)))
        p90_h = round(sorted_h[idx], 2)
    return TurnaroundRollup(
        shop_id=shop_id, since=since,
        sample_size=n,
        mean_hours=mean_h, median_hours=median_h, p90_hours=p90_h,
    )


def utilization_rollup(
    shop_id: int,
    from_date: str,
    to_date: str,
    db_path: Optional[str] = None,
) -> UtilizationRollup:
    dates = _daterange(from_date, to_date)
    days: list[DayUtilization] = []
    for d in dates:
        row = utilization_for_day(shop_id, d, db_path=db_path)
        u = float(row.get("utilization") or 0.0)
        days.append(DayUtilization(date=d, utilization=u))
    mean_pct = round(
        (sum(d.utilization for d in days) / len(days)) if days else 0.0,
        4,
    )
    over = sum(
        1 for d in days if d.utilization >= UTILIZATION_OVER_THRESHOLD
    )
    return UtilizationRollup(
        shop_id=shop_id,
        from_date=from_date, to_date=to_date,
        days=days, mean_pct=mean_pct, over_threshold_days=over,
    )


def overrun_rate(
    shop_id: int, since: str = "30d", db_path: Optional[str] = None,
) -> OverrunRateRollup:
    cutoff = _parse_date_window(since)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT s.status AS status, wo.assigned_mechanic_user_id AS mech
               FROM bay_schedule_slots s
               JOIN shop_bays b ON b.id = s.bay_id
               LEFT JOIN work_orders wo ON wo.id = s.work_order_id
               WHERE b.shop_id = ?
                 AND s.status IN ('completed', 'overrun')
                 AND datetime(COALESCE(s.actual_end, s.scheduled_end)) >= ?""",
            (shop_id, cutoff),
        ).fetchall()
    total = len(rows)
    overrun = sum(1 for r in rows if r["status"] == "overrun")
    rate = round((overrun / total), 4) if total else 0.0
    # Per-mechanic
    buckets: dict[str, tuple[int, int]] = {}  # key → (overrun, total)
    for r in rows:
        key = str(r["mech"]) if r["mech"] is not None else "unassigned"
        ov, tot = buckets.get(key, (0, 0))
        if r["status"] == "overrun":
            ov += 1
        tot += 1
        buckets[key] = (ov, tot)
    by_mechanic = {
        k: round(ov / tot, 4) if tot else 0.0
        for k, (ov, tot) in sorted(buckets.items())
    }
    return OverrunRateRollup(
        shop_id=shop_id, since=since,
        total_slots=total, overrun_slots=overrun, rate=rate,
        by_mechanic=by_mechanic,
    )


def labor_accuracy(
    shop_id: int, since: str = "30d", db_path: Optional[str] = None,
) -> LaborAccuracyRollup:
    cutoff = _parse_date_window(since)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT le.adjusted_hours AS estimated,
                      wo.actual_hours AS actual
               FROM labor_estimates le
               JOIN work_orders wo ON wo.id = le.wo_id
               WHERE wo.shop_id = ?
                 AND wo.completed_at IS NOT NULL
                 AND datetime(wo.completed_at) >= ?
                 AND wo.actual_hours IS NOT NULL
                 AND le.adjusted_hours IS NOT NULL
                 AND le.id = (
                     SELECT MAX(id) FROM labor_estimates
                     WHERE wo_id = le.wo_id
                 )""",
            (shop_id, cutoff),
        ).fetchall()
    deltas: list[float] = []
    within = under = over = 0
    for r in rows:
        est = float(r["estimated"] or 0)
        act = float(r["actual"] or 0)
        if est <= 0:
            continue
        delta_pct = (act - est) / est
        deltas.append(delta_pct)
        if abs(delta_pct) <= 0.20:
            within += 1
        elif delta_pct < 0:
            under += 1
        else:
            over += 1
    n = len(deltas)
    within_pct = round(within / n, 4) if n else 0.0
    med_delta = round(median(deltas), 4) if deltas else None
    return LaborAccuracyRollup(
        shop_id=shop_id, since=since,
        sample_size=n,
        within_count=within, under_count=under, over_count=over,
        within_pct=within_pct, median_delta_pct=med_delta,
    )


def top_issues(
    shop_id: int, since: str = "30d", limit: int = 10,
    db_path: Optional[str] = None,
) -> list[TopIssueRow]:
    cutoff = _parse_date_window(since)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT i.category, i.severity, COUNT(*) AS n
               FROM issues i
               JOIN work_orders wo ON wo.id = i.work_order_id
               WHERE wo.shop_id = ? AND datetime(i.created_at) >= ?
               GROUP BY i.category, i.severity
               ORDER BY n DESC, i.category ASC, i.severity ASC
               LIMIT ?""",
            (shop_id, cutoff, int(limit)),
        ).fetchall()
    return [
        TopIssueRow(category=r["category"], severity=r["severity"],
                    count=int(r["n"]))
        for r in rows
    ]


def top_parts(
    shop_id: int, since: str = "30d", limit: int = 10,
    db_path: Optional[str] = None,
) -> list[TopPartRow]:
    cutoff = _parse_date_window(since)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT wop.part_id AS part_id,
                      p.slug AS slug,
                      p.description AS description,
                      SUM(wop.quantity) AS total_qty,
                      SUM(wop.quantity *
                          COALESCE(wop.unit_cost_cents_override,
                                   p.typical_cost_cents, 0))
                          AS total_cost_cents
               FROM work_order_parts wop
               JOIN parts p ON p.id = wop.part_id
               JOIN work_orders wo ON wo.id = wop.work_order_id
               WHERE wo.shop_id = ? AND datetime(wo.created_at) >= ?
                 AND wop.status != 'cancelled'
               GROUP BY wop.part_id
               ORDER BY total_cost_cents DESC, wop.part_id ASC
               LIMIT ?""",
            (shop_id, cutoff, int(limit)),
        ).fetchall()
    return [
        TopPartRow(
            part_id=int(r["part_id"]),
            slug=r["slug"] or "",
            description=r["description"],
            total_qty=int(r["total_qty"] or 0),
            total_cost_cents=int(r["total_cost_cents"] or 0),
        )
        for r in rows
    ]


def mechanic_performance(
    shop_id: int, since: str = "30d", db_path: Optional[str] = None,
) -> list[MechanicPerformanceRow]:
    cutoff = _parse_date_window(since)
    with get_connection(db_path) as conn:
        wo_rows = conn.execute(
            """SELECT id, assigned_mechanic_user_id AS mech,
                      opened_at, completed_at
               FROM work_orders
               WHERE shop_id = ?
                 AND status = 'completed'
                 AND datetime(completed_at) >= ?""",
            (shop_id, cutoff),
        ).fetchall()
        slot_rows = conn.execute(
            """SELECT s.status AS status,
                      wo.assigned_mechanic_user_id AS mech
               FROM bay_schedule_slots s
               JOIN shop_bays b ON b.id = s.bay_id
               JOIN work_orders wo ON wo.id = s.work_order_id
               WHERE b.shop_id = ?
                 AND s.status IN ('completed', 'overrun')
                 AND datetime(COALESCE(s.actual_end, s.scheduled_end)) >= ?""",
            (shop_id, cutoff),
        ).fetchall()
        est_rows = conn.execute(
            """SELECT wo.assigned_mechanic_user_id AS mech,
                      le.adjusted_hours AS est,
                      wo.actual_hours AS act
               FROM labor_estimates le
               JOIN work_orders wo ON wo.id = le.wo_id
               WHERE wo.shop_id = ?
                 AND wo.completed_at IS NOT NULL
                 AND datetime(wo.completed_at) >= ?
                 AND wo.actual_hours IS NOT NULL
                 AND le.adjusted_hours IS NOT NULL
                 AND le.id = (
                     SELECT MAX(id) FROM labor_estimates
                     WHERE wo_id = le.wo_id
                 )""",
            (shop_id, cutoff),
        ).fetchall()

    # Aggregate
    mechs: dict[Optional[int], dict] = {}
    for r in wo_rows:
        key = r["mech"]
        bucket = mechs.setdefault(key, {
            "wos": 0, "hours": [], "slots": 0, "overruns": 0,
            "est_within": 0, "est_total": 0,
        })
        bucket["wos"] += 1
        if r["opened_at"] is not None and r["completed_at"] is not None:
            delta = _open_to_complete_hours(r)
            if delta >= 0:
                bucket["hours"].append(delta)
    for r in slot_rows:
        key = r["mech"]
        bucket = mechs.setdefault(key, {
            "wos": 0, "hours": [], "slots": 0, "overruns": 0,
            "est_within": 0, "est_total": 0,
        })
        bucket["slots"] += 1
        if r["status"] == "overrun":
            bucket["overruns"] += 1
    for r in est_rows:
        key = r["mech"]
        bucket = mechs.setdefault(key, {
            "wos": 0, "hours": [], "slots": 0, "overruns": 0,
            "est_within": 0, "est_total": 0,
        })
        est = float(r["est"] or 0)
        act = float(r["act"] or 0)
        if est <= 0:
            continue
        bucket["est_total"] += 1
        if abs((act - est) / est) <= 0.20:
            bucket["est_within"] += 1

    def _sort_key(k):
        # None last, numerics ascending
        return (1 if k is None else 0, k if k is not None else 0)

    out: list[MechanicPerformanceRow] = []
    for key in sorted(mechs.keys(), key=_sort_key):
        b = mechs[key]
        avg_turn = (
            round(sum(b["hours"]) / len(b["hours"]), 2)
            if b["hours"] else None
        )
        overrun_r = (
            round(b["overruns"] / b["slots"], 4)
            if b["slots"] else None
        )
        within_pct = (
            round(b["est_within"] / b["est_total"], 4)
            if b["est_total"] else None
        )
        out.append(MechanicPerformanceRow(
            mechanic_id=key,
            wos_completed=b["wos"],
            avg_turnaround_hours=avg_turn,
            overrun_rate=overrun_r,
            labor_within_pct=within_pct,
        ))
    return out


def customer_repeat_rate(
    shop_id: int, since: str = "30d", db_path: Optional[str] = None,
) -> CustomerRepeatRollup:
    cutoff = _parse_date_window(since)
    with get_connection(db_path) as conn:
        total_row = conn.execute(
            """SELECT COUNT(*) AS n FROM work_orders
               WHERE shop_id = ? AND datetime(created_at) >= ?""",
            (shop_id, cutoff),
        ).fetchone()
        repeat_row = conn.execute(
            """SELECT COUNT(*) AS n FROM work_orders wo
               WHERE wo.shop_id = ? AND datetime(wo.created_at) >= ?
                 AND EXISTS (
                     SELECT 1 FROM work_orders prior
                     WHERE prior.customer_id = wo.customer_id
                       AND prior.shop_id = wo.shop_id
                       AND prior.id < wo.id
                 )""",
            (shop_id, cutoff),
        ).fetchone()
    total = int(total_row["n"]) if total_row else 0
    repeat = int(repeat_row["n"]) if repeat_row else 0
    rate = round(repeat / total, 4) if total else 0.0
    return CustomerRepeatRollup(
        shop_id=shop_id, since=since,
        total_wos=total, repeat_wos=repeat, repeat_rate=rate,
    )


def dashboard_snapshot(
    shop_id: int,
    since: str = "30d",
    utilization_window_days: int = 7,
    db_path: Optional[str] = None,
) -> DashboardSnapshot:
    """Compose all rollups + Phase 169 revenue into one snapshot."""
    now = datetime.now(timezone.utc)
    today = now.astimezone()  # the shop's day (F192)
    end_date = today.strftime("%Y-%m-%d")
    start_date = (
        today - timedelta(days=int(utilization_window_days) - 1)
    ).strftime("%Y-%m-%d")

    return DashboardSnapshot(
        shop_id=shop_id, since=since,
        generated_at=now.strftime("%Y-%m-%d %H:%M:%S"),
        throughput=throughput(shop_id, since=since, db_path=db_path),
        turnaround=turnaround(shop_id, since=since, db_path=db_path),
        utilization=utilization_rollup(
            shop_id, start_date, end_date, db_path=db_path,
        ),
        overrun=overrun_rate(shop_id, since=since, db_path=db_path),
        labor_accuracy=labor_accuracy(
            shop_id, since=since, db_path=db_path,
        ),
        top_issues=top_issues(shop_id, since=since, db_path=db_path),
        top_parts=top_parts(shop_id, since=since, db_path=db_path),
        mechanic_performance=mechanic_performance(
            shop_id, since=since, db_path=db_path,
        ),
        customer_repeat=customer_repeat_rate(
            shop_id, since=since, db_path=db_path,
        ),
        revenue=revenue_rollup(
            shop_id=shop_id, since=since, db_path=db_path,
        ),
    )


# ---------------------------------------------------------------------------
# Financial report: a gross-margin P&L on recorded costs
# ---------------------------------------------------------------------------
#
# Revenue comes from the invoices. The costs come from what the shop has
# recorded (shop/shop_costs.py): part lines' purchase costs, and each time
# entry's hours at the cost rate of the person who logged it. A cost that was
# not recorded is reported as not recorded, and a margin that needs it is not
# computed: nothing unrecorded is shown as zero. The API's RevenueRollup and
# DashboardSnapshot are not touched.

PNL_DIMENSIONS: tuple[str, ...] = ("mechanic", "bay", "customer", "shop")
PNL_PERIODS: tuple[str, ...] = ("month", "quarter", "year")

ATTRIBUTION_RULES: dict[str, str] = {
    "mechanic": (
        "A work order's revenue and all its costs count for its assigned "
        "mechanic; a work order with none counts as unassigned."
    ),
    "bay": (
        "A work order's revenue and costs are split across bays by the slot "
        "hours it spent in each (actual times when recorded, else scheduled); "
        "a work order with no slot counts as no bay."
    ),
    "customer": "Each invoice counts for the invoice's customer.",
    "shop": (
        "The whole shop. Expenses are subtracted here only; they are never "
        "split across mechanics, bays or customers."
    ),
}

COST_RULES: tuple[str, ...] = (
    "Revenue: invoices not cancelled, issued in the period, before tax.",
    "Parts cost: each billed part line's recorded purchase cost times its quantity.",
    "Labour cost: each logged time entry's hours at the cost rate, in force on "
    "the entry's date, of the person who logged it.",
)


class PnlGroup(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key: str
    work_orders: float
    revenue_cents: dict[str, int] = Field(default_factory=dict)
    revenue_total_cents: int
    parts_cost_cents: Optional[int]
    parts_cost_missing: int
    labour_cost_cents: Optional[int]
    labour_cost_missing: int
    labour_hours: float
    gross_margin_cents: Optional[int]


class PnlReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shop_id: int
    by: str
    period: str
    period_key: str
    start: str
    end: str
    attribution_rule: str
    cost_rules: list[str]
    groups: list[PnlGroup]
    expenses_cents: Optional[int] = None
    expense_months_missing: list[str] = Field(default_factory=list)
    net_cents: Optional[int] = None


def _period_bounds(period: str, key: str) -> tuple[str, str, list[str]]:
    """``(start, end_exclusive, months)`` for a month (YYYY-MM), a quarter
    (YYYY-Qn) or a year (YYYY)."""
    if period == "month":
        m = re.fullmatch(r"(\d{4})-(0[1-9]|1[0-2])", key)
        if not m:
            raise ValueError("a month is YYYY-MM")
        year, first, count = int(m.group(1)), int(m.group(2)), 1
    elif period == "quarter":
        m = re.fullmatch(r"(\d{4})-Q([1-4])", key, re.IGNORECASE)
        if not m:
            raise ValueError("a quarter is YYYY-Qn, n from 1 to 4")
        year, first, count = int(m.group(1)), 3 * int(m.group(2)) - 2, 3
    elif period == "year":
        if not re.fullmatch(r"\d{4}", key):
            raise ValueError("a year is YYYY")
        year, first, count = int(key), 1, 12
    else:
        raise ValueError(f"period must be one of {', '.join(PNL_PERIODS)}")
    months = [f"{year:04d}-{first + i:02d}" for i in range(count)]
    last = first + count
    end = f"{year + 1:04d}-01-01" if last > 12 else f"{year:04d}-{last:02d}-01"
    return f"{months[0]}-01", end, months


def _hours_between(start, end) -> float:
    try:
        a = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        b = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return 0.0
    if (a.tzinfo is None) != (b.tzinfo is None):
        a, b = a.replace(tzinfo=None), b.replace(tzinfo=None)
    return max(0.0, (b - a).total_seconds() / 3600.0)


def _bay_weights(conn, wo_id: int) -> dict[str, float]:
    """Each bay's share of a work order, by its slot hours there."""
    rows = conn.execute(
        "SELECT s.bay_id, b.name, s.scheduled_start, s.scheduled_end, "
        "s.actual_start, s.actual_end FROM bay_schedule_slots s "
        "JOIN shop_bays b ON b.id = s.bay_id "
        "WHERE s.work_order_id = ? AND s.status != 'cancelled'",
        (wo_id,),
    ).fetchall()
    hours: dict[str, float] = {}
    for r in rows:
        if r["actual_start"] and r["actual_end"]:
            h = _hours_between(r["actual_start"], r["actual_end"])
        else:
            h = _hours_between(r["scheduled_start"], r["scheduled_end"])
        label = f"{r['name']} (bay {r['bay_id']})"
        hours[label] = hours.get(label, 0.0) + h
    total = sum(hours.values())
    if total <= 0:
        return {"no bay": 1.0}
    return {k: v / total for k, v in hours.items()}


def _wo_costs(
    conn, wo_id: int, rates: list[dict],
) -> tuple[Optional[int], Optional[int], float]:
    """``(parts_cost, labour_cost, labour_hours)`` for one work order. A
    cost is None when any part of it was not recorded; a work order with no
    billed part lines has a parts cost of 0, and one with no logged time has
    no labour cost to show."""
    parts = conn.execute(
        "SELECT wop.quantity, c.purchase_cost_cents_each FROM work_order_parts wop "
        "LEFT JOIN work_order_part_costs c ON c.work_order_part_id = wop.id "
        "WHERE wop.work_order_id = ? AND wop.status IN ('received', 'installed')",
        (wo_id,),
    ).fetchall()
    parts_cost: Optional[int] = 0
    for p in parts:
        if p["purchase_cost_cents_each"] is None:
            parts_cost = None
            break
        parts_cost += int(p["quantity"]) * int(p["purchase_cost_cents_each"])

    entries = conn.execute(
        "SELECT user_id, started_at, duration_seconds FROM work_order_time_entries "
        "WHERE work_order_id = ? AND duration_seconds IS NOT NULL",
        (wo_id,),
    ).fetchall()
    hours = sum(int(e["duration_seconds"]) for e in entries) / 3600.0
    labour_cost: Optional[int] = None
    if entries:
        total: Optional[float] = 0.0
        for e in entries:
            rate = cost_rate_on(rates, int(e["user_id"]), str(e["started_at"])[:10])
            if rate is None:
                total = None
                break
            total += int(e["duration_seconds"]) / 3600.0 * rate
        labour_cost = None if total is None else int(round(total))
    return parts_cost, labour_cost, hours


def financial_report(
    shop_id: int, by: str = "shop", period: str = "month",
    period_key: Optional[str] = None, db_path: Optional[str] = None,
) -> PnlReport:
    """Gross margin per mechanic, bay or customer, or the shop's P&L, for
    one month, quarter or year. The report carries the attribution rule for
    ``by`` and the cost rules, so what it counted is stated with it."""
    if by not in PNL_DIMENSIONS:
        raise ValueError(f"by must be one of {', '.join(PNL_DIMENSIONS)}")
    if period_key is None:
        now = datetime.now(timezone.utc).astimezone()  # the shop's month (F192)
        period_key = {"month": now.strftime("%Y-%m"),
                      "quarter": f"{now.year}-Q{(now.month - 1) // 3 + 1}",
                      "year": str(now.year)}.get(period, "")
    start, end, months = _period_bounds(period, period_key)
    rates = list_mechanic_cost_rates(shop_id, db_path=db_path)

    acc: dict[str, dict] = {}
    with get_connection(db_path) as conn:
        invoices = conn.execute(
            "SELECT inv.id, inv.customer_id, inv.work_order_id, "
            "wo.assigned_mechanic_user_id AS mech, c.name AS customer_name "
            "FROM invoices inv JOIN work_orders wo ON wo.id = inv.work_order_id "
            "LEFT JOIN customers c ON c.id = inv.customer_id "
            "WHERE wo.shop_id = ? AND inv.status != 'cancelled' "
            "AND datetime(inv.issued_at) >= ? "
            "AND datetime(inv.issued_at) < ? ORDER BY inv.id",
            (shop_id, local_day_start(start), local_day_start(end)),
        ).fetchall()
        for inv in invoices:
            revenue: dict[str, int] = {}
            for ln in conn.execute(
                "SELECT item_type, line_total FROM invoice_line_items "
                "WHERE invoice_id = ?", (inv["id"],),
            ).fetchall():
                revenue[ln["item_type"]] = revenue.get(ln["item_type"], 0) + int(
                    round(float(ln["line_total"] or 0) * 100))
            parts_cost, labour_cost, hours = _wo_costs(conn, inv["work_order_id"], rates)
            if by == "mechanic":
                mech = inv["mech"]
                weights = {str(mech) if mech is not None else "unassigned": 1.0}
            elif by == "customer":
                name = inv["customer_name"] or "?"
                weights = {f"{name} (customer {inv['customer_id']})": 1.0}
            elif by == "bay":
                weights = _bay_weights(conn, inv["work_order_id"])
            else:
                weights = {"shop": 1.0}
            for key, w in weights.items():
                g = acc.setdefault(key, {"wos": 0.0, "revenue": {}, "parts": 0.0,
                                         "parts_missing": 0, "labour": 0.0,
                                         "labour_missing": 0, "hours": 0.0})
                g["wos"] += w
                for t, cents in revenue.items():
                    g["revenue"][t] = g["revenue"].get(t, 0.0) + cents * w
                if parts_cost is None:
                    g["parts_missing"] += 1
                else:
                    g["parts"] += parts_cost * w
                if labour_cost is None:
                    g["labour_missing"] += 1
                else:
                    g["labour"] += labour_cost * w
                g["hours"] += hours * w

    groups: list[PnlGroup] = []
    for key in sorted(acc, key=lambda k: (k in ("unassigned", "no bay"), k)):
        g = acc[key]
        revenue = {t: int(round(v)) for t, v in sorted(g["revenue"].items())}
        rev_total = sum(revenue.values())
        parts = None if g["parts_missing"] else int(round(g["parts"]))
        labour = None if g["labour_missing"] else int(round(g["labour"]))
        margin = None if parts is None or labour is None else rev_total - parts - labour
        groups.append(PnlGroup(
            key=key, work_orders=round(g["wos"], 2), revenue_cents=revenue,
            revenue_total_cents=rev_total,
            parts_cost_cents=parts, parts_cost_missing=g["parts_missing"],
            labour_cost_cents=labour, labour_cost_missing=g["labour_missing"],
            labour_hours=round(g["hours"], 2), gross_margin_cents=margin,
        ))

    report = PnlReport(
        shop_id=shop_id, by=by, period=period, period_key=period_key,
        start=start, end=end, attribution_rule=ATTRIBUTION_RULES[by],
        cost_rules=list(COST_RULES), groups=groups,
    )
    if by == "shop":
        expenses = list_expenses(shop_id, months=months, db_path=db_path)
        seen = {e["month"] for e in expenses}
        report.expenses_cents = sum(int(e["amount_cents"]) for e in expenses)
        report.expense_months_missing = [m for m in months if m not in seen]
        margin = groups[0].gross_margin_cents if groups else 0
        if margin is not None and not report.expense_months_missing:
            report.net_cents = margin - report.expenses_cents
    return report


# ---------------------------------------------------------------------------
# Estimate vs actual variance
# ---------------------------------------------------------------------------


class VarianceRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    work_order_id: int
    title: str
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    labour_note: Optional[str]
    labour_delta_pct: Optional[float]
    estimated_parts_cents: Optional[int]
    actual_parts_cents: int
    parts_note: Optional[str]
    parts_delta_pct: Optional[float]
    quote_total_cents: Optional[int]
    invoice_subtotal_cents: Optional[int]
    quote_note: Optional[str]
    quote_delta_pct: Optional[float]


class VarianceReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shop_id: int
    since: str
    rows: list[VarianceRow]
    labour_scored: int
    parts_scored: int
    quotes_scored: int
    labour_median_delta_pct: Optional[float]
    parts_median_delta_pct: Optional[float]
    quote_median_delta_pct: Optional[float]


def _delta_pct(estimate: float, actual: float) -> Optional[float]:
    if estimate <= 0:
        return None
    return round((actual - estimate) / estimate, 4)


def estimate_variance(
    shop_id: int, since: str = "30d", db_path: Optional[str] = None,
) -> VarianceReport:
    """Per completed work order: labour hours, parts cost and the quote
    against what happened.

    The quote is the latest one recorded when an estimate was queued to the
    customer, at or before the invoice's issue; with none, the row says "no
    quote recorded" and no figure is recomputed in its place.
    """
    cutoff = _parse_date_window(since)
    rows: list[VarianceRow] = []
    with get_connection(db_path) as conn:
        wos = conn.execute(
            "SELECT * FROM work_orders WHERE shop_id = ? AND status = 'completed' "
            "AND datetime(completed_at) >= ? ORDER BY datetime(completed_at), id",
            (shop_id, cutoff),
        ).fetchall()
        for wo in wos:
            est_h, act_h = wo["estimated_hours"], wo["actual_hours"]
            labour_note = labour_pct = None
            if est_h is None:
                labour_note = "no estimate"
            elif act_h is None:
                labour_note = "no actual hours"
            else:
                labour_pct = _delta_pct(float(est_h), float(act_h))
                if labour_pct is None:
                    labour_note = "estimate is zero"

            actual_parts = conn.execute(
                "SELECT COALESCE(SUM(wop.quantity * COALESCE("
                "wop.unit_cost_cents_override, p.typical_cost_cents, 0)), 0) "
                "FROM work_order_parts wop JOIN parts p ON p.id = wop.part_id "
                "WHERE wop.work_order_id = ? "
                "AND wop.status IN ('received', 'installed')",
                (wo["id"],),
            ).fetchone()[0]
            est_parts = wo["estimated_parts_cost_cents"]
            parts_note = parts_pct = None
            if est_parts is None:
                parts_note = "no estimate"
            else:
                parts_pct = _delta_pct(float(est_parts), float(actual_parts))
                if parts_pct is None:
                    parts_note = "estimate is zero"

            invoice = conn.execute(
                "SELECT subtotal, issued_at FROM invoices WHERE work_order_id = ? "
                "AND status != 'cancelled' ORDER BY id DESC LIMIT 1",
                (wo["id"],),
            ).fetchone()
            quote_total = subtotal = quote_pct = quote_note = None
            if invoice is None:
                quote_note = "not invoiced"
            else:
                subtotal = int(round(float(invoice["subtotal"] or 0) * 100))
                # the two stamps differ in their date-time separator
                quote = conn.execute(
                    "SELECT total_cents FROM work_order_quotes WHERE work_order_id = ? "
                    "AND replace(quoted_at, 'T', ' ') <= replace(?, 'T', ' ') "
                    "ORDER BY quoted_at DESC, id DESC LIMIT 1",
                    (wo["id"], str(invoice["issued_at"])),
                ).fetchone()
                if quote is None:
                    quote_note = "no quote recorded"
                else:
                    quote_total = int(quote["total_cents"])
                    quote_pct = _delta_pct(float(quote_total), float(subtotal))
                    if quote_pct is None:
                        quote_note = "quote is zero"
            rows.append(VarianceRow(
                work_order_id=wo["id"], title=wo["title"],
                estimated_hours=est_h, actual_hours=act_h,
                labour_note=labour_note, labour_delta_pct=labour_pct,
                estimated_parts_cents=est_parts,
                actual_parts_cents=int(actual_parts),
                parts_note=parts_note, parts_delta_pct=parts_pct,
                quote_total_cents=quote_total, invoice_subtotal_cents=subtotal,
                quote_note=quote_note, quote_delta_pct=quote_pct,
            ))

    def _med(values: list[Optional[float]]) -> Optional[float]:
        known = [v for v in values if v is not None]
        return round(median(known), 4) if known else None

    labour = [r.labour_delta_pct for r in rows]
    parts = [r.parts_delta_pct for r in rows]
    quotes = [r.quote_delta_pct for r in rows]
    return VarianceReport(
        shop_id=shop_id, since=since, rows=rows,
        labour_scored=sum(v is not None for v in labour),
        parts_scored=sum(v is not None for v in parts),
        quotes_scored=sum(v is not None for v in quotes),
        labour_median_delta_pct=_med(labour),
        parts_median_delta_pct=_med(parts),
        quote_median_delta_pct=_med(quotes),
    )
