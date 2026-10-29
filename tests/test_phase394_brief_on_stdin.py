"""Phase 394 — a rank's brief goes on standard input, never in argv.

PR #34 made the Red Team's brief larger than Linux's limit on one argument
(131072 bytes with its NUL), so `claude -p <brief>` could not start: 69
"cycle failed" lines and 69 "Red Team started" comments on #31.

The calls here are real processes. A stand-in `claude` on PATH reads its
stdin, records what came (its argv, the size of its stdin, whether the
planted marker was in it) and answers as claude does; the fenced calls go
through a stand-in fence that drops its own arguments and execs the rest,
as `fence.sh` does. So the kernel's real limit applies to every argv, and
the first test shows it refusing the shape this phase removed.
"""
from __future__ import annotations

import datetime as dt
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
import captain  # noqa: E402
import dispatcher as D  # noqa: E402
import engineer as E  # noqa: E402
import journal as J  # noqa: E402
import plan_check  # noqa: E402
import quartermaster  # noqa: E402
import rank_call  # noqa: E402
import red_team  # noqa: E402
import scout  # noqa: E402
import xo  # noqa: E402
import yeoman  # noqa: E402
from plan_check import FIXTURE_PHASE, GOOD  # noqa: E402
import test_phase389_dispatcher as T389  # noqa: E402
from test_phase388_dispatcher import T0, claude_json  # noqa: E402
from test_phase389_dispatcher import go_to_approved, labels, step, world  # noqa: E402,F401
from test_phase389_red_team import TABLE  # noqa: E402
from test_phase392_ranks_cite import repo  # noqa: E402,F401  (the fixture)

