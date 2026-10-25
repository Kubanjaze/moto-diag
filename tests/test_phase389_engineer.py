"""Phase 389 — the Chief Engineer: the brief, the watchers, the checks.

What must hold (the 389 prompt): the Engineer stops and the stage sets
needs-admiral at a third bug fix, at a rule-1 condition, and when a guard
blocks twice for the same reason; the watchers that hold the first and the
last run outside the model; a `pr-ready` is believed only when the clone is
committed and clean, the close-out check (A1–A8) is empty, and a run no
model touched counts what the Engineer's line counts.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(SKILL))

import dispatcher as D  # noqa: E402
import engineer as E  # noqa: E402
import rank_call  # noqa: E402

CLOSED = ROOT / ".claude" / "skills" / "closeout" / "fixtures" / "good"
LINE = ("Regression of record: 1234 passed, 0 failed, 0 skipped, 0 errors at `ccccccc` "
        "(12 min 0 s wall, `python -m pytest -n auto --dist load`, exit 0)")
HOOK_BLOCK = ("PreToolUse:Bash hook error: [${CLAUDE_PROJECT_DIR}/.claude/skills/closeout/"
              "edit_guard.sh]: edit guard: blocked — `sed -i` edits a file in place, and is "
              "blocked wherever it points. Use the Edit or Write tool.")


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def closed(tmp_path):
    """The closeout skill's complete phase ZZZ, in git, its bug-fix commits real."""
    c = tmp_path / "closed"
    shutil.copytree(CLOSED, c)
    git("init", "-q", cwd=c)
    git("add", "-A", cwd=c)
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "x", cwd=c)
    head = git("rev-parse", "--short", "HEAD", cwd=c).stdout.strip()
    log = c / "docs" / "phases" / "completed" / "ZZZ_phase_log.md"
    log.write_text(log.read_text().replace("8fd680f", head).replace("f11505b", head))
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "real hashes", cwd=c)
    return c


def transcript(run_dir: pathlib.Path, *results: tuple[str, bool]) -> None:
    d = run_dir / "claude" / "projects" / "-fleet-moto-diag"
    d.mkdir(parents=True, exist_ok=True)
    with (d / "s.jsonl").open("a") as f:
        for text, err in results:
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t", "is_error": err,
                 "content": text}]}}) + "\n")


class TestTheBrief:
    def test_the_command(self):
        cmd = E.session_argv("389A", 31)
        assert cmd[:2] == ["claude", "-p"] and rank_call.OPUS in cmd
        assert cmd[cmd.index("--permission-mode") + 1] == "bypassPermissions"
        assert "WebFetch" in cmd[cmd.index("--disallowedTools") + 1]
        assert cmd[cmd.index("--output-format") + 1] == "json"

    def test_it_names_the_plan_the_stops_and_the_traps(self):
        brief = E.session_argv("389A", 31)[2]
        for words in ("389A_implementation.md", "issue #31", "wholetree.sh", "regression.sh",
                      "a third bug fix", "rule-1", "twice for the same reason", "F124", "244H",
                      "never pip install", "closeout_check.py . 389A", "engineer.json",
                      "Never change CLAUDE.md"):
            assert words in brief, words

    def test_a_fix_round_carries_the_findings(self):
        brief = E.session_argv("389A", 31, findings="- [factual] the row: F213", rnd=1)[2]
        assert "fix round 1" in brief and "- [factual] the row: F213" in brief and "K9" in brief


