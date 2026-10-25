# Phase 388 — The fleet's host and its fence

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-24 (v1.0 2026-10-22, `2f570ce`)

v1.1 updates every section to what shipped, ticks the planned items, and
adds Deviations and Results.

---

## Goal

Steps 4 and 5 of `docs/reports/2026-10-22_fleet_proposal.md`, built on the
home desktop, which is the fleet's host from this phase on. Three things
ship, all read-only toward the repository:

1. **`fence.sh`**: one stage in a fresh clone under bubblewrap. The clone and
   its run directory are writable; everything else is read-only or not
   mounted; the operator's home, with `~/.config`, `~/.ssh` and every
   credential in it, is not in the fence's view; the network reaches the
   model API and nothing else.
2. **`dispatcher.py`**: one process that polls the labels every few minutes,
   runs the Executive Officer on `plan:needs-review` and the Yeoman's daily
   digest, sweeps any state label older than 24 hours, stops on a rate limit
   and resumes after the reset, and launches no Opus stage above 70% of the
   weekly cap.
3. **The service**: a systemd unit for the dispatcher shaped like
   `motodiag-api.service`, and a Windows startup task beside
   `motodiag-wsl-boot.xml`. Both installs, and the reboot proof, are the
   operator's paste blocks under pre-approval (a).

All three shipped. The fence's boundary is 39 tests on Linux; one real
dispatcher cycle ran on a planted issue; the service is installed and
active. The reboot proof is the operator's, still to come.

