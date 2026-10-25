"""Phase 390 — the search on start: what it resumes, what it ends, what it says.

What must hold (v1.0 section 5, as built: the stall rule in Deviations):
- a `started` marker left open with nothing to resume from gets one stop
  comment, label unchanged, when no stage is due on its issue (F219's
  stall), and none when one is (#14 at 15:50: the operator re-applied
  `review:open`, and the Red Team was due);
- #14's real history, read from GitHub into `fixtures/resume/`, at three
  moments: F219's restart (15:34), the operator's re-apply (15:50), and
  16:33 (`needs-admiral`, the operator's);
- a journal whose issue is closed, held by the operator, no longer 🚧, or
  worked on by another stage since, is not resumed and is ended, with a
  comment on an open issue;
- `--dry-run` writes nothing; `run` and `once` search before their first
  cycle; `prune_runs` keeps an unfinished run.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
FIX = SKILL / "fixtures" / "resume"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(ROOT / "tests"))

import dispatcher as D  # noqa: E402
import journal as J  # noqa: E402
from test_phase388_dispatcher import iso  # noqa: E402
from test_phase389_fleet_git import git  # noqa: E402
from test_phase390_resume import APPROVE, SCOUT, V1, N, advance, killed, labels  # noqa: E402
from test_phase390_resume import ledger, model, restart, to_review, w  # noqa: E402

assert w and ledger  # the fixtures, imported for their names

ISSUE14 = json.loads((FIX / "issue14_1633.json").read_text())
EVENTS14 = [json.loads(ln) for ln in (FIX / "issue14_events_1633.jsonl").read_text().splitlines()]


def at(s: str) -> dt.datetime:
    return D._time(s)


def plant14(w, until: str, labels14: list[str]) -> None:
    """#14 as GitHub had it at `until`: its comments and `labeled` events up
    to then, its labels as given; row 389A 🚧 on master, as it is."""
    road = w.origin / "docs" / "ROADMAP.md"
    road.write_text(road.read_text().rstrip("\n") + "\n| 389A | 385's ROADMAP row | 🚧 | x |\n")
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "row 389A", cwd=w.origin)
    git("branch", "phase-389A-385s-roadmap-row", "master", cwd=w.origin)
    w.fleet.update_mirror()
    w.host.issues.clear()
    w.host.issues[14] = {
        "title": ISSUE14["title"], "body": "planted trial", "labels": list(labels14),
        "comments": [c for c in ISSUE14["comments"] if at(c["createdAt"]) <= at(until)],
        "events": [{"label": e["label"], "at": e["at"]} for e in EVENTS14
                   if e["event"] == "labeled" and at(e["at"]) <= at(until)]}
    w.clock.t = at(until).astimezone(w.clock.t.tzinfo) + dt.timedelta(minutes=1)
    w.planted14 = len(w.host.issues[14]["comments"])


def stops(w, n=14) -> list[str]:
    """Stop comments made here: #14's own history has some (the scout's, 389)."""
    old = w.planted14 if n == 14 else 0
    return [b for b in w.host.comments(n)[old:] if b.startswith(f"{D.MARKER} stopped")]


# ------------------------------------------------------------ #14, for real
def test_the_fixture_is_issue_14_as_read(w):
    assert ISSUE14["title"] == "Phase 389A: 385's ROADMAP row"
    started = [c for c in ISSUE14["comments"] if c["body"].startswith(D.ENGINEER_M + " started")]
    assert [c["createdAt"] for c in started][-2:] == ["2026-10-25T19:06:25Z",
                                                       "2026-10-25T20:02:02Z"]
    assert {"at": "2026-10-25T19:50:17Z", "event": "labeled", "label": "review:open"} in EVENTS14


def test_14_at_f219s_restart_is_a_stall_and_gets_one_stop(w):
    """15:34: the fix round's `started` (15:06) is the last rank comment,
    `build:open` is on, the Red Team's back is older: nothing is due."""
    plant14(w, "2026-10-25T19:34:11Z", ["mission", "build:open"])
    said = w.fleet.recover()
    assert said == ["stop the engineer on issue 14: started 2026-10-25T19:06:25+00:00, "
                    "nothing to resume from"]
    (stop,) = stops(w)
    assert "stopped rank=engineer run=none" in stop and "`review:open` again" in stop
    assert sorted(w.host.issues[14]["labels"]) == ["build:open", "mission"]
    assert w.fleet.recover() == [], "said twice"


