# Phase 406 — phase log

**Status:** Complete

## 2026-11-19 — Step 0 and v1.0

The operator, 2026-11-19 (K93): "Yes. Set it up as phase 406 and build it on
the Mac now, alongside 334. Two conditions: it comes as a pull request I
merge after your review, not a direct push to master, and the database step
from the Mac must still show me the dry run's list before it asks for yes."

Master `3ebeac6` holds K93, row 406 (🚧), the prompt
(`docs/prompts/406_the_mac_runs_the_rest.txt`) and the plan of record's
entry. This branch is `phase-406-the-mac-runs-the-rest`, from `3ebeac6`.

Step 0 (`406_step0.md`): the fixed list has 13 operations; the lock's
`PermitTTY no` means the database step cannot ask for yes through the way
in, so it becomes two calls with the yes on the Mac; the only password-free
rule is the app server's. Classification: extension.

v1.0 (`406_implementation.md`): ten operations, the database step's two
modes, `remote.py deploy-step`, one more password-free rule line and
`update_remote.sh`. No change to the lock. Committed and pushed as
`a7c5070` before any code.

## 2026-11-19 — the build

- **The dispatcher** (`ops/desktop/motodiag_remote.py`): four patterns, three
  paths, `Shell.run`/`capture` with an environment and `Shell.sleep`, and the
  ten operations. `api` now calls the shared `unit`.
