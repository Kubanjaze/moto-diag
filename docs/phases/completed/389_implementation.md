# Phase 389 — The Captain and the Engineer

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-25 (v1.0 `18af1fa`)

v1.1 updates every section to what shipped (each change marked "As
built"), ticks the planned items, and adds Deviations and Results.

---

## Goal

Steps 6 and 7 of `docs/reports/2026-10-22_fleet_proposal.md`: the first
seats that write. Four ranks join the fleet, each a script that runs one
fenced `claude -p` call (or one long one) and moves a label only from a
checked result:

1. **The Science Officer** (`scout.py`, Haiku): on `mission`, the Step 0
   report, every count with its query, and the prompt saved; `step0:done`.
2. **The Captain** (`captain.py`, Fable): on `step0:done`, v1.0 with every
   section, committed and pushed on the phase branch; `plan:needs-review`.
   On `review:clear`, a three-line merge recommendation on the PR. Never
   touches `src/`.
3. **The Chief Engineer** (`engineer.py`, Opus): on `plan:approved`, the
   build in a fresh fenced clone to a PR, with the full suite run by the
   Engineer and again by the dispatcher with no model; `review:open`. It
   stops on `needs-admiral` at a third bug fix, at a rule-1 condition, and
   when a guard blocks twice for the same reason.
4. **The Red Team** (`red_team.py`, Opus, a fresh call that did not build
   it): on `review:open`, `/refute` with C1–C7, the F9 checks and the A1–A8
   diff of v1.0 against v1.1, posted on the PR; `review:clear` or back to
   the Engineer, three rounds at most.

The dispatcher runs all four, with the 70% rule on Fable's own weekly cap
too. Merging stays the operator's; the Quartermaster is the next phase.

The prompt is `docs/prompts/389_captain_engineer.txt`. Step 0 is
`389_step0.md` (classification: extension). The operator's steps are
`389_operator_steps.md`.

As built: all four ranks, the gate and the dispatcher's stages shipped and
ran live on the service. Two of the operator's answers added to the goal:
a regression run inside the fence can be of record, and the gates read the
usage on the operator's sign-in (both in Deviations).

## Logic

### 1. The fence (`fence.sh`, `fence_net.py`)

Three changes, each measured in Step 0:

- **The token on a pipe** (S0-4). The caller hands the token on file
  descriptor 3; `fence.sh` passes fd 3 into the fence and sets
  `CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR=3`; `fence_net.py inside` passes
  fd 3 to the command it starts. `CLAUDE_CODE_OAUTH_TOKEN` no longer
  crosses: the environment is built from nothing, as before, and now
  holds no credential at all. A fence started with the old variable set
  refuses (exit 2), so a caller cannot fall back to it by accident.
- **`--venv DIR`**: the fleet's virtualenv (S0-5), bound read-only at
  `/fleet/moto-diag/.venv`, where `wholetree.sh` and `regression.sh` look.
- **`--mobile DIR`**: the mobile repository, bound read-only at
  `/fleet/moto-diag-mobile`, so `../moto-diag-mobile` resolves from the
  clone (S0-5: four gate tests, two finding tests and the ledger test
  read it).

As built: all three, as planned; the network gate's proxy is started with
`3<&-`, so only the command inside holds the token's pipe. And, after the
operator's "Sandbox counts", five tests skip inside the fence with a reason
naming it, beside `closeout_check.FENCE_EXPECTED_SKIPS` (Deviations).

### 2. The dispatcher's plumbing (`dispatcher.py`, and `fleet_git.py`, new)

- **The token pipe.** `FencedRunner` opens a pipe per call, writes the
  token, closes the write end, and starts `fence.sh` with the read end on
  fd 3 and stdin from `/dev/null`.
- **The model-free run.** `Fleet.check_run(clone, commit, full)`: a fresh
  clone of that commit, `fence.sh --net none` with no token, running
  `wholetree.sh` (fast, or `--full` then `regression.sh`); the result is
  the exit codes and, for a full run, the line `regression.sh` printed,
  parsed by `closeout_check.regression_record`. No model touches it, so
  its record is the one the dispatcher trusts (S0-4).
- **The push gate** (`fleet_git.py`). Before any push, outside the fence:
  the branch is `phase-<N>-*`, never `master`; the push is a fast-forward
  of what GitHub has; every changed path is one the rank may touch
  (`RANK_PATHS`: the Science Officer its step-0 report and prompt file,
  the Captain its plan, the Engineer anything except `.claude/settings.json`,
  `CLAUDE.md`, the closeout guards, `.claude/skills/fleet/` and other
  phases' ROADMAP rows); no added line holds a credential
  (`sk-ant-`, `sk-gw-`, `ghp_`, `github_pat_`, `gho_`);
  `roadmap_check.check_tree(clone)` passes; and the commit passed a
  model-free run. Each refusal names itself; nothing is pushed.
- **The push identity** (`fleet_git.py`). The push names its credential
  on the one command (`git -c credential.helper=` then a helper that
  reads the token from that process's environment): the fleet's account
  from `~/.config/motodiag/fleet-github.env` (mode 600, the account and
  its token); without that file, the operator's login, and only for an
  issue whose body carries the trial marker `<!-- fleet-trial -->`
  (pre-approval (b)); any other issue gets a `needs-hands` comment naming
  the operator's step, and nothing is pushed. `gh` calls that write (a
  comment, a label, a PR) use the same identity (`GH_TOKEN`), so the fleet
  speaks as itself once the account exists.
- **Commit authors.** A commit made for a rank carries `MotoDiag fleet
  (<rank>)` and `fleet@motodiag.invalid` until the account exists, then
  the account's `users.noreply.github.com` address, and a
  `Co-Authored-By:` line naming the model that wrote it.
- **The Fable gate.** `fable_refusal(usage)`: a new Fable stage is
  refused at 70% or more of "Current week (Fable)", or when it cannot be
  read; 388's Opus gate is unchanged. A resumed stage is not gated (388).
- **Closed phases.** Every stage reads the phase's ROADMAP row on the
  mirror's `master` first and does nothing for a row that is not 🚧,
  logging it once per issue (issues #9 and #10, S0-6).
- **Timeouts.** A fenced call keeps 388's 30 minutes; the Engineer's
  session gets 6 hours. The loop is one process: while the Engineer
  builds, no other stage runs (one writer per phase branch, and one
  phase building at a time).

As built, four changes: **the usage** is read by `Fleet.usage` on the
operator's sign-in, outside the fence (F218: the fleet's token cannot read
it; the operator's "Use my sign-in to read"); **the gate lets the Engineer
add ROADMAP rows**, refusing only a change to or removal of another
phase's row; **issues carrying `needs-admiral` or `needs-hands` are left
alone**; and **every stage clone has a local `master`** tracking
`origin/master` (bug fix #3). `RANK_PATHS` shipped as `fleet_git.may_touch`
and `NEVER`.

### 3. The Science Officer (`scout.py`)

On an open issue whose only fleet label is `mission`, titled
`Phase <N>: <title>`, with a 🚧 row for `<N>` on `master`:

1. The branch: the one `phase-<N>-*` head on GitHub, else
   `phase-<N>-<slug>` made from `master` (the slug from the title).
2. The terms: one Haiku call, no tools, returns the nouns and verbs of the
   mission (the issue body and the row) as a list of at most twelve
   search terms (schema-checked).
3. **The census** (257's census shape: a rule applied to everything, no
   model): for each term, `git grep -c -i -F -e <term>` over `src/`,
   `tests/`, `.claude/` and `docs/`, and over the mobile repository's
   `src/`; each count is written beside the exact command that made it.
4. **The candidates** (257's candidates shape): at most five hits per
   term, three lines either side, at most 30,000 characters in all.
5. The report: one Haiku call, no tools, with the mission, the census, the
   candidates, the ROADMAP rows around `<N>` and the newest handoff,
   returns the classification (greenfield, extension or reshape), its
   reason, and prose for "What exists", "What the row promises" (each verb
   with how a user reaches it) and "Risks and stops". The prose may carry
   no count: `plan_check.unshown_counts` must find none, else one
   corrective call, else a stop.
6. The script writes `docs/phases/in_progress/<N>_step0.md` (the census
   table is the script's, so every count shows its query) and saves the
   issue's body verbatim as `docs/prompts/<N>_<slug>.txt` when no prompt
   for `<N>` is there yet.
7. The commit, a model-free whole-tree run, the push gate and the push,
   then `step0:done` is added. `mission` stays for the issue's life (388).

A reshape is written as found; P4 then sends the plan to the Admiral at
the XO, as 387 built.

As built: as planned, with three changes. A branch the issue's body names
and GitHub lacks yet is the one made (two planted proofs and the trial
shared phase 389A). The brief says to write a phase's number only after
the word Phase, and so does the corrective call (bug fix #1: "385 exists"
read to P3 as a count). The slug drops a leading `Phase <N>:`. Ran live on
the trial: twelve terms, the report pushed (`ffe1691`). Its title repeats
the phase, a nit, logged.

### 4. The Captain (`captain.py`)

- **v1.0, on `step0:done`.** A clone of the phase branch; one Fable call
  with 387's read-only tools and a schema of one string, given the brief
  (measured as drafted in S0-3), the ROADMAP row, the prompt file and the
  step-0 report. The script writes the plan, runs `plan_check.check`; on a
  failure, one more call given the failed items; still failing, a stop
  (comment, label unchanged, nothing pushed). The commit `Phase <N> v1.0:
  the plan`, the model-free whole-tree run, the push gate, the push, then
  `plan:needs-review` (removing `step0:done`).
- **A revision, on the XO's back-to-captain.** When the issue carries
  `plan:needs-review` and the XO's newest verdict marker is
  `back-to-captain`, newer than the Captain's last marker: the same call
  given the XO's items; the commit names the round; then
  `plan:needs-review` is removed and added, so the XO is due again (388,
  S0-6). The XO's two-round limit (387) still sends a third to the
  Admiral.
- **The merge recommendation, on `review:clear`.** One Fable call, read-only,
  given the PR's diff summary, v1.1's Results and Deviations, the Red
  Team's clear and the model-free run's line; three lines, schema-checked
  (merge or hold, and why); posted on the PR; then `merge:needs-review`.
- It never touches `src/`: its pushes may change only its plan
  (`RANK_PATHS`).

As built: as planned, except that the recommendation needs no push
identity, since it only comments. Ran live on the trial: v1.0 (`4eee8ab`),
and two revisions on the XO's items (`a28256b`, `f13d170`). The second
revision answered a defect of the fleet's, not the plan's (bug fix #3); the
operator: "don't make the Captain revise for a defect that isn't its own".
The recommendation was dry-run on the trial's plan before going live:
"hold", three lines (`fixtures/dry_runs/recommend_hold.json`).

### 5. The Chief Engineer (`engineer.py`)

- **On `plan:approved`** (and on `build:open` when the Red Team's newest
  findings are newer than the Engineer's last marker: a fix round). It
  sets `build:open` first and comments that it started.
- **The session.** A fresh clone of the phase branch with the commit
  author set; one Opus `claude -p` in the fence with the default tools and
  `--permission-mode bypassPermissions` (the fence and the repository's
  hooks are the boundary: S0-4 measured both guards firing in that mode),
  6 hours at most. The brief: build the approved v1.0 as CLAUDE.md sets
  out, in small commits with `wholetree.sh` before each; the regression of
  record with `regression.sh`; v1.1 with Results and Deviations; dated
  phase-log entries and the `### Bug fix #N` register; the close-out (the
  files to `completed/`, the row ✅, `implementation.md`, the root
  `phase_log.md`, the handoff). It pushes nothing and opens nothing. It
  ends by writing `/fleet/run/engineer.json`: `pr-ready` with a summary,
  or `stop` with the kind and a question in plain English for the
  operator (rule 6). The traps named in the brief: the editable venv,
  `.venv` as a symlink, schema-head literals (F124), tests that read live
  (244H), allowlists pinned in several files, a migration's predecessor's
  rollback.
- **Two watchers, outside the model**, every 30 seconds while it runs:
  the clone's phase log reaching `### Bug fix #3`, and two guard blocks
  with the same guard and reason in the session's transcript
  (`<run>/claude/projects/-fleet-moto-diag/*.jsonl`, a tool result
  marked `is_error` that starts `PreToolUse:Bash hook error`). Either ends
  the session; the stage sets `needs-admiral` with the reason.
- **Before the PR**, every claim checked: `closeout_check.check(clone, N)`
  returns nothing (A1–A8); the model-free full run passes and its passed,
  skipped and failed counts equal the Engineer's regression line; the push
  gate. Then the push, `gh pr create` (title `Phase <N>: <title>`, the
  body naming the mission issue, the regression line and the model-free
  run), and `review:open`. A failed check is `needs-admiral` with the
  failure quoted.
- **A rate limit** leaves the label, records the reset and the session,
  and resumes the same session in the same run directory (388's pause).

As built: as planned. Its harness was dry-run on the trial's branch before
its first live run (`fixtures/dry_runs/engineer_result.json`). Live, it
built the trial's row, ran its own regression, and stopped at a rule-1
condition ("a test it cannot make green"), with a plain-English question.
The dispatcher set `needs-admiral` and pushed nothing. Two causes: the
trial's branch predated 389's fence pins on `master` (my ordering error),
and the suite's network guard let a loopback proxy through (bug fix #4).

### 6. The Red Team (`red_team.py`)

- **On `review:open`.** A fresh clone of the PR's branch. The script
  gathers what the model reads: `closeout_check.check` (A1–A8), the
  output of `scripts/check_f9_patterns.py`'s `run_all_checks`, the plan as
  committed at its plan commit and as it stands, the diff of v1.0 against
  v1.1, and the branch's diff from `master`. One fresh Opus call with
  387's read-only tools (it can open every source it refutes against),
  told to refute every claim in v1.1, the phase log and the handoff, and
  to check v1.1's Deviations against the diff.
- **Its result**, schema-checked: `clear` or `back`, the findings, and a
  `## Refuter pass` table that must pass `refute_check.check` (C1–C7).
  For a repository file the page is the line number
  (`docs/FOLLOWUPS.md p. 3677` means line 3677): C4 asks for a page, and
  a text file has none. A table that fails is a stop.
- **Posted on the PR**, with a marker carrying the round. `back` sets
  `build:open`; a fourth round sets `needs-admiral` (K9's three).
  `clear` sets `review:clear`, and the dispatcher commits the table into
  the branch's phase log (replacing a "No refute pass ran" line), so A8
  holds on what merges; the model-free fast run and the push gate first.

As built: as planned, with two changes. C6 holds only a clear's table: a
back's open rows are what it found (bug fix #2). And it comments with no
push identity; only the push of a cleared table needs one. Ran live on
the planted bug: back, round 1, naming the F213 citations with quotes and
line numbers.

### 7. The labels

| on the issue | the stage | it sets |
|---|---|---|
| `mission` only, row 🚧 | Science Officer | `step0:done` |
| `step0:done` | Captain, v1.0 | `plan:needs-review` |
| `plan:needs-review`, due | XO (387, unchanged) | `plan:approved`, or back |
| `plan:needs-review`, XO's newest verdict back | Captain, revision | `plan:needs-review` (removed and added) |
| `plan:approved` | Engineer | `build:open`, then `review:open` or `needs-admiral` |
| `review:open` | Red Team | `review:clear`, `build:open`, or `needs-admiral` |
| `build:open`, findings newer than the Engineer | Engineer, fix round | `review:open` or `needs-admiral` |
| `review:clear` | Captain, recommendation | `merge:needs-review` |

`NEXT_RANK` says the Admiral merges `merge:needs-review` until the
Quartermaster exists. The due rule is 388's, per stage: the label's last
`labeled` event is newer than that rank's last marker on the issue.

### 8. The machine user (the operator's)

`389_operator_steps.md`, step 1: the account in a browser, a classic
token with only `public_repo`, then one paste block on the desktop that
saves it (mode 600), invites the account with write access under the
operator's login, accepts as the account, and prints ALL GOOD only when
the account can write and is not an administrator.

As built: tightened at the operator's request, "the exact repo permission
it needs and nothing more". The account gets Write and is checked to be
neither a maintainer nor an administrator. If the token cannot accept the
invitation, the block says where to press Accept. The operator does it on
2026-10-25.

### 9. The proofs, in the phase log

1. **The trial, end to end:** issue `Phase 389A: 385's ROADMAP row`
   (planted, the trial marker, the operator's login), row 389A 🚧 on
   `master` first; the Science Officer, the Captain, the XO, the
   Engineer, the Red Team and the Captain's recommendation run by the
   service's dispatcher; the operator merges by hand.
2. **A planted bad v1.0:** a phase branch whose plan has no stops
   section; the XO sends it back (P8) with no model call.
3. **A planted bug:** a copy of the trial's PR whose row names F213 for
   385 instead of F212; the Red Team sends it back naming it.

As built: proofs 2 and 3 shown live (issue #11, and PR #12 with issue #13).
The trial ran live through the Science Officer, the Captain (v1.0 and two
revisions), the XO (two rounds back, then approve) and the Engineer, which
stopped at a rule-1 condition and was handed to the operator. Its last
stages (the Engineer's fresh round, the PR, the Red Team, the
recommendation and the operator's merge) need 389 on `master` and are
recorded after the merge, in the handoff.

## The change log's three newest entries

- **2026-10-22, `fleet` joins the procedure folders.** No check: the
  entry says the row "is text only, and no check reads the table". This
  phase adds four ranks to the folder that row names; the table's one row
  still describes it.
- **2026-10-20, rule 6: plain English to the operator.** No check: the
  entry says "Text only; no check holds it." The operator's step is
  written to it (which computer, which window, one block, ALL GOOD or
  SOMETHING IS OFF), and the Engineer's stop writes its question to it.
- **2026-10-19, live is on the home desktop.** The check it became:
  `tests/test_phase382_live_location.py`. No rank reads live: stage clones
  come from the GitHub mirror, and the fence has no `/home`, so
  `~/.config/motodiag/live.json` is not there (a stage is a machine that
  does not hold live).

## Rule-1 stops anticipated

- **A login or a credential:** the fleet's GitHub account is the
  operator's (pre-approval (a)): `389_operator_steps.md`; the build and
  the trial do not wait for it.
- **A rule's definition, met at Step 0:** a regression inside the fence
  carries 14 failures and 53 skips `EXPECTED_SKIPS` does not pin (S0-5),
  and that list is the operator's (F206, F216). Asked with two plans (the
  fence a machine of record, or the Mac the only one). The Engineer's
  check of the model-free run reads whatever the operator picks; the
  trial's Engineer stage waits for it.
- None expected from a test that cannot be made green (the 14 are the
  stop above) or a live-database change (no rank reads live).

As it went: the login stop as planned, with the operator's step written.
The rule's definition was answered by the operator: "Sandbox counts
(Recommended)". A third stop came up while building, a login put to a new
use (F218: how the gates read the usage), answered with "Use my sign-in to
read (Recommended)". And the rule-5 stop after the third bug fix, at the
operator's instruction, with its shared cause and the fleet rule it became.

## Tests

- `tests/test_phase389_fence_token.py` (Linux, skipped on macOS like
  388's): the token reaches claude on fd 3 and appears in no
  `/proc/*/environ`, command line or readable fd inside the fence (a
  probe with a planted fake token); the old variable makes the fence
  refuse; `--venv` and `--mobile` are read-only.
- `tests/test_phase389_fleet_git.py`: the push gate refuses each
  known-bad case in `fixtures/push_gate/` (master, a non-fast-forward, a
  path outside the rank, a credential in an added line, a ledger drift, an
  untested commit) and passes the good one; the identity: the fleet's
  file, the trial-only fallback, the `needs-hands` refusal.
- `tests/test_phase389_scout.py`, `test_phase389_captain.py`,
  `test_phase389_engineer.py`, `test_phase389_red_team.py`: each rank with
  388's stand-ins for `gh` and the fence and a real git mirror; each
  known-bad model reply in `fixtures/<rank>/` refused (a report with an
  unshown count, a plan that fails P1–P8, a `pr-ready` whose close-out
  fails, a refute table that fails C1–C7), no label moved and nothing
  pushed; the watchers stop a session at a third bug fix and at a second
  identical guard block; a rate limit pauses and resumes.
- `tests/test_phase389_dispatcher.py`: the label table end to end on
  stand-ins, the Fable gate at 69% and 70% and unreadable, closed phases
  skipped, the due rule per stage.
- 388's tests updated where the token moved from the environment to the
  pipe.
- `389_mutate.py`: every mutation red.

As built: the fence's new tests went into `tests/test_phase388_fence_boundary.py`
(`TestTheTokenPipe`, `TestTheVenvAndTheMobileRepository`), under its
already-pinned Mac skip, not a new file: a new file's Mac skip would have
needed a new pin. New files: `test_phase389_fleet_git.py` (53),
`test_phase389_engineer.py` (27), `test_phase389_scout.py` (18),
`test_phase389_red_team.py` (17), `test_phase389_dispatcher.py` (16),
`test_phase389_captain.py` (13), and `test_phase389_fence_regression.py`
(20, for the operator's "Sandbox counts"). 388's dispatcher tests changed
where 389 changed the behaviour (the phase log lists each). 281's guard
test gained one (bug fix #4). Mutations: 46/46 red. `COLLECTED_TEST_FLOOR`
went from 11227 to 11402.

## Non-goals

- The Quartermaster and merging by the fleet: the next phase.
- The master ruleset (F214's other half): it changes who may push to
  `master`, the operator's call; the push gate refuses `master` meanwhile.
- A second vendor for the Red Team; GLM for the Science Officer (K42:
  Haiku until the sourcing backlog is scheduled).
- Any path under the data folder, seed content, splits, eval protocols;
  anything under `src/`; live.
- Closing issues #9 and #10: the operator's.

## Planned items

- [x] the fence: the token pipe, `--venv`, `--mobile`; 388's tests moved
- [x] `fleet_git.py`: the push gate and the identity, with fixtures
- [x] the dispatcher: the pipe, the model-free run, the Fable gate, closed
      phases, the four stages
- [x] `scout.py`, `captain.py`, `engineer.py`, `red_team.py`, each with
      fixtures and tests
- [x] `SKILL.md`, `CHANGELOG.md`, `389_operator_steps.md`
- [x] the mutation run; `COLLECTED_TEST_FLOOR` raised
- [x] the service on the new code; the three proofs (the bad v1.0 and the
      planted bug in full; the trial through the Engineer's stop, its last
      stages after the merge, in the handoff)
- [x] close-out: `wholetree.sh --full`, the regression of record, the
      handoff, row 389 to ✅

## Deviations

- **Two rule-1 answers changed what ships.** The operator, 2026-10-25:
  "Sandbox counts (Recommended)": a regression run inside the fence is of
  record, with `closeout_check.FENCE_EXPECTED_SKIPS` (twelve pairs) accepted
  only on a line carrying `FENCE_MARK`, and five tests skipping inside the
  fence with a reason naming it (204's ffmpeg, 257's Subconscious control
  and stop-alert compile, 209's wheel build, 388's fence module). And "Use
  my sign-in to read (Recommended)": `Fleet.usage` reads `/usage` on the
  operator's sign-in, outside the fence (F218: the fleet's setup-token
  cannot read it; `/usage` inside the fence prints a cost summary and
  `api/oauth/usage` answers 403). v1.0 had both as stops; neither plan was
  built before the answer.
- **F218, found while building**, not at Step 0: the fenced usage read was
  never seen to work (388 measured it on the operator's login). The service
  stayed on 388's code until the answer.
- **Four bug fixes**, all found by the first live runs, and the rule-5
  stop after the third (the operator's instruction): #1 the Science
  Officer's bare phase number, #2 the Red Team's back refused on C6, #3 a
  stage clone with no `master`, #4 the suite's network guard letting a
  loopback proxy through inside the Engineer's session. The shared
  cause (checks of a model's work tested only against stand-ins written
  from the same picture as the code) became the fleet's rule in `SKILL.md`:
  no rank live on a new check before one run against a real artefact. The
  Engineer and the Captain's recommendation were dry-run on the trial's
  branch before their first live run; both outputs are fixtures. #4 is
  the same cause: the Engineer's dry run checked its harness, not the
  suite in its own environment.
- **The trial could not finish before 389 merges**, my ordering error: its
  branch came from `master`, which lacks the fence's pins and skips, so the
  Engineer's run there could not be of record; it stopped correctly. The
  trial resumes after the merge, recorded in the handoff.
- **The push gate lets the Engineer add ROADMAP rows** and refuses only a
  change to, or removal of, another phase's row: v1.0's "other phases'
  ROADMAP rows" would have refused the trial's own deliverable.
- **The Red Team and the Captain's recommendation need no push identity**:
  they comment as 387's and 388's ranks do; only the push of a cleared
  refute table needs one. Without this, the planted-bug proof (no trial
  marker) could not run.
- **The Science Officer makes the branch an issue's body names**, so the two
  planted proofs and the trial could share phase 389A.
- **A stage clone has a local `master`** (bug fix #3), a change to 388's
  `Fleet.clone`.
- **The fence gained no `--wheelhouse`**: 209's packaging tests skip inside
  it ("no network to build a wheel") rather than build offline.
- **`fleet_git.py` is a new file the plan named; `tests/support/fleet_fence.py`
  is one it did not**: the tests' handle on `closeout_check.in_fleet_fence`.
- **The service was restarted four times by this session** (SIGTERM to the
  operator's own process; `Restart=always` brought it back) to load the
  phase branch's code: to 389's at 09:47, then after bug fixes #1–#2 and #3.
  Its clone runs the phase branch until 389 merges.
- **The trial's issue was held twice with `needs-admiral`** by this
  session, each with a comment: for bug fix #3 (the operator's instruction),
  and before the Engineer's first live run (the rule-5 stop's rule).
- **Six guard blocks, all mine**: a `cp` to a variable path; a needless
  `sed -i` (twice, once trailing a command that opened the planted PR); a
  `>>` into `tests/`; a commit and a push in one command (twice, the second
  time the point at which every commit and push became its own command).
  Each refused before anything ran; no guard changed.
- **This desktop's `/tmp` is a 16 GB in-memory filesystem**, filled once by
  this session's scratch runs; one model-free run died of it. The
  dispatcher's own runs are on the real disk.
- **Not done**: CLAUDE.md's procedure-folders row for `fleet` still says
  "read-only ranks, no pushes" (CLAUDE.md is the operator's); the master
  ruleset (F214's other half); the Science Officer's duplicated title (a
  nit, logged).

## Results

Regression of record: 11297 passed, 0 failed, 105 skipped, 0 errors at `2754a01` (30 min 19 s wall, `python -m pytest -n auto --dist load`, exit 0) (run inside the fleet's fence)

That's the dispatcher's own model-free run, in the real fence, with no
model and no token. Its 105 skips are those `FENCE_EXPECTED_SKIPS` and
`EXPECTED_SKIPS` pin. 11297 + 105 = 11402, the floor.

- **The four ranks, live on the service**: the Science Officer wrote and
  pushed the trial's Step 0 (twelve terms, each count with its command).
  The Captain wrote v1.0 and two revisions, each passing P1–P8 before its
  commit. The XO sent it back twice and then approved it. The Engineer
  built the row, ran its own regression, and stopped at a rule-1
  condition with a plain-English question; the dispatcher set
  `needs-admiral` and pushed nothing. The Red Team sent the planted PR back,
  naming the F213 citations with quotes and line numbers (11 turns, 31 s,
  $0.13).
- **A planted bad v1.0, sent back by the XO** on P8 with no model call
  (issue #11). **A planted bug, caught by the Red Team** (PR #12, issue
  #13). **The trial** ran through the Engineer's stop. It resumes after the
  merge, recorded in the handoff.
- **The fence**: the token on a pipe, found by a probe in no environment,
  command line or open file. The fleet's venv is at the fence's paths; the
  mobile repository is bound read-only.
- **The push gate**: G1–G6, each known-bad case refused on its own item.
  **The identity**: the fleet's machine user, or the operator's login for
  a trial only. The operator's step is written (Write, nothing more).
- **The usage**: read on the operator's sign-in outside the fence (F218,
  closed). **The Fable gate** is at 70% of Fable's own week.
- **Measured costs**: a Captain v1.0 about 5–8 min of Fable ($2.36 dry
  run). An XO review 3–5 min ($1.77–2.43). A model-free full check 45 min
  (the whole-tree check, then the 30-minute regression).
- Four bug fixes, the rule-5 stop and its rule. Mutations 46/46 red.
  `COLLECTED_TEST_FLOOR` went from 11227 to 11402. F218 filed and closed;
  F216 answered for the fence; F217 corrected.
