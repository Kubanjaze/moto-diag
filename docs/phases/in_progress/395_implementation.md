# Phase 395 — The fleet hands the operator the database step

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-29

---

## Goal

Unblocks 348 (K43, K58), whose new table needs a live migration. Today a
phase with a migration has no path through the fleet (F232): the fence
never sees live, so the Engineer cannot dry-run or apply, and it closes
out in the session that builds, so K18's point between the regression of
record and the close-out does not exist; the Quartermaster's Q1 refuses
any migration.

After this phase:
1. an Engineer whose plan names the database step builds the migration,
   its scope file and its tests, runs the regression of record and ends
   with a new outcome, `deploy`, believed only as a `pr-ready` is;
2. the dispatcher pushes the branch, holds the run, and hands the operator
   one comment with one paste block for the desktop: the dry run on a
   copy, the change in plain words, nothing applied until the operator
   types yes, the apply, the check, ALL GOOD or SOMETHING IS OFF;
3. when the operator takes `needs-hands` off, the dispatcher checks live
   against the approved diff and gives the Engineer a close-out round in
   the same clone, then the usual `pr-ready`;
4. Q1 passes a migration applied this way, and only that way.

## The plan of record

Row 5 of "Next, in order" in `docs/reports/2026-10-12_plan_of_record.md`,
after 393 and before 348, built by a builder: the dated entry of
2026-10-29, on the operator's word recorded as K58 in `docs/decisions.md`
("yes go ahead"). Unblocks: 348, the audit log, whose new table needs a
live migration; every later first-shop phase with a migration goes the
same way.

## Logic

Design and reasons: `395_step0.md`, S0-3 and S0-4.

1. **`.claude/skills/deploy/through_fleet.py`** (new), the block's work,
   run with the fleet's venv from the fleet's checkout (master's tools):
   `through_fleet.py <phase> <branch> <commit> <issue>`.
   - refuses (exit 4) when live is not on this machine;
   - clones the fleet's mirror to `~/motodiag/deploy/<phase>` at the
     commit, which must be the branch's head there;
   - refuses a branch that changes `.claude/skills/deploy/` or
     `.claude/skills/closeout/`, or has no scope file;
   - `deploy.dryrun` with the branch's `src/` for the migration and the
     seed build; a scope problem stops it;
   - prints the change in plain words: tables, indexes and triggers
     added, removed or rewritten; columns added; rows added, changed and
     removed per table;
   - asks on the terminal (`/dev/tty`), and writes the answer verbatim to
     `<phase>_deploy_answer.md`; anything but `yes` stops, nothing applied;
   - commits the dry-run diff and the answer; stops the API if it serves
     this database; `deploy.apply_live`; starts the API and reads
     `/healthz`; commits the live diff; `deploy.verify_live` must exit 0;
   - run again after the apply, it changes nothing and runs `verify-live`;
   - every failure prints `SOMETHING IS OFF: <reason>` and exits non-zero.
   Finish line: each refusal tested on fixture databases; the trial.
2. **`engineer.py`.** The brief's database step: when the plan has
   `## The database step`, the Engineer writes the migration, the scope
   file and tests on fresh databases, runs the regression of record, and
   ends with `{"outcome": "deploy", "summary", "regression_line",
   "live_change"}` instead of closing out; a migration the plan does not
   name, or one that alters or deletes existing live rows, is a stop.
   `read_result` accepts `deploy`; `verify_deploy` believes it only with a
   clean clone, the scope file committed in `in_progress/`, a migration
   changed against master, no dry-run or live diff yet, the phase's
   documents still in `in_progress/`, and the model-free run counting
   what the Engineer's line counts. A `CLOSEOUT` brief for the round after
   the apply. `verify_after_apply`: no code path changed after the live
   diff's commit, and the answer quoted in the phase log. The fix round's
   brief: an applied migration is not changed.
   Finish line: the fixtures below, seen red.
3. **`dispatcher.py`.**
   - On a `deploy` result: the model-free full run on HEAD; `verify_deploy`;
     the push through the gate; `journal.hold(why: deploy, commit)`; one
     comment (which computer and which window, the change in one
     sentence, one paste block); `needs-hands`.
   - `held_for` releases a `deploy` hold once `needs-hands` is off and its
     comment is the newest rank comment; `stage_deployed`: fetch the
     deploy checkout's commits into the held clone (only the three deploy
     files may change), `verify-live` outside the fence (exit 0 or
     `needs-admiral`, no Engineer), the Engineer's close-out round, then
     `engineer_finish` with `verify_after_apply`; release the hold.
   - After a live diff is on the branch, `engineer_finish` refuses any
     later change to `src/motodiag/core/migrations.py`.
   - Resumable like every stage (`resume`, `STAGE_RANK`).
   - Q1 is given `verify-live` as `live_check`.
   Finish line: `tests/test_phase395_*`.
