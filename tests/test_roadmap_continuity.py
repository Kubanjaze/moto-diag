"""The ROADMAP stays true while phases are worked (roadmap_check.py R1-R5).

The guarantee behind the CLAUDE.md rule "a phase gets its row before Step 0,
and the row changes with the work": it runs with every suite, and the push
guard refuses a `git push` while it fails. Each rule is also seen to fire
on a hand-written known-bad tree, and a good tree holds the cases each rule
must NOT remove (a Track I phase found in the mobile ledger, a paused phase,
a phase in progress, a row past the original plan).
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLOSEOUT = ROOT / ".claude" / "skills" / "closeout"
sys.path.insert(0, str(CLOSEOUT))

import _pre_push_guard as guard  # noqa: E402
import roadmap_check as R  # noqa: E402

BAD = CLOSEOUT / "fixtures" / "roadmap_bad"
GOOD = CLOSEOUT / "fixtures" / "roadmap_good"


class TestTheRealLedger:
    def test_the_mobile_repo_is_beside_this_one(self):
        """Without it, the Track I half of R2/R3 and R5 would pass unrun."""
        assert R.SIBLING.is_dir(), f"the mobile repo is not at {R.SIBLING}"

    def test_the_roadmap_and_the_phase_documents_agree(self):
        assert R.check_tree() == []


class TestEachRuleFiresOnTheKnownBadTree:
    @pytest.fixture(scope="class")
    def fails(self):
        return R.check_tree(BAD, BAD / "sibling")

    @pytest.mark.parametrize("rule,case", [
        ("R1 phase 256 has 2 rows", "a number reused (the real 256, 2026-09-24)"),
        ("R2 phase 259 has documents", "documents with no row"),
        ("R2 phase 191 has documents", "a Track I phase missing from the mobile ledger"),
        ("R3 phase 257 has documents in completed/", "a closed phase whose row was never closed"),
        ("R3 phase 258 has documents in in_progress/", "a phase under way whose row still says not started"),
        ("R4 phase 190 is mobile-owned", "a Track I row in the backend ledger"),
        ("R4 phase 400 is in no range", "a row no authority range covers (the real 353)"),
        ("R5 the two copies", "the contract's copies drifting apart"),
    ])
    def test_it_fires(self, fails, rule, case):
        assert any(f.startswith(rule) for f in fails), (case, fails)


class TestTheGoodTreePasses:
    def test_every_allowed_case_passes(self):
        assert R.check_tree(GOOD, GOOD / "sibling") == []


class TestThePushGuardCallsIt:
    """Wiring: a module called from one integration point ships with a test
    that the point calls it. The guard refuses ANY push while the ledger has
    drifted - unlike close-out, continuity can be true mid-phase."""

    @staticmethod
    def _push(monkeypatch, capsys, fails, command="git push origin phase-branch"):
        monkeypatch.setattr(R, "check_tree", lambda *a, **k: list(fails))
        monkeypatch.setattr(sys, "stdin", _Stdin(json.dumps({"tool_input": {"command": command}})))
        return guard.main(), capsys.readouterr().err

    def test_a_push_is_refused_while_the_ledger_has_drifted(self, monkeypatch, capsys):
        code, err = self._push(monkeypatch, capsys, ["R1 phase 256 has 2 rows in docs/ROADMAP.md"])
        assert code == 2 and "R1 phase 256" in err

    def test_a_push_goes_through_when_it_agrees(self, monkeypatch, capsys):
        code, _ = self._push(monkeypatch, capsys, [])
        assert code == 0

    def test_a_command_that_is_not_a_push_is_never_checked(self, monkeypatch, capsys):
        code, _ = self._push(monkeypatch, capsys, ["R1 anything"], command="git status")
        assert code == 0


class _Stdin:
    def __init__(self, text: str):
        self._text = text

    def read(self, *_):
        return self._text
