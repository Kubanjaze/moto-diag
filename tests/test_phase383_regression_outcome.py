"""Phase 383, F206 — only a passing run is a regression of record.

`closeout_check.regression_line` read the count, the hash and the command,
never the failures, the errors or the exit code; `regression.sh` printed the
same prefix whatever the outcome, and `deploy.regression_problem` (K18)
shares the parser. So 382's failing run on the desktop ("5 failed … exit 1")
satisfied A5 and apply-live's precondition, verbatim.

The operator's 1C: the line must record 0 failed, 0 errors and exit 0, and
every skip is named below it by its test file and its reason, each pinned in
`EXPECTED_SKIPS`, held here by equality; adding to it is the operator's call.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

import pytest

from test_phase358_deploy_contract import (  # noqa: F401  (env is a fixture)
    _commit_diff, _dryrun, _git, _refusal, env,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "closeout"
sys.path.insert(0, str(SKILL))

import closeout_check as C  # noqa: E402

FIX = SKILL / "fixtures" / "k6_k7"
K18 = ROOT / ".claude" / "skills" / "deploy" / "fixtures" / "k18"
DONE = ROOT / "docs" / "phases" / "completed"
CMD = "python -m pytest -n auto --dist load"

BAD = ["a5_bad_failing_run.md", "a5_bad_exit_nonzero.md", "a5_bad_errors.md",
       "a5_bad_unnamed_skip.md", "a5_bad_unexpected_skip.md", "a5_bad_miscounted_skip.md",
       "a5_bad_skip_other_file.md", "a5_bad_failed_exit_zero.md"]

#: A pytest -rA tail as regression.sh's run writes it.
PASSING_LOG = (
    "PASSED tests/test_a.py::test_one\n"
    "SKIPPED [1] tests/test_phase244H_test_db_isolation.py:79: no production database "
    "on this machine\n"
    "================ 10870 passed, 1 skipped, 10 warnings in 1641.20s (0:27:21) ================\n")
FAILING_LOG = (
    "FAILED tests/test_b.py::test_two - assert 1 == 2\n"
    "================ 3 failed, 10867 passed in 1641.20s (0:27:21) ================\n")


def _logs() -> dict[str, str]:
    return {p.name.split("_")[0]: p.read_text(encoding="utf-8")
            for p in sorted(DONE.glob("*_phase_log.md"))}


class TestTheKnownBadLinesAreRefused:
    @pytest.mark.parametrize("name", BAD)
    def test_a5_refuses(self, name):
        line, why = C.regression_record((FIX / name).read_text())
        assert line is None and why

    def test_382s_failing_line_passed_the_old_rule(self):
        """The fixture is the defect: the pre-383 pattern matched it."""
        import re
        old = re.compile(r"Regression of record:\s*(\d[\d,]*) passed\b.*?\bat `([0-9a-f]{7,40})`"
                         r".*?`([^`]*\bpytest\b[^`]*)`")
        assert old.search((FIX / "a5_bad_failing_run.md").read_text())

    def test_the_reason_names_the_failure(self):
        _, why = C.regression_record((FIX / "a5_bad_failing_run.md").read_text())
        assert "5 failed" in why and "exit 1" in why

    def test_an_unexpected_skip_is_named(self):
        _, why = C.regression_record((FIX / "a5_bad_unexpected_skip.md").read_text())
        assert "test_phase209_packaging.py" in why

    def test_the_expected_skip_passes(self):
        assert C.regression_line((FIX / "a5_good_expected_skip.md").read_text()) == (
            "10870", "74e3599", CMD)

    def test_the_legacy_line_refuses_a_failure(self):
        assert C.legacy_regression_line("Regression 8,091 passed / 0 failed at `f279533`.")
        assert not C.legacy_regression_line("Regression 8,091 passed / 2 failed at `f279533`.")


class TestTheWriterAndTheReaderAgree:
    def test_a_passing_run_with_the_expected_skip_parses(self):
        text = C.format_regression(PASSING_LOG, "74e3599", 1641, CMD, 0)
        assert text.splitlines()[0].startswith(C.PREFIX)
        assert C.regression_line(text) == ("10870", "74e3599", CMD)

    def test_a_failing_run_is_not_printed_as_of_record(self):
        text = C.format_regression(FAILING_LOG, "74e3599", 1641, CMD, 1)
        assert text.startswith(C.FAILED_PREFIX) and C.PREFIX not in text
        assert C.regression_line(text) is None

    def test_a_nonzero_exit_alone_is_not_of_record(self):
        assert C.format_regression(PASSING_LOG, "74e3599", 1641, CMD, 2).startswith(
            C.FAILED_PREFIX)

    def test_regression_sh_calls_the_writer(self):
        text = (SKILL / "regression.sh").read_text(encoding="utf-8")
        assert '--format-regression "$STEM.log"' in text
        assert 'echo "Regression of record:' not in text

    def test_the_command_line_prints_it(self, tmp_path):
        log = tmp_path / "run.log"
        log.write_text(PASSING_LOG)
        r = subprocess.run([sys.executable, "-B", str(SKILL / "closeout_check.py"),
                            "--format-regression", str(log), "74e3599", "1641", CMD, "0"],
                           capture_output=True, text=True)
        assert r.returncode == 0
        assert C.regression_line(r.stdout) == ("10870", "74e3599", CMD)


class TestThePins:
    def test_expected_skips_is_exactly_this(self):
        """Adding to it is the operator's call: this literal changes with it."""
        assert C.EXPECTED_SKIPS == frozenset({
            ("tests/test_phase244H_test_db_isolation.py",
             "no production database on this machine"),
            # Phase 388, the operator: "Mac runs it (Recommended)".
            ("tests/test_phase388_fence_boundary.py",
             "macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py")})

    def test_each_expected_skip_is_still_in_its_file(self):
        for path, reason in C.EXPECTED_SKIPS:
            assert f'pytest.skip("{reason}")' in (ROOT / path).read_text(encoding="utf-8")

    def test_the_unnamed_skip_exemption_is_exactly_what_the_rule_refuses(self):
        """The control: the closed logs the new rule refuses when no phase is
        exempt are exactly the pin, and the pin lets each of them through."""
        logs = _logs()
        measured = {p for p, t in logs.items()
                    if p not in C.A5_COMMAND_EXEMPT and "Regression of record:" in t
                    and C.regression_line(t) is None}
        assert measured == C.A5_UNNAMED_SKIP_EXEMPT == {"382"}
        assert all(C.regression_line(logs[p], p) for p in measured)

    def test_every_closed_log_still_passes_a5(self):
        refused = [p for p, t in _logs().items()
                   if p not in C.A5_COMMAND_EXEMPT and "Regression of record:" in t
                   and C.regression_line(t, p) is None]
        assert refused == []


class TestK18RefusesAFailingRun:
    def test_apply_live_refuses_the_failing_line(self, env, capsys):
        assert _dryrun(env) == 0
        _commit_diff(env)
        log = env["repo"] / "docs" / "phases" / "in_progress" / "ZZZ_phase_log.md"
        shutil.copy(K18 / "failing_regression_line.md", log)
        _git(env["repo"], "commit", "-qam", "the known-bad log")
        err = _refusal(env, capsys)
        assert "has no regression of record that A5 can read" in err
        assert "5 failed" in err


def test_check_fires_a5_on_a_failing_line(tmp_path):
    """Wiring: check(), which the push guard and verify_phase call."""
    tree = tmp_path / "tree"
    shutil.copytree(SKILL / "fixtures" / "good", tree)
    log = tree / "docs" / "phases" / "completed" / "ZZZ_phase_log.md"
    assert not [f for f in C.check(tree, "ZZZ") if f.startswith("A5")]
    bad = next(ln for ln in (FIX / "a5_bad_failing_run.md").read_text().splitlines()
               if ln.startswith(C.PREFIX))
    log.write_text(log.read_text() + "\n" + bad + "\n")
    assert any(f.startswith("A5") and "5 failed" in f for f in C.check(tree, "ZZZ"))
