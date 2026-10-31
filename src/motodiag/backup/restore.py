"""Reading a snapshot back (Phase 345): list, pick, restore, verify.

A restore writes only into an empty folder of the operator's choosing, and
refuses one that is, holds or lies under the current database's folder or
the current data folder: nothing here writes over live. Every object is
decrypted (which checks its tag) and then checked against the manifest's
sha256; the database must also pass ``pragma integrity_check``. A failed
restore removes what it wrote.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from motodiag.backup.crypt import BackupTampered, decrypt_file
from motodiag.backup.settings import BackupSettings
from motodiag.backup.snapshot import (
    DB_OBJECT,
    MANIFEST_OBJECT,
    SNAPSHOTS,
    STAMP,
    Manifest,
    integrity_of,
    sha256_of,
)
from motodiag.backup.store import ObjectStore


class NoSnapshotBefore(Exception):
    """No snapshot was taken at or before the time asked for."""


class RestoreRefused(Exception):
    """The target folder is not empty, or is live's."""


@dataclass(frozen=True)
class SnapshotRef:
    stamp: str
    taken_at: datetime
    db_size: int

    @property
    def folder(self) -> str:
        return f"{SNAPSHOTS}{self.stamp}/"


@dataclass
class RestoreReport:
    taken_at: str
    schema_version: int | None
    rows: dict[str, int] = field(default_factory=dict)
    media_count: int = 0
    media_bytes: int = 0
    to_dir: str = ""


def list_snapshots(store: ObjectStore) -> list[SnapshotRef]:
    """Every complete snapshot, newest first: a folder holding both the
    database and the manifest. Needs no passphrase."""
    folders: dict[str, dict[str, int]] = {}
    for info in store.list(SNAPSHOTS):
        parts = info.key.split("/")
        if len(parts) == 3:
            folders.setdefault(parts[1], {})[parts[2]] = info.size
    refs = []
    for stamp, objects in folders.items():
        if DB_OBJECT not in objects or MANIFEST_OBJECT not in objects:
            continue
        try:
            when = datetime.strptime(stamp, STAMP).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        refs.append(SnapshotRef(stamp, when, objects[DB_OBJECT]))
    return sorted(refs, key=lambda r: r.taken_at, reverse=True)


def parse_at(text: str) -> datetime | None:
    """``latest`` as None; an ISO time as an aware datetime (naive is this
    machine's local time)."""
    if text.strip().lower() == "latest":
        return None
    when = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    return when if when.tzinfo else when.astimezone()


def pick(refs: list[SnapshotRef], at: datetime | None) -> SnapshotRef:
    """The newest snapshot taken at or before ``at`` (``None``: the newest)."""
    if not refs:
        raise NoSnapshotBefore("no snapshot has been taken yet")
    candidates = [r for r in refs if at is None or r.taken_at <= at]
    if not candidates:
        oldest = min(refs, key=lambda r: r.taken_at)
        raise NoSnapshotBefore(f"no snapshot at or before {at.isoformat() if at else ''}; "
                               f"the oldest is {oldest.taken_at.isoformat()}")
    return max(candidates, key=lambda r: r.taken_at)


def _overlaps(target: Path, live: Path) -> bool:
    return target == live or live in target.parents or target in live.parents


def _refuse_target(to_dir: Path, current_db: Path | None, current_data_dir: Path | None) -> None:
    target = to_dir.expanduser().resolve()
    live = [p.expanduser().resolve() for p in
            ((current_db.parent if current_db else None), current_data_dir) if p]
    for folder in live:
        if _overlaps(target, folder):
            raise RestoreRefused(f"{target} is live's folder {folder}, or holds or lies "
                                 "under it; a restore never writes over live")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise RestoreRefused(f"{target} is not an empty folder")


def _decrypt_checked(store: ObjectStore, key: str, dst: Path, passphrase: str,
                     incoming: Path, sha256: str | None) -> None:
    enc = incoming / "object.enc"
    try:
        store.get(key, enc)
        decrypt_file(enc, dst, passphrase)
    finally:
        enc.unlink(missing_ok=True)
    if sha256 is not None and sha256_of(dst) != sha256:
        dst.unlink()
        raise BackupTampered(f"{key} does not match the manifest's sha256")


def _rows(db: Path) -> dict[str, int]:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        names = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {n: int(conn.execute(f'SELECT count(*) FROM "{n}"').fetchone()[0])
                for n in names}
    finally:
        conn.close()


def _restore_into(ref: SnapshotRef, store: ObjectStore, settings: BackupSettings,
                  target: Path, db_only: bool) -> RestoreReport:
    incoming = target / ".incoming"
    incoming.mkdir(mode=0o700)
    manifest_path = incoming / "manifest.json"
    _decrypt_checked(store, ref.folder + MANIFEST_OBJECT, manifest_path,
                     settings.passphrase, incoming, None)
    manifest = Manifest.from_json(manifest_path.read_text(encoding="utf-8"))
    manifest_path.unlink()
    db = target / "motodiag.db"
    _decrypt_checked(store, ref.folder + DB_OBJECT, db, settings.passphrase, incoming,
                     manifest.db_sha256)
    check = integrity_of(db)
    if check != "ok":
        raise BackupTampered(f"the restored database fails its integrity check ({check[:200]})")
    report = RestoreReport(manifest.taken_at, manifest.schema_version, _rows(db),
                           to_dir=str(target))
    for entry in [] if db_only else manifest.media:
        dst = (target / entry.path).resolve()
        if target not in dst.parents:
            raise BackupTampered(f"the manifest names a path outside the folder: {entry.path}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        _decrypt_checked(store, entry.key, dst, settings.passphrase, incoming, entry.sha256)
        report.media_count += 1
        report.media_bytes += entry.size
    incoming.rmdir()
    return report


def restore(ref: SnapshotRef, store: ObjectStore, settings: BackupSettings, to_dir: Path,
            *, db_only: bool = False, current_db: Path | None = None,
            current_data_dir: Path | None = None) -> RestoreReport:
    """Bring ``ref`` back into ``to_dir``: ``motodiag.db`` and each media file at
    its relative path. A failure removes everything written."""
    _refuse_target(Path(to_dir), current_db, current_data_dir)
    target = Path(to_dir).expanduser().resolve()
    created = not target.exists()
    target.mkdir(parents=True, exist_ok=True)
    try:
        return _restore_into(ref, store, settings, target, db_only)
    except BaseException:
        if created:
            shutil.rmtree(target, ignore_errors=True)
        else:
            for child in target.iterdir():
                shutil.rmtree(child) if child.is_dir() else child.unlink()
        raise


def verify(ref: SnapshotRef, store: ObjectStore, settings: BackupSettings) -> RestoreReport:
    """The database half of a restore into a temporary folder, then deleted:
    proof that the snapshot can be read back."""
    with tempfile.TemporaryDirectory(prefix="motodiag-verify-") as tmp:
        report = restore(ref, store, settings, Path(tmp) / "snapshot", db_only=True)
    report.to_dir = ""
    return report
