
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
