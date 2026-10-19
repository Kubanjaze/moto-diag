# Phase 382 — Live and the backend on the home desktop

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-19 (v1.0 2026-10-12)

## Goal

Live moves once, from the Mac (which sleeps) to the home desktop, and gets
its first always-on server. The operator's picks, 2026-10-12: "1A(i), 2A +
2-i, 3A. HTTPS certificates are on." So:
- everything that touches live runs on the desktop (1A);
- the Mac's copy is frozen, renamed and kept (i);
- a scheduled task starts WSL at boot, systemd starts the API, and the
  Windows Tailscale serves it to the tailnet (2A, 2-i);
- live's copy travels by Taildrop, sha256 checked (3A). It did not: Taildrop
  failed, and the copy came by USB, the operator's 3B (Deviations).

v1.1: all of it shipped. Live has been on the desktop since 2026-10-19,
served from loopback to the tailnet, with the six video paths rewritten
(V-A) and every proof seen failing, then passing.

## Logic

### Where live is: `~/.config/motodiag/live.json`, per machine

`.claude/skills/deploy/live.py`, one function, `where()`:
- reads `~/.config/motodiag/live.json`, or the file
  `MOTODIAG_LIVE_CONFIG` names (tests);
- returns the path in `"live"`;
- **refuses** (`LiveElsewhere`, exit 4 from its command line) when the file
  is missing, when `"live"` is null ("live is on <host>"), or when the path
  does not exist. A fresh clone anywhere fails closed.

The desktop's file: `{"live": "/home/lilcu/motodiag/live/motodiag.db"}`.
The Mac's: `{"live": null, "host": "desktop-76s9bqv"}`.

The five tools read it instead of `data/motodiag.db`:
- `deploy.py` (`dryrun`, `apply-live`, `verify-live`): live resolved at the
  call, a refusal exits 4 before anything is read or written. Tests inject
  `db=` as now.
- `verify_phase.sh` check 8: the schema line and `verify-live` read the
  resolved path; a refusal fails the check.
- `source-transmission`: `census.py`'s default, `acquire.machine_names`'s
  default, `orchestrate.make_run`'s snapshot and its census call. An
  explicit database argument to `census.py` still works.

### Backups

`deploy.py backup` (new): a backup-API copy of live to
`~/backups/motodiag/motodiag_<label>_<stamp>.db`, its sha256 printed, 5
kept by the existing `retain`. It prints the cut-over's before-state copy
and gives the server's first backup here.

The backup folder is refused if it resolves under a Windows drive
(`/mnt/<letter>/`) or under a known sync root (`OneDrive`, `iCloud`,
`Library/Mobile Documents`, `Dropbox`, `Google Drive`). Here it is
`~/backups/motodiag/` on the WSL disk.

### The server

- **Code:** its own clone of `master`, `~/motodiag/server/`, with its own
  `.venv` from the Mac's freeze (`docs/phases/…/382_mac_freeze.txt`) and
  `pip install --no-deps -e .`.
- **Data:** `~/motodiag/live/` holds `motodiag.db`, and is the server's
  `data_dir`, so uploads land beside live.
- **Unit:** `ops/desktop/motodiag-api.service`, a system unit,
  `User=lilcu`, `Restart=always`. It runs `motodiag serve --host 127.0.0.1
  --port 8000 --skip-migrations` with `MOTODIAG_DB_PATH` and
  `MOTODIAG_DATA_DIR` set, and `EnvironmentFile=-~/.config/motodiag/server.env`
  (mode 600) for the keys the operator adds. Without `--skip-migrations`,
  every restart would migrate live outside the deploy skill.
- **Boot:** `ops/desktop/motodiag-wsl-boot.xml`, a Task Scheduler task:
  at startup, whether or not anyone is signed in, `wsl.exe -d
  Ubuntu-26.04 --exec sleep infinity`. Tried first without a stored
  password (S4U); if WSL will not start that way, the operator stores the
  password once. `.wslconfig` turns the idle timeouts off.
- **Tailnet:** the Windows Tailscale, `tailscale serve --bg
  http://127.0.0.1:8000`, so `https://desktop-76s9bqv.<tailnet>.ts.net`.
  No Funnel; nothing on the LAN.
- **After a merge:** `git -C ~/motodiag/server pull --ff-only`, then a
  restart. The deploy skill gains this as its last step.

### The move (3A), and the cut-over (rule 1)

1. Before-state on the Mac: schema, row counts, `deploy.py backup` style
   copy with its sha256 (commands given).
2. The operator's word.
3. The Mac: the backup-API copy, `chmod 444 data/motodiag.db`, rename to
   `data/motodiag_mac_retired_382.db`, its `live.json` written, `tailscale
   file cp` to `desktop-76s9bqv`.
4. Here: `tailscale.exe file get C:\motodiag-inbox`, copied to
   `~/motodiag/live/motodiag.db`, sha256 equal to the Mac's, **before the
   API first opens it**; then the unit starts.
5. Media: as M2 shows (see the log).

As built (v1.1): steps 3–4 by USB into `C:\motodiag-inbox`, the operator's
3B, after Taildrop and a tailnet pull both failed and the operator rolled
back once. `382_receive.py` checks both files against M3's sha256 (with a
one-byte-flipped control), each video against its row, and places live at
mode 600 before the unit first opens it. The six `videos.file_path` values
then named the Mac's folder; they were rewritten by a dry run, an approved
diff and `apply-live` (V-A, `382_video_paths.py`, `382_deploy_scope.json`).

## Proofs, each seen failing once

