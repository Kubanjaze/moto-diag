"""Phase 394's regression of record: one model-free run, as the fleet makes it.

    .venv/bin/python docs/phases/in_progress/394_regression.py <state-dir> <commit> <mobile-dir>

This branch's `Fleet.check_run` (`wholetree.sh --full`, then `regression.sh`)
on <commit>, in a fresh clone in the fence, no model, no token, with the
fleet's virtualenv, in its own state folder so the service's runs are not
touched. <mobile-dir> is mounted as `../moto-diag-mobile`.

Why not this checkout (the phase log, 2026-10-28): gate 11 reads the mobile
repository beside the checkout, and the one on this machine carries an
unpushed commit (`7489fd5`, "API schema: refresh for backend Phase 303 …
push after 303 merges") that describes 303's routes. Every backend without
303 fails gate 11 against it, master included. The run of record uses a
clean clone of the mobile repository at its published `origin/main`.
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