def test_14_after_the_operators_reapply_has_a_stage_due_and_nothing_is_said(w):
    plant14(w, "2026-10-25T19:50:17Z", ["mission", "review:open"])
    said = w.fleet.recover()
    assert said == ["leave the engineer's cut stage on issue 14: a stage is due, the cycle runs it"]
    assert stops(w) == []


def test_14_now_is_the_operators_and_nothing_is_said(w):
    plant14(w, "2026-10-25T20:33:00Z", ISSUE14["labels"])
    assert "needs-admiral" in ISSUE14["labels"]
    assert w.fleet.recover() == [] and stops(w) == []


def test_14_with_needs_admiral_taken_off_and_its_run_held_has_the_recheck_due(w):
    """The operator's ask (2026-10-25): #14 stopped at 16:29 only because
    its model-free run was lost to load (F220). Its run is held by hand
    (`held.json`, as 390's code writes one); once the operator takes
    `needs-admiral` off, the recheck is the stage due, and nothing else."""
    plant14(w, "2026-10-25T20:33:00Z", ["mission", "build:open"])
    held = w.fleet.runs / "20261025_160200_engineer_389A"
    (held / "run").mkdir(parents=True)
    J.hold(held, {"issue": 14, "phase": "389A", "rnd": 2,
                  "commit": "e15b46278cc0" + "0" * 28})
    issue = {"title": ISSUE14["title"], "body": "planted trial",
             "labels": [{"name": "mission"}, {"name": "build:open"}]}
    assert w.fleet.held_for(14) == held
    rank, _ = w.fleet.next_stage(14, "389A", {"mission", "build:open"}, "planted trial",
                                 ISSUE14["title"])
    assert rank == "engineer" and not w.fleet.stalled(14, "389A", issue)
    J.release(held)
    assert w.fleet.held_for(14) is None
    assert w.fleet.next_stage(14, "389A", {"mission", "build:open"}, "planted trial",
                              ISSUE14["title"]) is None, "without the hold, #14 stays as it is"


def test_the_dry_run_on_14s_stall_writes_nothing(w):
    plant14(w, "2026-10-25T19:34:11Z", ["mission", "build:open"])
    log = w.fleet.state_dir / "dispatcher.log"
    before = log.read_text() if log.exists() else ""
    said = w.fleet.recover(dry_run=True)
    assert said and said[0].startswith("stop the engineer on issue 14")
    assert stops(w) == [] and (log.read_text() if log.exists() else "") == before
    assert all(ln.startswith("would ") for ln in w.lines[-len(said) - 1:-1])
    assert w.lines[-1] == "the search on start: 1 stage(s) acted on"


# ----------------------------------------------------- journals not resumed
def cut_scout(w):
    w.kill.at(model)
    killed(w)
    (j,) = J.unfinished(w.fleet.runs)
    return j


def test_a_journal_on_a_closed_issue_is_ended_with_no_comment(w):
    j = cut_scout(w)
    del w.host.issues[N]
    said = restart(w)
    assert said[0].startswith("not resume scout") and "closed" in said[0]
    assert J.Journal.load(j.run).data["outcome"].startswith("abandoned: issue 31 is closed")


def test_a_journal_on_an_issue_the_operator_holds_is_ended_and_said(w):
    j = cut_scout(w)
    w.host.label(N, "needs-admiral")
    said = restart(w)
    assert "the operator holds it" in said[0]
    assert stops(w, N)[-1].startswith(f"{D.MARKER} stopped rank=scout run={j.run.name}")
    assert not J.Journal.load(j.run).unfinished and w.host.model_calls() == []


def test_a_journal_whose_phase_closed_is_ended(w):
    cut_scout(w)
    road = w.origin / "docs" / "ROADMAP.md"
    road.write_text(road.read_text().replace("| 902 | The trial | 🚧 |",
                                             "| 902 | The trial | ✅ |"))
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "902 closed", cwd=w.origin)
    said = restart(w)
    assert "not 🚧" in said[0]


def test_a_journal_another_stage_has_passed_is_ended(w):
    j = cut_scout(w)
    w.host.issues[N]["comments"].append({"body": f"{D.SCOUT_M} step0 commit=abc -->\nby hand",
                                         "createdAt": iso(w.clock())})
    said = restart(w)
    assert "another stage has run on it since" in said[0]
    assert not J.Journal.load(j.run).unfinished


