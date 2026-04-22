# MotoDiag Phase 171 — Shop Analytics Dashboard

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Deterministic, read-only shop analytics that roll up Phase 161 work
orders, Phase 162 issues, Phase 165 parts, Phase 167 labor
reconciliation, Phase 168 bay utilization/overruns, and Phase 169
invoices into one dashboard snapshot. **No new state, no migrations, no
AI.** Mechanics get a single command (`shop analytics snapshot`) for
the end-of-week view; Phase 173 automation rules + Phase 171 per-
mechanic drill-downs consume the same composable rollup functions.

CLI — `motodiag shop analytics {snapshot, throughput, turnaround,
utilization, overruns, labor-accuracy, top-issues, top-parts, mechanic,
customer-repeat}` — **10 subcommands**.

**Design rule:** zero migrations, zero AI, zero tokens. Pure SQL
aggregations over existing Track G + accounting tables. Each rollup is
a stateless pure function taking `shop_id`, a `since` window, and
returning a Pydantic model. `DashboardSnapshot` composes all of them
for the all-in-one view.

Outputs:
- `src/motodiag/shop/analytics.py` (~520 LoC) — 10 rollup functions +
  10 Pydantic models + `DashboardSnapshot` composer + 2 date helpers.
- `src/motodiag/shop/__init__.py` +20 LoC re-exports.
- `src/motodiag/cli/shop.py` +320 LoC — `analytics` subgroup with 10
  subcommands + `_render_dashboard_panel` helper.
- No migration, no SCHEMA_VERSION bump (remains 34).
- `tests/test_phase171_analytics.py` (~30 tests across 5 classes).

## Logic

### Rollup functions

```python
def throughput(shop_id: int, since: str, db_path=None) -> ThroughputRollup:
    """Work-orders-by-status counts + completions-by-day timeseries."""

def turnaround(shop_id: int, since: str, db_path=None) -> TurnaroundRollup:
    """Mean / median / p90 hours from WO opened_at → completed_at."""

def utilization_rollup(
    shop_id: int, since_date: str, until_date: str,
    db_path=None,
) -> UtilizationRollup:
    """Per-day utilization % across window. Deltas from 90% threshold."""

def overrun_rate(
    shop_id: int, since: str, db_path=None,
) -> OverrunRateRollup:
    """Overrun-slot count / total-completed-slot count; per-mechanic."""

def labor_accuracy(
    shop_id: int, since: str, db_path=None,
) -> LaborAccuracyRollup:
    """Phase 167 reconcile buckets (within/under/over ±20%) aggregated
    across the window."""

def top_issues(
    shop_id: int, since: str, limit: int = 10, db_path=None,
) -> list[TopIssueRow]:
    """Count issues by category × severity; return top N."""

def top_parts(
    shop_id: int, since: str, limit: int = 10, db_path=None,
) -> list[TopPartRow]:
    """Aggregate work_order_parts quantity + cost by part; top N by
    cost across the window."""

def mechanic_performance(
    shop_id: int, since: str, db_path=None,
) -> list[MechanicPerformanceRow]:
    """Per-mechanic: WOs completed, avg turnaround, overrun rate,
    labor-estimate accuracy. Null-mechanic-id = unassigned bucket."""

def customer_repeat_rate(
    shop_id: int, since: str, db_path=None,
) -> CustomerRepeatRollup:
    """% of WOs this window whose customer had ≥1 prior WO."""

def dashboard_snapshot(
    shop_id: int, since: str = "30d",
    utilization_window_days: int = 7,
    db_path=None,
) -> DashboardSnapshot:
    """Compose all of the above. Uses Phase 169 revenue_rollup for the
    revenue section — no duplication."""
```

### Pydantic models (all `extra="ignore"`)

- `ThroughputRollup`: `by_status: dict[str, int]`, `completed_total: int`, `completions_by_day: list[DayBucket]`
- `TurnaroundRollup`: `sample_size: int`, `mean_hours: float | None`, `median_hours: float | None`, `p90_hours: float | None`
- `UtilizationRollup`: `days: list[DayUtilization]`, `mean_pct: float`, `over_threshold_days: int`
- `OverrunRateRollup`: `total_slots: int`, `overrun_slots: int`, `rate: float`, `by_mechanic: dict[str, float]`
- `LaborAccuracyRollup`: `sample_size: int`, `within_count: int`, `under_count: int`, `over_count: int`, `within_pct: float`, `median_delta_pct: float | None`
- `TopIssueRow`: `category: str`, `severity: str`, `count: int`
- `TopPartRow`: `part_id: int`, `slug: str`, `description: str`, `total_qty: int`, `total_cost_cents: int`
- `MechanicPerformanceRow`: `mechanic_id: int | None`, `wos_completed: int`, `avg_turnaround_hours: float | None`, `overrun_rate: float | None`, `labor_within_pct: float | None`
- `CustomerRepeatRollup`: `total_wos: int`, `repeat_wos: int`, `repeat_rate: float`
- `DashboardSnapshot`: composes above + Phase 169 `RevenueRollup`; has
  `shop_id`, `since`, `generated_at`.

### Date window parsing

Reuse the same pattern as Phase 164's `_since_cutoff`: accept
`30d`/`7d`/`24h`/`48h`/ISO timestamp. Add `_parse_date_window(since)`
helper returning an ISO timestamp string that SQL can compare directly
against TEXT timestamp columns.