class TestTheWatchers:
    def test_two_bug_fixes_go_on_a_third_stops(self, tmp_path):
        log = tmp_path / "docs" / "phases" / "in_progress" / "389A_phase_log.md"
        log.parent.mkdir(parents=True)
        log.write_text("### Bug fix #1 — 2026-10-25 — a\n\n### Bug fix #2 — 2026-10-25 — b\n")
        assert E.watch(tmp_path, tmp_path / "run", "389A") is None
        log.write_text(log.read_text() + "\n### Bug fix #3 — 2026-10-25 — c\n")
        assert E.watch(tmp_path, tmp_path / "run", "389A").startswith("third-bug-fix")

    def test_the_log_in_completed_counts_too(self, tmp_path):
        log = tmp_path / "docs" / "phases" / "completed" / "389A_phase_log.md"
        log.parent.mkdir(parents=True)
        log.write_text("### Bug fix #3 — 2026-10-25 — c\n")
        assert E.bug_fixes(tmp_path, "389A") == 3

    def test_one_guard_block_goes_on_the_same_one_twice_stops(self, tmp_path):
        run = tmp_path / "run"
        transcript(run, (HOOK_BLOCK, True), ("ok", False))
        assert E.watch(tmp_path, run, "389A") is None
        transcript(run, (HOOK_BLOCK.replace("Use the Edit or Write tool.", "Try again."), True))
        assert E.watch(tmp_path, run, "389A").startswith("guard-blocked-twice")

    def test_two_different_blocks_are_not_the_same_reason(self, tmp_path):
        run = tmp_path / "run"
        other = HOOK_BLOCK.replace("`sed -i` edits a file in place", "a redirect to a variable")
        transcript(run, (HOOK_BLOCK, True), (other, True))
        assert E.watch(tmp_path, run, "389A") is None

    def test_an_ordinary_tool_error_is_not_a_guard_block(self, tmp_path):
        run = tmp_path / "run"
        transcript(run, ("Exit code 1\nfile not found", True), ("Exit code 1\nfile not found", True))
        assert E.guard_blocks(run) == {}


class TestTheResult:
    def write(self, tmp_path, obj):
        (tmp_path / E.RESULT).write_text(json.dumps(obj) if isinstance(obj, dict) else obj)
        return tmp_path

    def test_pr_ready(self, tmp_path):
        r = E.read_result(self.write(tmp_path, {"outcome": "pr-ready", "summary": "It ships.",
                                                "regression_line": LINE}))
        assert r["outcome"] == "pr-ready"

    def test_the_measured_dry_run_result(self, tmp_path):
        """What a real fenced session wrote, read as a stop (fixtures/dry_runs)."""
        shutil.copy(SKILL / "fixtures" / "dry_runs" / "engineer_result.json", tmp_path / E.RESULT)
        assert E.read_result(tmp_path)["kind"] == "fork"

    def test_a_stop(self, tmp_path):
        r = E.read_result(self.write(tmp_path, {"outcome": "stop", "kind": "fork",
                                                "question": "Which of two plans?"}))
        assert r["kind"] == "fork"

    @pytest.mark.parametrize("obj,why", [
        (None, "without writing"),
        ("not json", "not JSON"),
        ({"outcome": "done"}, "no outcome"),
        ({"outcome": "stop", "kind": "bored", "question": "?"}, "no known kind"),
        ({"outcome": "stop", "kind": "fork", "question": " "}, "no question"),
        ({"outcome": "pr-ready", "summary": "", "regression_line": LINE}, "no summary"),
        ({"outcome": "pr-ready", "summary": "x", "regression_line": "Regression run FAILED"},
         "no regression of record"),
    ])
    def test_known_bad_results_stop(self, tmp_path, obj, why):
        if obj is not None:
            self.write(tmp_path, obj)
        with pytest.raises(rank_call.Stop, match=why):
            E.read_result(tmp_path)


