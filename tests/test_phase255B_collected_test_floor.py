"""A floor on the number of tests this suite collects. 244U's orphan pin, in reverse.

244U pins a running count of orphaned definitions: it moves DOWN when a
phase wires something up and UP only when a new gap lands, and the literal
is the record of the trend. This pins the opposite quantity for the
opposite reason.

**Why it exists.** Phase 255B lost a guard and both tests that pinned it to
a single `re.sub` and one slice of index surgery. A protection and its
tests deleted in the same stroke leave nothing to notice, and nothing did:
the suite stayed green on the files that were run, and the loss surfaced
only when a full regression failed 134 tests in 17 other phase files for an
unrelated-looking reason.

The generalisation is that **a suite cannot report its own absences.**
Every other guard in this tree asserts something about code that is
present. None of them fires when a test stops existing. A green run over a
shrinking suite reads exactly like a green run over a whole one.

**What it costs.** Collection is not execution — `--collect-only` imports
the test modules and walks them, and on this tree that is about one second
for eight thousand tests. The guard is cheap enough to be unconditional.

**How to change it.** Raise the floor in the same commit that adds the
tests, and say in the commit message what they cover. Lowering it is the
interesting case: it is allowed, it is sometimes right — a phase that
deletes a superseded module deletes its tests with it — but it must be
deliberate, stated, and reviewed, which is exactly what a pinned literal
forces and an implicit count does not.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The floor. A commit that collects fewer tests than this fails the suite.
#:
#: 7999 (Phase 255B, 2026-09-22) — the first pin. The regression that closed
#: 255B collected 7,997 at `1fbcdaa`; this file's own two tests make 7,999.
#: Phase 256 closed at 7,964.
#:
#: 8088 (Phase 255C, 2026-09-22) — +89, all in
#: `test_phase255C_junction_identity.py`: the thousands-separator bug fix,
#: the positive gate and its whole-corpus negative control, and the
#: one-canonical-per-machine work — the six-spelling PCX control, Guard 1,
#: Guard 2 per marque, the tier table and the schema-56 degradation path.
#:
#: 8091 (Phase 255C bug fix #7, 2026-09-22) — +3: Guard 3 over the whole
#: junction, its planted positive control, and a unit test of `canonicalise`
#: against another marque's prefix. Guard 3 is the one decision 6 specified
#: and nobody wrote; it caught 59 rows the day it was written.
#:
#: Raise it in the commit that adds the tests. Lower it only deliberately,
#: with the reason in the commit message — a superseded module taking its
#: tests with it is a legitimate reason; a refactor that "tidied" a file is
#: not.
#: 8130 (Phase 255D, 2026-09-22) — +39, the three procedure folders'
#: contracts: 23 closeout, 9 finding, 7 refute. Each folder's known-bad
#: fixture is asserted per-assertion, so a silently removed planted
#: defect fails rather than passing quietly.
#:
#: 8139 (Phase 255D close-out fixes, 2026-09-22) — +9: A4 resolving the
#: commit (non-answer, unresolvable hash, real hash, sibling repo, absent
#: sibling) and check 2's scope (skill script reported, docs-only not, the
#: real b0ae748..3dfc78a miss, every tracked script classified as code).
#: Raised BEFORE the regression of record, so the green run covers it —
#: the previous raise landed after, and check 2 reported it.
#:
#: 8145 (Phase 255D fix #9, 2026-09-22) — +6: A4's heading-time rule — the
#: known-bad fixture, the three real mis-dated headings from history, an
#: honest batch-written heading that must pass, and an uncommitted heading
#: judged against now.
#:
#: 8958 (Phase 257 close-out, 2026-09-23) — +813 over 8145, measured at
#: ebdc7a9: `tests/test_phase257_*.py` collects 813 (the sandbox boundary,
#: the orchestrator's guards and stops, entry_check E1–E12, acquire.py's
#: routes, the manual-route excerpts, and every write). Phase 256's 69 were
#: never added to the floor; the whole count is what is pinned here.
#: Raised before the regression of record.
#:
#: 8959 (Phase 257 close-out, 2026-09-24) — +1: B2 excludes Yamaha's
#: publication numbers ("BRG-F8199-11") by name, with a control that a
#: real citation in the same document still fails (bug fix #9).
#:
#: 8999 (Phase 257B close-out, 2026-09-24) — +40, measured at 26b5007:
#: `test_phase257B_transmission_field.py` 25; the finding contract +1
#: (257B bug fix #2 replaced one test with two); and
#: `test_roadmap_continuity.py` 14, added by 76edc69 (a rule change
#: between 257 and 257B, not a phase) and never added to the floor.
#: Raised before the regression of record.
#:
COLLECTED_TEST_FLOOR = 8999


def _collected_count() -> int:
    """Ask pytest how many tests it can see. Collection only, never execution."""
    out = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "--collect-only", "-q",
         "-p", "no:cacheprovider", str(ROOT / "tests")],
        cwd=str(ROOT), capture_output=True, text=True, timeout=600,
    )
    m = re.search(r"(\d+) tests? collected", out.stdout)
    if not m:
        m = re.search(r"(\d+)/(\d+) tests? collected", out.stdout)
        if m:
            return int(m.group(1))
        pytest.fail(
            "could not read a collected count from pytest.\n"
            f"  returncode: {out.returncode}\n"
            f"  stdout tail: {out.stdout[-800:]}\n"
            f"  stderr tail: {out.stderr[-800:]}")
    return int(m.group(1))


class TestTheSuiteDoesNotShrinkSilently:
    def test_the_collected_count_is_at_or_above_the_floor(self):
        got = _collected_count()
        assert got >= COLLECTED_TEST_FLOOR, (
            f"the suite collects {got} tests; the floor is "
            f"{COLLECTED_TEST_FLOOR}. {COLLECTED_TEST_FLOOR - got} test(s) "
            "have gone missing.\n"
            "If that is deliberate — a superseded module taking its tests "
            "with it — lower COLLECTED_TEST_FLOOR in the same commit and say "
            "why in the message. If it is not deliberate, something deleted "
            "tests without anyone noticing, which is the defect this guard "
            "exists to catch.")

    def test_the_floor_is_not_set_above_what_the_tree_holds(self):
        """A floor above the real count would fail every run and get raised
        rather than investigated. Keeps the pin honest in both directions."""
        got = _collected_count()
        assert COLLECTED_TEST_FLOOR <= got, (
            f"the floor {COLLECTED_TEST_FLOOR} exceeds the {got} tests the "
            "tree holds")
