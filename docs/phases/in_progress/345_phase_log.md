
## 2026-10-31: The operator's answers to the Chief Engineer's stop

> My answers to the Chief Engineer's stop on 345: go with your picks. 1: the passphrase was generated on the home desktop, a copy is kept by the operator, and it is in ~/.config/motodiag/backup.env as MOTODIAG_BACKUP_PASSPHRASE (mode 600); it is not in this answer. 2: keep every nightly copy forever; nothing offsite is deleted. 3: the private Backblaze bucket and its bucket-only application key exist, and backup.env holds MOTODIAG_BACKUP_S3_ENDPOINT, MOTODIAG_BACKUP_S3_BUCKET, MOTODIAG_BACKUP_S3_KEY_ID and MOTODIAG_BACKUP_S3_SECRET. Nightly at 03:00 desktop time is fine.
