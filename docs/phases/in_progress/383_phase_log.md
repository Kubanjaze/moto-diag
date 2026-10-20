# Phase 383 — 382's follow-ups: the live gates, then media paths — phase log

**Status:** 🚧 In progress
**Branch:** `phase-383` (Opus session on the Mac, the only writer; the deploy
runs on the desktop, from commands given here)

---

### 2026-10-19 — Opened, Step 0, and the stop

The prompt is `docs/prompts/383_follow_ups_from_382.txt` (merged
`e4a691f`). Row 383 went 🚧 before Step 0. Read first: F205, F206, F208 in
`docs/FOLLOWUPS.md`; 382's handoff and `382_*` in `completed/`; the deploy
skill, "Where live is (Phase 382)" first.

`383_step0.md` re-verifies every measured fact in the prompt (S0-1): all
hold. The prompt's figures were taken at `05f9e5c`; this branch starts at
`e4a691f`, which adds only the prompt.

Decided at Step 0, without a stop (reasons in `383_step0.md` S0-5): 087
rewrites by the routes' layout, not by a data folder; readers outside the
routes resolve with `get_settings().data_dir`; the route docstrings that
feed the OpenAPI descriptions are not edited, so the mobile snapshot stays
equal.

**A guard blocked a command:** a `sed -i` on `383_step0.md` (fixing the
prompt's file name) was refused by the edit guard. Made with the Edit tool
instead; the guard is unchanged.

The prompt asks for a stop at Step 0 with three questions: F206's rule,
F208's rule, F205's window. They are in `383_step0.md` S0-2 to S0-4, with
the options, what each ships, and the recommendation (1C, 2A with
apply-live following it and check 8 unchanged, 3A). Waiting for the
operator's picks.

### 2026-10-19 — The operator's picks, F210, v1.0

The operator, verbatim:

> 1C, 2A with apply-live following it, check 8 unchanged, 3A.
> - 1C: pin each expected skip by its test file and its reason, not the reason alone. EXPECTED_SKIPS is held by an equality test as A5_COMMAND_EXEMPT is, and adding to it is my call.
> - 2A: file a finding now that the column list cannot hold once a shop's traffic reaches live (a new work order between the dry run and the apply refuses the apply; any use after it fails check 8), to be settled before onboarding (330).

**F210 filed** (`docs/FOLLOWUPS.md`, through the finding skill:
`next_f_number.sh` gave F210; `finding_check.py` exit 0).

v1.0 written. Decided without a stop:
- The strict shape parses all 28 post-K6 closed logs (scratchpad
  `f206_strict.py`); it is the new `_REGRESSION`.
- pytest's `-rA` groups identical skips as `SKIPPED [N] file:line: reason`
  (measured on 244H's file under `-n 2`), so a skip line carries its count
  and A5 sums them.
- The line's writer moves into `closeout_check.py` beside its reader, so a
  test can feed one to the other; `regression.sh` calls it.
