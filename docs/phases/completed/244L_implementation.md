# Phase 244L — The vision calls spend money and the ledger cannot hold it

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-10 (built 2026-09-10)

---

## Goal

A shop owner asked what a day of questions costs and there is no way to tell
them. Three separate reasons, and only the first is a missing feature:

1. **The guidance endpoint throws its cost away.** `answer_question_about_frames`
   calls `client.ask_with_images(...)` and binds the usage to `_usage` — the
   underscore says *deliberately unused*. The sweep, on the same call, keeps it.
   Phase 244J wired an endpoint that spends a vision call per request and
   records nothing. That one is mine.
2. **The ledger structurally cannot hold a vision cost.**
   `cost_events.kind` carries `CHECK (kind IN ('whisper', 'claude_extraction'))`,
   so the insert would be *rejected by the database* even if a caller tried. The
   ledger was built at Phase 195B for voice and never widened when vision landed.
3. **`cost_events` has zero rows.** Nothing has ever written to it by any path.

The sweep's cost does survive — as `cost_estimate_usd` inside the
`analysis_findings` JSON blob on the video row (`0.141099` on the most recent
run). Real, but per-video and buried, so "what did today cost" means parsing
JSON out of every video row, and guidance contributes nothing at all.

## Step 0 finding — most of this already exists

`shop/cost_repo.py` has `record_cost_event()`, `aggregate_costs()` and
`shop_cost_this_month()`. `cli/costs.py` exposes
`motodiag costs report --since / --this-month / --shop`. `aggregate_costs`
groups by `kind` and `model` and takes no fixed list of kinds, so **the existing
report renders vision spend the moment rows exist** — no reporting work at all.

The `units_label` / `units_value` pair is already kind-polymorphic —
`('duration_ms', N)` for Whisper, `('tokens', N)` for Claude — so vision needs no
schema shape of its own, only permission to use it.

This is a small phase attached to well-built infrastructure, not a new subsystem.

## Non-goals

- **No enforcement.** `cost_cap_monthly_usd_cents` stays unread. Deciding what
  happens to a shop mid-shift when it hits a ceiling is a product decision, and
  the operator asked for reporting.
- **Not backfilling history.** The sweep costs already sitting in
  `analysis_findings` blobs stay where they are. A migration inventing ledger
  rows with fabricated timestamps would put numbers in a financial report that
  never came from a recorded event.
- **Not changing what a call costs**, only recording it.

## Logic

**Migration 057** widens the `kind` CHECK to add `vision_sweep` and
`vision_guidance`, and adds a nullable `video_id` FK (`ON DELETE SET NULL`,
matching how `transcript_id` already behaves) so a row survives its video being
deleted. Two kinds rather than one because the operator's question — *what do the
questions cost* — cannot be answered if guidance is averaged into sweeps.

The rebuild must re-declare the three existing indexes, per the Phase 244D
lesson on this codebase's table rebuilds.

**One helper, both paths.** `media/vision_costs.py` gains
`record_vision_cost(usage, kind, *, video_id, shop_id, db_path)`, converting USD
to cents via the existing `cost_dollars_to_cents`. Both the sweep and the
guidance endpoint call it. A single choke point is the point: two call sites that
each remember to record are two chances to forget, which is exactly how the
guidance path shipped untracked.

**Recording must not break answering.** A ledger write that fails cannot cost a
technician their answer — the call has already been paid for either way. Failures
are caught and logged, and the guard asserts the answer still returns.

**Reporting needs no work**, per Step 0. `motodiag costs report --this-month`
will show `vision_sweep` and `vision_guidance` lines beside the existing ones.

## Key Concepts

- **An underscore-prefixed binding is a decision, and it was the wrong one.**
  `_usage` is how the cost got discarded silently — no warning, no lint, nothing.
- **A CHECK constraint is a contract about what the system does.** This one said
  the product only spends money on voice, which stopped being true at Phase 191B.
