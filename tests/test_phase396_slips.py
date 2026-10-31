"""Phase 396 — the fleet's four slips from 348 and 385 (K61).

Each slip's real artefact is kept in `.claude/skills/fleet/fixtures/slips396/`
and is seen refused or reproduced here:

(a) the Quartermaster's fenced code check gave no result (385's kept output);
(b) "No refute pass ran" beside the Red Team's own record (303, 348, 385);
(c) the next mission read from a mirror gone stale during a stage (#44);
(d) the Red Team handed the Captain's first draft as the approved plan (348).
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / ".claude" / "skills" / "fleet" / "fixtures" / "slips396"
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "closeout"))
sys.path.insert(0, str(ROOT / "tests"))
import closeout_check  # noqa: E402
import dispatcher as D  # noqa: E402
import engineer  # noqa: E402
import quartermaster as Q  # noqa: E402
import red_team  # noqa: E402
from test_phase389_dispatcher import world  # noqa: E402,F401
from test_phase390_resume import advance, w  # noqa: E402,F401
from test_phase391_dispatcher import REFUSE, qm_comments, to_merge_review  # noqa: E402
from test_phase389_fleet_git import git  # noqa: E402
from test_phase392_next_mission import TITLE, merge_row, next_world, step, the_issue  # noqa: E402,F401


# ------------------------------------------------------------------ (a)
def _repo(tmp_path: pathlib.Path) -> tuple[pathlib.Path, str]:
    """A repository whose base has a `scripts/code_quality.py` standing in
    for the real one: it prints the `pr` JSON and the arguments it was given."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "code_quality.py").write_text(
        "import json, sys\nprint('measuring')\n"
        "print(json.dumps({'Q10': [], 'Q12': [], 'argv': sys.argv[1:]}))\n")
    git("init", "-q", "-b", "master", cwd=repo)
    git("add", "-A", cwd=repo)
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "base", cwd=repo)
    head = git("rev-parse", "HEAD", cwd=repo).stdout.strip()
    return repo, head


def _fence(tmp_path: pathlib.Path) -> pathlib.Path:
    """fence.sh's interface with no sandbox: the run folder stands for
    /fleet/run and the clone's .venv for the fleet's venv, as the real fence
    binds them. The command it is handed runs exactly as given."""
    f = tmp_path / "fence.sh"
    f.write_text("#!/bin/bash\n"
                 "while [ \"$1\" != --run ]; do shift; done; RUN=$2\n"
                 "while [ \"$1\" != -- ]; do shift; done; shift\n"
                 "mkdir -p .venv/bin && ln -sf " + sys.executable + " .venv/bin/python\n"
                 "[ \"$1\" = /bin/bash ] && [ \"$2\" = -c ] || exit 99\n"
                 "exec /bin/bash -c \"${3//\\/fleet\\/run/$RUN}\"\n")
    f.chmod(0o755)
    return f


@pytest.fixture
def fleet(tmp_path):
    return D.Fleet(state=tmp_path / "state", token="", out=lambda s: None,
                   identity_file=tmp_path / "none.env", venv=tmp_path / "nv",
                   mobile=tmp_path / "nm")


