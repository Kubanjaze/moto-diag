# Phase 389 — The Captain and the Engineer

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-25

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

- [ ] the fence: the token pipe, `--venv`, `--mobile`; 388's tests moved
- [ ] `fleet_git.py`: the push gate and the identity, with fixtures
- [ ] the dispatcher: the pipe, the model-free run, the Fable gate, closed
      phases, the four stages
- [ ] `scout.py`, `captain.py`, `engineer.py`, `red_team.py`, each with
      fixtures and tests
- [ ] `SKILL.md`, `CHANGELOG.md`, `389_operator_steps.md`
- [ ] the mutation run; `COLLECTED_TEST_FLOOR` raised
- [ ] the service on the new code; the three proofs
- [ ] close-out: `wholetree.sh --full`, the regression of record, the
      handoff, row 389 to ✅
