---
name: deploy
description: Apply a migration to the live moto-diag database — the dry run on a copy, the diff the operator approves (written into the phase folder and committed), and the live apply that refuses without it. Use when a phase's migration must reach the live database (on the home desktop since Phase 382; live.json says where), or when asked to deploy, dry-run or back up the live database.
---

# deploy — one script from backup to live

Built in Phase 358 (K3) from Phase 262's `deploy262.py`. Seven data phases
had each rewritten this step in a scratchpad under `/private/tmp`, and the
diff the operator approved for migration 071 survived there only by luck.

## Where live is (Phase 382)

Live is on the home desktop (WSL2), at `~/motodiag/live/motodiag.db`, served
by `motodiag-api.service` on 127.0.0.1:8000 and reached over the tailnet
through `tailscale serve`, never the LAN. Each machine says where live is in
`~/.config/motodiag/live.json` (`MOTODIAG_LIVE_CONFIG` overrides it):

- the desktop: `{"live": "/home/lilcu/motodiag/live/motodiag.db"}`;
- the Mac: `{"live": null, "host": "desktop-76s9bqv"}`, or no file.

`live.py` reads it. Every mode refuses with **exit 4**, before touching
anything, when the file is missing, says `null`, or names a path that does
not exist; so on the Mac each mode refuses and names the host. Backups must
be outside a Windows drive (`/mnt/<letter>/`) and any cloud-synced folder
(OneDrive, iCloud, Dropbox, Google Drive), or every mode refuses.

**A deploy runs on the desktop, from its own checkout** (the operator's 1A,
Phase 382), **driven from the Mac** (Phase 384, the operator's 1A, 2A (i),
3A). The Mac reaches a fixed list of operations on the desktop over the
tailnet, through `remote.py`:

    python .claude/skills/deploy/remote.py status            # read only: live, checkouts, service, backups
    python .claude/skills/deploy/remote.py dryrun <phase>    # at HEAD, which must be clean and pushed
    python .claude/skills/deploy/remote.py fetch <phase> dryrun
    python .claude/skills/deploy/remote.py api-stop
    python .claude/skills/deploy/remote.py apply-live <phase>
    python .claude/skills/deploy/remote.py verify-live <phase>
    python .claude/skills/deploy/remote.py fetch <phase> live
    python .claude/skills/deploy/remote.py backup <label>
    python .claude/skills/deploy/remote.py server-pull       # after the merge; master only
    python .claude/skills/deploy/remote.py api-start         # or api-restart
    python .claude/skills/deploy/remote.py media-check       # every video through the file route, on a copy

- **The way in:** an SSH server inside Ubuntu, listening only on the
  tailnet address of `motodiag-ops`, a second Tailscale device in Ubuntu;
  keys only, from the Mac's tailnet address only, and the tailnet's rules
  let only the Mac reach its port 22. Installed once by the operator,
  `ops/desktop/install_remote.sh`.
- **The fixed list:** the key runs `ops/desktop/motodiag_remote.py`,
  installed root-owned as `/usr/local/libexec/motodiag-remote`, and nothing
  else: no shell, no file transfer, no forwarding. Each operation that runs
  repository code names the exact commit the Mac pushed; the desktop's
  checkout must be clean and is checked out detached at it. Each request is
  logged in the desktop's `~/motodiag/remote.log`. A change to the list
  reaches the desktop only by running the installer again.
- **The files the desktop writes** (the dry-run and live diffs) go to its
  outbox, `~/motodiag/outbox/`, never into its checkout; `fetch` brings
  each to the Mac's `in_progress/`, written only when its sha256 equals the
  desktop's. The Mac commits it, under its own guards. The desktop never
  commits.
