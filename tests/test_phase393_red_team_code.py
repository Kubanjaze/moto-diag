"""Phase 393 (K54) — the Red Team asks five questions of the code.

Each is answered "yes", "no" or "not-applicable" with a file and a line. A
"no" with a file and line is a factual defect under K9, so the round is a
back. Questions 2 and 3 are also scanned by script over the lines the
branch adds; a scripted "no" makes the round a back whatever the model
says. The known-bad case: a planted diff with `except Exception: pass` in
`payments/`, answered "clear" by a model that saw nothing.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
sys.path.insert(0, str(ROOT / "tests"))

import rank_call  # noqa: E402
import red_team as R  # noqa: E402
from support.phase393 import ALL_YES  # noqa: E402
from test_phase389_red_team import FINDING, TABLE, Replies  # noqa: E402,F401
from test_phase389_red_team import ledger  # noqa: E402,F401
from test_phase390_resume import D, advance, labels, to_pr, w  # noqa: E402,F401

SWALLOW = ("def refund_once(intent_id: str) -> None:\n"
           "    try:\n"
           "        _send(intent_id)\n"
           "    except Exception:\n"
           "        pass\n")


def git(repo: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@l", *args],
                   check=True, capture_output=True)


@pytest.fixture
def branch(tmp_path) -> pathlib.Path:
    """master with payments/refunds.py; a branch that adds the given body."""
    repo = tmp_path / "repo"
    pay = repo / "src" / "motodiag" / "payments"
    pay.mkdir(parents=True)
    (pay / "refunds.py").write_text("def _send(intent_id: str) -> None:\n    return None\n")
    git(repo, "init", "-q", "-b", "master")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    git(repo, "checkout", "-qb", "phase-999-x")
    return repo


def add(repo: pathlib.Path, body: str, path: str = "src/motodiag/payments/refunds.py") -> None:
    f = repo / path
    f.write_text(f.read_text() + "\n\n" + body)
    git(repo, "commit", "-qam", "head")


# --------------------------------------------------------------- the scan
class TestTheScan:
    def test_the_planted_swallow_in_payments_is_a_no(self, branch):
        add(branch, SWALLOW)
        scan = R.code_scan(branch, "master")
        [no] = scan["no"]
        assert no["question"] == 3 and no["where"] == "src/motodiag/payments/refunds.py:8"
        assert "`except Exception` whose body only passes" in no["why"]
        assert scan["sensitive"] == ["src/motodiag/payments/refunds.py"]
        assert scan["public"] == ["src/motodiag/payments/refunds.py:5 refund_once"]

    def test_a_handler_that_names_its_error_is_not(self, branch):
        """The exclusion's control: a named error, or a body that does
        something, is not a scripted no."""
        add(branch, SWALLOW.replace("except Exception:", "except KeyError:"))
        add(branch, "def g():\n    try:\n        return 1\n    except Exception:\n        raise\n")
        assert R.code_scan(branch, "master")["no"] == []

    def test_a_bare_except_and_a_new_money_helper(self, branch):
        add(branch, "def _money(cents: int) -> str:\n    try:\n        return f'{cents}'\n"
                    "    except:\n        pass\n    return ''\n")
        got = {(n["question"], n["where"]) for n in R.code_scan(branch, "master")["no"]}
        assert got == {(2, "src/motodiag/payments/refunds.py:5"),
                       (3, "src/motodiag/payments/refunds.py:8")}

    def test_an_old_swallow_the_branch_did_not_add_is_not(self, branch):
        """Only added lines: the 22 already in src/ are F234's, not this PR's."""
        add(branch, SWALLOW)
        git(branch, "checkout", "-q", "master")
        git(branch, "merge", "-q", "phase-999-x")
        git(branch, "checkout", "-qb", "phase-998-y")
        add(branch, "def h() -> int:\n    return 2\n")
        assert R.code_scan(branch, "master")["no"] == []

    def test_the_scan_reaches_the_brief(self, branch):
        add(branch, SWALLOW)
        text = R.scan_text(R.code_scan(branch, "master"))
        assert "question 3, src/motodiag/payments/refunds.py:8" in text


# -------------------------------------------------------------- the review
class TestTheReview:
    def test_the_brief_asks_the_five_questions(self, tmp_path):
        run = Replies({"verdict": "clear", "findings": [], "refuter_pass": TABLE})
        R.review("999", 1, "ctx", clone=tmp_path, run=run)
        for n, q in R.QUESTIONS.items():
            assert f"   {n}. {q}" in run.briefs[0]
        assert "code_checklist" in run.briefs[0] and "{QUESTIONS}" not in run.briefs[0]

    def test_the_planted_swallow_makes_a_clear_a_back(self, branch, tmp_path):
        """The known-bad case: the model saw nothing and said clear."""
        add(branch, SWALLOW)
        scan = R.code_scan(branch, "master")
        v, _ = R.review("999", 1, "ctx", clone=tmp_path, scan=scan, run=Replies(
            {"verdict": "clear", "findings": [], "refuter_pass": TABLE}))
        assert v["verdict"] == "back"
        [f] = v["findings"]
        assert f["kind"] == "code" and f["where"] == "src/motodiag/payments/refunds.py:8"
        assert "found by script" in f["what_is_wrong"]

    def test_the_models_no_with_a_file_and_line_is_a_back(self, tmp_path):
        no = [*ALL_YES[:3], {"question": 4, "answer": "no", "where": "tests/test_x.py:12",
                             "why": "it asserts only that a word is in a file"}, ALL_YES[4]]
        v, _ = R.review("999", 1, "ctx", clone=tmp_path, run=Replies(
            {"verdict": "clear", "findings": [], "refuter_pass": TABLE, "code_checklist": no}))
        assert v["verdict"] == "back" and v["findings"][0]["where"] == "tests/test_x.py:12"

    @pytest.mark.parametrize("checklist, why", [
        (None, "no code checklist"),
        (ALL_YES[:4], "not each of 1-5 once"),
        ([*ALL_YES, ALL_YES[0]], "not each of 1-5 once"),
        ([{**ALL_YES[0], "answer": "no", "where": "the payments code"}, *ALL_YES[1:]],
         "names no file and line"),
    ])
    def test_a_checklist_that_does_not_answer_stops(self, tmp_path, checklist, why):
        reply = {"verdict": "clear", "findings": [], "refuter_pass": TABLE,
                 "code_checklist": checklist}
        if checklist is None:
            reply.pop("code_checklist")
            run = Replies(reply)
            run.queue = [q.replace('"code_checklist"', '"ignored"') for q in run.queue]
        else:
            run = Replies(reply)
        with pytest.raises(rank_call.Stop, match=why):
            R.review("999", 1, "ctx", clone=tmp_path, run=run)

    def test_the_schema_requires_the_checklist(self):
        assert "code_checklist" in R.SCHEMA["required"]


# ---------------------------------------------------------- the dispatcher
def test_the_stage_hands_the_scan_to_the_review(w, monkeypatch):
    """Wiring: the Red Team stage scans the branch, and a scripted no turns
    the model's clear into a back (`build:open`)."""
    to_pr(w)
    seen = []

    def scan(clone, base="origin/master"):
        seen.append(base)
        return {"no": [{"question": 3, "where": "src/motodiag/payments/refunds.py:8",
                        "why": "planted"}], "public": [], "sensitive": [], "tests": []}

    monkeypatch.setattr(D.red_team, "code_scan", scan)
    from test_phase390_resume import CLEAR
    advance(w, CLEAR)
    assert seen and "build:open" in labels(w)
