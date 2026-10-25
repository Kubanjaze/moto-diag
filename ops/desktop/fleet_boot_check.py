#!/usr/bin/env python3
"""Phase 388: did the fleet dispatcher come up by itself after a restart?

    python3 ~/motodiag/fleet/code/ops/desktop/fleet_boot_check.py

Run in the Ubuntu window after signing back in. It compares the time
motodiag-fleet.service last became active with the Windows sign-in time
(`quser.exe`, through WSL's interop): the unit up before anyone signed in is
the pass, the shape of Phase 382's restart proof. Prints the three times and
ends with ALL GOOD or SOMETHING IS OFF.
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys

UNIT = "motodiag-fleet.service"
QUSER = "/mnt/c/Windows/System32/quser.exe"
_LOGON = re.compile(r"(\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2} [AP]M)\s*$")


def unit_started(value: str) -> dt.datetime | None:
    """systemd's 'Thu 2026-10-23 07:49:15 EDT', local, to the second."""
    m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", value)
    return dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S") if m else None


def signed_in(quser_out: str, user: str = "lilcu") -> dt.datetime | None:
    """The user's LOGON TIME from quser, local, to the minute."""
    for line in quser_out.splitlines():
        if line.lstrip(" >").lower().startswith(user.lower() + " "):
            m = _LOGON.search(line.strip())
            if m:
                return dt.datetime.strptime(m.group(1), "%m/%d/%Y %I:%M %p")
    return None


def verdict(active: bool, started: dt.datetime | None, logon: dt.datetime | None) -> tuple[bool, str]:
    if not active or started is None:
        return False, "the fleet dispatcher is not running"
    if logon is None:
        return False, "could not read the Windows sign-in time"
    if started < logon:
        return True, (f"the fleet dispatcher came up at {started:%H:%M:%S}, before you signed "
                      f"in at {logon:%H:%M}")
    return False, (f"the fleet dispatcher came up at {started:%H:%M:%S}, after you signed in "
                   f"at {logon:%H:%M}: it waited for you")


def main() -> int:
    show = lambda prop: subprocess.run(["systemctl", "show", UNIT, "-p", prop, "--value"],  # noqa: E731
                                       capture_output=True, text=True).stdout.strip()
    active = show("ActiveState") == "active"
    started = unit_started(show("ActiveEnterTimestamp"))
    q = subprocess.run([QUSER], capture_output=True, text=True, cwd="/mnt/c")
    logon = signed_in(q.stdout)
    boot = subprocess.run(["uptime", "-s"], capture_output=True, text=True).stdout.strip()
    print(f"Ubuntu started:          {boot}")
    print(f"fleet dispatcher up at:  {started or 'not running'}")
    print(f"you signed in at:        {logon or 'unknown'}")
    ok, why = verdict(active, started, logon)
    print(f"{'ALL GOOD' if ok else 'SOMETHING IS OFF'}: {why}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
