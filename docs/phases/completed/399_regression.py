"""Phase 399's regression of record: one model-free run, as the fleet makes it.

    .venv/bin/python docs/phases/completed/399_regression.py <state-dir> <commit> <mobile-dir>

398's driver, with the real cost ledger read before and after (the
prompt: "the regression of record leaves the real ledger unchanged (its
size and hash before and after, in the phase log)"). This branch's
`Fleet.check_run` (`wholetree.sh --full`, then `regression.sh`) on <commit>,
in a fresh clone in the fence, no model, no token, with the fleet's
virtualenv, in its own state folder. <mobile-dir> is a clean clone of the
mobile repository at its published `origin/main`, mounted as
`../moto-diag-mobile`.

The fleet runs beside it and may append real calls to the ledger
meanwhile, so "unchanged" is said as the suite's guard says it: the bytes
that were there are the same, and every appended row's session is named
in one of the fleet's run folders (`tests/support/ledger_guard.py`).
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
sys.path.insert(0, str(ROOT / "tests"))
import dispatcher as D  # noqa: E402
from support import ledger_guard as G  # noqa: E402

FLEET_VENV = pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet" / "venv"
LEDGER = pathlib.Path.home() / G.DEFAULT
RUNS = pathlib.Path.home() / G.DEFAULT.parent / "runs"


def said(label: str, b: bytes) -> None:
    print(f"the real ledger {label}: {len(b)} bytes, {b.count(b'\n')} rows, "
          f"sha256 {hashlib.sha256(b).hexdigest()}", flush=True)


def main(argv: list[str]) -> int:
    state, commit, mobile = pathlib.Path(argv[0]).resolve(), argv[1], pathlib.Path(argv[2])
    before = LEDGER.read_bytes()
    said("before", before)
    fleet = D.Fleet(state=state, venv=FLEET_VENV, mobile=mobile.resolve())
    c = fleet.check_run(ROOT, commit, full=True)
    after = LEDGER.read_bytes()
    said("after", after)
    problems = G.foreign_rows(before, after, RUNS)
    appended = after[len(before):].count(b"\n") if after[:len(before)] == before else None
    print(f"the ledger: {appended} row(s) appended meanwhile, "
          + ("every one the fleet's" if not problems else f"NOT the fleet's: {problems}"))
    print(f"ok={c.ok} commit={c.commit}")
    print(c.line or f"no regression line: {c.why}")
    print("the whole output:", sorted((state / "runs").glob("*_check/run/check.txt"))[-1])
    return 0 if c.ok and not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
