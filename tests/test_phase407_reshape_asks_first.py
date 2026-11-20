"""Phase 407 — a decision for the operator is asked first, with its label (F285).

What must hold (407's v1.0, K96): a Step 0 report classified reshape, the
operator's call (`plan_check` P4), puts `needs-admiral` and a plain question
on the issue before any plan-writer call; an extension report goes on to the
plan writer as before; a reshape report that reaches the plan writer's stage
is asked the same way, with no model call; the release (the report
relabelled, the label taken off) starts the plan writer.

389's stand-ins: git is real, `gh` and the models are stand-ins on one clock.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))

import rank_call  # noqa: E402
from test_phase388_dispatcher import T0, claude_json  # noqa: E402
from test_phase389_dispatcher import (  # noqa: E402,F401
    ASSESS,
    BRANCH,
    PHASE,
    PLAN,
    TERMS,
    TITLE,
    TRIAL,
    labels,
    ledger,
    step,
    world,
)
from test_phase389_fleet_git import git  # noqa: E402

RESHAPE = {**ASSESS, "classification": "reshape",
           "reason": "The row changes what existing refusals do. Today they refuse everything."}
REPORT = f"docs/phases/in_progress/{PHASE}_step0.md"


def scout(clock, fleet, host, assess) -> None:
    """The Science Officer's cycle: its two Haiku calls."""
    step(clock, fleet, host, claude_json(TERMS, model=rank_call.HAIKU),
         claude_json(assess, model=rank_call.HAIKU))


def asked(host, rank: str) -> list[str]:
    return [c for c in host.comments(31) if f"needs-admiral rank={rank}" in c]


def relabel(origin, tmp_path, old: str, new: str) -> None:
    """One line of the report changed on the phase branch, as the advisor
    did for 404 and 405."""
    work = tmp_path / "relabel"
    subprocess.run(["git", "clone", "-q", "--branch", BRANCH, str(origin), str(work)],
                   check=True, capture_output=True)
    path = work / REPORT
    text = path.read_text()
    assert text.count(old) == 1, f"{old!r} occurs {text.count(old)} times in the report"
    path.write_text(text.replace(old, new))
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "relabel", cwd=work)
    git("push", "-q", "origin", BRANCH, cwd=work)


def test_a_reshape_report_asks_the_operator_and_holds_the_issue(world):
    fleet, host, clock, *_ = world
    host.issue(31, TITLE, TRIAL, {"mission": T0})
    scout(clock, fleet, host, RESHAPE)
    assert labels(host) == ["mission", "needs-admiral", "step0:done"]
    [question] = asked(host, "scout")
    assert f"Phase {PHASE}'s first step calls it a reshape, which is your call" in question
    assert "The row changes what existing refusals do" in question
    assert "Today they refuse" not in question, "more than the reason's first sentence"
    assert "K90 and K95" in question and "take `needs-admiral` off" in question
    calls = len(host.model_calls())
    step(clock, fleet, host)                          # held: no stage, no model call
    assert len(host.model_calls()) == calls
    assert labels(host) == ["mission", "needs-admiral", "step0:done"]


def test_an_extension_report_goes_on_to_the_plan_writer(world):
    fleet, host, clock, *_ = world
    host.issue(31, TITLE, TRIAL, {"mission": T0})
    scout(clock, fleet, host, ASSESS)
    assert labels(host) == ["mission", "step0:done"] and asked(host, "scout") == []
    step(clock, fleet, host, claude_json({"implementation_md": PLAN}))
    assert labels(host) == ["mission", "plan:needs-review"]


def test_a_reshape_report_reaching_the_plan_writer_is_asked_with_no_model_call(world, tmp_path):
    fleet, host, clock, origin, *_ = world
    host.issue(31, TITLE, TRIAL, {"mission": T0})
    scout(clock, fleet, host, ASSESS)                 # labelled step0:done, as before 407
    relabel(origin, tmp_path, "Classification: **extension.**", "Classification: **reshape.**")
    calls = len(host.model_calls())
    step(clock, fleet, host)
    assert len(host.model_calls()) == calls, "the plan writer was called on a reshape"
    assert labels(host) == ["mission", "needs-admiral", "step0:done"]
    assert len(asked(host, "captain")) == 1


def test_the_release_starts_the_plan_writer(world, tmp_path):
    fleet, host, clock, origin, *_ = world
    host.issue(31, TITLE, TRIAL, {"mission": T0})
    scout(clock, fleet, host, RESHAPE)
    relabel(origin, tmp_path, "Classification: **reshape.**",
            "Classification: **extension**, by the operator's decision.")
    host.issues[31]["labels"].remove("needs-admiral")  # the operator takes it off
    step(clock, fleet, host, claude_json({"implementation_md": PLAN}))
    assert labels(host) == ["mission", "plan:needs-review"]


@pytest.mark.parametrize("line,asks", [
    ("Classification: **greenfield.** Nothing of this exists.", False),
    ("Classification: **extension.** It adds to what exists.", False),
    ("No classification line at all.", False),
    ("Classification: **reshape.** It changes what exists. More after that.", True),
])
def test_ask_reshape_asks_only_on_a_reshape(world, line, asks):
    fleet, host, *_ = world
    host.issue(31, TITLE, TRIAL, {"mission": T0})
    assert fleet.ask_reshape(31, "scout", PHASE, f"# Step 0\n\n{line}\n") is asks
    assert ("needs-admiral" in host.issues[31]["labels"]) is asks
    assert len(asked(host, "scout")) == (1 if asks else 0)
