# Phase 206 — Performance: fix what is actually wrong

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-07

## Existing-code audit (Step 0 — run 2026-09-07, before this plan)

**The framing matters more than usual here.** The dev database holds 6
work orders, 5 parts, 6 customers and 4 sessions. Measured baseline
before planning: `/healthz` 2-3ms, `/v1/sessions` 7-9ms,
`/v1/shop/{id}/work-orders` 8-10ms, `/v1/reports/session/4` 8-10ms,
`/v1/kb/export` 6-8ms at 21KB. **Nothing is slow.** A phase that tunes
these numbers would be measuring noise and reporting it as progress.

So this phase targets DEFECTS, not tuning. Every item below is wrong
regardless of scale.

**1 — `rows[:limit]`: full materialisation to return a page.**
`api/routes/kb.py:291,335,361` fetch every row from the repo and slice
in Python. Asking for 50 known-issues materialises all **6,600**.
`knowledge/issues_repo.py:149` already accepts a `LIMIT`; the route
never passes it. This is the worst offender and it is real today,
against the one genuinely large table.

**2 — `/v1/kb/search` is unbounded.** `kb.py:394` takes no limit
parameter; `core/search.py:50` runs `search_known_issues` alongside four
other unbounded searches. One common word scans 6,600 rows and returns
every match.

**3 — two N+1 loops.** `reporting/builders.py:273` calls `get_dtc()`
once per fault code inside the report loop. `shop/parts_needs.py:578`
calls `get_xrefs()` once per part inside the aggregation loop. Both are
measurable by counting queries, which needs no big database.

**4 — ~26 `async def` handlers do blocking sqlite and never await.**
`photos.py:392,409,431,488,511`, `videos.py:317,339,360,378`,
`transcripts.py:447,468,492,559`, plus blocking `Path.exists()` at
`photos.py:526` and `videos.py:393`. FastAPI threadpools SYNC handlers;
an `async def` that blocks stalls the event loop for every concurrent
request. Only `billing.py:168` (raw webhook body) and `live.py`
(WebSocket) genuinely need async.

**5 — `known_issues` is outside the migration system.** It is defined in
`core/database.py:59-77` with one index, `idx_known_issues_make_model`,
which the primary query path cannot use: `issues_repo.py:64-87` filters
`make LIKE '%x%'` (leading wildcard, no B-tree can serve it) then sorts
`ORDER BY severity DESC, title` on unindexed columns. The only large
table in the product does a full scan plus a sort, always.

**6 — `/v1/kb/export` recomputes its own version stamp every request.**
`kb.py:260-266` runs `json.dumps` + `sha256` over the whole payload just
to derive `kb_version`, uncached. And mobile (`kbSync.ts:24-63`)
downloads the entire body BEFORE comparing the stamp, so the
"unchanged" cold-start path still pays full transfer. No `ETag` /
`If-None-Match` exists anywhere in the product.

**What is NOT wrong, recorded so nobody re-audits it:** index coverage
elsewhere is genuinely thorough — 150 indexes, solid FK coverage across
the shop and work-order tables. The AI cache (`engine/cache.py:44-59`)
keys on `sha256(kind + canonical_json(payload))` and persists; it caches
AI responses only, and there is no HTTP response caching in the product.

**User decisions (2026-09-07):** *"don't make it theatre, focus on
what's actually wrong."* Convert ALL blocking async handlers · build a
seeded dataset **only** to assert query COUNTS and `EXPLAIN` shapes,
explicitly NOT to publish latency numbers.

## Goal

Fix six real defects and leave behind a harness that catches their
return. Publish no latency figures — at 16MB they would describe a
database no shop will ever have.

Run: `pytest tests/test_phase206_performance.py`

Outputs:
- **Pagination pushed into SQL** — `kb.py` routes pass `limit`/`offset`
  to the repo instead of slicing; `/v1/kb/search` grows a bounded
  `limit` with a sane default and cap.
- **Both N+1 loops batched** — `get_dtc` and `get_xrefs` gain
  bulk-by-ids variants; the loops call them once.
- **~26 handlers de-asynced**, leaving `async` only where something is
  awaited.
- **Migration 049** — bring `known_issues` under migration control with
  indexes that its real query path can use, including one for the
  `ORDER BY severity, title` sort.
- **Conditional GET on `/v1/kb/export`** — cache the version stamp,
  honour `If-None-Match`, return 304. Mobile's `kbSync` sends the stamp
  it holds, so the unchanged path stops transferring the body.
- **`tests/test_phase206_performance.py`** — a seeded fixture plus
  query-count assertions: "listing 50 issues issues a bounded number of
  queries and does not materialise the table", "building a report with
  N fault codes does not issue N DTC queries", "every route handler that
  is `async` awaits something".

## Logic

Query counting is done by installing a `sqlite3` trace callback on the
connection for the duration of a call and counting statements. That
makes the assertions about SHAPE (how many queries, and does it grow
with N) rather than duration — the only honest thing to assert at this
data size.

The async audit is enforced by a test that walks the FastAPI route table,
inspects each endpoint with `inspect.iscoroutinefunction`, and asserts
the handler's source contains an `await`. That turns "handlers are sync
unless they await" from a convention into something checkable.

## Key Concepts

- **Defects, not tuning.** Every item is wrong at 6 rows and at 6
  million. Nothing here depends on a number that would change with
  scale.
- **Count queries, not milliseconds.** An N+1 is proven by "issues N+1
  queries for N rows", which is true on any machine, on any dataset,
  forever. A millisecond figure on a 16MB database is fiction with a
  decimal point.
- **A seeded fixture is for shape, not speed.** It exists so a query
  count can be asserted against more than one row, not so latency can
  be graphed.
- **`async` without `await` is a correctness bug.** It does not merely
  fail to help; it actively stalls every other in-flight request.

## Verification Checklist

- [ ] `/v1/kb/issues` and siblings pass LIMIT to SQL; no `rows[:limit]`
      remains in the routes
- [ ] `/v1/kb/search` is bounded, with a documented default and cap
- [ ] Report building issues a constant number of DTC queries
      regardless of fault-code count
- [ ] Parts aggregation issues a constant number of xref queries
- [ ] Every `async def` route handler awaits something; the rest are
      sync
- [ ] Migration 049 applies; `known_issues` is under migration control
      with indexes its real queries can use
- [ ] `/v1/kb/export` returns 304 for a matching `If-None-Match`
- [ ] Backend regression green
- [ ] **No latency numbers published anywhere in the phase docs**

## Risks

- **Theatre.** Named by the audit as the top risk and settled by the
  user's instruction. The guard is that every checklist item is a
  defect with a named file and line, and none is a percentage.
- **The de-async diff is broad.** ~26 handlers across four route
  modules. Mechanically identical each time, and covered by existing
  route tests, but a wide diff invites a careless mistake — hence the
  automated check rather than eyeballing.
- **Migration 049 moves a table into the migration system.** The rows
  already exist from `SCHEMA_SQL`; the migration must be additive
  (indexes only) and must not attempt to recreate the table.
- **ETag correctness.** A stale-but-matching stamp would serve 304 to a
  client that actually needs new data. The stamp must derive from the
  same content it always did, and the test must prove a content change
  produces a different stamp.
- **Bulk variants changing behaviour.** `get_dtc` batched by ids must
  return exactly what N single calls returned, including for missing
  codes. Pinned by test rather than assumed.
