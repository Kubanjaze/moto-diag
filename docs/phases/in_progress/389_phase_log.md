# Phase 389 — The Captain and the Engineer — phase log

**Status:** 🚧 In progress
**Branch:** `phase-389-captain-engineer` (Opus session on the home desktop, the only writer)

---

### 2026-10-25 — Opened, and the two records before it

The prompt is `docs/prompts/389_captain_engineer.txt`, saved verbatim. It
opened with two requests about 388, done first, on `master` (`c7f61bc`):

- **The restart test.** The operator: "I shut the PC off tonight and
  powered it back on. The dispatcher came back on its own and posted its
  47-hour sweep comment on issue #10 at about 03:5x UTC Oct 25." What the
  desktop recorded did not support it as the restart proof: Windows'
  event 1074 shows a power off from the Start menu at 06:09 EDT on 10-23,
  turned by Fast Startup into a kernel hibernation (Kernel-Power 42;
  `Win32_OperatingSystem.LastBootUpTime` still 2026-10-21 07:48:30);
  WSL's `uptime -s` and the unit's `ActiveEnterTimestamp` are both
  2026-10-22 23:16, `NRestarts=0`; the only sweep since 10-22 is
  21:37:52 EDT on 10-24, 01:37 UTC. So the VM resumed; the boot task and
  the unit never ran. Recorded as measured in 388's handoff, and F217
  corrected to a power-off, as the operator said. The restart test still
  needs a full boot. The operator has not been told yet; the end-of-run
  report says it first.
- **K11.** Recorded with `yeoman.py decide` as **K42**, the operator's
  words verbatim.

389 is the next free number (385 is held by its committed prompt; 388 is
closed). Row 389 went in as 🚧 before Step 0, `68eb86e`.

### 2026-10-25 — Step 0

`389_step0.md`. What it found, in short:
- **Fable is reachable** from `claude -p` on the fleet's token: the
  Captain's dry run was served `claude-fable-5-1`; pre-approval (d) does
  not apply. One Captain call: 30 turns, 312 s, 237K tokens read, 20K
  written; its plan passed `plan_check` first time.
- **The token on a pipe**: with `CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR`
  a Bash command inside the fence finds the token in no environment,
  command line or open file; with 388's environment variable, three
  processes' `/proc/<pid>/environ` held it. The scrub setting instead
  turns on Claude Code's own Bash sandbox, which needs `socat`.
- **The repository's guards fire inside the fence**, under `dontAsk` and
  under `bypassPermissions`.
- **The fleet needs its own venv** at the fence's paths; built.
- **A regression inside the fence is not of record as the rules stand**:
  14 failures and 53 unpinned skips. The second rule-1 stop.

**A model refused a probe.** The first token probe asked a fenced Haiku
to run a bare command that scanned every process for a string starting
`sk-ant-oat`; it refused ("I won't run this one. It scans every process
on the machine"). A fair refusal of an unexplained credential scan. The
probe was rewritten as a script file that writes counts and process
names only, with the prompt saying plainly what it was for and that no
credential is printed; that ran. The probe's first pattern also counted
its own command line (the pattern is in grep's argv); the second used
`sk-ant-oat01-[A-Za-z0-9_-]{20}`, which its own argv cannot match.

**Decided at Step 0** (each with its reason in `389_step0.md` S0-8): the
token on a pipe for every stage; the fleet's venv and the mobile
repository bound read-only; the dispatcher pushes, outside the fence,
through its own gate, and re-runs the whole-tree check and the regression
with no model before a PR; 389A as the trial's number; every stage
refuses a closed phase; the fleet's commit author until the machine user
exists. And one not in `389_step0.md`: **for a repository file, the Red
Team's refute table gives the line number as the page** (`p. 3677` for
line 3677). C4 asks every row for a page, every table so far cited PDF
pages (`grep -l '^## Refuter pass' docs/phases/completed/*_phase_log.md`,
the newest 381's), and a text file has none. The SKILL and the brief say
so; `refute_check.py` is unchanged.

### 2026-10-25 — The build: the fence, the gate, four ranks, the dispatcher

v1.0 was committed and pushed first (`18af1fa`, `plan_check 389`: PASS).
Then, in `.claude/skills/fleet/`:

- **`fence.sh`, `fence_net.py`**: `--token-fd` (the token on fd 3,
  `CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR=3`; the old variable refused),
  `--venv`, `--mobile`. The network gate's proxy gets `3<&-`, so only
  claude holds the pipe.
- **`fleet_git.py`** (new): the push gate G1–G6 and the identity.
- **`rank_call.py`**: a `tools=` parameter and `NO_TOOLS`, for the Science
  Officer's one-turn calls; 387's default is unchanged.
- **`scout.py`, `captain.py`, `engineer.py`, `red_team.py`** (new).
- **`dispatcher.py`**: the token pipe, the model-free run (`check_run`),
  the push in an explicit identity, the Fable gate, closed phases skipped,
  issues with `needs-admiral` or `needs-hands` left alone, the four stages
  and their resumes, the Engineer's watched session.

**One correction to v1.0 while building, recorded for v1.1's Deviations:**
v1.0's push gate refused the Engineer "other phases' ROADMAP rows"
outright, which would refuse the trial itself: its one deliverable is a
new row, 385. The gate refuses a change to, or removal of, another
phase's row (a removed `| N |` line that is not the phase's own), and
lets a new row through (`fixtures/push_gate/cases.json`: `good-engineer`
adds row 385; `G3-engineer-changes-another-row` renames 898's).

**388's tests changed where 389 changed the behaviour**, each on purpose:
the fence's environment test (nothing crosses now), the dispatcher's
environment assertion (`PATH` only, the token on `pass_fds=(3,)`), the
Fable test (gated by its own week since 389), the no-branch test (now on
phase 900, since phase 777 has no 🚧 row and gets no stage at all, a new
test), the once-per-application test (after a back-to-captain the
Captain's revision is next, and with no account and no trial marker it
is `needs-hands`), and the three pause tests (the limit is found by the
call, after the gate read the usage as fine: the stand-in's
`usage_after`).

**Found by the tests, fixed before any commit** (not bug fixes: nothing
had shipped): the Science Officer's list of excerpt locations
(`registry.py:3, tests/…`) read to P3 as a count with no query, so its own
check refused its report; the locations are backticked now. A slug
repeated the phase (`385_phase_385_…`); it drops a leading `Phase <N>:`.
A repository with no `docs/prompts/` made the prompt write fail; the
folder is made. And in the tests, a pipe opened with `preexec_fn` lost its
fd 3, because `subprocess` closes descriptors after `preexec_fn` runs;
`pass_fds=(3,)` keeps it (the Captain's dry run in Step 0 only worked
because its pipe happened to be fd 3).

**Two guard blocks, both mine.** The edit guard refused `cp -r … $T/`
("the edit guard cannot tell where `cp` `$T/` writes"), a scratch copy to
a variable path; rerun with a literal path. And it refused a pointless
`sed -i` on `/dev/null` ("`sed -i` edits a file in place, and is blocked
wherever it points"); the import it was meant to remove was removed with
the Edit tool. No guard changed. (Earlier in the build I also edited
`fence.sh` and `fence_net.py` with a short Python script making exact,
count-checked replacements; the working rules ask for the Edit tool on
source, which every later edit used.)
