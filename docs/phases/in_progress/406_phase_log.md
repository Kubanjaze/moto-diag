# Phase 406 — phase log

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
- **Mutations** (`406_mutate.py`, `406_mutate.out`): 50/50 red. 22 are new,
  one per fix and two for 384's lines; D6, D7, D11 and T5 were moved to the
  rewritten lines.
- **`COLLECTED_TEST_FLOOR`** 12865 → 12887, by a diff of collected ids
  against master `3ebeac6` (12779): +108 −0, all in the four new files.
- **The code's counts** (`scripts/code_quality.py counts`) still equal their
  pins: ruff 1108, mypy 202, complex 25, big 5, helpers 19, swallowed 22.