class TestA:
    def test_the_code_command_runs_through_the_real_check_run(self, fleet, tmp_path):
        """Not stubbed (393's stage tests stub `check` for this command, so
        the join that broke it was never run)."""
        repo, head = _repo(tmp_path)
        fleet.fence = _fence(tmp_path)
        c = fleet.check_run(repo, head, full=False, command=Q.code_command(head))
        got = Q.code_result(c.out)
        assert got is not None, c.out
        assert got["argv"] == ["pr", "--base", head, "--root", "."]
        assert c.ok

    def test_the_real_fence_gave_a_result_on_348_and_385(self):
        """`396_real_fence.py`'s kept output, in the desktop's fence."""
        got = {p: Q.code_result((FIX / f"a_real_fence_{p}.txt").read_text()) for p in ("348", "385")}
        assert got["385"] == {"Q10": [], "Q12": []}
        assert got["348"]["Q10"] == []
        assert [e["file"] for e in got["348"]["Q12"]] == ["src/motodiag/core/migrations.py"]  # F238

    def test_385s_kept_output_is_the_join_breaking_the_script(self):
        """The real run, `runs/20261031_115942_check`: what bash was given."""
        kept = (FIX / "a_385_fenced_code_check.txt").read_text()
        assert "syntax error near unexpected token `then'" in kept
        assert "`/bin/sh -c if git cat-file" in kept       # the script, unquoted
        assert Q.code_result(kept) is None

    def test_no_result_says_why_and_not_the_commands_tail(self):
        kept = (FIX / "a_385_fenced_code_check.txt").read_text()
        why = Q.no_result_why(kept, ok=False)
        assert "syntax error near unexpected token" in why and "failed" in why
        q10, _, q12 = Q.code_checks(None, {"ok": True, "percent": None}, why)
        assert "syntax error" in q10.why and "syntax error" in q12.why
        # 348's and 385's verdicts said only a tail of the command:
        for line in (FIX / "a_348_verdict_lines.txt").read_text().splitlines():
            assert "gave no result: ity.py 2>/dev/null; then" in line

    @pytest.mark.parametrize("out,ok,want", [
        ("", False, "printed nothing"),
        ("", True, "exited 0"),
        ("collecting\nTraceback (most recent call last):\n  x\nKeyError: 'Q10'\n", False,
         "Traceback"),
        ("one\ntwo\nlast words\n", False, "last words"),
    ])
    def test_every_no_result_names_a_reason(self, out, ok, want):
        assert want in Q.no_result_why(out, ok=ok)

    def test_a_time_limit_is_said(self):
        """Over any error in the partial output, which the limit cut short."""
        why = Q.no_result_why("E   AssertionError: half-way\n", ok=False,
                              why="the run with no model passed its time limit of 3600 s")
        assert "time limit" in why and "AssertionError" not in why

    def test_the_stages_comment_names_the_error_on_385s_output(self, w):
        """The dispatcher's Quartermaster stage, given 385's real run as
        `check_run` returns it (ok False, `why` the output's tail)."""
        kept = (FIX / "a_385_fenced_code_check.txt").read_text()
        to_merge_review(w)
        real = w.fleet.check

        def check(clone, commit, *, full, command=None):
            if command and "code_quality.py pr" in command[-1]:
                return D.Check(False, commit, why=kept[-2000:], out=kept)
            return real(clone, commit, full=full, command=command)
        w.fleet.check = check
        advance(w, REFUSE)
        [text] = qm_comments(w)
        q10 = next(ln for ln in text.splitlines() if ln.startswith("- Q10"))
        assert "it failed, and printed no Q10/Q12 line" in q10
        assert "syntax error near unexpected token" in q10 and "ity.py 2>/dev/null" not in q10

    def test_the_findings_never_say_a_bare_no_result(self):
        for why in ("", "  "):
            q10, _, q12 = Q.code_checks(None, {"ok": True, "percent": None}, why)
            assert not q10.why.rstrip().endswith("no result:") and "no reason" in q10.why


# ------------------------------------------------------------------ (b)
FALSE = json.loads((FIX / "b_false_lines.json").read_text())["lines"]
TABLE = ("## Refuter pass\n\n| claim | verdict | quote | source | round · kind · outcome |\n"
         "|---|---|---|---|---|\n"
         "| The pin holds three entries | kept | \"three entries\" | docs/x.md p. 1 | "
         "1 · none · kept |\n")


def _closed(tmp_path: pathlib.Path, phase: str, *, log: str = "", impl: str = "",
            handoff: str = "", table: bool = True, rounds: bool = False) -> pathlib.Path:
    repo = tmp_path / f"r{phase}"
    done = repo / "docs" / "phases" / "completed"
    done.mkdir(parents=True)
    (repo / "docs" / "handoffs").mkdir(parents=True)
    body = f"# {phase} log\n\n**Status:** Complete\n\n## 2026-10-30 — close-out\n\n{log}\n"
    if rounds:
        body += "\n## 2026-10-30: The Red Team's round 1 (documents only)\n\nFixed.\n"
    (done / f"{phase}_phase_log.md").write_text(body + ("\n" + TABLE if table else ""))
    (done / f"{phase}_implementation.md").write_text(f"# {phase}\n\n## Deviations\n\n{impl}\n")
    (repo / "docs" / "handoffs" / f"2026-10-30_{phase}_closed.md").write_text(
        f"# {phase} closed\n\n{handoff}\n")
    return repo


