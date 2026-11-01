# Backups: an encrypted copy of the shop's data, off the machine

The shop's data lives on the home desktop: one database file and three
folders of uploads (videos, photos and voice notes). If that machine's disk
fails, or the machine is stolen, the data on it is gone. So every night the
desktop makes a copy of all of it and sends that copy somewhere else.

## What is copied, and when

- **What:** the database, and every uploaded video, photo and audio file.
  Nothing else (no logs, no settings, no keys).
- **When:** every night at 03:00, desktop time. If the desktop was switched
  off at 03:00, the copy is made the next time it starts.
- **Where it goes:** to one private storage bucket at Backblaze, used only
  for these copies.
- **Encrypted before it leaves.** Each file is locked on the desktop with a
  passphrase that only you hold, before it is sent. Backblaze stores
  scrambled bytes it cannot read. Without the passphrase nobody, including
  you, can open a copy, so keep the passphrase in your password manager.
- **What moves each night:** the database is sent whole each time. An
  upload is sent once, the first night it exists, and never again.
- **Nothing is ever deleted** from the bucket, so you can go back to any
  night.

The key to the bucket and the passphrase live in one file on the desktop,
`~/.config/motodiag/backup.env`, which only your user can read (mode 600).
They are never typed on a command line and never printed.

## Before any command below

Run them on the home desktop, in the Ubuntu terminal, with the server's own
copy of `motodiag` and the two settings that say where live is, exactly as
the nightly run has them. Paste this first, once per terminal window:

```bash
export PATH="$HOME/motodiag/server/.venv/bin:$PATH"
export MOTODIAG_DB_PATH="$HOME/motodiag/live/motodiag.db"
export MOTODIAG_DATA_DIR="$HOME/motodiag/live"
```

Without the two settings, `motodiag backup run` would copy some other
database, and `restore` could not tell which folder is live's.

## Did last night's copy happen?

```bash
motodiag backup status
motodiag backup list
```

`status` says when the last copy was made and whether it worked; it ends
with an error when the last one failed. `list` shows every copy, newest
first.

To prove a copy can be read back, without writing anything anywhere:

```bash
motodiag backup verify --at latest
```

It downloads the newest copy's database into a temporary folder, unlocks it,
checks it, and deletes it.

## Getting a copy back

Pick an empty folder of your own, and the night you want (`latest`, or a
time such as `2026-11-03T09:00`, which means the newest copy made at or
before that time on the desktop's clock):

```bash
motodiag backup restore --at latest --to ~/motodiag/restore_check
```

It unlocks the database and every upload into that folder, and checks each
file against the hash recorded when the copy was made. If anything does not
match, it stops and leaves nothing behind. Add `--db-only` to bring back the
database alone.

**It never writes over live.** It refuses a folder that is, holds or lies
inside the live database's folder or the live uploads folder, and it refuses
a folder that is not empty. Putting a restored copy in place of live is a
change to the live database, and goes through the deploy procedure with the
operator's approval, never through this command.

When it finishes it prints the two settings a server needs to run against
the restored folder: `MOTODIAG_DB_PATH` (the restored `motodiag.db`) and
`MOTODIAG_DATA_DIR` (the folder). The uploads are stored by their place
inside that folder, so they are found on any machine.

## Taking a copy by hand

```bash
motodiag backup run
```

It does what the nightly run does, at once, and prints what it sent.
