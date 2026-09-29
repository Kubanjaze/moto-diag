# Phase 360 — F174 powertrain default, and the edit guard — phase log

**Status:** 🚧 In progress
**Branch:** `phase-360` (Opus session, main checkout, the only writer)

---

### 2026-09-28 — Opened

The prompt is `docs/prompts/360_powertrain_and_edit_guard.txt` (merged in
`145d0b6`). The operator's decisions of 2026-09-28, verbatim:

> 1, 2, 3, 5 as recommended.

> add to the F174 phase: enforce the edit rule. 356 and 357 both edited source without the Edit tool — a written rule broken twice. PreToolUse hook on Bash that blocks sed -i, heredoc/redirect writes into src/ and tests/, same fail-closed pattern as the push guard, with a planted positive control per blocked form.

Recommendation 5 was a small phase for F174 before Track O batch 1.

Read first: the 357 handoff (`docs/handoffs/2026-09-28_357_closed.md`),
F174 and 357's amendment, the Track O triage with the decisions at its top,
the deploy skill, and `pre_push_guard.sh` / `_pre_push_guard.py`.

- 360 is the next free number: the highest row was 359, and no phase
  document or handoff names 360.
- Row 360 🚧: `dfb0a9a`, pushed. `roadmap_check.py` green; the row is 61
  words. `wholetree.sh` before the commit: 1480 passed.

### 2026-09-28 — The session's machine slept mid-Step 0

After `dfb0a9a`, the machine slept before any Step 0 document was
written. The operator measured, and this session re-measured:
- only `dfb0a9a` had landed, and it was pushed;
- the tree was clean and `in_progress/` was empty;
- live was untouched: the database file's mtime was still 14:49, and it
  held 10 bikes, all `ice`, at schema 73.

The census and the 17 tables referencing `vehicles` were read again, with
the same result. The per-option test counts had been grep counts of call
sites, not a measurement, so they were measured again by running each
option in a worktree (S0-6).

### 2026-09-28 — Step 0

`360_step0.md`. In short:
- **Six paths store `ice` nobody stated**: the four named, plus the photo
  path when the vision reply omits the key, and the column default, which
  live rows 6–9 very likely came through.
- **Storing NULL changes no reader's output today except `garage list`**,
  which prints NULL as `ice`.
- **The live census is `ice` 10**, every one a petrol-only model. Whether
  anyone stated them cannot be told. No option changes a live row.
- **The fork**: (a) require or ask everywhere; (b) store unknown; (c) the
  CLI asks and the API stores unknown. Recommended: (c), with
  `workflow start` storing the stated value on a bike held as unknown.
  Migration 074's rebuild (the default removed) is common to all three.
- **The guard's design**, with its blocked forms, fail-closed cases,
  allowed forms and known limits. `perl -i` is proposed beyond the
  operator's list.

Decisions made here, not stops:
- **The per-option counts come from a worktree of `dfb0a9a`**, run with
  `PYTHONPATH` set to the worktree's `src`, never from a checkout of this
  tree. Its own 16 baseline failures are subtracted as IDs. They come
  from the worktree's location: the packaging tests' fresh venv, and gate
  11's read of the sibling mobile repo. That ceiling is written in S0-6.
  Measured counts beyond that baseline: (a) 85, (b) 6, (c) 61; every one
  is a test that pins the old default or adds a bike without a
  powertrain.
- `engine_type`'s identical default is out of scope. It is filed as F177
  with this Step 0, because the first `wholetree.sh` run failed B2 on the
  citation before the entry existed.
- The app's `ice` preselection is the mobile repo's finding, for a session
  rooted there.

**Stopped for the operator's pick on part 1** (rule 1: a real fork).
