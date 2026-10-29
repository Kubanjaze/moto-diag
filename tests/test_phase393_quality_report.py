"""Phase 393 (K54) — the weekly page, "Code health, weekly".

`quality_report.py` measures the seven counts on a tree with no model and
writes one page: each number, last week's, an arrow, and on the first line
the counts that went the wrong way two weeks running. The dispatcher runs
it once a week, from Monday 08:00 local, in the fence on master, posts the
page as a comment on one pinned issue opened by the fleet's account (never
without it), and the next digest gains one line naming it.

The stage's world is 392's next-mission world (real git, `gh` stood in,
the fleet's account present).
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLEET_DIR = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(FLEET_DIR))
sys.path.insert(0, str(ROOT / "tests"))

import journal as J  # noqa: E402
import quality_report as QR  # noqa: E402
import yeoman  # noqa: E402
from test_phase388_dispatcher import NY  # noqa: E402
from test_phase389_dispatcher import world  # noqa: E402,F401
from test_phase390_resume import D, Killed  # noqa: E402
from test_phase392_next_mission import FLEET, Hub, next_world  # noqa: E402,F401

COUNTS = {"ruff": 1108, "mypy": 202, "complex": 25, "big": 5, "helpers": 19, "swallowed": 22,
          "coverage": 87.6, "coverage_commit": "abc1234", "commit": "def5678"}
MONDAY = dt.datetime(2026, 10, 26, 8, 5, tzinfo=NY)


# --------------------------------------------------------------- the page
class TestThePage:
    def test_each_number_last_weeks_and_an_arrow(self):
        last = {**COUNTS, "ruff": 1110, "mypy": 202, "coverage": 87.4}
        page = QR.page(COUNTS, [last], dt.date(2026, 10, 26))
        assert "| lint findings (ruff) | 1108 | 1110 | ↓ (better) |" in page
        assert "| type errors (mypy) | 202 | 202 | → |" in page
        assert "| line coverage, % (regression of record) | 87.6 | 87.4 | ↑ (better) |" in page
        assert "master at `def5678`" in page and "at `abc1234`" in page

    def test_the_first_line_names_two_weeks_running_the_wrong_way(self):
        before = {**COUNTS, "mypy": 200, "coverage": 88.0, "ruff": 1108}
        last = {**COUNTS, "mypy": 201, "coverage": 87.8, "ruff": 1109}
        now = {**COUNTS, "mypy": 202, "coverage": 87.6, "ruff": 1108}
        first = QR.page(now, [before, last], dt.date(2026, 10, 26)).splitlines()[0]
        assert first == ("Two weeks running the wrong way: type errors (mypy); "
                         "line coverage, % (regression of record).")

    def test_once_the_wrong_way_is_not_two_weeks(self):
        """The control: worse this week only is not on the first line."""
        last = {**COUNTS, "mypy": 201}
        first = QR.page({**COUNTS, "mypy": 202}, [COUNTS, last], dt.date(2026, 10, 26))
        assert first.splitlines()[0] == "Nothing went the wrong way two weeks running."

    def test_a_first_week_has_no_arrows(self):
        page = QR.page(COUNTS, [], dt.date(2026, 10, 26))
        assert "| lint findings (ruff) | 1108 | — | · |" in page


class TestMeasure:
    def test_coverage_comes_from_the_newest_regression_of_record_line(self, tmp_path):
        repo = tmp_path / "r"
        logs = repo / "docs" / "phases" / "completed"
        logs.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)

        def commit(msg: str) -> str:
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@l",
                            "commit", "-q", "--allow-empty", "-m", msg,
                            "--date", f"2026-10-{20 + len(msg)}T12:00:00"], check=True,
                           env={"GIT_COMMITTER_DATE": f"2026-10-{20 + len(msg)}T12:00:00",
                                "PATH": "/usr/bin:/bin"})
            return subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                                  capture_output=True, text=True).stdout.strip()

        old, new = commit("a"), commit("bb")
        (logs / "1_phase_log.md").write_text(f"Line coverage of record: 80.00% at `{new}` (x)\n")
        (logs / "2_phase_log.md").write_text(f"Line coverage of record: 90.00% at `{old}` (x)\n")
        assert QR.coverage_of_record(repo) == (80.0, new)

    def test_print_measures_here_and_posts_nothing(self, tmp_path):
        r = subprocess.run([sys.executable, str(FLEET_DIR / "quality_report.py"), "--print",
                            "--history", str(tmp_path / "none.jsonl")],
                           capture_output=True, text=True, cwd=ROOT, timeout=600)
        assert r.returncode == 0, r.stderr
        assert r.stdout.splitlines()[0].startswith(("Nothing went", "Two weeks running"))
        assert "**Code health, weekly, " in r.stdout and "| lint findings (ruff) |" in r.stdout

    def test_the_measure_line_parses(self):
        assert QR.parse_measure("noise\n" + json.dumps(COUNTS)) == COUNTS
        assert QR.parse_measure("Traceback") is None


# -------------------------------------------------------------- the stage
class PinHub(Hub):
    """392's stand-in, which can also open an issue with no label and pin one."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.pinned: list[int] = []

    def gh(self, cmd):
        if cmd[1:3] == ["issue", "create"] and "--label" not in cmd:
            n = max([*self.issues, 40]) + 1
            self.issue(n, cmd[cmd.index("--title") + 1], cmd[cmd.index("--body") + 1], {})
            self.issues[n]["author"] = FLEET
            return subprocess.CompletedProcess(cmd, 0,
                                               f"https://github.com/{D.REPO}/issues/{n}\n", "")
        if cmd[1:3] == ["issue", "pin"]:
            self.pinned.append(int(cmd[3]))
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return super().gh(cmd)


