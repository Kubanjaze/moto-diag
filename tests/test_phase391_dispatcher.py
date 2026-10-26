"""Phase 391 — the dispatcher runs the Quartermaster, in shadow.

What must hold (v1.0, Logic 2): on `merge:needs-review`, once per
application and only for one made after `quartermaster_since`, the stage
writes its verdict on the PR, on the issue and in `quartermaster.jsonl`; it
moves no label and merges nothing; it is held below the free-space floor;
and cut anywhere, it resumes (`fixtures/resume/kill_points.json`'s
`quartermaster` entry names each kill point's test here).

390's world: real git (389's origin, row 902 🚧), `gh`, the fence's model
calls and the model-free runs stood in.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from test_phase388_dispatcher import claude_json  # noqa: E402
from test_phase389_dispatcher import BRANCH  # noqa: E402
from test_phase390_resume import (CLEAR, CUT, DIGEST, MERGE, SCOUT, N, D, J, World, advance, calls,  # noqa: E402,F401
                                  comment, killed, labels, ledger, model, pr_comment, restart,
                                  said, to_pr, w)
from test_phase390_space import Disk, s  # noqa: E402,F401

import rank_call  # noqa: E402

REFUSE = claude_json({"verdict": "refuse", "failed": [{"check": "Q7", "why": "v1.1 is the plan."}],
                      "summary": "Not finished."}, model=rank_call.OPUS)


def to_merge_review(w):
    to_pr(w)
    advance(w, CLEAR)
    advance(w, MERGE)
    assert labels(w) == ["merge:needs-review", "mission"]


def verdicts(w) -> list[dict]:
    p = w.fleet.verdicts()
    return [json.loads(ln) for ln in p.read_text().splitlines()] if p.is_file() else []


def pr(w) -> dict:
    return w.host.prs[BRANCH]


def qm_comments(w) -> list[str]:
    return [b for b in pr(w)["comments"] if b.startswith(D.QM_PR_M)]


# ------------------------------------------------------------- the stage
def test_a_verdict_on_the_pr_the_issue_and_the_record_and_no_label_moved(w):
    to_merge_review(w)
    before = len(w.checks)
    advance(w, REFUSE)
    assert labels(w) == ["merge:needs-review", "mission"]
    [text] = qm_comments(w)
    assert "The Quartermaster, phase 902 (shadow): refuse" in text and "nothing is merged" in text
    assert said(w, f"{D.QM_M} verdict=refuse") == 1
    [rec] = verdicts(w)
    assert rec["verdict"] == "refuse" and rec["pr"] == pr(w)["number"] and "Q7" in rec["failed"]
    runs = w.checks[before:]
    assert [full for _, full, cmd in runs if cmd is None] == [True], "one full model-free run"
    [cmd] = [cmd for _, _, cmd in runs if cmd]
    assert cmd[0] == ".claude/skills/closeout/verify_phase.sh" and cmd[1] == "902"
    no_unfinished(w)


def no_unfinished(w):
    assert J.unfinished(w.fleet.runs) == [], "a journal left open"


def test_it_runs_once_per_application_of_the_label(w):
    to_merge_review(w)
    advance(w, REFUSE)
    advance(w)                                         # no reply wanted: not due
    w.host.issues[N]["labels"].remove("merge:needs-review")
    w.clock.t += dt.timedelta(minutes=1)
    w.host.label(N, "merge:needs-review")
    advance(w, REFUSE)
    assert len(qm_comments(w)) == 2 and len(verdicts(w)) == 2


def test_a_label_applied_before_it_came_up_is_left_alone(w):
    """#14's, during this build: the operator applies the label again."""
    to_merge_review(w)
    state = w.fleet.load()
    state["quartermaster_since"] = (w.clock.t + dt.timedelta(hours=1)).isoformat()
    w.fleet.save(state)
    advance(w)
    assert qm_comments(w) == [] and verdicts(w) == []


