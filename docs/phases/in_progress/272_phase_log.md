# Phase 272 — Gate 15: Track N's five workflows walked end-to-end through the workflow door — phase log

**Status:** 🚧 In progress
**Branch:** `phase-272` (Opus session, main checkout)

---

### 2026-09-26 — Opened: Gate 15, test-only

The operator's prompt, 2026-09-26: start Phase 272, Gate 15, the Track N
integration test, and run it to its finish line. The last session's
state is `docs/handoffs/2026-09-26_262_closed.md`. Tests and documents
only: no production code, no migration, no change to the live database.

**The operator's decision, recorded verbatim:**

> option 1, test-only gate, with three conditions:
> 1. correct gate 15's roadmap row: it verifies the five workflows walk
>    through end-to-end via workflow list/show, per powertrain, with every
>    template link resolving — it does not claim they "run". the row
>    can't say something nothing does.
> 2. positive control on the walk: plant a broken template link and a
>    wrong-powertrain step (valve adjustment on an electric), show the
>    gate fails on each, then remove them.
> 3. "a workflow can't be run" is filed as a finding AND named as a
>    specific phase on the roadmap (the in-memory runner, option 2's
>    scope), not left as "future". saved runs (option 3) come after that,
>    as their own phase with the migration.

**The operator's stop condition:** "If Step 0 finds the walk cannot be
written without production code, or anything else that needs a
decision, stop and give me the options."

**Carried forward** (the operator's list): no test reads
`data/motodiag.db`; no literal pin of the schema head (F124); the
whole-tree gates before every commit, including the 244G scanner over
the new test file; the Edit tool for source edits; scratch files out of
`/tmp`; commit messages through a quoted heredoc. Regression by
`.claude/skills/closeout/regression.sh`.

Row 272 went 🚧 before Step 0, with its text corrected per condition 1.

### 2026-09-26 — Step 0

`272_step0.md`. The operator's five measured points all re-verify
(S0-1). The walk needs no production code (S0-2). The link census finds
22 slug references (16 distinct links, 22 resolving), 1 slug-with-item
reference and 12 same-template item references, and 0 references in any
other form (S0-3).

**One decision, taken here and not a stop** (S0-4, v1.0 D1): the
title-vocabulary rule for wrong-powertrain steps finds one live
violation, `generic_ppi_v1` item 3, a required "Engine compression test"
in a template that covers electric. Fixing it is a migration, which the
operator excluded. Recorded as the rule's exact, measured exception and
filed (F166), as Gates 13 and 14 did with every gap they measured. Why
this is not a stop under rule 1: no second plan ships different code;
the operator's rule, controls and conditions are unchanged; the
alternative (the migration) is outside the scope the operator set.
