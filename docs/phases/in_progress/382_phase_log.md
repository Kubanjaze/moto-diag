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
  `video_analyses` 5, `diagnostic_sessions` 7; 113 tables in all.
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
