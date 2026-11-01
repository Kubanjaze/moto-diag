"""CLI: ``motodiag backup {run, list, restore, verify, status}`` (Phase 345).

Offsite encrypted backups of live's database and uploads to the operator's
Backblaze B2 bucket (K62). The key and the passphrase are read only from
``~/.config/motodiag/backup.env`` (mode 600); no command takes either as an
argument, and no output carries a value from that file. ``restore`` writes
into an empty folder and never over live.

Exit codes: 0 done; 1 a failed upload, check or refusal; 2 the key file or
the working folder refused, before anything is touched.
"""

from __future__ import annotations

import json as _json
from datetime import datetime
from pathlib import Path
from typing import NoReturn, Optional

import click

from motodiag.backup.settings import (
    ENV_NAMES,
    BackupConfigError,
    BackupSettings,
    env_path,
    load_backup_settings,
    names_in,
    work_dir,
)
from motodiag.backup.store import ObjectStore, S3Store
from motodiag.core.config import get_settings

CONFIG_REFUSED = 2


def open_store(settings: BackupSettings) -> ObjectStore:
    """The bucket, from the key file's values. Tests replace this."""
    return S3Store(settings.endpoint, settings.bucket, settings.key_id, settings.secret)


def _settings_or_exit() -> BackupSettings:
    try:
        return load_backup_settings()
    except BackupConfigError as e:
        click.echo(f"REFUSED: {e}", err=True)
        raise SystemExit(CONFIG_REFUSED) from None


def _fail(message: str) -> NoReturn:
    click.echo(f"FAILED: {message}", err=True)
    raise SystemExit(1)