- **The database step** (`.claude/skills/deploy/through_fleet.py`): `run` is
  `dry_run`, the question, then `apply`; `dry_run_only` and `apply_approved`
  are the Mac's two calls, and `main` takes `--dry-run-only` or `--apply
  <sha256>`. Phase 395's 17 tests pass unchanged.
- **The Mac's client** (`.claude/skills/deploy/remote.py`): `stream`,
  `ask_tty` and `deploy_step`; `main` checks `deploy-step`'s three
  arguments against the same patterns as the desktop.
- **The install:** `install_sudoers.sh`'s second line; `update_remote.sh`.
- **Two pins moved on purpose,** each with K93 beside it: 384's "the list is
  exactly these" (13 names, now 23) and 382's rule test, which now holds the
  first line of the rule file; 406's install test holds the second.
- **One check removed before the tests were written:** `apply_approved`
  re-ran `refusals`, which read only the branch's committed history between
  master and the commit; with the checkout and the branch both held at the
  commit it could not change, and no test could see it.
- **The stand-in, wrong twice and fixed, the code unchanged:**
  `test_phase406_remote_client.py`'s SSH stand-in compared the words as
  separate arguments, where `ssh_argv` sends them as one quoted command
  (11 cases red on the first run; the stand-in now reads the last argument).
- **A guard blocked a command:** `sed -i '' '/^import subprocess$/d'
  tests/test_phase406_remote_client.py`, at about 16:00 EST: "edit guard:
  blocked — `sed -i` edits a file in place". The line was removed with the
  Edit tool instead. The guard is unchanged.
- **Tests:** 86 new (`tests/test_phase406_remote_ops.py` 46,
  `_through_fleet_split.py` 12, `_remote_client.py` 19, `_install.py` 9);
  201 pass across every file 406 touches. One case was added after reading
  the planned mutations: the feed running on its old process
  (`test_server_update_puts_the_code_back_when_the_feed_kept_its_old_process`),
  without which the PID check had no test.
- **Mutations** (`406_mutate.py`, `406_mutate.out`): 28/28 red.
- **`COLLECTED_TEST_FLOOR`** 12779 → 12865, by a diff of collected ids
  against master `3ebeac6`: +86 −0.
- **The code's counts** (`scripts/code_quality.py counts`) equal their pins:
  ruff 1108, mypy 202, complex 25, big 5, helpers 19, swallowed 22.

## 2026-11-19 — the review, and its fixes

A fresh agent reviewed the build's diff (`6d9b356`), given the code and the
plan, not this log. It found seven points. Each is fixed, and each fix has
a test that a planted fault turns red:

1. **A Mac gone away mid-step stopped the put-back.** The dispatcher's own
   lines, and the commands it ran, wrote to the closed channel; it was
   reproduced with the merge and restart done and no reset. Now:
   - every line goes through `say`, which drops what cannot be sent;
   - `Shell.run` passes each command's lines on through `say`, so no command
     writes to the channel itself (`errors="replace"` for bytes that are not
     UTF-8);
   - SIGHUP is ignored;
   - the steps that change something hold one lock (`remote.lock`), so a
     second call is refused, not raced;
   - `through_fleet.py` runs with `-u`, so its lines arrive as they come.
   Tests: the put-back with stdout closed; a real pipe with no reader; the
   real dispatcher run as SSH runs it, its output unread and SIGHUP sent
   mid-step; the lock.
2. **The put-back claimed success unchecked.** `back()` reads the reset's
   exit and then HEAD. A put-back that did not take is said ("could NOT be
   put back … Bring this to the advisor now"), and nothing restarts on the
   new code after it. Tests: a reset that fails, and one that exits 0
   without moving, for `server-update` and `fleet-move`.
3. **The feed check was weaker than 404's step.** `server-update` waits up
   to 3 minutes for a new check-in row on live, as 404's block did. Then the
   feed must still run on the process it was restarted as: its unit
   restarts it after a crash (`Restart=on-failure`), so a new PID is a
   crash. A crash puts the code back. No check-in at all keeps the new code
   and says so, because the feed asks Stripe as before. Tests: the feed
   dying after its check-in, systemd restarting it, no check-in.
4. **The settings were read only after the change.** `live.json`,
   `server.env` and live's check-ins are read before anything moves. Tests:
   each one unreadable is refused, nothing changed.
5. **The apply could be sent without the question.** `remote.py` refuses
   `deploy-apply` on its own; only `deploy-step` sends it, after the list
   and the yes. The answer file no longer says the operator typed yes. It
   says the answer was typed on the Mac, not at the desktop, and how the Mac
   sends the apply, and records it as `> yes`, the line the close-out
   quotes. The plan's re-run of `refusals()` in the apply was removed in the
   build (above); v1.1's Deviations says so.
6. **Tests that could not see a check.** The stand-in's reset can now fail
   and stdout can close; the search on start's exit and the fleet's running
   state each have a case. The install scripts are run, not read: copies
   with only their two root paths moved (each move asserted once), and
   stand-ins for `id`, `install`, `visudo`, `sha256sum` and `systemctl`,
   proven by `command -v` in the scripts' shell.
7. **The search on start ran with sshd's PATH.** It runs with the fleet
   unit's (`~/.local/bin` first); the test reads the unit file's line.

- **One test was wrong, the code unchanged:** the case for `Shell.run`'s
  lines had its child print one line to a buffered stdout and one to
  stderr, and they arrived in the other order. The child flushes now.
- **One more, found while writing v1.1:** Phase 384's own operations, in
  the same file, still printed with `print`, so a Mac gone away mid-step
  ended the dispatcher at its next line and the request's outcome went
  unlogged (the steps themselves were already safe: an apply's child runs
  to its end, and a dry run stops before it starts). Their 18 lines now go
  through `say` too. It predates 406; fixed here rather than filed,
  because it is the review's first point in the file 406 owns, and the
  regression of record had not run. The full whole-tree run started on
  `e4a2792` was stopped for it, unfinished.
- **And the review's 4, finished:** `server-update` still read the
  server's settings and live's check-ins again after its change. Had
  either read failed there, the step would have been refused with
  "nothing was changed" while the new code ran. It now keeps the settings
  it read before the change, and a check-in it cannot read after the
  change counts as not seen ("no new check-in could be seen on live", true
  either way). Found while drafting the handoff; the full whole-tree run
  started on `8529590` was stopped for it, unfinished.
- **A guard blocked a command,** at 17:24 EST: a Python heredoc that edited
  my draft of v1.1 in the scratchpad, through a path given as an argument,
  with `tests/` in its text: "edit guard: blocked — a Python script body
  writes to a path the edit guard cannot resolve, and the body names src/
  or tests/". The draft was edited with the Edit tool instead. The guard is
  unchanged.
- **Mutations** (`406_mutate.py`, `406_mutate.out`): 52/52 red. 24 are new:
  one per fix, two for 384's lines, two for the reads after the change; D6,
  D7, D11, D21, D23 and T5 were moved to the rewritten lines.
- **`COLLECTED_TEST_FLOOR`** 12865 → 12889, by a diff of collected ids
  against master `3ebeac6` (12779): +110 −0, all in the four new files.
- **The code's counts** (`scripts/code_quality.py counts`) still equal their
  pins: ruff 1108, mypy 202, complex 25, big 5, helpers 19, swallowed 22.

## 2026-11-19 — the regression of record, and the close-out

`wholetree.sh --full` on `d844fba` first: 5326 passed, 1 skipped, in
13 min 24 s; its record is `ef5c5d03…_full.json`. Then
`.claude/skills/closeout/regression.sh`, on the Mac, on AC power, from
17:52 to 18:28 EST:

Regression of record: 12840 passed, 0 failed, 49 skipped, 0 errors at `d844fba` (35 min 55 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0)
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:131: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:139: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:148: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:159: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [7] tests/test_phase388_fence_boundary.py:221: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:235: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:244: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:280: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:287: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:291: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:295: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:303: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:316: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:325: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:330: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:338: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:344: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:350: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:354: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:360: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase390_space.py:327: bubblewrap is the desktop's
Line coverage of record: 88.36% at `d844fba` (the pin is 87.50%): 0.86 points above it; raise COVERAGE_PERCENT to lock it in

12840 + 49 = 12889, the collected count. The coverage pin is left at
87.50%, as 404 left it.

- **No live step:** the phase has no migration and changes nothing on
  live, so the close-out's live step does not apply.
- **No bug-fix register:** v1.1's Deviations, 4, says why.
- **No generator:** nothing the phase wrote ships in `src/` or is loaded by
  a migration.
- **The handoff** (`docs/handoffs/2026-11-19_406_closed.md`) carries the
  operator's two blocks, each run first on a bench in the advisor's
  scratchpad, with stand-ins proven to be the ones the block's shell finds:
  step 1 (the desktop) in 11 cases, with 4 planted faults each caught;
  step 2 (the Mac) in 6 cases, with 2. The merge block, given to the
  operator in the session, in 13 cases, with 3.

## 2026-11-20 — after the merge

- **The merge** was the operator's, from the Mac: pull request #74 as
  `be1e43a`, at 23:45:47 EST on 2026-11-19. The block's first paste
  stopped at its first GitHub call ("error connecting to
  api.github.com"), having changed nothing. A few minutes later, from
  the same Mac, GitHub answered, the head was still `09e5f76`, its check
  had passed and master had not moved. The second paste merged. Master's
  tree is `6b90f37`, `09e5f76`'s own.
- **Step 1's check was wrong, and was corrected before it ran.** Found on
  reading the step again after the merge.
  - The handoff's block asked `sudo -n -l /usr/bin/systemctl <verb>
    <unit>` of the five approved restarts. It asked the same of `restart
    ssh.socket` and `stop motodiag-fleet.service`, which must not run
    without a password.
  - `sudo -l` with a command says whether the policy permits it, with a
    password or without, and lilcu has `(ALL : ALL) ALL`. 390's log
    measured this on the desktop: "`sudo -n -l <cmd>` passes before the
    rule exists".
  - So the first loop could not fail, and the second would fail on any
    desktop: the block would install correctly, then print a false
    SOMETHING IS OFF.
  - The first bench's stand-in `sudo` answered `-n -l` from a list of
    password-free commands, which is not what sudo does.
- **The corrected block reads the rules themselves.** It reads them with
  the password typed once for the install, before `sudo -k`.
  - The restarts' file, `/etc/sudoers.d/motodiag-api`, must equal the
    two approved lines exactly.
  - It lists every sudoers file with a line that lets a command run
    without a password: `NOPASSWD` or `!authenticate`, comments left out.
    It reads `/etc/sudoers`, `/etc/sudoers.d`, and `/etc/sudoers-rs`
    when there is one, with GNU `grep -R`, so a linked file is read too.
  - Only two files may be on that list: the restarts' file, and the disk
    clean-up's (`/etc/sudoers.d/motodiag-fstrim`) holding its one line.
  - None of it depends on how `sudo -l` prints, which differs between
    sudo and sudo-rs. The desktop's sudo words its refusal as sudo-rs
    does ("interactive authentication is required", 390's reclaim line).
- **Its bench** is bench30, in the advisor's scratchpad.
  - The stand-in `sudo` is the policy as 390 measured it. `-n -l <cmd>`
    lists any command. A password typed once is cached until `-k`, and
    `-n cat` and `-n grep` run only while it is.
  - The install writes the merged `install_sudoers.sh`'s own lines,
    taken from `be1e43a`.
  - grep is GNU grep 3.12, as on the desktop, installed on the Mac from
    Homebrew for this bench (rule 6, K26).
  - 19 cases, all as expected: the first bench's 11, and 8 on the rules.
    The 8: another file; a `!authenticate` default; a wider clean-up
    rule; `/etc/sudoers-rs`; a linked file; comments that must not
    count; a wider install; a password that ran out.
  - The first version, run there as a control, fails a good install with
    "systemctl restart ssh.socket runs without a password".
  - 10 planted faults, 10 caught.
- **Step 1, run by the operator:** ALL GOOD. `visudo` parsed the new
  rules and the policy, and the installed dispatcher hashes to
  `938af2952962b66e…`, the merged file's.
- **No finding was filed.** 334's branch is open, so a number taken on
  master now could be handed out twice (F230). This entry and the
  handoff are the record.
- **Step 2 lost its move of the fleet's code copy,** before it ran. The
  fleet was holding 334 for its database step, the move restarts the
  fleet, and nothing that night needed it. The copy, at `ce12882`, moves
  after 405.
  - The read-only block ran first from the advisor, then from the
    operator: ALL GOOD both times. These were the first runs of
    `feed-status`, `fleet-status` and `fleet-log` against the real
    desktop.
  - One refusal along the way was the advisor's own. `fleet-log 72 6`,
    from the advisor's zsh, which does not split an unquoted variable,
    went out as one word. The desktop refused it, as it should ("'fleet-log
    72 6' is not an operation"). The operator's blocks run under bash.
- **334's database step stayed at the PC** (K93), with the advisor's
  stop-the-feed block, checked first against the real note on issue #72.
  Migration 091 is live (schema 91). `verify-live 334` equals the
  approved exact diff, and the fleet's own check matched. The payments
  feed was stopped about 3 minutes. The handoff has the lines.
