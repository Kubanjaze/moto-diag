#!/usr/bin/env python3
"""Phase 390: after a whole-Ubuntu restart, did the fleet pick up where it left off?

    python3 ~/motodiag/fleet/code/docs/phases/in_progress/390_ubuntu_check.py

Run by the operator's paste block, after `wsl --shutdown` and the boot
task. Waits up to five minutes, then says in plain English: when Ubuntu
started, when the fleet's service came up, and what its search on start
did, and ends with ALL GOOD or SOMETHING IS OFF. ALL GOOD needs the
service up after Ubuntu started and a "resume <stage> from <run>" line
written after Ubuntu started. (The first version also waited for the
search's summary line, which is written only when the resumed stage ends:
run on 2026-10-25 at 19:55, mid-way through an Engineer's build, it could
only time out.)
"""
from __future__ import annotations

import datetime as dt
import pathlib
import subprocess
import sys
import time

UNIT = "motodiag-fleet.service"
LOG = pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet" / "dispatcher.log"


def booted() -> dt.datetime:
    out = subprocess.run(["uptime", "-s"], capture_output=True, text=True).stdout.strip()
    return dt.datetime.strptime(out, "%Y-%m-%d %H:%M:%S")


def service() -> tuple[bool, str]:
    show = lambda p: subprocess.run(["systemctl", "show", UNIT, "-p", p, "--value"],  # noqa: E731
                                    capture_output=True, text=True).stdout.strip()
    return show("ActiveState") == "active", show("ActiveEnterTimestamp")


def lines_since(t: dt.datetime) -> list[str]:
    out = []
    for ln in LOG.read_text(errors="replace").splitlines():
        try:
            when = dt.datetime.fromisoformat(ln.split(" ", 1)[0]).replace(tzinfo=None)
        except ValueError:
            continue
        if when >= t:
            out.append(ln)
    return out


def main() -> int:
    boot = booted()
    print(f"Ubuntu started at:           {boot:%H:%M:%S}", flush=True)
    deadline = time.time() + 300
    resumed, search = None, None
    while time.time() < deadline:
        new = lines_since(boot)
        resumed = next((ln for ln in new if " resume " in ln and " from " in ln), None)
        # The search's summary line comes only when the resumed stage ends,
        # which can be an hour away (the first version waited for it).
        search = next((ln for ln in new if "the search on start:" in ln), None)
        if resumed:
            break
        time.sleep(5)
    up, since = service()
    print(f"the fleet's service:         {'running since ' + since if up else 'NOT running'}")
    print(f"what it picked up:           {resumed.split(' ', 1)[1] if resumed else 'nothing'}")
    print(f"its search on start:         "
          f"{search.split(' ', 1)[1] if search else 'still working on what it picked up'}")
    if up and resumed:
        print("ALL GOOD: the fleet came back by itself and picked up the stage it was in the "
              "middle of")
        return 0
    print("SOMETHING IS OFF: " + ("the service is not running" if not up else
                                  "no stage was picked up after the restart"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
