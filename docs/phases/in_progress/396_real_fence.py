"""Phase 396, (a): the Quartermaster's code check, once in the real fence.

389's rule: no rank goes live on a new check until it has run once against a
real artefact in the real place. On the home desktop, with no fleet run in
progress: this branch's `Fleet.check_run`, the real `fence.sh` (bubblewrap),
the fleet's own venv, and a clone of the fleet's mirror, at the two heads the
Quartermaster judged and could not check (348, PR #40; 385, PR #43) against
the master each was judged on. Nothing is pushed, and the fleet's state
folder is only read (its mirror is cloned); the runs go to a scratch folder.

    .venv/bin/python docs/phases/in_progress/396_real_fence.py <scratch-folder>

Writes `fixtures/slips396/a_real_fence_<phase>.txt` and exits 1 unless both
print a `{"Q10": ..., "Q12": ...}` line that `code_result` reads.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
FLEET = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(FLEET))
import dispatcher as D  # noqa: E402
import quartermaster as Q  # noqa: E402

FLEET_STATE = pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet"
#: phase: (the head the Quartermaster judged, the master it judged it on)
HEADS = {"348": ("dd5aed2bed07905ade02795619eb96b1308ffff9", "d76b8654538432de3fc2336f080c8357a5431049"),
         "385": ("46db82e1df7a0a293ee0b4486ded5b6e786a18ae", "ddcdfd68472e0a93574226378cda8d30c3354298")}


def main(scratch: pathlib.Path) -> int:
    fleet = D.Fleet(state=scratch / "state", venv=FLEET_STATE / "venv", out=print,
                    mobile=pathlib.Path.home() / "motodiag" / "fleet" / "mobile")
    print(f"fence {fleet.fence}; venv {fleet.venv} ({fleet.venv.is_dir()})")
    bad = 0
    for phase, (head, base) in HEADS.items():
        src = scratch / f"src{phase}"
        if not src.is_dir():
            subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(FLEET_STATE / "mirror.git"),
                            str(src)], check=True)
        c = fleet.check_run(src, head, full=False, command=Q.code_command(base))
        got = Q.code_result(c.out)
        text = (f"# Phase 396, (a): the code check in the real fence, phase {phase}\n"
                f"# head {head}, base {base}, on {os.uname().nodename}\n"
                f"# ok={c.ok}, result read: {got is not None}\n\n{c.out}")
        (FLEET / "fixtures" / "slips396" / f"a_real_fence_{phase}.txt").write_text(text)
        print(f"{phase}: ok={c.ok} result={json.dumps(got)[:300] if got else None}")
        if got is None:
            print("  why: " + Q.no_result_why(c.out, ok=c.ok, why=c.why))
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1])))
