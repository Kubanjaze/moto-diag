# Phase 292 — Gate 16: one job walked from booking to the accounting export — phase log

**Status:** 🚧 In progress
**Branch:** `phase-292` (Opus session, main checkout)

---

### 2026-10-06 — Opened: Gate 16, test-only

The operator's prompt is `docs/prompts/292_gate16.txt` (committed
`9016d54`). The last session's state is
`docs/handoffs/2026-10-06_273_closed.md`. Tests and documents only, the
shape of Gate 15: no production code, no migration, no change to the live
database, no Stripe key. Row 292 went 🚧 before Step 0.

### 2026-10-06 — Step 0

`292_step0.md`. Every measured fact in the prompt re-verifies (S0-1). The
payment-command count is 3 files by the operator's vocabulary and 5 when
`mark-paid` is counted; no file runs booking, payment and export.

A dry walk of one job on a scratch database (S0-3) ran every step
through the real commands. It found two wrong assumptions in the walk
itself before the gate was written: customer id 1 is the "Unassigned"
placeholder, and `factory` is not a coverage type.

**Three hand-offs that do not exist or do not hold** (S0-4): H1, the Xero
export spreads the invoice's tax over untaxed labour; H2, a warranty
claim and the invoice do not know about each other; H3, check-in opens a
work order with no intake, and none can be attached afterwards. Closing
any of them takes production code, so per the prompt this was a fork,
and the session stopped and asked.

**The operator's choices, verbatim (2026-10-06):**

> H1: "Fix in 292 (Recommended)"
> H2: "Finding + row (Recommended)"
> H3: "Finding + row (Recommended)"

So rows 373 (warranty work on the invoice) and 374 (check-in with an
intake) were added, both 🔲, and then F188 and F189 were filed with the
finding skill, so the rows were in place before the findings cited
them. `roadmap_check.py` and `finding_check.py` exit 0. H1 is bug fix #1
of this phase.

**Decisions taken here, not stops** (S0-5): D1, the mechanic is user 1,
the seeded system user, because no command creates a user and nothing is
seeded; D2, the clock; D3, two card walks with a cash job in each.

**The live database was not read.** A read-only query of
`data/motodiag.db` to count Xero exports already written (H1's live
exposure) was refused by the session's permission classifier as a
production read. It was not retried by any other route. The question is
left to the operator; the query is in the handoff.

**The edit guard** blocked `sed -i` on a scratch script in the session
scratchpad: "`sed -i` edits a file in place, and is blocked wherever it
points". That is its documented scope (CHANGELOG, Phase 360), not a
misfire. The script was edited with the Edit tool. The guard was not
changed.
