# Phase 345 — phase log: Cloud backup + sync

**Status:** Complete

Built 2026-10-31 by the Chief Engineer in a fresh clone of
`phase-345-cloud-backup-sync`, inside the fleet's fence, the only writer.
The plan is `345_implementation.md` v1.0, approved on issue #45. No bug
fixes.


## 2026-10-31: The operator's answers to the Chief Engineer's stop

> My answers to the Chief Engineer's stop on 345: go with your picks. 1: the passphrase was generated on the home desktop, a copy is kept by the operator, and it is in ~/.config/motodiag/backup.env as MOTODIAG_BACKUP_PASSPHRASE (mode 600); it is not in this answer. 2: keep every nightly copy forever; nothing offsite is deleted. 3: the private Backblaze bucket and its bucket-only application key exist, and backup.env holds MOTODIAG_BACKUP_S3_ENDPOINT, MOTODIAG_BACKUP_S3_BUCKET, MOTODIAG_BACKUP_S3_KEY_ID and MOTODIAG_BACKUP_S3_SECRET. Nightly at 03:00 desktop time is fine.

## 2026-10-31: The Chief Engineer reads the operator's answers (item 1)

The heading above is on the branch (`15c8449`), so the Engineer does not
stop again and goes to item 2. The operator's words, applied literally:

- "go with your picks": the Captain's three picks stand, as below.
- **1, the passphrase:** it is in `~/.config/motodiag/backup.env` as
  `MOTODIAG_BACKUP_PASSPHRASE`, mode 600, beside the four K62 names. Item
  2 reads it from that file, under that name, and from nowhere else; no
  command takes it as an argument. The Captain's pick, kept.
- **2, offsite retention:** "keep every nightly copy forever; nothing
  offsite is deleted." Nothing in this phase deletes an object from the
  bucket: the store has no delete call. The Captain's pick, kept.
- **3, the account:** the bucket, its bucket-only key and the four names in
  `backup.env` exist. The live proof in item 9 rests on this.
- **The nightly time:** "Nightly at 03:00 desktop time is fine." The timer
  is `OnCalendar=*-*-* 03:00:00`. The Captain's pick, kept.

## 2026-10-31: Items 2–4 built (`cb1420d`)

- `backup/settings.py`, `backup/crypt.py`, `backup/store.py`, and
  `tests/support/phase345.py` (the fake S3 transport and the in-memory
  store). 55 tests.
- The two SigV4 known-answer tests reproduce AWS's published signatures
  on the first run, with no change to either side: the object GET
  `f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41`, the
  listing `max-keys=2&prefix=J`
  `34b48302e7b5fa45bde8084f4b7868a86f0a534bc59db6670ed5711ef69dc6f7`.
- Decided: `decrypt_file` refuses a header cost outside 2**10–2**22 before
  deriving a key, so a changed cost byte cannot make it allocate gigabytes
  before the tag fails. Recorded in v1.1's Deviations.
- Decided: the default urllib transport is tested against an HTTP server
  on 127.0.0.1, which `network_guard` allows; the real bucket is reached
  only by the operator's run after the merge.
- `wholetree.sh`: exit 0, 2561 passed, 10 skipped (120.2 s).

## 2026-10-31: Items 5–8 built

- `backup/snapshot.py`, `backup/restore.py`, `cli/backup.py` (registered
  in `cli/main.py` after `audit`), the service, the timer, the installer,
  the `backup` extra in `server`, `docs/guide/backups.md` and the install
  guide's pointer. 52 more tests.
- Found by the first run of the new tests, before any commit: a copy made
  from live by the backup API keeps live's WAL mode, so reading it (the
  integrity check, a restore's check) left `-wal` and `-shm` files beside
  it, and a `-wal` file can hold plaintext pages. `copy_database` now
  switches the copy to `journal_mode=delete`; the two tests that saw it
  (no plaintext left in the work folder; `--db-only` restores exactly one
  file) pass.
- Decided: the guide tells the operator to set the service's two names
  (`MOTODIAG_DB_PATH`, `MOTODIAG_DATA_DIR`) before any command, because
  without them `backup run` copies the settings' default database and
  `restore` cannot tell which folder is live's.
