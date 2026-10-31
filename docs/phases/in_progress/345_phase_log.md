
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
