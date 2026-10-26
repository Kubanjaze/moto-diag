"""Phase 391 — the Quartermaster's checks, each on its own known-bad case.

The good tree is a real phase the operator merged: 390 at its close-out
(`48e7d2c`, merged as `546fa25`), with `master` at 390's base (`6f32013`)
and one commit correcting its handoff's paste block (F222: R8 refuses the
block as 390 shipped it, and Q8 runs R8). Each known-bad case is one edit
to that tree, and must fail its own check and no other (387's rule for the
plan checklist). `verify_phase.sh`'s output is the one measured in the fence
on PR #20's head (`fixtures/quartermaster/pr20/verify.txt`).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
FIX = SKILL / "fixtures" / "quartermaster"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(ROOT / "tests"))

import quartermaster as Q  # noqa: E402
import rank_call  # noqa: E402
from rank_call import Stop  # noqa: E402
from test_phase388_dispatcher import claude_json  # noqa: E402

TIP, BASE, PHASE = "48e7d2c", "6f32013", "390"
VERIFY = (FIX / "pr20" / "verify.txt").read_text()
HANDOFF = "docs/handoffs/2026-10-26_390_closed.md"
IMPL = f"docs/phases/completed/{PHASE}_implementation.md"
LOG = f"docs/phases/completed/{PHASE}_phase_log.md"


def git(clone: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(clone), "-c", "user.name=t", "-c", "user.email=t@l",
                           *args], capture_output=True, text=True, check=True).stdout


def edit(clone: pathlib.Path, rel: str, old: str, new: str, *, commit: bool = True) -> None:
    p = clone / rel
    text = p.read_text(encoding="utf-8")
    assert text.count(old) == 1, (rel, old)
    p.write_text(text.replace(old, new), encoding="utf-8")
    if commit:
        git(clone, "commit", "-qam", f"edit {rel}")


@pytest.fixture
def tree(tmp_path) -> pathlib.Path:
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", "--shared", "--no-checkout", str(ROOT), str(clone)],
                   check=True)
    git(clone, "checkout", "-q", "-B", "phase-390-resume", TIP)
    git(clone, "branch", "-q", "-f", "master", BASE)
    edit(clone, HANDOFF, "gh issue edit 14 --remove-label",
         "gh issue edit 14 -R Kubanjaze/moto-diag --remove-label")
    return clone


def head(clone: pathlib.Path) -> str:
    return git(clone, "rev-parse", "HEAD").strip()


def failing(clone: pathlib.Path) -> list[str]:
    """The tree-reading checks that fail: Q1, Q6, Q7, Q8, Q9."""
    v11 = Q._text(Q.doc(clone, PHASE, "implementation"))
    found = [Q.scope(clone, PHASE), Q.claims(clone, PHASE, head(clone))[0], Q.stubs(v11),
             Q.handoff(clone, PHASE), Q.mergeable(clone)]
    return [f.check for f in found if f.ok is False]


# ------------------------------------------------------------ the good tree
def test_the_real_merged_phase_passes_every_tree_check(tree):
    assert failing(tree) == []


def test_390_as_it_shipped_fails_q8_on_its_paste_block(tree):
    """The real case: 390's handoff block, which failed for the operator
    on 2026-10-26, is what the Quartermaster refuses."""
    git(tree, "reset", "-q", "--hard", TIP)
    q8 = Q.handoff(tree, PHASE)
    assert failing(tree) == ["Q8"] and "R8" in q8.why and "gh issue edit 14" in q8.why


# ------------------------------------------------------------ Q1, the scope
@pytest.mark.parametrize("case", ["reshape", "migration", "content", "data", "deploy"])
def test_q1_refuses_what_is_out_of_scope(tree, case):
    if case == "reshape":
        edit(tree, f"docs/phases/completed/{PHASE}_step0.md", "Classification: **extension**",
             "Classification: **reshape**")
    else:
        rel = {"migration": Q.MIGRATIONS, "content": Q.CONTENT_PATHS[0] + "x_planted.json",
               "data": "data/planted.txt",
               "deploy": f"docs/phases/completed/{PHASE}_dryrun_diff.md"}[case]
        p = tree / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text((p.read_text() if p.is_file() else "") + "\n# planted\n")
        git(tree, "add", "-A")
        git(tree, "commit", "-qm", f"plant {case}")
    q1 = Q.scope(tree, PHASE)
    assert failing(tree)[:1] == ["Q1"] and q1.ok is False, q1


def test_q1_reads_the_classification_as_plan_check_does():
    import plan_check
    assert plan_check.classification("Classification: **Extension** of x") == "extension"
    assert plan_check.classification("no line") is None


# --------------------------------------------------------- Q2, Q3 the issue
def comment(body: str, at: str) -> dict:
    return {"body": body, "createdAt": at}


CAP_MERGE = comment("<!-- fleet-captain: recommendation=merge run=r -->\n**Captain**", "2026-10-26T10:00:00Z")
RED_CLEAR = comment("<!-- fleet-red-team: verdict=clear round=2 run=r -->\nok", "2026-10-26T09:00:00Z")
READY = comment("<!-- fleet-engineer: pr-ready round=1 pr=7 run=r -->\nPR", "2026-10-26T08:00:00Z")


def ids(found):
    return [f.check for f in found if f.ok is False]


def test_q2_q3_pass_on_a_clear_and_a_merge():
    found, texts = Q.issue_checks([READY, RED_CLEAR, CAP_MERGE])
    assert ids(found) == [] and "recommendation=merge" in texts["captain"]


@pytest.mark.parametrize("comments,want", [
    ([READY, RED_CLEAR, comment("<!-- fleet-captain: recommendation=hold run=r -->", "2026-10-26T10:00:00Z")], ["Q2"]),
    ([READY, comment("<!-- fleet-red-team: verdict=back round=1 run=r -->", "2026-10-26T09:00:00Z"), CAP_MERGE], ["Q3"]),
    ([RED_CLEAR, comment("<!-- fleet-engineer: pr-ready round=2 pr=7 run=r -->", "2026-10-26T09:30:00Z"), CAP_MERGE], ["Q3"]),
    ([READY], ["Q2", "Q3"]),
])
def test_q2_q3_each_case_on_its_own_check(comments, want):
    assert ids(Q.issue_checks(comments)[0]) == want


def test_the_real_390A_record_fails_q2_and_q3():
    """#24's Captain marker and PR #20's Red Team verdicts, as GitHub holds them."""
    found, _ = Q.issue_checks([
        comment("<!-- fleet-red-team: verdict=back round=1 run=20261025_231739_red_team_390A -->",
                "2026-10-26T03:19:47Z"),
        comment("<!-- fleet-captain: recommendation=hold run=20261025_232502_recommend_390A -->",
                "2026-10-26T03:26:50Z")])
    assert ids(found) == ["Q2", "Q3"]


