# Phase 359 — Content clean-up: starter templates and build references — phase log

**Status:** 🚧 In progress
**Branch:** `phase-359` (Opus session, main checkout, the only writer)

---

### 2026-09-27 — Opened

The prompt is `docs/prompts/359_content_cleanup.txt` (committed in
`30ac15f`, merged `bb3ef02`).

**The operator's order and condition, verbatim (2026-09-27):**

> order after: content phase (F159/F163/F166 templates + F158's 27 rows) → 356 → 357 → Track O.
> content phase: decide "retire vs repair" for the two old starter templates at its step 0, with a count of every template and row that references them. not before.

**Row 359 🚧:** `dc69e50`. 359 is the next free number: the highest row
was 358, the mobile ROADMAP has no 359, and `ROADMAP_AUTHORITY.md` gives
205+ to this repo.

### 2026-09-27 — Bug fix #1: A5 judged the first regression line, not the last

- **Issue:** 358's close-out check A5 read a log's first regression line
  that parsed. When a regression is re-run, that is the superseded run.
  358 recorded two: 9636 at `8a205ee`, then 9639 at `d93d8de` after its
  bug fix #2. A log whose first line parsed and whose re-run line did not
  would have passed. Reported in 358's handoff
  (`docs/handoffs/2026-09-27_358_closed.md`, "What is open").
- **Root cause:** `regression_line` ran `_REGRESSION.search` over the
  whole log, which returns the first match.
- **Fix:** it takes the last line carrying "Regression of record:" and
  parses that one. This fixes 358's check; the rule (count + hash +
  command) is unchanged.
- **Files:** `.claude/skills/closeout/closeout_check.py`; fixtures
  `k6_k7/a5_bad_last_line_superseded.md` and `k6_k7/a5_good_last_line.md`;
  `tests/test_phase359_a5_last_line.py` (4 tests); the skill's
  `CHANGELOG.md`.
- **Verified:** with the old `regression_line` restored, 3 of the 4 new
  tests failed, including the `check()` wiring test; with the fix, 67
  passed across the new file, `test_phase358_closeout_k6_k7.py` and
  `test_phase255D_closeout_contract.py`. 358's exemption controls still
  recompute to 10 and 40. Fast whole-tree: 1472 passed.

**Commit.** `5bc40c8`.