- **Separate the kinds or the answer is unavailable.** Averaging guidance into
  sweeps loses precisely the number that was asked for.
- **Recording is subordinate to answering.** The money is spent before the ledger
  is touched.

## Verification Checklist

- [x] A guidance call writes exactly one `vision_guidance` row
- [x] A sweep writes exactly one `vision_sweep` row
- [x] The recorded cents match the usage the API returned
- [x] `video_id` is set, and survives its video being deleted
- [x] A failing ledger write does not stop the answer being returned
- [x] `costs report` renders both new kinds without modification
- [x] Existing `whisper` / `claude_extraction` rows still validate
- [x] The migration re-declares all three existing indexes
- [x] Mutation: discard the usage again → a guard fails
- [x] Mutation: record both paths under one kind → a guard fails
- [x] Rounding is half-up, not Python's banker's rounding
- [x] A negative cost records zero, never a credit
- [x] A broken `video_id` link still records the charge, unlinked
- [x] **Rolling back 057 preserves the whisper ledger it did not create**
- [x] The rollback re-declares its indexes too, and narrows the CHECK back
- [x] Mutation: restore the destructive rollback → all 5 rollback guards fail
- [x] Full regression green

## Risks

- **A widened CHECK is a one-way door in SQLite** — narrowing it later means
  another table rebuild. Two kinds are added deliberately rather than a generic
  `vision`, because splitting a kind afterwards cannot be done retroactively:
  rows already written would be unattributable.
- **Cost estimates are estimates.** `_calculate_cost` uses a local price table
  that drifts from Anthropic's actual billing. The report says *estimated* and
  the ledger records the model, so a stale price table is diagnosable rather
  than invisible.
- **Recording inside the request adds a write to a slow path.** It is one INSERT
  against a request already tens of seconds long, and it happens after the answer
  is in hand.

---

## Deviations from v1.0

**1. The rollback was migration 043's, copied verbatim — and it destroyed the
ledger.** The plan said the rebuild "must re-declare the three existing
indexes", and it did. What it did not say is what the *rollback* must do. The
first draft dropped the table:

```sql
DROP TABLE IF EXISTS cost_events;
```

That is correct for migration 043, which **created** `cost_events`. It is
destructive for 057, which only widened a CHECK: rolling back to any version
below 57 deleted the entire whisper ledger 043 had created. It did not fail
review because the two blocks are byte-identical and a text search for the
statement returns two hits, only one of them a defect — an attempt to patch it
by text alone asserted `count == 1`, found 2, and would otherwise have edited
043's legitimate rollback instead.

It was caught by **Phase 235B's fixture**, which rolls back to version 51 and
then found no table to read — 10 failures in a file with nothing to do with
costs. The rollback now rebuilds the pre-057 table and re-inserts the rows it
can still hold. It necessarily discards `vision_sweep` / `vision_guidance` rows,
because the narrowed CHECK cannot hold them; that loss is now stated in the
migration's own description rather than left to be discovered.

**2. Five rollback guards added, which v1.0 did not plan.** Nothing in the
original checklist tested rollback at all. Under mutation — the destructive
rollback restored — all five fail; reverted, all pass.

**3. One of those five was vacuous on first write.**
`test_rolling_back_drops_the_column_it_added` read `PRAGMA table_info` and
asserted `"video_id" not in cols`. For a **dropped** table `PRAGMA table_info`
returns an empty list, so the assertion passed against the very defect it was
written to catch. Fixed by asserting the table exists first. This is the same
family the session has hit repeatedly, and the only reason it surfaced is that
the mutation was actually run rather than assumed.

**4. `Decimal`/`ROUND_HALF_UP` instead of `round()`.** The helper's docstring
said "rounded half-up"; Python's built-in `round()` is banker's rounding, so
the docstring described behaviour the code did not have. On money that is a
defect, not a nit.

