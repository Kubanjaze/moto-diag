"""Shop analytics dashboard (Phase 171).

Read-only deterministic rollups over existing Track G state. Zero new
tables, zero migrations, zero AI. Each rollup is a stateless pure
function returning a Pydantic summary; :func:`dashboard_snapshot`
composes them + the Phase 169 revenue rollup into one view.

Timestamp comparisons are lexicographic against SQLite TEXT columns —
safe because Phase 160+ columns use ISO-ish format
(``YYYY-MM-DD HH:MM:SS``). :func:`_parse_date_window` normalizes
``Nd``/``Nh``/ISO inputs to the same format at the binding boundary.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from statistics import mean, median
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from motodiag.core.database import get_connection
from motodiag.shop.bay_scheduler import utilization_for_day
from motodiag.shop.invoicing import RevenueRollup, revenue_rollup


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
    """Convert ``Nd``/``Nh``/``Nm``/ISO to an ISO cutoff timestamp string.

    Returned format: ``YYYY-MM-DD HH:MM:SS`` (space separator) which
    matches SQLite ``CURRENT_TIMESTAMP`` and lex-compares correctly.
    """
    if since is None:
        raise ValueError("since cannot be None")
    since = str(since).strip()
    if not since:
        raise ValueError("since cannot be empty")
    m = WINDOW_PATTERN.match(since)
    if m is not None:
        n = int(m.group(1))
        unit = m.group(2).lower()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if unit == "d":
            cutoff = now - timedelta(days=n)
        elif unit == "h":
            cutoff = now - timedelta(hours=n)
        elif unit == "m":
            cutoff = now - timedelta(minutes=n)
        else:
            raise ValueError(f"unsupported unit {unit!r}")
        return cutoff.strftime("%Y-%m-%d %H:%M:%S")
    # Try parse as ISO
    try:
        parsed = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(
            f"since must be Nd/Nh/Nm or ISO timestamp, got {since!r}"
        ) from e
    # Strip tz for comparison against naive SQLite strings
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


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
               WHERE shop_id = ? AND created_at >= ?
               GROUP BY status ORDER BY status""",
            (shop_id, cutoff),
        ).fetchall()
        comp_rows = conn.execute(
            """SELECT DATE(completed_at) AS d, COUNT(*) AS n
               FROM work_orders
               WHERE shop_id = ? AND completed_at IS NOT NULL
                 AND completed_at >= ?
               GROUP BY DATE(completed_at)
               ORDER BY d ASC""",
            (shop_id, cutoff),
        ).fetchall()
    by_status = {r["status"]: int(r["n"]) for r in by_status_rows}
    completions_by_day = [
        DayBucket(date=r["d"], count=int(r["n"])) for r in comp_rows
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
            """SELECT opened_at, completed_at FROM work_orders
               WHERE shop_id = ?
                 AND status = 'completed'
                 AND opened_at IS NOT NULL
                 AND completed_at IS NOT NULL
                 AND completed_at >= ?""",
            (shop_id, cutoff),
        ).fetchall()
    hours: list[float] = []
    for r in rows:
        try:
            o = datetime.fromisoformat(str(r["opened_at"]))
            c = datetime.fromisoformat(str(r["completed_at"]))
        except (ValueError, TypeError):
            continue
        delta = c - o
        if delta.total_seconds() < 0:
            continue
        hours.append(delta.total_seconds() / 3600.0)
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
                 AND COALESCE(s.actual_end, s.scheduled_end) >= ?""",
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
                 AND wo.completed_at >= ?
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
               WHERE wo.shop_id = ? AND i.created_at >= ?
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
               WHERE wo.shop_id = ? AND wo.created_at >= ?
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
            """SELECT assigned_mechanic_user_id AS mech,
                      opened_at, completed_at
               FROM work_orders
               WHERE shop_id = ?
                 AND status = 'completed'
                 AND completed_at >= ?""",
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
                 AND COALESCE(s.actual_end, s.scheduled_end) >= ?""",
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
                 AND wo.completed_at >= ?
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
        try:
            o = datetime.fromisoformat(str(r["opened_at"]))
            c = datetime.fromisoformat(str(r["completed_at"]))
            delta = (c - o).total_seconds() / 3600.0
            if delta >= 0:
                bucket["hours"].append(delta)
        except (ValueError, TypeError):
            pass
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
               WHERE shop_id = ? AND created_at >= ?""",
            (shop_id, cutoff),
        ).fetchone()
        repeat_row = conn.execute(
            """SELECT COUNT(*) AS n FROM work_orders wo
               WHERE wo.shop_id = ? AND wo.created_at >= ?
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
    since_cutoff = _parse_date_window(since)
    now = datetime.now(timezone.utc)
    end_date = now.strftime("%Y-%m-%d")
    start_date = (
        now - timedelta(days=int(utilization_window_days) - 1)
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
            shop_id=shop_id, since=since_cutoff, db_path=db_path,
        ),
    )
