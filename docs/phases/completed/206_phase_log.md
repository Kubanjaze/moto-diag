# Phase 206 — Performance: fix what is actually wrong — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
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

---

### 2026-09-07 13:24 — Six defects fixed; no theatre

- **Measuring first is what saved the phase.** Baseline: 2-10ms across
  every endpoint against 6 work orders. Nothing was slow. A phase that
  "optimised" that would have reported large percentages on
  sub-millisecond queries and left every real defect in place.
- **fix #1 — pagination pushed into SQL.** The KB routes fetched every
  row and sliced in Python; asking for 50 known-issues materialised all
  6,600. Now 50. A shared WHERE helper feeds both the page and a
  `COUNT(*)` so `total` stays honest — naively adding LIMIT would have
  silently broken it.
- **fix #2 — the report builder's DTC N+1.** One query per fault code,
  and up to three because of the make → generic → any fallback.
  `get_dtcs()` resolves the set once and reproduces that precedence.
  **11 queries at 1 code and at 20.**
- **fix #3 — a per-part query that computed nothing.** Confirmed
  empirically against a seeded `parts_xref`: the loop passed an id where
  a part NUMBER goes, and read keys the function never returns, inside a
  bare `except`. Those cost fields have been `None` since Phase 153.
  Removed; F58 keeps the correctness half.
- **fix #4 — 14 `async def` handlers doing blocking sqlite.** Not
  slowness: each stalled the event loop for every OTHER in-flight
  request. One word per handler; offender count now 0, verified by
  walking the live route table.
- **fix #5 — the only large table had no usable index.**
  `known_issues` was the one table outside the migration system.
  `EXPLAIN` went from `SCAN + USE TEMP B-TREE FOR ORDER BY` to an index
  walk. Migration 049, additive.
- **fix #6 — conditional GET on the KB export.** 21,628 bytes becomes a
  bodyless 304. The subtlety the plan missed: mobile must NOT
  revalidate when its cache is wedged (stamp, zero rows), or a 304
  skips Phase 198's self-heal and makes the wedge permanent.
- **Two of my own errors, both caught by the system rather than by me:**
  a slice-edit deleted `list_symptoms_by_category` (collection error
  caught it; I then checked the other two repos), and migration 049
  originally indexed a `category` column that does not exist (the
  migration refused to apply).
- **Harness asserts SHAPE, never duration** — rows fetched, statements
  issued and whether they grow with N, the query plan, and async-without-
  await. True on any machine forever.
- **Suites:** backend **4814 passed, 0 failed**; mobile 84 / 1016.
