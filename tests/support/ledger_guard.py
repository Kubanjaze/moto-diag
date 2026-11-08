"""Phase 399 (F254): no test writes the fleet's real cost ledger.

The ledger is `~/.local/state/motodiag/fleet/calls.jsonl`, or `$FLEET_LEDGER`
(`rank_call.LEDGER`, `rank_call.record`). Before this phase every test that
called a rank with a stand-in and did not set `FLEET_LEDGER` itself appended
its rows there: on 2026-11-07, 5,616 of the desktop's 5,724 rows.

Two parts, imported into `tests/conftest.py` so they run with every suite:

- **The fixture**, `_never_the_real_cost_ledger`, autouse: every test runs
  with `FLEET_LEDGER` naming a file of its own under the session's
  temporary directory. A test that sets `FLEET_LEDGER` itself still wins
  (monkeypatch's later `setenv`), and a subprocess inherits the variable.
- **The check**, `pytest_sessionstart` / `pytest_sessionfinish`, on the
  controller only: the real ledger is read before and after the run. The
  run fails when the bytes that were there changed, or when a row was
  appended that is not the fleet's own. The fleet runs beside the suite on
  the home desktop and appends real calls meanwhile; a row is the fleet's
  when its session id is named in one of the fleet's run folders (a
  journal's call, or an Engineer's `session.json`). No test can make such a
  row: no test reaches the network or a real `claude`.

What the check guards is the path the suite started with: `$FLEET_LEDGER`
when it is set, the default otherwise. A nested pytest a test spawns
inherits that test's own file, and guards it.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import pathlib

import pytest

DEFAULT = pathlib.Path(".local") / "state" / "motodiag" / "fleet" / "calls.jsonl"
_count = itertools.count()
_state: dict = {}


def real_ledger() -> pathlib.Path:
    return pathlib.Path(os.environ.get("FLEET_LEDGER") or pathlib.Path.home() / DEFAULT)


def fleet_runs() -> pathlib.Path:
    state = os.environ.get("FLEET_STATE")
    base = pathlib.Path(state) if state else pathlib.Path.home() / DEFAULT.parent
    return base / "runs"


def _read(p: pathlib.Path) -> bytes | None:
    try:
        return p.read_bytes()
    except OSError:
        return None


def fleet_sessions(runs: pathlib.Path) -> set[str]:
    """Every session id the fleet's run folders name: each journal's calls,
    and each Engineer `session.json`'s last line."""
    found: set[str] = set()
    if not runs.is_dir():
        return found
    for p in runs.iterdir():
        try:
            data = json.loads((p / "stage.json").read_text(encoding="utf-8"))
            found.update(c.get("session") for c in data.get("calls", []) if c.get("session"))
        except (OSError, ValueError, AttributeError):
            pass
        try:
            last = (p / "run" / "session.json").read_text(errors="replace").strip().splitlines()
            sid = json.loads(last[-1]).get("session_id") if last else None
            if sid:
                found.add(sid)
        except (OSError, ValueError, AttributeError):
            pass
    return found


def foreign_rows(before: bytes | None, after: bytes | None, runs: pathlib.Path) -> list[str]:
    """What a run of the suite did to the ledger: [] when nothing a test
    could have written. Otherwise one line per problem."""
    before, after = before or b"", after or b""
    if after[:len(before)] != before:
        return [f"the ledger's existing {len(before)} bytes changed (now {len(after)} bytes)"]
    new = after[len(before):].decode("utf-8", "replace").splitlines()
    if not new:
        return []
    known = fleet_sessions(runs)
    bad = []
    for ln in new:
        try:
            sid = json.loads(ln).get("session_id")
        except (ValueError, AttributeError):
            sid = None
        if not sid or sid not in known:
            bad.append(f"a row the fleet did not write: {ln[:160]}")
    return bad


@pytest.fixture(scope="session")
def _cost_ledger_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("fleet_ledger")


@pytest.fixture(autouse=True)
def _never_the_real_cost_ledger(_cost_ledger_dir, monkeypatch):
    monkeypatch.setenv("FLEET_LEDGER", str(_cost_ledger_dir / f"calls_{next(_count)}.jsonl"))


def _controller(session) -> bool:
    return not hasattr(session.config, "workerinput")


def pytest_sessionstart(session):
    if _controller(session):
        p = real_ledger()
        _state.update(path=p, before=_read(p), runs=fleet_runs())


def pytest_sessionfinish(session, exitstatus):
    if not _controller(session) or "path" not in _state:
        return
    p = _state["path"]
    problems = foreign_rows(_state["before"], _read(p), _state["runs"])
    if not problems:
        return
    before = _state["before"] or b""
    after = _read(p) or b""
    lines = [f"the fleet's cost ledger {p} was changed by this run of the suite (Phase 399, F254):",
             f"  before {len(before)} bytes, sha256 {hashlib.sha256(before).hexdigest()[:16]}",
             f"  after  {len(after)} bytes, sha256 {hashlib.sha256(after).hexdigest()[:16]}",
             *(f"  {x}" for x in problems[:10])]
    if len(problems) > 10:
        lines.append(f"  … and {len(problems) - 10} more")
    tr = session.config.pluginmanager.get_plugin("terminalreporter")
    for ln in lines:
        if tr is not None:
            tr.write_line(ln, red=True)
        else:
            print(ln)
    session.exitstatus = pytest.ExitCode.TESTS_FAILED
