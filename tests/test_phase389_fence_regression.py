"""Phase 389 — a regression run inside the fleet's fence can be of record.

The operator, 2026-10-25: "Sandbox counts (Recommended)": the tests that
cannot run inside the fence skip there with a reason naming it, "and the
machine-shaped skips are accepted only for runs made in the sandbox. The Mac
keeps today's strict list." So `FENCE_EXPECTED_SKIPS` counts only on a line
that carries `FENCE_MARK`, which `regression.sh` prints only inside the
fence; `EXPECTED_SKIPS` is unchanged (383's equality test still holds it).
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "closeout"))

import closeout_check as C  # noqa: E402

CMD = "python -m pytest -n auto --dist load"
FENCED_LOG = (
    "PASSED tests/test_a.py::test_one\n"
    "SKIPPED [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine\n"
    "SKIPPED [12] tests/test_phase257_sandbox_boundary.py:72: sandbox-exec is macOS-only; the "
    "orchestrator runs only there\n"
    "SKIPPED [21] tests/test_phase209_packaging.py:60: inside the fleet's fence: no network to "
    "build a wheel\n"
    "========== 11300 passed, 34 skipped, 10 warnings in 600.00s (0:10:00) ==========\n")


def test_the_fence_pins_are_exactly_these():
    """Adding to them is the operator's call: this literal changes with them."""
    assert C.FENCE_EXPECTED_SKIPS == frozenset({
        ("tests/test_phase191b_ffmpeg.py", "real ffmpeg binary or fixture mp4 not available"),
        ("tests/test_phase204_gate10.py", "inside the fleet's fence: no ffmpeg on the home desktop"),
        ("tests/test_phase209_packaging.py", "inside the fleet's fence: no network to build a wheel"),
        ("tests/test_phase257_orchestrator_guards.py",
         "inside the fleet's fence: no Subconscious login there (K42)"),
        ("tests/test_phase257_orchestrator_guards.py",
         "inside the fleet's fence: osacompile is macOS-only"),
        ("tests/test_phase257_sandbox_boundary.py",
         "sandbox-exec is macOS-only; the orchestrator runs only there"),
        ("tests/test_phase257_source_checks.py", "needs the on-disk library"),
        ("tests/test_phase257_source_checks.py",
         "acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library"),
        ("tests/test_phase257_source_checks.py",
         "acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library"),
        ("tests/test_phase257_source_checks.py", "the KTM manual is not in this machine's library"),
        ("tests/test_phase257_manual_route_excerpts.py", "needs the on-disk library"),
        ("tests/test_phase388_fence_boundary.py",
         "inside the fleet's fence: its boundary is proven from the host, not from inside"),
    })


#: Where each pinned reason comes from in its file: the literal, or for the
#: two that name a path, the template that makes it.
SOURCE = {
    "acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library":
        "is not in this machine's library",
    "acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library":
        "is not in this machine's library",
}


@pytest.mark.parametrize("path,reason", sorted(C.FENCE_EXPECTED_SKIPS))
def test_each_pinned_reason_is_still_in_its_file(path, reason):
    assert SOURCE.get(reason, reason) in (ROOT / path).read_text(encoding="utf-8")


def test_the_mac_list_is_untouched_and_disjoint_in_meaning():
    assert not C.FENCE_EXPECTED_SKIPS & C.EXPECTED_SKIPS


def test_a_fenced_line_with_fence_skips_is_of_record():
    text = C.format_regression(FENCED_LOG, "abc1234", 600, CMD, 0, fence=True)
    assert text.splitlines()[0].endswith(C.FENCE_MARK)
    assert C.regression_line(text) == ("11300", "abc1234", CMD)


def test_the_same_run_without_the_mark_is_refused():
    """A Mac run, or a line copied without the mark, gets no fence pins."""
    text = C.format_regression(FENCED_LOG, "abc1234", 600, CMD, 0, fence=False)
    line, why = C.regression_record(text)
    assert line is None and "test_phase257_sandbox_boundary.py" in why
    assert "test_phase209_packaging.py" in why


def test_the_mark_does_not_accept_a_skip_no_one_pinned():
    log = FENCED_LOG.replace("inside the fleet's fence: no network to build a wheel",
                             "wheel build unavailable: pip said no")
    line, why = C.regression_record(C.format_regression(log, "abc1234", 600, CMD, 0, fence=True))
    assert line is None and "pip said no" in why


def test_the_mark_does_not_rescue_a_failure():
    log = FENCED_LOG.replace("11300 passed", "1 failed, 11299 passed")
    assert C.regression_line(C.format_regression(log, "abc1234", 600, CMD, 1, fence=True)) is None


def test_any_other_root_is_not_the_fence(tmp_path):
    """The control for the skips: they fire only at /fleet/moto-diag, which
    this test may itself be running in (the fleet's own regression)."""
    assert not C.in_fleet_fence(tmp_path)
    assert C.in_fleet_fence(ROOT) == (ROOT.resolve() == C.FENCE_ROOT
                                      and pathlib.Path("/fleet/run").is_dir())


def test_the_command_line_marks_exactly_when_inside_the_fence(tmp_path):
    import subprocess
    log = tmp_path / "run.log"
    log.write_text(FENCED_LOG)
    r = subprocess.run([sys.executable, "-B", str(ROOT / ".claude/skills/closeout/closeout_check.py"),
                        "--format-regression", str(log), "abc1234", "600", CMD, "0"],
                       capture_output=True, text=True)
    assert r.returncode == 0 and (C.FENCE_MARK in r.stdout) == C.in_fleet_fence()