#: One argument's limit, with its terminating NUL (`394_step0.md`, S0-1).
ARG_LIMIT = 131072
MARK = "MARK-394-THE-WHOLE-BRIEF-ARRIVED"
#: 300 KiB of brief, the marker at its end: only a whole brief carries it.
BIG = "a line of context that the rank reads in full.\n" * (300 * 1024 // 47 + 1) + MARK

FAKE_CLAUDE = """#!/usr/bin/env python3
import json, pathlib, sys
here = pathlib.Path(__file__).resolve().parent
brief = sys.stdin.read()
seen = here / "seen.jsonl"
with seen.open("a") as f:
    f.write(json.dumps({"argv": sys.argv[1:], "stdin": len(brief.encode()),
                        "whole": brief.endswith(%r) or %r in brief}) + "\\n")
n = len(seen.read_text().splitlines()) - 1
print(json.loads((here / "replies.json").read_text())[n])
""" % (MARK, MARK)

FAKE_FENCE = """#!/bin/bash
while [ "$1" != "--" ]; do shift; done
shift
exec "$@"
"""


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("FLEET_LEDGER", str(tmp_path / "calls.jsonl"))


class Claude:
    """The stand-in `claude`, first on PATH, and what it saw."""

    def __init__(self, bin_dir: pathlib.Path):
        self.dir = bin_dir

    def answer(self, *structured: dict, model: str) -> None:
        (self.dir / "replies.json").write_text(
            json.dumps([claude_json(s, model=model) for s in structured]))

    @property
    def seen(self) -> list[dict]:
        p = self.dir / "seen.jsonl"
        return [json.loads(ln) for ln in p.read_text().splitlines()] if p.is_file() else []

    def got_the_whole_brief(self, calls: int = 1) -> None:
        assert len(self.seen) == calls, self.seen
        for s in self.seen:
            assert s["stdin"] >= 300 * 1024 and s["whole"], s["stdin"]
            assert max(len(a.encode()) + 1 for a in s["argv"]) < ARG_LIMIT
            p = s["argv"].index("-p")
            assert s["argv"][p + 1].startswith("--")          # no brief after -p


@pytest.fixture
def claude(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    exe = bin_dir / "claude"
    exe.write_text(FAKE_CLAUDE)
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return Claude(bin_dir)


def test_the_kernel_refuses_the_old_shape():
    """The control: what `rank_call.command` built before this phase."""
    with pytest.raises(OSError) as e:
        subprocess.run(["true", "-p", BIG, "--model", rank_call.OPUS])
    assert e.value.errno == 7


def test_the_command_has_no_brief():
    cmd = rank_call.command(rank_call.OPUS, {"type": "object"})
    assert cmd[:4] == ["claude", "-p", "--model", rank_call.OPUS]
    assert cmd[-2] == "--json-schema"
    assert E.session_argv()[:3] == ["claude", "-p", "--model"]


# ------------------------------------------- each rank, its brief on stdin
class TestEachRank:
    def test_red_team(self, claude, repo):
        claude.answer({"verdict": "clear", "findings": [], "refuter_pass": TABLE},
                      model=rank_call.OPUS)
        v, _ = red_team.review(FIXTURE_PHASE, 1, BIG, clone=repo, run=subprocess.run)
        assert v["verdict"] == "clear"
        claude.got_the_whole_brief()

    def test_quartermaster(self, claude, repo):
        claude.answer({"verdict": "merge", "failed": [], "summary": "Fine."},
                      model=rank_call.OPUS)
        quartermaster.judge(FIXTURE_PHASE, BIG, clone=repo, run=subprocess.run)
        claude.got_the_whole_brief()

    def test_captain_recommendation(self, claude, repo):
        claude.answer({"decision": "merge", "lines": ["It ships.", "Checked.", "Clean."]},
                      model=rank_call.FABLE)
        captain.recommend(FIXTURE_PHASE, BIG, clone=repo, run=subprocess.run)
        claude.got_the_whole_brief()

    def test_captain_plan(self, claude, repo):
        impl = repo / plan_check.plan_paths(FIXTURE_PHASE)[0]
        plan = impl.read_text()
        impl.unlink()
        claude.answer({"implementation_md": plan}, model=rank_call.FABLE)
        captain.write_plan(FIXTURE_PHASE, "| 900 |", BIG, "step0", clone=repo, run=subprocess.run)
        claude.got_the_whole_brief()

    def test_science_officer_terms_and_judgement(self, claude, repo):
        fix = SKILL / "fixtures" / "scout"
        claude.answer(json.loads((fix / "terms_good.json").read_text()),
                      json.loads((fix / "assess_good.json").read_text()), model=rank_call.HAIKU)
        scout.terms(BIG, "row", cwd=repo, run=subprocess.run)
        scout.assess(BIG, "row", "table", [], "ctx", cwd=repo, run=subprocess.run)
        claude.got_the_whole_brief(calls=2)

    def test_executive_officer(self, claude, repo, monkeypatch):
        real = xo.build_prompt
        monkeypatch.setattr(xo, "build_prompt", lambda *a: real(*a) + BIG)
        claude.answer({"verdict": "approve", "items": [], "reason": ""}, model=rank_call.FABLE)
        assert xo.review(FIXTURE_PHASE, None, repo=repo, label=False, run=subprocess.run,
                         out=lambda s: None) == 0
        claude.got_the_whole_brief()

    def test_yeoman(self, claude, tmp_path, monkeypatch):
        monkeypatch.setattr(yeoman, "facts", lambda *a, **k: BIG)
        claude.answer({"summary": "A quiet day."}, model=rank_call.HAIKU)
        (tmp_path / "root").mkdir()
        assert yeoman.digest(dt.date(2026, 10, 28), root=tmp_path / "root", run=subprocess.run,
                             out=lambda s: None) == 0
        claude.got_the_whole_brief()


# ------------------------------------------------- through the fence
def fleet(tmp_path: pathlib.Path) -> D.Fleet:
    fence = tmp_path / "fence.sh"
    fence.write_text(FAKE_FENCE)
    fence.chmod(0o755)
    return D.Fleet(state=tmp_path / "state", token="sk-ant-oat01-test-token",
                   host=subprocess.run, fence=fence, workspace_docs=tmp_path,
                   popen=subprocess.Popen, sleep=lambda s: None, venv=tmp_path / "no-venv",
                   mobile=tmp_path / "no-mobile")


class TestThroughTheFence:
    def test_a_rank_call(self, claude, repo, tmp_path):
        claude.answer({"verdict": "clear", "findings": [], "refuter_pass": TABLE},
                      model=rank_call.HAIKU)
        (tmp_path / "run").mkdir()
        runner = D.FencedRunner(fleet(tmp_path), repo, tmp_path / "run")
        red_team.review(FIXTURE_PHASE, 1, BIG, clone=repo, run=runner, model=rank_call.HAIKU)
        claude.got_the_whole_brief()

    def test_a_resumed_rank_call(self, claude, repo, tmp_path):
        """A call cut off, run again with `--resume`: the brief still on stdin."""
        claude.answer({"verdict": "clear", "findings": [], "refuter_pass": TABLE},
                      model=rank_call.HAIKU)
        run = tmp_path / "stage"
        (run / "run").mkdir(parents=True)
        j = J.Journal.create(run, {"stage": "red_team", "session": "sess-cut"},
                             dt.datetime(2026, 10, 28, tzinfo=dt.timezone.utc))
        j.resumed = True
        runner = D.FencedRunner(fleet(tmp_path), repo, run / "run", journal=j)
        red_team.review(FIXTURE_PHASE, 1, BIG, clone=repo, run=runner, model=rank_call.HAIKU)
        claude.got_the_whole_brief()
        assert claude.seen[0]["argv"][:2] == ["--resume", "sess-cut"]

    def test_the_chief_engineers_session(self, claude, tmp_path):
        claude.answer({}, model=rank_call.HAIKU)
        (tmp_path / "run").mkdir()
        runner = D.FencedRunner(fleet(tmp_path), tmp_path, tmp_path / "run")
        brief = E.session_brief("303", 31, findings=BIG, rnd=1)
        r, reason = runner.session(E.session_argv(model=rank_call.HAIKU), brief,
                                   watch=lambda: None, every=0)
        assert reason is None and r.returncode == 0
        claude.got_the_whole_brief()


def test_the_journal_keys_a_call_the_same_before_and_after():
    """A stage cut across the upgrade replays its calls: the key is the
    command without its brief, in either shape."""
    tools = ("--tools", "Read,Grep,Glob")
    old = ["claude", "-p", BIG, "--model", rank_call.OPUS, *tools, "--output-format", "json"]
    new = rank_call.command(rank_call.OPUS, tools=tools)
    assert J.call_key(old) == J.call_key(new)
    assert J.call_key(new) != J.call_key(rank_call.command(rank_call.HAIKU, tools=tools))
    resumed = ["claude", "--resume", "s1", *new[1:]]
    assert J.call_key(resumed) == J.call_key(new)
    eng_old = ["claude", "-p", "brief", *E.session_argv()[2:]]
    assert J.call_key(eng_old) == J.call_key(E.session_argv())


# ----------------------------------- a stage that cannot start stops once
def too_long(fleet_: D.Fleet):
    """The host as on 2026-10-28: a model call's launch raises Errno 7."""
    real = fleet_.host

    def host(cmd, **kw):
        if cmd[0] == str(fleet_.fence) and "/usage" not in cmd:
            raise OSError(7, "Argument list too long", str(fleet_.fence))
        return real(cmd, **kw)
    fleet_.host = host
    return real


def to_review(world):
    fleet_, host, clock, *_ = world
    go_to_approved(world)
    step(clock, fleet_, host)                                      # the Engineer, its PR
    assert labels(host) == ["mission", "review:open"]


def said(host, start: str) -> int:
    return sum(c.startswith(start) for c in host.comments(31))


def test_a_launch_oserror_stops_the_stage_once(world):
    fleet_, host, clock, *_ = world
    to_review(world)
    before = len(host.comments(31))
    too_long(fleet_)
    step(clock, fleet_, host)                                      # no raise: a stop
    assert labels(host) == ["mission", "review:open"]              # label unchanged
    new = host.comments(31)[before:]
    assert [c.split(" run=")[0] for c in new] == [f"{D.STARTED_M} rank=red-team",
                                                  f"{D.MARKER} stopped rank=red-team"]
    assert "the model call could not start: [Errno 7] Argument list too long" in new[-1]
    calls = len(host.fenced)
    for _ in range(3):
        step(clock, fleet_, host)                                  # not retried
    assert len(host.comments(31)) == before + 2 and len(host.fenced) == calls
    assert "cycle failed" not in "\n".join(world[6])


def test_the_engineers_launch_oserror_stops_once(world):
    fleet_, host, clock, *_ = world
    go_to_approved(world)

    def popen(cmd, **kw):
        raise OSError(7, "Argument list too long", cmd[0])
    fleet_.popen = popen
    step(clock, fleet_, host)
    assert "the model call could not start" in host.comments(31)[-1]
    n = len(host.comments(31))
    step(clock, fleet_, host)
    assert len(host.comments(31)) == n


# ------------------------------------------ "started" once per stage run
def test_started_is_said_once_over_a_failed_run_and_its_retries(world):
    fleet_, host, clock, *_ = world
    to_review(world)
    real = fleet_.host

    def broken(cmd, **kw):
        if cmd[0] == str(fleet_.fence) and "/usage" not in cmd:
            raise RuntimeError("a failure that is not a stop")
        return real(cmd, **kw)
    fleet_.host = broken
    for _ in range(3):
        clock.t += dt.timedelta(minutes=5)
        with pytest.raises(RuntimeError):
            fleet_.cycle()
    assert said(host, f"{D.STARTED_M} rank=red-team") == 1
    assert sum("its `started` comment stands" in ln for ln in world[6]) == 2
    fleet_.host = real
    step(clock, fleet_, host, claude_json({"verdict": "clear", "findings": [],
                                           "refuter_pass": TABLE}, model=rank_call.OPUS))
    assert said(host, f"{D.STARTED_M} rank=red-team") == 1
    assert "review:clear" in labels(host)


def test_only_a_failed_runs_started_stands_for_a_retry(world):
    """A `started` marker last on the issue stands for the retry only when
    its run ended `failed`, and only for the same rank."""
    fleet_, host, clock, *_ = world
    host.issue(31, T389.TITLE, T389.TRIAL, {"mission": T0})
    for outcome, kept in ((None, False), ("stopped: x", False), ("failed: OSError: y", True)):
        clock.t += dt.timedelta(minutes=1)
        run = fleet_.new_run("red_team_902", {"stage": "red_team", "issue": 31})
        if outcome:
            J.Journal.load(run).end(outcome, clock())
        fleet_.say(31, f"{D.STARTED_M} rank=red-team run={run.name} -->", "started")
        assert fleet_.failed_start(31, "red-team") == (run.name if kept else None), outcome
        assert fleet_.failed_start(31, "captain") is None


def test_started_is_said_again_for_a_new_stage_run(world):
    """After a stop, the operator applies the label again: a new stage run."""
    fleet_, host, clock, *_ = world
    to_review(world)
    real = too_long(fleet_)
    step(clock, fleet_, host)
    fleet_.host = real
    clock.t += dt.timedelta(minutes=1)
    host.issues[31]["labels"].remove("review:open")
    host.label(31, "review:open")
    step(clock, fleet_, host, claude_json({"verdict": "clear", "findings": [],
                                           "refuter_pass": TABLE}, model=rank_call.OPUS))
    assert said(host, f"{D.STARTED_M} rank=red-team") == 2
    assert "review:clear" in labels(host)