| claim | the check | seen failing by |
|---|---|---|
| back by itself after a restart, nobody signed in | from the Mac, `curl https://desktop-76s9bqv…/healthz` after a Windows restart with nobody signing in | a restart before the task is registered |
| answers over the tailnet | the same `curl`, from the Mac | before `tailscale serve` is set |
| not from the home network | from the Mac, `curl`/`nc` at `10.0.0.55:8000` and `:443` must fail | a LAN port that is open answers the same probe (positive control) |
| backups land here, 5 kept, unsynced | `deploy.py backup`; the tests | a planted sync-root folder is refused |
| every tool knows where live is | `tests/test_phase382_live_location.py`; on the Mac after the merge, each mode exits 4 | the tests against the old fixed path |
| live here equals the Mac's copy | `sha256sum` on both sides, before the first open | the same check on a copy with one byte changed |
| the app reaches the new address | Settings → Server on the phone; the app checks `/healthz` before saving | the LAN address, refused by the same screen |

## Tests

`tests/test_phase382_live_location.py`:
- `where()`: the desktop file, a null with a host, a missing file, a
  missing path;
- `deploy.py` each mode, `census`, `acquire`, `orchestrate`: refuse on the
  Mac's file, before touching anything;
- `verify_phase.sh` check 8 fails on a refusal;
- `backup`: 5 kept, sha256 printed, a sync-root folder refused;
- the unit file: `--skip-migrations`, `127.0.0.1`, no `0.0.0.0`; the task
  XML: at startup, not interactive-only.

Plus bug fix #1 (the suite's width): see the log.

v1.1: `tests/test_phase382_suite_width.py` holds bug fixes #1–#3 (a narrow
terminal; a width set after import; three workers, three default
databases). `382_mutate.py` breaks 23 things, each seen red.

## Non-goals

- Anything beyond the tailnet: Stripe's endpoint is 371's.
- K27's weekly copy (after a shop's real data); offsite backups (345).
- The mobile repository: the app's address is set in Settings, no build.
- F77's floors, beyond this machine matching the Mac.

## Planned items

- [x] `live.py` and the five tools
- [x] `deploy.py backup`, the sync-root refusal
- [x] the unit, the task, `.wslconfig`, `tailscale serve`
- [x] the deploy skill, its changelog, CLAUDE.md's dated line
- [x] tests, mutations, the floor
- [x] the move and the cut-over (rule 1)
- [x] the proofs
- [x] regression of record (on the Mac, not here: Deviations), V-A applied,
  close-out, handoff; the merge and verify_phase follow this commit
- [x] once on the Mac after the merge: the refusals, handed to the operator
  with the merge (its result goes in the handoff)

## Deviations

- **The transfer.** 3A's Taildrop failed twice with a 502 into the
  Windows peer, and a tailnet `http.server` pull cut off at ~15 s; the
  operator rolled live back on the Mac (2026-10-15) and cut over by USB
  (3B, 2026-10-19). Neither failure is explained (handoff).
- **V-A, a live row change the plan did not list.** The six
  `videos.file_path` values held the Mac's absolute paths. Rewritten under
  the operator's words, "only the 6 videos.file_path values change", by the
  deploy skill with no migration (`dryrun`/`apply_live` gained a `migrate`
  callable). verify-live: `videos +0 ~6 -0`, the approved diff exactly.
- **The regression of record ran on the Mac**, the operator's A. The
  desktop has no `osacompile`, no `ffmpeg` and no Subconscious profile, so
  4 tests cannot pass here. Live's deploys run here; a full regression here
  needs those three first.
- **Three bug fixes in the test suite**, one shared cause: the suite
  inherited its environment (the terminal width; a width fixed at import;
  the controller's database path in every worker). Each held on the Mac by
  circumstance.
- **F206 and F207 filed.** A failing regression line would satisfy A5 and
  `apply-live`'s precondition (F206). The app cannot play a backend-only
  video (F207), so M6 proved the app's address and the backend's `/file`
  route separately (`382_video_serve.py`).
- **`MOTODIAG_PUBLIC_BASE_URL` left unset**: the tailnet name is the only
  address that reaches the server, and the Host fallback gives it.
- **Live's file sha256 moves under use**: the API writes
  `api_keys.last_used_at` on each request. The backup and verify-live
  compare rows, so nothing depends on the file hash after the receive.

## Results

- **Live:** `~/motodiag/live/motodiag.db` on DESKTOP-76S9BQV, schema 86,
  sha256 `7c302011…2eed` on arrival, equal to the Mac's M3 copy. The Mac's
  is retired as `data/motodiag_mac_retired_382.db`, kept.
- **V-A:** backup `motodiag_pre382_20261019_145601.db` (`07e8fcc7…`);
  after, 5801 rows, 121 tables, integrity and foreign keys ok; all six
  files exist; videos 2–6 served by `/file` with matching sha256 (1 is
  soft-deleted).
- **The server:** `motodiag-api.service` on `127.0.0.1:8000`,
  `--skip-migrations`; `tailscale serve` at
  `https://desktop-76s9bqv.taila45995.ts.net`, tailnet only; the boot task
  in S4U; Tailscale unattended.
- **Proofs:** all seven seen failing, then passing (the log's table).
- **Tests:** `test_phase382_live_location.py`,
  `test_phase382_suite_width.py`; mutations **23/23 red**; the floor
  10871.
- **Regression of record:** 10870 passed, 0 failed, 1 skipped at
  `74e3599`, on the Mac (27 min 21 s, `python -m pytest -n auto --dist
  load`, exit 0).
