"""Where an uploaded media file is, stored relative to the data folder (F205).

Phase 383. The upload routes stored the receiving machine's absolute path
(`str(storage_dir / name)`), so moving live from the Mac to the home desktop
(Phase 382) stranded every media row until its paths were rewritten by hand.
A row now holds the path relative to `settings.data_dir`, in POSIX form
(`videos/shop_1/session_1/1.mp4`), and every reader resolves it under the
data folder of the machine that reads it.

A stored absolute path still resolves to itself (pathlib's join), so a row
written before migration 087, or a test's tmp path, reads unchanged.
"""

from __future__ import annotations

from pathlib import Path


def stored_media_path(path: Path, data_dir: str | Path) -> str:
    """The value a media row stores for ``path``: relative to ``data_dir``
    when it lies under it, else the whole path."""
    try:
        return Path(path).resolve().relative_to(Path(data_dir).resolve()).as_posix()
    except ValueError:
        return str(path)


def resolve_media_path(stored: str, data_dir: str | Path) -> Path:
    """The file a media row names, on this machine."""
    return Path(data_dir) / stored
