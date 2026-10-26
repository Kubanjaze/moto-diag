# Phase 391 — The Quartermaster, in shadow

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-26 (v1.0 `d2947f5`)

---

## Goal

Step 8 of `docs/reports/2026-10-22_fleet_proposal.md`: the last rank before
a merge, in shadow. On `merge:needs-review`, after the Captain's
recommendation, the Quartermaster checks a fleet-built pull request the way
the operator does before merging, and writes its verdict: **merge**, or
**refuse** naming each check that failed. The verdict goes on the PR, on the
mission issue and in the digest. **It never merges and sets no label**: the
operator still merges by hand, and the digest shows whether the two agreed.

Its scope is the proposal's decision (2026-10-22): an extension or a
greenfield phase, with no migration, nothing in the repository's data folder and no live
apply. Anything else it refuses as out of scope, before any run.

Promotion out of shadow is not in this phase: it is the operator's decision
afterwards, recorded in both CLAUDE.md files with the date.

## Logic

1. **`.claude/skills/fleet/quartermaster.py`**, the rank. Pure functions
   over a stage clone of the PR's head, and one model call:
   - `scope(clone, phase, base)` → **Q1**: the Step 0 report's
     `Classification:` is extension or greenfield (P4's parse); the diff
     from `master` touches no `src/motodiag/core/migrations.py`, nothing in
     `wholetree.CONTENT_PATHS` and no path in the top-level data folder; no
     `<phase>_dryrun_diff.md`. A failure here is the verdict: refuse, out
     of scope, with no run and no model call.
   - `issue_checks(comments)` → **Q2** the Captain's newest recommendation
     is `merge`; **Q3** the Red Team's newest verdict is `clear`, newer
     than the Engineer's newest `pr-ready` (S0-4).
   - `full_run(ok, line, why, log_text)` → **Q4**: the model-free `wholetree.sh --full`
     and `regression.sh` on the head passed and count what the phase log's
     regression of record counts (`engineer.counts`).
   - `read_verify(text, phase)` → **Q5**, one result per check of
     `verify_phase.sh`'s fourteen, by S0-1's table (`V1`…`V14`); checks
     1, 7, 8 and 9 read as "not read, and why". V10 needs a pytest summary
     line with no `failed` or `error` (a run with no pytest at all prints
     none: S0-6).
   - `claims(clone, phase, tip)` → **Q6**: v1.0's commit in v1.1's header,
     every `**Commit.**` and `Commit:` line, and the regression of
     record's commit, each an ancestor of the head (S0-3).
   - `stubs(v11)` → **Q7**: `plan_check.unfilled` on v1.1; a non-empty
     Results and Deviations; no unticked box.
   - `handoff(clone, phase)` → **Q8**: `docs/handoffs/<date>_<phase>_closed.md`
     on the branch, dated no earlier than the close, with "What is open"
     and "What is next"; `roadmap_check.check_tree` empty on the branch.
   - `mergeable(clone, base)` → **Q9**: the clone is clean and
     `git merge-tree --write-tree` onto `master` exits 0.
   - `judge(...)`: one fresh read-only Opus call (`rank_call.call`,
     `FENCE`, `OPUS`), never the builder's session, with the brief, the
     checks' results, check 4's hits, the v1.0 → v1.1 diff, the Captain's
     and the Red Team's words and the PR body. Its schema: verdict,
     `failed` (each naming a check), summary. **The script composes the
     verdict**: any scripted failure refuses, whatever the model says; a
     model `refuse` must name a check id from the list the brief gives, or
     the stage stops (the dry run's model named checks of its own, Step 0
     S0-5); a model `merge` beside a scripted failure is recorded as such.
   - Finish line: each function's known-bad fixture fails on its own check
     and on no other.

   *As built:* as planned, with one change: Q8 has no date rule of its own.
   It ran R6's (a handoff dated no earlier than the close) a second time,
   and the mutation that removed it survived (Deviations). The good tree for
   the tests is a real phase the operator merged, 390 at `48e7d2c`, with
   its handoff's paste block corrected; **390 as it shipped fails Q8 on
   R8**, the block that failed for the operator on 2026-10-26.
2. **`dispatcher.py`: `stage_quartermaster`**, journaled like every 390
   stage: `begin`, the `started` marker, the stage clone of the branch, the
   scope, the two model-free runs through `checked` (so the free-space
   floor holds them, and a resumed stage reads a finished run back), the
   call through `FencedRunner`, then the PR comment and the issue marker
   `<!-- fleet-quartermaster: verdict=<merge|refuse> failed=<ids> -->`, each a `step`
   checked against GitHub on a resume. No label is set or removed.
   - Due on `merge:needs-review` once per application (`due_for`), and only
     for an application after `state.json`'s `quartermaster_since`, set the
     first time a dispatcher with this stage runs a cycle (S0-4).
   - `verify_phase.sh` runs as a `check_run` command, and a command run
     keeps its whole output, in the journal too (`Check.out`).
   - `resume()`, `STAGE_RANK`, `NEXT_RANK` (the sweep's text) and the
     module docstring name it.
   - Each verdict is appended to `quartermaster.jsonl` in the state
     directory: issue, PR, phase, head, verdict, the failed checks, run.
   - Finish line: the end-to-end stand-in test runs mission to verdict;
     every kill point resumes.

   *As built:* as planned. `QM_M` is a rank comment (`RANK_PREFIXES`), so a
   later stage ends it and the search on start reads it. A resumed stage
   reads both model-free runs back from its journal, `verify_phase.sh`'s
   output included (a test holds it). 389's walk-through now ends at the
   verdict.
3. **The digest**: `yeoman.digest` takes the day's verdicts, and `facts`
   writes a section, "The Quartermaster (shadow)": each verdict with its
   PR, the checks it named, and the PR's state now (merged, closed or open)
   beside it, so a merge refused or a refusal merged shows. The dispatcher
   passes the day's lines from `quartermaster.jsonl`. Finish line: a test
   with one match and one miss.

   *As built:* `yeoman.shadow`; each verdict says "Agrees with the
   operator: yes", "NO", "not yet" (the PR is open) or "unknown" (`gh`'s
   answer unreadable).
4. **The skill's records**: `SKILL.md` (the rank, Q1–Q9, the shadow),
   `CHANGELOG.md` (the phase's entry), `fixtures/quartermaster/` (the
   known-bad cases, one per check, and the real PR #20 context from the
   dry run).

   *As built:* the known-bad cases are edits to the real 390 tree inside
   the tests, not files; `fixtures/quartermaster/pr20/` holds the dry run's
   four real artefacts. `fixtures/resume/kill_points.json` gains the
   stage's four kill points, and 390's contract finds their tests in 391's
   file.
5. **The proofs**, on the service, cut once by a restart in a gap with no
   #14 stage running (pre-approval (c)), under the operator's login with
   the trial marker (pre-approval (a)), each issue and PR closed unmerged
   afterwards:
   - **green**: this phase's branch, finished, its trial issue opened at
     `review:open`: the real Red Team and the real Captain, then the
     Quartermaster: merge;
   - **stub**: the green head plus one commit making v1.1's Results a
     stub, the Red Team's clear and the Captain's merge planted by hand and
     said to be: refuse, naming **Q7** (and **V4**);
   - **no handoff**: the green head minus its handoff, planted the same
     way: refuse, naming **Q8**.
   The green verdict is set beside the operator's own on this phase at the
   merge.

   *As built:* the trials run on this phase's close-out head, after the
   close-out commit, so their outcomes are recorded after it: the two
   planted bad PRs in the commit that follows (documents only), and the
   green trial, which is the finished head itself, in the handoff's last
   section. The green trial's Red Team clear is planted too, and its
   Captain is real (Deviations).
6. **Commits**: v1.0 first, pushed; then the code with its tests; each
   commit after `wholetree.sh` run on its own and its exit read;
   `wholetree.sh --full` before the regression of record; the regression
   by `regression.sh`; the close-out.

   *As built:* in that order: v1.0 `d2947f5`, the build `a45b5be`, the
   mutations `944fd42`, the floor `ac1dc6b`; each after `wholetree.sh`,
   exit 0, in the phase log.

## The change log's three newest entries

- **2026-10-26, R8: an operator paste block's `gh` names its repository.**
  The check it became: `tests/test_roadmap_continuity.py`
  (`.claude/skills/closeout/roadmap_check.py` R8). The Quartermaster runs
  `roadmap_check` on the branch, so R8 is one of Q8's; this phase's own
  operator blocks are written to it.
- **2026-10-22, `fleet` joins the procedure folders.** The check it named
  is the folder's own tests (`tests/test_phase387_fleet_contract.py`); the
  table row is text. This phase adds a rank to the folder; the CHANGELOG
  records it, and the row's "read-only ranks, no pushes" (stale since 389)
  stays the operator's to change.
- **2026-10-20, rule 6: plain English to the operator.** No check: the
  entry says "Text only; no check holds it." The verdict's summary line
  and the handoff's operator block are written to it.

## Rule-1 stops anticipated

- **A real fork:** none seen at Step 0. Q2 (a Captain's hold refuses) and
  `quartermaster_since` are decided here, with their reasons in the log.
- **A threshold or a rule's definition:** none. The 50 GB floor, the 70%
  gates and the K9 rounds stay as they are.
- **A test that cannot be made green:** none expected.
- **A login or a credential:** none; the fleet's identity exists
  (`kubanjazefleet`), and trials use the operator's login as before.
- **A live-database change:** none; the Quartermaster refuses any phase
  that has one, and nothing here reads live.

## Tests

- `tests/test_phase391_quartermaster.py`: each Q-check on its known-bad
  fixture and on the good one; `read_verify` on the measured fence output
  and on a hand-written red one per check; the verdict's composition (a
  scripted failure refuses over a model merge; a model refusal with no
  check id stops; a malformed answer stops); the real PR #20 context
  refused on Q2 and Q3.
- `tests/test_phase391_dispatcher.py`: on 389's stand-ins, mission to the
  Quartermaster's verdict; due once per application, never before
  `quartermaster_since`; no label moved; held below the free-space floor;
  every kill point in `fixtures/resume/kill_points.json`'s new
  `quartermaster` entry resumed.
- `tests/test_phase391_contract.py`: SKILL.md and the CHANGELOG; the
  verdict never merges (no `gh pr merge` and no `merged` label anywhere in
  the stage); the fixtures' list.
- The digest's section: one match and one miss.
- 389's and 390's tests that end at `merge:needs-review` are carried on to
  the verdict where they would now meet it.
- `docs/phases/in_progress/391_mutate.py`: each check broken one at a
  time, and R8's rule; every mutation red.
- `COLLECTED_TEST_FLOOR` raised by the diff of collected ids (pre-approval
  (b)); `wholetree.sh` before each commit; `wholetree.sh --full`, then
  `regression.sh`, for the regression of record.

*As built:* all of it. 49, 17 and 8 tests in the three new files; four
kill-point tests in the dispatcher's; 389's walk-through carried on;
`391_mutate.py` 59/59 red.

## Non-goals

- Merging, closing the mission issue, or any `/closeout` tail: the
  operator's, until promotion.
- Promotion out of shadow, and the CLAUDE.md lines that record it.
- A migration, `data/`, seed data, a split or an eval protocol, or live:
  out of the Quartermaster's scope, and not touched here.
- The master ruleset (F214's other half).
- #14 and PR #15: not touched; judged only if the operator applies
  `merge:needs-review` again after this phase is live.

## Planned items

- [x] `quartermaster.py`, Q1–Q9 and the call, with fixtures
- [x] `stage_quartermaster`, journaled, under the floor, `quartermaster_since`
- [x] the digest's section
- [x] SKILL.md, CHANGELOG, contract tests, kill points
- [x] mutations, all red
- [x] regression of record, close-out, handoff, row ✅

The three trials are not a box here: they run on the head this list is
part of (Logic 5, Deviations).

## Deviations

- **The trials left Planned items.** They can only run on the finished
  close-out, so the record of them comes after it: the two planted bad
  PRs' outcomes in the next commit, the green trial's in the handoff. An
  open box here would also have refused every trial under Q7.
- **The green trial's Red Team clear is planted**, as the two bad ones'
  are; its Captain is the real one. v1.0 had the real Red Team on it: a
  back from it moves a trial issue to `build:open`, where the Chief
  Engineer would run a fix round on the trial branch. The phase's own
  refute ran instead as a fresh agent, recorded in the phase log.
- **Q8 has no date rule of its own.** It repeated R6, which Q8 runs on the
  branch; the mutation that removed it survived. Removed.
- **`yeoman.shadow` reads an unreadable `gh` answer as "unknown"**, not a
  crash: the digest is one page for the day.
- **Found and filed, not fixed (F223):** Q2 and Q3 read the Captain's and
  the Red Team's markers from whoever wrote them, as every rank has since
  389. In shadow that changes nothing; before promotion it must.
- **No bug fixes.** One defect was found before any commit held it
  (`_text` on a missing file) and is in the phase log, not the register.

## Results

To be written after the merge.
