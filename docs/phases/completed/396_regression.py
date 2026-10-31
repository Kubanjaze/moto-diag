"""Phase 396's regression of record: one model-free run, as the fleet makes it.

    .venv/bin/python docs/phases/in_progress/396_regression.py <state-dir> <commit> <mobile-dir>

395's driver, unchanged but for this note: this branch's `Fleet.check_run`
(`wholetree.sh --full`, then `regression.sh`) on <commit>, in a fresh clone
in the fence, no model, no token, with the fleet's virtualenv, in its own
state folder. <mobile-dir> is a clean clone of the mobile repository at its
published `origin/main`, mounted as `../moto-diag-mobile`.

Why not this checkout (the phase log, 2026-10-31): `regression.sh` here gave
12147 passed, 4 failed at `c8bd296`, and the same four fail on master in
this checkout (test_phase204_gate10's installed-ffmpeg check and three of
test_phase257_orchestrator_guards'): they read this machine's own tools and
profile, not the code. 393, 394 and 395 recorded their runs in the fence too.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
import dispatcher as D  # noqa: E402

FLEET_VENV = pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet" / "venv"


def main(argv: list[str]) -> int:
    state, commit, mobile = pathlib.Path(argv[0]).resolve(), argv[1], pathlib.Path(argv[2])
    fleet = D.Fleet(state=state, venv=FLEET_VENV, mobile=mobile.resolve())
    c = fleet.check_run(ROOT, commit, full=True)
    print(f"ok={c.ok} commit={c.commit}")
    print(c.line or f"no regression line: {c.why}")
    print("the whole output:", sorted((state / "runs").glob("*_check/run/check.txt"))[-1])
    return 0 if c.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
