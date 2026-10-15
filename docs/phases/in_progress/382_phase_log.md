# Phase 382 — Live and the backend on the home desktop — phase log

**Status:** 🚧 Step 0, stopped for the operator (2026-10-12)
**Branch:** `phase-382` (Opus session on DESKTOP-76S9BQV, WSL2 Ubuntu-26.04; the only writer)

---

### 2026-10-12 — Opened, Step 0, and the stop

The prompt is `docs/prompts/382_live_on_the_home_desktop.txt` (merged
`77755a4`). Row 382 went 🚧 before Step 0. Part 1's report is copied
verbatim as `382_part1_report.md`. `382_step0.md` re-measures what can be
measured from here; the Mac's half is its M1 block.

Decided at Step 0, without a stop:
- **The service runs `motodiag serve --skip-migrations`.** Without it,
  every restart applies pending migrations to live outside the deploy
  skill (`cli/serve.py`, Phase 191B). A test holds the unit file to it.
- **The server's packages equal the Mac's `pip freeze`.** The whole-tree
  command was red here only by F77 (FastAPI 0.143); with the Mac's
  recorded `fastapi 0.136.3` / `starlette 1.3.1` it passed (exit 0, 1674
  passed, 10 skipped). The full freeze comes from M1.
- **Live here sits outside every checkout:** `~/motodiag/live/motodiag.db`,
  served from its own checkout of `master` (`~/motodiag/server/`, own
  venv). A branch switch in the development checkout cannot change the
  code the server runs, and no `git clean` can reach live.
- **Backups stay at `~/backups/motodiag/`**, inside the WSL disk, which no
  cloud service syncs (OneDrive is rooted at `C:\Users\lilcu\OneDrive`).

The prompt asked for a stop at Step 0 with three questions. As put to the
operator:

