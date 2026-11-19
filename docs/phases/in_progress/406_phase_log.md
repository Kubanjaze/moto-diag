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