class TestVerify:
    RESULT = {"outcome": "pr-ready", "summary": "x", "regression_line": LINE}

    def test_a_complete_phase_with_matching_counts(self, closed):
        assert E.verify(closed, "ZZZ", self.RESULT, LINE) == []

    def test_counts_that_differ(self, closed):
        theirs = LINE.replace("1234 passed", "1233 passed").replace("0 failed", "1 failed")
        fails = E.verify(closed, "ZZZ", self.RESULT, theirs)
        assert len(fails) == 1 and "(1234, 0, 0)" in fails[0] and "(1233, 1, 0)" in fails[0]

    def test_no_model_free_line(self, closed):
        assert "produced no regression of record" in E.verify(closed, "ZZZ", self.RESULT, None)[0]

    def test_an_unclean_clone(self, closed):
        (closed / "stray.txt").write_text("x")
        assert any("uncommitted" in f for f in E.verify(closed, "ZZZ", self.RESULT, LINE))

    def test_an_incomplete_close_out(self, closed):
        git("rm", "-q", "docs/phases/completed/ZZZ_implementation.md", cwd=closed)
        git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "gone", cwd=closed)
        assert any(f.startswith("close-out: A1") for f in E.verify(closed, "ZZZ", self.RESULT, LINE))


class FakeProc:
    """A Popen stand-in: lives `ticks` polls, writing `out` to its stdout file."""

    def __init__(self, cmd, stdout, stderr, out="", ticks=3, rc=0, **kw):
        self.cmd, self.kw, self.ticks, self.rc, self.terminated = cmd, kw, ticks, rc, False
        stdout.write(out)
        stdout.flush()

    def poll(self):
        if self.terminated:
            return -15
        self.ticks -= 1
        return None if self.ticks > 0 else self.rc

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return -15

    def kill(self):
        self.terminated = True

    @property
    def returncode(self):
        return -15 if self.terminated else self.rc


class TestTheSession:
    def runner(self, tmp_path, popen, usage="Current week (all models): 8% used · resets Oct 28, "
               "12pm (America/New_York)\n"):
        host = lambda cmd, **kw: subprocess.CompletedProcess(  # noqa: E731
            cmd, 0, json.dumps({"result": usage}), "")
        fleet = D.Fleet(state=tmp_path / "state", token="sk-ant-oat01-test-token", host=host,
                        fence=tmp_path / "fence.sh", workspace_docs=tmp_path, popen=popen,
                        sleep=lambda s: None, venv=tmp_path / "no-venv", mobile=tmp_path / "no-mobile")
        (tmp_path / "run").mkdir(exist_ok=True)
        return D.FencedRunner(fleet, tmp_path, tmp_path / "run")

    def test_it_ends_by_itself(self, tmp_path):
        made = []

        def popen(cmd, **kw):
            made.append((cmd, kw))
            return FakeProc(cmd, out='{"is_error": false}', **kw)

        r, reason = self.runner(tmp_path, popen).session(E.session_argv("389A", 1), watch=lambda: None)
        assert reason is None and r.returncode == 0 and r.stdout == '{"is_error": false}'
        cmd, kw = made[0]
        assert "--token-fd" in cmd and kw["pass_fds"] == (3,) and kw["env"].keys() == {"PATH"}

    def test_a_watcher_reason_ends_it(self, tmp_path):
        procs = []

        def popen(cmd, **kw):
            procs.append(FakeProc(cmd, ticks=100, **kw))
            return procs[0]

        r, reason = self.runner(tmp_path, popen).session(
            E.session_argv("389A", 1), watch=lambda: "third-bug-fix: #3")
        assert reason == "third-bug-fix: #3" and procs[0].terminated

    def test_a_new_session_over_the_opus_ceiling_never_starts(self, tmp_path):
        made = []
        runner = self.runner(tmp_path, lambda *a, **k: made.append(1),
                             usage="Current week (all models): 71% used · resets Oct 28, 12pm "
                                   "(America/New_York)\n")
        with pytest.raises(rank_call.Stop, match="no new Opus stage"):
            runner.session(E.session_argv("389A", 1), watch=lambda: None)
        assert made == []

    def test_a_usage_limit_is_a_pause_not_a_stop(self, tmp_path):
        limited = (ROOT / ".claude" / "skills" / "fleet" / "fixtures" / "dispatcher"
                   / "rate_limited.json").read_text()
        with pytest.raises(D.RateLimited):
            self.runner(tmp_path, lambda cmd, **kw: FakeProc(cmd, out=limited, rc=1, **kw)).session(
                E.session_argv("389A", 1), watch=lambda: None)