**5. Two collateral test fixes, both the same shape.** `record_vision_cost`
added `video_id` / `shop_id` / `db_path` kwargs to `analyze_video_frames` and
`answer_question_about_frames`; two pre-existing fakes had fixed signatures and
raised `TypeError` — `test_phase244J_guidance_surface.py` (5 failures) and
`test_media_pipeline_wiring_guard.py` (1).

**6. A hardcoded model ID in this phase's own test, caught by Phase 191C's f9
lint.** `USAGE` was built with a literal `"claude-sonnet-4-6"`. Now sourced from
`MODEL_ALIASES`. The guard did exactly its job on the phase that wrote the
violation.

---

## Results

| Metric | Value |
|---|---|
| Full regression | **6341 passed, 0 failed** (`exit 0`), 24:29 |
| New guards | 35 in `tests/test_phase244L_vision_costs.py` |
| Schema | v56 → **v57** (migration 057) |
| New module | `media/vision_costs.py`, 110 LoC |
| Call sites | 2, both through the one helper |
| Regression failures introduced then fixed | 18 |
| Verified spend, 7 questions | `vision_guidance $0.98` |

**The operator's question is now answerable.** Against a seeded ledger,
`motodiag costs report --this-month` renders — with no change to the reporting
code, per Step 0:

```
Cost report — since 2026-09-01 00:00:00, all shops
  total: $1.43 across 9 call(s)
  by kind:
    vision_guidance      $0.98
    vision_sweep         $0.14
    whisper              $0.31
  by model:
    claude-sonnet-4-6    $1.12
    whisper-1            $0.31
```

Seven questions, $0.98 — **about 14¢ per question**, so a 50-question day runs
roughly $7. That is the number that could not be produced before this phase, and
it is separable from sweeps only because the two kinds were split at migration
time rather than after.

**The 18 failures broke down as three families, none of them the feature.**
Ten in `test_phase235b_regulation_provenance.py` — a file about regulation
provenance — because its fixture rolls back to version 51 and the destructive
rollback had deleted the table underneath it. Six across
`test_phase244J_guidance_surface.py` and `test_media_pipeline_wiring_guard.py`,
both the same shape: fakes with fixed signatures meeting the new
`video_id`/`shop_id`/`db_path` kwargs. One in `test_phase191c_f9_lint.py`, this
phase's own hardcoded model ID. One in `test_f52_f55_cleanup.py`, collateral of
the rollback.

### Key finding

**A rollback is a migration, and this one was another migration's.** Migration
057's rollback was 043's, copied verbatim — correct there, because 043 created
`cost_events`; destructive here, because 057 only widened a CHECK. What makes
it worth recording is that the two blocks are byte-identical, so every
text-based approach to finding or fixing it is ambiguous by construction: a
search returns two hits with one defect, and a patch keyed on the text would
have edited the *legitimate* copy. It was found by a test in an unrelated file,
and confirmed only by asking which migration each block belonged to.

The second-order finding is smaller and more familiar: **the guard written to
catch it was vacuous on first write.** `PRAGMA table_info` returns an empty
list for a table that does not exist, so `"video_id" not in cols` passed
happily against a rollback that had just destroyed the table. Running the
mutation is what surfaced it — asserting the guard was correct would not have.
That is now five occurrences of this family in one session, and the reliable
detector has been the same every time: reintroduce the defect and watch.

### Risks — resolution

- **The one-way CHECK door** — held. Two kinds were added, not a generic
  `vision`, so the operator's per-question figure is recoverable.
- **Estimates drift from billing** — unresolved by design. The ledger records
  the model per row, so a stale price table stays diagnosable.
- **A write on a slow path** — one INSERT, after the answer is in hand. A
  failed write returns `None`; the answer still returns, guarded.
- **New, unplanned:** the rollback discards vision rows on the way back to
  v51, because the narrowed CHECK cannot hold them. Unavoidable, and now stated
  in the migration's own description rather than discovered.
