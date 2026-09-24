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

    def test_the_next_number_clears_both_files(self):
        """Phase 257B replaced `max(here) > max(there)` with this. The old
        assertion pinned which file happened to be ahead and asked for the
        allocation's assumptions to be revisited if it flipped; 257B filed
        three app findings in the mobile file and it flipped. Revisited: the
        script takes the max over both files and B1 compares the header with
        that same global max, so neither cares which file leads. What must
        hold in either direction is that the next number clears both."""
        here = entries(ROOT / "docs" / "FOLLOWUPS.md")
        there = entries(ROOT / ".." / "moto-diag-mobile" / "docs" / "FOLLOWUPS.md")
        out = subprocess.run(
            ["sh", str(SKILL / "next_f_number.sh")],
            capture_output=True, text=True, check=True,
        ).stdout
        nxt = int(out.rsplit("next free: F", 1)[1].split()[0])
        assert nxt == max(here | there) + 1, out


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

    def test_yamahas_publication_numbers_are_excluded_by_name(self, tmp_path):
        """257 cites Yamaha manuals by number ("BRG-F8199-11"). Control: in
        the same document, a citation one past the highest entry still fails."""
        (tmp_path / "docs" / "phases" / "completed").mkdir(parents=True)
        (tmp_path / "docs" / "FOLLOWUPS.md").write_text(
            "highest assigned is **F11**\n\n### F10\n\nx\n\n### F11\n\ny\n")
        doc = tmp_path / "docs" / "phases" / "completed" / "999_phase_log.md"
        doc.write_text("Yamaha OM BRG-F8199-11 (2026), PDF p. 85\n")
        assert [x for x in check(tmp_path, sibling=None) if x.startswith("B2")] == []
        doc.write_text("Yamaha OM BRG-F8199-11 (2026), PDF p. 85; filed as F12\n")
        assert any("F12 " in x for x in check(tmp_path, sibling=None) if x.startswith("B2"))


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
