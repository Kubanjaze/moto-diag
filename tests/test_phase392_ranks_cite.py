"""Phase 392 — every rank that plans or judges reads the plan of record and
cites it.

On the good tree (phase 900: its "Next, in order" row, the dated entry
2026-10-05, K90): each brief carries `plan_order.brief_block`, and each
thing a rank writes ends with `plan_order.cite_line`: the Science
Officer's report (scripted), the XO's verdict, the Quartermaster's verdict,
and on the 389 walk-through the Red Team's and the Captain's comments.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(ROOT / "tests"))
import captain  # noqa: E402
import plan_check  # noqa: E402
import plan_order  # noqa: E402
import quartermaster  # noqa: E402
import rank_call  # noqa: E402
import red_team  # noqa: E402
import scout  # noqa: E402
import test_phase389_dispatcher as T389  # noqa: E402
import xo  # noqa: E402
from plan_check import FIXTURE_PHASE, GOOD  # noqa: E402
from test_phase388_dispatcher import claude_json  # noqa: E402
from test_phase389_dispatcher import world  # noqa: E402,F401  (the fixture)
from test_phase389_fleet_git import git  # noqa: E402

HEAD = "=== the plan of record and docs/decisions.md, on phase 900 ==="
CITE = plan_order.cite_line(GOOD, FIXTURE_PHASE)


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("FLEET_LEDGER", str(tmp_path / "calls.jsonl"))


class Replies:
    def __init__(self, *structured, model=rank_call.FABLE):
        self.queue = [claude_json(s, model=model) for s in structured]
        self.prompts: list[str] = []

    def __call__(self, cmd, **kw):
        if cmd[0] == "claude":
            self.prompts.append(cmd[cmd.index("-p") + 1])
            return subprocess.CompletedProcess(cmd, 0, self.queue.pop(0), "")
        return subprocess.CompletedProcess(cmd, 0, "{\"comments\": []}", "")


@pytest.fixture
def repo(tmp_path):
    c = tmp_path / "clone"
    shutil.copytree(GOOD, c)
    git("init", "-q", "-b", "master", cwd=c)
    git("add", "-A", cwd=c)
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "good", cwd=c)
    return c


def test_the_cite_line_names_the_entry_the_date_and_the_k_id():
    assert CITE == ("The plan of record on this phase: the plan of record's 'Next, in order' "
                    "#1; the plan of record, 2026-10-05; K90.")
    assert HEAD in plan_order.brief_block(GOOD, FIXTURE_PHASE)
    assert '"do the widget check"' in plan_order.brief_block(GOOD, FIXTURE_PHASE)


def test_the_science_officers_section_is_scripted_and_passes_p3():
    record = plan_order.brief_block(GOOD, FIXTURE_PHASE)
    s = scout.record_section(FIXTURE_PHASE, CITE, record)
    assert s.startswith("## The plan of record\n") and CITE in s and record in s
    assert plan_check.unshown_counts(s) == []


def test_the_science_officers_report_carries_the_section():
    """Not only built: rendered into the Step 0 report itself."""
    s = scout.record_section(FIXTURE_PHASE, CITE, plan_order.brief_block(GOOD, FIXTURE_PHASE))
    v = {"classification": "extension", "reason": "r", "what_exists": "e",
         "what_the_row_promises": "p", "risks_and_stops": "None found."}
    text = scout.render(FIXTURE_PHASE, "t", 1, "abcdef1", v, "table", [], [], dt.date(2026, 10, 27),
                        s)
    assert s in text and text.index("## Risks and stops") < text.index("## The plan of record")


def test_the_science_officers_judgement_reads_the_record():
    r = Replies({"classification": "extension", "reason": "It adds.", "what_exists": "x",
                 "what_the_row_promises": "y", "risks_and_stops": "None found."},
                model=rank_call.HAIKU)
    scout.assess("m", "row", "table", [], "ctx", cwd=GOOD, run=r,
                 record=plan_order.brief_block(GOOD, FIXTURE_PHASE))
    assert HEAD in r.prompts[0]


def test_the_captains_plan_and_recommendation_read_the_record(repo):
    plan = (GOOD / plan_check.plan_paths(FIXTURE_PHASE)[0]).read_text()
    (repo / plan_check.plan_paths(FIXTURE_PHASE)[0]).unlink()
    r = Replies({"implementation_md": plan},
                {"decision": "merge", "lines": ["It ships.", "Checked.", "Merge: clean."]})
    captain.write_plan(FIXTURE_PHASE, "| 900 |", "", "step0", clone=repo, run=r)
    captain.recommend(FIXTURE_PHASE, "summary", clone=repo, run=r)
    assert all(HEAD in p for p in r.prompts)
    assert '"The plan of record"' in captain.BRIEF and "Unblocks:" in captain.BRIEF


def test_the_captains_plan_without_a_citation_fails_p9_twice_and_stops(repo):
    plan = (GOOD / plan_check.plan_paths(FIXTURE_PHASE)[0]).read_text()
    bad = plan.replace("- The operator's K90 puts this phase in order.", "- Because.")
    (repo / plan_check.plan_paths(FIXTURE_PHASE)[0]).unlink()
    r = Replies({"implementation_md": bad}, {"implementation_md": bad})
    with pytest.raises(rank_call.Stop, match="P9 FAIL"):
        captain.write_plan(FIXTURE_PHASE, "| 900 |", "", "step0", clone=repo, run=r)
    assert "P9 FAIL" in r.prompts[1]                       # the second call is told why


def test_the_xos_brief_reads_the_record_and_its_verdict_cites_it(repo):
    r = Replies({"verdict": "approve", "items": [], "reason": ""})
    out: list[str] = []
    assert xo.review(FIXTURE_PHASE, None, repo=repo, label=False, run=r, out=out.append) == 0
    assert HEAD in r.prompts[0]
    assert any(CITE in o for o in out), out


def test_the_red_teams_context_reads_the_record(repo):
    assert HEAD in red_team.gather(repo, FIXTURE_PHASE, "F9 lint: clean", base="master")


def test_the_quartermasters_context_and_verdict_cite_the_record(repo):
    ctx = quartermaster.gather(repo, FIXTURE_PHASE, [], {"verify": [], "cited": [],
                                                         "captain": "-", "red_team": "-"}, "", "")
    assert HEAD in ctx
    text = quartermaster.verdict_text(FIXTURE_PHASE, "merge", [], "Fine.", cite=CITE)
    assert CITE in text
    assert "Q1" in quartermaster.BRIEF.split("4. The plan of record")[1].split("\n\n")[0]


def test_the_walk_through_red_team_and_captain_comments_cite_the_record(world):
    T389.test_mission_to_merge_needs_review(world)
    fleet, host, *_ = world
    origin = world[3]
    cite = plan_order.cite_line(origin, T389.PHASE)
    assert "K92" in cite
    said = host.comments(31)
    red = [c for c in said if c.startswith("<!-- fleet-red-team: verdict=")]
    rec = [c for c in said if c.startswith("<!-- fleet-captain: recommendation=")]
    assert red and rec
    assert all(cite in c for c in red + rec), (red, rec)
    xo_said = [c for c in said if c.startswith("<!-- xo-verdict:")]
    assert xo_said and all(cite in c for c in xo_said)