- The docs-drift control: with `docs/guide/backups.md` on `BACKEND_DOCS`,
  a planted fenced line `motodiag backup prune` turned
  `tests/test_phase208_docs.py` red ("`backup` has no subcommand
  'prune'", 1 failed, 19 passed); with the line removed, 20 passed.
- `COLLECTED_TEST_FLOOR` 12184 → 12291, by a diff of collected ids against
  the branch's base `2df4799`: +107 −0, all in the five
  `test_phase345_*.py` files.

## 2026-10-31: The mutations, 8/8 red (committed after `47f0a78`)

`docs/phases/in_progress/345_mutate.py`, each mutation reverted on its own;
its output is `345_mutate.out`: the tag check removed, the host header
unsigned, the media skip inverted, `pick` after `at`, the over-live refusal
removed, the mode check removed, the manifest before the database, and a
folder with no manifest listed. All eight red. The first run stopped at M2
because its text occurred twice in `store.py` (the harness asserts once);
the string was anchored on the call in `_request`, and the rerun was 8/8.

## 2026-10-31: The regression of record

`wholetree.sh --full` on `c2b0767`: exit 0, "PASSED — 5056 passed, 36 skipped" (1009.2 s wall), record written for that commit. Then `regression.sh` on the clean tree, its lines as printed:

Regression of record: 12186 passed, 0 failed, 105 skipped, 0 errors at `c2b0767` (35 min 23 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:259: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:272: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:292: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:306: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:321: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:333: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:340: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:438: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:445: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:464: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_orchestrator_guards.py:85: inside the fleet's fence: no Subconscious login there (K42)
Skipped in the regression of record: [2] tests/test_phase257_orchestrator_guards.py:149: inside the fleet's fence: osacompile is macOS-only
Skipped in the regression of record: [4] tests/test_phase257_sandbox_boundary.py:72: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:80: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:87: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:93: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:106: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:112: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:119: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:125: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:131: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:104: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:121: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:137: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:145: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:153: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:162: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:175: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:185: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:218: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:223: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:248: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [7] tests/test_phase388_fence_boundary.py:221: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:235: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:244: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:280: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:287: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:291: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:295: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:303: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:316: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:325: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:330: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:338: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:344: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:350: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:354: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:360: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:131: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:139: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:148: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:159: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: inside the fleet's fence: its boundary is proven from the host, not from inside
Line coverage of record: 87.92% at `c2b0767` (the pin is 87.50%)

## 2026-10-31: Close-out

v1.1 written, the phase's files moved to `docs/phases/completed/`, the
ROADMAP row closed, the root `phase_log.md` pointer and the handoff
`docs/handoffs/2026-10-31_345_closed.md` written. The live proof against
the real bucket is the operator's run on the home desktop after the merge,
in the handoff; the fence has no network.

## Refuter pass

| claim | verdict | quote | source | round · kind · outcome |
|---|---|---|---|---|
| Items 2–4 added 55 tests | kept | "test_phase345_backup_settings.py (24), test_phase345_cli.py (26), test_phase345_crypt.py (13), test_phase345_snapshot_restore.py (26), test_phase345_store.py (18). Measured: 12291." | tests/test_phase255B_collected_test_floor.py p. 469 | 1 · none · kept |
| Items 5–8 added 52 more tests; 107 in five files | kept | "the branch's base 2df4799 (12184): +107 -0. Added:" | tests/test_phase255B_collected_test_floor.py p. 468 | 1 · none · kept |
| Collected floor 12184 → 12291 | kept | "COLLECTED_TEST_FLOOR = 12291" | tests/test_phase255B_collected_test_floor.py p. 473 | 1 · none · kept |
| Regression of record 12186 passed, 105 skipped at c2b0767 (passed + skipped equals the floor) | kept | "Regression of record: 12186 passed, 0 failed, 105 skipped, 0 errors at `c2b0767`" | docs/phases/completed/345_phase_log.md p. 90 | 1 · none · kept |
| SigV4 GET known answer f0e8bdb8…bdb41 reproduced | kept | "assert _sig(auth) == \"f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41\"" | tests/test_phase345_store.py p. 45 | 1 · none · kept |
| SigV4 listing known answer 34b48302…dc6f7 reproduced | kept | "assert _sig(auth) == \"34b48302e7b5fa45bde8084f4b7868a86f0a534bc59db6670ed5711ef69dc6f7\"" | tests/test_phase345_store.py p. 52 | 1 · none · kept |
| Mutations 8/8 red | kept | "8/8 red" | docs/phases/completed/345_mutate.out p. 9 | 1 · none · kept |
| backup registered in cli/main.py after audit, before completion | kept | "register_backup(cli)" | src/motodiag/cli/main.py p. 921 | 1 · none · kept |
| The store has no delete call; nothing offsite is deleted | kept | "There is no delete: nothing offsite is ever removed (the operator's answer at 345's stop)." | src/motodiag/backup/store.py p. 5 | 1 · none · kept |
| decrypt_file refuses a header cost outside 2**10 to 2**22 | kept | "if not 10 <= log2_cost <= 22:" | src/motodiag/backup/crypt.py p. 110 | 1 · none · kept |
| A version other than 1 is refused | kept | "raise BackupTampered(f\"unknown backup format version {version}\")" | src/motodiag/backup/crypt.py p. 96 | 1 · none · kept |
| The database copy is switched out of WAL mode | kept | "target.execute(\"pragma journal_mode=delete\")" | src/motodiag/backup/snapshot.py p. 104 | 1 · none · kept |
| A restore refuses a manifest path that leaves the target folder | kept | "raise BackupTampered(f\"the manifest names a path outside the folder: {entry.path}\")" | src/motodiag/backup/restore.py p. 165 | 1 · none · kept |
| work_dir() takes no argument and is created mode 700 | kept | "folder.mkdir(parents=True, exist_ok=True, mode=0o700)" | src/motodiag/backup/settings.py p. 127 | 1 · none · kept |
| The key file's parser removes one pair of matching quotes | kept | "if len(value) >= 2 and value[0] == value[-1] and value[0] in \"\\\"'\":" | src/motodiag/backup/settings.py p. 72 | 1 · none · kept |
| The timer names its unit; 03:00; Persistent | kept | "Unit=motodiag-backup.service" | ops/desktop/motodiag-backup.timer p. 10 | 1 · none · kept |
| The service has ConditionPathExists on backup.env | kept | "ConditionPathExists=/home/lilcu/.config/motodiag/backup.env" | ops/desktop/motodiag-backup.service p. 17 | 1 · none · kept |
| The server extra installs backup | kept | "\"motodiag[api,ai,vision,push,backup,reports,payments]\"," | pyproject.toml p. 85 | 1 · none · kept |
| backups.md is on BACKEND_DOCS under a Phase 345 comment | kept | "REPO_ROOT / \"docs\" / \"guide\" / \"backups.md\"," | tests/test_phase208_docs.py p. 50 | 1 · none · kept |
| The handoff block restores into a dated folder and checks with the server's Python | kept | "TO=~/motodiag/restore_check_$(date +%Y%m%d_%H%M%S)" | docs/handoffs/2026-10-31_345_closed.md p. 103 | 1 · none · kept |
| The handoff block checks the server's venv loads the new package | kept | "\"$SRV/.venv/bin/python\" -c \"import cryptography, motodiag.backup.crypt\"" | docs/handoffs/2026-10-31_345_closed.md p. 86 | 1 · none · kept |
| The operator's answers kept all three Captain's picks | kept | "My answers to the Chief Engineer's stop on 345: go with your picks." | docs/phases/completed/345_phase_log.md p. 13 | 1 · none · kept |
| ROADMAP row closed with CLOSED date and regression line | kept | "**CLOSED 2026-10-31.**" | docs/ROADMAP.md p. 622 | 1 · none · kept |
| Deviations cover every departure from the plan's signatures | killed | "clock: Callable[[], datetime] \| None = None) -> None:" | src/motodiag/backup/store.py p. 147 | 1 · wording · open |
