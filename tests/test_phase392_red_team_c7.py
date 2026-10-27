"""Phase 392 — F228: a Red Team round that leaves a wording defect open can
finish.

C7 asks an open wording defect to cite the one finding it goes to (K9:
"after round 3, remaining wording defects go to one finding"). The Red Team
is read-only and cannot file it, and its brief never said so: #14's round
3 (2026-10-27 10:07) stopped on C7. Now the brief states the rule in its
own words; C7 is set aside on a back before the last round, as C6 is; on a
clear, or a back in the last round, the dispatcher files the finding (the
next number over both repositories) and writes it into each row. The
known-bad case is #14's round-3 output, `fixtures/red_team/14_round3.json`.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLEET = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(FLEET))
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "refute"))
sys.path.insert(0, str(ROOT / "tests"))
import fleet_git  # noqa: E402
import rank_call  # noqa: E402
import red_team  # noqa: E402
import refute_check  # noqa: E402
from test_phase388_dispatcher import claude_json  # noqa: E402
from test_phase389_dispatcher import BRANCH, go_to_approved, labels, step, world  # noqa: E402,F401
from test_phase389_fleet_git import git  # noqa: E402

R14 = json.loads((FLEET / "fixtures" / "red_team" / "14_round3.json").read_text())
TABLE14 = R14["refuter_pass"]
WORDING = "The Results bullet says `wholetree.sh --full` passed 4530"
V14 = {k: R14[k] for k in ("verdict", "findings", "refuter_pass")}


def clear_with_wording() -> str:
    """#14's table with its factual rows fixed: a table a clear could ship."""
    return "\n".join(ln.replace("3 · factual · open", "3 · factual · fixed")
                     .replace("| killed |", "| kept |") for ln in TABLE14.splitlines())


class TestTheKnownBadCase:
    def test_14s_table_as_it_came_fails_c7_on_its_wording_row(self):
        c7 = [f for f in refute_check.check(TABLE14) if f.startswith("C7 ")]
        assert len(c7) == 1 and "leaves a wording defect open with no finding" in c7[0]

    def test_before_392_its_round_3_stopped(self, monkeypatch):
        """392's change set aside, the round stops as it did at 10:09."""
        monkeypatch.setattr(red_team, "open_wording", lambda table: [])
        with pytest.raises(rank_call.Stop, match="C7 row"):
            red_team.check_table(dict(V14), TABLE14, 3)

    def test_now_its_round_3_finishes_with_the_one_row_to_file(self):
        v = red_team.check_table(dict(V14), TABLE14, 3)
        assert [r["claim"] for r in v["wording_open"]] == [WORDING]

    def test_with_the_number_written_c7_holds_and_c6_still_sees_the_factual_rows(self):
        filed = red_team.with_finding(TABLE14, "F229")
        fails = refute_check.check(filed)
        assert not [f for f in fails if f.startswith("C7 ")]
        # Four factual rows are open; one quotes `\|` and is not a row C6 reads.
        assert len([f for f in fails if f.startswith("C6 ")]) == 3
        assert "| 3 · wording · open F229 |" in filed
        assert filed.count("F229") == 1


class TestTheRounds:
    def test_a_back_before_the_last_round_files_nothing(self):
        table = TABLE14.replace("| 3 · ", "| 1 · ")
        v = red_team.check_table(dict(V14), table, 1)
        assert v["wording_open"] == []

    def test_a_clear_with_open_wording_files_one(self):
        table = clear_with_wording()
        v = red_team.check_table({"verdict": "clear", "findings": [], "refuter_pass": table},
                                 table, 1)
        assert [r["claim"] for r in v["wording_open"]] == [WORDING]

    def test_two_different_numbers_still_fail_c7(self):
        row = "| docs/phases/completed/389A_implementation.md p. 74 | 3 · none · kept |"
        assert clear_with_wording().count(row) == 1
        table = clear_with_wording().replace(row, row.replace("none · kept", "wording · open F100"))
        with pytest.raises(rank_call.Stop, match="C7 open wording defects go to ONE finding"):
            red_team.check_table({"verdict": "clear", "findings": [], "refuter_pass": table},
                                 table, 1)

    def test_the_brief_states_c7_in_its_own_words(self):
        b = " ".join(red_team.BRIEF.split())
        assert "every wording defect left open goes to one finding" in b
        assert 'written "open" with no F-number' in b and "never write an" in b


class TestTheDispatcherFilesIt:
    @pytest.fixture
    def with_followups(self, world):
        fleet, host, clock, origin, *_ = world
        (origin / "docs" / "FOLLOWUPS.md").write_text(
            "# Follow-ups\n\nAt the time of writing the highest assigned is **F228** "
            "(this file).\n\n### F228\n\n**The last one**\n")
        git("add", "-A", cwd=origin)
        git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "followups", cwd=origin)
        git("branch", "-f", BRANCH, "master", cwd=origin)          # a fast-forward
        return world

    def test_14s_round_3_finishes_files_f229_and_goes_to_the_operator(self, with_followups):
        fleet, host, clock, origin, *_ = with_followups
        go_to_approved(with_followups)
        step(clock, fleet, host)                                  # the PR
        back = claude_json({"verdict": "back", "findings": [{"claim": "c", "kind": "code",
                                                             "what_is_wrong": "w", "where": "x"}],
                            "refuter_pass": TABLE14.replace("| 3 · ", "| 1 · ")},
                           model=rank_call.OPUS)
        for _ in (1, 2):
            step(clock, fleet, host, back)
            step(clock, fleet, host)                              # the fix round
        step(clock, fleet, host, claude_json(V14, model=rank_call.OPUS))
        assert "needs-admiral" in labels(host)
        said = host.comments(31)[-1]
        assert "round 3 of 3" in said and "filed as F229" in said
        log = git_show(origin, f"{BRANCH}:docs/FOLLOWUPS.md")
        assert "### F229" in log and "highest assigned is **F229**" in log
        assert WORDING in log and "Filed by the fleet's dispatcher" in log
        pr = next(iter(host.prs.values()))
        assert "| 3 · wording · open F229 |" in pr["comments"][-1]


def git_show(repo: pathlib.Path, spec: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "show", spec], capture_output=True,
                          text=True, check=True).stdout


class TestTheGate:
    def test_the_record_may_add_a_finding_and_change_nothing_else(self, tmp_path):
        repo = tmp_path / "r"
        repo.mkdir()
        git("init", "-q", "-b", "master", cwd=repo)
        (repo / "docs").mkdir()
        (repo / "docs" / "FOLLOWUPS.md").write_text("highest assigned is **F1**\n\n### F1\n\nold\n")
        git("add", "-A", cwd=repo)
        git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "a", cwd=repo)
        base = git_show(repo, "HEAD:docs/FOLLOWUPS.md") and _head(repo)
        f = repo / "docs" / "FOLLOWUPS.md"
        f.write_text("highest assigned is **F2**\n\n### F1\n\nchanged\n\n### F2\n\nnew\n")
        git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "b", cwd=repo)
        fails = fleet_git.gate(repo, rank="red-team-record", phase="902", branch="phase-902-x",
                               base=base, tested=lambda c: (True, ""), mobile=None)
        assert [x for x in fails if x.startswith("G3")] == [
            "G3 the red-team-record may only add to docs/FOLLOWUPS.md, not change 'old'"]


def _head(repo: pathlib.Path) -> str:
    return git_show(repo, "HEAD").split()[1]
