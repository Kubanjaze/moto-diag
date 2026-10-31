---
name: fleet
description: The fleet's ranks — the Executive Officer's plan checklist and verdict (plan_check.py, xo.py), the Yeoman's decisions file and daily digest (yeoman.py), the GitHub labels that carry a phase's state (labels.py), and since Phase 389 the ranks that write — the Science Officer's Step 0 (scout.py), the Captain's v1.0 and merge recommendation (captain.py), the Chief Engineer's build to a PR (engineer.py), the Red Team's refute (red_team.py) — and since Phase 391 the Quartermaster in shadow (quartermaster.py), the last check before a merge, which merges nothing — with the push gate and identity they push through (fleet_git.py); on the home desktop, the bubblewrap fence every model call runs in (fence.sh) and the dispatcher that polls the labels (dispatcher.py, its systemd unit), with since Phase 390 each stage's journal (journal.py) and the search on start that resumes a stage a restart cut off; and since Phase 392 the plan of record, read exactly (plan_order.py: the "Next, in order" list, what bears on a phase, the stops a K-id answers), and the next mission the dispatcher opens from it; and since Phase 393 the code itself checked (the Quartermaster's Q10–Q12, the Red Team's five questions, the weekly page quality_report.py). Use when reviewing a phase's v1.0, recording an operator decision as a K-id, writing the digest, checking the labels, opening a mission for the fleet, running, checking or changing the fence, the push gate, a rank or the dispatcher, restarting the fleet's service and checking what it resumed, or reading or changing the order the fleet follows.
---

# fleet — the ranks, the fence and the dispatcher

The first two ranks (387) read and never write code. Since Phase 389 four
more write, each only through the dispatcher's push gate, and merging stays
the operator's.

## Why this folder exists

The operator was the message bus between sessions: approving plans that
already passed the written rules, answering questions already answered in
the plan of record, carrying state between windows by hand
(`docs/reports/2026-10-22_fleet_proposal.md`, "What the record shows").
This folder holds the first two ranks that take that work, both read-only:
the **Executive Officer** (approves a plan by checklist) and the
**Yeoman** (keeps the decisions file, writes the digest). Neither pushes
code or merges.

**A GitHub label on the mission issue is the state word.** The script sets
it from a parsed result; a model never does.

## The plan checklist — `plan_check.py`

```
python3 .claude/skills/fleet/plan_check.py <phase> [--rev COMMIT] [--no-pin]
python3 .claude/skills/fleet/plan_check.py --self-test
```

Pure checks, no model. Exit 0 pass, 1 fail (each failed item named), 2
cannot read the ROADMAP, `CLAUDE.md` or the plan.

| id | the item |
|---|---|
| P1 | a ROADMAP row, 🚧 (`roadmap_check.rows`, reused) |
| P2 | `<N>_step0.md` exists |
| P3 | every count in the step-0 report shows the query that produced it |
| P4 | `Classification:` greenfield or extension; reshape or none fails |
| P5 | no path under `data/`, the knowledge content path (`wholetree.CONTENT_PATHS`, reused), seed data, a split or an eval protocol named outside the Non-goals |
| P6 | every section filled, no stub line; Goal and Logic present |
| P7 | the three newest `CLAUDE.md` change-log entries cited, each with a backticked path that exists, or "no check" for an entry that says it is text only |
| P8 | a section listing the rule-1 stops, each one of the five kinds, or "none" |
| P9 | a K-id whose `docs/decisions.md` row names the phase, a dated "Changes to the order" entry naming it (by its date), or its "Next, in order" row's K-id (Phase 392) |
| P10 | a fleet-only phase names, on a line saying "unblocks", a Wave 1 phase whose row is not ✅ (K43) |

**P3, the count rule, is strict on purpose.** A count is a number
followed within two words (no preposition, article or verb between) by a
counted noun. It is shown when its paragraph or bullet, or for a table
row its row or the block just before the table, holds a backticked
command or script. Over the 34 step-0 reports written before it, 32 have
at least one count without its query (197 blocks, measured in Phase 387).
Most are real (a live count with only its source named); some are not
(a number in prose arithmetic). A false hit costs a round back to the
Captain, never a wrong approval. Counts written as words ("three nodes")
are not read.

**The pin.** `WRITTEN_BEFORE`: 384 and 386's v1.0 predate P4, P7 and P8
(the operator, 2026-10-22, K41: "Pin them (Recommended)"). Equality-tested.
`BEFORE_THE_RECORD` (Phase 392): 384 and 386 fail P9, 387 fails P9 and
P10, at their v1.0; equality-tested the same way.

## The Executive Officer — `xo.py`

```
python3 .claude/skills/fleet/xo.py review <phase> --issue N
python3 .claude/skills/fleet/xo.py review <phase> --no-label
```

1. `plan_check`; a failure is back-to-captain with no model call.
2. One read-only call on Fable (`claude-fable-5-1`) with `--json-schema`:
   approve; back-to-captain with items; recommend-to-admiral with a reason.
3. The label from the parsed verdict: `plan:approved`, `plan:needs-review`,
   `needs-admiral`. The third back-to-captain becomes `needs-admiral`;
   rounds are counted from the rank's own marker comments on the issue.