- **The Mac's live.json names the way in:** `"remote": {"ssh":
  "lilcu@motodiag-ops", "key": "~/.ssh/motodiag_ops"}`. With no remote or
  no key, `remote.py` refuses with exit 4, as live.py does.
- **Each change to live still waits for the operator's scoped approval**
  in the phase log, and `apply-live` still refuses on its own terms below.
  A deploy now needs both machines up; the operator accepted that.
- **Not reachable through the list:** a phase script's own `migrate`
  callable (below, "A row change with no schema migration"). Such a phase
  needs an operation added to the list first, by a phase.

After the merge, the server's checkout follows master and the API restarts
(`server-pull`, then `api-restart`). Run by hand on the desktop, the same is:

    git -C ~/motodiag/server pull --ff-only
    sudo -n systemctl restart motodiag-api.service    # no password: ops/desktop/install_sudoers.sh

The unit starts with `--skip-migrations`: the migration reaches live only
through `apply-live`, never through a restart.

## The sequence

1. **Write the scope** as data:
   `docs/phases/in_progress/<phase>_deploy_scope.json`. Name every table
   the migration may touch, how many rows it adds or removes, and each
   existing row it may change. A row is found by a `where` clause that
   matches exactly one row before the migration, and it names the fields
   that may change. `fixtures/scope_262.json` is 262's scope in this form.
   An entry may also carry `"to": {field: value}`, the exact value the field
   must hold afterwards (Phase 359). Name every schema object the migration
   adds, removes or rewrites under `"schema"`, as
   `{"added": ["table workflow_runs", "index idx_wr_vehicle"]}`; any other
   schema change is a scope problem (Phase 357).
2. **`python .claude/skills/deploy/deploy.py dryrun <phase>`.** Live is
   only read. It then:
   - backs up to `~/backups/motodiag/` and keeps 5 (the operator, K27,
     2026-10-07: 5 now; 5 plus the first backup of each week once the
     first shop's real data is in);
   - migrates a copy in `data/deploy_scratch/` (gitignored, deleted after
     use) and diffs every table by rowid;
   - checks the scope and runs the F158 census on the copy;
   - **seed parity** (Phase 380, the operator's 2A): every `known_issues` row
     the migration adds or changes must equal the row with the same
     `row_key` in a fresh seed build at HEAD, every column but the id and
     the clocks, and a row it removes must be gone from that build (Phase
     381). A difference is a scope problem, so the seed and live cannot
     drift. `apply-live`'s own fresh run checks it again;
   - writes **`docs/phases/in_progress/<phase>_dryrun_diff.md`**, headed
     with the backup's path and sha256, the scope file's sha256, the
     census count and any scope problem. It ends with the **exact diff**
     as JSON: every field of every added or removed row, the before and
     after of every changed field, and the SQL of every schema object
     added or rewritten. A timestamp within a day of the run's own clock
     reads `<clock>`.
3. **Commit the diff and show it to the operator.** Changing an existing
   live row is a rule-1 stop. Wait for the operator's words.
4. **`deploy.py apply-live <phase>`, from the branch, after the regression
   of record** (Phase 378, K18: one order; the regression, the apply, the
   close-out commit, the merge). It refuses, before touching live, unless:
   - the phase log in `in_progress/` carries a regression line A5 can read
     as passing (0 failed, 0 errors, exit 0, only the pinned skips: F206,
     Phase 383),
     no code path changed between its commit and HEAD, and no code path is
     uncommitted (`fixtures/k18/` holds the known-bad logs);
   - the diff file exists, is committed and is unchanged;
   - the diff records no scope problem;
   - the backup still hashes as recorded, and the scope file is the one
     the diff was made with;
   - live still equals the backup, but for the columns the running API
     writes by itself (`SERVER_WRITES`: `api_keys.last_used_at`; F208, the
     operator's 2A, Phase 383). Each one set aside is printed and named in
     the live diff; any other change refuses. A field the approved diff
     names is never set aside. F210 records where the list stops holding,
     before onboarding (330);
   - a fresh dry run on a new copy stays in scope;
   - **that fresh run equals the committed exact diff, field for field**,
     clock values masked (F172, Phase 357). A diff file written before
     this check has no exact diff and is refused.

   It then migrates live, writes `<phase>_live_diff.md` and checks the
   scope and the equality again; the live diff says whether live equals
   the approved exact diff.
5. **`deploy.py verify-live <phase>`** (Phase 378, K25), read-only, any
   time after: it copies live and the phase's backup (opened immutable, so
   no `-shm` or `-wal` is left beside it) and prints the schema objects and
   tables that differ, whether that equals the approved exact diff, and
   live's integrity and foreign keys. It exits 3 when live does not equal
   the approved diff, and says when live's schema is past the phase's own
   migrations (F197, Phase 379); 1 on integrity or a foreign key; 2 with no
   deploy. verify_phase's check 8 calls it and fails on 1 or 3. It sets
   aside the `SERVER_WRITES` columns as apply-live does, and prints each
   one (F208). Where live is not, check 8 runs through the way in
   (`remote.py live-check`, the operator's (i), Phase 384) and fails on its
   failure, or with no way in.
6. **At close-out**, the diff files move to `completed/` with the phase
   documents, and so does the scope file.

## Backups, and a change with no migration

- **`deploy.py backup [label]`** (Phase 382) takes a backup-API copy of live
  into `~/backups/motodiag/motodiag_<label>_<time>.db`, keeps 5 and prints
  its sha256. The label defaults to `manual`.
- **A row change with no schema migration** (382's V-A rewrote 6 video
  paths) passes its own `migrate` callable to `deploy.dryrun` and
  `deploy.apply_live` from a phase script (`382_video_paths.py`); every
  refusal above still runs. The command line would apply no migration, so
  its fresh run would not equal the approved diff, and it refuses.
- **Exit codes:** 0 done or equal; 1 a scope problem, an integrity or a
  foreign-key failure; 2 refused (no approved diff, no deploy); 3 live does
  not equal the approved diff; 4 live is not on this machine.

## What it holds, and what it cannot

`tests/test_phase358_deploy_contract.py` runs every refusal on fixture
databases. Each refusal was broken on purpose and seen red.

- **It cannot see whether the operator approved.** It sees only that the
  diff is committed and unchanged. The approval is the operator's words,
  quoted in the phase log.
- **The scope is as good as the person who writes it.** A `where` clause
  that matches the wrong single row passes.
- **The clock mask has a ceiling.** A migration edited to write a
  different timestamp that also falls within a day of the run is not told
  apart. A fixed date is compared (`tests/test_phase357_deploy_exact.py`).
