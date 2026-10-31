"""One snapshot of live, encrypted and put offsite (Phase 345).

The database is copied with SQLite's backup API (as ``deploy.py backup``
does, so the running API is never blocked), checked with
``pragma integrity_check`` and uploaded whole. A media file is uploaded once,
as ``media/<sha256>.enc``, and skipped on every later run: that is the sync.
The manifest goes last, so a snapshot folder with a manifest is complete.

Store layout::

    snapshots/<YYYYMMDDTHHMMSSZ>/motodiag.db.enc
    snapshots/<YYYYMMDDTHHMMSSZ>/manifest.json.enc
    media/<sha256 of the plaintext>.enc
"""

from __future__ import annotations

import hashlib
import json
import socket
import sqlite3
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from motodiag.backup.crypt import encrypt_file
from motodiag.backup.settings import BackupSettings
from motodiag.backup.store import ObjectStore
from motodiag.core.timestamps import utc_now

MEDIA_DIRS = ("videos", "photos", "audio")
SNAPSHOTS = "snapshots/"
MEDIA = "media/"
DB_OBJECT = "motodiag.db.enc"
MANIFEST_OBJECT = "manifest.json.enc"
RUNS_LOG = "runs.log"
STAMP = "%Y%m%dT%H%M%SZ"


class SnapshotRefused(Exception):
    """The copy of the database failed its integrity check; nothing was uploaded."""


@dataclass
class MediaEntry:
    path: str
    sha256: str
    size: int
    key: str


@dataclass
class Manifest:
    taken_at: str
    label: str
    host: str
    schema_version: int | None
    db_sha256: str
    db_size: int
    db_cipher_sha256: str
    media: list[MediaEntry] = field(default_factory=list)
    stamp: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "Manifest":
        data = json.loads(text)
        data["media"] = [MediaEntry(**m) for m in data.get("media", [])]
        return cls(**data)


@dataclass
class RunResult:
    manifest: Manifest
    media_uploaded: int
    media_skipped: int
    bytes_sent: int


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fin:
        while chunk := fin.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def stamp_of(when: datetime) -> str:
    return when.astimezone(timezone.utc).strftime(STAMP)


def copy_database(src: Path, dst: Path) -> None:
    """A consistent copy of a live database, by SQLite's backup API. The copy
    is switched out of WAL mode (live's), so reading it, here or after a
    restore, leaves no ``-wal`` or ``-shm`` file holding plaintext beside it."""
    source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
        target.execute("pragma journal_mode=delete")
    finally:
        target.close()
        source.close()


def integrity_of(path: Path) -> str:
    """``pragma integrity_check``'s answer, or the error opening the file."""
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            rows = conn.execute("pragma integrity_check").fetchall()
        finally:
            conn.close()
    except sqlite3.DatabaseError as e:
        return str(e)
    return "; ".join(str(r[0]) for r in rows)


def schema_version_of(path: Path) -> int | None:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT max(version) FROM schema_version").fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
    return None if row is None or row[0] is None else int(row[0])


def media_files(data_dir: Path) -> list[tuple[str, Path]]:
    """Every file under the three upload folders, by its path relative to the
    data folder in POSIX form (F205's form)."""
    found: list[tuple[str, Path]] = []
    for name in MEDIA_DIRS:
        root = data_dir / name
        if root.is_dir():
            found += [(p.relative_to(data_dir).as_posix(), p)
                      for p in root.rglob("*") if p.is_file()]
    return sorted(found)


def _log(work: Path, entry: dict) -> None:
    with open(work / RUNS_LOG, "a", encoding="utf-8") as fout:
        fout.write(json.dumps(entry, sort_keys=True) + "\n")


def _upload_media(data_dir: Path, settings: BackupSettings, store: ObjectStore,
                  work: Path, counts: dict) -> list[MediaEntry]:
    have = {o.key for o in store.list(MEDIA)}
    entries: list[MediaEntry] = []
    for rel, path in media_files(data_dir):
        digest = sha256_of(path)
        key = f"{MEDIA}{digest}.enc"
        if key in have:
            counts["media_skipped"] += 1
        else:
            enc = work / "media.enc"
            try:
                cipher_sha = encrypt_file(path, enc, settings.passphrase)
                store.put(key, enc, cipher_sha)
                counts["bytes_sent"] += enc.stat().st_size
            finally:
                enc.unlink(missing_ok=True)
            have.add(key)
            counts["media_uploaded"] += 1
        entries.append(MediaEntry(rel, digest, path.stat().st_size, key))
    return entries


def take_snapshot(db_path: Path, data_dir: Path, settings: BackupSettings,
                  store: ObjectStore, work: Path, clock: Callable[[], str] | None = None,
                  *, label: str = "manual") -> RunResult:
    """Take one snapshot of ``db_path`` and the upload folders under
    ``data_dir``; appends one line to ``work/runs.log`` whatever happens."""
    taken = datetime.fromisoformat((clock or utc_now)())
    stamp = stamp_of(taken)
    folder = f"{SNAPSHOTS}{stamp}/"
    counts = {"media_uploaded": 0, "media_skipped": 0, "bytes_sent": 0}
    entry: dict = {"time": taken.isoformat(), "label": label, "snapshot": folder}
    plain = [work / "motodiag.db", work / DB_OBJECT, work / "manifest.json",
             work / MANIFEST_OBJECT]
    try:
        copy_database(Path(db_path), plain[0])
        check = integrity_of(plain[0])
        if check != "ok":
            raise SnapshotRefused(f"the copy of the database failed its integrity check "
                                  f"({check[:200]}); nothing was uploaded")
        media = _upload_media(Path(data_dir), settings, store, work, counts)
        cipher_sha = encrypt_file(plain[0], plain[1], settings.passphrase)
        manifest = Manifest(
            taken_at=taken.isoformat(), label=label, host=socket.gethostname(),
            schema_version=schema_version_of(plain[0]), db_sha256=sha256_of(plain[0]),
            db_size=plain[0].stat().st_size, db_cipher_sha256=cipher_sha, media=media,
            stamp=stamp,
        )
        store.put(folder + DB_OBJECT, plain[1], cipher_sha)
        counts["bytes_sent"] += plain[1].stat().st_size
        plain[2].write_text(manifest.to_json(), encoding="utf-8")
        manifest_sha = encrypt_file(plain[2], plain[3], settings.passphrase)
        store.put(folder + MANIFEST_OBJECT, plain[3], manifest_sha)
        counts["bytes_sent"] += plain[3].stat().st_size
        entry.update(outcome="ok", db_size=manifest.db_size, db_sha256=manifest.db_sha256)
        return RunResult(manifest, **counts)
    except Exception as e:
        entry.update(outcome="failed", error=traceback.format_exception_only(e)[-1].strip())
        raise
    finally:
        for p in plain:
            p.unlink(missing_ok=True)
        entry.update(counts)
        _log(work, entry)
