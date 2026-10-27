# Phase 392 — The fleet follows the plan of record

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-27 (v1.0 `acfb11d`)

---

## Goal

The fleet was built to take the operator's place as the message bus
(`docs/reports/2026-10-22_fleet_proposal.md`): answering what the plan of
record already answers, approving what already passes the written rules,
and carrying state between windows. It never read the plan of record
(Step 0, S0-1). This phase makes it:

- every rank that plans or judges reads `docs/reports/2026-10-12_plan_of_record.md`
  and `docs/decisions.md`, and what it writes cites the dated entry or the
  K-id that bears on the phase; `plan_check` holds the v1.0 to it;
- the next mission comes from the plan's "Next, in order" list (K48),
  through a one-row pull request the operator merges by hand (K49);
- a stop the record already answers is answered from it, by lookup (K50);
- and four findings that could trip its own proof close: F223, F226
  (K45), F225 and F227 (K46, K51), F228 (K47).

Unblocks: 303 and 348, the next first-shop phase in the plan (K43).

*As built:* all of it, and F227's leak, found in `init_db` and fixed (bug
fix #1). The list was corrected before it merged (K52).

## The plan of record

- **The entry that puts 392 in order:** the plan of record's "2026-10-26,
  later: 392 goes between 391 and 303/348", the operator's decision K44
  ("its supposed to replace what ive been doing. so bridge that gap
  however it must, thats priority, so we can continue on track").
- **What it unblocks:** 303 and 348 (K43: "a later fleet-only phase must
  name the first-shop phase it unblocks").
- **Riding along:** K45 (F226), K46 (F225, F227), K47 (F228); the Step 0
  answers K48–K51; K52, the list's two corrections.

## Logic

1. **`.claude/skills/fleet/plan_order.py`** (new), the one reader of the
   record, pure functions, no model: `parse_order` (the "Next, in order"
   table, `| # | phase | kind | built by | needs the operator | entry |`,
   and its "As of <date>, <K-id>." line), `changes` (the dated entries),
   `decisions` (with the `Covers` column), `check` and `check_texts`,
   `next_entry`, `first_shop` (Wave 1), `bearing`, `brief_block`,
   `cite_line`, `answer`, `names`. A need is `nothing` or one of
   `an outside account`, `an outside person`, `a credential`, `a fork`,
   `a live change`, and (K52) `a rule change`, with a colon and what.
   *As built*, with `tests/test_phase392_plan_order.py`: the real list and
   decisions file read with nothing wrong; each refusal on its own
   known-bad copy of the real files.
2. **The plan of record and `docs/decisions.md`.** The list at the plan's
   top, as of 2026-10-27, K52: 392 (a builder's), 303, 348, then Wave 1's
   own numbering, each row's need from Wave 1 and "The operator's steps
   outside the code"; the dated entry of 2026-10-27 (K48, and K52's
   sub-bullet). `docs/decisions.md` has the `Covers` column; K32–K52 are
   all `no stop`. `yeoman.py decide --covers` refuses a rule-1 kind and a
   line that is not a lookup.
3. **The ranks read and cite.** `brief_block` in the Science Officer's
   judgement call, the Captain's v1.0 and recommendation briefs, the XO's,
   the Red Team's context and the Quartermaster's; each brief says what in
   it is a finding. `cite_line` ends the XO's verdict, the Red Team's issue
   and PR comments, the Captain's recommendation and the Quartermaster's
   verdict, and the Science Officer's report has a scripted "## The plan of
   record" section. *As built*, `tests/test_phase392_ranks_cite.py`.
4. **`plan_check.py` P9 and P10**, as planned. `BEFORE_THE_RECORD`, measured
   rather than guessed: 384 and 386 at their v1.0 fail P9 only, 387 fails
   both. Four known-bad cases; the good tree has a plan of record and a
   decisions file (K90–K92; 900 is a builder's row, so no walk-through
   starts a mission it did not ask for).
5. **The next mission** (`stage_next`, journaled, a kill point): as
   planned, with `row_branch`, `mark_row_active`, `mission_body`,
   `ask_text`, `row_pr_body` (plain English and a one-line paste block
   ending ALL GOOD or SOMETHING IS OFF, `-R Kubanjaze/moto-diag`), and the
   push gate's rank `row` (`row_status_only`: one line, the phase's status
   to 🚧). `dispatcher.py next --dry-run` says what the next cycle would do.
   *As built*, `tests/test_phase392_next_mission.py`.
6. **Answered stops** (`answer_stop`, `engineer.ANSWERED`), as planned.
   *As built*, `tests/test_phase392_answers.py`.
7. **F223** (`fleet_git.trusted_authors`, `from_trusted`,
   `opened_by_trusted`; `Fleet.comments`, `issues_open`, `pr_has_comment`;
   `xo.prior_rounds`, `xo.review(identity_file=…)`). *As built*,
   `tests/test_phase392_authors.py`.
8. **F226** (`clean_tmp`, `nothing_back`), as planned.
   *As built*, `tests/test_phase392_tmp.py`.
9. **F225** (`CHECK_TIMEOUT_S = 5400`, `run_group`). *As built*,
   `tests/test_phase392_check_limit.py`.
10. **F227**: `LimitNOFILE=1048576` in the unit; the probe
    (`392_fd_probe.py`); the leak, found in `init_db` and fixed (bug fix
    #1, `tests/test_phase392_init_db_closes.py`); the planted small-limit
    run (`tests/test_phase392_open_files.py`).
11. **F228** (`red_team.check_table`, `open_wording`, `with_finding`,
    `wording_entry`, the brief; `dispatcher.next_f`, `write_finding`; G3
    for `red-team-record` on `docs/FOLLOWUPS.md`). *As built*,
    `tests/test_phase392_red_team_c7.py`, with #14's round 3 as
    `fixtures/red_team/14_round3.json`.
12. **The skill, its CHANGELOG, the findings**: F223, F225, F226, F227 and
    F228 closed; F221's method says what replaced the shrink.

## The change log's three newest entries

- **2026-10-26, R8: an operator paste block's `gh` names its repository.**
  The check it became: `tests/test_roadmap_continuity.py`
  (`.claude/skills/closeout/roadmap_check.py` R8). This phase's operator
  blocks, and the row PR's, carry `-R Kubanjaze/moto-diag`.
- **2026-10-22, `fleet` joins the procedure folders.** The folder's own
  tests hold it (`tests/test_phase387_fleet_contract.py`); the row is
  text. This phase extends the folder.
- **2026-10-20, rule 6: plain English to the operator.** No check: the
  entry says "Text only; no check holds it." The next-mission comments,
  the row PR's body and the handoff's blocks are written to it.

## Rule-1 stops anticipated

- **A real fork:** none open; the four Step 0 questions were answered
  (K48–K51) and the list corrected (K52).
- **A threshold or a rule's definition:** the open-file limit and the
  check's time limit, set by the operator (K51). Nothing else changed.
- **A test that cannot be made green:** none met.
- **A login or a credential:** the unit's install needs the operator's
  sudo: one paste block in the handoff.
- **A live-database change:** none; nothing here reads live. Bug fix #1
  changes how `init_db` closes its connection, not what it writes.

## Tests

- `tests/test_phase392_plan_order.py` (45), `test_phase392_tmp.py` (16),
  `test_phase392_authors.py` (13), `test_phase392_next_mission.py` (12),
  `test_phase392_ranks_cite.py` (10), `test_phase392_red_team_c7.py` (10),
  `test_phase392_answers.py` (4), `test_phase392_check_limit.py` (4),
  `test_phase392_open_files.py` (2), `test_phase392_init_db_closes.py` (1);
  added to `test_phase387_fleet_contract.py` (10), `test_phase387_yeoman.py`
  (3), `test_phase388_service_contract.py` (2),
  `test_phase390_resume_contract.py` (1). Counted by a diff of collected
  ids against master at `f1763df`: +133 −0, floor 11605 → 11738.
- 387's to 391's walk-throughs carried on: the stand-ins learned comment
  authors and issue creation, and the issues that modelled the fleet under
  the operator's login carry the trial marker, as #14 does.
- `docs/phases/in_progress/392_mutate.py`: 53 mutations, 53/53 red
  (`392_mutate.out`).
- `wholetree.sh` before each commit; `wholetree.sh --full` then
  `regression.sh` in the fence for the regression of record.

## Non-goals

- Promoting the Quartermaster; the operator's master ruleset.
- Running 303 or 348 here: after the merge, the fleet starts them.
- Any migration, anything under `data/`, seed data, a split or an eval
  protocol, or live.
- Changing the order of any row (K52 corrected two rows' needs, not their
  places).
- F224 (a commit named in two code files): open, for a later phase that
  runs its own regression.

## Planned items

- [x] `plan_order.py`, the list, the `Covers` column, `decide --covers`
- [x] the ranks read and cite
- [x] P9, P10, their cases, the pin
- [x] the next mission and the `row` rank
- [x] answered stops
- [x] F223
- [x] F226, with the disk measured before and after two stages
- [x] F225, F227 (the probe, the unit)
- [x] F228
- [x] skill, CHANGELOG, findings; mutations; regression; close-out; handoff

## Deviations

- **A change under `src/`** (bug fix #1). v1.0 planned none. F227 asked
  for the leak to be found; it was `init_db` never closing its
  connection, so every CLI command left one for the garbage collector,
  and in the fence one worker ended the suite holding 919 open files.
  Fixed in one line, with a test that failed first. Behaviour unchanged:
  the same commit or rollback, then a close.
- **K52**, after v1.0: the operator, relaying the advisor, corrected rows
  6 (371: Stripe's live account too) and 8 (330: F210's rule first). The
  need kinds gained `a rule change`, asked with `needs-admiral`.
- **`dispatcher.py next --dry-run`**, not in v1.0: the read-only proof of
  the next-mission step before the merge, as `recover --dry-run` is for
  the resume.
- **The F227 measurement went further than planned**: a second fenced run
  with per-test tracing inside the workers, which is what found the leak;
  the first probe's run, outside the fence, saw no build-up.
- **The F226 proof's stages are model-free runs**, made by this branch's
  `check_run` from `392_disk_proof.py` in a state folder of their own, the
  first being the regression of record: the service runs master's code
  until the merge, so its own stages could not show this phase's deletion.
- **Tests outside the plan's list**: 387's to 391's walk-throughs and
  contract tests changed where F223, P9 and the reclaim line meant they
  had to (each named in the phase log).
- **`next_due` reads master's record from the mirror** (`check_texts`),
  rather than from a stage clone each cycle: no clone is made unless there
  is something to do.

## Results

- **What each rank reads and cites:** the Science Officer, the Captain, the
  XO, the Red Team and the Quartermaster read `brief_block` (the "Next, in
  order" row, each dated change and each K-id naming the phase, verbatim);
  their comments end with `cite_line` (for 303: "the plan of record's
  'Next, in order' #2; …; K43; K44").
- **The check:** P9 and P10, four known-bad cases each failing alone, the
  pin equality-tested.
- **The next mission:** on a scratch mirror with 392 merged, `next
  --dry-run` printed "next: would open the mission issue for phase 303 (the
  plan's #2), then open the row's pull request (`phase-303-row`)".
- **F227:** the worker's peak 793, then 922 with 919 held at the end;
  the leak was `init_db`; the unit's limit is 1048576.
- **F226, the disk, two stages** (`392_disk_proof.py`, each a full
  model-free run made by this branch's `check_run`): stage 1, C: 331.11 →
  295.60 GB free, the image 184.09 → 219.26 GB; stage 2, C: 295.59 →
  295.61 GB, the image 219.26 → 219.26 GB. After each, `run/tmp` held only
  its worker-loss folders. The image grows to the fleet's peak and stays
  there; it did not grow with the second stage, so the operator's stop was
  not met. At Step 0 the image was 119.00 GB and C: had 396.35 GB free;
  this phase's own probes took most of the difference.
- **Mutations:** 53/53 red (`392_mutate.out`).
- **Regression of record** (inside the fence, after `wholetree.sh --full`
  4788 passed): Regression of record: 11633 passed, 0 failed, 105 skipped, 0 errors at `98083c3` (35 min 12 s wall, `python -m pytest -n auto --dist load`, exit 0) (run inside the fleet's fence)
