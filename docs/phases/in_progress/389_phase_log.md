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
