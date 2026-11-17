"""Phase 403 (e) — a review round the operator grants is recorded (F277, K88).

The operator's three conditions (K88): "1. One written grant = one extra
round. No 5th round without a new grant from me. 2. Ship it with a
regression test: a granted 4th round's findings get saved and acted on, and
an ungranted 4th round never runs. 3. Update the 403 plan before any code."

372's fourth review is replayed from its journal
(`tests/fixtures/phase403/red_team_372_round4.json`: run
`20261115_125327_red_team_372`, call 0's whole output). With a grant planted
in master's `docs/decisions.md` its table is recorded and its back starts a
fix round; with none, no fourth round starts, where the old code ran one;
one grant never lets a fifth round start.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "phase403"
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "closeout"))
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "refute"))
sys.path.insert(0, str(ROOT / "tests"))

import closeout_check as C  # noqa: E402
import dispatcher as D  # noqa: E402
import plan_order  # noqa: E402
import red_team  # noqa: E402
import refute_check  # noqa: E402
from test_phase389_dispatcher import BRANCH, PHASE  # noqa: E402
from test_phase389_fleet_git import git  # noqa: E402
from test_phase390_resume import BACK, N, advance, calls, labels, ledger, to_pr, w  # noqa: E402

assert w and ledger  # the fixtures, imported for their names

ROUND4 = json.loads((FIX / "red_team_372_round4.json").read_text(encoding="utf-8"))
TABLE4 = json.loads(ROUND4["stdout"])["structured_output"]["refuter_pass"]
#: The rows the checker reads: 15 of the table's 16. The 16th quotes a line
#: holding `\|`, which splits its cells (filed as F279, left).
READ = [ln for ln in TABLE4.splitlines() if refute_check._ROW.match(ln) and "| 4 · " in ln]
GRANT = "K93"
ROW = f'| {GRANT} | 2026-11-16 | "one more review round for {PHASE}" | No check. | ' \
      f"grant=review-round subject={PHASE} |"


def commit_on_master(w, rel: str, add: str) -> None:
    p = w.origin / rel
    p.write_text((p.read_text() if p.is_file() else "") + add)
    git("add", rel, cwd=w.origin)
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", rel, cwd=w.origin)


def grant(w, row: str = ROW) -> None:
    commit_on_master(w, "docs/decisions.md", row + "\n")


def plant(w, body: str) -> None:
    w.host.gh(["gh", "issue", "comment", str(N), "--body", body])


def review_open_again(w) -> None:
    w.clock.t += D.dt.timedelta(minutes=1)
    if "review:open" in w.host.issues[N]["labels"]:
        w.host.issues[N]["labels"].remove("review:open")
    w.host.label(N, "review:open")


def to_round(w, done: int) -> None:
    """`done` rounds came back, then `review:open` applied again: as 372
    stood at 12:53 EST on 2026-11-15 for done=3."""
    commit_on_master(w, "docs/FOLLOWUPS.md",
                     "# Follow-ups\n\nAt the time of writing the highest assigned is **F1** "
                     "(this file).\n\n### F1\n\nA planted finding.\n")
    to_pr(w)
    for r in range(1, done + 1):
        plant(w, f"{D.RED_M} verdict=back round={r} -->\nplanted: round {r} came back")
    review_open_again(w)


def stopped(w) -> str:
    return next(c for c in reversed(w.host.comments(N))
                if c.startswith(f"{D.MARKER} stopped rank=red-team"))


# ------------------------------------------------- the replay of 372's round 4
def test_an_ungranted_fourth_round_never_runs(w):
    """Red on the old code: it called the model for round 4 (here, with no
    reply to give, the stand-in fails)."""
    to_round(w, 3)
    n = len(calls(w))
    advance(w)
    assert len(calls(w)) == n, "a fourth round ran with no grant"
    said = stopped(w)
    assert "the review rounds are spent, 3 of 3" in said and "No review round 4 starts" in said
    for option in ("1. Grant one more review round", "2. Fix it by hand", "3. Merge it as it"):
        assert option in said
    assert "review:open" in labels(w), "the label moved"


def test_a_granted_fourth_round_is_recorded_and_acted_on(w):
    """372's round 4, as it ran: back, on one code and one wording finding.
    Red on the old code: C5 refused all 16 rows and nothing was recorded."""
    to_round(w, 3)
    grant(w)
    advance(w, ROUND4["stdout"])
    pr = next(iter(w.host.prs.values()))
    table = next(c for c in pr["comments"] if "round=4" in c)
    assert table.count(f"| 4 {GRANT} · ") == len(READ) == 15 and TABLE4.count("| 4 · ") == 16
    said = w.host.comments(N)
    assert any(c.startswith(f"{D.RED_M} verdict=back round=4") for c in said)
    assert labels(w) == ["build:open", "mission"], "the back did not start a fix round"
    assert any("[code]" in c and "round 4: back" in c for c in said), "the findings were not said"
    advance(w)                                     # the fix round
    assert w.engineer.runs == 2 and labels(w) == ["mission", "review:open"]


def test_one_grant_never_lets_a_fifth_round_start(w):
    to_round(w, 3)
    grant(w)
    advance(w, ROUND4["stdout"])
    advance(w)                                     # the fix round, then review:open
    n = len(calls(w))
    advance(w)
    assert len(calls(w)) == n, "a fifth round ran on one grant"
    assert "No review round 5 starts" in stopped(w)
    grant(w, ROW.replace(GRANT, "K94"))           # a second grant
    review_open_again(w)
    advance(w, ROUND4["stdout"].replace("| 4 · ", "| 5 · "))
    assert any(c.startswith(f"{D.RED_M} verdict=back round=5") for c in w.host.comments(N))


@pytest.mark.parametrize("row", [
    ROW.replace(f"subject={PHASE}", "subject=903"),
    ROW.replace(f"subject={PHASE}", f"subject={PHASE},903"),
    ROW.replace("grant=review-round", "grant=review-rounds"),
    f'| {GRANT} | 2026-11-16 | "one more review round for {PHASE}" | No check. | no stop |',
], ids=["another phase", "two phases", "another form", "only the words"])
def test_a_grant_in_any_other_form_grants_nothing(w, row):
    to_round(w, 3)
    grant(w, row)
    n = len(calls(w))
    advance(w)
    assert len(calls(w)) == n and "No review round 4 starts" in stopped(w)


def test_round_3_with_no_grant_stops_and_names_the_options(w):
    to_round(w, 2)
    advance(w, BACK)
    note = w.host.comments(N)[-1]
    assert note.startswith(f"{D.MARKER} needs-admiral rank=red-team")
    assert "round 3 of 3" in note and "The operator decides." in note
    assert "3. Merge it as it stands." in note
    w.host.issues[N]["labels"].remove("needs-admiral")
    w.host.label(N, "build:open")                  # K85's way, with no grant
    runs = w.engineer.runs
    advance(w)
    assert w.engineer.runs == runs, "a fix round ran past round 3 with no grant"
    assert "the review rounds are spent, 3 of 3" in w.host.comments(N)[-1]


def test_a_grant_at_round_3_lets_the_fix_round_and_round_4_run(w):
    to_round(w, 2)
    grant(w)
    advance(w, BACK)
    assert labels(w) == ["build:open", "mission"]
    advance(w)
    assert labels(w) == ["mission", "review:open"]


# --------------------------------------------------------- the record's rules
def test_grants_are_found_by_lookup_only():
    text = "\n".join([
        ROW,
        ROW.replace(GRANT, "K95").replace(f"subject={PHASE}", "subject=903"),
        ROW.replace(GRANT, "K96").replace(f"subject={PHASE}", f"subject={PHASE},903"),
        f'| K97 | 2026-11-16 | "grant=review-round subject={PHASE}" | No check. | no stop |',
        ROW.replace(GRANT, "K98"),
    ])
    assert refute_check.grants(text, PHASE) == [GRANT, "K98"]
    assert refute_check.grants(text, "903") == ["K95"]


def test_the_record_check_takes_a_grant_and_refuses_other_forms():
    assert plan_order.covers_problem(f"grant=review-round subject={PHASE}") is None
    for bad in (f"grant=review-round subject={PHASE},903", "grant=review-round",
                f"grant=one-round subject={PHASE}"):
        assert plan_order.covers_problem(bad), bad


def test_c5_on_372s_round_4_table():
    """The 12:56 EST stop, measured: every row the checker reads fails C5
    with no grant."""
    c5 = [f for f in refute_check.check(TABLE4) if f.startswith("C5 ")]
    assert len(c5) == len(READ) == 15
    assert all("is round 4; at most 3 refute rounds" in f for f in c5)
    named = red_team.with_grant(TABLE4, 4, GRANT)
    assert [f for f in refute_check.check(named, grants=[GRANT]) if f.startswith("C5 ")] == []
    assert any(f.startswith("C5 ") for f in refute_check.check(named, grants=["K94"]))
    assert any(f.startswith("C5 ") for f in refute_check.check(named)), "a grant named, none held"
    five = named.replace(f"| 4 {GRANT} · ", f"| 5 {GRANT} · ")
    assert any(f.startswith("C5 ") for f in refute_check.check(five, grants=[GRANT]))
    early = TABLE4.replace("| 4 · ", f"| 2 {GRANT} · ")
    assert any("only a round past 3 is granted" in f
               for f in refute_check.check(early, grants=[GRANT]))


def test_a8_reads_the_grants(tmp_path):
    log = ("# 372 log\n\n" + red_team.with_grant(TABLE4, 4, GRANT)
           .replace("· open", "· fixed").replace("· open F9999", "· fixed"))
    assert any("C5 " in f for f in C.refute_record(log, "372"))
    assert not any("C5 " in f for f in C.refute_record(log, "372", [GRANT]))
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "decisions.md").write_text(ROW.replace(PHASE, "372") + "\n")
    assert C.review_grants(tmp_path, "372") == [GRANT]
    assert C.review_grants(tmp_path, "371") == []
