"""Phase 399 — the fleet's cost ledger, made true (F254, F255).

F254: tests that called a rank with a stand-in wrote their rows into the
real ledger. Every test now writes a file of its own
(`support/ledger_guard.py`'s autouse fixture), a run of the suite that
changes the real ledger fails (its check), and readers skip the stand-in's
rows by a named rule (`rank_call.STAND_IN_SESSION`).

F255: the Chief Engineer's sessions never reached the ledger. Each now goes
in once when it ends, a resumed one is not counted twice, every line names
its phase, issue and run, and kept run folders are read in once.

The nested runs below run pytest under a throwaway HOME, so a broken guard
writes nowhere real. The replayed session is a real `claude -p
--output-format json` result (the Science Officer's on 371, 2026-11-07, as
its journal kept it): the Engineer's `session.json` is the same command's
output, and no real Engineer session survived the prune (F255).
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(ROOT / "tests"))

import dispatcher as D  # noqa: E402
import journal  # noqa: E402
import rank_call  # noqa: E402
import test_phase389_dispatcher as W  # noqa: E402
from support import ledger_guard as G  # noqa: E402
from test_phase389_dispatcher import FakeEngineer, go_to_approved, step  # noqa: E402

#: 389's test world: a real git origin, `gh` and the model as stand-ins.
world = W.world

REAL = SKILL / "fixtures" / "f255" / "claude_result_scout_371.json"
REAL_SESSION = "4d03aa2e-7d15-4aae-820e-a6faed7a398c"


def ledger() -> pathlib.Path:
    return pathlib.Path(os.environ["FLEET_LEDGER"])


def rows() -> list[dict]:
    return rank_call.rows(ledger(), stand_ins=True)


def a_call(session: str = "sess-1", **kw) -> rank_call.Call:
    return rank_call.Call("xo", rank_call.FABLE, session, [rank_call.FABLE], 1, 2, 3, 4, 0.5, 1,
                          2.0, "2026-11-08T00:00:00-05:00", None, "", **kw)


# ------------------------------------------------------------------ F254
def test_every_test_has_a_ledger_of_its_own():
    p = ledger()
    assert p != pathlib.Path.home() / G.DEFAULT
    assert "fleet_ledger" in str(p) and not p.exists()
    assert rank_call.record(a_call()) == p and len(rows()) == 1


def test_two_tests_do_not_share_a_ledger_file(request):
    assert ledger().name != getattr(request.config, "_399_seen", None)
    request.config._399_seen = ledger().name


def test_the_check_takes_appended_fleet_rows_and_refuses_any_other(tmp_path):
    runs = tmp_path / "runs"
    (runs / "20261108_000000_xo_371").mkdir(parents=True)
    (runs / "20261108_000000_xo_371" / "stage.json").write_text(
        json.dumps({"calls": [{"session": "real-xo"}]}))
    (runs / "20261108_010000_engineer_371" / "run").mkdir(parents=True)
    (runs / "20261108_010000_engineer_371" / "run" / "session.json").write_text(
        json.dumps({"type": "result", "session_id": "real-eng"}))
    before = b'{"session_id": "old"}\n'
    fleet = before + b'{"session_id": "real-xo"}\n{"session_id": "real-eng"}\n'
    assert G.foreign_rows(before, before, runs) == []
    assert G.foreign_rows(None, None, runs) == []
    assert G.foreign_rows(before, fleet, runs) == []                  # the control
    bad = G.foreign_rows(before, fleet + b'{"session_id": "sess-1"}\n', runs)
    assert len(bad) == 1 and "sess-1" in bad[0]
    assert G.foreign_rows(before, b'{"session_id": "new"}\n', runs)[0].startswith(
        "the ledger's existing")                                         # rewritten
    assert G.foreign_rows(before, before + b"not json\n", runs)


NESTED = '''
import os, pathlib, sys
sys.path.insert(0, {skill!r})
import rank_call

def test_writes():
    {body}
    rank_call.record(rank_call.Call("xo", "m", {sid!r}, [], 1, 0, 0, 1, 0.0, 1, 1.0, "t", None, ""))
'''


def nested(tmp_path: pathlib.Path, *, body: str = "pass", sid: str = "sess-1",
           plant: str | None = None, guard: bool = True) -> tuple[subprocess.CompletedProcess,
                                                                   pathlib.Path]:
    """One test in a pytest of its own, HOME a throwaway folder, FLEET_LEDGER
    unset: what the suite's guard does with a test that writes the ledger."""
    home = tmp_path / "home"
    real = home / G.DEFAULT
    if plant:
        run = home / G.DEFAULT.parent / "runs" / "20261108_000000_xo_1"
        run.mkdir(parents=True)
        (run / "stage.json").write_text(json.dumps({"calls": [{"session": plant}]}))
    t = tmp_path / "t" / "test_nested.py"
    t.parent.mkdir()
    t.write_text(NESTED.format(skill=str(SKILL), body=body, sid=sid))
    (t.parent / "pytest.ini").write_text("[pytest]\naddopts =\n")
    env = {k: v for k, v in os.environ.items() if k not in ("FLEET_LEDGER", "FLEET_STATE",
                                                            "PYTEST_XDIST_WORKER")}
    env.update(HOME=str(home), PYTHONPATH=str(ROOT / "tests"))
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:xdist",
           *(["-p", "support.ledger_guard"] if guard else []), str(t)]
    return subprocess.run(cmd, cwd=t.parent, env=env, capture_output=True, text=True,
                          timeout=120), real


