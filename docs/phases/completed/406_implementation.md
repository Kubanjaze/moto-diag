# Phase 406 — The Mac runs the rest of the desktop's steps

**Version 1.1, 2026-11-19.** Built by the advisor session on the Mac (K93),
on `phase-406-the-mac-runs-the-rest` from master `3ebeac6`. Classification:
**extension** (`406_step0.md`). v1.0 was committed as `a7c5070` before any
code; the build is `6d9b356`; the review's fixes are `e4a2792`, `8529590`
and `d844fba`, the commit of the regression of record.

## Goal

The operator does every routine step on the home desktop from the Mac's
Terminal, through the way in Phase 384 built, and the lock stays as 384
made it: keys only, from the Mac's tailnet address only, no terminal, no
forwarding, every request one named operation of the root-owned dispatcher.
The steps are the ones done in the desktop's Ubuntu window on 2026-11-18
and 19 (`406_step0.md`, S0-3). The database step from the Mac shows the dry
run's list before it asks for yes (K93's second condition).

## The plan of record

406 runs beside the 'Next, in order' list (K93; the plan of record's entry
"2026-11-19, later"). The fleet does not wait for it, and it does not wait
for the fleet. It arrives as a pull request the operator merges after the
advisor's review (K93's first condition).

## Logic

### 1. The dispatcher (`ops/desktop/motodiag_remote.py`)

- **Arguments.** Four patterns join `PATTERNS`: `issue` (`\d{1,5}`),
  `count` (`\d{1,3}`), `branch` (`phase-\d{3}[A-Z]?-[a-z0-9-]{1,80}`) and
  `sha256` (`[0-9a-f]{64}`). No argument reaches a shell, as before.
- **Paths.** `Paths` gains the fleet's code copy (`~/motodiag/fleet/code`),
  its state folder (`~/.local/state/motodiag/fleet`), the server's
  settings (`~/.config/motodiag/server.env`) and the home folder.
- **Shell.** `run` passes each command's lines on as they come, through
  `say`, so no command writes to the Mac's channel itself; `run` and
  `capture` take an environment; `sleep` is the shell's, so the tests wait
  for nothing.
- **A Mac gone away mid-step.** Every line the dispatcher prints, 384's
  operations' too, goes through `say`, which drops a line that cannot
  reach the Mac, and SIGHUP is ignored, so every operation runs to its
  end, a put-back included, and its outcome is logged.
- **One at a time.** The seven operations that change something hold one
  lock (`~/motodiag/remote.lock`); a second call while one runs is refused,
  having changed nothing.
- **Ten operations,** each refused having changed nothing when a check
  before it fails:
  1. `feed-status`: `motodiag payments feed status` from the server's
     checkout and venv, with the server's settings (the paste blocks' LOAD:
     `MOTODIAG_*` cleared, `server.env` read, the database and data folder
     from `live.json`). Its exit code is the operation's.
  2. `feed-stop`, `feed-start`, `feed-restart`: `sudo -n systemctl <verb>
     motodiag-payments.service`, then `is-active` said. `api-stop`,
     `api-start` and `api-restart` share the code.
  3. `server-update <commit>`: the server's update after a merge (404's
     step 1). Refused unless the app server and the feed run, `live.json`,
     `server.env` and live's check-ins can be read, the server's checkout is
     on master and clean, and master on GitHub is at `<commit>`, a
     descendant of the checkout. Then: fast-forward; restart the app server
     and wait for `/healthz` to say ok; restart the feed and see a new main
     PID; wait up to 3 minutes for a new check-in row on live; the feed must
     still run as that PID. When any of these fails, the code is put back
     (`git reset --keep`, its exit and then HEAD checked) and both are
     restarted on it; a put-back that does not take is said, and nothing
     restarts on the new code. No check-in seen keeps the new code and says
     so; after the change, a check-in that cannot be read counts as not
     seen, so nothing after the change is refused. Then `feed-status` once,
     with the settings read before the change, its exit the operation's.
  4. `fleet-status`: the fleet's service, whether a stage is running
     (`pgrep -x bwrap`), its code copy's branch, commit and cleanliness, and
     `dispatcher.py recover --dry-run`, run with the fleet unit's PATH.
     Reads only.
  5. `fleet-log <issue> <count>`: the last `<count>` lines of the fleet's
     log that name `issue <issue>:`, read as bytes, so a zero byte cannot
     hide them (F284).
  6. `fleet-move <commit>`: the move of the fleet's code copy (403's step
     2). Refused while a stage runs, unless `recover --dry-run` exits 0 and
     says "nothing to resume", unless the copy is on master and clean, and
     unless master on GitHub is at `<commit>`, a descendant of the copy.
     Then: fast-forward; `sudo -n systemctl restart motodiag-fleet.service`;
     wait for a new "the search on start:" line in the fleet's log with the
     unit running. When it does not come, the copy is put back (checked as
     in 3) and the fleet restarted on it.
  7. `deploy-dryrun <phase> <branch> <commit>` and `deploy-apply <phase>
     <branch> <commit> <sha256>`: the fleet's database step in two calls,
     run unbuffered with the fleet's venv and its own code copy, as its
     paste block does (`deploy_block`).

