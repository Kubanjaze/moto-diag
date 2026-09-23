"""Phase 255D — the refuter checklist contract.

**This is a REPORT check and the test says so.** Whether a claim survived
contact with the documents cannot be asserted by a script. What is asserted
is that the pass emitted its checklist and that every row carries the two
things that make a human spot-check cheap: a verbatim quote, and a document
plus page.

A complete block is consistent with a lazy pass. That ceiling is the reason
`refute` was sequenced last and the reason it ships a checklist rather than
a guarantee.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "refute"
sys.path.insert(0, str(SKILL))

from refute_check import ASSERTION_IDS, check  # noqa: E402

FIX = SKILL / "fixtures"


def _read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


class TestTheKnownBadFixturesFailEveryAssertion:
    @pytest.fixture(scope="class")
    def fails(self):
        # C1 needs a log with no block at all; C2-C4 need a block with
        # defective rows. Two fixtures, one per shape.
        return check(_read("missing_log.md")) + check(_read("bad_log.md"))

    @pytest.mark.parametrize("aid", ASSERTION_IDS)
    def test_this_assertion_fires(self, fails, aid):
        assert any(f.startswith(aid) for f in fails), (
            f"{aid} did not fire on the known-bad fixtures: {fails}")

    def test_c3_and_c4_name_the_offending_row(self, fails):
        quoted = [f for f in fails if f.startswith(("C3", "C4"))]
        assert quoted and any("Kymco Like" in f for f in quoted), (
            "a failure must name which row is short of a quote or a page, or "
            f"it cannot be acted on: {fails}")


class TestTheKnownGoodFixturePasses:
    def test_no_assertion_fires(self):
        assert check(_read("good_log.md")) == []


class TestTheCeilingIsWrittenDown:
    """The honest limit must be in the skill, where a reader will meet it."""

    def test_the_skill_states_that_this_checks_the_report_not_the_work(self):
        txt = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "checks the report, not the work" in txt, (
            "the skill must state its own ceiling; a checklist that reads as "
            "a guarantee is worse than no checklist")
        assert "consistent with a lazy pass" in txt
