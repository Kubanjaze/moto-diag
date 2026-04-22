# MotoDiag Phase 171 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-22 | **Completed:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written

Plan v1.0 authored in-session. Scope: deterministic read-only analytics
rollups over existing Track G state — throughput / turnaround /
utilization / overrun rate / labor accuracy / top issues / top parts /
mechanic performance / customer repeat + single composed
`DashboardSnapshot`. **No migration, no AI, no tokens.**

Key design decisions:
- Each rollup is a stateless pure function returning a Pydantic model.
  Phase 173 automation rules can call any individual rollup as a rule
  condition.
- `DashboardSnapshot` composes all rollups + delegates the revenue
  section to Phase 169 `revenue_rollup` (no duplicated revenue math).
- `_parse_date_window(since)` inherits Phase 164's pattern (`Nd`/`Nh`/
  ISO). Timestamps compared lexicographically against SQLite TEXT
  columns — safe because all Phase 160+ columns use ISO format.
- p90 returns None when sample_size < 5 (not enough data to be
  meaningful).
- NULL mechanic_id surfaces as the "unassigned" bucket in
  `mechanic_performance`.
- Deterministic ordering on every list output so two calls with same
  args produce identical results.

10 rollups × 10 Pydantic models = the backbone of Phase 171. CLI adds
10 subcommands to `motodiag shop analytics` — each subcommand is a thin
Click wrapper around one rollup.

### 2026-04-22 — Build complete

Files shipped:

1. **`shop/analytics.py`** (~524 LoC): 10 public rollup functions
   (`throughput`, `turnaround`, `utilization_rollup`, `overrun_rate`,
   `labor_accuracy`, `top_issues`, `top_parts`, `mechanic_performance`,
   `customer_repeat_rate`, `dashboard_snapshot`), 10 Pydantic summaries,
   2 date helpers (`_parse_date_window`, `_daterange`). All stateless,
   deterministic ordering on list outputs.

2. **`shop/__init__.py`** +22 re-exports.

3. **`cli/shop.py`** +212 LoC — `analytics` subgroup with **10
   subcommands** + `_simple_rollup_cmd` factory (a local helper that
   generates 6 of the 10 subcommands from a shared shape to avoid
   boilerplate) + explicit commands for `snapshot`/`utilization`/
   `top-issues`/`top-parts` which have distinct option shapes.

4. **`tests/test_phase171_analytics.py`** (31 tests across 5 classes):
   - `TestDateWindow` (5): Nd/Nh/ISO parsing, bad input raises, range.
   - `TestRollups` (12): each rollup + empty-case + override-priority
     + null-mechanic bucket + repeat rate.
   - `TestDashboardSnapshot` (3): compose, empty shop, determinism.
   - `TestAnalyticsCLI` (8): each subcommand round-trip.
   - `TestAntiRegression` (3): no migration bumped; re-exports present.

**Bug fixes during build:**
- **Bug fix #1: `bay_schedule_slots` has no `shop_id`**. First draft of
  `overrun_rate` and `mechanic_performance` queried `s.shop_id =`
  directly — but slots FK to `shop_bays` which FKs to `shops`. Fixed
  both queries to JOIN through `shop_bays b ON b.id = s.bay_id` and
  filter on `b.shop_id`. Files: `shop/analytics.py:285,380`. Verified:
  affected tests passed on rerun.
- **Bug fix #2: Customer-repeat ordering**. `CURRENT_TIMESTAMP`
  resolution is 1 second; two WOs created in the same second have
  identical `created_at`, so `prior.created_at < wo.created_at` returned
  zero repeats. Switched to `prior.id < wo.id` (monotonic by insert
  order). Files: `shop/analytics.py:490`. Verified: test_customer_
  repeat_rate passed on rerun.

Single-pass-after-fix: 31 GREEN in 18.32s.

**Targeted regression: 574 GREEN in 357.21s (5m 57s)** covering Phase
113 + 118 + 131 + 153 + Track G 160-171 + 162.5. Zero regressions.

Build deviations vs plan:
- Two schema corrections (JOIN through shop_bays; id-ordering for
  repeat rate) — both documented above as dated bug fixes.
- `_parse_date_window` added `Nm` minute unit (plan had Nd/Nh/ISO
  only) — adds ~5 LoC; useful for Phase 173 rule windows.
- 31 tests vs ~30 planned (+1 day-range helper test).

### 2026-04-22 — Documentation finalization

`implementation.md` promoted to v1.1. Verification Checklist all `[x]`.
Deviations section lists both build-phase bug fixes + `Nm` addition.
Results table populated.

Project-level updates:
- `implementation.md` Database Tables: no change (no migration)
- `implementation.md` Phase History: append Phase 171 row
- `implementation.md` Shop CLI Commands: 96 → 106 subcommands; added
  `motodiag shop analytics` row (14th subgroup)
- `phase_log.md` project-level: Phase 171 closure entry
- `docs/ROADMAP.md`: Phase 171 row → ✅
- Project version 0.10.2 → **0.10.3** (Track G analytics layer landed)

**Key finding:** Phase 171 validates the "compose existing rollups,
don't duplicate" pattern. By delegating revenue to Phase 169's
`revenue_rollup`, per-day utilization to Phase 168's `utilization_for_
day`, and computing only cross-phase aggregations this phase owns
(turnaround, overrun rate, mechanic perf, top parts/issues, customer
repeat), the analytics layer stayed at ~520 LoC without duplicating
any prior logic. Phase 173 automation rules get a clean API surface:
each rollup is a pure function that can serve as a rule-condition
evaluator, with `trigger_notification()` (Phase 170) as the action
side. No new plumbing needed.
