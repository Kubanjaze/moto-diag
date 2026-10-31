"""The key file and the working folder (Phase 345, K62).

The bucket's key and the passphrase live only in
``~/.config/motodiag/backup.env``, mode 600, as ``NAME=VALUE`` lines under
the five names in :data:`ENV_NAMES`. ``MOTODIAG_BACKUP_ENV`` names another
file, for tests, as ``MOTODIAG_LIVE_CONFIG`` does for the deploy skill's
``live.py``.

Every refusal names a variable, never its value, and :class:`BackupSettings`
prints names only, so no traceback or log line can carry a secret.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

ENDPOINT = "MOTODIAG_BACKUP_S3_ENDPOINT"
BUCKET = "MOTODIAG_BACKUP_S3_BUCKET"
KEY_ID = "MOTODIAG_BACKUP_S3_KEY_ID"
SECRET = "MOTODIAG_BACKUP_S3_SECRET"
PASSPHRASE = "MOTODIAG_BACKUP_PASSPHRASE"
ENV_NAMES = (ENDPOINT, BUCKET, KEY_ID, SECRET, PASSPHRASE)

DEFAULT_ENV = Path.home() / ".config" / "motodiag" / "backup.env"
DEFAULT_WORK = Path.home() / "backups" / "motodiag" / "offsite"

# The same markers as the deploy skill's live.py (which src/ cannot import):
# a folder a cloud service syncs never holds a plaintext copy of live.
SYNC_MARKERS = ("OneDrive", "iCloud", "Mobile Documents", "Dropbox", "Google Drive",
                "GoogleDrive", "CloudStorage")


class BackupConfigError(Exception):
    """The key file or the working folder is refused. The text names no value."""


@dataclass(frozen=True)
class BackupSettings:
    """The five values from the key file. ``repr`` and ``str`` show names only."""

    path: Path
    endpoint: str = field(repr=False)
    bucket: str = field(repr=False)
    key_id: str = field(repr=False)
    secret: str = field(repr=False)
    passphrase: str = field(repr=False)

    def __repr__(self) -> str:
        return f"BackupSettings(path={str(self.path)!r}, names={list(ENV_NAMES)!r})"

    __str__ = __repr__


def env_path() -> Path:
    """The key file this process reads."""
    return Path(os.environ.get("MOTODIAG_BACKUP_ENV") or DEFAULT_ENV).expanduser()


def _parse(text: str) -> dict[str, str]:
    """``NAME=VALUE`` lines; blank lines and ``#`` comments are skipped, and one
    pair of matching quotes around a value is removed."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name.strip()] = value
    return values


def names_in(path: Path | None = None) -> list[str]:
    """Which of the five names the key file holds with a value. Names only."""
    cfg = path or env_path()
    if not cfg.is_file():
        return []
    values = _parse(cfg.read_text(encoding="utf-8"))
    return [n for n in ENV_NAMES if values.get(n)]


def load_backup_settings(path: Path | None = None) -> BackupSettings:
    """Read the key file, refusing a missing file, a missing or empty name, or a
    mode that grants anything to group or others."""
    cfg = path or env_path()
    if not cfg.is_file():
        raise BackupConfigError(f"{cfg} is missing: the backup's key file is not on "
                                "this machine.")
    mode = stat.S_IMODE(cfg.stat().st_mode)
    if mode & 0o077:
        raise BackupConfigError(f"{cfg} is mode {mode:o}; it must be 600 "
                                f"(chmod 600 {cfg}).")
    values = _parse(cfg.read_text(encoding="utf-8"))
    missing = [n for n in ENV_NAMES if not values.get(n)]
    if missing:
        raise BackupConfigError(f"{cfg} has no value for {', '.join(missing)}.")
    return BackupSettings(
        path=cfg, endpoint=values[ENDPOINT], bucket=values[BUCKET],
        key_id=values[KEY_ID], secret=values[SECRET], passphrase=values[PASSPHRASE],
    )


def refuse_synced(folder: Path) -> Path:
    """``folder``, unless it is on a Windows drive seen from WSL or under a
    cloud-synced folder."""
    resolved = Path(folder).expanduser().resolve()
    parts = resolved.parts
    if len(parts) > 2 and parts[1] == "mnt" and len(parts[2]) == 1:
        raise BackupConfigError(f"{resolved} is on a Windows drive; the backup's "
                                "working folder stays on the WSL disk.")
    hit = [m for m in SYNC_MARKERS if any(m in p for p in parts)]
    if hit:
        raise BackupConfigError(f"{resolved} is under a synced folder ({hit[0]}); the "
                                "backup's working folder never goes there.")
    return resolved


def work_dir() -> Path:
    """The staging and log folder (``MOTODIAG_BACKUP_WORK_DIR`` overrides the
    default), refused when synced, created mode 700."""
    folder = refuse_synced(Path(os.environ.get("MOTODIAG_BACKUP_WORK_DIR") or DEFAULT_WORK))
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    return folder
