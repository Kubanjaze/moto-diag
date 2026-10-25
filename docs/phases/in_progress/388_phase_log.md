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

### 2026-10-22 — The billing check, the first call on the fleet's token

386's procedure (`.claude/skills/deploy/CHANGELOG.md`, "The Haiku billing
check"), run through the fence rather than bare, since that is how every
fleet call will go.

**Before**, the operator, verbatim: "claude.ai Usage session 2%, this week
9% (Fable 15%), usage credits $0. Console billing: $Z (or: I have no
Console/API account)." The Console figure came back as the template's
placeholder; asked which applies, answer pending.

**The call**, at 22:57:32 EDT: `env -i PATH=… CLAUDE_CODE_OAUTH_TOKEN=<read
from the file inside the command, never printed> fence.sh --clone <fresh
clone from GitHub> --run … --workspace-docs … -- claude -p "Reply with the
single word OK." --model claude-haiku-5-5 --tools "" --strict-mcp-config
--output-format json --no-session-persistence`. Exit 0; served
`["claude-haiku-5-5"]` only; `is_error` False; result `OK`; input 2,
cache write 15,496, cache read 0, output 4; $0.0031 at list price (Claude
Code's estimate, not a bill); session `fe57421b-2164-470b-9bad-8b917aab4184`.
The gate's log: 3 lines, all `ALLOW CONNECT api.anthropic.com:443`. The
token's prefix occurs 0 times in the output, the error stream or the gate's
log (`grep -c`).

**After:** waiting for the operator's two readings. Per the procedure, one
short call may not move a whole percent, so an unmoved Usage is not a pass
by itself; a moved Console bill is a stop.

**The operator's answer**, verbatim: "After: the usage-credits switch is
now off (2026-10-22 22:59 ET). Console baseline for the billing check,
from platform.claude.com/cost, month to date as of Oct 23 01:56 UTC: total
cost $0.00, total token cost $0.00, no daily data; the org holds a $220.42
prepaid balance, untouched. Record that as the before; after the
dispatcher's first Haiku stage and again after its first full cycle, I'll
check that this page is still $0.00 and that claude.ai usage moved
instead."

Recorded as the Console's before. On the times: 01:56 UTC is 21:56 EDT,
an hour before the test call (22:57:32 EDT, 02:57 UTC), so the baseline
precedes it too, and the operator's next $0.00 covers the test call and
the dispatcher's stages together. The usage-credits switch went off at
22:59, after the test call; the credits read $0 before it, so none could
have been drawn. Still open: claude.ai Usage after the test call (not yet
reported), and the operator's two later Console readings.

**The operator's after-reading**, verbatim, received while the first
dispatcher cycle ran: "After: the usage-credits switch is now off
(2026-10-22 22:59 ET). Console, platform.claude.com/cost: before, month to
date as of 01:56 UTC Oct 23: $0.00 total cost, no daily data, prepaid
balance $220.42. After the 22:57 EDT test message, as of (time): still
$0.00, balance still $220.42. claude.ai Usage after: session X%, this week
Y%. Record the 01:56 UTC reading as the before. I'll check this page again
after the dispatcher's first Haiku stage and after its first full cycle:
it must stay $0.00, and claude.ai usage should move instead."

Recorded: **before**, 01:56 UTC, $0.00, balance $220.42; **after the test
call**, Console still $0.00, balance still $220.42. Three fields came back
as the template's placeholders and are not filled in here: the time of the
after-reading ("(time)") and claude.ai Usage after ("X%", "Y%"). Asked
for; the Console half of the check holds on what was given, and the
Usage half waits.

**The operator's readings at 23:03**, in two messages. The first,
verbatim: "After-readings at 23:03 ET. claude.ai Usage: session 3%, this
week 10%, Fable 15%. Console, month to date: still $0.00 on every line,
balance still $220.42, data as of Oct 23 01:56 UTC. The usage moved on
claude.ai and not on the Console: the billing check passes. Carry on." I
answered that the Console's "data as of" (01:56 UTC, 21:56 EDT) is before
the test call (02:57 UTC), so its $0.00 does not yet cover it. The second,
verbatim, which stands: "After-readings at 23:03 ET. claude.ai Usage:
session 3% (was 2%), this week 10% (was 9%), Fable 15%. Console, month to
date: still $0.00 on every line, balance still $220.42, but its data is
only as of Oct 23 01:56 UTC, before the 02:57 UTC test call, so the
Console half isn't conclusive yet. Usage moved on claude.ai as expected.
Carry on, and I'll recheck the Console once its "data as of" time is after
02:57 UTC, and again after the first full dispatcher cycle."

So: **the claude.ai half passes** (session 2% → 3%, week 9% → 10%, Fable
15% unchanged, consistent with a Haiku call). **The Console half is open**
until a reading whose "data as of" is after 02:57 UTC shows $0.00. The
"(time)" and "X%, Y%" placeholders of the earlier message are superseded
by these readings.

### 2026-10-22 — The ninth case: the workspace rules inside the fence

Two Haiku calls with `--tools ""`, each in its own fresh clone from GitHub,
asked to quote the first bullet under "Evidence" or answer NOT LOADED (the
2026-09-23 proof's question):

| run | fence | the approval in the fence's `.claude.json` | answer | session |
|---|---|---|---|---|
| 23:01:41 | `fence.sh` | `True` | quoted verbatim: "**Print the count before acting on a search; a truncated result is not a census.** A test subset is a sample, not an inventory. → §[Evidence discipline (searching)]" | `e38112e5-6c12-4145-99fb-d151235a1c33` |
| 23:01:44 | a scratch copy, one line changed (`diff`: `hasClaudeMdExternalIncludesApproved=False`) | `False` | `NOT LOADED` | `773fb9b2-fad2-46d7-9d28-be5bcb669689` |

Both served `claude-haiku-5-5` only, exit 0. **The import resolves inside
the fence, and the seeded approval is what makes it resolve**: the same
fence, the same `workspace-docs` binding, without it, runs with no
workspace rules.

**A guard blocked a command.** The first attempt looped over both runs and
wrote each with `> $d/out.json`. The edit guard refused it: "the edit guard
cannot tell where the redirect `>` `$d/out.json` writes (a variable,
substitution, glob or unknown directory), and blocks what it cannot
resolve. Use a literal path." Rerun as separate commands with literal
paths; the guard is unchanged.

### 2026-10-22 — One dispatcher cycle end to end, on a planted issue

`plan_check 388`: PASS at the branch head. Issue
[#10](https://github.com/Kubanjaze/moto-diag/issues/10), "Phase 388: the
fleet's host and its fence", opened under the operator's login (as 387
opened #9) with `mission` and `plan:needs-review`, its body naming the
branch `phase-388-fleet-host`. Then `/usr/bin/python3
.claude/skills/fleet/dispatcher.py once` from the dispatcher's own clone
(`~/motodiag/fleet/code` at `6417d86`), the way the unit will run it:
23:02:15 to 23:06:29 EDT, exit 0. Its log:

- the mirror updated; the sweep at 24 hours posted nothing;
- `issue 10: the Executive Officer on phase 388`, in the stage clone
  `runs/20261022_230221_xo_388/clone` of the phase branch;
- the verdict **approve**, comment at 03:06:14Z opening `<!-- xo-verdict:
  approve round=0 applied=approve phase=388 -->`; `label set:
  plan:approved on issue 10`. GitHub's events for #10:
  `plan:needs-review` removed and `plan:approved` added at 03:06:16Z;
  labels now `mission`, `plan:approved`;
- the call: `claude-fable-5-1`, session
  `371d328c-761c-4337-a537-6f387a3161cd`, input 130, cache write 62,042,
  cache read 172,928, output 14,328, 27 turns, 231 s, $2.00 at list price;
- then **the digest** for 2026-10-21 in the stage clone
  `runs/20261022_230617_digest/clone`, kept at
  `~/.local/state/motodiag/fleet/digests/2026-10-21.md` (2,420 bytes; its
  summary names 384's close and 31 open findings); `claude-haiku-5-5`,
  session `c17c1c9a-cd52-45fc-9d11-37907787cef3`, input 2, cache write
  19,001, output 1,992, 2 turns, 9 s.
- Both stages' gate logs: 3 lines each, all `ALLOW CONNECT
  api.anthropic.com:443`. Both calls are in `calls.jsonl`.

This was the dispatcher's first Haiku stage and its first full cycle: the
operator's two Console rechecks fall on the same moment.

**The XO's note, and the measurement it asked for.** The verdict carried
one note, "not a defect": the due rule "rests on GitHub recording no new
`labeled` event when `gh issue edit --add-label` names a label the issue
already carries … only the planted-issue proof after the token can show
GitHub behaves this way; the phase log should record that it did." It was
right that the tests could not show it: they use stand-ins. Measured on
#10 with `mission`, which triggers nothing:
- `gh issue edit 10 --add-label mission` at 03:06:53Z, the label already
  on: **no new event**, in both `issues/10/events` and
  `issues/10/timeline`.
- The control, `--remove-label mission` then `--add-label mission`:
  `unlabeled mission 03:07:04Z`, `labeled mission 03:07:06Z`, at once. So
  the empty result was not lag.

So on GitHub, a back-to-captain verdict (which re-adds a present
`plan:needs-review`) makes no event and is not re-reviewed, and the
Captain's re-application (remove, then add) makes one and is.

### 2026-10-22 — One sweep comment

`dispatcher.py once --sweep-hours 1` at 23:07:20 (the log line: "the sweep
at 1.0 hours, not 24.0: a proof run"). One hour rather than 24 so that a
proof runs tonight, and so one run shows both sides: issue #9's
`plan:approved` (applied 2026-10-22T22:33:15Z, 4 h 34 min) and #10's
(about a minute). Result: `issue 9: swept plan:approved, 5 h`; the comment
at 03:07:23Z, "`<!-- fleet-sweep: label=plan:approved
applied=2026-10-22T22:33:15Z -->` **Fleet dispatcher: `plan:approved` has
sat on this issue for 5 hours** (applied 2026-10-22T22:33:15Z). Nothing has
moved it. Next to move it: the Chief Engineer." Nothing on #10; `mission`
on either was not swept. A second run at 23:07:32 posted nothing: #9
holds 1 sweep comment (`gh issue view 9 --json comments`, counted). Neither
run called a model (no issue waiting for review; the day's digest done).

#9 is still open with `plan:approved` though 387 closed; the comment says
so truthfully. Closing it is the operator's.

### Bug fix #2 — 2026-10-22 — step 3 registered the task with a command that refuses its file

**Issue.** Before running step 3, the operator, verbatim: "Before step 3:
in 382, schtasks /Create /XML failed on a UTF-8 task XML with "(1,40):
unable to switch the encoding", and motodiag-fleet-boot.xml also declares
encoding="UTF-8". Please change step 3 to register with
Register-ScheduledTask -TaskPath "\motodiag\" -TaskName "fleet-boot" -Xml
((Get-Content <xml> -Raw) -replace '^<\?xml[^>]*\?>\s*',''), as we did for
wsl-boot, and log it."

**Root cause.** Step 3 copied the registration from
`motodiag-wsl-boot.xml`'s own comment ("Registered with schtasks /Create
/TN "motodiag\wsl-boot" /XML <this file>, elevated"), which is not how
that task was actually registered. 382's records do not mention the
failure or the workaround (`grep -rn "Register-ScheduledTask\|unable to
switch"` over 382's phase documents, its handoff and `ops/`: nothing); the
operator's account is the source. A record that says one thing and a
command that did another is F9's family (assumption against reality).

**Fix.** Step 3 now reads the file from the dispatcher's clone over
`\\wsl.localhost`, strips the `<?xml … ?>` line with the operator's
`-replace`, registers with `Register-ScheduledTask -TaskPath "\motodiag\"
-TaskName "fleet-boot" -Xml …`, starts it with `Start-ScheduledTask`, and
prints ALL GOOD when `Get-ScheduledTask`'s `State` is `Running`. The step
says why, in plain words. `motodiag-fleet-boot.xml`'s comment names the
same command. `motodiag-wsl-boot.xml` is unchanged: its comment is 382's
record and outside this phase; the handoff names it.

**Files.** `388_operator_steps.md`, `ops/desktop/motodiag-fleet-boot.xml`
(comment only), `tests/test_phase388_service_contract.py` (1).

**Verified.**
- The task file is ASCII only (`LC_ALL=C grep -c '[^ -~]'` → 0), so
  Windows PowerShell 5.1's default reading of `Get-Content -Raw` cannot
  change it; it still parses (`xml.etree`).
- Through interop, `powershell.exe` 5.1.26100.9711 on this desktop, on a
  copy of the file under `C:\Users\Public` (removed after): the `-replace`
  leaves text starting `<!-- P`; `[xml]` of it gives URI
  `\motodiag\fleet-boot` and arguments `-d Ubuntu-26.04 --exec /bin/sleep
  infinity`. Nothing was registered: registration is the operator's
  (administrator).
- The new test holds step 3 to `Register-ScheduledTask` with the strip and
  to no `schtasks /Create` in any command line; with `schtasks /Create …
  /XML` planted back into step 3 it went red, then the file was restored.
  Its first draft refused any `/XML` in the document and failed on the
  step's own explanation; it now reads command lines only.
- `COLLECTED_TEST_FLOOR` 11225 → 11226, +1 −0 against `7b6b766`.

**Commit.** The commit that carries this entry.

**Held for close-out, outside this phase:** the operator sent proof 5's
Mac half for 382 ("Please record it when you next touch master"): on the
Mac, 2026-10-22, on `master`, `dryrun`, `apply-live`, `verify-live` and
`backup` each printed "REFUSED: live is on desktop-76s9bqv, not here
(/Users/lilquant/.config/motodiag/live.json). Run this there." and exited
4; a first attempt exited 2 for every mode (zsh passed "dryrun 382" as one
argument and argparse rejected it before anything ran). It goes into
`docs/handoffs/2026-10-19_382_closed.md` (lines 122–123, "Still to come")
in the close-out, verbatim.

Two bug fixes in this build, both in the operator's paste blocks and both
caught by the operator: the next would be the third, the stop to look for
a shared cause. Already visible: each block was written from a record
(386's procedure, 382's comment) and not checked against how it actually
ran.

### 2026-10-22 — The service installed; close-out begins

The operator, verbatim: "Step 2: ALL GOOD. Step 3: ALL GOOD. Confirmed
from outside: motodiag-fleet.service active/running, enabled, User=lilcu,
NRestarts=0; scheduled tasks \motodiag\fleet-boot and \motodiag\wsl-boot
both Running, S4U, Limited; the live API still answers 200, schema 87. Go
ahead with the regression, the handoff and the merge. I'll do Step 4 (the
restart test) tomorrow, and the Console recheck once its data passes 03:07
UTC."

Read here, after the install: `systemctl show motodiag-fleet.service`:
`ActiveState=active`, `SubState=running`, `UnitFileState=enabled`,
`User=lilcu`, `NRestarts=0`, `ActiveEnterTimestamp=Thu 2026-10-22 23:16:27
EDT`; the journal: started 23:16:17, stopped and started again at 23:16:27
(step 2's restart). **The unit active after a service restart: shown.**

`wholetree.sh --full` at `74012fc`: exit 0, 106 test files, 4392 passed,
20 skipped, 6 min 58 s, record written.

### 2026-10-22 — The desktop's regression failed, and the operator's pick

`regression.sh` at `74012fc`, on the desktop:

Regression run FAILED (not of record): 11189 passed, 4 failed, 33 skipped, 0 errors at `74012fc` (9 min 26 s wall, `python -m pytest -n auto --dist load`, exit 1)

The four failures, each run alone: 204's ffmpeg test (no ffmpeg here: a
`TypeError` on `None`); 257's Subconscious profile test ("control missing:
/home/lilcu/.subconscious/profiles/default.env (run `subc login`)");
257's stop-alert test, twice ("osacompile missing: this check needs
macOS"). None is this phase's code; all are this machine's. And 33 skips,
none pinned in `EXPECTED_SKIPS` (257's `sandbox-exec` tests and its tests
needing the manuals library, which is on the Mac). Since 383 every
regression of record ran on the Mac. And on the Mac this phase's fence test
skips, unpinned. So no machine could produce a regression of record for
this phase without a change to `EXPECTED_SKIPS`, which is the operator's
call (F206): a rule-1 stop, put as a question with two plans.

**The operator's pick, verbatim: "Mac runs it (Recommended)"**: pin the
fence test's Mac skip, the Mac runs the regression of record, and a
finding for the desktop.

Done:
- `closeout_check.EXPECTED_SKIPS` gains `("tests/test_phase388_fence_boundary.py",
  "macOS: the fence there is sandbox-exec, proven by
  test_phase257_sandbox_boundary.py")`, with the operator's words beside
  it; `test_phase383_regression_outcome.py`'s equality literal gains the
  same, so the list still changes only with that test.
- The fence test skips through a module-scoped autouse fixture calling
  `pytest.skip("<reason>")` instead of a `skipif` marker: 383's second pin
  test requires that literal in the file. On a simulated Mac (a pytest
  plugin in the scratchpad setting `sys.platform = "darwin"` after
  collection; setting it before Python's own startup broke `sysconfig`):
  39 skipped, 27 skip groups, every one `(file, reason)` in
  `EXPECTED_SKIPS`. On the desktop: 39 passed.
- **F216** filed (`next_f_number.sh`: F215 here, F181 in mobile, next
  F216): the desktop cannot produce a regression of record, the four
  failures and the 33 skips, and what would close it.

**A guard blocked a command.** Updating `FOLLOWUPS.md`'s "highest
assigned" header with `sed -i` was refused by the edit guard ("`sed -i`
edits a file in place, and is blocked wherever it points"). My slip: the
working rules forbid it. Done with the Edit tool; the guard ran before
`sed`, so nothing was written. The guard is unchanged.

### Bug fix #3 — 2026-10-24 — step 1's check passed only with Linux's tools

**Issue.** The operator, from the Mac, at `bcabc89`: "wholetree --full
FAILED, 1 failed, 4411 passed, 10 warnings in 8m 31s (511.5 s wall), so
regression.sh never started … FAILED
tests/test_phase388_service_contract.py::TestTheTokenStepsCheck::test_one_token_passes".
They asked whether it depends on the desktop's state; if so, skip it with
the machine named, and if it is a defect in 388, fix it on the branch.

**Root cause.** A defect in 388, not the desktop's state. The test runs
step 1's own check on a planted file, and the check used
`stat -c %a "$F"`: the Mac's `stat` has no `-c`, so the permission test
fails and a good file gives SOMETHING IS OFF. Reproduced here with a
stand-in `stat` that refuses `-c`: the same one test red, 7 green. A
second difference sat behind it: `grep -o … | wc -l`, whose count the
Mac's `wc` pads with spaces, so `= 1` never matches. The step runs on the
desktop and was right there; its test runs on every machine.

**Fix.** The check counts with `grep -c ''` and tests the mode with
`find "$F" -perm 600`, which mean the same on both machines' tools
(`-perm` with no sign is an exact match on both). No skip: a skip on the
Mac would have needed a new `EXPECTED_SKIPS` pin, the operator's call,
for a test that can run there.

**Files.** `388_operator_steps.md` (step 1's check), `388_mutate.py`
(S6's text, and S7 new), `tests/test_phase388_service_contract.py` (1
new test), `tests/test_phase255B_collected_test_floor.py`.

**Verified.**
- The new test runs the check with stand-ins on `PATH` for the Mac's
  `stat` (refuses `-c`) and `wc` (pads; the test asserts the padding
  first): ALL GOOD on one token at 600, SOMETHING IS OFF at 644. With the
  old check restored (only the steps file stashed): red. With the fix:
  33/33 in the file; with the `-c`-refusing `stat` alone, 9/9 of the
  class.
- The Mac's `wholetree --full` ran `test_phase388_dispatcher.py` and the
  rest of `test_phase388_service_contract.py` (both are members of the
  full set, 106 files): every other test there passed.
- Mutations: 44/44 red (`388_mutate.out`); S7 puts the Linux-only check
  back.
- `COLLECTED_TEST_FLOOR` 11226 → 11227, +1 −0 against `bcabc89`.

**Commit.** The commit that carries this entry.

**The third bug fix, and the shared cause.** All three are in the
operator's paste blocks, and each block's check was proven only where I
wrote it: #1's against a good file and no known-bad one, #2's command
copied from 382's comment and never run, #3's against the desktop's tools
while its test runs on the Mac too. The remedy applied in each: a
known-bad case (#1), the command run on the machine that runs it (#2,
through interop), and the other machine's tools stood in (#3). Steps 2–4
run on the desktop or Windows only, and no test runs their commands on
the Mac (read: `grep -n "subprocess" tests/test_phase388_service_contract.py`,
one call, this class's).

### 2026-10-24 — The host slept for 39 hours

Found while waiting for the Mac: `dispatcher.log` has no line between
23:07 on 10-22 and 21:37 on 10-24. Windows' System log: sleep at 06:09 on
10-23, wake at 21:37 on 10-24. The service never restarted
(`NRestarts=0`, `ActiveEnterTimestamp` 23:16:27 on 10-22) and nothing
hung (every call has a timeout). On waking: the sweep on issue #10 at
47 h and the digest for 10-23; **the digest for 10-22 was skipped**,
since the dispatcher writes only yesterday's. Filed as **F217**
(`next_f_number.sh`: F216 here, F181 in mobile, next F217). The power
settings are the operator's call; a paste block was offered.