4. **A stop leaves the label where it was** and comments why: exit 3 for
   a call with no usage, the wrong model served, no or a malformed
   verdict, a label `gh` refuses.

## The Yeoman — `yeoman.py`

```
python3 .claude/skills/fleet/yeoman.py decide --words "…" --check "…" --covers "no stop" [--kid K42]
python3 .claude/skills/fleet/yeoman.py digest [--date YYYY-MM-DD]
```

- **decide**: one row in `docs/decisions.md`, the next K-id, the words
  verbatim, and the stop it answers (`--covers`: `no stop`, or
  `stop=<kind> subject=<phase>[,<phase>]`; never a rule-1 kind; Phase 392). Refuses an unresolved K-id (defined only by the two triage
  reports and the file itself: K75 is a BMW), a wrong `--kid`, a path
  that does not exist, a newline. No model.
- **digest**: `docs/fleet/digests/<date>.md`, one local day by time window:
  ROADMAP rows changed and in progress, the newest handoff's open and next
  sections, findings open, filed and closed (this repository's
  `FOLLOWUPS.md` only: mobile's headings do not mark closure), and the open
  `needs-admiral` / `needs-hands` issues. A Haiku summary on top, read-only;
  a stop writes no file.

## The read-only fence — `rank_call.py`, `fence_probe.py`

Every model call goes through `rank_call.call`: `--tools Read,Grep,Glob`
(which tools exist), `--allowedTools Read,Grep,Glob`, `--disallowedTools
Bash`, `--permission-mode dontAsk`, `--strict-mcp-config`. Full model ids,
never aliases; the served model is checked; session id and token usage are
recorded per call in `~/.local/state/motodiag/fleet/calls.jsonl` (or
`$FLEET_LEDGER`). Not `--bare`: it reads only an API key, never the
subscription login.

**The brief goes on standard input, never in argv** (Phase 394, K55): the
command is `claude -p --model …` with no prompt argument, and `claude`
reads the brief from stdin (measured on 2.1.312 with 291094 bytes). Linux
refuses any one argument over 131072 bytes; PR #34's Red Team brief was
over it, and the stage could not start. The fence passes stdin through
(`FencedRunner.fenced`'s `input`); the Chief Engineer's brief is written to
`<run>/session.brief` and is its session's stdin (`engineer.session_brief`).
A launch that raises `OSError` is `rank_call.LaunchFailed`, a `Stop`: the
stage says "the model call could not start" once on its issue, the label
stays, and the cycle goes on.

`fence_probe.py` proves the fence on the machine it runs on: a planted
Bash call under the fence makes no file; the control, with Bash allowed,
does. It calls the model, so it is run by hand and its output logged.

## The labels — `labels.py`

The eleven, in the order a phase passes through them: `mission`,
`step0:done`, `plan:needs-review`, `plan:approved`, `build:open`,
`review:open`, `review:clear`, `merge:needs-review`, `needs-admiral`,
`needs-hands`, `merged`. An existing label is reused, never `--force`d.
Made under the operator's login (K40), a stand-in until the fleet's own
identity (F214).

## The fence on Linux — `fence.sh`, `fence_net.py` (Phase 388)

```
.claude/skills/fleet/fence.sh --clone DIR --run DIR --workspace-docs DIR [--net model|none] \
    [--venv DIR] [--mobile DIR] [--token-fd] -- CMD…
```

One stage under bubblewrap, on the home desktop (WSL2). What CMD sees: the
clone at `/fleet/moto-diag` and the run directory at `/fleet/run`, both
writable; `workspace-docs` read-only at `/fleet/workspace-docs`, so the
`../workspace-docs` import resolves; the claude binary; `/usr` and `/etc`
read-only. **No `/home`**: the operator's home, `~/.config`, `~/.ssh` and
every credential are not there to read, which closes F215 by construction
rather than by a list. `/` and `/fleet` are read-only.

- **The environment is built from nothing, and holds no credential**
  (Phase 389). With `--token-fd` the token comes on file descriptor 3 and
  reaches claude through `CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR=3`, read
  once from the pipe: a Bash command inside finds it in no
  `/proc/<pid>/environ`, command line or open file (389 Step 0, S0-4; in
  388's environment variable three processes' `environ` held it). A
  caller that sets `CLAUDE_CODE_OAUTH_TOKEN` is refused.
- **`--venv`**: the fleet's virtualenv (`~/.local/state/motodiag/fleet/venv`),
  read-only at `/fleet/moto-diag/.venv`, built with the project installed
  editable at `/fleet/moto-diag/src`, so a stage tests its own clone's code
  (the repository's `.venv` is uv's Python under `/home`, editable at the
  operator's checkout: the GLM report's trap 1). **`--mobile`**: the mobile
  repository, read-only at `/fleet/moto-diag-mobile`.
- **The repository's hooks fire inside** (measured: the edit guard refused a
  planted `sed -i`, under `dontAsk` and under `bypassPermissions`).
- **The import approval** for `/fleet/moto-diag` is seeded in the fence's
  own `.claude.json`: Claude Code's approval is per project path, and a
  fresh clone without it runs with no workspace rules (388 Step 0, S0-2).
- **The network**: `fence_net.py proxy`, outside, allows `CONNECT
  api.anthropic.com:443` and nothing else (403), logging each request to
  `<run>/net.log`; `fence_net.py inside` bridges `127.0.0.1:18080` in the
  fence's empty network to it; `HTTPS_PROXY` points there. `--net none`: no
  network.
- **Exit 2 before bwrap**: no bwrap, the clone not a work tree or the
  repository `fence.sh` lives in, no run directory, no `working-rules.md`.

The Mac's fence is `sandbox-exec` (`source-transmission/sandbox.sb.tmpl`,
`tests/test_phase257_sandbox_boundary.py`); this one is proven by
`tests/test_phase388_fence_boundary.py`, skipped on macOS.

