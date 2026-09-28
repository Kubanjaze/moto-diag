# Phase 356 — In-memory workflow runner — phase log

**Status:** 🚧 In progress
**Branch:** `phase-356` (Opus session, main checkout, the only writer)

---

### 2026-09-27 — Opened

The prompt is `docs/prompts/356_workflow_runner.txt` (committed in
`12aeec9`, merged `a2eafef`). The operator's order, verbatim
(2026-09-27): "content phase (F159/F163/F166 templates + F158's 27 rows)
→ 356 → 357 → Track O." 359 closed the content phase.

- Row 356 🚧, and F172 and F173 filed with the finding skill, as the
  first commit: `e86be59`.
  - F172: `apply-live` does not compare its fresh dry run with the
    committed diff; a gap to close before 357's live apply.
  - F173: `test_cross_platform_brakes` failed once in parallel in 359's
    first `--full`.

### 2026-09-27 — Step 0, stopped for the operator's pick

`356_step0.md`, committed `7cab578`. Phase 82's engine stops at the first
fail (measured on `brake_service_v1` and `valve_adjustment_v1`), so one
engine change is needed, `stop_on_fail`. Refusals match `show`. Gate 15
is unaffected. The powertrain is a fork: A (ask or flag), B (a garage
bike), C (both). Recommended A.

### 2026-09-28 — The operator's pick, verbatim

> A. Also file a finding for garage add's --powertrain default of "ice"
> (cli/main.py): an electric bike added without the flag is stored as
> ice, and diagnose, the predictor and the safety scoping read that
> value; 357's bike link would inherit it. File it, don't fix it in 356.

- **F174 filed.** Before citing them, each reader was read: diagnose
  (`cli/diagnose.py:466`, `:542`, `:721`), the predictor
  (`advanced/predictor.py:243`) and the priority scorer
  (`shop/priority_scorer.py:321`). One finding changes the premise's
  shape for the safety scoping: `ice` hides no rule from an electric
  bike, because no rule is scoped to electric alone; the seven
  `("ice", "hybrid")` rules are shown to it in addition. The entry says
  so.