# ---------------------------------------------------------- Q4 the full run
LINE = ("Regression of record: 11415 passed, 0 failed, 105 skipped, 0 errors at `8e70fc5` "
        "(38 min 13 s wall, `python -m pytest -n auto --dist load`, exit 0)")


def test_q4(tree):
    log = (tree / LOG).read_text()
    assert Q.full_run(True, LINE, "", log).ok
    assert not Q.full_run(True, LINE.replace("11415", "11414"), "", log).ok
    assert not Q.full_run(False, None, "subprocess timed out", log).ok
    assert not Q.full_run(True, LINE, "", "no line here").ok
    assert Q.regression_hash(tree, PHASE) == "8e70fc5"


# ------------------------------------------------------- Q5 verify_phase.sh
def test_q5_reads_the_measured_fence_output():
    found = {f.check: f for f in Q.read_verify(VERIFY, "390A")}
    assert [c for c, f in found.items() if f.ok is False] == ["V12"]
    assert [c for c, f in found.items() if f.ok is None] == ["V1", "V7", "V8", "V9"]


def section(text: str, n: int, new: str) -> str:
    """`text` with check n's section body replaced, where it stands."""
    start = text.index(f"=== {n}. ")
    body = text.index("\n", start) + 1
    end = text.find(f"=== {n + 1}. ", body)
    return text[:body] + new + "\n" + (text[end:] if end != -1 else "")