@pytest.fixture
def weekly(next_world):
    fleet, host, clock, origin, *_ = next_world
    host.__class__ = PinHub
    host.pinned = []
    origin.joinpath("docs/reports").mkdir(parents=True, exist_ok=True)
    measured = []

    def check(clone, commit, *, full, command=None):
        if command and command[-1] == "measure":
            measured.append(command)
            return D.Check(True, commit, out=json.dumps(COUNTS))
        return D.Check(True, commit, None, "")

    fleet.check = check
    fleet.digest_day = lambda: None                 # the digest's own tests are 388's and 391's
    fleet.cycle()                                   # the first cycle: quality_since
    return fleet, host, clock, measured


def pages(host) -> list[tuple[int, str]]:
    return [(n, b) for n, i in host.issues.items() if i["title"] == QR.TITLE
            for b in (c["body"] for c in i["comments"])]


class TestTheStage:
    def test_not_before_monday_8_and_not_for_a_week_before_it_came_up(self, weekly):
        fleet, host, clock, measured = weekly
        assert "quality_since" in fleet.load()
        clock.t = MONDAY - dt.timedelta(minutes=10)
        fleet.cycle()
        assert measured == [] and pages(host) == []

    def test_monday_8_measures_opens_pins_and_posts_once(self, weekly):
        fleet, host, clock, measured = weekly
        clock.t = MONDAY
        fleet.cycle()
        [(n, body)] = pages(host)
        assert host.pinned == [n] and host.issues[n]["author"] == FLEET
        assert body.startswith(f"{D.QUALITY_M} week=2026-10-26")
        assert "| lint findings (ruff) | 1108 |" in body
        [cmd] = measured
        assert cmd[:2] == [".venv/bin/python", ".claude/skills/fleet/quality_report.py"]
        clock.t += dt.timedelta(hours=3)
        fleet.cycle()
        assert len(pages(host)) == 1 and len(measured) == 1, "once a week"
        [rec] = QR.read_history(fleet.quality_path())
        assert rec["issue"] == n and rec["week"] == "2026-10-26" and rec["ruff"] == 1108

    def test_the_next_week_reuses_the_issue_and_compares(self, weekly):
        fleet, host, clock, measured = weekly
        clock.t = MONDAY
        fleet.cycle()
        clock.t = MONDAY + dt.timedelta(days=7)
        fleet.cycle()
        (n1, _), (n2, body) = pages(host)
        assert n1 == n2 and host.pinned == [n1]
        assert "| lint findings (ruff) | 1108 | 1108 | → |" in body

    def test_without_the_fleets_account_nothing_is_posted(self, weekly):
        fleet, host, clock, measured = weekly
        fleet.identity_file = fleet.identity_file.parent / "absent.env"
        clock.t = MONDAY
        fleet.cycle()
        assert pages(host) == [] and len(measured) == 1
        [rec] = QR.read_history(fleet.quality_path())
        assert rec["issue"] is None
        assert (fleet.state_dir / "quality" / "2026-10-26.md").is_file()

    def test_a_failed_measure_stops_and_waits_an_hour(self, weekly):
        fleet, host, clock, measured = weekly
        fleet.check = lambda clone, commit, *, full, command=None: D.Check(False, commit,
                                                                           why="exit 1")
        clock.t = MONDAY
        fleet.cycle()
        assert pages(host) == [] and "quality_failed" in fleet.load()
        clock.t += dt.timedelta(minutes=5)
        assert fleet.quality_week() is None
        clock.t += dt.timedelta(hours=1)
        assert fleet.quality_week() == MONDAY.date()

    def test_the_digest_gets_one_line(self, weekly):
        fleet, host, clock, measured = weekly
        clock.t = MONDAY
        fleet.cycle()
        [line] = fleet.quality_on(MONDAY.date())
        assert line.startswith("Posted on #") and "Nothing went the wrong way" in line
        facts = yeoman.facts(fleet.mirror, MONDAY.date(), subprocess.run, quality=[line])
        assert f"## Code health, weekly\n\n- {line}" in facts


def test_quality_cut_after_its_comment_resumes_with_no_second_page(weekly):
    """The kill point (`fixtures/resume/kill_points.json`): cut after the
    comment, before the record; the search on start resumes it."""
    fleet, host, clock, measured = weekly
    clock.t = MONDAY
    real = fleet.quality_path

    def killed():
        if pages(host):
            raise Killed
        return real()
    fleet.quality_path = killed
    with pytest.raises(Killed):
        fleet.cycle()
    (j,) = J.unfinished(fleet.runs)
    assert j.record["stage"] == "quality" and j.done("comment")
    fleet.quality_path = real
    fleet.recover()
    assert len(pages(host)) == 1 and not J.unfinished(fleet.runs)
    assert len(QR.read_history(fleet.quality_path())) == 1
