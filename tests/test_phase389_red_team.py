"""Phase 389 — the Red Team: a fresh refute, held to C1–C7.

What must hold (the 389 prompt): a fresh read-only Opus call refutes the
PR with the C1–C7 checklist, the F9 checks and the A1–A8 diff of v1.0
against v1.1; its table must pass `refute_check` or the stage stops; a
clear with a factual finding, or a back with none, is a stop; a cleared
table goes into the branch's phase log (A8) in place of "No refute pass ran".
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(SKILL))

import rank_call  # noqa: E402
import red_team as R  # noqa: E402
from test_phase388_dispatcher import claude_json  # noqa: E402

TABLE = """## Refuter pass

| claim | verdict | quote | source | round · kind · outcome |
|---|---|---|---|---|
| 385 closes F212 | kept | "add device_tokens.last_seen_at to the list as its own phase" | docs/FOLLOWUPS.md p. 3677 | 1 · none · kept |
"""
NO_PAGE = TABLE.replace("docs/FOLLOWUPS.md p. 3677", "docs/FOLLOWUPS.md")
KILLED = TABLE.replace("| 385 closes F212 | kept |", "| 385 closes F213 | killed |").replace(
    "1 · none · kept", "1 · factual · open")
FINDING = {"claim": "385 closes F213", "kind": "factual", "what_is_wrong": "F213 is not the push "
           "token finding; F212 is.", "where": "docs/ROADMAP.md p. 664"}


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("FLEET_LEDGER", str(tmp_path / "calls.jsonl"))


class Replies:
    def __init__(self, *structured):
        self.queue = [claude_json(s, model=rank_call.OPUS) for s in structured]
        self.calls: list[list[str]] = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, self.queue.pop(0), "")


def test_the_table_fixtures_are_what_they_claim():
    import refute_check
    assert refute_check.check(TABLE) == [] and refute_check.check(KILLED) != []
    assert any(f.startswith("C4") for f in refute_check.check(NO_PAGE))


class TestReview:
    def test_a_clear(self, tmp_path):
        run = Replies({"verdict": "clear", "findings": [], "refuter_pass": TABLE})
        v, _ = R.review("389A", 1, "ctx", clone=tmp_path, run=run)
        assert v["verdict"] == "clear"
        cmd = run.calls[0]
        assert rank_call.OPUS in cmd and cmd[cmd.index("--tools") + 1] == "Read,Grep,Glob"
        assert "1 · none" in cmd[2] and "p. <line>" in cmd[2]

    def test_a_back_with_a_killed_row_open(self, tmp_path):
        """Phase 389, bug fix #2: a killed factual row is open until the
        Engineer fixes it. C6 refuses it in a log that ships, so it holds
        only a clear's table; a back's table, posted on the PR, may carry it."""
        v, _ = R.review("389A", 1, "ctx", clone=tmp_path, run=Replies(
            {"verdict": "back", "findings": [FINDING], "refuter_pass": KILLED}))
        assert v["verdict"] == "back" and "F213" in R.findings_text(v)

    def test_a_clear_with_a_row_left_open_still_stops(self, tmp_path):
        """The control: on a clear, C6 still holds."""
        with pytest.raises(rank_call.Stop, match="C6"):
            R.review("389A", 1, "ctx", clone=tmp_path, run=Replies(
                {"verdict": "clear", "findings": [], "refuter_pass": KILLED}))

    def test_a_back_still_needs_the_rest_of_the_checklist(self, tmp_path):
        with pytest.raises(rank_call.Stop, match="C4"):
            R.review("389A", 1, "ctx", clone=tmp_path, run=Replies(
                {"verdict": "back", "findings": [FINDING],
                 "refuter_pass": KILLED.replace("docs/FOLLOWUPS.md p. 3677", "docs/FOLLOWUPS.md")}))

    @pytest.mark.parametrize("reply,why", [
        ({"verdict": "clear", "findings": [FINDING], "refuter_pass": TABLE}, "clear, with 1"),
        ({"verdict": "back", "findings": [], "refuter_pass": TABLE}, "back, with no findings"),
        ({"verdict": "clear", "findings": [], "refuter_pass": NO_PAGE}, "C4"),
        ({"verdict": "clear", "findings": [], "refuter_pass": "no table"}, "C1"),
        ({"verdict": "pass", "findings": [], "refuter_pass": TABLE}, "no verdict"),
    ])
    def test_known_bad_verdicts_stop(self, tmp_path, reply, why):
        with pytest.raises(rank_call.Stop, match=why):
            R.review("389A", 1, "ctx", clone=tmp_path, run=Replies(reply))

    def test_a_wording_finding_may_still_clear(self, tmp_path):
        v, _ = R.review("389A", 1, "ctx", clone=tmp_path, run=Replies(
            {"verdict": "clear", "findings": [{**FINDING, "kind": "wording"}],
             "refuter_pass": TABLE}))
        assert v["verdict"] == "clear"


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def branch(tmp_path):
    """master, then a plan commit, then v1.1 moved to completed with a change."""
    c = tmp_path / "clone"
    (c / "docs" / "phases" / "in_progress").mkdir(parents=True)
    (c / "README.md").write_text("x\n")
    git("init", "-q", "-b", "master", cwd=c)
    git("add", "-A", cwd=c)
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "base", cwd=c)
    git("update-ref", "refs/remotes/origin/master", "HEAD", cwd=c)
    plan = c / "docs" / "phases" / "in_progress" / "389A_implementation.md"
    plan.write_text("# v1.0\n\n## Goal\n\nRow 385.\n")
    git("add", "-A", cwd=c)
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "Phase 389A v1.0", cwd=c)
    (c / "docs" / "phases" / "completed").mkdir()
    git("mv", "docs/phases/in_progress/389A_implementation.md",
        "docs/phases/completed/389A_implementation.md", cwd=c)
    done = c / "docs" / "phases" / "completed" / "389A_implementation.md"
    done.write_text("# v1.1\n\n## Goal\n\nRow 385.\n\n## Deviations\n\nNone.\n")
    (c / "docs" / "phases" / "completed" / "389A_phase_log.md").write_text(
        "# log\n\nNo refute pass ran.\n")
    git("add", "-A", cwd=c)
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "close", cwd=c)
    return c


class TestWhatTheModelReads:
    def test_the_plan_commit_is_the_first_add(self, branch):
        first = git("log", "--format=%H", "--reverse", cwd=branch).stdout.split()[1]
        assert R.plan_commit(branch, "389A") == first

    def test_gather_carries_a1_to_a8_the_f9_lint_and_the_plan_diff(self, branch):
        ctx = R.gather(branch, "389A", "F9 lint: clean")
        assert "=== closeout_check.py . 389A (A1–A8) ===" in ctx and "A2" in ctx
        assert "F9 lint: clean" in ctx
        assert "+## Deviations" in ctx and "-# v1.0" in ctx and "+# v1.1" in ctx
        assert "docs/phases/completed/389A_phase_log.md" in ctx


class TestTheRecord:
    def test_the_table_replaces_no_refute_pass_ran(self, branch):
        path = R.record_in_log(branch, "389A", TABLE)
        text = (branch / path).read_text()
        assert "No refute pass ran." not in text and text.count("## Refuter pass") == 1
        import refute_check
        assert refute_check.check(text) == []

    def test_a_later_round_replaces_the_earlier_table(self, branch):
        R.record_in_log(branch, "389A", TABLE)
        R.record_in_log(branch, "389A", TABLE.replace("1 · none · kept", "2 · none · kept"))
        text = (branch / "docs/phases/completed/389A_phase_log.md").read_text()
        assert text.count("## Refuter pass") == 1 and "2 · none · kept" in text

    def test_no_log_is_a_stop(self, tmp_path):
        with pytest.raises(rank_call.Stop, match="no phase log"):
            R.record_in_log(tmp_path, "389A", TABLE)


def test_three_rounds_at_most():
    """K9: "max 3 refute rounds"."""
    assert R.MAX_ROUNDS == 3