4. **`quartermaster.py` Q1.** A migration or a dry-run diff passes only
   with the dry-run diff, the live diff (no scope problem, equal to the
   approved diff) and the answer committed, and `live_check` exiting 0;
   with no `live_check` it refuses as before. `NOT_READ["V8"]` says so.
5. **`captain.py`, `xo.py`.** The briefs: a migration is in scope when the
   plan names the database step; a plan that alters or deletes existing
   live rows still lists that as a rule-1 stop.
6. **Documents.** "Through the fleet" in the fleet skill's and the deploy
   skill's `SKILL.md`, each skill's `CHANGELOG.md`; F232 closed.
7. **The trial**, once, on the desktop: a planted phase whose migration
   adds one empty table, through the real dispatcher methods, the real
   push gate (to a local stand-in for GitHub), the real
   `through_fleet.py` against a copy of live (`MOTODIAG_LIVE_CONFIG`,
   `HOME` a trial folder), the real `verify-live`, and Q1. Its output kept
   as a fixture.

## The change log's three newest entries

- **2026-10-29, rule 6: the code's counts only improve, and the weekly
  page (Phase 393, K54).** The check it became:
  `tests/test_phase393_quality_ratchet.py`. This phase's new code is held
  by it.
- **2026-10-26, R8: an operator paste block's `gh` names its repository.**
  The check it became: `tests/test_roadmap_continuity.py`
  (`.claude/skills/closeout/roadmap_check.py` R8). The paste block in the
  dispatcher's comment and the handoff's block carry `-R Kubanjaze/moto-diag`.
- **2026-10-22, `fleet` joins the procedure folders.** Held by the
  folder's own tests (`tests/test_phase387_fleet_contract.py`). This phase
  extends the folder.

## Rule-1 stops anticipated

- **A real fork:** none; the order of the Red Team and the apply stays as
  today (the prompt's default).
- **A threshold or a rule's definition:** none; no refusal of the deploy
  skill changes.
- **A test that cannot be made green:** none expected.
- **A login or a credential:** none; the after-the-merge block is the
  operator's own.
- **A live-database change:** none; the trial uses a copy of live, never
  live.

## Tests

- `tests/test_phase395_through_fleet.py`: the block's script on fixture
  databases and a real git mirror: a clean run (diff, answer, apply, live
  diff, verify), "no" stops with live unchanged, no scope file, a branch
  that changes the deploy tools, a commit that is not the branch's head,
  a scope problem, live elsewhere, a second run, the plain words, the API
  left alone on a stand-in.
- `tests/test_phase395_engineer_deploy.py`: `read_result` and
  `verify_deploy` (a dirty clone, no scope file, no migration, a diff
  already there, documents moved, counts differ),
  `verify_after_apply` (code after the apply, the answer not quoted), the
  briefs.
- `tests/test_phase395_dispatcher_deploy.py`: on 389's harness, a deploy
  to its hold, comment and label; the resume (live not equal, wrong files
  fetched, a clean close-out to `review:open`); a migration changed after
  the apply; the planners' briefs.
- `tests/test_phase395_q1.py`: Q1 with a migration and no live diff, with
  a live diff saying no, with `live_check` failing, and passing.
- Known-bad fixtures in `.claude/skills/fleet/fixtures/deploy/`, each seen
  red: a deploy with a dirty clone, a deploy with no scope file, a resume
  with live not equal to the approved diff, a code change after the
  apply, Q1 with a migration and no live diff.

## Non-goals

348 itself; the phone app's address-list step; finding numbers given out
twice (F230); the Engineer's missing cost line; any change to live; any
change to a refusal in `deploy.py`; a dry run in the dispatcher; the order
of the Red Team and the apply.

## Planned items

- [ ] `through_fleet.py` and its tests
- [ ] the Engineer's `deploy` outcome, `verify_deploy`, `CLOSEOUT`, `verify_after_apply`
- [ ] the dispatcher's pause, comment, resume and close-out round
- [ ] Q1 with `live_check`
- [ ] the Captain's and the XO's briefs
- [ ] the known-bad fixtures, seen red
- [ ] the mutations, red
- [ ] the trial, on the desktop, against a copy of live
- [ ] "Through the fleet" in both skills; F232 closed
- [ ] the regression of record, the close-out, the handoff with the after-the-merge block