### CLI subgroup

```
analytics snapshot [--shop X] [--since 30d] [--utilization-days 7] [--json]
analytics throughput [--shop X] [--since 30d] [--json]
analytics turnaround [--shop X] [--since 30d] [--json]
analytics utilization [--shop X] [--from DATE] [--to DATE] [--json]
analytics overruns [--shop X] [--since 30d] [--json]
analytics labor-accuracy [--shop X] [--since 30d] [--json]
analytics top-issues [--shop X] [--since 30d] [--limit 10] [--json]
analytics top-parts [--shop X] [--since 30d] [--limit 10] [--json]
analytics mechanic [--shop X] [--since 30d] [--json]
analytics customer-repeat [--shop X] [--since 30d] [--json]
```

## Key Concepts

- **Pure read, pure SQL.** No new tables, no new state, no writes.
  Phase 171 is a read-only analytics layer over existing Track G
  state. Idempotent, cache-friendly.
- **Composable rollups.** Each function stands alone; `dashboard_snapshot`
  composes them. Phase 173 automation rules can call individual rollups
  as rule conditions ("IF weekly_revenue < $X THEN notify owner").
- **Deterministic ordering.** All list results sort by stable keys
  (date ASC, cost DESC, then id ASC) so two calls with the same args
  produce identical output. Tests assert this.
- **NULL-safe aggregates.** Windows with zero qualifying rows return
  `sample_size=0` and `None` for means/medians rather than raising —
  dashboards should render gracefully on fresh shops.
- **Mechanic id NULL handling.** Phase 161 WOs can have
  `assigned_mechanic_user_id=NULL`; mechanic performance treats NULL
  as the "unassigned" bucket with `mechanic_id=None` in the response.
- **Reuses Phase 169 `revenue_rollup`** via composition — no duplication
  of the revenue math. Phase 168 utilization math stays in
  `bay_scheduler`; Phase 167 reconcile stays in `labor_estimator`; Phase
  162 `issue_stats` is called directly. Phase 171 only owns the
  cross-phase aggregations (turnaround, overrun rate, mechanic perf,
  top-parts, customer-repeat).

## Verification Checklist

- [ ] All 10 rollup functions return the stated Pydantic types.
- [ ] Each rollup handles the zero-data case (sample_size=0, None
      means, empty lists).
- [ ] `throughput` buckets by status + day; respects `since` cutoff.
- [ ] `turnaround` computes mean/median/p90 correctly against a
      known fixture; skips non-completed WOs.
- [ ] `utilization_rollup` aggregates per-day from Phase 168
      `utilization_for_day` across the range.
- [ ] `overrun_rate` counts status='overrun' slots; per-mechanic map.
- [ ] `labor_accuracy` reads `labor_estimates` + `work_orders.actual_hours`
      joined.
- [ ] `top_issues` counts by (category, severity) with ties broken by
      category ASC.
- [ ] `top_parts` sums `work_order_parts.quantity * effective_cost`,
      respects Phase 165 `unit_cost_cents_override` priority.
- [ ] `mechanic_performance` rolls up per-mechanic; NULL bucket shows
      as `mechanic_id=None`.
- [ ] `customer_repeat_rate` flags customers with ≥1 WO pre-window.
- [ ] `dashboard_snapshot` composes all + includes Phase 169 revenue
      rollup.
- [ ] `_parse_date_window` handles `Nd`, `Nh`, ISO, bad-input raise.
- [ ] CLI `analytics {snapshot, throughput, turnaround, utilization,
      overruns, labor-accuracy, top-issues, top-parts, mechanic,
      customer-repeat}` round-trip.
- [ ] Phase 113/118/131/153/160-170 tests still GREEN.
- [ ] Zero AI calls.

## Risks

- **Timestamp comparison semantics.** SQLite TEXT timestamps compare
  lexicographically; `ISO 8601` format with leading zeros on month/day
  makes this correct. All Phase 160+ `created_at`/`completed_at`
  columns use `CURRENT_TIMESTAMP` (ISO-ish `YYYY-MM-DD HH:MM:SS`) so
  lex comparison works. Mitigation: `_parse_date_window` normalizes
  inputs to the same format before SQL binding; tests cover boundary
  cases (exact-match, off-by-second).
- **Turnaround p90 with small samples.** A shop with 2-3 completed
  WOs in the window doesn't have a meaningful p90. Mitigation: p90
  returns `None` when `sample_size < 5`; CLI renders as "n/a".
- **Mechanic-id → name resolution.** `work_orders.assigned_mechanic_user_id`
  FKs to `users`, but some tests seed WOs without a `users` row.
  `mechanic_performance` returns mechanic id not name — CLI layer
  resolves the name via a LEFT JOIN that tolerates missing user rows
  (renders "(user #N)" fallback).
- **`top_parts` cost aggregation accuracy.** Phase 165 stores
  `unit_cost_cents_override` (optional) + `parts.typical_cost_cents`
  (catalog default). Aggregation uses `COALESCE(override, typical)`
  per the Phase 165 effective-cost rule. Tests cover both paths.
- **Date-window rounding.** "30d" means rolling-30-days not calendar
  month. Users expecting calendar boundaries will get ±3 days of noise.
  Mitigation: CLI `--since` help text says "rolling window (e.g., 30d,
  7d, 24h)"; Phase 173 automation rules can pass explicit ISO cutoffs.
