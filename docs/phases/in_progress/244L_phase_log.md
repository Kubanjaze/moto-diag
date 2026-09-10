# Phase 244L — Vision costs reach the ledger — phase log

**Status:** Planned
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
