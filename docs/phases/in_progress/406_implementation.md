# Phase 406 — The Mac runs the rest of the desktop's steps

**Version 1.0, 2026-11-19.** Built by the advisor session on the Mac (K93),
on `phase-406-the-mac-runs-the-rest` from master `3ebeac6`. Classification:
**extension** (`406_step0.md`).

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
  `sha256` (`[0-9a-f]{64}`). No argument reaches a shell, as now.
- **Paths.** `Paths` gains the fleet's code copy (`~/motodiag/fleet/code`),
  its state folder (`~/.local/state/motodiag/fleet`) and the server's
  settings (`~/.config/motodiag/server.env`).
- **Shell.** `run` and `capture` take an environment; `sleep` is the
  shell's, so the tests wait for nothing.
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
     step 1). Refused unless the app server and the feed run, the server's
     checkout is on master and clean, and master on GitHub is at
     `<commit>`, a descendant of the checkout. Then: fast-forward; restart
     the app server and wait for `/healthz` to say ok; restart the feed and
     see a new main PID; read `feed-status` until it exits 0 or the tries
     run out. When the app server or the feed does not come back, the code
     is put back (`git reset --keep`) and both restarted on it.
  4. `fleet-status`: the fleet's service, whether a stage is running
     (`pgrep -x bwrap`), its code copy's branch, commit and cleanliness, and
     `dispatcher.py recover --dry-run`. Reads only.
  5. `fleet-log <issue> <count>`: the last `<count>` lines of the fleet's
     log that name `issue <issue>:`, read as bytes, so a zero byte cannot
     hide them (F284).
  6. `fleet-move <commit>`: the move of the fleet's code copy (403's step
     2). Refused while a stage runs, unless `recover --dry-run` says
     "nothing to resume", unless the copy is on master and clean, and
     unless master on GitHub is at `<commit>`, a descendant of the copy.
     Then: fast-forward; `sudo -n systemctl restart motodiag-fleet.service`;
     wait for a new "the search on start:" line in the fleet's log. When it
     does not come, the copy is put back and the fleet restarted on it.
  7. `deploy-dryrun <phase> <branch> <commit>` and `deploy-apply <phase>
     <branch> <commit> <sha256>`: the fleet's database step in two calls,
     run with the fleet's venv and its own code copy, as its paste block
     does (`deploy_block`).

### 2. The database step in two calls (`.claude/skills/deploy/through_fleet.py`)

- **`--dry-run-only`:** the checkout, the refusals and the dry run on a
  copy, then the change in plain words and a last line `dry-run diff
  sha256: <hex>`. Nothing is asked and nothing is applied; the checkout and
  its uncommitted diff stay for the second call.
- **`--apply <sha256>`:** no new checkout and no new dry run. Refused
  unless the checkout from the first call is at `<commit>`, its branch is
  still at `<commit>` in the fleet's mirror, the refusals still pass, and
  the dry-run diff it left hashes to `<sha256>`, the diff the operator was
  shown. Then the rest of `run` as now: the answer file (the operator's
  "yes", asked on the Mac through the way in), the commits, the apply and
  `verify_live`.
- **`run`** (the desktop's paste block) is the two halves with the yes
  asked on the terminal between them, and does what it does now.

### 3. The Mac's client (`.claude/skills/deploy/remote.py`)

`remote.py deploy-step <phase> <branch> <commit>`: calls `deploy-dryrun`,
shows its lines as they come, takes the sha256 from its last line, asks for
yes on the Mac's own terminal, and only then calls `deploy-apply` with that
sha256. Anything but yes calls nothing more. The other new operations go
through as words, like `status`. Handing the step back to the fleet (taking
`needs-hands` off) stays in the operator's paste block, as in the fleet's.

### 4. The install, once, at the desktop

- `ops/desktop/install_sudoers.sh` keeps 382's rule and adds one line:
  `systemctl start|stop|restart motodiag-payments.service` and `systemctl
  restart motodiag-fleet.service`, for `lilcu`, nothing else. `visudo -c`
  checks it before and after.
- `ops/desktop/update_remote.sh` (new): installs the new dispatcher
  root-owned where 384 put it, and runs `install_sudoers.sh`. It touches no
  SSH setting and no key.
- The handoff's step at the desktop: the development checkout at the
  merge, `sudo sh ops/desktop/update_remote.sh`, the fleet's code copy moved
  to the merge and the fleet restarted (the last move by hand). Then, from
  the Mac, `remote.py status`, `feed-status` and `fleet-status`.

### 5. The deploy skill's own record

`.claude/skills/deploy/SKILL.md` names the new operations;
`.claude/skills/deploy/CHANGELOG.md` gets a dated entry with K93.

## Rule-1 stops anticipated

- **Password-free rules** change what the operator's account may do
  without a password: K93 approves exactly these two units' rules. Any
  wider rule (another unit, another verb, `systemd-run`) is a stop.
- **The lock:** no change to `sshd`, the key, `PermitTTY` or the
  dispatcher's place. Any is a stop.
- None other.

## Tests

- `tests/test_phase406_remote_ops.py`, through the stand-in shell: each
  operation's commands; each refusal planted (a bad argument, a dirty
  checkout, master not at the named commit, a stage running, something to
  resume, the app server not healthy, the feed's PID unchanged, no start
  line), and in each refusal no restart and no reset; the put-back on each
  failure after the change; a log with zero bytes read.
- `tests/test_phase406_through_fleet_split.py`, on a real git mirror and a
  tmp database as in 395's tests: the dry run alone changes nothing on live
  and prints the sha256; the apply with that sha256 equals `run`'s outcome;
  a wrong sha256, a diff changed between the calls, a branch moved between
  them, and an apply with no dry run before it are each refused with live
  untouched.
- `tests/test_phase406_remote_client.py`: `deploy-step` shows the dry
  run's lines before it asks; "no" calls nothing more; "yes" calls the
  apply with the sha256 from the dry run's last line; no sha256 line, no
  question.
- `tests/test_phase406_install.py`: the rule file holds exactly 382's rule
  and the new one; `update_remote.sh` installs the dispatcher root-owned,
  mode 755, where 384 does, and names no SSH file.
- Mutations: each new check removed in turn turns a test red (N/N).

## Non-goals

- No open terminal, and no change to the 384 key or `sshd` (the operator
  chose against it).
- No stop of the payments feed inside the Mac's database step: the first
  database step after 334's comes after 405 (S0-6).
- No change to `deploy.py`'s comparison: that is 405's.
- Nothing runs by itself on a timer.

## Planned items

- [ ] The dispatcher's patterns, paths, shell and ten operations
- [ ] `through_fleet.py`'s two modes, `run` unchanged
- [ ] `remote.py deploy-step`
- [ ] The rule line and `update_remote.sh`
- [ ] The four test files, each check seen red
- [ ] The deploy skill's `SKILL.md` and `CHANGELOG.md`
- [ ] The regression of record, the close-out, the handoff and its step
- [ ] The pull request, for the operator to merge after review

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-19 | The plan, from Step 0 (K93). |
