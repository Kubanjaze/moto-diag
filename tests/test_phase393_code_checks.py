"""Phase 393 (K54) — the Quartermaster's Q10, Q11 and Q12, on hand-written fixtures.

Each fixture under `.claude/skills/fleet/fixtures/code_checks/` is a base
tree and a head tree (and, for Q11, the head's coverage JSON), committed
into a throwaway repository here as `master` and a pull request's branch:

  good             a typed, covered, small change: Q10, Q11 and Q12 pass
  q10_bad          an unused import (ruff) and a wrong return type (mypy)
  q11_bad          a new function the tests never run: 1 of 8 lines covered
  q12_bad_complex  a function taken from McCabe 20 to 22
  q12_bad_size     a file grown past a limit, and grown while over one

A failure refuses, and the verdict names the file and the number.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLEET = ROOT / ".claude" / "skills" / "fleet"
FIX = FLEET / "fixtures" / "code_checks"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(FLEET))

sys.path.insert(0, str(ROOT / "tests"))

import code_quality as cq  # noqa: E402
import quartermaster as Q  # noqa: E402
from test_phase390_resume import D, advance, w  # noqa: E402,F401
from test_phase391_dispatcher import REFUSE, qm_comments, to_merge_review, verdicts  # noqa: E402


def git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@l",
                           *args], check=True, capture_output=True, text=True).stdout


def repo_of(name: str, tmp: pathlib.Path) -> pathlib.Path:
    """The fixture's base as `master`, its head as the branch checked out."""
    repo = tmp / name
    repo.mkdir()
    git(repo, "init", "-q", "-b", "master")
    shutil.copyfile(FIX / "pyproject.toml", repo / "pyproject.toml")
    shutil.copytree(FIX / name / "base" / "src", repo / "src")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    git(repo, "checkout", "-qb", "phase-999-x")
    shutil.rmtree(repo / "src")
    shutil.copytree(FIX / name / "head" / "src", repo / "src")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "head")
    return repo


def checks(name: str, tmp: pathlib.Path, **kw) -> tuple[dict, dict]:
    repo = repo_of(name, tmp)
    cov = FIX / name / "coverage.json"
    return cq.pr_checks(repo, "master", **kw), cq.q11(cov if cov.is_file() else None, repo,
                                                     "master")


def findings(pr: dict | None, cov: dict, why: str = "") -> dict[str, Q.Finding]:
    return {f.check: f for f in Q.code_checks(pr, cov, why)}


# ------------------------------------------------------------------- good
def test_the_good_fixture_passes_all_three(tmp_path):
    pr, cov = checks("good", tmp_path)
    assert pr == {"Q10": [], "Q12": []} and cov["ok"] and cov["percent"] == 100.0
    assert all(f.ok for f in findings(pr, cov).values())


# -------------------------------------------------------------------- Q10
def test_q10_refuses_a_new_lint_finding_and_a_new_type_error(tmp_path):
    pr, cov = checks("q10_bad", tmp_path)
    got = {(e["tool"], e["file"], e["head"], e["base"]) for e in pr["Q10"]}
    assert got == {("ruff", "src/motodiag/svc.py", 1, 0), ("mypy", "src/motodiag/svc.py", 1, 0)}
    q10 = findings(pr, cov)["Q10"]
    assert q10.ok is False
    assert "src/motodiag/svc.py" in q10.why and "1 ruff finding" in q10.why
    assert "1 mypy error" in q10.why and "0 on master" in q10.why


def test_q10_uses_the_bases_rules_not_the_heads(tmp_path):
    """A pull request cannot loosen the rules it is checked by: a head that
    drops F from ruff's select is still checked with the base's."""
    repo = repo_of("q10_bad", tmp_path)
    cfg = repo / "pyproject.toml"
    cfg.write_text(cfg.read_text().replace('select = ["E", "F", "I", "W"]', 'select = ["E"]'))
    git(repo, "commit", "-qam", "loosen")
    assert any(e["tool"] == "ruff" for e in cq.pr_checks(repo, "master")["Q10"])


# -------------------------------------------------------------------- Q11
def test_q11_refuses_changed_lines_under_85_percent(tmp_path):
    pr, cov = checks("q11_bad", tmp_path)
    assert (cov["covered"], cov["measured"], cov["ok"]) == (1, 8, False)
    q11 = findings(pr, cov)["Q11"]
    assert q11.ok is False and "12.5%" in q11.why and "85%" in q11.why
    assert "src/motodiag/svc.py: 1 of 8" in q11.why


def test_q11_with_no_coverage_data_refuses(tmp_path):
    repo = repo_of("q11_bad", tmp_path)
    cov = cq.q11(None, repo, "master")
    assert cov["ok"] is False
    assert "no coverage data" in findings({"Q10": [], "Q12": []}, cov)["Q11"].why


