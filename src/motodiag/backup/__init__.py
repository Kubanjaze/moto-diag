"""Offsite encrypted backups of live, and restoring them (Phase 345).

A snapshot is live's database (by SQLite's backup API) and every uploaded
video, photo and audio file, encrypted on the desktop with the operator's
passphrase and put in one private Backblaze B2 bucket through its
S3-compatible API (K62). Nothing here writes to live and nothing here deletes
an object from the bucket.

- ``settings``: the key file, ``~/.config/motodiag/backup.env``, and the
  working folder;
- ``crypt``: the one encrypted format (scrypt, AES-256-GCM);
- ``store``: the S3 client, in the standard library;
- ``snapshot``: taking one; ``restore``: listing, picking and reading one back.
"""
