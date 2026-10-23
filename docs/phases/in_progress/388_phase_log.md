# Phase 388 — The fleet's host and its fence — phase log

**Status:** 🚧 In progress
**Branch:** `phase-388-fleet-host` (Opus session on the home desktop, the only writer)

---

### 2026-10-22 — Opened, and Step 0

The prompt is `docs/prompts/388_fleet_host.txt`, saved verbatim. 385 has
a committed prompt (`385_the_push_tokens_own_write.txt`) and no row, and
387 is closed, so the next free number is 388.

- `9c67f93`: row 388 as 🚧 (72 words by `roadmap_words.py`;
  `roadmap_check.py` ok) and the prompt. `wholetree.sh` before it, run on
  its own: exit 0, 1837 passed, 10 skipped.
- `c6cc419`: `388_step0.md`. `wholetree.sh` before it: exit 0.
- `2f570ce`: v1.0, `plan_check 388` PASS (a first run failed P6 on a line
  of mine starting with "…", rewrapped). `wholetree.sh` before it: exit 0.
  Pushed.

Read first: `docs/handoffs/2026-10-22_387_closed.md` (the newest, by
`git log -1 --name-only --format= -- docs/handoffs/`); rows 380–387;
`ROADMAP_AUTHORITY.md` (388 is this repository's); the fleet proposal;
`387_implementation.md` (what it locked: `rank_call.call` and the ranks'
`run=` callable, the eleven labels, the read-only fence by tool list);
`386_implementation.md` and the deploy changelog's setup-token procedure;
F213, F214 and F215 in `docs/FOLLOWUPS.md`.

Step 0's findings, in `388_step0.md`:
- claude 2.1.309, the operator's Max login, no `ANTHROPIC_API_KEY`
  anywhere looked, and **no fleet setup-token on this machine**: the phase's
  one rule-1 stop (a login). Built and proven without it as far as no model
  call is needed.
- `../workspace-docs` is here (pre-approval (b) not needed). The import
  loads from the repository root and **not** from a fresh clone, even with
  the sibling beside it: Claude Code's approval is per project path.
- `claude -p "/usage"` prints the 5-hour and weekly figures in print mode,
  0 turns, no cost: no ceiling file needed.
- A prototype bubblewrap fence with no `/home` refused every planted write
  and read; a proxy outside with a bridge inside let claude reach only
  `api.anthropic.com` (a dummy key, refused by the real API, nothing billed)
  and refused GitHub with 403.

**A guard blocked a command.** A Step 0 probe ran `git commit` and `git
push` inside one `bwrap … sh -c '…'` line, against a throwaway clone in the
scratchpad. The push guard refused it: "This command runs `git commit`
before `git push` … Run `git commit` and `git push` as separate commands."
It judges the command's text, and the text held both. Split into two runs;
the guard is unchanged.

Decisions (each in `388_step0.md` S0-7 with its reason): the model call is
the fenced part and the rank's script is not; the fence seeds the import
approval for its own clone path; the sweep reads the ten state labels, not
`mission`; the digest is kept, not committed or posted; a second Windows
task holds the VM like 382's.

### 2026-10-22 — The build

Each commit after `wholetree.sh` run on its own, exit 0:

- `310af40`: `fence.sh`, `fence_net.py`, `tests/test_phase388_fence_boundary.py`.
- `317e529`: `dispatcher.py`, `fixtures/dispatcher/`, `tests/test_phase388_dispatcher.py`.
- `30e6650`: the unit, `install_fleet_unit.sh`, `motodiag-fleet-boot.xml`,
  `fleet_boot_check.py`, `fixtures/service/cases.json`,
  `tests/test_phase388_service_contract.py`, `SKILL.md`, `CHANGELOG.md`,
  `388_operator_steps.md`. Pushed.

Decisions made while building:
- **The token never rides on a command line.** `bwrap --setenv` would put it
  in `bwrap`'s argv, which any process on the machine can read in
  `/proc/<pid>/cmdline`. `fence.sh` unsets every other variable with shell
  builtins in a subshell and `bwrap` inherits the token; a test holds that
  `--setenv CLAUDE_CODE_OAUTH_TOKEN` never appears.
- **`gh` runs with `GH_REPO`.** A stage clone's `origin` is the mirror's
  path, from which `gh` cannot tell the repository.
- **A refusal is not retried by systemd** (`RestartPreventExitStatus=4`):
  no token, an API key in the environment or a second dispatcher is a
  setup problem, and restarting every 30 seconds would bury it.
- **The restart check is a script**, `ops/desktop/fleet_boot_check.py`,
  not an inline heredoc: 382's relay lost heredocs and `<`. It reads the
  Windows sign-in time with `quser.exe` through interop (measured working:
  "LOGON TIME 10/21/2026 07:48 AM", Ubuntu up at 07:49:12).
- **`dispatcher.py`'s `main` reads `TOKEN_FILE` at call time**, so its
  refusal can be tested; the first draft bound it at definition.
- **A safety check refused one of my commands**: an `rm -rf` of a variable
  path in the scratchpad (Claude Code's built-in check, not the repo's
  guards). Rewritten to use fresh literal directories; nothing removed.

Read against the real GitHub, with no token (no model call): the mirror
cloned; `branch_for("388", "")` → `phase-388-fleet-host`; issue #9's label
events (3 `labeled`); `due(9)` → False (its `plan:needs-review` was
removed); a sweep that posted nothing (its `plan:approved` is under 24
hours old). `dispatcher.py once` with no token file: "REFUSED: no token
file at /home/lilcu/.config/motodiag/anthropic.env", exit 4.
`systemd-analyze verify` on the unit: no output, clean.
`fleet_boot_check.py` now: "SOMETHING IS OFF: the fleet dispatcher is not
running" (not installed yet), the right verdict.

The dispatcher's own code clone, `~/motodiag/fleet/code`, made from GitHub
on `phase-388-fleet-host` (no sudo, mine to make); it moves to `master`
after the merge.

### 2026-10-22 — Mutations

`388_mutate.py`, 41 mutations across the fence, the gate, the dispatcher
and the service, none making a model call or reaching GitHub. First run
**40/41**: D5 ("a usage limit not recognised") survived. The stand-in
exited 1 on every error result, so the second branch (a non-zero exit
naming a limit) caught what the first branch is for, a limit reported in
the result with exit 0. A test of that case was added; rerun **41/41 red**
(`388_mutate.out`). Also added before the run: a test that the fence's own
`/` and `/fleet` are read-only (`touch /`, `touch /fleet`, `mkdir -p
/home/lilcu`), which the plan claims and nothing tested: every planted
target failed as absent before read-only mattered. Its first draft
expected `/home/PLANTED_388` to be read-only; it is absent, so that case
became the `mkdir`.

119 tests in the three new files: 39, 57 and 23.

### 2026-10-22 — The floor, and the stop for the token

The desktop app restarted mid-session while the floor was being measured.
After it: the branch `phase-388-fleet-host`, clean, level with
`origin` at `58bc372`; no `index.lock`; one worktree (the comparison's
temporary worktree had already been removed). Nothing was lost; the
operator asked for the state and said to go on.

**`COLLECTED_TEST_FLOOR` 11093 → 11212**, by a diff of collected ids
against `master` `5909b78` in a temporary worktree: 11093 there, 11212
here, +119 −0, all in the three new files (57, 39, 23). Two first attempts
compared nothing: the project's `addopts` turns `--collect-only -q` into a
tree with no `::` ids, so both sides counted 172 and then 0. With `-o
addopts=` the ids print. `tests/test_phase255B_collected_test_floor.py`: 2
passed.

**Stopped for rule 1: a login.** Everything that needs no model call is
built and proven. What waits for the fleet's token
(`~/.config/motodiag/anthropic.env`, step 1 of `388_operator_steps.md`):
the billing check on Haiku, the `workspace-docs` import loading inside the
fence, one dispatcher cycle on a planted `plan:needs-review` issue, one
sweep comment, then the operator's service install, restart and the
restart test. The row stays 🚧 (R3: a phase with documents in progress is
🚧, never ⏸️; 386's log).

### Bug fix #1 — 2026-10-22 — step 1's check passed a token written five times

**Issue.** The operator ran step 1 and reported, verbatim: "ALL GOOD.
Note: the first attempt wrote the token several times plus a stray escape
character into anthropic.env (480 chars, 5 copies), and step 1's check
passed it anyway because it only checks the line's start. I rewrote the
file; it now has exactly one token, 108 chars, mode 600. Please tighten
step 1's check to require exactly one token and nothing else on the line,
and log this."

**Root cause.** The check in `388_operator_steps.md` was `grep -c
'^CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat'` plus the mode: it judged how the
line started and nothing after. It was copied from 386's procedure in the
deploy changelog, which has the same prefix check. The dispatcher's
`load_token` had the same gap: `startswith("sk-ant-oat")`, so it would have
accepted the operator's first file and sent a 480-character token to the
API. A doubled paste is plausible from the terminal (a bracketed paste
writes `ESC[200~` around what is pasted); not measured here.

**Fix.**
- Step 1's check now passes only a file of one line, matching
  `^CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat[A-Za-z0-9_-]+$`, with `sk-ant-oat`
  occurring once (the character class alone accepts five copies run
  together), mode 600. The step says to run the block again on SOMETHING IS
  OFF.
- `load_token` refuses, exit 4, anything but one token of that shape on
  its line, with the reason "a doubled paste or a stray character fails
  here". Quotes around the value, which it used to strip, are now refused.

**Files.** `388_operator_steps.md`, `.claude/skills/fleet/dispatcher.py`,
`tests/test_phase388_dispatcher.py` (5), `tests/test_phase388_service_contract.py`
(8: the step's own block is extracted from the document and run against
planted files), `388_mutate.py` (D23, S6).

**Verified.**
- The old check on a planted file shaped like the operator's (five copies
  of a 108-character token, then `ESC`): "ALL GOOD (wrongly)". The new
  check on the same file: SOMETHING IS OFF, and on five other bad shapes
  (one escape, two copies, trailing text, two lines, the API-key class) and
  a file others can read.
- The operator's rewritten file, read without printing it (`stat`, `grep
  -c`, `awk` of the value's length): mode 600, 133 bytes, one line, one
  `sk-ant-oat`, no byte outside printable ASCII, a 108-character value; the
  new `load_token` accepts it.
- Mutations: D23 (the full match removed) and S6 (the step back to the
  prefix check) red; the whole set **43/43 red** (`388_mutate.out`).
- `COLLECTED_TEST_FLOOR` 11212 → 11225, +13 −0 against `33d2b24`.

Not changed: 386's procedure in `.claude/skills/deploy/CHANGELOG.md`
keeps its prefix check. It is a dated record of what that phase wrote; the
handoff names it for whoever next uses it.

**Commit.** The commit that carries this entry.
