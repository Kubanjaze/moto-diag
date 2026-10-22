"""Phase 387 — the Executive Officer, `xo.py`, with stand-ins for claude and gh.

What must hold, from the operator's prompt: the script, not the model, sets
the label from the parsed verdict; two back-to-captain rounds at most, then
needs-admiral; a call with no recorded usage is a stop; the call is
read-only (Read, Grep, Glob; no Bash). And from the fleet proposal: a stage
that cannot finish leaves the label where it found it.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(SKILL))

import rank_call  # noqa: E402
import xo  # noqa: E402
from plan_check import FIXTURE_PHASE, GOOD, apply_case, bad_cases  # noqa: E402


def claude_json(verdict: dict | None = None, *, model: str = rank_call.FABLE, usage: bool = True,
                session: str = "sess-1") -> dict:
    return {"type": "result", "is_error": False, "session_id": session, "num_turns": 3,
            "duration_ms": 4000, "total_cost_usd": 0.5, "result": json.dumps(verdict or {}),
            "structured_output": verdict,
            "modelUsage": {model: {"inputTokens": 10, "outputTokens": 20}},
            "usage": ({"input_tokens": 10, "cache_creation_input_tokens": 100,
                       "cache_read_input_tokens": 1000, "output_tokens": 20} if usage else {})}


class Stand:
    """claude and gh, answering from fixed state; every call recorded."""

    def __init__(self, reply: dict | None = None, rc: int = 0, labels=("plan:needs-review",),
                 comments=(), gh_fails: str | None = None):
        self.reply, self.rc = reply, rc
        self.labels, self.comments = list(labels), list(comments)
        self.gh_fails = gh_fails
        self.calls: list[list[str]] = []

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
        ok = lambda out="": subprocess.CompletedProcess(cmd, 0, out, "")  # noqa: E731
        if cmd[0] == "claude":
            return subprocess.CompletedProcess(cmd, self.rc, json.dumps(self.reply), "boom")
        sub = cmd[1:3]
        if self.gh_fails and self.gh_fails in cmd:
            return subprocess.CompletedProcess(cmd, 1, "", f"{self.gh_fails} refused")
        if sub == ["issue", "view"]:
            field = cmd[cmd.index("--json") + 1]
            if field == "comments":
                return ok(json.dumps({"comments": [{"body": b} for b in self.comments]}))
            return ok(json.dumps({"labels": [{"name": n} for n in self.labels]}))
        if sub == ["issue", "comment"]:
            self.comments.append(cmd[cmd.index("--body") + 1])
            return ok()
        if sub == ["issue", "edit"]:
            for i, a in enumerate(cmd):
                if a == "--add-label" and cmd[i + 1] not in self.labels:
                    self.labels.append(cmd[i + 1])
                if a == "--remove-label" and cmd[i + 1] in self.labels:
                    self.labels.remove(cmd[i + 1])
            return ok()
        raise AssertionError(f"unexpected command {cmd}")

    def claude_calls(self):
        return [c for c in self.calls if c[0] == "claude"]


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "calls.jsonl"
    monkeypatch.setenv("FLEET_LEDGER", str(path))
    return path


def review(stand, repo=GOOD, issue=7, label=True):
    lines: list[str] = []
    rc = xo.review(FIXTURE_PHASE, issue, repo=repo, label=label, run=stand, out=lines.append)
    return rc, "\n".join(lines)


V_APPROVE = {"verdict": "approve", "items": [], "reason": "Buildable as written."}
V_BACK = {"verdict": "back-to-captain", "items": ["Fix the count."], "reason": "One defect."}
V_ADMIRAL = {"verdict": "recommend-to-admiral", "items": [], "reason": "A cost risk."}


class TestTheLabelComesFromTheParsedVerdict:
    @pytest.mark.parametrize("verdict,label", [(V_APPROVE, "plan:approved"),
                                               (V_BACK, "plan:needs-review"),
                                               (V_ADMIRAL, "needs-admiral")])
    def test_each_verdict_sets_its_label_and_only_that(self, verdict, label):
        s = Stand(claude_json(verdict), labels=["plan:needs-review", "mission"])
        rc, _ = review(s)
        assert rc == 0
        plan_labels = [lab for lab in s.labels if lab in xo.PLAN_LABELS]
        assert plan_labels == [label]
        assert "mission" in s.labels

    def test_the_comment_carries_the_marker_and_the_call(self, ledger):
        s = Stand(claude_json(V_APPROVE, session="sess-42"))
        review(s)
        body = s.comments[-1]
        assert body.startswith("<!-- xo-verdict: approve round=0")
        assert "sess-42" in body and "output 20" in body
        rec = json.loads(ledger.read_text().splitlines()[-1])
        assert rec["session_id"] == "sess-42" and rec["output_tokens"] == 20


class TestRounds:
    def marker(self, n):
        return f"<!-- xo-verdict: back-to-captain round={n} applied=back-to-captain phase=900 -->"

    def test_the_first_and_second_back_to_captain_are_rounds(self):
        s = Stand(claude_json(V_BACK), comments=[self.marker(1)])
        rc, text = review(s)
        assert rc == 0 and "round=2" in s.comments[-1]
        assert "plan:needs-review" in s.labels and "needs-admiral" not in s.labels

    def test_the_third_becomes_needs_admiral(self):
        s = Stand(claude_json(V_BACK), comments=[self.marker(1), self.marker(2)])
        rc, text = review(s)
        assert rc == 0
        assert "needs-admiral" in s.labels and "plan:needs-review" not in s.labels
        assert "applied=recommend-to-admiral" in s.comments[-1]

    def test_an_approve_after_two_rounds_is_still_an_approve(self):
        s = Stand(claude_json(V_APPROVE), comments=[self.marker(1), self.marker(2)])
        review(s)
        assert "plan:approved" in s.labels


class TestAFailedChecklistCallsNoModel:
    def test_back_to_captain_with_the_failed_items(self, tmp_path):
        case = next(c for c in bad_cases() if c["id"] == "P3_bare_count")
        repo = apply_case(case, tmp_path / "tree")
        s = Stand(claude_json(V_APPROVE))
        rc, text = review(s, repo=repo)
        assert rc == 0 and not s.claude_calls()
        assert "P3 FAIL" in s.comments[-1] and "plan:needs-review" in s.labels

    def test_an_unreadable_plan_is_exit_2_and_moves_nothing(self, tmp_path):
        s = Stand(claude_json(V_APPROVE))
        rc, _ = review(s, repo=tmp_path)
        assert rc == 2 and not s.claude_calls() and s.labels == ["plan:needs-review"]


class TestStopsMoveNoLabel:
    @pytest.mark.parametrize("stand", [
        Stand(claude_json(V_APPROVE, usage=False)),                       # no usage
        Stand(claude_json(V_APPROVE, model=rank_call.OPUS)),              # wrong model
        Stand(claude_json(None)),                                          # no verdict
        Stand(claude_json({"verdict": "ship it", "items": [], "reason": ""})),
        Stand(claude_json({"verdict": "back-to-captain", "items": [], "reason": "x"})),
        Stand(claude_json(V_APPROVE), rc=1),                               # claude failed
        Stand(claude_json(V_APPROVE), gh_fails="--add-label"),             # gh refused
    ], ids=["no-usage", "wrong-model", "no-verdict", "bad-verdict", "back-without-items",
            "claude-exit-1", "gh-refused"])
    def test_a_stop_is_exit_3_and_the_label_stays(self, stand):
        rc, text = review(stand)
        assert rc == 3 and "STOP" in text
        assert [lab for lab in stand.labels if lab in xo.PLAN_LABELS] == ["plan:needs-review"]
        assert "label unchanged" in stand.comments[-1]

    def test_no_label_mode_touches_nothing_on_github(self):
        s = Stand(claude_json(V_APPROVE))
        rc, text = review(s, label=False)
        assert rc == 0 and "would be plan:approved" in text
        assert not [c for c in s.calls if c[:3] in (["gh", "issue", "edit"],
                                                    ["gh", "issue", "comment"])]


class TestTheCallIsReadOnly:
    def test_the_command_carries_the_fence_and_no_bash(self):
        s = Stand(claude_json(V_APPROVE))
        review(s)
        (cmd,) = s.claude_calls()
        assert cmd[cmd.index("--tools") + 1] == "Read,Grep,Glob"
        assert cmd[cmd.index("--allowedTools") + 1] == "Read,Grep,Glob"
        assert cmd[cmd.index("--disallowedTools") + 1] == "Bash"
        assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk"
        assert "--strict-mcp-config" in cmd and cmd[cmd.index("--model") + 1] == rank_call.FABLE
        assert json.loads(cmd[cmd.index("--json-schema") + 1]) == xo.SCHEMA
        assert "Bash" not in cmd[cmd.index("--tools") + 1]