def test_the_xos_own_verdict_does_not_count_as_another_stage(w):
    to_review(w)
    w.kill.at(lambda c: c[:3] == ["gh", "issue", "comment"]
              and c[c.index("--body") + 1].startswith("<!-- xo-verdict:"), after=True)
    killed(w, APPROVE)
    said = restart(w)
    assert said[0].startswith("resume xo") and labels(w) == ["mission", "plan:approved"]


def test_a_resume_that_fails_is_said_on_its_issue_and_ended(w, monkeypatch):
    j = cut_scout(w)
    monkeypatch.setattr(D.scout, "run_scout", lambda *a, **k: 1 / 0)
    restart(w)
    assert "the resumed stage failed: ZeroDivisionError" in stops(w, N)[-1]
    assert not J.Journal.load(j.run).unfinished


# ------------------------------------------------------- start, and prune
def test_run_and_once_search_before_their_first_cycle(monkeypatch, tmp_path):
    order = []

    class Fake:
        def __init__(self, **kw):
            pass

        def recover(self):
            order.append("recover")

        def cycle(self):
            order.append("cycle")

        def log(self, msg):
            order.append(msg)

    monkeypatch.setattr(D, "Fleet", Fake)
    monkeypatch.setattr(D, "lock", lambda state: open(tmp_path / "lock", "w"))
    monkeypatch.setattr(D, "load_token", lambda path: "sk-ant-oat01-x")
    assert D.main(["once"]) == 0
    assert order == ["recover", "cycle"]


def test_a_failed_search_is_logged_and_the_cycle_still_runs(monkeypatch, tmp_path):
    order = []

    class Fake:
        def __init__(self, **kw):
            pass

        def recover(self):
            raise RuntimeError("gh is down")

        def cycle(self):
            order.append("cycle")

        def log(self, msg):
            order.append(msg.splitlines()[0])

    monkeypatch.setattr(D, "Fleet", Fake)
    monkeypatch.setattr(D, "lock", lambda state: open(tmp_path / "lock", "w"))
    monkeypatch.setattr(D, "load_token", lambda path: "sk-ant-oat01-x")
    D.main(["once"])
    assert order == ["the search on start failed:", "cycle"]


def test_prune_keeps_an_unfinished_run_and_removes_finished_ones(w, monkeypatch):
    monkeypatch.setattr(D, "KEEP_RUNS", 2)
    old = cut_scout(w)
    for k in range(4):
        w.clock.t += dt.timedelta(minutes=1)
        run = w.fleet.new_run(f"done{k}", {"stage": "digest", "day": "2026-10-21"})
        J.Journal.load(run).end("written", w.clock())
    w.fleet.prune_runs(set())
    left = sorted(p.name for p in w.fleet.runs.iterdir())
    assert old.run.name in left and len(left) == 3


def test_the_journal_is_written_before_the_clone(w, monkeypatch):
    seen = []
    real = w.fleet.clone

    def clone(run, branch):
        seen.append(J.Journal.load(run))
        return real(run, branch)

    monkeypatch.setattr(w.fleet, "clone", clone)
    advance(w, *SCOUT)
    assert seen and seen[0] is not None and seen[0].record["stage"] == "scout"


def test_a_replayed_call_is_not_put_in_the_ledger_twice(w, tmp_path):
    w.kill.at(model, nth=2, cut=True)
    killed(w, SCOUT[0])
    restart(w, SCOUT[1])
    rows = [json.loads(ln) for ln in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert len(rows) == 2, rows


def test_every_marker_a_stage_writes_names_its_run(w):
    advance(w, *SCOUT)
    advance(w, V1)
    bodies = [b.split("\n", 1)[0] for b in w.host.comments(N)]
    run_named = [b for b in bodies if b.startswith(D.RANK_PREFIXES)]
    assert run_named and all(" run=" in b for b in run_named), run_named


def test_a_killed_stage_is_not_quiet(w):
    w.kill.at(model)
    killed(w)
    said = restart(w, *SCOUT)
    assert said and said[0].startswith("resume scout")
    assert any("resume scout" in ln for ln in w.lines)
    assert w.lines[-1].endswith("the search on start: 1 stage(s) acted on")


def test_a_start_with_nothing_to_resume_says_so(w):
    w.fleet.recover()
    assert w.lines[-1].endswith("the search on start: nothing to resume")
    log = (w.fleet.state_dir / "dispatcher.log").read_text()
    assert log.rstrip().endswith("the search on start: nothing to resume")
