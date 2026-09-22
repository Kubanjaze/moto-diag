"""Phase 255D — the finding contract.

**The evidence is F135.** Phase 255C's plan stated a question had been
"filed on the general-applicability ticket". It had not — the claim was
written and the entry never created. B2 is that sentence made executable:
every F-number a phase document cites must resolve to an entry that exists.

**Why the known-bad fixture cites one past the end.** The first version of
B2 excluded false positives with a ceiling — ignore anything above the
highest assigned number. `F650`/`F700`/`F750` are BMW motorcycles and `F401`
is a flake8 code, so the ceiling worked on those; but it also skipped a
citation of `F139` in a file that stops at `F138`, which is precisely the
failure the check exists to catch. The fixture pins that case so the ceiling
cannot come back.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "finding"
sys.path.insert(0, str(SKILL))

from finding_check import (ASSERTION_IDS, KNOWN_DANGLING,  # noqa: E402
                           NOT_FINDINGS, check, entries)

BAD = SKILL / "fixtures" / "bad"
GOOD = SKILL / "fixtures" / "good"


class TestTheKnownBadFixtureFailsEveryAssertion:
    @pytest.fixture(scope="class")
    def fails(self):
        return check(BAD, sibling=None)

    @pytest.mark.parametrize("aid", ASSERTION_IDS)
    def test_this_assertion_fires(self, fails, aid):
        assert any(f.startswith(aid) for f in fails), (
            f"{aid} did not fire on the known-bad fixture: {fails}")

    def test_b2_names_the_citation_one_past_the_end(self, fails):
        """The ceiling regression, pinned."""
        b2 = [f for f in fails if f.startswith("B2")]
        assert b2 and "F139" in b2[0], (
            "B2 must catch a citation one past the highest entry — that is "
            f"the real failure shape, and a ceiling rule hides it: {fails}")


class TestTheKnownGoodFixturePasses:
    def test_no_assertion_fires(self):
        assert check(GOOD, sibling=None) == []


class TestAgainstTheRealRepository:
    def test_the_repository_is_clean(self):
        fails = check(ROOT)
        assert fails == [], f"finding contract broken in the real repo: {fails}"

    def test_both_followups_files_are_read(self):
        """F-numbers are ONE sequence across both repos. Reading only this
        one reported 98 dangling citations that are all real mobile
        findings."""
        here = entries(ROOT / "docs" / "FOLLOWUPS.md")
        there = entries(ROOT / ".." / "moto-diag-mobile" / "docs" / "FOLLOWUPS.md")
        assert here and there, (
            "both files must contribute; if the sibling is missing the check "
            "silently narrows and reports mobile findings as dangling")
        assert max(here) > max(there), (
            "this repo holds the higher numbers; if that flips, the "
            "allocation script's assumptions need revisiting")


class TestTheExclusionsAreNamedNotNumericRanges:
    def test_every_exclusion_carries_a_reason(self):
        for n, why in {**KNOWN_DANGLING, **NOT_FINDINGS}.items():
            assert isinstance(why, str) and len(why) > 10, (
                f"exclusion F{n} has no stated reason; an unexplained "
                "exclusion is indistinguishable from a bug")

    def test_the_motorcycles_are_excluded_by_name(self):
        for n in (650, 700, 750):
            assert n in NOT_FINDINGS, (
                f"F{n} is a BMW model and must be excluded BY NAME, not by a "
                "ceiling — a ceiling also hides a citation one past the end")


class TestTheAllocationScript:
    def test_it_reports_a_number_above_both_files(self):
        r = subprocess.run([str(SKILL / "next_f_number.sh")],
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr
        assert "next free: F" in r.stdout, r.stdout
        nxt = int(r.stdout.split("next free: F")[1].split()[0])
        here = entries(ROOT / "docs" / "FOLLOWUPS.md")
        there = entries(ROOT / ".." / "moto-diag-mobile" / "docs" / "FOLLOWUPS.md")
        assert nxt > max(here | there), (
            "the next free number must exceed the highest in BOTH files; "
            "taking it from one is how two findings share a number")
