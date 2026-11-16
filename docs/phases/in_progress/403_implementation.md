# Phase 403 — The fleet's stops: work kept, the answer carried, the app's copy refreshed (F231, F266, F275, F261, F264, F276, F277)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-11-16

---

## Goal

A fleet-only phase, built by a builder session because it changes
`.claude/skills/fleet/`. It unblocks 404, 334 and 330 and every later shop
phase (K43, K84): 372 lost more than two days to these stops, for about
seven hours of the fleet's own work. The operator's words: "yes go with
templates, and approve both drafts" (K84), and for (e) (K88): "Option 1,
save a 4th round I grant, with three conditions: 1. One written grant = one
extra round. No 5th round without a new grant from me. 2. Ship it with a
regression test: a granted 4th round's findings get saved and acted on, and
an ungranted 4th round never runs. 3. Update the 403 plan before any code.
If this turns out to be more than a small addition, stop and ask me before
building it."

After this phase:
1. (a) An Engineer stop whose clone holds commits GitHub's phase branch
   lacks keeps its run (hold reason `stopped`); the commits go, through
   the push gate, to `phase-<N>-stopped-<run>`, never the phase branch;
   the stop note names them and says where they are. The next Engineer
   round starts from them when GitHub's branch is an ancestor of them, and
   from GitHub's branch, said in the log, when it is not.
2. (b) When the operator takes `needs-admiral` off an Engineer stop, the
   comments the operator's own account (`Kubanjaze`, no other) posted after
   the stop are quoted verbatim in a dated phase-log entry, and the
   Engineer is due again with no `plan:approved` re-applied; its brief says
   where the answer is.
3. (c) A new Engineer result, `app-copy`: the dispatcher, with no model,
   regenerates moto-diag-mobile's `api-schema/openapi.json` from the
   clone's HEAD, commits it on the app repository's branch named as the
   phase branch (never `main`), pushes it with the fleet's account, runs
   Gate 11 against the fleet's own copy of the app, and resumes the
   Engineer from its held run. The fence mounts the fleet's own copy of
   the app, never the operator's folder.
4. (d) The briefs state the checks' rules: the edit guard's (F275), the
   regression record's (F264), and the refute table's kind for a code
   finding (F261).
5. (e) A phase has three review rounds and one more for each grant: a
   `docs/decisions.md` row whose Covers cell is `grant=review-round
   subject=<phase>`. A granted round's table names its grant and passes
   C1–C7; its findings are saved and acted on. Past the rounds the
   dispatcher starts no review round, and every spent-rounds stop names the
   operator's three options.

## The plan of record

Row 15 of "Next, in order" (`docs/reports/2026-10-12_plan_of_record.md`),
built by a builder; the fleet waits for it. The list does not change.
K84 (the phase, its side branch and its one file of moto-diag-mobile), K88
((e) and its size stop).

## Logic

Causes and measurements: `403_step0.md`, S0-1 to S0-5.

1. **(d), the Engineer's brief** (`engineer.py` `BRIEF`).
   - Rule 3 states the guard's rule in its own words: `sed -i` is refused
     wherever it points; a shell write (`>`, `>>`, `tee`, `cp`, `mv`) is
     refused unless its target is a literal path the guard can read;
     scratch files go to a literal directory, `/fleet/run/`; the same
     refusal twice ends the session.
   - Rule 6 names `regression.sh`'s whole record (the regression line,
     every skip line under it, the coverage line) and the read-back with
     `closeout_check.regression_record` before the turn ends; the database
     step's `regression_line` sentence points to it.
2. **(d), the Red Team's brief** (`red_team.py` `BRIEF`): the table line
   says a code finding's row is written with the kind `factual` (F261's
   first option; no checklist changes).