The prompt is `docs/prompts/388_fleet_host.txt`. Step 0 is `388_step0.md`
(classification: extension). The XO ran on the Mac in 387, as that prompt
said; from this phase it runs here (it did: 388's own plan, on issue #10).

## Logic

### 1. `fence.sh` and `fence_net.py`

```
fence.sh --clone DIR --run DIR --workspace-docs DIR [--net model|none] -- CMD [ARG…]
```

It runs `CMD` under `bwrap` and exits with `CMD`'s code. It refuses, exit 2
and before `bwrap` starts: a missing `bwrap`; a clone that is not a git
work tree; a clone that is the repository `fence.sh` itself lives in (rule
5: the fence never runs in a checkout someone works in); a run directory
that does not exist; a `workspace-docs` that does not hold
`claude/working-rules.md` (a fence without it runs with no workspace rules,
Step 0 S0-2, so it does not run at all).

**The layout** (measured in Step 0 S0-5):
- `--unshare-all --die-with-parent --new-session`;
- `/usr` and `/etc` read-only, the four root symlinks, a private `/proc`,
  `/dev` and `/tmp`;
- no `/home`: the operator's home is absent, not masked by a list;
- `/fleet/moto-diag` the clone, writable; `/fleet/run` the run directory,
  writable; `/fleet/workspace-docs` read-only, so the import's
  `../workspace-docs` resolves; the claude binary read-only at
  `/fleet/bin/claude`, resolved with `readlink -f` each run (the installer
  moves the symlink on update); `fence_net.py` read-only at `/fleet/lib/`;
- `--remount-ro /fleet` and `--remount-ro /`.

**The environment** is built from nothing: `HOME=/fleet/run/home`,
`TMPDIR=/fleet/run/tmp`, `CLAUDE_CONFIG_DIR=/fleet/run/claude`,
`PATH=/fleet/bin:/usr/bin:/bin`, `TERM=dumb`, `LANG=C.UTF-8`,
`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, and `CLAUDE_CODE_OAUTH_TOKEN`
only when the caller set it. Nothing else of the caller's environment
crosses. As built, the caller's environment is emptied in a subshell with
bash builtins (`compgen -e`, `unset`) before `exec bwrap`, and the token is
inherited, never passed with `--setenv`: an argument to `bwrap` is readable
by any process through `/proc/<pid>/cmdline`.

**The import approval.** Before the run, `fence.sh` makes sure
`/fleet/run/claude/.claude.json` holds `hasClaudeMdExternalIncludesApproved`
and `hasClaudeMdExternalIncludesWarningShown` for `/fleet/moto-diag`,
merged into what is there (a resumed stage keeps its file). This is the
operator's 2026-09-23 approval of this import, reproduced for the fleet's
clone path (Step 0 S0-7); without it the import does not load (S0-2).

**The network** (`--net model`, the default): `fence_net.py proxy` runs
outside the fence on a unix socket in a short directory under `/tmp` (the
108-byte limit, S0-5), allows `CONNECT api.anthropic.com:443` only, answers
403 to anything else, and logs one line per request, `ALLOW` or `DENY`, to
`<run>/net.log`. Inside, `fence_net.py inside` binds `127.0.0.1:18080`
first, forwards each connection to the socket, then runs `CMD`;
`HTTPS_PROXY` and `https_proxy` point at it. `--net none` runs with no
network at all. The proxy is killed and its directory removed on exit.

### 2. `dispatcher.py`

```
dispatcher.py run [--interval 300]      the loop (the unit's command)
dispatcher.py once                      one cycle
dispatcher.py usage                     the parsed /usage lines
```

**Where its state lives:** `~/.local/state/motodiag/fleet/`
(`$FLEET_STATE`): `mirror.git` (its own `git clone --mirror` of the GitHub
repository, public, no credential), `runs/<stamp>_<stage>/` (each stage's
clone and run directory), `state.json` (a rate-limit pause, the last
digest's date, the last cycle), `digests/`, `dispatcher.log`, and
`dispatcher.lock`. 387's call ledger, `calls.jsonl`, sits beside them.

**One process, one host.** `run` and `once` take an exclusive `flock` on
`dispatcher.lock` and exit 4 if another holds it. The label is the lock
between ranks; the flock is the lock between dispatchers.

**Its credential.** It reads `CLAUDE_CODE_OAUTH_TOKEN` from
`~/.config/motodiag/anthropic.env` (386's procedure) and passes it to
`fence.sh` and nothing else. It refuses to start, exit 4, when the file is
missing, holds anything but that one variable, or holds a value that is not
of the OAuth class (`sk-ant-oat`) or is more than one token (as built, after
bug fix #1: the value must be exactly one `sk-ant-oat[A-Za-z0-9_-]+` and
nothing else), and when `ANTHROPIC_API_KEY` is in its own
environment: a key would bill API rates silently (the proposal's cost
model). `gh` runs outside the fence on the operator's login, a stand-in
until the fleet has its own identity (F214, K40), with `GH_REPO` set.

**One cycle:**
1. The mirror: cloned if missing, else `git remote update --prune`.
2. The sweep (no model).
3. A paused stage whose reset has passed is resumed (below).
4. Unless paused: each open issue labelled `plan:needs-review` that is due
   gets the Executive Officer.
5. Unless paused: after 07:00 local, yesterday's digest, once a day.

**The fenced runner.** The ranks' scripts take a `run=` callable for their
subprocesses (387). The dispatcher passes one that runs `gh` outside the
fence with `GH_REPO` set, and wraps every `claude` call as `fence.sh
--clone <stage clone> --run <stage run> --workspace-docs <path> -- claude …`.
It checks the call's `cwd` is the stage's clone. When the call names
`--model claude-opus-5-5`, it reads the usage first and refuses the call
at 70% or more of the weekly all-models figure, or when the figure cannot
be read. On a resumed stage it adds `--resume <session>`. After the call it
reads the output for a rate limit (below).

**The Executive Officer stage.** Due when the last `labeled` event of
`plan:needs-review` (`gh api …/issues/<n>/events`) is newer than the
rank's last comment on the issue (a comment opening with `<!-- xo-verdict:`,
`Executive Officer, phase` or `<!-- fleet-dispatcher:`). So a stage runs
once per application of the label, and a back-to-captain verdict, which
sets the same label, waits for the Captain to apply it again. The phase is
the issue title's `Phase <N>`; the branch is the backticked `phase-<N>-…`
in the body, else the one `phase-<N>-*` head in the mirror. Neither found,
or two heads: a dispatcher comment saying so, the label unchanged. Then a
stage clone of that branch from the mirror (`git clone --no-hardlinks
--branch`), and `xo.review(phase, issue, repo=clone, run=runner)`, which
sets the label from the parsed verdict or stops and leaves it (387).

**A rate limit** is a claude result with `is_error` whose text names a
usage or rate limit, or a non-zero exit whose output does. The runner
raises it past the rank (it is not a `Stop`, so `xo.py` neither comments
nor moves the label). The dispatcher reads `/usage` for the reset time
(the line at 100%; else the session line), records the stage, its issue,
run directory and session id with `paused_until` in `state.json`, and
comments on the issue: stopped, label unchanged, the reset time, the
session. No model stage starts while paused. After the reset it reruns the
same stage in the same run directory with `--resume <session>`. When no
reset can be read, it waits one hour and reads again.

**The usage.** `claude -p "/usage" --output-format json` through the fence
(0 turns, no cost, Step 0 S0-4). Parsed: `Current session`, `Current week
(all models)` and any `Current week (<model>)` line, each a percentage and
a reset time in the named zone; the year is the first that puts the reset
no more than a day in the past.

**The digest stage.** At the first cycle after 07:00 local whose
`state.json` does not already record yesterday: a stage clone of `master`,
`yeoman.digest(yesterday, root=clone, run=runner)`, and the page copied to
`digests/<date>.md` in the state directory. Not committed, not posted
(Step 0 S0-7). A stop records nothing, so the next cycle tries again.

**The sweep.** For each open issue carrying any of the ten state labels
(every one of 387's eleven but `mission`, Step 0 S0-7): a label whose last
`labeled` event is more than 24 hours old, with no sweep comment yet for
that label and that time, gets one comment opening
`<!-- fleet-sweep: label=<label> applied=<time> -->`, saying how long it
has sat and who moves it next (the proposal's label table: the Executive
Officer, the Captain, the Engineer, the Red Team, the Quartermaster, or
the Admiral). `--sweep-hours` exists for the proof only, and the log says
when it was used.

**What it never does:** move a label itself (only a rank's script does,
from a parsed result); run anything that writes code or merges; run a
stage outside the fence; delete a run directory that a pause still names.
It keeps the newest 20 run directories.

### 3. The service

- **`ops/desktop/motodiag-fleet.service`**, shaped like
  `motodiag-api.service`: `User=lilcu`, `WorkingDirectory` its own clone
  (`~/motodiag/fleet/code`), `ExecStart=` `/usr/bin/python3` on that
  clone's `.claude/skills/fleet/dispatcher.py run`, `PATH` naming `~/.local/bin`
  for `claude` and `gh`, `Restart=always` (as built, with `RestartSec=30`
  and `RestartPreventExitStatus=4`, so a refusal is not retried),
  `WantedBy=multi-user.target`, and
  `ConditionPathExists` on the token file, so the unit never starts without
  its credential, as the API's never starts without live. No
  `EnvironmentFile`: the dispatcher reads the token itself and hands it only
  to the fence.
- **`ops/desktop/install_fleet_unit.sh`**, shaped like `install_unit.sh`:
  `install -m 644`, `daemon-reload`, `enable`, `is-enabled`; run with sudo
  by the operator.
- **`ops/desktop/motodiag-fleet-boot.xml`**: the same task as
  `motodiag-wsl-boot.xml` (boot trigger, S4U, least privilege, `wsl.exe -d
  Ubuntu-26.04 --exec /bin/sleep infinity`), its own name
  `\motodiag\fleet-boot` and description, so the fleet holds the VM up
  whether or not the API's task exists. Registered elevated by the operator,
  with `Register-ScheduledTask` and the `<?xml?>` declaration stripped
  (bug fix #2: `schtasks /Create /XML` refuses a UTF-8 file).
- **`ops/desktop/fleet_boot_check.py`** (not in v1.0): the restart test's
  judge, comparing the unit's `ActiveEnterTimestamp` with the Windows
  sign-in time from `quser.exe`.
- **The paste blocks**, plain English, which computer and which window, one
  block each, ending ALL GOOD or SOMETHING IS OFF: the code clone and the
  unit's install (Ubuntu window, sudo); the task's registration (Windows,
  an administrator PowerShell); the service restart proof; the reboot proof
  written like 382's M7 (task off then on, nobody signed in), for the
  operator to run tomorrow. As built: `388_operator_steps.md`, steps 1–4
  (the token, the unit, the task, the restart test).

## The change log's three newest entries

- **2026-10-22, `fleet` joins the procedure folders.** No check: the entry
  says this row "is text only, and no check reads the table". This phase
  adds to the folder that row names.
- **2026-10-20, rule 6: plain English to the operator.** No check: the
  entry says "Text only; no check holds it." Every paste block in this phase
  is written to it: which computer, which window, one block, ending ALL
  GOOD or SOMETHING IS OFF, no internal labels.
- **2026-10-19, live is on the home desktop.** The check it became:
  `tests/test_phase382_live_location.py`. The dispatcher runs on the
  machine that holds live and never reads it; no stage clone carries live
  (Step 0 S0-6: stage clones come from the GitHub mirror).

## Rule-1 stops anticipated

- **A login or a credential: met at Step 0.** The fleet's setup-token is
  not on this machine. The operator runs `claude setup-token` and writes
  `~/.config/motodiag/anthropic.env`. Until then everything without a model
  call is built and proven; the model-level proofs (the import resolving
  inside the fence, one dispatcher cycle on a planted issue, the service
  running) follow it.
- None expected from a fork, a threshold or a rule's definition (the 70%
  and the 24 hours are the operator's), a test that cannot be made green,
  or a live-database change (nothing touches live).

As it went: the token stop, as planned ("ALL GOOD"). And one not
anticipated: the desktop could not produce a regression of record, and
the Mac could not either without pinning the fence test's Mac skip in
`EXPECTED_SKIPS`, the operator's call (F206). The operator picked "Mac
runs it (Recommended)".

## Tests

- `tests/test_phase388_fence_boundary.py`, skipped on macOS, naming
  `tests/test_phase257_sandbox_boundary.py` as its Mac twin; on Linux it
  fails, never skips, without `bwrap`. No model. 257's eight planted
  attempts refused: a write to this repository's tree, to its `.git`, to
  `~/.claude`, to `~`, a Python write to `~`, a push into this repository,
  a read of the operator's login file, a read of `gh`'s credential, each with
  a control showing the target or the credential is there outside. A push to
  `master` rejected, `master` unmoved, and a push to GitHub refused by the
  gate. The `workspace-docs` import: the file read inside, a write to it
  refused, the approval seeded for the fence's clone path, and a fence with
  no `workspace-docs` refused. F215's planted read of `~/.config` refused,
  with a second canary elsewhere in the home also refused (a confinement,
  not a list). The network: a direct connection unreachable; the gate's
  403 for any host but the model API, its log line. The controls: the same
  write outside the fence succeeds; writes and a commit inside the clone and
  run directory succeed. The refusals: no `bwrap`, the operator's checkout
  as the clone, a missing run directory.
- `tests/test_phase388_dispatcher.py`, with stand-ins for `claude`, `gh`
  and `fence.sh`: the usage parsed from the measured text and its reset
  times; the Opus gate at 69% and 70% and unreadable; Fable and Haiku not
  gated; the due rule; the phase and branch from an issue, and the stop
  when neither is found; one XO cycle end to end with each verdict's label;
  a stop that moves no label; the rate limit recorded, the comment, no stage
  while paused, and the rerun with `--resume`; the sweep's one comment, no
  duplicate, nothing under 24 hours, `mission` not swept; the digest once a
  day and its copy; the token rules and the refusal with an API key in the
  environment; the flock.
- `tests/test_phase388_service_contract.py`: the unit's shape against
  `motodiag-api.service`; the task's XML equal to `motodiag-wsl-boot.xml`
  but for its name and description; the install script; each hand-written
  known-bad unit under `fixtures/service/` failing its own rule.
- `388_mutate.py`: every mutation red.

As built: 39 tests in the fence file (27 functions), 62 in the dispatcher
file, 33 in the service file; 134 in all. The service file also runs
step 1's token check on planted files, with the Mac's `stat` and `wc`
stood in, and holds step 3 to `Register-ScheduledTask`. Mutations: 44/44
red.

## Non-goals

- Any seat that writes code, pushes or merges (the Captain, the Engineer,
  the Red Team, the Quartermaster): later rollout steps. So is the answer to
  the model's token being in a Bash-capable seat's environment (Step 0
  S0-5).
- The fleet's own GitHub identity and the master ruleset (F214): created in
  the phase where a rank first pushes, the operator's words.
- Posting or committing the digest; the Mac's activity log as an input.
- Labels: 387's eleven are reused as they are.
- Any path under the data folder, seed data, a split or an eval protocol;
  anything under `src/`; live.
- Closing issue #9: it is the operator's.

Held: none of these was done.

## Planned items

- [x] `fence_net.py` and `fence.sh`
- [x] `tests/test_phase388_fence_boundary.py`, and the fence proofs in the log
- [x] `dispatcher.py`, its fixtures and `tests/test_phase388_dispatcher.py`
- [x] the unit, the install script, the task, their known-bad fixtures and
      `tests/test_phase388_service_contract.py`
- [x] `SKILL.md` and `CHANGELOG.md`
- [x] the paste blocks
- [x] after the operator's token: the import inside the fence, one
      dispatcher cycle on a planted issue, one sweep comment, the unit
      active after a restart
- [x] the mutation run; `COLLECTED_TEST_FLOOR` raised
- [x] close-out: `wholetree.sh --full`, `regression.sh`, the handoff,
      `verify_phase.sh`, row 388 to ✅ (`verify_phase.sh` after the merge,
      as the closeout sequence orders it)

## Deviations

- **Three bug fixes, all in the operator's paste blocks.** #1: step 1's
  check, and `load_token`, judged only how the token's line started, and
  passed a file holding the token five times with a stray escape
  character (caught by the operator). #2: step 3 registered the Windows
  task with `schtasks /Create /XML`, which refuses a UTF-8 task file; it
  now uses `Register-ScheduledTask` with the declaration stripped (caught
  by the operator). #3: step 1's check used Linux's `stat -c` and `wc -l`,
  so its test failed on the Mac (caught by the Mac's `wholetree --full`).
  The shared cause, in the log: each block's check was proven only where
  it was written. 386's procedure and `motodiag-wsl-boot.xml`'s comment,
  the records #1 and #2 copied, are not changed here; the handoff names
  both.
- **The regression of record ran on the Mac**, with the fence test's Mac
  skip pinned in `EXPECTED_SKIPS` (the operator's "Mac runs it
  (Recommended)"), and 383's equality literal updated with it. The
  desktop's own run failed for want of the Mac's tools: **F216**.
- **The billing check ran through the fence**, not bare as 386's procedure
  wrote it: that is how every fleet call goes.
- **`ops/desktop/fleet_boot_check.py`, a file the plan did not name**: the
  restart test's judge, a script rather than an inline heredoc (382's relay
  lost heredocs and `<`), reading the Windows sign-in time with `quser.exe`.
- **The token never rides on a command line**, a decision the plan did not
  spell out: `bwrap --setenv` would put it in an argv any process can read;
  `fence.sh` cleans the environment with builtins and the token is
  inherited. So no `--clearenv`.
- **A test the plan claimed and nothing held**: the fence's own `/` and
  `/fleet` read-only, added before the mutation run.
- **The XO's note measured**: the due rule depended on GitHub making no
  event when a present label is re-added; measured on #10, with the
  remove-and-add control.
- **The sweep proof ran at a 1-hour threshold** (`--sweep-hours 1`), so it
  could run the same night and show both sides in one run; the log says so.
- **The host slept for 39 hours** (2026-10-23 06:09 to 10-24 21:37); the
  dispatcher resumed on waking but skipped the digest for 10-22: **F217**.
- **An extra record for 382**: the operator's proof-5 Mac output, added to
  382's handoff in this close-out at the operator's request.
- **Guard blocks**: the push guard (a commit and a push in one `bwrap … sh
  -c` line, Step 0), the edit guard twice (a redirect to a variable path;
  `sed -i` on `FOLLOWUPS.md`, my slip), and one built-in Claude Code check
  (an `rm -rf` of a variable path). Each in the log; no guard changed.

## Results

Regression of record: 11187 passed, 0 failed, 40 skipped, 0 errors at `54e6d6f` (25 min 47 s wall, `python -m pytest -n auto --dist load`, exit 0)

Run on the Mac, after `wholetree.sh --full` at `54e6d6f` (record
`9ad4df51…_full.json`). The 40 skips are 244H's "no production database
on this machine" and the 39 fence tests on macOS, both pinned.

- The fence: 39 tests on Linux, 257's eight planted attempts among them;
  the workspace rules load inside the fence, and not without the
  approval.
- One dispatcher cycle, real: the XO approved 388 on issue #10 and the
  script set `plan:approved`; the digest for 2026-10-21; one sweep comment
  on #9, not repeated.
- The service: active and enabled since 2026-10-22 23:16:27, `NRestarts=0`;
  the task Running, S4U.
- The billing check: claude.ai usage moved (session 2% → 3%, week 9% →
  10%); the Console half is open until its data passes 03:07 UTC.
- Mutations 44/44 red. `COLLECTED_TEST_FLOOR` 11093 → 11227 (+134).
- Open: the restart test (the operator's), the Console reading, F216,
  F217.