class TestB:
    @pytest.mark.parametrize("row", FALSE, ids=[f"{r['phase']}-{pathlib.Path(r['file']).name}"
                                                for r in FALSE])
    def test_each_real_false_line_is_refused(self, tmp_path, row):
        kind = ("log" if row["file"].endswith("_phase_log.md") else
                "impl" if row["file"].endswith("_implementation.md") else "handoff")
        # 303's log had no checklist yet, only the Red Team's dated rounds.
        repo = _closed(tmp_path, row["phase"], **{kind: row["text"]},
                       table=row["phase"] != "303", rounds=row["phase"] in ("303", "348"))
        fails = closeout_check.refute_contradictions(repo, row["phase"])
        assert len(fails) == 1 and pathlib.Path(row["file"]).name in fails[0], fails

    def test_it_is_an_a8_failure_of_the_close_out(self, tmp_path):
        repo = _closed(tmp_path, "385", impl=FALSE[-1]["text"])
        assert any(f.startswith("A8 ") and "no refute pass" in f
                   for f in closeout_check.check(repo, "385"))

    def test_a_line_wrapped_across_two_lines_is_found(self, tmp_path):
        repo = _closed(tmp_path, "385", handoff="the regression stands. No refute\npass ran.")
        assert closeout_check.refute_contradictions(repo, "385")

    def test_the_tables_own_quote_of_the_line_is_not_a_contradiction(self, tmp_path):
        """The control: 385's checklist quotes the claim it judged."""
        repo = _closed(tmp_path, "385")
        log = repo / "docs" / "phases" / "completed" / "385_phase_log.md"
        log.write_text(log.read_text() + "| No refute pass ran | killed | \"No refute pass ran.\" "
                                          "| docs/x.md p. 2 | 1 · factual · fixed |\n")
        assert closeout_check.refute_contradictions(repo, "385") == []

    def test_with_no_red_team_record_the_line_still_passes_a8(self, tmp_path):
        """The control: a builder's phase with no refute says so, as A8 asks."""
        repo = _closed(tmp_path, "395", log="No refute pass ran.", table=False)
        assert closeout_check.refute_contradictions(repo, "395") == []
        assert closeout_check.refute_record((repo / "docs/phases/completed/395_phase_log.md")
                                            .read_text(), "395") == []

    def test_masters_closed_phases_have_no_contradiction(self):
        done = ROOT / "docs" / "phases" / "completed"
        phases = sorted(p.name[:-len("_phase_log.md")] for p in done.glob("*_phase_log.md"))
        assert len(phases) > 300
        assert {p: f for p in phases if (f := closeout_check.refute_contradictions(ROOT, p))} == {}

    def test_the_engineers_brief_says_not_to_write_it(self):
        brief = " ".join(engineer.BRIEF.split())
        assert "goes to the Red Team after your close-out" in brief
        assert "Write no sentence saying a refute pass did or did not run" in brief
        assert "## Refuter pass" in brief


# ------------------------------------------------------------------ (c)
def test_c_the_log_of_2026_10_31_is_the_slip():
    log = (FIX / "c_dispatcher_2026-10-31.log").read_text().splitlines()
    qm = next(i for i, ln in enumerate(log) if "the Quartermaster on phase 385" in ln)
    opened = next(i for i, ln in enumerate(log) if "next: opened issue 44: Phase 385" in ln)
    assert qm < opened and log[opened + 1].endswith("next: the row is on master")