3. **(a), the kept stop** (`dispatcher.py`).
   - `Fleet.keep_stop`: after an Engineer stop (a watcher's reason, a
     result `stop`, or an `app-copy` the dispatcher refuses), with the
     mirror updated: the commits `<GitHub's branch>..HEAD`. None: nothing
     held, nothing pushed, the note as today. Some: `journal.hold(run,
     {issue, phase, rnd, commit, why: "stopped", side, kind})`, then the
     side push, then the note's paragraph naming each commit (short hash
     and subject) and where it is. A refused side push is said in the
     note; the hold stands.
   - `Fleet.push_side`: `fleet_git.gate(..., side=True)` then
     `fleet_git.push` to the side branch. `gate`'s `side` holds G1 to
     `phase-<N>-stopped-<…>` exactly, keeps G2–G5, and skips only G6
     (K84: nothing merges the side branch). No pull request is opened from
     it; `branch_for`'s fallback never counts a `-stopped-` branch.
   - `escalate` gains `stop=<kind>` in its marker for an Engineer stop and
     a `more` paragraph after the bold one. The marker still begins
     `needs-admiral rank=engineer`, so every reader of it is unchanged.
   - `Fleet.engineer_clone`: an Engineer stage on an issue with a held
     `stopped` or `app-copy` run clones the held clone when GitHub's branch
     is its ancestor, sets `origin` back to the mirror, and logs it; else
     clones GitHub's branch and logs why. The held run is released once the
     new clone is made (journaled). Used by `stage_engineer`, so the
     record's answer (K50), the operator's answer and a hand
     `plan:approved` all start from the kept work.
4. **(b), the operator's answer** (`dispatcher.py`, `engineer.py`).
   - `Fleet.operator_comments(issue, after)`: the issue's comments by
     `fleet_git.OPERATOR_LOGIN` only (case-insensitive), created after
     `after`, not beginning with a fleet marker. Read raw, not through
     `comments()`, which shows the operator only on a trial.
   - Due (`next_stage`, `build:open`): the issue's last rank comment is an
     Engineer stop (`needs-admiral rank=engineer stop=`), the label is off
     (the cycle reaches the issue), and the operator has commented since.
     With no comment yet, one `fleet-no-answer` comment (read by no due
     rule) says to write the answer as a comment; the stage becomes due
     when one is there.
   - The stage is `stage_engineer(..., carried=True)`: its clone (item 3),
     then the entry appended to the phase log
     (`## <date> <time> — the operator's answer to the stop of <time>`,
     each comment as `> ` lines under its time, the login named), committed
     with no co-author, then the session. `ANSWER_CARRIED` in the brief
     names the log and the entry's heading. Round and findings as the
     record answer's path takes them (the Red Team's backs).
