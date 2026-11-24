"""The virus scan of an uploaded manual (K119).

``clamdscan`` (the daemon, handed the open file) when it is on PATH, else
``clamscan``. Exit 0 is clean and 1 is infected; any other exit, a scanner
that cannot be run, or none on the machine is ``unavailable``, and the
upload route refuses every file then: none is let through unscanned.
Nothing here downloads or installs anything; installing ClamAV is the
operator's step on the server.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SCAN_TIMEOUT_S = 600

ScanStatus = Literal["clean", "infected", "unavailable"]


@dataclass(frozen=True)
class ScanResult:
    status: ScanStatus
    detail: str


def _command(path: Path) -> list[str] | None:
    daemon = shutil.which("clamdscan")
    if daemon is not None:
        return [daemon, "--fdpass", "--no-summary", str(path)]
    standalone = shutil.which("clamscan")
    if standalone is not None:
        return [standalone, "--no-summary", str(path)]
    return None


def scan_file(path: str | Path) -> ScanResult:
    command = _command(Path(path))
    if command is None:
        return ScanResult("unavailable", "no virus scanner is installed on the server")
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=SCAN_TIMEOUT_S, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ScanResult("unavailable", f"the virus scanner did not run: {exc}")
    output = (proc.stdout or proc.stderr).strip()
    if proc.returncode == 0:
        return ScanResult("clean", output)
    if proc.returncode == 1:
        return ScanResult("infected", output)
    return ScanResult("unavailable", f"the virus scanner failed (exit {proc.returncode})")