**A regression inside the fence is not of record as the rules stand** (389
Step 0, S0-5): 14 failures (the desktop's four, F216, and 388's fence tests
run inside a fence) and 53 skips `EXPECTED_SKIPS` does not pin. Which
skips a fenced run may carry is the operator's call (F206).

## The dispatcher — `dispatcher.py` (Phase 388)

```
.claude/skills/fleet/dispatcher.py run [--interval 300]   # the unit's command
.claude/skills/fleet/dispatcher.py once                   # one cycle
.claude/skills/fleet/dispatcher.py usage                  # the parsed /usage lines
.claude/skills/fleet/dispatcher.py recover --dry-run      # what a start would resume (390)
```

Not the 384 door's dispatcher. One process (an exclusive `flock` on
`dispatcher.lock`), on the home desktop, as the operator's user. State in
`~/.local/state/motodiag/fleet/` (`$FLEET_STATE`): its own GitHub mirror,
`runs/`, `state.json`, `digests/`, `dispatcher.log`.

Each cycle: the mirror updated; **the sweep** (one comment per state label,
every label but `mission`, that has sat more than 24 hours, saying who
moves it next; never twice for one application); a paused stage resumed
after its reset with `--resume`; **the Executive Officer** on each open
`plan:needs-review` issue once per application of the label (due when the
label's last `labeled` event is newer than the rank's last comment), in a
stage clone of the phase branch the issue's body names; after 07:00,
**yesterday's digest**, kept in `digests/`, not committed or posted.

- **Every `claude` goes through `fence.sh`**; the ranks' scripts and `gh`
  run outside it (`gh` with `GH_REPO`). It never moves a label itself.
- **A usage limit** pauses: the reset from `/usage`, the session, a comment
  on the issue, no model stage until the reset, then `--resume` in the same
  run directory. No reset readable: one hour.
- **No new Opus stage** at or above 70% of the weekly all-models figure,
  **and no new Fable stage** at or above 70% of Fable's own week (389), or
  with the usage unreadable. A resumed stage is not new.
- **Exit 4, before any cycle**: another dispatcher; no
  `~/.config/motodiag/anthropic.env`; a token that is not `sk-ant-oat…`;
  `ANTHROPIC_API_KEY` in its environment.

**The service**: `ops/desktop/motodiag-fleet.service` (installed by
`install_fleet_unit.sh`, with sudo, by the operator) runs `dispatcher.py
run` from its own clone `~/motodiag/fleet/code`; `ops/desktop/
motodiag-fleet-boot.xml` is 382's boot task under its own name, so the VM is
held up for it. The operator's steps are in `388_operator_steps.md`.

## The ranks that write — Phase 389