5. **(c), the app's copy** (`app_copy.py`, new, and `dispatcher.py`).
   - `engineer.read_result` takes `{"outcome": "app-copy", "summary": …}`;
     the brief says when (Gate 11 red only because this phase changed the
     API's description, and `wholetree.sh` green), that the dispatcher
     then refreshes the copy and resumes the session's clone, and that no
     handoff asks the operator to move the desktop's copy of the app.
   - `Fleet.app_copy`, outside the model: the clone clean; the run held
     (`why: "app-copy"`); model-free runs in the fence with no network:
     `wholetree.sh` must pass (else "another check is also red"), Gate 11
     must fail (else nothing to refresh), the generator
     (`app_copy.GENERATOR`, the 372 method, writing `/fleet/run/openapi.json`)
     must exit 0; then `app_copy.commit_copy` on the fleet's own copy of
     the app: refuses `main`, `master` or any branch not
     `phase-<N>-…`; branches from `origin/<branch>` or `origin/main`;
     writes the one file; refuses when anything else would change or
     nothing does; commits; pushes with the fleet's account only. Then
     Gate 11 again against that copy, which must pass. A comment
     (`fleet-app-copy`, read by `held_for`) says what was done; the next
     cycle resumes the Engineer from the held run (item 3) with
     `APP_COPIED` in its brief. Any refusal is a stop (item 3).
   - The fleet's own copy of the app: `fleet_git.MOBILE` becomes
     `~/.local/state/motodiag/fleet/moto-diag-mobile`; the service's
     dispatcher clones it from GitHub when it is missing, and every stage
     clone puts it on the phase branch's name when the app has one, else
     on `origin/main`. Tests never reach GitHub (`mobile_url` is set only
     by `main`).
6. **(e), the granted round** (`refute_check.py`, `plan_order.py`,
   `red_team.py`, `dispatcher.py`, `closeout_check.py`).
   - `refute_check`: the round cell may carry the grant (`4 K89 · factual
     · fixed`); `grants(decisions_text, phase)` reads the K-ids whose Covers
     is exactly `grant=review-round subject=<phase>`, in file order; C5
     passes round 3 + k only when it names grant k. `check(text, …,
     grants=())`.
   - `plan_order.covers_problem` accepts that Covers form for one phase,
     so `yeoman.py decide --covers` can write it and `plan_order check`
     passes it; any other form is refused, as today.
   - `red_team.check_table(v, table, rnd, grants)`: the round's rows get
     its grant's K-id (`with_grant`, as `with_finding` writes an F-number),
     the last round is 3 + the grants, and the checked table is the one
     recorded.
   - The dispatcher reads the grants from master's `docs/decisions.md`
     (the mirror), never the branch's. A review round past 3 + grants is
     not started: a stop, label unchanged, with the three options. A back
     in round 3 with no grant stops as today, its note now naming the three
     options; any other back starts a fix round (a granted round's findings
     are acted on); the review round after it starts only if granted.
   - `closeout_check.refute_record` (A8) hands `refute_check` the grants
     from the tree's `docs/decisions.md` and `origin/master`'s.
   - K88's size measure: `403_step0.md` S0-5, about 90 lines of code over
     five files and one test file: a small addition, so it is built.
7. **Finish line:** each fixture red on master's code and green here; the
   known-bad cases; the mutations red; the regression of record in the
   fence's conditions; `verify_phase.sh`; the handoff with the operator's
   three after-merge steps and the trial's block.

## Rule-1 stops anticipated

- The prompt's own: no loosening of the push gate beyond the side branch
  (only G6, only for `phase-<N>-stopped-…`); no write to the app's
  repository other than `api-schema/openapi.json` on a phase branch; no
  change to the guards (`_edit_guard.py`, `_pre_push_guard.py` and their
  shells are not touched).
- K88: the size measure is recorded above; it is a small addition.
- **A reading, recorded:** after a granted round's back the fleet runs a
  fix round (K88: "findings get saved and acted on"; the prompt's proof:
  "its back starts a fix round"), and the review round after it needs
  another grant ("one grant never lets a fifth round start"). After round
  3's back with no grant the phase stops, as K9 has it. The operator is
  told this reading with the pull request.

## Tests

- `tests/test_phase403_kept_stop.py`: 372's three stops replayed through
  390's world from their fixtures (base, commits' subjects, kind and
  question): held, on the side branch, named in the note, the next round
  from them; GitHub moved by hand as on 2026-11-14 (ancestor: from the
  held run; not: from GitHub's branch, logged); a stop with no new commits
  holds nothing; a held run outlives a restart and `prune_runs`; the gate's
  side mode refuses a non-side name and still runs G2–G5.
- `tests/test_phase403_answer_carried.py`: issue #59's three operator
  comments quoted verbatim after their stops; another login's comment
  never quoted; no comment, no stage; the Engineer due again without
  `plan:approved`; its brief names the entry.
- `tests/test_phase403_app_copy.py`: the generator reproduces `993fadc`
  from `cbfa766` and `d292eef` from `76bdea5` by sha-256; the step on a
  stand-in app repository: one file on the phase branch, pushed, Gate 11
  run against it, the Engineer resumed; refused on `main`, when a second
  file would change, when `wholetree.sh` is also red, without the fleet's
  account.
- `tests/test_phase403_briefs.py`: each brief against its real failure
  (F275's refusal and `_edit_guard.check`; 371's first log entry under
  `regression_record`; F261's `1 · code · open` under C5).
- `tests/test_phase403_granted_round.py`: 372's round 4 from its journal:
  with a grant planted on master, recorded (PR and issue comments) and a
  fix round started; with none, no round 4 starts (the old code ran one);
  one grant never lets round 5 start; a grant for another phase or in
  another form grants nothing; the spent-rounds stops name the three
  options; C5 and A8 with grants.
- Old code: each new file against master's `.claude/skills/`, red.
- Mutations, `403_mutate.py`.
- `COLLECTED_TEST_FLOOR` raised by a diff of collected ids.

## Non-goals

F260, F267, F256, F263, F262, F265, F217's missed digests, F230, F237,
F238, F253 (the prompt's list). The guards. The operator's own
`~/Projects/moto-diag-mobile`. The fleet's service: it moves to master
only by the operator's after-merge block.

## Planned items

- [ ] (d) the two briefs
- [ ] (a) the kept stop, the side branch, the next round from it
- [ ] (b) the operator's answer carried
- [ ] (c) the app-copy step and the fleet's own copy of the app
- [ ] (e) the granted round
- [ ] the fixtures red on the old code; the known-bad cases; the mutations
- [ ] the regression of record, `verify_phase.sh`, the close-out, the handoff

## Deviations

(v1.1)

## Results

(v1.1)

## Version history

| Version | Date | What changed |
|---|---|---|
| 1.0 | 2026-11-16 | The plan, before any code |
