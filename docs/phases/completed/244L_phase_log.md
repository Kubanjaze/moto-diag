# Phase 244L — Vision costs reach the ledger — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-10

---

## 2026-09-10 — Plan v1.0 written

Opened because the operator asked what a day of questions costs and there was no
way to tell them. The answer turned out to have three parts, and only one is a
missing feature.

**The guidance endpoint discards its own cost.** `answer_question_about_frames`
binds the usage from `ask_with_images` to `_usage` — the underscore is the
convention for *deliberately unused*. The sweep makes the same call and keeps it.
So Phase 244J shipped an endpoint that spends a vision call on every request and
records nothing, and nothing complained: no warning, no lint, no failing test.
That one is mine, and it is the second time in this session that wiring a path
without asking what it owes has cost something.

**The ledger structurally cannot hold a vision cost.** `cost_events.kind` carries
`CHECK (kind IN ('whisper', 'claude_extraction'))`, so the insert would be
rejected by the database even if a caller tried. That constraint was an accurate
description of the product at Phase 195B and stopped being true at Phase 191B
when vision arrived. **A CHECK constraint is a claim about what the system does**,
and this one quietly went stale.

**And `cost_events` has zero rows** — nothing has ever written to it, by any path.

**Step 0 made the phase much smaller than it first looked.** `shop/cost_repo.py`
already has `record_cost_event` / `aggregate_costs` / `shop_cost_this_month`, and
`cli/costs.py` already exposes `motodiag costs report`. `aggregate_costs` groups
by kind and model with no fixed list of kinds, so **the existing report renders
vision spend the moment rows exist** — there is no reporting work in this phase
at all. The `units_label`/`units_value` pair is already kind-polymorphic, so
vision needs permission to use the ledger rather than a shape of its own.

Worth recording that as its own lesson: the third time this session that reading
for what exists first would have saved building something. The theme tokens, the
`withTheme` helper, and now an entire cost-reporting surface.

**Two kinds, not one.** `vision_sweep` and `vision_guidance` are separated
because the operator's actual question is what the *questions* cost, and
averaging them into sweeps loses exactly that number. Splitting a kind
afterwards is impossible retroactively — rows already written would be
unattributable — so the choice has to be made now.

**Recording is subordinate to answering.** A failed ledger write must not cost a
technician their answer; the money is already spent by then either way.

## 2026-09-10 — Build complete

**Regression: 6341 passed, 0 failed, 24:29.**

The feature was the easy part, and Step 0 had already predicted that — the
reporting surface needed no change at all, so `motodiag costs report` rendered
`vision_guidance $0.98` for seven questions the moment rows existed. About 14¢
a question.

**The first regression came back with 18 failures and none of them were the
feature.** Ten were in `test_phase235b_regulation_provenance.py`, a file about
regulation provenance, which rolls back to schema 51 in its fixture and found
no `cost_events` table to read.

Migration 057's `rollback_sql` was **migration 043's, copied verbatim**. It
drops the table. That is right for 043, which created `cost_events`; it is
destructive for 057, which only widened a CHECK — rolling back to anything
below 57 deleted the whisper ledger 043 had built.

What makes this worth more than a line: the two blocks are byte-identical, so
**every text-based approach to it is ambiguous by construction.** My first
attempt to patch it asserted the anchor appeared once, found two, and stopped —
and had it not asserted, it would have rewritten *043's legitimate rollback*
instead. The question that resolves it is not "where is this text" but "which
migration does this block belong to", and only the second one has an answer.

Five rollback guards added. **One of them was vacuous on first write.**
`test_rolling_back_drops_the_column_it_added` read `PRAGMA table_info` and
asserted `"video_id" not in cols` — and for a *dropped* table that PRAGMA
returns an empty list, so the assertion passed against the exact defect it was
written to catch. It surfaced only because the mutation was actually run.
That is the fifth instance of this family in one session, and running the
mutation has caught every one of them; reasoning about the guard has caught
none.

Three smaller things, all found by other people's guards rather than mine:
`Decimal`/`ROUND_HALF_UP` replaced `round()` after the docstring claimed
half-up on money and Python's is banker's; Phase 191C's f9 lint caught a
hardcoded `claude-sonnet-4-6` in this phase's own test file; and six failures
across two files were fakes with fixed signatures meeting the new kwargs.

**Status:** ✅ Complete