The dispatcher's cycle, on each open `Phase <N>: …` issue whose row on
`master` is 🚧 and that carries neither `needs-admiral` nor `needs-hands`
(the operator's: the fleet leaves it alone until the label comes off), runs
the one stage its labels ask for, latest state first:

| on the issue | the stage | it sets |
|---|---|---|
| `mission` only | the Science Officer (`scout.py`, Haiku) | `step0:done` |
| `step0:done` | the Captain, v1.0 (`captain.py`, Fable) | `plan:needs-review` |
| `plan:needs-review`, due | the Executive Officer (`xo.py`, 387) | `plan:approved`, or back |
| `plan:needs-review`, XO's newest verdict back | the Captain, revision | `plan:needs-review`, removed and added |
| `plan:approved` | the Chief Engineer (`engineer.py`, Opus) | `build:open`, then `review:open` |
| `review:open` | the Red Team (`red_team.py`, Opus) | `review:clear`, or `build:open` |
| `build:open`, findings newer | the Chief Engineer, a fix round | `review:open` |
| `review:clear` | the Captain's recommendation | `merge:needs-review` (the operator merges) |

- **The Science Officer**: 257's census shape. The terms from one no-tools
  Haiku call; the counts by `git grep -c` per area (and the mobile
  repository's `src/`), each beside its command, so P3 holds by
  construction; bounded excerpts; the judgement from a second no-tools
  call, whose prose may carry no count. It saves the issue's body as the
  phase's prompt when there is none.
- **The Captain**: read-only Fable; the script writes the one file it may
  change and runs `plan_check`; a failure gets one more call, then a stop.
- **The Chief Engineer**: one Opus session per round in the fence,
  `bypassPermissions` (the fence and the hooks are the boundary). It ends by
  writing `/fleet/run/engineer.json` (`pr-ready` or `stop`). Two watchers
  outside the model end it early: the phase log reaching `### Bug fix #3`,
  and two guard blocks with the same guard and reason in its transcript.
  A `pr-ready` is believed only when the clone is clean, `closeout_check`
  is empty, and **a run no model touched** (`Fleet.check_run`: a fresh
  fenced clone, `wholetree.sh --full`, `regression.sh`, no token) counts
  what the Engineer's line counts.
- **The Red Team**: a fresh read-only Opus call with A1–A8, the F9 lint, the
  plan as approved and as it stands, and the branch's diff. Its `## Refuter
  pass` table must pass `refute_check` (C1–C7). **For a repository file the
  page is the line number** (`docs/FOLLOWUPS.md p. 3677` is line 3677). Three
  rounds, then `needs-admiral` (K9). A cleared table is committed into the
  branch's phase log (A8).

**The push gate** (`fleet_git.gate`), before every push, outside any
session: G1 a `phase-<N>-…` branch, never `master`; G2 a fast-forward; G3
each path one the rank may touch (no rank changes `CLAUDE.md`, the hook
settings, the guards, or `.claude/skills/fleet/`; the Engineer may add
ROADMAP rows but change only its own); G4 no credential in an added line;
G5 `roadmap_check`; G6 a model-free run passed. Whole-tree records written
inside a fence are not trusted: their key is the run's own.

**The model-free run's limit** (Phase 392, F225): `CHECK_TIMEOUT_S` 5400 s
(K51). The run has its own process group (`run_group`); past the limit the
group is killed and the run is a failed check with the limit named, so the
stage stops the usual way, once, and is not started again until the
operator acts. **The service's open-file limit** (F227): `LimitNOFILE=1048576`
in the unit (K51); a fenced worker peaked at 793 at 392's Step 0, against
systemd's default 1024.

**An open wording defect** (Phase 392, F228): the Red Team's brief says to
leave it "open" with no F-number; on a clear, or a back in round 3, the
dispatcher files the one finding they go to (K9) and writes its number in
each row, committed as `red-team-record`, which may add to
`docs/FOLLOWUPS.md` and nothing more.

**The push identity** (`fleet_git.identity`): the fleet's machine user from
`~/.config/motodiag/fleet-github.env` (mode 600), named on the one push
command with the operator's credential helper reset; without it, the
operator's login only for an issue carrying `<!-- fleet-trial -->`; any
other issue gets `needs-hands`. Comments and labels go out in the fleet's
name once the file exists, else the operator's, as in 387 and 388.

**No rank goes live on a new check until it has run once against a real
artefact in the real place** (Phase 389's rule-5 stop). The build's three
bug fixes were each a check of a model's work tested only against
stand-ins written from the same picture as the code: a bare phase number
P3 reads as a count, C6 held on a back's table, a stage clone with no
`master`. All three failed in the first minutes of the first live run. So:
a fenced dry run of the rank on a real branch first, its output kept as a
fixture; every live failure's real artefact kept as a fixture too; and
where a check and a brief could disagree, the brief states the check's
rule in its own words.

## A stage a restart cuts off — `journal.py` (Phase 390, F219)

A restart, a power cut or a crash kills every process in the unit at once,
and nothing runs at the moment of death. So each stage keeps a **journal**,
`runs/<run>/stage.json`, beside `clone/` and `run/`: outside the fence's
`/fleet/run`, so no model can write it. It is written before the clone and
after each step: the stage and its arguments (the pause record's shape),
each model call (its session once known, its output once it ended), each
model-free run's verdict, each commit, push and GitHub write; and `ended`
when the stage is over. A paused stage stays open.

**On every start, before the first cycle** (`run` and `once`), `recover()`:
- names any run whose journal cannot be read, and keeps it;
- leaves the paused run to its reset;
- **resumes** each unfinished journal from its run directory, unless its
  issue is closed, held by the operator, no longer 🚧, or worked on by
  another stage since (then it is ended, with a comment, label unchanged).
  Resumed, the rank's script runs again from the top and the runner
  **replays** it: a finished call returns its saved output (and is not put
  in the cost ledger twice); the cut call goes on with `--resume` and the
  session its transcript names (`run/claude/projects/*/<id>.jsonl`: a killed
  `claude` prints nothing, and `--resume` keeps the id, measured in the
  fence); a call cut before its first answer runs fresh in the same run. A
  call is known by its model, tools and schema, not its prompt: a prompt
  can read what the stage itself already wrote. A finished model-free run
  is read back; an unfinished one runs again on the same commit. Every
  commit, push and GitHub write is a step, and a resumed step asks GitHub
  first (is the branch at this commit, is this marker there, is the label
  on);
- then, on each issue the cycle would work, a **`started` marker** that is
  the issue's last rank comment, with no unfinished journal behind it and
  **no stage due** (F219's stall), gets a stop comment saying which label
  to apply again. When a stage is due (the operator re-applied a label),
  nothing is said: the cycle runs it.

**A model-free run lost to load (F220).** When the Engineer's work fails
only its model-free run (with the Engineer's own regression line in its
place, every other check passes), the run folder is **held** (`held.json`:
issue, phase, round, commit) and the stop says so. The operator taking
`needs-admiral` off then runs it again on the held commit (`stage_recheck`,
journaled like any stage), and goes on as a `pr-ready` does: the push, the
PR, `review:open`, the Red Team. `prune_runs` never removes a held run.
Other stops are not held: taking the label off them changes nothing, as
before.

One log line per stage. Every rank posts `<!-- fleet-started: rank=<rank>
run=<run> -->` first (its own prefix: no due rule reads it), and every marker
a stage writes ends ` run=<run>`. Once per stage run (Phase 394): a stage the
cycle runs again after its run *failed*, with that run's `started` still
the issue's last rank comment, says nothing new (`failed_start`); the log
says whose comment stands. `paused` stays in `state.json` until its
resumed stage ends. `prune_runs` keeps every unfinished run.
`recover --dry-run` says what a start would do and writes nothing (no lock,
no mirror update): run it beside the live service before new code goes live.

## The plan of record — `plan_order.py` (Phase 392)

```
python3 .claude/skills/fleet/plan_order.py check | next | bearing <phase>
.claude/skills/fleet/dispatcher.py next --dry-run      # what the next cycle would do
```

The fleet was built to answer what the plan of record already answers
(the fleet proposal); until 392 no rank read it. Now:

- **The order** is the "Next, in order" table at the top of
  `docs/reports/2026-10-12_plan_of_record.md`, read exactly (the operator,
  K48: "it changes only by a dated entry with a K-id, written on my
  word"). A row: number, phase, kind (`shop`, `fleet`), built by
  (`fleet`, `builder`), what it needs from the operator (`nothing`, or
  `an outside account`, `an outside person`, `a credential`, `a fork`,
  `a live change`, `a rule change`, a colon and what), and its entry with a
  K-id. Its "As of <date>, <K-id>." names a dated change that cites it.
- **Every rank that plans or judges** gets `brief_block` (the entry, each
  dated change and each K-id row naming the phase, verbatim) and ends what
  it writes with `cite_line`, by script. P9 and P10 hold the v1.0.
- **The next mission** (`stage_next`, each cycle, journaled): the first
  entry whose row is not ✅. A builder's is waited for. Otherwise its
  issue, in the fleet's name, `mission`, naming the work branch; when the
  plan says the phase needs the operator, one plain-English question
  quoting the entry, with `needs-hands` (an account, a person, a
  credential) or `needs-admiral` (a fork, a live change, a rule change),
  and nothing more until the operator takes the label off; then branch
  `phase-<N>-row` from master with the row's status alone set to 🚧, the
  push gate's rank `row` (G3: that one line, its status only), and a pull
  request the operator merges by hand (K49). The merge makes the row 🚧,
  and the cycle's rule starts the Science Officer. Without the fleet's
  account nothing is opened; a list that does not read exactly starts
  nothing.
- **A stop the record answers** (K50): only the Engineer's `third-bug-fix`
  and `guard-blocked-twice`, and only when one K-id's Covers names that
  kind and the phase. Its words go on the issue verbatim
  (`<!-- fleet-answered: … -->`) and into the Engineer's next brief, to
  apply literally; the same K-id and stop again, and every rule-1 stop,
  goes to the operator.

**Whose words count** (F223, Phase 392): the repository is public, so a
rank reads a comment as a marker only when the fleet's account wrote it,
or the operator on an issue carrying `<!-- fleet-trial -->`
(`fleet_git.trusted_authors`); the dispatcher works only issues the fleet
or the operator opened. Every due rule, round count, marker search and
model brief reads through `Fleet.comments`.

## Free space, phase to phase (Phase 390, F221)

The operator, 2026-10-25: "it's just something that needs to be done
frequently to free up the claimed space, now it just needs to be written
into the method itself. as a part of the overall process phase to phase".

- **The one-time switch is the operator's:** the disk image is made sparse
  (`wsl --manage Ubuntu-26.04 --set-sparse true`), and
  `ops/desktop/install_fstrim_sudoers.sh` gives lilcu one command with no
  password, `fstrim -v /`. A model cannot use it: bubblewrap sets
  `no_new_privs`, so sudo fails inside the fence.
- **The dispatcher reclaims** (`Fleet.reclaim`):
  - on a timer, every `RECLAIM_HOURS`;
  - at each merge, when a row that was 🚧 on master is ✅;
  - at each close-out, after the Engineer's model-free run passes. Its line
    goes in the PR, for the handoff.
  Each reclaim logs `reclaim (<why>): C: a -> b GB free; Ubuntu c -> d GB
  free; fstrim: <its line>`.
- **The floor** (`SPACE_FLOOR_GB`, the operator's numbers): no new model
  stage and no model-free run below it on either disk, or when a disk
  cannot be read. Below a floor it reclaims first. If it is still below, it
  holds the stage: the label stays, the comment `<!-- fleet-space:` says
  why, and `needs-hands` is added. That comment is read by no due rule, so
  taking `needs-hands` off lets the held stage run. An Engineer held before
  its model-free run keeps its run (`held.json`, `why: space`), and that
  run goes again on the same commit.
- **What replaced the shrink** (Phase 392, F226; the operator's K45: "go
  with your pick, delete each run's temp files"). The disk image has not
  been sparse since 2026-10-26, so `fstrim` frees blocks inside Ubuntu and
  gives Windows nothing; the image grows to the fleet's peak and keeps that
  size. So the peak is kept down instead: when a stage ends, its `run/tmp`
  (pytest's folders, about 9 GB a full run) is deleted (`clean_tmp`), but
  the `motodiag_worker_loss_*` folders rule 6 reads after a lost worker; a
  check run's, once it has written its result; a held run's, when it is
  released; `prune_runs` cleans any it keeps that have ended. A held, a
  paused and an unfinished run keep theirs until they end. The reclaim
  line says "(nothing came back to Windows …)" when C: did not move.
- **By hand:** `dispatcher.py reclaim` prints the line a handoff records.
  It runs beside the service and writes no state.
- **Only `main` sets the disks up.** A `Fleet` built without `disks`
  reads none and trims nothing: that is every test's, and the default.

## The Quartermaster, in shadow — `quartermaster.py` (Phase 391)

The last check before a merge, step 8 of the fleet proposal. On
`merge:needs-review` (after the Captain's recommendation) the dispatcher
runs `stage_quartermaster`: once per application of the label, and only
for one applied after `state.json`'s `quartermaster_since` (set by the
first cycle that has the stage; apply the label again to have an older
issue judged). **In shadow it merges nothing and moves no label**: the
operator merges, and the digest's "The Quartermaster (shadow)" section sets
each verdict beside what became of its PR. Promotion is the operator's
decision, recorded in both CLAUDE.md files with the date.

| id | the check |
|---|---|
| Q1 | scope: Step 0 says extension or greenfield; the diff touches no `migrations.py`, no content path (`wholetree.CONTENT_PATHS`), nothing under `data/`, no `_dryrun_diff.md`. A failure is the verdict: no run, no model call |
| Q2 | the Captain's newest recommendation on the issue is merge |
| Q3 | the Red Team's newest verdict is clear, after the Engineer's newest `pr-ready` |
| Q4 | `wholetree.sh --full` and `regression.sh` on the head, in the fence with no model, pass and count what the phase log's regression of record counts |
| Q5 | `verify_phase.sh <phase> <regression hash> <head>`, in the fence with no model, read section by section (V1–V14; V1, V7, V8, V9 not read before a merge, each with its reason); its exit code is never read |
| Q6 | the phase's commit claims (v1.0's commit in v1.1's header, each `**Commit.**` and `Commit:` line, the regression's commit) are in the head's history |
| Q7 | v1.1: P6's stub rule, a Results and a Deviations section, no unticked box |
| Q8 | `docs/handoffs/<date>_<phase>_closed.md`, dated no earlier than the close, with "What is open" and "What is next"; `roadmap_check` (R1–R8) on the branch |
| Q9 | the clone is clean and `git merge-tree --write-tree` onto master has no conflict |

Then one fresh read-only Opus call (`rank_call.FENCE`), never the builder's
session, reads the results and judges what no script can: check 4's hits
(a stub, or prose) and the v1.0 → v1.1 diff (**a section left unchanged is
not a stub**: every phase from 384 to 390 left some, measured at 391's Step
0). **The script composes the verdict**: a scripted failure refuses
whatever the model says; the model may add a refusal naming a listed id;
an answer naming any other check, a refusal naming none, or a merge naming
failures, is a stop, label unchanged. The verdict goes on the PR, on the
issue (`<!-- fleet-quartermaster: verdict=<v> failed=<ids> run=… -->`) and
in `quartermaster.jsonl` in the state directory.

**A trap measured at Step 0:** with no virtualenv bound, `verify_phase.sh`
falls back to `python3`, and check 10 prints "No module named pytest" and
no summary line. V10 needs a pytest summary with no failure.

**Commits** made for a rank carry `MotoDiag fleet (<rank>)`,
`fleet@motodiag.invalid` until the account exists, and a `Co-Authored-By:`
line naming the model.

## The code itself is checked (Phase 393, K54)

The operator's numbers (K54): 85% changed-line coverage, McCabe 20, 100 KB
per file, and the ratchet. `scripts/code_quality.py` is the one measure.

**The Quartermaster's Q10–Q12**, scripted, model-free, in the fence. The
dispatcher runs `quartermaster.code_command(<merge-base>)` as a fenced
check (no model, no network): `code_quality.py pr`, the **base's** copy of
the script when the base has one, and the base's `pyproject.toml` for both
trees, so a pull request is not checked by rules or a judge it brought.
The base's `src/` is unpacked beside the head with `git archive`. Q11 reads
the full run's coverage JSON (`regression.sh` writes it under the fence's
`HOME`, the check run's own folder), copied into the stage's folder as
`head.coverage.json`.

| id | the check | refuses with |
|---|---|---|
| Q10 | no `src/` file the PR touches has more ruff findings or mypy errors on the head than on master | the file, the tool, the head's count and master's |
| Q11 | the lines the PR adds or changes in `src/` that coverage can run are at least 85% covered by the full run on the head; a changed file the JSON does not hold counts as missed; no coverage data refuses | the percent, the lines, the worst files |
| Q12 | no new or changed function over McCabe 20 (a changed line inside its span); no `src/` file grows past 100,000 bytes, and none already over it grows | the file and line, the function and its number; or the file's bytes on the head and on master |

Known-bad and good fixtures: `fixtures/code_checks/` (its README), each
committed into a throwaway repository by `tests/test_phase393_code_checks.py`.

**The Red Team's five questions** (`red_team.QUESTIONS`). The brief asks
each of the diff, answered in `code_checklist` as `yes`, `no` or
`not-applicable`, with a file and line. Each is worded so that "no" is the
defect (Deviations, 393):
1. every new public function is reached from the CLI or the API, or is on
   the integration-gap allowlist with its reason;
2. no new private money, time or constant helper where one module should own it;
3. every new handler names the error it expects;
4. the new tests check behaviour, not only that some text exists;
5. on `auth/`, `payments/`, `billing/`, `api/uploads.py` or
   `memory/erase.py`: nothing newly reachable without the right role or tier.

A "no" with a file and line is a factual defect (K9): `review` adds it as
a `code` finding and the round is a **back**, whatever the model's verdict.
`red_team.code_scan` answers 2 and 3 by script over the **added** lines
(a broad handler whose body only passes; a new `_money`/`_now`-style
name); a scripted no stands whatever the model says. A checklist missing a
question, answering one twice, or a "no" with no file and line, is a stop.
Known-bad: a planted `except Exception: pass` in `payments/`, answered
clear by the stand-in model, comes back a back.

**The weekly page, "Code health, weekly"** (`quality_report.py`).
`measure` gives the seven counts of a tree as JSON, model-free; coverage is
the newest "Line coverage of record" line a phase log on that tree carries
(a full run is forty minutes; the page names its commit). `page` writes
each number, last week's and an arrow, and on the first line the counts
that went the wrong way two weeks running. `--print` measures where it is
run and prints, posting nothing.

The dispatcher's `stage_quality`, journaled: from Monday 08:00 local
(`QUALITY_HOUR`), once a week, and only for a Monday after `quality_since`
(set by the first cycle, as `quartermaster_since` is: the first page is the
first Monday after the stage came up). It measures master in the fence,
keeps the page in `state/quality/<monday>.md` and one record in
`quality.jsonl`, and posts the page as a comment on the one open issue
titled "Code health, weekly" opened by the fleet's account, opening and
pinning it the first time. **Without the fleet's account nothing is opened
or posted**; the record is kept. A failed measure is a stop, tried again
after an hour. The next digest gains one line naming the page (`yeoman.facts`'s
"Code health, weekly").

**Off this PC.** `.github/workflows/quality.yml`, on every pull request:
the lint and type ratchet and `roadmap_check.py`; no secret, read-only.

## Through the fleet: the database step (Phase 395, K58)

F232: the fence never sees live, so a phase with a migration had no path.
Now it has one, and the fence still never sees live, a backup or a
credential.

1. **The plan names it.** A migration is in scope only under a section
   `## The database step` (what the change does to live, what it adds, and
   that it changes or deletes no existing live row). The Captain writes it;
   the XO sends a migration without it back. A migration that changes or
   deletes existing live rows is still a rule-1 stop.
2. **The Engineer stops at K18's point.** It writes the migration, the
   deploy skill's scope file and tests on fresh databases, runs the
   regression of record, and ends with `{"outcome": "deploy", …,
   "live_change": "<one sentence>"}`, never closing out.
   `engineer.verify_deploy` believes it only as a `pr-ready` is believed:
   the clone clean, the plan naming the step, a migration and its scope
   file committed, no deploy or close-out file yet, master's deploy and
   close-out tools, and the model-free run counting what its line counts.
3. **The dispatcher hands it over** (`engineer_deploy`): the push through
   the gate, `held.json` with `why: deploy`, one comment (`fleet-database-step`)
   with the change in a sentence and one paste block for the home desktop's
   Ubuntu terminal (`deploy_block`), and `needs-hands`.
4. **The operator's block** runs master's `.claude/skills/deploy/through_fleet.py`
   with the fleet's venv: the dry run on a copy, the change in plain words,
   nothing applied until the operator types yes, the apply, `verify-live`;
   then it takes `needs-hands` off and prints ALL GOOD, or SOMETHING IS OFF.
   The deploy skill's own "Through the fleet" says what it refuses.
5. **The resume** (`held_for`, `stage_deployed`): the step's commits fetched
   from `~/motodiag/deploy/<phase>` into the held clone (only the phase's
   dry-run diff, answer and live diff may change); `verify-live` outside the
   fence, and anything but exit 0 goes to the operator with no Engineer; the
   Engineer's close-out round (`engineer.CLOSEOUT`) in the same clone;
   `engineer_finish` with `verify_after_apply`: no code path changed after
   the live diff's commit, and the operator's answer quoted in the phase log.
   The close-out stopping and `needs-admiral` coming off runs it again from
   the same hold. Resumable (`STAGE_RANK["deployed"]`, its kill point).
6. **After the apply** the migration is the operator's: any later change to
   `src/motodiag/core/migrations.py` refuses a `pr-ready`
   (`engineer.migration_changes`), and the fix round's brief says so.
7. **Q1** passes a migration or a dry-run diff only with the three files
   committed, the live diff clean and equal to the approved diff, and
   `verify-live`, run by the dispatcher outside the fence, exiting 0 (the
   stage passes `live_check`). In the fence, with none, it refuses.

The Red Team still reviews after the close-out (the order of record).
Proven once on the desktop against a copy of live:
`fixtures/deploy/trial/trial_output.txt`; the known-bad cases are in
`fixtures/deploy/known_bad/`.

## Four slips from 348 and 385 (Phase 396, K61)

Each was measured on a real phase; its artefact is in `fixtures/slips396/`.

1. **A command reaches the fence as its argv.** `check_run` builds the
   script with `shlex.join`; a plain join broke the Quartermaster's
   `sh -c` code check into a bash syntax error on 348 and 385, so Q10 and
   Q12 never ran. When a run gives no result, `quartermaster.no_result_why`
   says how it ended and the line that names the error (a time limit
   first), never a tail of the output. Proven in the real fence on both
   heads (`a_real_fence_348.txt`, `a_real_fence_385.txt`, by
   `396_real_fence.py`).
2. **The close-out says nothing about a refute pass.** A fleet phase goes
   to the Red Team after its close-out, and the dispatcher's committed
   `## Refuter pass` table is the record (A8). The Engineer's brief (rule 7)
   says so; `closeout_check.refute_contradictions`, inside A8, refuses a
   "no refute pass" claim in v1.1, the log outside the table or the handoff
   of a phase whose log records the Red Team.
3. **The next mission reads master as it is.** `cycle()` refreshes the
   mirror just before `next_due`: on 2026-10-31 385 merged during a
   53-minute stage and the stale row opened duplicate #44.
4. **The plan of record is the plan as approved.** `red_team.plan_commit`
   takes the time `plan:approved` was last applied
   (`Fleet.plan_approved_at`) and picks the newest plan commit at or before
   it, for the Red Team's brief and the Quartermaster's v1.0-to-v1.1 diff.
   Without one, the brief says the plan is its first commit, never "as
   approved".

## What is held by a test

`tests/test_phase387_fleet_contract.py` (the checklist, every known-bad
case on its own item, the pin's equality, 384/386/387 at their v1.0, the
reuse, the labels), `tests/test_phase387_xo.py`, `tests/test_phase387_yeoman.py`;
`tests/test_phase388_fence_boundary.py` (the planted attempts and their
controls), `tests/test_phase388_dispatcher.py`,
`tests/test_phase388_service_contract.py` (the unit's known-bad cases in
`fixtures/service/cases.json`); `tests/test_phase389_fleet_git.py` (every
known-bad push in `fixtures/push_gate/cases.json` on its own G-id, the
identity), `tests/test_phase389_scout.py`, `test_phase389_captain.py`,
`test_phase389_engineer.py`, `test_phase389_red_team.py`,
`test_phase389_dispatcher.py` (the label table end to end on stand-ins);
`tests/test_phase390_resume.py` (every kill point in `fixtures/resume/
kill_points.json`), `test_phase390_search.py` (#14's real history in
`fixtures/resume/`), `test_phase390_kill.py` (a real process SIGKILLed and
restarted), `test_phase390_resume_contract.py` (the kill-point list, the
known-bad journals in `fixtures/resume/bad/`, the journal outside the fence),
`test_phase390_space.py` (a planted low reading holds each kind of stage;
the reclaim on the timer, at a merge and at a close-out; the service's
wiring; the one sudoers line); `tests/test_phase391_quartermaster.py` (each
check on its own known-bad case, against 390's real close-out as the good
tree), `test_phase391_dispatcher.py` (the stage, its kill points, the
digest's section), `test_phase391_contract.py`; Phase 392's
`tests/test_phase392_plan_order.py` (the list, the Covers column, each
refusal on its own copy), `test_phase392_ranks_cite.py`,
`test_phase392_next_mission.py` (the issue, the ask, the row PR, its gate,
its kill point), `test_phase392_answers.py`, `test_phase392_authors.py`
(F223's third login), `test_phase392_tmp.py` (F226), `test_phase392_check_limit.py`
(F225), `test_phase392_open_files.py` (F227), `test_phase392_red_team_c7.py`
(F228, #14's round 3); Phase 393's `tests/test_phase393_code_checks.py`
(Q10–Q12 on `fixtures/code_checks/`, the stage's fenced run),
`test_phase393_red_team_code.py` (the five questions, the planted swallow),
`test_phase393_quality_report.py` (the page, the weekly stage, its kill
point), `test_phase393_quality_ratchet.py` (the counts against their pins)
and `test_phase393_actions.py` (the workflow's shape); Phase 395's
`tests/test_phase395_through_fleet.py` (the operator's block on a real
mirror, its refusals, a real terminal), `test_phase395_engineer_deploy.py`
(the `deploy` outcome and the round after the apply, on
`fixtures/deploy/known_bad/`), `test_phase395_dispatcher_deploy.py` (the
hand-over, the resume, its kill point, the planners) and
`test_phase395_q1.py`.