def test_a_suite_with_the_guard_leaves_the_ledger_alone(tmp_path):
    r, real = nested(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not real.exists()


def test_a_test_past_the_fixture_fails_the_suite_and_says_so(tmp_path):
    r, real = nested(tmp_path, body='os.environ.pop("FLEET_LEDGER")')
    assert r.returncode == 1, r.stdout + r.stderr
    assert "the fleet's cost ledger" in r.stdout and "sess-1" in r.stdout
    assert "1 passed" in r.stdout                    # the test passed; the run did not
    assert len(real.read_text().splitlines()) == 1  # under the throwaway HOME only


def test_without_the_guard_the_same_test_writes_the_ledger_and_passes(tmp_path):
    """The control: what F254 was. The same test, no guard, writes the default
    ledger and the run is green."""
    r, real = nested(tmp_path, guard=False)
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(real.read_text().splitlines()) == 1


def test_a_row_the_fleet_wrote_meanwhile_does_not_fail_the_suite(tmp_path):
    r, real = nested(tmp_path, body='os.environ.pop("FLEET_LEDGER")', sid="real-1",
                     plant="real-1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(real.read_text().splitlines()) == 1


def test_readers_skip_the_stand_ins_rows_and_only_those(tmp_path):
    p = tmp_path / "calls.jsonl"
    for sid in ("sess-1", REAL_SESSION, "sess-10", "sess-1"):
        rank_call.record(a_call(sid), p)
    with p.open("a") as f:
        f.write('{"session_id": "cut off mid')            # a write cut mid-line
    assert [r["session_id"] for r in rank_call.rows(p)] == [REAL_SESSION, "sess-10"]
    assert len(rank_call.rows(p, stand_ins=True)) == 4
    assert rank_call.is_stand_in({"session_id": "sess-1"})
    assert not rank_call.is_stand_in({"session_id": "sess-10"})       # the planted control
    s = rank_call.summary(p)
    assert "2 rows (2 stand-in rows left out)" in s and "xo: 2 rows, $1.00" in s


# ------------------------------------------------------------------ F255
def test_a_real_result_becomes_an_engineer_row():
    data = REAL.read_bytes()
    c = rank_call.session_call(data, model=rank_call.OPUS, wall_s=None, at="t", phase="371",
                               issue=54, run="r1", source="session")
    assert (c.rank, c.session_id, c.served) == ("engineer", REAL_SESSION, [rank_call.HAIKU])
    assert (c.input_tokens, c.cache_write_tokens, c.cache_read_tokens, c.output_tokens) == \
        (2, 37953, 0, 5159)
    assert c.cost_usd == pytest.approx(0.0101703) and c.turns == 2 and c.wall_s == 25.7
    assert (c.phase, c.issue, c.run, c.source) == ("371", 54, "r1", "session")
    assert c.key == rank_call.session_key("r1", data)
    nothing = rank_call.session_call(b"", model="m", wall_s=3.0, at="t", phase=None, issue=None,
                                     run="r2", source="session")
    assert (nothing.session_id, nothing.cost_usd, nothing.wall_s) == ("", 0.0, 3.0)


class RealEngineer(FakeEngineer):
    """389's stand-in Engineer, printing a real result instead of its stub."""

    def __call__(self, cmd, stdout, stderr, **kw):
        class Out:
            def write(self, s):
                stdout.write(REAL.read_text())

            def flush(self):
                stdout.flush()
        return super().__call__(cmd, Out(), stderr, **kw)


def engineer_rows() -> list[dict]:
    return [r for r in rows() if r["rank"] == "engineer"]


def test_the_engineers_session_reaches_the_ledger_once_with_its_stage(world):
    fleet, host, clock, origin, engineer, *_ = world
    fleet.popen = RealEngineer()
    go_to_approved(world)
    step(clock, fleet, host)                                # the Engineer
    found = engineer_rows()
    assert len(found) == 1, found
    r = found[0]
    run = r["run"]
    assert run.endswith("_engineer_902") and (fleet.runs / run / "run" / "session.json").is_file()
    assert (r["phase"], r["issue"], r["source"], r["session_id"]) == \
        ("902", 31, "session", REAL_SESSION)
    assert r["model"] == rank_call.OPUS and r["cost_usd"] == pytest.approx(0.0101703)
    assert r["key"] == rank_call.session_key(run, (fleet.runs / run / "run" / "session.json")
                                             .read_bytes())
    # every rank's line names its phase, issue and run
    for x in rows():
        assert x["phase"] == "902" and x["issue"] == 31 and x["run"], x
        assert (fleet.runs / x["run"]).is_dir()


def resume_session(fleet, run: pathlib.Path):
    j = journal.Journal.load(run)
    j.resumed = True
    runner = D.FencedRunner(fleet, run / "clone", run / "run", journal=j)
    return runner.session(D.engineer.session_argv(), "brief", watch=lambda: None)


def test_a_resumed_session_is_not_counted_twice(world):
    fleet, host, clock, *_ = world
    fleet.popen = RealEngineer()
    go_to_approved(world)
    step(clock, fleet, host)
    run = fleet.runs / engineer_rows()[0]["run"]
    before = ledger().read_bytes()
    r, reason = resume_session(fleet, run)               # read back from its files
    assert json.loads(r.stdout)["session_id"] == REAL_SESSION and reason is None
    assert fleet.popen.runs == 1 and ledger().read_bytes() == before


def test_a_stage_cut_between_the_end_and_the_ledger_writes_it_once_on_resume(world):
    fleet, host, clock, *_ = world
    fleet.popen = RealEngineer()
    go_to_approved(world)
    step(clock, fleet, host)
    run = fleet.runs / engineer_rows()[0]["run"]
    kept = [x for x in rows() if x["rank"] != "engineer"]
    ledger().write_text("".join(json.dumps(x) + "\n" for x in kept))   # the write never happened
    resume_session(fleet, run)
    resume_session(fleet, run)
    assert len(engineer_rows()) == 1 and engineer_rows()[0]["run"] == run.name


def test_a_session_a_usage_limit_ended_is_one_row_however_often_it_is_read(world):
    """The part a usage limit ended printed its own result, and is spend: one
    row. Resumed, the stage reads that result back from its files (and raises
    the limit again: F256, filed by this phase and left), and adds nothing."""
    fleet, *_ = world
    limited = (SKILL / "fixtures" / "dispatcher" / "rate_limited.json").read_text()

    def popen(cmd, stdout, stderr, **kw):
        stdout.write(limited)
        stdout.flush()
        return type("Proc", (), {"poll": lambda s: 1, "returncode": 1,
                                 "terminate": lambda s: None})()
    fleet.popen = popen
    run = fleet.new_run("engineer_902", {"stage": "engineer", "issue": 31, "phase": "902"})
    (run / "clone").mkdir()
    with pytest.raises(D.RateLimited):
        D.FencedRunner(fleet, run / "clone", run / "run", journal=journal.Journal.load(run)) \
            .session(D.engineer.session_argv(), "brief", watch=lambda: None)
    assert [x["session_id"] for x in engineer_rows()] == ["sess-limited-1"]
    for _ in range(2):
        j = journal.Journal.load(run)
        j.resumed = True
        with pytest.raises(D.RateLimited):
            D.FencedRunner(fleet, run / "clone", run / "run", journal=j).session(
                D.engineer.session_argv(), "brief", watch=lambda: None)
    assert [x["session_id"] for x in engineer_rows()] == ["sess-limited-1"]


def test_a_cut_session_resumed_with_resume_is_one_row(world):
    """A session a restart cut printed nothing, so nothing of it is known; the
    part `--resume` ran after it is one row, and reading it back adds none."""
    fleet, *_ = world
    argvs = []

    def popen(cmd, stdout, stderr, **kw):
        argvs.append(cmd)
        stdout.write(REAL.read_text())
        stdout.flush()
        return type("Proc", (), {"poll": lambda s: 0, "returncode": 0,
                                 "terminate": lambda s: None})()
    fleet.popen = popen
    run = fleet.new_run("engineer_902", {"stage": "engineer", "issue": 31, "phase": "902"})
    (run / "clone").mkdir()
    # the cut: the call began, its transcript named the session, it printed nothing
    j = journal.Journal.load(run)
    j.begin_call(0, journal.call_key(D.engineer.session_argv()), [])
    j.update_call(0, session=REAL_SESSION)
    (run / "run" / "session.json").write_text("")
    for _ in range(2):
        j = journal.Journal.load(run)
        j.resumed = True
        D.FencedRunner(fleet, run / "clone", run / "run", journal=j).session(
            D.engineer.session_argv(), "brief", watch=lambda: None)
    assert len(argvs) == 1 and argvs[0][argvs[0].index("--resume") + 1] == REAL_SESSION
    got = engineer_rows()
    assert [(x["session_id"], x["run"]) for x in got] == [(REAL_SESSION, run.name)], got


def plant_run(runs: pathlib.Path, name: str, out: str | None, record: dict | None = None):
    p = runs / name
    (p / "run").mkdir(parents=True)
    if record is not None:
        journal.Journal.create(p, record, D.dt.datetime(2026, 11, 8, tzinfo=D.dt.timezone.utc))
    if out is not None:
        (p / "run" / "session.json").write_text(out)
    return p


def test_kept_run_folders_are_read_in_once(world):
    fleet, *_ = world
    lines: list[str] = []
    fleet.log = lines.append
    real = REAL.read_text()
    plant_run(fleet.runs, "20261107_230000_engineer_371", real,
              {"stage": "engineer", "issue": 54, "phase": "371"})
    plant_run(fleet.runs, "20261107_220000_engineer_370", "")             # cut: no result
    plant_run(fleet.runs, "20261107_210000_xo_371", None, {"stage": "xo"})  # no session
    assert fleet.ledger_read_in(dry_run=True) == 1 and not ledger().exists()
    assert fleet.ledger_read_in() == 1
    assert lines[-1] == "the ledger read-in: 1 Engineer session(s) added, 0 already there"
    (r,) = rows()
    assert (r["rank"], r["phase"], r["issue"], r["run"], r["source"], r["model"]) == \
        ("engineer", "371", 54, "20261107_230000_engineer_371", "read-in", rank_call.HAIKU)
    before = ledger().read_bytes()
    assert fleet.ledger_read_in() == 0                                    # the second pass
    assert lines[-1] == "the ledger read-in: 0 Engineer session(s) added, 1 already there"
    assert ledger().read_bytes() == before


def test_a_session_recorded_as_it_ended_is_not_read_in_again(world):
    fleet, host, clock, *_ = world
    fleet.popen = RealEngineer()
    go_to_approved(world)
    step(clock, fleet, host)
    before = ledger().read_bytes()
    assert fleet.ledger_read_in() == 0 and ledger().read_bytes() == before


def test_the_search_on_start_reads_kept_folders_in(world):
    fleet, host, *_ = world
    lines: list[str] = []
    fleet.log = lines.append
    plant_run(fleet.runs, "20261107_230000_engineer_371", REAL.read_text(),
              {"stage": "engineer", "issue": 54, "phase": "371"})
    fleet.recover()
    assert "the ledger read-in: 1 Engineer session(s) added, 0 already there" in lines
    assert any(ln.startswith("the search on start:") for ln in lines)
    assert [r["source"] for r in rows()] == ["read-in"]