**Q1. The cross-machine flow** (changes the deploy skill's rules).
- **1A, everything that touches live runs here (recommended).** The Mac
  builds; this machine runs K18's whole order: the regression of record,
  `dryrun`, `apply-live`, `verify-live`, `verify_phase.sh`, the close-out
  commit and the merge. The diff files are written in this checkout and
  reach the branch by commit and push from here; the Mac pulls with
  `--ff-only`. This venv (equal to the Mac's freeze) becomes the
  interpreter of record.
  - **Where live is:** each machine carries a local file,
    `~/.config/motodiag/live.json`. Here: `{"live":
    "/home/lilcu/motodiag/live/motodiag.db"}`. On the Mac: `{"live": null,
    "host": "desktop-76s9bqv"}`. The five tools read it. A missing file
    or a null path refuses with "live is on <host>", so a fresh clone
    anywhere fails closed. Tests use injected paths, as now.
  - **The Mac's `data/motodiag.db`** is frozen at the copy (`chmod 444`),
    renamed `data/motodiag_mac_retired_382.db`, and kept. A Mac dev
    database, when wanted, is built from the seed.
- **1B, split.** The regression of record stays on the Mac (the interpreter
  of record unchanged). Only `dryrun`, `apply-live` and `verify-live` run
  here. K18's hash check still works through git, but each data phase
  crosses machines twice (pull here for the dry run, push the diff, pull on
  the Mac, regression there, push, pull here for the apply). Same
  `live.json` mechanism; the Mac's copy as in 1A.
- **1C, the Mac reaches live remotely** (`deploy.py` runs its live steps
  through `tailscale ssh` to this machine). Nothing moves in the workflow,
  but it opens SSH on this machine and makes every deploy depend on two
  machines being up. Not recommended.
- **The Mac's copy, either way:** (i) rename and freeze, as above
  (recommended: once a shop's data is in, a stale copy at the old live
  path is a hazard); (ii) keep it in place as the Mac's dev database,
  guarded only by `live.json`.

**Q2. How the API starts at boot, with nobody signed in.** WSL2 can do it;
a WSL distribution starts only when a `wsl.exe` asks for it, so Windows
must ask at boot.
- **2A, a scheduled task (recommended):** "At startup", "Run whether the
  user is logged on or not", action `wsl.exe -d Ubuntu-26.04 --exec sleep
  infinity` (it holds the distribution up), with `.wslconfig`
  `vmIdleTimeout=-1` and `instanceIdleTimeout=-1`. Inside Ubuntu, systemd
  starts `motodiag-api.service` (127.0.0.1:8000, `--skip-migrations`,
  `Restart=always`). I try the task without a stored password first
  (S4U); if WSL will not start that way, it needs your Windows password
  stored in the task once (a credential: your hands).
- **2B, automatic sign-in** (`AutoAdminLogon`) and a logon task. Simpler,
  but the desktop sits signed in after every restart. Not recommended.
- **Where `tailscale serve` runs**, which decides the app's address:
  - **2-i, the Windows Tailscale already installed (recommended).** It is a
    Windows service, starts before sign-in, and is set to run unattended.
    It serves `https://desktop-76s9bqv.<tailnet>.ts.net` → `127.0.0.1:8000`
    through WSL's loopback relay, measured working while signed in. The
    restart proof shows whether the relay works with nobody signed in; if
    it does not, I come back with 2-ii.
  - **2-ii, Tailscale inside Ubuntu,** a second node (e.g.
    `motodiag-server`), serving Linux's loopback directly, with no relay.
    One more sign-in, and two Tailscale clients on one machine.
  - Either needs **HTTPS certificates enabled** on the tailnet (admin
    console, DNS → HTTPS), for the https address a Release build needs. If
    not on, that is a click of yours.

**Q3. How live's copy travels from the Mac.**
- **3A, Taildrop (recommended).** On the Mac: a backup-API copy, its
  sha256, `tailscale file cp <copy> desktop-76s9bqv:`. Here:
  `tailscale.exe file get` into a folder outside OneDrive, copied into
  Ubuntu, sha256 compared before anything opens it. End to end over the
  tailnet, no cloud, no new listener. The Mac's Tailscale has to be
  started for the tailnet checks anyway.
- **3B, a USB drive** by hand. No network at all; sha256 checked the same
  way.
- **Not offered:** git (public), a cloud folder, `scp` (it needs an SSH
  server here).

What M1 (read-only, in `382_step0.md`) gives, before the plan: the Mac's
freeze, schema and row counts, backups, and that nothing serves.

### 2026-10-12 — The push guard blocked the Step 0 push (recorded; the guard unchanged)

- **Git identity:** this machine had none. Set for this repository only
  (`git config user.name/user.email`), matching the history's author,
  `Kerwyn <kubanjaze@gmail.com>`. Step 0 committed as `b7ecbf9`.
- **The block:** `git push -u origin phase-382` was refused by
  `pre_push_guard.sh`: fast mode 2 failed, 1672 passed. Both failures
  assert on Rich-rendered CLI text that wrapped at about 38 columns:
  `test_phase244T_safety_wiring.py::…::test_a_warning_diagnosis_shows_its_alert`
  and `test_f86_recall_honesty.py::…::test_a_real_duplicate_is_still_idempotent`.
  The same command passed twice in this session, run from a shell
  with no `COLUMNS`.
- **Reproduced:** the two tests with `COLUMNS=38`: 2 failed; with 60, 79
  or unset: 2 passed. A 38-column pty without `COLUMNS` passes, so it is
  the variable, which the hook's environment carries from the operator's
  terminal. The suite's result depends on the width of the terminal it
  was started from.
- **Decided:** a defect in the test harness, to be fixed as bug fix #1
  after v1.0 (the conftest pins the width the suite already passes at).
  The guard is not loosened. Step 0 stays local until then.

### 2026-10-12 — The operator's picks, M1 from the Mac, the venv rebuilt

**The operator's words:** "1A(i), 2A + 2-i, 3A. HTTPS certificates are on."

**M1, run on the Mac by the operator** (output pasted into the session):
- `master...origin/master`, `77755a4`; Python 3.14.5; `fastapi 0.136.3`,
  `starlette 1.3.1`; `pip freeze` 92 lines (91 pins and the editable line).
- Live: schema 86 (`schema_version` holds 85 rows); `known_issues` 1057,
  `known_issue_makes` 1291, `known_issue_models` 2772, `api_keys` 26,
  `users` 4, `shops` 1, `customers` 6, `work_orders` 6, `videos` 6,
  `video_analyses` 5, `diagnostic_sessions` 7. (This line first said "113
  tables in all", a figure not counted; M3 counts 121.)
- `data/motodiag.db` 32301056 bytes, modified Oct 9 09:52; `-wal` 0 bytes.
- `launchctl list | grep -i moto` and `lsof … LISTEN | grep -i python`:
  nothing. Nothing serves on the Mac, as the prompt said.
- **Two gaps in M1:** `ls -lt ~/backups/motodiag/ | head -7` was cut at 7
  lines, so it shows 2 backups (pre381, pre380) and is not a count; and
  `zsh: command not found: tailscale` (the Mac app's CLI is not on PATH).
  M2 covers both.

**The venv rebuilt from the Mac's freeze.** Diffing the freeze against this
`.venv` showed wide drift, not only F77's pair: `anthropic` 1.13.0 here
against 0.109.1, `openai` 3.29.0 against 2.41.1, `reportlab` 5.0.1 against
4.5.1, and 13 packages the Mac does not have. The part-1 venv is kept as
`.venv_part1`; `.venv` is new (uv, CPython 3.14.5), installed from the
Mac's 91 pins and `pip install --no-deps -e .`. `pip check`: no broken
requirements; the freeze, less pip, equals the Mac's 91 lines (`diff`
empty). Under 1A this is now the interpreter of record.

**Decided, without a stop:**
- **sudo needs the operator's password here** (`sudo -n true`:
  "interactive authentication is required"; `Linger=no`). The API runs as
  a system unit with `User=lilcu`; installing it is one command block the
  operator runs.
- **Taildrop's landing folder is `C:\motodiag-inbox`**, outside the user
  profile (OneDrive is `C:\Users\lilcu\OneDrive`), and the file is copied
  from there into Ubuntu.

**A question M2 must answer first: live's media.** Uploads are stored
under `settings.data_dir` (`videos/`, `photos/`, `audio/`), and
`videos.file_path` stores the path. Live has 6 `videos` rows. If the
stored paths are absolute Mac paths, moving only the database leaves 6
rows pointing at files that are not here, and rewriting them is a live-row
change (rule 1). M2 reads the values on the Mac.

### Bug fix #1 — 2026-10-12 — the suite read the operator's terminal width

- **Issue:** the push guard refused the Step 0 push: fast mode 2 failed,
  `test_phase244T_safety_wiring.py::…::test_a_warning_diagnosis_shows_its_alert`
  and `test_f86_recall_honesty.py::…::test_a_real_duplicate_is_still_idempotent`,
  each asserting a phrase that Rich had wrapped at about 38 columns.
- **Root cause:** Rich sizes a console from `COLUMNS` before anything else.
  The hook's environment carries the operator's terminal width; a run from a
  shell without `COLUMNS` gets 80, because stdout is not a terminal. The
  suite's result depended on the terminal it was started from.
- **Fix:** `tests/conftest.py` sets `COLUMNS=80` at import, the width every
  run without it already passes at. The guard is unchanged.
- **Files:** `tests/conftest.py`; `tests/test_phase382_suite_width.py` (new,
  spawns pytest on the f86 test with `COLUMNS=38`).
- **Verified:** with `COLUMNS=38`, the two tests: 2 failed before the fix
  (conftest stashed), 2 passed after, serial and `-n 2`. The new test:
  1 passed with the pin, 1 failed with the pin stashed.
- **Commit:** the one that carries this entry.

### 2026-10-12 — The build: where live is, the server's files, the tests

- **`live.py`** (deploy skill): `where()` reads `~/.config/motodiag/live.json`
  (or `MOTODIAG_LIVE_CONFIG`) and refuses, exit 4, on a missing file, a null
  path ("live is on desktop-76s9bqv") or a path that does not exist;
  `unsynced()` refuses a backup folder on a Windows drive (`/mnt/<x>/`) or
  under a sync root (OneDrive, iCloud's Mobile Documents, CloudStorage,
  Dropbox, Google Drive).
- **The five tools:**
  - `deploy.py`: `LIVE` is gone; each mode resolves live at the call and
    `main` exits 4 on a refusal; `backup [label]` is new (backup API, 5
    kept, sha256 printed); `dryrun` and `backup` refuse a synced folder.
  - `verify_phase.sh` check 8 reads `live.py`'s path and fails on a refusal.
  - `census.py` (`live_db()`, and exit 4 from its command line unless a
    copy is named); `acquire.machine_names`; `orchestrate` refuses before
    any clone, since every batch snapshots live.
- **Decided: the test suite's 244H tripwire learns live's new path.**
  The tripwire and the redirect guarded only the checkout's
  `data/motodiag.db`, which is not live after the move. `conftest` now
  reads `live.json`: an explicit `MOTODIAG_DB_PATH` naming live is
  dropped and redirected, and the tripwire refuses it. On the Mac the
  file names no path, and nothing changes there.
- **`ops/desktop/`:** `motodiag-api.service` (127.0.0.1:8000,
  `--skip-migrations`, `User=lilcu`, `Restart=always`), `install_unit.sh`
  (the operator runs it with sudo), `wslconfig` (both idle timeouts off),
  `motodiag-wsl-boot.xml` (at boot, S4U, `wsl.exe -d Ubuntu-26.04 --exec
  /bin/sleep infinity`).
- **The edit guard blocked one command**: a Python script writing
  `tests/test_phase382_live_location.py`. The three edits were redone with
  the Edit tool. The guard is unchanged. (The `.claude/` scripts were
  edited by exact-string replacement, each asserted to occur once, and the
  diff was read back whole.)
- **Tests:** `test_phase382_live_location.py` 29 passed. The first run had
  2 failures, both mine: `live.py`'s docstring named the old path (the
  scan caught it; reworded), and the probe's conftest shim did not load the
  suite's conftest (now loaded with `-p conftest`).
- **Mutations: 19/19 red** (`382_mutate.py`, output in `382_mutate.out`).
- **Floor:** 10838 → 10868, +30 by a diff of collected ids against master
  `77755a4` (+30, -0).
- **Whole-tree caught two older fixtures** written against the old
  contract: `test_phase257_source_stage.py::…::test_the_flag_reaches_batch`
  (`orchestrate.main` now refuses without `live.json`; KeyError on the
  unreached batch) and `test_phase379_verify_live_fails.py::test_check_8_passes_when_equal_or_with_no_deploy`
  (check 8's fake skills folder had no `live.py`). Each fixture gains the
  piece the new contract asks for (a `live.json` naming a temp file; a
  `live.py` printing the fixture's path); no assertion changed. 91 passed.

### 2026-10-12 — The server's side, before live

- **Decided: the unit waits for live** (`ConditionPathExists`). With no
  database at its path, `serve` creates a fresh one. Enabled before the
  cut-over, a WSL restart would have made an empty live where the Mac's
  copy must land, before its sha256 check. Test and mutation O5 (red);
  the harness re-run: **20/20 red**.
- **`~/motodiag/server/`**: a clone of `master` at `77755a4`; `.venv`
  CPython 3.14.5 from the Mac's freeze plus `-e .`; `pip check` clean;
  freeze equal to the Mac's; `motodiag v0.6.0`. The phase adds no product
  code, so master's code is what serves.
- **`~/motodiag/live/`**: created empty, mode 700.
- **This machine's `live.json`** names `~/motodiag/live/motodiag.db`;
  `live.py` refuses (exit 4, "does not exist") until the copy lands.
- **`C:\Users\lilcu\.wslconfig`** written from `ops/desktop/wslconfig`
  (there was none). It takes effect at WSL's next start.

### 2026-10-12 — M2 from the Mac: live's videos hold absolute Mac paths

M2, run on the Mac by the operator (output pasted into the session):
- **Backups: 5** (`ls … *.db | wc -l`): pre375, pre376, pre380 (two), pre381.
  M1's two was its `head -7`.
- **The Mac's Tailscale CLI** is `/Applications/Tailscale.app/Contents/MacOS/Tailscale`,
  1.102.3.
- **`data/`** holds `videos/` (42M) and `serve.log`, besides the seed folders,
  `deploy_scratch/`, `library/` and eight `.fuse_hidden000000140000000N`
  files (not read; they are not live's).
- **All 6 `videos` rows store absolute Mac paths**, each file present:
  `/Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_{1,4,4,1,6,6}/{1..6}.mp4`.
- **The census of absolute paths:** every text column of every table,
  `like '%/Users/%'`: **6 cells, all `videos.file_path`**. Nothing else in
  live names the Mac.

So moving only the database leaves 6 rows naming files that are not on
the desktop. Rewriting them changes live rows: a rule-1 stop, put to the
operator with the cut-over's before-state.

### 2026-10-12 — The unit installed and the boot task registered (the operator)

Observed from here after the operator ran steps 1 and 2:
- `systemctl is-enabled motodiag-api.service`: `enabled`; status
  `inactive (dead)`: live is not there, so `ConditionPathExists` holds it.
- Task `\motodiag\wsl-boot`: State `Running`, LogonType **S4U**, UserId
  `lilcu`, LastRunTime 23:49:19, LastTaskResult 267009 (0x41301, "the task
  is currently running"). Its `/bin/sleep infinity` is PID 25092, started
  23:49:18, parent WSL's `/init`, not this session. **WSL starts under
  S4U: no password stored.** Whether it does so with nobody signed in is
  the restart proof.

### 2026-10-13 — V-A, M3's before-state, and the stop for the cut-over

**The operator's words:** "V-A." (with M3's output).

**M3, run on the Mac at 2026-10-13 00:05 EDT** (output pasted):
- The Mac's Tailscale started: the tailnet lists the Mac, the desktop and
  the phone; `tailscale ping desktop-76s9bqv`: pong via DERP(nyc), 681 ms,
  "direct connection not established".
- The backup-API copy `~/382_cutover/motodiag_before.db`: schema 86,
  integrity ok, 0 foreign-key violations, **121 tables, 5801 rows**
  (`known_issues` 1057, `known_issue_models` 2772, `known_issue_makes` 1291,
  `api_keys` 26, `users` 4, `shops` 1, `customers` 6, `work_orders` 6,
  `videos` 6, `schema_version` 85, …; the non-empty tables are listed in
  the output).
- Each of the 6 video files' sha256 equals its row's `sha256`: True ×6.
- The copy: 32301056 bytes, **sha256
  `7c302011e3cff0a8acbd95ecb61d96f2e438f2a69d879daa6fe81c0390b12eed`**.
- `videos.tar`: 6 mp4, **sha256
  `665f8528e9bc89e4fb091cf31945911b6b9beec7e7f9deb2d619e4f7133db6f4`**.

**Filed F205** (media rows store the receiving machine's absolute path),
before any document cites it.

**Decided:** `ops/desktop/install_sudoers.sh` lets `lilcu` start, stop and
restart `motodiag-api.service`, and nothing else, without a password, so
the deploy skill's restart after a merge needs no password at the
keyboard. `visudo -cf` checks the rule before it is installed. A test pins
the three commands; mutation O6 (a wildcard verb) is red; the harness is
21/21 red. The floor 10868 → 10869 (that test).

**The tailnet name** is `desktop-76s9bqv.taila45995.ts.net` (MagicDNS on);
the Windows Tailscale has no serve config yet.

M4 (the cut-over, in `382_mac_steps.md`) waits for the operator's word.

## 2026-10-14 23:43 EDT — the operator's word on the cut-over

The operator, in their own words: **"cut over"**. This grants rule 1's
stop for the cut-over as the prompt scoped it: the Mac stops being live and
this machine starts; no rows change; the Mac's `data/motodiag.db` is kept
(M4 renames it to `data/motodiag_mac_retired_382.db`). The video-path
rewrite (V-A) is a separate row change and still needs its own approval of
the committed diff.

**Guard block (2026-10-14 23:50 EDT):** the push guard refused a command
that ran `git commit` and `git push` together ("it would push a commit it
never saw"). Run as separate commands; the guard is unchanged.

## 2026-10-14 23:57 EDT — M4: the Mac stopped being live; the Taildrop failed

M4's output (pasted): "unchanged since M3: True" (both copies
`7c3020…2eed`); live renamed to `data/motodiag_mac_retired_382.db` with
`-shm`/`-wal`; the Mac's `live.json` written. The transfer: "warning:
desktop-76s9bqv is not replying; trying anyway", `502 Bad Gateway`, 0 bytes;
"sent" printed only because M4's `echo` was not chained to `file cp` (my
error in M4; M4b chains it). **From 23:57 neither machine is live: the API
is down until the desktop starts.**

Looked at here, 2026-10-15 00:0x: Windows Tailscale up (`WantRunning`,
`ForceDaemon` true, `ShieldsUp` false); its peer API listens on
100.75.113.50:41476 and the v6 address; the firewall's Tailscale rules
allow inbound; `file cp --targets` lists the Mac; `tailscale ping` to the
Mac answers **directly** (10.0.0.147:41641, 103 ms), where M3's went
through DERP. Not reproduced; M4b retries with a probe file first.

## 2026-10-15 00:01–00:06 EDT — M4b failed the same way; the desktop pulls instead

M4b (pasted): `tailscale ping` direct over 10.0.0.55:41641 in 3 ms, then
"not replying" and `502 Bad Gateway`, 0 bytes. Measured here: the
desktop's peer API answers itself at 100.75.113.50:41476 (GET 200, a PUT of
`selftest.txt` 200; no file from it reached the inbox); the firewall has no
inbound block rule, and its Tailscale rules allow any port; a Taildrop **from
the desktop to the Mac** (`probe-out.txt`) exits 0. So the Mac cannot open a
connection into the desktop's peer API, while the desktop's outbound
connections work. The cause is not found; the Mac's own `curl` of the peer API
(M4c's first line) will say whether any inbound TCP gets through.

**Decided:** the transfer no longer waits on Taildrop. M4c serves the two
files on the Mac's tailnet address only (100.80.109.103:8382, `http.server`
bound to that address; WireGuard-encrypted, not the LAN, not Funnel, not a
cloud folder, not git), and the desktop pulls them with `curl.exe` through
Windows' tailnet route. The receiving check (`382_receive.py`) is unchanged:
nothing is placed unless both sha256 values equal M3's.

**Note for the API proof:** the API goes through `tailscale serve`, which
tailscaled answers itself, not through a Windows listener. Whether that is
also blocked inbound is measured, not assumed, before and after it is turned on.

**The operator, 2026-10-15 ~00:07 EDT, in their own words:** "Switch the
transfer: I'm serving ~/382_cutover from the Mac with python3 -m http.server
8382 --bind 100.80.109.103, bound to the tailnet address only. Pull
motodiag_before.db and videos.tar … into C:\motodiag-inbox, run your
receiving check (sha256 against M3's), and tell me when to stop the server.
Log the change of transfer method." (The operator serves `~/382_cutover`
itself, not M4c's `send/` folder; the pull takes only the two names.)

First pull, 00:08: `http://100.80.109.103:8382/` timed out from Windows
(8 s, 0 bytes); ICMP to 100.80.109.103 timed out; the Mac's peer API
(tailscaled's own listener, :38579) answered 200. So the tunnel works, and
what the Mac's OS answers itself does not: the macOS application firewall
is the likely block (python3 not yet allowed). Asked the operator to allow
it, or to front the server with the Mac's `tailscale serve` (tailnet-only).

**Guard block again (00:10 EDT):** the same push-guard refusal as at 23:50
(commit and push in one command), my repeat; run separately, guard unchanged.

**Correction, 00:10 EDT.** The operator's server log (00:05–00:07: six GETs
of `videos.tar`, five broken pipes, no request for the database) shows the
pull **did** reach the Mac. The repeated GETs were my poller: it asked for
byte 0 of `videos.tar` with a 5 s limit, `http.server` ignores ranges and
sends the whole file, so each poll was cut off and repeated. The "likely
macOS firewall" note above was wrong for that window. Stopped the poller.
A direct pull at 00:09 then failed: the database reset after 19 s with 0
bytes, `videos.tar` and `/` timed out connecting, while `tailscale ping`
(direct, 5 ms) and the Mac's peer API (200) answered. Inbox still empty.

## 2026-10-15 ~00:15 EDT — the operator rolled the cut-over back; paused until a USB transfer

The operator, in their own words (pasted): "Rolled back for tonight. Live is
back on the Mac as data/motodiag.db (mode 644, sha256 7c302011...
unchanged), live.json is removed, http server stopped. Nothing was running
on the Mac before tonight, so nothing was restarted." "Transfer status:
NOTHING verified on Windows." The HTTP route saw "14 GETs for videos.tar and
2 for motodiag_before.db, almost all cut off mid-transfer about 15s in —
looks like a client-side timeout on the Windows fetch. Any partial files …
should be deleted, not trusted." The payload stays in `~/382_cutover` on the
Mac (`motodiag_before.db` and `motodiag_at_cutover.db` identical,
`7c3020…`; `videos.tar` `665f85…`, built with `COPYFILE_DISABLE=1`). "Next
session: cut over by USB (3B). Separately: figure out why Taildrop 502s on
the Windows peer and why the Windows fetch has a ~15s cutoff before trying
the network route again."

**Live is on the Mac again from ~00:15; the outage ran from 23:57.** No row
changed on either machine.

Checked here: no partial file anywhere: `C:\motodiag-inbox` holds only the
boot task's XML; nothing named `motodiag_before*` or `videos.tar*` under
`C:\Users\lilcu` (depth 3, Downloads included); `~/motodiag/live/` is empty;
`motodiag-api.service` inactive (enabled, held by its
`ConditionPathExists`). My poller wrote to `NUL`, and the curl pulls
wrote nothing (exit 56 and 28).

**On the ~15 s cutoff, what my side ran:** the poller used `-m 5`, and the
direct pull used `--connect-timeout 15`, which limits only the connect, not
the transfer. Neither explains a cut at ~15 s on a transfer that had
started, and some of the 16 GETs were not mine. That is open, with the
Taildrop 502, for the next session to measure before the network route is
tried again.

**Decided:** the row stays 🚧, with "Paused 2026-10-15" and the reason in
its text. `roadmap_check.py` R3 refuses ⏸️ while the phase's documents
are in `in_progress/` (⏸️ is for an archived record), and the phase resumes
from here. The check is unchanged.

**For the next session (3B, USB):** the Mac has no `live.json` and still
runs master, which does not read one, so nothing refuses there until this
branch merges. The cut-over is repeated in full (a fresh M3-style
before-state and sha256, since live has been live again since ~00:15),
and the operator's word is asked again: tonight's "cut over" was for
tonight's attempt.