### 2. The database step in two calls (`.claude/skills/deploy/through_fleet.py`)

- **`--dry-run-only`:** the checkout, the refusals and the dry run on a
  copy, then the change in plain words and a last line `dry-run diff
  sha256: <hex>`. Nothing is asked and nothing is applied; the checkout and
  its uncommitted diff stay for the second call.
- **`--apply <sha256>`:** no new checkout and no new dry run. Refused
  unless the checkout from the first call is at `<commit>`, its branch is
  still at `<commit>` in the fleet's mirror, and the dry-run diff it left
  hashes to `<sha256>`, the diff the operator was shown. Then the rest of
  `run`: the answer file, the commits, the apply and `verify_live`. The
  answer file says the answer was typed on the Mac, not at the desktop, and
  how the Mac sends the apply, and records it as `> yes`, the line the
  close-out quotes.
- **`run`** (the desktop's paste block) is the two halves with the yes
  asked on the terminal between them, and does what it did before (395's
  17 tests pass unchanged).

### 3. The Mac's client (`.claude/skills/deploy/remote.py`)

`remote.py deploy-step <phase> <branch> <commit>`: calls `deploy-dryrun`,
shows its lines as they come, takes the sha256 from its one sha256 line,
asks for yes on the Mac's own terminal, and only then calls `deploy-apply`
with that sha256. Anything but yes calls nothing more. `remote.py
deploy-apply` on its own is refused, so the apply is never sent without
the question. The other new operations go through as words, like `status`.
Handing the step back to the fleet (taking `needs-hands` off) stays in the
operator's paste block, as in the fleet's.

### 4. The install, once, at the desktop

- `ops/desktop/install_sudoers.sh` keeps 382's rule and adds one line:
  `systemctl start|stop|restart motodiag-payments.service` and `systemctl
  restart motodiag-fleet.service`, for `lilcu`, nothing else. `visudo -c`
  checks it before and after.
- `ops/desktop/update_remote.sh` (new): refuses without sudo, without 384's
  install, or with a dispatcher that does not parse; installs the new
  dispatcher root-owned, mode 755, where 384 put it, and runs
  `install_sudoers.sh`. It touches no SSH setting, no key and no unit.
- The handoff's two blocks, after the merge: at the desktop (Ubuntu
  window), the development checkout on master, `sudo sh
  ops/desktop/update_remote.sh`, the installed dispatcher's sha256 and the
  password-free rules checked, both ways; then from the Mac (Terminal),
  `status`, `feed-status`, `fleet-status` and `fleet-move` to master.

### 5. The deploy skill's own record

`.claude/skills/deploy/SKILL.md` names the new operations;
`.claude/skills/deploy/CHANGELOG.md` has a dated entry with K93.

## Rule-1 stops anticipated

- **Password-free rules** change what the operator's account may do
  without a password: K93 approves exactly these two units' rules. Any
  wider rule (another unit, another verb, `systemd-run`) is a stop.
- **The lock:** no change to `sshd`, the key, `PermitTTY` or the
  dispatcher's place. Any is a stop.
- None other. None arose: the rule line is the approved one, and the lock
  is unchanged.

## Tests

- `tests/test_phase406_remote_ops.py` (67), through a stand-in desktop:
  each operation's commands; each refusal planted, and in each no restart
  and no reset; the put-back on each failure after the change, and a
  put-back that fails or does not move said, not claimed; the feed dying,
  restarted by systemd, or never checking in; live's check-ins and the
  server's settings gone after the change; the lock; the Mac gone away
  mid-step, as a closed stdout, as a real pipe with no reader, and as the
  real dispatcher run as SSH runs it with SIGHUP sent mid-step, and two of
  384's operations with the channel closed; the fleet unit's PATH, read
  from the unit file; a log with zero bytes read.
- `tests/test_phase406_through_fleet_split.py` (12), on a real git mirror
  and a tmp database as in 395's tests: the dry run alone changes nothing
  on live and prints the sha256; the apply with that sha256 makes the
  change, and its answer file says where the answer was typed; a wrong
  sha256, a diff changed between the calls, a branch moved between them,
  and an apply with no dry run before it are each refused with live
  untouched.
- `tests/test_phase406_remote_client.py` (20): `deploy-step` shows the dry
  run's lines before it asks; anything but yes calls nothing more; yes
  calls the apply with the sha256 from the dry run; no single sha256 line,
  no question; `deploy-apply` alone is refused.