def _local(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _print_report(report) -> None:
    click.echo(f"Snapshot taken {_local(report.taken_at)} (UTC {report.taken_at})")
    click.echo(f"Schema version {report.schema_version}; "
               f"{len(report.rows)} tables, {sum(report.rows.values())} rows")
    click.echo(f"Media files: {report.media_count} ({report.media_bytes} bytes)")


def _pick(store: ObjectStore, at: str):
    from motodiag.backup.restore import NoSnapshotBefore, list_snapshots, parse_at, pick
    try:
        return pick(list_snapshots(store), parse_at(at))
    except (NoSnapshotBefore, ValueError) as e:
        _fail(str(e))


def register_backup(cli_group: click.Group) -> None:
    """Attach the ``backup`` subgroup to the top-level CLI."""

    @cli_group.group("backup")
    def backup_group() -> None:
        """Offsite encrypted backups of live, and restoring them (Phase 345)."""

    @backup_group.command("run")
    @click.option("--label", default="manual", show_default=True)
    @click.option("--db", "db", default=None, help="The database (default: settings).")
    @click.option("--data-dir", default=None, help="The data folder (default: settings).")
    def backup_run(label: str, db: Optional[str], data_dir: Optional[str]) -> None:
        """Take one snapshot now and put it offsite."""
        settings = _settings_or_exit()
        try:
            work = work_dir()
        except BackupConfigError as e:
            click.echo(f"REFUSED: {e}", err=True)
            raise SystemExit(CONFIG_REFUSED) from None
        from motodiag.backup.crypt import BackupLibraryMissing
        from motodiag.backup.snapshot import SnapshotRefused, take_snapshot
        from motodiag.backup.store import StoreError
        app = get_settings()
        try:
            result = take_snapshot(Path(db or app.db_path), Path(data_dir or app.data_dir),
                                   settings, open_store(settings), work, label=label)
        except (StoreError, SnapshotRefused, BackupLibraryMissing, OSError) as e:
            _fail(f"{e} (logged in {work / 'runs.log'})")
        m = result.manifest
        click.echo(f"Snapshot {m.stamp} taken {_local(m.taken_at)}")
        click.echo(f"Database: {m.db_size} bytes, sha256 {m.db_sha256}")
        click.echo(f"Media: {result.media_uploaded} uploaded, {result.media_skipped} "
                   f"already offsite; {result.bytes_sent} bytes sent")

    @backup_group.command("list")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def backup_list(as_json: bool) -> None:
        """Every snapshot, newest first."""
        from motodiag.backup.restore import list_snapshots
        from motodiag.backup.store import StoreError
        settings = _settings_or_exit()
        try:
            refs = list_snapshots(open_store(settings))
        except StoreError as e:
            _fail(str(e))
        if as_json:
            click.echo(_json.dumps([{"stamp": r.stamp, "taken_at": r.taken_at.isoformat(),
                                     "db_size": r.db_size} for r in refs], indent=2))
            return
        if not refs:
            click.echo("No snapshot has been taken yet.")
            return
        for r in refs:
            local = r.taken_at.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
            click.echo(f"{r.stamp}  {local}  database {r.db_size} bytes (encrypted)")

    @backup_group.command("restore")
    @click.option("--at", "at", required=True, help="An ISO time, or 'latest'.")
    @click.option("--to", "to_dir", required=True, help="An empty folder to restore into.")
    @click.option("--db-only", is_flag=True, default=False, help="The database only.")
    @click.option("--db", "db", default=None, help="Live's database (default: settings).")
    @click.option("--data-dir", default=None, help="Live's data folder (default: settings).")
    def backup_restore(at: str, to_dir: str, db_only: bool, db: Optional[str],
                       data_dir: Optional[str]) -> None:
        """Bring back the newest snapshot taken at or before --at, into --to."""
        from motodiag.backup.crypt import BackupLibraryMissing, BackupTampered
        from motodiag.backup.restore import RestoreRefused, restore
        from motodiag.backup.store import StoreError
        settings = _settings_or_exit()
        app = get_settings()
        try:
            store = open_store(settings)
            ref = _pick(store, at)
            report = restore(ref, store, settings, Path(to_dir), db_only=db_only,
                             current_db=Path(db or app.db_path),
                             current_data_dir=Path(data_dir or app.data_dir))
        except (RestoreRefused, BackupTampered, StoreError, BackupLibraryMissing) as e:
            _fail(str(e))
        _print_report(report)
        click.echo(f"Restored into {report.to_dir}. To run a server against it:")
        click.echo(f"  MOTODIAG_DB_PATH={report.to_dir}/motodiag.db")
        click.echo(f"  MOTODIAG_DATA_DIR={report.to_dir}")

    @backup_group.command("verify")
    @click.option("--at", "at", default="latest", show_default=True)
    def backup_verify(at: str) -> None:
        """Read a snapshot's database back into a temporary folder and check it."""
        from motodiag.backup.crypt import BackupLibraryMissing, BackupTampered
        from motodiag.backup.restore import verify
        from motodiag.backup.store import StoreError
        settings = _settings_or_exit()
        try:
            store = open_store(settings)
            report = verify(_pick(store, at), store, settings)
        except (BackupTampered, StoreError, BackupLibraryMissing) as e:
            _fail(str(e))
        _print_report(report)
        click.echo("Verified: the snapshot decrypts, matches its hash and passes "
                   "the integrity check.")

    @backup_group.command("status")
    def backup_status() -> None:
        """The last run, which names the key file holds, and the working folder."""
        cfg = env_path()
        held = names_in(cfg)
        click.echo(f"Key file {cfg}: holds {', '.join(held) if held else 'none'} "
                   f"of the {len(ENV_NAMES)} names")
        try:
            work = work_dir()
        except BackupConfigError as e:
            _fail(str(e))
        click.echo(f"Working folder: {work}")
        log = work / "runs.log"
        lines = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
        if not lines:
            _fail("no backup run is logged yet")
        last = _json.loads(lines[-1])
        when = last.get("time", "")
        when_local = _local(when) if when else "an unknown time"
        click.echo(f"Last run: {when_local} (UTC {when}), {last.get('label')}, "
                   f"{last.get('outcome')}")
        click.echo(f"  media uploaded {last.get('media_uploaded', 0)}, already offsite "
                   f"{last.get('media_skipped', 0)}, bytes sent {last.get('bytes_sent', 0)}")
        if last.get("outcome") != "ok":
            _fail(f"the last run failed: {last.get('error', 'no reason logged')}")