def test_the_first_cycle_sets_quartermaster_since(w):
    assert "quartermaster_since" not in w.fleet.load()
    advance(w, *SCOUT)
    assert w.fleet.load()["quartermaster_since"] <= w.clock.t.isoformat()


def test_out_of_scope_runs_nothing_and_calls_no_model(w, monkeypatch):
    to_merge_review(w)
    monkeypatch.setattr(D.quartermaster, "scope", lambda *a, **k: D.quartermaster.Finding(
        "Q1", False, "it changes src/motodiag/core/migrations.py, a migration"))
    before, models = len(w.checks), len(calls(w))
    advance(w)
    assert len(w.checks) == before and len(calls(w)) == models
    [text] = qm_comments(w)
    assert ": refuse" in text and "Q1 (the phase is in scope)" in text


def test_a_merge_verdict(w, monkeypatch):
    to_merge_review(w)
    monkeypatch.setattr(D.quartermaster, "scripted", lambda *a, **k: (
        [D.quartermaster.Finding(c, True) for c in ("Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9")],
        {"captain": "", "red_team": "", "verify": [], "cited": []}))
    advance(w, claude_json({"verdict": "merge", "failed": [], "summary": "Ready."},
                           model=rank_call.OPUS))
    [text] = qm_comments(w)
    assert "(shadow): merge" in text and labels(w) == ["merge:needs-review", "mission"]
    assert verdicts(w)[0]["failed"] == []


def test_a_model_answer_naming_no_real_check_is_a_stop_label_unchanged(w):
    to_merge_review(w)
    advance(w, claude_json({"verdict": "refuse", "failed": [{"check": "V1.1 diff", "why": "x"}],
                            "summary": "s"}, model=rank_call.OPUS))
    assert qm_comments(w) == [] and labels(w) == ["merge:needs-review", "mission"]
    assert said(w, f"{D.MARKER} stopped rank=quartermaster") == 1


def test_held_below_the_free_space_floor(s):
    to_merge_review(s)
    s.disk.free["C:"] = 10.0
    advance(s)
    assert "needs-hands" in labels(s) and qm_comments(s) == []
    assert said(s, f"{D.SPACE_M} rank=quartermaster") == 1


def test_the_sweep_names_the_quartermaster():
    assert "Quartermaster" in D.NEXT_RANK["merge:needs-review"]
    assert "not built yet" not in D.NEXT_RANK["merge:needs-review"]


# ---------------------------------------------------------- kill points
def test_quartermaster_cut_in_its_model_call(w):
    to_merge_review(w)
    w.kill.at(model, cut=True)
    killed(w)
    restart(w, REFUSE)
    assert calls(w)[-1][:3] == ["claude", "--resume", CUT]
    assert len(qm_comments(w)) == 1 and len(verdicts(w)) == 1
    no_unfinished(w)


def test_quartermaster_cut_in_its_full_model_free_run(w):
    to_merge_review(w)
    w.check_kill = (True, False)
    killed(w)
    head = [c for c, full, cmd in w.checks if full][-1]
    restart(w, REFUSE)
    fulls = [c for c, full, cmd in w.checks if full]
    assert fulls[-1] == head and len(qm_comments(w)) == 1
    no_unfinished(w)


def test_quartermaster_cut_after_its_pr_comment(w):
    to_merge_review(w)
    w.kill.at(pr_comment, after=True)
    killed(w, REFUSE)
    restart(w)
    assert len(qm_comments(w)) == 1 and said(w, f"{D.QM_M} verdict=refuse") == 1
    assert len(verdicts(w)) == 1


def test_quartermaster_cut_after_its_issue_marker(w):
    to_merge_review(w)
    w.kill.at(comment(f"{D.QM_M} verdict"), after=True)
    killed(w, REFUSE)
    restart(w)
    assert said(w, f"{D.QM_M} verdict=refuse") == 1 and len(verdicts(w)) == 1
    assert len(qm_comments(w)) == 1