@pytest.mark.parametrize("n,new", [
    (2, "--- code after the regression hash ---\nsrc/motodiag/x.py"),
    (3, "--- in_progress (empty) ---\n390A_phase_log.md"),
    (5, "--- register contiguous from #1, each naming its commit ---\nA4 bug-fix numbering is not contiguous"),
    (6, "131"),
    (10, "/usr/bin/python3: No module named pytest"),
    (10, "FAILED tests/test_x.py::t\n===== 1 failed, 3 passed in 2.00s ====="),
    (11, "A2 phase log Status line is not Complete"),
    (13, "B2 F999 cited but not filed"),
    (14, "  no regression line names its command"),
])
def test_each_verify_check_fails_on_its_own_red_section(n, new):
    found = Q.read_verify(section(VERIFY, n, new), "390A")
    assert [f.check for f in found if f.ok is False] == sorted({f"V{n}", "V12"}, key=lambda c: int(c[1:]))


def test_v10_the_no_pytest_trap_is_red():
    """Step 0: with no virtualenv, check 10 printed one line and no summary."""
    v10 = next(f for f in Q.read_verify(section(VERIFY, 10, "/usr/bin/python3: No module named pytest"),
                                        "390A") if f.check == "V10")
    assert v10.ok is False


def test_v4_hits_go_to_the_model_not_to_a_verdict():
    found = Q.read_verify(section(VERIFY, 4, "docs/phases/completed/390A_phase_log.md:7:TODO tidy"), "390A")
    v4 = next(f for f in found if f.check == "V4")
    assert v4.ok is None and "TODO tidy" in v4.why


def test_a_missing_section_fails():
    found = Q.read_verify(VERIFY.split("=== 13.")[0], "390A")
    assert {"V13", "V14"} <= {f.check for f in found if f.ok is False}


# ------------------------------------------------------- Q6 the commit claims
@pytest.mark.parametrize("hash_", ["133dc26", "abcdef1"], ids=["not-an-ancestor", "no-such-commit"])
def test_q6_a_claim_outside_the_heads_history(tree, hash_):
    edit(tree, LOG, "**Commit.** `f681617`", f"**Commit.** `{hash_}`")
    q6, _ = Q.claims(tree, PHASE, head(tree))
    assert failing(tree) == ["Q6"] and hash_ in q6.why


def test_q6_lists_cited_hashes_that_are_not_claims(tree):
    _, cited = Q.claims(tree, PHASE, head(tree))
    assert any(c.startswith("e15b462") for c in cited), "#14's held commit, cited, not claimed"


# ---------------------------------------------------------------- Q7 stubs
@pytest.mark.parametrize("old,new", [
    ("## Results\n", "## Results\n\nTo be written after the merge.\n\n## Results, as measured\n"),
    ("## Deviations\n", "## Departures\n"),
    ("- [x] ", "- [ ] "),
], ids=["a-stub-results-section", "no-deviations", "an-open-box"])
def test_q7_each_stub(tree, old, new):
    p = tree / IMPL
    text = p.read_text()
    assert old in text
    p.write_text(text.replace(old, new, 1))
    git(tree, "commit", "-qam", "plant a stub")
    assert failing(tree) == ["Q7"], Q.stubs(p.read_text())


