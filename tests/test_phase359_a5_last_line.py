"""Phase 359, bug fix #1 — A5 judges the last regression line, not the first.

358's A5 took the first line that parsed. After a re-run (358 itself: bug
fix #2 changed code, and 9636 at `8a205ee` was superseded by 9639 at
`d93d8de`), that is the run the close-out no longer rests on. This fixes
358's check; its rule (count + hash + command) is unchanged.
"""

from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "closeout"
sys.path.insert(0, str(SKILL))

import closeout_check as C  # noqa: E402

FIX = SKILL / "fixtures" / "k6_k7"


def test_a_log_whose_last_line_does_not_parse_fails():
    text = (FIX / "a5_bad_last_line_superseded.md").read_text()
    lines = [ln for ln in text.splitlines() if "Regression of record:" in ln]
    assert len(lines) == 2
    assert C._REGRESSION.search(lines[0]), "the fixture's first line must parse"
    assert C.regression_line(text) is None


def test_a_log_whose_last_line_parses_passes_with_the_last_run():
    text = (FIX / "a5_good_last_line.md").read_text()
    assert C.regression_line(text) == ("9639", "bbbbbbb", "python -m pytest -n auto --dist load")


def test_358_is_judged_on_its_re_run():
    log = (ROOT / "docs" / "phases" / "completed" / "358_phase_log.md").read_text()
    assert C.regression_line(log)[:2] == ("9639", "d93d8de")


def test_check_fires_a5_when_a_bad_line_follows_a_good_one(tmp_path):
    """Wiring: the good tree with a non-parsing re-run appended below its
    good line. check() — what the push guard and verify_phase call — must
    fire A5."""
    tree = tmp_path / "tree"
    shutil.copytree(SKILL / "fixtures" / "good", tree)
    log = tree / "docs" / "phases" / "completed" / "ZZZ_phase_log.md"
    assert not [f for f in C.check(tree, "ZZZ") if f.startswith("A5")]
    bad = next(ln for ln in (FIX / "a5_bad_last_line_superseded.md").read_text().splitlines()
               if "Regression of record:" in ln and "exit 0)" in ln and "pytest" not in ln)
    log.write_text(log.read_text() + "\n" + bad + "\n")
    assert any(f.startswith("A5") for f in C.check(tree, "ZZZ"))
