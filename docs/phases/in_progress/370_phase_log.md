# Phase 370 — F10: session times stored in UTC — phase log

**Status:** 🚧 In progress
**Branch:** `phase-370` (Opus session, main checkout, the only writer)

---

### 2026-10-06 — Opened: F10

The prompt is `docs/prompts/370_f10_session_times_utc.txt` (merged in
`d6ba474`). F10 is in moto-diag-mobile's `docs/FOLLOWUPS.md`, filed
2026-05-01 by Phase 191B: `session_repo` stamps diagnostic sessions in
naive local time while "this month" starts in UTC. It must land before
2026-10-31, when it next bites.

Read first: the 369 handoff (`docs/handoffs/2026-10-01_369_closed.md`),
F10, the note above `session_repo._month_start_iso()`, 191B's
`video_repo._month_start_iso()`, and 281's bug fix #2
(`docs/phases/completed/281_phase_log.md`).

The first commit: **row 370 🚧** (`f9451dd`), with wholetree.sh at 1523
passed.

### 2026-10-06 — Step 0, and the stop

`370_step0.md`. What it found:
- **Every fact in the prompt holds** (S0-2), at the same line numbers.
- **F10 reproduces on demand** (S0-3). With the clock frozen at 2026-10-31
  21:42 EDT (2026-11-01 01:42 UTC), today's code fails gate 9's lifecycle
  and six Phase 178 quota tests: 7 failed, 3 passed. On the real clock all
  ten pass.
- **The format decided:** `YYYY-MM-DDTHH:MM:SS.mmm+00:00` (S0-4). It is
  the shape the month start, the API's `since` and the CLI's filters
  already compare in. The offset is in the string, and three fraction
  digits are the ECMAScript format every JavaScript engine must parse.
- **Every reader listed** (S0-5). The predictor does not read session
  times. The app parses with `new Date(iso)`. The CLI, the report Timeline
  and client memory's dates are made to show local time.
- **The live rows** (S0-6): converting changes 10 fields in 7 sessions,
  previewed by `370_live_rows_preview.py` (read-only).
- **F186 filed:** work-order, issue, intake, repair-plan and booking times
  are stamped local and compared with UTC by shop analytics' rolling
  windows.

Stopped for the operator. There are three questions: the live rows (rule 1),
the note stamp in notes text (what a user sees), and whether F186 rides
in 370 (a real fork).

No refute pass ran.

### 2026-10-06 — The operator's answers

The operator's words, verbatim:

> Q1: A. Apply 079 live only if the dry-run diff changes exactly the 10 fields in the 7 sessions your preview shows, each to the preview's value, and nothing else. Anything else, stop and show me.
> Q2: (a), local time with its offset.
> Q3: separate phase; 370 ships F10 only.

So 370 ships:
- every session time in UTC;
- migration 079, converting the 10 live fields. It goes live only if the
  dry run's exact diff is exactly `370_live_rows_preview.out`'s ten
  changes; anything else is a stop;
- the note stamp as local time with its offset (`[2026-10-06T15:42-04:00]`).

F186 stays open for its own phase.
