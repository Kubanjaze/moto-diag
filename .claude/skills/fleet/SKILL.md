---
name: fleet
description: The fleet's ranks — the Executive Officer's plan checklist and verdict (plan_check.py, xo.py), the Yeoman's decisions file and daily digest (yeoman.py), the GitHub labels that carry a phase's state (labels.py), and since Phase 389 the ranks that write — the Science Officer's Step 0 (scout.py), the Captain's v1.0 and merge recommendation (captain.py), the Chief Engineer's build to a PR (engineer.py), the Red Team's refute (red_team.py) — with the push gate and identity they push through (fleet_git.py); on the home desktop, the bubblewrap fence every model call runs in (fence.sh) and the dispatcher that polls the labels (dispatcher.py, its systemd unit), with since Phase 390 each stage's journal (journal.py) and the search on start that resumes a stage a restart cut off. Use when reviewing a phase's v1.0, recording an operator decision as a K-id, writing the digest, checking the labels, opening a mission for the fleet, running, checking or changing the fence, the push gate, a rank or the dispatcher, or restarting the fleet's service and checking what it resumed.
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
python3 .claude/skills/fleet/yeoman.py decide --words "…" --check "…" [--kid K42]
python3 .claude/skills/fleet/yeoman.py digest [--date YYYY-MM-DD]
```

- **decide**: one row in `docs/decisions.md`, the next K-id, the words
  verbatim. Refuses an unresolved K-id (defined only by the two triage
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
a stage writes ends ` run=<run>`. `paused` stays in `state.json` until its
resumed stage ends. `prune_runs` keeps every unfinished run.
`recover --dry-run` says what a start would do and writes nothing (no lock,
no mirror update): run it beside the live service before new code goes live.

**Commits** made for a rank carry `MotoDiag fleet (<rank>)`,
`fleet@motodiag.invalid` until the account exists, and a `Co-Authored-By:`
line naming the model.

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
known-bad journals in `fixtures/resume/bad/`, the journal outside the fence).
