# Phase 244L — The vision calls spend money and the ledger cannot hold it

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-10

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

- [ ] A guidance call writes exactly one `vision_guidance` row
- [ ] A sweep writes exactly one `vision_sweep` row
- [ ] The recorded cents match the usage the API returned
- [ ] `video_id` is set, and survives its video being deleted
- [ ] A failing ledger write does not stop the answer being returned
- [ ] `costs report` renders both new kinds without modification
- [ ] Existing `whisper` / `claude_extraction` rows still validate
- [ ] The migration re-declares all three existing indexes
- [ ] Mutation: discard the usage again → a guard fails
- [ ] Mutation: record both paths under one kind → a guard fails
- [ ] Full regression green

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