def test_c_a_merge_during_a_stage_opens_no_issue_in_the_same_cycle(next_world):
    """2026-10-31: 385 merged at 11:37, during the Quartermaster's stage
    (11:07 to 12:00); its merge closed #41; at 12:00 the same cycle opened #44."""
    fleet, host, clock, origin, *_ = next_world
    step(clock, fleet, host)                            # the issue and the row's PR
    n, _ = the_issue(host)
    merge_row(origin)                                   # 901 is 🚧 on master

    def the_quartermaster():
        road = origin / "docs" / "ROADMAP.md"
        road.write_text(road.read_text().replace("| 901 | The shop's first screen | 🚧 |",
                                                 "| 901 | The shop's first screen | ✅ |"))
        git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "merged", cwd=origin)
        del host.issues[n]                              # the merge closes the issue
        return "verdict: refuse"
    fleet.next_stage = lambda *a, **k: ("quartermaster", the_quartermaster)
    step(clock, fleet, host)
    assert [i for i in host.issues.values() if i["title"] == TITLE] == []


# ------------------------------------------------------------------ (d)
HIST = json.loads((FIX / "d_348_plan_history.json").read_text())
PLAN = "docs/phases/in_progress/348_implementation.md"


@pytest.fixture
def plan_repo(tmp_path):
    """348's plan history, commit by commit, at its committer dates."""
    repo = tmp_path / "p348"
    (repo / "docs" / "phases" / "in_progress").mkdir(parents=True)
    git("init", "-q", "-b", "phase-348", cwd=repo)
    made = {}
    for c in HIST["plan_commits"]:
        (repo / PLAN).write_text(f"# 348\n\n{c['subject']}\n")
        git("add", "-A", cwd=repo)
        env = {**os.environ, "GIT_COMMITTER_DATE": c["at"], "GIT_AUTHOR_DATE": c["at"]}
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm",
                        c["subject"]], cwd=repo, env=env, check=True)
        made[c["commit"]] = git("rev-parse", "HEAD", cwd=repo).stdout.strip()
    return repo, made


class TestD:
    def test_the_last_approval_is_1251(self):
        events = [{"label": "plan:approved", "at": e["at"]} for e in HIST["plan_approved"]
                  if e["event"] == "labeled"]
        assert D.Fleet.last_applied(events, "plan:approved") == "2026-10-30T12:51:15Z"

    def test_the_plan_of_record_is_the_one_approved(self, plan_repo):
        repo, made = plan_repo
        got = red_team.plan_commit(repo, "348", approved_at="2026-10-30T12:51:15Z")
        assert got == made[HIST["of_record"]] != made[HIST["given"]]

    def test_an_earlier_approval_picks_the_plan_as_it_was_then(self, plan_repo):
        """#36's first `plan:approved` (02:30Z, 22:30 EDT) came before the
        operator's commits: the plan then was the Captain's draft; the XO's
        later round-2 revision was the plan at 23:31 EDT."""
        repo, made = plan_repo
        assert red_team.plan_commit(repo, "348", approved_at="2026-10-30T02:30:40Z") == \
            made["f1a4146"]
        assert red_team.plan_commit(repo, "348", approved_at="2026-10-30T03:31:13Z") == \
            made["cb033f9"]

    def test_without_an_approval_the_brief_says_which_commit_it_is(self, plan_repo):
        repo, made = plan_repo
        assert red_team.plan_commit(repo, "348") == made[HIST["given"]]
        text = red_team.gather(repo, "348", "F9 lint: clean", base="HEAD")
        assert "plan:approved was never applied on the issue" in text
        assert "=== v1.0 as approved" not in text

    def test_the_red_teams_brief_names_the_approved_commit(self, plan_repo):
        repo, made = plan_repo
        text = red_team.gather(repo, "348", "F9 lint: clean", base="HEAD",
                               approved_at="2026-10-30T12:51:15Z")
        assert f"=== v1.0 as approved ({made[HIST['of_record']][:12]}" in text
        assert "four sentences brought into line" in text

    def test_the_quartermasters_diff_starts_from_the_approved_commit(self, plan_repo):
        repo, made = plan_repo
        text = Q.gather(repo, "348", [], {"verify": [], "cited": [], "captain": "",
                                          "red_team": ""}, "", "",
                        approved_at="2026-10-30T12:51:15Z")
        assert f"=== the diff of v1.0 ({made[HIST['of_record']][:12]}, the plan when " in text

    def test_the_dispatcher_passes_the_label_time_to_both(self):
        src = (ROOT / ".claude" / "skills" / "fleet" / "dispatcher.py").read_text()
        assert src.count('approved_at=self.plan_approved_at(') == 2
