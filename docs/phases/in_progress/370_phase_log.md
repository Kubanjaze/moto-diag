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

### 2026-10-06 — v1.0 committed (`8be7d8b`), then the build

**Code:**
- `core/timestamps.py` (new): `utc_now()`, `to_utc()`, `local_display()`,
  and `convert_session_times_079()`.
- `session_repo`: the nine stamps call `utc_now()`; `_month_start_iso()`
  returns `YYYY-MM-01T00:00:00.000+00:00`, and its 191B note is replaced; the
  note stamp is local time with its offset.
- `api/routes/sessions.py:_parse_since`: the cutoff is written in the stored
  format, and any offset is converted to UTC.
- `cli/diagnose.py`: `_short_ts` and the `list` Created column show local
  time; `--since`/`--until` are read as local time and converted. A value
  that is not ISO is now a usage error, where before it went to SQL as
  typed.
- `reporting/builders.py` Timeline and `memory/compile._date_of`: local
  time.
- Migration 079 `session_times_utc`, data only; `SCHEMA_VERSION` 79.

**Tests:**
- `tests/support/frozen_clock.py`: the frozen clock, as a helper and as a
  plugin for a spawned run. Its report header prints the time
  `session_repo` itself sees, so a freeze that did not take hold shows the
  real clock and fails the header check. This was decided after the first
  draft printed the configured moment, which mutation M24 would have left
  green.
- `tests/test_phase370_session_utc.py`: 19 tests, all at 2026-10-31
  21:42:07 EDT. The first run had 1 failure, mine: Rich folds the Created
  column at 80 characters. The assertion now takes the visible prefix
  `2026-10-31T21:4`, which UTC (`2026-11-01T01:4`) does not match.
  19 passed.

**Related suites:** 132 test files touching sessions, migrations, memory,
reports or the `diagnose` CLI, in parallel: 4313 passed, 0 failed (8 min
43 s). No existing test asserted the old naive shape.

**Mutations:** `370_mutate.py`, 24/24 red (`370_mutate.out`). M1 is the
planted control the prompt asks for: `create_session_for_owner` stamping
`datetime.now().isoformat()` again. The other 23:
- the other eight writers, the note stamp's offset, the month start's
  format and `utc_now()`;
- each reader: show, list, `--since`/`--until`, the Timeline, memory dates,
  and the API's two `since` forms;
- 079's space rule, its `post_apply` and its rollback;
- the plugin not freezing the clock.

**244G's scanner** over all of `tests/` (the new files included): 0 hits.

**`COLLECTED_TEST_FLOOR`** 10271 → 10299, measured by `--collect-only`.
The +28 is 369's 8 (369 did not raise the floor), 370's 19, and gate 15's
`[78]` rollback case. No module was added to or removed from the
integration-gap tables: `core/timestamps.py` is imported by
`session_repo`, so it is reachable.