# -------------------------------------------------------------- Q8 handoff
def test_q8_no_handoff(tree):
    git(tree, "rm", "-q", HANDOFF)
    git(tree, "commit", "-qm", "the handoff, gone")
    q8 = Q.handoff(tree, PHASE)
    assert failing(tree) == ["Q8"] and "no docs/handoffs/" in q8.why


def test_q8_a_handoff_with_no_next(tree):
    edit(tree, HANDOFF, "## What is next", "## Later")
    assert failing(tree) == ["Q8"]


def test_q8_a_handoff_dated_before_the_close(tree):
    git(tree, "mv", HANDOFF, HANDOFF.replace("2026-10-26", "2026-10-24"))
    git(tree, "commit", "-qm", "an early handoff")
    assert failing(tree) == ["Q8"]


# ------------------------------------------------------------ Q9 mergeable
def test_q9_dirty(tree):
    (tree / "planted.txt").write_text("x")
    assert failing(tree) == ["Q9"]


def test_q9_a_conflict_with_master(tree):
    git(tree, "switch", "-q", "master")
    edit(tree, "docs/ROADMAP.md", "| 390 |", "| 390 | (master moved) |")
    git(tree, "switch", "-q", "phase-390-resume")
    q9 = Q.mergeable(tree)
    assert q9.ok is False and "docs/ROADMAP.md" in q9.why


# --------------------------------------------------- the model, and composing
def fake(answer: dict):
    out = claude_json(answer, model=rank_call.OPUS)
    return lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, out, "")


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("FLEET_LEDGER", str(tmp_path / "calls.jsonl"))


@pytest.mark.parametrize("answer,why", [
    ({"verdict": "refuse", "failed": [{"check": "Q3 the Captain's recommendation", "why": "x"}],
      "summary": "s"}, "do not exist"),
    ({"verdict": "refuse", "failed": [], "summary": "s"}, "naming no check"),
    ({"verdict": "merge", "failed": [{"check": "Q7", "why": "x"}], "summary": "s"}, "merge, with"),
    ({"verdict": "merge", "failed": [], "summary": " "}, "no summary"),
])
def test_an_answer_that_cannot_be_used_is_a_stop(tmp_path, answer, why):
    with pytest.raises(Stop, match=why):
        Q.judge(PHASE, "ctx", clone=tmp_path, run=fake(answer))


def test_the_dry_runs_real_answer_is_a_stop():
    """Step 0's call on PR #20 named checks of its own; the brief now lists
    the ids, and an answer like that one is not acted on."""
    real = json.loads((FIX / "pr20" / "verdict.json").read_text())
    with pytest.raises(Stop, match="do not exist"):
        Q.judge("390A", "ctx", clone=FIX, run=fake(real))


def test_the_brief_lists_every_check_id():
    text = Q.brief(PHASE)
    assert all(f"  {k}: " in text for k in Q.CHECKS)


def test_a_scripted_failure_refuses_over_a_model_merge():
    found = [Q.Finding("Q1", True), Q.Finding("Q8", False, "no handoff")]
    verdict, failed, note = Q.compose(found, {"verdict": "merge", "failed": [], "summary": "s"})
    assert verdict == "refuse" and failed == [("Q8", "no handoff")] and "merge" in note


def test_the_model_may_add_a_refusal():
    found = [Q.Finding("Q1", True)]
    verdict, failed, _ = Q.compose(found, {"verdict": "refuse", "summary": "s",
                                           "failed": [{"check": "V4", "why": "a stub"}]})
    assert verdict == "refuse" and failed == [("V4", "a stub")]


def test_all_green_merges():
    assert Q.compose([Q.Finding("Q1", True)], {"verdict": "merge", "failed": [],
                                               "summary": "s"})[:2] == ("merge", [])


def test_the_verdict_text_says_shadow_and_names_each_check():
    text = Q.verdict_text("390", "refuse", [("Q8", "no handoff")], "Hold it.")
    assert "(shadow): refuse" in text and "- Q8 (the handoff): no handoff" in text
    assert "nothing is merged" in text
