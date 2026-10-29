"""Phase 393's regression of record: one model-free run, as the fleet makes it.

    .venv/bin/python docs/phases/in_progress/393_regression.py <state-dir> <commit>

This branch's `Fleet.check_run` (`wholetree.sh --full`, then `regression.sh`,
which since this phase measures coverage) on <commit>, in a fresh clone in
the fence, no model, no token, with the fleet's virtualenv, in its own state
folder so the service's runs are not touched. The mobile repository is the
operator's checkout, `~/Projects/moto-diag-mobile`, published at its
`origin/main` (303's API refresh pushed), as the fleet's own runs mount it.
394's script, with the coverage line and file printed too.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
import dispatcher as D  # noqa: E402

FLEET_VENV = pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet" / "venv"
MOBILE = pathlib.Path.home() / "Projects" / "moto-diag-mobile"


def main(argv: list[str]) -> int:
    state, commit = pathlib.Path(argv[0]).resolve(), argv[1]
    fleet = D.Fleet(state=state, venv=FLEET_VENV, mobile=MOBILE)
    c = fleet.check_run(ROOT, commit, full=True)
    print(f"ok={c.ok} commit={c.commit}")
    print(c.line or f"no regression line: {c.why}")
    out = sorted((state / "runs").glob("*_check/run/check.txt"))[-1]
    print("the whole output:", out)
    print("coverage data:", c.coverage or "(none)")
    for line in out.read_text(encoding="utf-8").splitlines():
        if line.startswith(("Line coverage of record:", "wholetree full:")):
            print(line)
    return 0 if c.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