def test_a_resumed_stage_reads_verify_phases_output_back_from_its_journal(w, monkeypatch):
    """The model call is cut after both model-free runs finished: the
    resumed stage must hand the model the same verify_phase.sh output, read
    from the journal, not an empty one (`Check.out`)."""
    marker = "=== 2. no code after regression hash ===\n  none (docs only)\n"
    plain = World.make

    def make(self):
        f = plain(self)
        inner = f.check

        def check(clone, commit, *, full, command=None):
            c = inner(clone, commit, full=full, command=command)
            if command and command[0].endswith("verify_phase.sh"):
                c.out = marker
            return c
        f.check = check
        return f
    monkeypatch.setattr(World, "make", make)
    w.make()
    to_merge_review(w)
    w.kill.at(model, cut=True)
    killed(w)
    runs = len(w.checks)
    restart(w, REFUSE)
    assert len(w.checks) == runs, "a finished model-free run was made again"
    prompt = calls(w)[-1][calls(w)[-1].index("-p") + 1]
    assert "V2 no code after the regression hash: pass" in prompt and marker.strip() in prompt


# --------------------------------------------------------------- the digest
def test_the_digest_stage_carries_the_days_verdicts(w):
    w.host.issues.clear()
    w.host.prs["b"] = {"number": 7, "url": "u", "body": "", "comments": []}
    w.fleet.save({"last_digest": "2026-10-20"})
    w.fleet.verdicts().write_text(json.dumps({
        "at": "2026-10-21T12:00:00-04:00", "issue": 31, "pr": 7, "phase": "902",
        "head": "abcdef1234", "verdict": "refuse", "failed": ["Q8"], "run": "r"}) + "\n")
    advance(w, DIGEST)
    page = (w.fleet.state_dir / "digests" / "2026-10-21.md").read_text()
    assert "## The Quartermaster (shadow)" in page and "PR #7 (phase 902" in page


def test_the_digest_sets_each_verdict_beside_the_operators():
    import yeoman
    states = {20: "CLOSED", 21: "MERGED", 22: "OPEN", 23: "MERGED"}

    def run(cmd, **kw):
        n = int(cmd[3])
        return subprocess.CompletedProcess(cmd, 0, json.dumps({"state": states[n]}), "")
    v = [{"pr": 20, "phase": "390A", "head": "f987bf3130", "verdict": "refuse", "failed": ["Q2", "Q3"]},
         {"pr": 21, "phase": "391", "head": "aaaaaaa", "verdict": "merge", "failed": []},
         {"pr": 22, "phase": "391", "head": "bbbbbbb", "verdict": "refuse", "failed": ["Q8"]},
         {"pr": 23, "phase": "391", "head": "ccccccc", "verdict": "refuse", "failed": ["Q7"]}]
    text = "\n".join(yeoman.shadow(v, run))
    assert "Verdicts in the window: 4." in text
    assert "PR #20 (phase 390A, head `f987bf3`): refuse, checks named: Q2, Q3. The PR now: closed unmerged. Agrees with the operator: yes." in text
    assert "PR #21" in text and "merged. Agrees with the operator: yes." in text
    assert "PR #22" in text and "open. Agrees with the operator: not yet." in text
    assert "PR #23" in text and text.rstrip().endswith("Agrees with the operator: NO.")


def test_the_digest_reads_the_days_verdicts(w):
    p = w.fleet.verdicts()
    p.parent.mkdir(parents=True, exist_ok=True)
    day = w.clock.t.date()
    p.write_text(json.dumps({"at": w.clock.t.isoformat(), "pr": 7}) + "\n"
                 + json.dumps({"at": (w.clock.t - dt.timedelta(days=2)).isoformat(), "pr": 8}) + "\n")
    assert [r["pr"] for r in w.fleet.verdicts_on(day)] == [7]