def test_q11_passes_a_change_with_no_source_lines(tmp_path):
    repo = repo_of("good", tmp_path)
    git(repo, "checkout", "-q", "master")
    git(repo, "checkout", "-qb", "docs-only")
    (repo / "README.md").write_text("docs only\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "docs")
    assert cq.q11(None, repo, "master")["ok"] is True


# -------------------------------------------------------------------- Q12
def test_q12_refuses_a_changed_function_over_mccabe_20(tmp_path):
    pr, cov = checks("q12_bad_complex", tmp_path)
    [e] = pr["Q12"]
    assert (e["file"], e["function"], e["complexity"], e["limit"]) == (
        "src/motodiag/codes.py", "reason", 22, 20)
    q12 = findings(pr, cov)["Q12"]
    assert q12.ok is False and "`reason` is McCabe 22" in q12.why


def test_q12_refuses_a_file_grown_past_the_limit(tmp_path):
    pr, _ = checks("q12_bad_size", tmp_path, size_limit=800)
    [e] = pr["Q12"]
    assert (e["file"], e["limit"]) == ("src/motodiag/catalogue.py", 800)
    assert e["base_bytes"] <= 800 < e["bytes"]


def test_q12_refuses_a_file_already_over_the_limit_that_grows(tmp_path):
    pr, cov = checks("q12_bad_size", tmp_path, size_limit=700)
    [e] = pr["Q12"]
    assert 700 < e["base_bytes"] < e["bytes"]
    why = findings(pr, cov)["Q12"].why
    assert "catalogue.py is 858 bytes (790 on master), over the limit of 700" in why


def test_q12_passes_the_same_file_under_the_limit(tmp_path):
    """The exclusion's control: under the limit, growth is not Q12's."""
    pr, _ = checks("q12_bad_size", tmp_path, size_limit=1000)
    assert pr["Q12"] == []


def test_no_result_from_the_fenced_run_fails_q10_and_q12():
    found = findings(None, {"ok": True, "covered": 0, "measured": 0, "percent": None,
                            "worst": []}, "exit 1")
    assert found["Q10"].ok is False and found["Q12"].ok is False and "exit 1" in found["Q10"].why


# ------------------------------------------------------- the dispatcher's run
def test_the_fenced_command_takes_the_bases_script_when_it_has_one():
    cmd = Q.code_command("abc1234")
    script = cmd[-1]
    assert "git show abc1234:scripts/code_quality.py" in script
    assert "pr --base abc1234 --root ." in script


def test_the_result_is_read_from_the_last_json_line():
    out = 'noise\n{"Q10": [], "Q12": [{"file": "x"}]}\n'
    assert Q.code_result(out) == {"Q10": [], "Q12": [{"file": "x"}]}
    assert Q.code_result("Traceback\nboom\n") is None


class TestTheStage:
    """In 390's world (real git, `gh` and the fenced runs stood in): the
    dispatcher's Quartermaster stage runs the code check in the fence and
    refuses on what it finds, naming the file and the number."""

    @staticmethod
    def _code_out(w, out: str, coverage: str = "") -> list:
        seen = []
        real = w.fleet.check

        def check(clone, commit, *, full, command=None):
            if command and "code_quality.py pr" in command[-1]:
                seen.append(command)
                return D.Check(True, commit, out=out)
            c = real(clone, commit, full=full, command=command)
            return D.Check(c.ok, c.commit, c.line, c.why, c.out, coverage) if full else c

        w.fleet.check = check
        return seen

    def test_a_q10_failure_refuses_and_names_the_file(self, w):
        to_merge_review(w)
        seen = self._code_out(w, json.dumps({"Q10": [{"file": "src/motodiag/x.py", "tool": "ruff",
                                                       "head": 3, "base": 1}], "Q12": []}))
        advance(w, REFUSE)
        [text] = qm_comments(w)
        assert ("Q10 (lint and types, per touched file): src/motodiag/x.py: 3 ruff findings on "
                "the head, 1 on master") in text
        [cmd] = seen
        assert cmd[0] == "/bin/sh" and "--root ." in cmd[-1]
        assert "Q10" in verdicts(w)[0]["failed"]

    def test_no_result_from_the_code_check_refuses_q10_and_q12(self, w):
        to_merge_review(w)
        self._code_out(w, "Traceback: boom")
        advance(w, REFUSE)
        assert {"Q10", "Q12"} <= set(verdicts(w)[0]["failed"])

    def test_the_full_runs_coverage_is_kept_in_the_stages_folder(self, w, tmp_path):
        to_merge_review(w)
        cov = tmp_path / "x.coverage.json"
        cov.write_text(json.dumps({"files": {}, "totals": {"percent_covered": 90.0}}))
        self._code_out(w, json.dumps({"Q10": [], "Q12": []}), coverage=str(cov))
        advance(w, REFUSE)
        kept = sorted(w.fleet.runs.glob("*_quartermaster_902/head.coverage.json"))
        assert kept and kept[-1].read_text() == cov.read_text()


def test_the_three_are_named_checks():
    for q in ("Q10", "Q11", "Q12"):
        assert q in Q.CHECKS
    assert "Q1-Q12" in Q.BRIEF
