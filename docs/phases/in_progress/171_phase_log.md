# MotoDiag Phase 171 — Phase Log

**Status:** 🟡 In Progress | **Started:** 2026-04-22
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
