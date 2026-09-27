"""Phase 358, K6 and K7 — two close-out checks that were prose.

* **K6 (A5):** the regression line must parse to count + hash + command, as
  `regression.sh` prints it. Before 358, A5 took any line saying
  "regression" with a hash and a count.
* **K7 (A8):** "a log mentioning refute without a refute checklist fails"
  (the operator, 2026-09-27). The honest line "No refute pass ran" passes.

Each exemption is a pinned list of phase ids, not a date cutoff (the
operator), and each has a control that recomputes it from the 312 closed
logs and requires equality: the list may neither grow to hide a new close
nor shrink without anyone noticing.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "closeout"
sys.path.insert(0, str(SKILL))

import closeout_check as C  # noqa: E402

FIX = SKILL / "fixtures" / "k6_k7"
DONE = ROOT / "docs" / "phases" / "completed"


def _logs() -> dict[str, str]:
    return {p.name.split("_")[0]: p.read_text(encoding="utf-8")
            for p in sorted(DONE.glob("*_phase_log.md"))}


class TestK6TheRegressionLineParses:
    def test_the_line_regression_sh_prints_parses(self):
        assert C.regression_line((FIX / "a5_good.md").read_text()) == (
            "9507", "5750985", "python -m pytest -n auto --dist load")

    @pytest.mark.parametrize("name", ["a5_bad_no_command.md", "a5_bad_command_is_not_pytest.md"])
    def test_the_known_bad_lines_do_not(self, name):
        text = (FIX / name).read_text()
        assert C.legacy_regression_line(text), "the fixture must pass the OLD A5"
        assert C.regression_line(text) is None

    def test_every_phase_since_355_parses(self):
        """The five closes that print regression.sh's line."""
        logs = _logs()
        for phase in ("355", "261", "264", "262", "272"):
            assert C.regression_line(logs[phase]), phase

    def test_the_exemption_is_exactly_what_the_old_rule_let_through(self):
        """The control: closed logs that pass the old A5 and fail the new one."""
        measured = {p for p, t in _logs().items()
                    if C.legacy_regression_line(t) and not C.regression_line(t)}
        assert measured == C.A5_COMMAND_EXEMPT
        assert len(C.A5_COMMAND_EXEMPT) == 10

    def test_an_exempt_phase_still_needs_the_old_line(self):
        """Exempt from the command, not from A5."""
        text = "# log\n\nno regression recorded\n"
        assert not C.legacy_regression_line(text)


class TestK7ARefuteNeedsItsChecklist:
    @pytest.mark.parametrize("name", ["a8_bad_prose_refute.md", "a8_bad_block.md"])
    def test_the_known_bad_logs_fail(self, name):
        assert C.refute_record((FIX / name).read_text())

    def test_a_block_with_a_defective_row_is_named(self):
        fails = C.refute_record((FIX / "a8_bad_block.md").read_text())
        assert any("C4" in f for f in fails), fails

    @pytest.mark.parametrize("name", [
        "a8_good_no_refute_line.md", "a8_good_block.md", "a8_good_no_mention.md"])
    def test_the_known_good_logs_pass(self, name):
        assert C.refute_record((FIX / name).read_text()) == []

    def test_the_honest_line_must_say_it_whole(self):
        """The trap the prompt named: a guard that fails on the honest
        sentence. The escape is one line, not any sentence with "no" in it."""
        assert C.refute_record("We refuted nothing; no refutes were needed.\n")
        assert C.refute_record("- No refute pass ran: tooling only.\n") == []

    def test_the_real_prose_refute_is_caught_without_its_exemption(self):
        """259 refuted as prose under a heading. Take it off the list and A8
        must fire on the real log."""
        assert C.refute_record(_logs()["259"])

    def test_the_exemption_is_exactly_the_logs_that_fail(self):
        measured = {p for p, t in _logs().items() if C.refute_record(t, p)}
        assert measured == C.A8_REFUTE_EXEMPT
        assert len(C.A8_REFUTE_EXEMPT) == 40
        assert {"255B", "258", "259"} <= C.A8_REFUTE_EXEMPT

    def test_the_seven_old_checklists_pass(self):
        logs = _logs()
        for phase in ("257", "260", "261", "262", "264", "353", "354"):
            assert C.refute_record(logs[phase], phase) == [], phase


class TestTheWiring:
    """Both run inside check(), the function the push guard and verify_phase
    call — shown on the shared known-bad fixture."""

    def test_check_reports_a5_and_a8_on_the_bad_fixture(self):
        fails = C.check(SKILL / "fixtures" / "bad", "ZZZ")
        assert any(f.startswith("A5") for f in fails)
        assert any(f.startswith("A8") for f in fails)

    def test_check_fires_a5_on_a_line_with_no_command(self, tmp_path):
        """The good tree with its regression line swapped for the known-bad
        one: a hash and a count, no command. check() must fire A5 — the
        case the old A5 passed."""
        import shutil
        tree = tmp_path / "tree"
        shutil.copytree(SKILL / "fixtures" / "good", tree)
        log = tree / "docs" / "phases" / "completed" / "ZZZ_phase_log.md"
        good_line = next(ln for ln in log.read_text().splitlines()
                         if ln.startswith("Regression of record:"))
        bad_line = next(ln for ln in (FIX / "a5_bad_no_command.md").read_text().splitlines()
                        if ln.startswith("Regression of record:"))
        log.write_text(log.read_text().replace(good_line, bad_line))
        assert any(f.startswith("A5") for f in C.check(tree, "ZZZ"))

    def test_check_passes_the_good_fixture_on_both(self):
        fails = C.check(SKILL / "fixtures" / "good", "ZZZ")
        assert not [f for f in fails if f[:2] in ("A5", "A8")], fails
