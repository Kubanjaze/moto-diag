#!/usr/bin/env python3
"""Where live is, on this machine (Phase 382, the operator's 1A).

Live moved from the Mac to the home desktop. Every tool that reads live by its
path asks here instead of assuming the checkout's own data folder. Each machine carries
`~/.config/motodiag/live.json`:

    the desktop  {"live": "/home/lilcu/motodiag/live/motodiag.db"}
    the Mac      {"live": null, "host": "desktop-76s9bqv"}

A missing file, a null path or a path that does not exist refuses, so a fresh
clone anywhere fails closed. `MOTODIAG_LIVE_CONFIG` names another file (tests).

    live.py           print live's path; exit 4 when it is not on this machine
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

REFUSED = 4
CONFIG = pathlib.Path.home() / ".config" / "motodiag" / "live.json"
# A folder that a cloud service syncs: a Windows drive seen from WSL, or a
# known sync root. Backups of live never go there.
SYNC_MARKERS = ("OneDrive", "iCloud", "Mobile Documents", "Dropbox", "Google Drive",
                "GoogleDrive", "CloudStorage")


class LiveElsewhere(Exception):
    """Live is not on this machine, or this machine has not been told where it is."""


def config_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get("MOTODIAG_LIVE_CONFIG") or CONFIG)


def where(config: pathlib.Path | None = None) -> pathlib.Path:
    cfg = config or config_path()
    if not cfg.is_file():
        raise LiveElsewhere(f"{cfg} is missing: this machine has not been told where live "
                            "is (Phase 382). Live is on the home desktop.")
    entry = json.loads(cfg.read_text())
    if not entry.get("live"):
        raise LiveElsewhere(f"live is on {entry.get('host') or 'another machine'}, "
                            f"not here ({cfg}). Run this there.")
    path = pathlib.Path(entry["live"]).expanduser()
    if not path.is_file():
        raise LiveElsewhere(f"{cfg} names {path}, which does not exist.")
    return path


def unsynced(folder: pathlib.Path) -> pathlib.Path:
    """`folder`, unless a cloud service could sync it."""
    resolved = folder.expanduser().resolve()
    parts = resolved.parts
    if len(parts) > 2 and parts[1] == "mnt" and len(parts[2]) == 1:
        raise LiveElsewhere(f"{resolved} is on a Windows drive; backups of live stay on "
                            "the WSL disk.")
    hit = [m for m in SYNC_MARKERS if any(m in p for p in parts)]
    if hit:
        raise LiveElsewhere(f"{resolved} is under a synced folder ({hit[0]}); backups of "
                            "live never go there.")
    return folder


def main() -> int:
    try:
        print(where())
    except LiveElsewhere as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return REFUSED
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
