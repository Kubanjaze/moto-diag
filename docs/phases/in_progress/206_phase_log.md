# Phase 206 — Performance: fix what is actually wrong — Phase Log

**Status:** 📋 Planned
**Started:** 2026-09-07 | **Completed:** —
**Repos:** `Kubanjaze/moto-diag` (+ mobile `kbSync` for conditional
GET), branch `phase-206-performance`

---

### 2026-09-07 12:50 — Plan written (Step 0 audit + v1.0)

- **Measured before planning, which reframed the phase.** Baseline on
  the real API: healthz 2-3ms, sessions 7-9ms, work-orders 8-10ms,
  session report 8-10ms, kb/export 6-8ms at 21KB. **Nothing is slow.**
  The dev DB holds 6 work orders and 5 parts. Tuning those numbers would
  be measuring noise and reporting it as progress.
- **User instruction: "don't make it theatre, focus on what's actually
  wrong."** The phase is scoped to six defects, each wrong at any scale.
- **The audit corrected a premise of mine.** I assumed
  `/v1/kb/export` carried the 6,600-row `known_issues` table; it
  exports DTC codes only (`kb.py:83-85`), which is why it measures
  21KB. Recorded because an unchecked assumption nearly became the
  phase's headline.
- **The six defects:** `rows[:limit]` full materialisation
  (`kb.py:291,335,361`) · unbounded `/v1/kb/search` · two N+1 loops
  (`builders.py:273`, `parts_needs.py:578`) · ~26 `async def`
  handlers doing blocking sqlite and never awaiting · `known_issues`
  outside the migration system with an index its own query path cannot
  use · `/v1/kb/export` recomputing its version stamp per request with
  no conditional GET.
- **Deliberate non-finding, recorded so nobody re-audits it:** index
  coverage elsewhere is thorough (150 indexes, solid FK coverage). The
  problem is concentrated on the one table nobody migrated.
- **Method decision: count queries, not milliseconds.** An N+1 is proven
  by "N+1 queries for N rows" — true on any machine forever. A
  millisecond figure on a 16MB database is fiction with a decimal point.
  A seeded fixture is built for SHAPE assertions only.
- **Next milestone:** pagination into SQL → batch the two N+1s →
  de-async → migration 049 → conditional GET → the query-count harness.
