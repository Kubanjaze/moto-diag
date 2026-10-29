"""Phase 389 — the Captain: v1.0 that passes the checklist, or nothing.

What must hold: the model returns text and the script writes the one file
the Captain may change; a plan that fails `plan_check` gets one more call
with the failed items, and a second failure is a stop that leaves the
branch's plan as it was; a revision is given the XO's items and the plan as
it stands; the recommendation is three single lines, merge or hold.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(SKILL))

import captain  # noqa: E402
import rank_call  # noqa: E402
from plan_check import FIXTURE_PHASE, GOOD  # noqa: E402
from test_phase388_dispatcher import claude_json  # noqa: E402

IMPL = f"docs/phases/in_progress/{FIXTURE_PHASE}_implementation.md"
PLAN = (GOOD / IMPL).read_text()
NO_STOPS = PLAN[:PLAN.index("## Rule-1 stops anticipated")] + PLAN[PLAN.index("## Non-goals"):]
ROW = "| 900 | The phase under review | 🚧 | x |"


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("FLEET_LEDGER", str(tmp_path / "calls.jsonl"))


class Replies:
    def __init__(self, *structured, model=rank_call.FABLE):
        self.queue = [claude_json(s, model=model) for s in structured]
        self.calls: list[list[str]] = []
        self.briefs: list[str] = []          # each call's stdin (Phase 394)

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        self.briefs.append(kw["input"])
        return subprocess.CompletedProcess(cmd, 0, self.queue.pop(0), "")


@pytest.fixture
def clone(tmp_path):
    c = tmp_path / "clone"
    shutil.copytree(GOOD, c)
    (c / IMPL).unlink()                       # the Captain writes it
    return c


def step0(clone):
    return (clone / f"docs/phases/in_progress/{FIXTURE_PHASE}_step0.md").read_text()


def test_the_bad_fixture_really_fails_p8(clone):
    """The control for every case below: without its stops section the
    good plan fails P8 and nothing else."""
    import plan_check
    (clone / IMPL).write_text(NO_STOPS)
    assert set(plan_check.check(FIXTURE_PHASE, clone).failed) == {"P8"}


def test_a_plan_that_passes_is_written(clone):
    run = Replies({"implementation_md": PLAN})
    calls = captain.write_plan(FIXTURE_PHASE, ROW, "the prompt", step0(clone), clone=clone, run=run)
    assert len(calls) == 1 and (clone / IMPL).read_text() == PLAN
    cmd = run.calls[0]
    assert rank_call.FABLE in cmd and cmd[cmd.index("--tools") + 1] == "Read,Grep,Glob"
    assert "Bash" in cmd[cmd.index("--disallowedTools") + 1]


def test_a_failing_plan_gets_one_more_call_with_the_failures(clone):
    run = Replies({"implementation_md": NO_STOPS}, {"implementation_md": PLAN})
    calls = captain.write_plan(FIXTURE_PHASE, ROW, "", step0(clone), clone=clone, run=run)
    assert len(calls) == 2 and (clone / IMPL).read_text() == PLAN
    assert "P8 FAIL" in run.briefs[1] and "=== the plan as it stands ===" in run.briefs[1]


def test_failing_twice_is_a_stop_and_writes_nothing(clone):
    run = Replies({"implementation_md": NO_STOPS}, {"implementation_md": NO_STOPS})
    with pytest.raises(rank_call.Stop, match="still fails the checklist"):
        captain.write_plan(FIXTURE_PHASE, ROW, "", step0(clone), clone=clone, run=run)
    assert not (clone / IMPL).exists()


def test_a_failed_revision_restores_the_plan_it_had(clone):
    (clone / IMPL).write_text(PLAN)
    run = Replies({"implementation_md": NO_STOPS}, {"implementation_md": NO_STOPS})
    with pytest.raises(rank_call.Stop):
        captain.write_plan(FIXTURE_PHASE, ROW, "", step0(clone), clone=clone, run=run,
                           items=["Name the stops."])
    assert (clone / IMPL).read_text() == PLAN


def test_a_revision_is_given_the_xos_items_and_the_plan(clone):
    (clone / IMPL).write_text(PLAN)
    run = Replies({"implementation_md": PLAN})
    captain.write_plan(FIXTURE_PHASE, ROW, "", step0(clone), clone=clone, run=run,
                       items=["Fix the count in Logic."])
    prompt = run.briefs[0]
    assert "- Fix the count in Logic." in prompt and PLAN[:200] in prompt


def test_an_empty_plan_is_a_stop(clone):
    with pytest.raises(rank_call.Stop, match="empty"):
        captain.write_plan(FIXTURE_PHASE, ROW, "", step0(clone), clone=clone,
                           run=Replies({"implementation_md": "  "}))


class TestTheRecommendation:
    def test_three_lines(self, clone):
        v, _ = captain.recommend("900", "summary", clone=clone, run=Replies(
            {"decision": "merge", "lines": ["It ships x.", "All green.", "Merge."]}))
        assert v["decision"] == "merge"

    def test_the_measured_dry_run_passes_the_schema(self, clone):
        import json
        reply = json.loads((SKILL / "fixtures" / "dry_runs" / "recommend_hold.json").read_text())
        v, _ = captain.recommend("389A", "s", clone=clone, run=Replies(reply))
        assert v["decision"] == "hold" and len(v["lines"]) == 3

    @pytest.mark.parametrize("reply,why", [
        ({"decision": "maybe", "lines": ["a", "b", "c"]}, "no decision"),
        ({"decision": "hold", "lines": ["a", "b"]}, "three single lines"),
        ({"decision": "hold", "lines": ["a", "b\nc", "d"]}, "three single lines"),
    ])
    def test_anything_else_is_a_stop(self, clone, reply, why):
        with pytest.raises(rank_call.Stop, match=why):
            captain.recommend("900", "s", clone=clone, run=Replies(reply))


def test_the_brief_names_every_section_plan_check_holds():
    for words in ("Goal", "Logic", "The change log's three newest entries",
                  "Rule-1 stops anticipated", "Non-goals", "Planned items"):
        assert words in captain.BRIEF
