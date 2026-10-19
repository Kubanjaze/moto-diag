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
