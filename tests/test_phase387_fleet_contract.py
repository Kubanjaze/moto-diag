"""Phase 387 — the fleet contract: the XO's checklist, `plan_check.py`.

**Why the known-bad cases are one edit each.** A checklist that fails a bad
plan for the wrong reason has not been shown to work: a plan missing its
step-0 report also has no classification, and a test that only asked "did
it fail?" would pass if P4 caught it and P2 were broken. So each case breaks
one item, and must fail on that item and on no other.

**Why 384 and 386 are read at their commits.** The prompt names their v1.0
as known-good. Their v1.0 are history (`b6ffcb6`, `5d0a687`); the documents
on disk are v1.1, moved to `completed/`. `--rev` reads every file as the
commit held it, the CLAUDE.md change log included.

**The pin is held to equality** (the operator, 2026-10-22: "Pin them
(Recommended)"): without it, each pinned plan fails on exactly its pinned
items. An item that a pinned plan passes anyway turns this red, and so does
a plan added to the pin that does not need it.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(SKILL))

import plan_check  # noqa: E402
from plan_check import (FIXTURE_PHASE, GOOD, ITEM_IDS, WRITTEN_BEFORE,  # noqa: E402
                        apply_case, bad_cases, check)

#: The v1.0 commits the prompt names as known-good, and this phase's own.
V10 = {"384": "b6ffcb6", "386": "5d0a687", "387": "ea6fed8"}
CASES = bad_cases()


class TestTheKnownBadCases:
    @pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
    def test_each_fails_on_its_own_item_and_no_other(self, case, tmp_path):
        rep = check(FIXTURE_PHASE, apply_case(case, tmp_path / "tree"))
        assert set(rep.failed) == {case["item"]}, rep.lines()
        assert not rep.unreadable
        assert any(ln.startswith(f"{case['item']} FAIL") for ln in rep.lines())

    @pytest.mark.parametrize("item", ITEM_IDS)
    def test_every_item_has_a_case(self, item):
        assert any(c["item"] == item for c in CASES), f"{item} has no known-bad case"

    def test_a_case_that_edits_nothing_is_refused(self, tmp_path):
        fake = {"id": "noop", "item": "P1", "file": "docs/ROADMAP.md",
                "old": "text that is not there", "new": "x"}
        with pytest.raises(ValueError, match="not once"):
            apply_case(fake, tmp_path / "tree")


class TestTheKnownGoodPlans:
    def test_the_good_fixture_passes(self):
        rep = check(FIXTURE_PHASE, GOOD)
        assert rep.ok and not rep.skipped, rep.lines()

    @pytest.mark.parametrize("phase", sorted(V10))
    def test_the_named_v1_0_passes_at_its_commit(self, phase):
        rep = check(phase, ROOT, rev=V10[phase])
        assert rep.ok, rep.lines()
        assert set(rep.skipped) == set(WRITTEN_BEFORE.get(phase, ())), rep.lines()

    def test_387_needs_no_pin(self):
        """The positive control for P4, P7 and P8 on a real plan."""
        assert "387" not in WRITTEN_BEFORE
        rep = check("387", ROOT, rev=V10["387"], pin=False)
        assert rep.ok, rep.lines()


class TestThePinIsExactlyWhatIsNeeded:
    @pytest.mark.parametrize("phase", sorted(WRITTEN_BEFORE))
    def test_without_the_pin_it_fails_on_exactly_its_pinned_items(self, phase):
        rep = check(phase, ROOT, rev=V10[phase], pin=False)
        assert set(rep.failed) == set(WRITTEN_BEFORE[phase]), rep.lines()

    def test_the_pin_holds_the_two_plans_the_operator_named(self):
        assert set(WRITTEN_BEFORE) == {"384", "386"}


class TestExitCodes:
    def run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SKILL / "plan_check.py"), *args],
                              capture_output=True, text=True)

    def test_0_on_a_pass(self):
        assert self.run(FIXTURE_PHASE, "--repo", str(GOOD)).returncode == 0

    def test_1_on_a_fail_naming_the_item(self, tmp_path):
        tree = apply_case(next(c for c in CASES if c["id"] == "P4_reshape"), tmp_path / "t")
        r = self.run(FIXTURE_PHASE, "--repo", str(tree))
        assert r.returncode == 1 and "P4 FAIL" in r.stdout and "FAIL (P4)" in r.stdout

    def test_2_when_the_plan_cannot_be_read(self):
        r = self.run("999", "--repo", str(GOOD))
        assert r.returncode == 2 and "CANNOT READ" in r.stdout

    def test_the_self_test_passes(self):
        r = self.run("--self-test")
        assert r.returncode == 0, r.stdout


class TestReusedNotCopied:
    """Step 0 (S0-4): P1 and P5 use what the closeout skill already has."""

    def test_p1_reads_the_roadmap_with_roadmap_check(self):
        import roadmap_check
        assert plan_check.rows is roadmap_check.rows
        assert plan_check.ACTIVE is roadmap_check.ACTIVE

    def test_p5_takes_the_knowledge_path_from_wholetree(self):
        import wholetree
        assert plan_check.CONTENT_PATHS is wholetree.CONTENT_PATHS


class TestTheCountRule:
    def test_a_planted_bare_count_is_caught(self):
        assert plan_check.unshown_counts("The corpus holds 412 manuals on disk.")

    def test_a_count_with_its_command_passes(self):
        assert not plan_check.unshown_counts("`ls inbox | wc -l` → 412 manuals on disk.")

    @pytest.mark.parametrize("text", [
        "Read literally, it fails 384 on three items.",   # a phase, then a preposition
        "Step 8 says so.", "Built in 2026 releases.", "pre-tax 23000 × 3500 parts",
    ])
    def test_what_names_rather_than_counts_is_not_a_count(self, text):
        assert not plan_check.counts_in(text), text