- `tests/test_phase406_install.py` (11): the rule file holds exactly 382's
  rule and the new one; the two scripts run, with stand-ins proven to be
  the ones their shell finds: the dispatcher installed root-owned, mode
  755, then the rules, mode 440, each checked; refused without sudo,
  without 384's install, with a dispatcher that does not parse, or with
  rules `visudo` refuses, having changed nothing.
- Mutations (`406_mutate.py`): 52/52 red.

## Non-goals

- No open terminal, and no change to the 384 key or `sshd` (the operator
  chose against it).
- No stop of the payments feed inside the Mac's database step: the first
  database step after 334's comes after 405 (S0-6).
- No change to `deploy.py`'s comparison: that is 405's.
- Nothing runs by itself on a timer.

## Deviations

1. **The apply does not re-run the refusals.** v1.0 said the apply is
   refused unless "the refusals still pass". `refusals` reads only the
   branch's committed history between master and the commit; with the
   checkout and the branch both held at the commit, it cannot change
   between the calls, and no test could see it. Removed before the tests
   were written (the phase log, "the build").
2. **`server-update` reads `feed-status` once, after a check-in.** v1.0
   said it reads `feed-status` until it exits 0. That verdict reads stored
   rows (the last poll within two intervals, a check-in within two
   check-in intervals, `cli/payments.py`), which the old process's rows
   meet right after a restart, so a new feed that died at once would pass.
   It waits instead for a new check-in row on live, as 404's block did (the
   feed checks in on its first round, `event_feed.run_forever`), then
   checks the feed still runs as the PID it was restarted as.
3. **Checks v1.0 did not name,** each from the review: the lock; a step
   that runs to its end when the Mac goes away (`say`, `Shell.run`, SIGHUP),
   384's operations included;
   the put-back checked; `live.json`, `server.env` and live's check-ins
   read before any change, and nothing read after it that could refuse; the fleet unit's PATH for the search on start;
   the search on start's exit read, and the fleet's unit running after its
   start line; `remote.py`'s refusal of `deploy-apply` alone; the answer
   file's wording.
4. **The review's seven points are recorded as a review round, not as a
   bug-fix register.** A fresh agent reviewed the build's diff before the
   regression, as the Red Team reviews a fleet build, and the seven were
   fixed in one commit (`e4a2792`), as a fleet build's round is; two
   follow-ups found in the same file before the regression, one of them
   finishing the review's 4, are `8529590` and `d844fba`. Their
   shared cause is the one the review named in its sixth point: the
   build's stand-ins could only succeed (a reset that never fails, a
   channel that never closes, scripts read and never run), so no test could
   see a failure path. The fix made each stand-in able to fail, and runs the
   real dispatcher, a real pipe and the real install scripts.
5. **Two pins outside the phase's files moved on purpose,** each with K93
   beside it: 384's "the list is exactly these" (13 names, now 23) and
   382's rule test, which now holds the first line of the rule file.
6. **The fleet's code copy moves through `fleet-move`.** v1.0 planned a
   last move by hand at the desktop. The handoff's Mac block moves it with
   the new operation instead, so its refusals guard the first move too.

## Results

- **Tests:** 110 new, in the four files above. The regression of record,
  on `d844fba`, on the Mac: 12840 passed, 0 failed, 49 skipped, 0 errors
  (35 min 55 s wall, `python -m pytest -n auto --dist load
  --cov=motodiag`, exit 0), after `wholetree.sh --full` on the same commit
  (5326 passed, 1 skipped). Line coverage of record: 88.36% (the pin is
  87.50%). The 49 skips are the Mac's pinned ones, listed in the phase
  log.
- **Mutations:** 52/52 red (`406_mutate.out`).
- **`COLLECTED_TEST_FLOOR`:** 12779 → 12889, a diff of collected ids
  against master `3ebeac6`: +110 −0.
- **The code's counts** equal their pins: ruff 1108, mypy 202, complex 25,
  big 5, helpers 19, swallowed 22.
- **Live:** no migration and no live change in this phase. The install at
  the desktop is the operator's, after the merge (the handoff's two
  blocks); its outcome is added to the handoff then.

## Planned items

- [x] The dispatcher's patterns, paths, shell and ten operations
- [x] `through_fleet.py`'s two modes, `run` unchanged
- [x] `remote.py deploy-step`
- [x] The rule line and `update_remote.sh`
- [x] The four test files, each check seen red
- [x] The deploy skill's `SKILL.md` and `CHANGELOG.md`
- [x] The regression of record, the close-out, and the handoff with its two
  blocks
- [x] The branch ready for a pull request the operator merges after review

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-19 | The plan, from Step 0 (K93). |
| 1.1 | 2026-11-19 | As built, with the review's seven fixes; Deviations and Results. |
