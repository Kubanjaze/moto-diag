"""Phase 407 — a decision for the operator is asked first, with its label (F285).

What must hold (407's v1.0, K96): a Step 0 report classified reshape, the
operator's call (`plan_check` P4), puts `needs-admiral` and a plain question
on the issue before any plan-writer call; an extension report goes on to the
plan writer as before; a reshape report that reaches the plan writer's stage
is asked the same way, with no model call; the release (the report
relabelled, the label taken off) starts the plan writer. Since the review
(407's phase log): the scout labels `step0:done` before it asks, so a
question GitHub refuses is asked again by the plan writer's guard; a stage
cut between the question and its label asks once; the reason is read on its
own line and made safe for a comment; a held issue is swept for its hold
alone.

389's stand-ins: git is real, `gh` and the models are stand-ins on one clock;
390's, for the stage cut and resumed.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))

import dispatcher as D  # noqa: E402
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
from test_phase390_resume import comment as comment_starting  # noqa: E402
from test_phase390_resume import killed, restart, said, w  # noqa: E402,F401
from test_phase390_resume import labels as labels_of_w  # noqa: E402

RESHAPE = {**ASSESS, "classification": "reshape",
           "reason": "The row changes what existing refusals do. Today they refuse everything."}
REPORT = f"docs/phases/in_progress/{PHASE}_step0.md"


def scout(clock, fleet, host, assess) -> None:
    """The Science Officer's cycle: its two Haiku calls."""
    step(clock, fleet, host, claude_json(TERMS, model=rank_call.HAIKU),
         claude_json(assess, model=rank_call.HAIKU))


def asked(host, rank: str) -> list[str]:
    return [c for c in host.comments(31) if f"needs-admiral rank={rank}" in c]


def scout_note(host) -> str:
    [note] = [c for c in host.comments(31) if c.startswith(D.SCOUT_M)]
    return note


def relabel(origin, tmp_path, old: str, new: str) -> None:
    """One line of the report changed on the phase branch, as the advisor
    did for 404 and 405."""
    work = tmp_path / "relabel"
    if work.exists():
        work = tmp_path / f"relabel{len(list(tmp_path.glob('relabel*')))}"
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
    assert "`Classification: extension`, that word first" in question
    assert "as you decided for phases 404 and 405" in question and "K9" not in question
    assert "take `needs-admiral` off" in question
    assert "Next: the operator's call, asked below." in scout_note(host)
    calls, notes = len(host.model_calls()), len(host.comments(31))
    step(clock, fleet, host)                          # held: no stage, no model call
    assert len(host.model_calls()) == calls
    assert len(host.comments(31)) == notes and asked(host, "captain") == [], \
        "a stage ran on the held issue"
    assert labels(host) == ["mission", "needs-admiral", "step0:done"]


def test_a_question_github_refuses_is_asked_again_with_no_model_call(world):
    """The scout labels `step0:done` before it asks: a question GitHub refuses
    leaves the plan writer due, and its guard asks again, calling no model.
    Asked first, the refusal left only `mission`, and nothing was due."""
    fleet, host, clock, *_ = world
    host.issue(31, TITLE, TRIAL, {"mission": T0})
    gh = host.gh

    def refuse_the_question(cmd):
        if cmd[1:3] == ["issue", "comment"] and \
                "needs-admiral rank=scout" in cmd[cmd.index("--body") + 1]:
            return subprocess.CompletedProcess(cmd, 1, "", "HTTP 502: Bad Gateway")
        return gh(cmd)

    host.gh = refuse_the_question
    scout(clock, fleet, host, RESHAPE)
    assert labels(host) == ["mission", "step0:done"] and asked(host, "scout") == []
    host.gh = gh
    calls = len(host.model_calls())
    step(clock, fleet, host)
    assert len(host.model_calls()) == calls, "the plan writer was called on a reshape"
    assert labels(host) == ["mission", "needs-admiral", "step0:done"]
    assert len(asked(host, "captain")) == 1


def test_a_scout_cut_between_its_question_and_its_label_asks_once(w):
    """390's kill, after the question is posted and before its label: the
    resumed stage asks GitHub, posts no second question, and labels the hold."""
    question = "<!-- fleet-dispatcher: needs-admiral rank=scout"
    w.kill.at(comment_starting(question), after=True)
    killed(w, claude_json(TERMS, model=rank_call.HAIKU),
           claude_json(RESHAPE, model=rank_call.HAIKU))
    restart(w)
    assert said(w, question) == 1
    assert labels_of_w(w) == ["mission", "needs-admiral", "step0:done"]


def test_an_extension_report_goes_on_to_the_plan_writer(world):
    fleet, host, clock, *_ = world
    host.issue(31, TITLE, TRIAL, {"mission": T0})
    scout(clock, fleet, host, ASSESS)
    assert labels(host) == ["mission", "step0:done"] and asked(host, "scout") == []
    assert "Next: the Captain writes v1.0." in scout_note(host)
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


def test_the_release_after_the_plan_writers_ask_starts_the_plan_writer(world, tmp_path):
    """The plan writer's ask comes after `step0:done`, so its marker must not
    be one the plan writer's due rule reads."""
    fleet, host, clock, origin, *_ = world
    host.issue(31, TITLE, TRIAL, {"mission": T0})
    scout(clock, fleet, host, ASSESS)
    relabel(origin, tmp_path, "Classification: **extension.**", "Classification: **reshape.**")
    step(clock, fleet, host)                          # the plan writer's guard asks
    assert len(asked(host, "captain")) == 1
    relabel(origin, tmp_path, "Classification: **reshape.**",
            "Classification: **extension**, by the operator's decision.")
    host.issues[31]["labels"].remove("needs-admiral")
    step(clock, fleet, host, claude_json({"implementation_md": PLAN}))
    assert labels(host) == ["mission", "plan:needs-review"]


def test_a_held_issue_is_swept_for_its_hold_alone(world):
    """After 24 hours a held issue's sweep names the hold, not the rank whose
    label sits under it: no rank moves `step0:done` while it is held."""
    fleet, host, *_ = world
    host.issue(9, f"Phase {PHASE}: the trial", "",
               {"mission": T0 - dt.timedelta(hours=100),
                "step0:done": T0 - dt.timedelta(hours=30),
                "needs-admiral": T0 - dt.timedelta(hours=30)})
    assert fleet.sweep() == 1
    [note] = host.comments(9)
    assert "label=needs-admiral" in note and "the Admiral" in note
    assert "the Captain" not in note


@pytest.mark.parametrize("line,reason", [
    ("Classification: **reshape.**\n\n## The overlap census", ""),
    ("Classification: reshape. It changes e.g. the refusals. More after.",
     "It changes e.g. the refusals"),
    ("Classification: reshape. It asks **@octocat** to merge.", "It asks `@octocat` to merge"),
    ("Classification: reshape. Mail a@b.example about it.", "Mail a@b.example about it"),
])
def test_the_reason_stays_on_its_line_and_safe_in_a_comment(line, reason):
    assert D.reshape_reason(f"# Step 0\n\n{line}\n") == reason


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
