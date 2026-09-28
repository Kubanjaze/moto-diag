"""Phase 357 — F175: a test that pins a whole-tree check's ledger joins
`wholetree.sh --full` by rule.

On 2026-09-28 `test_phase244Z_shelved_content.py` was in neither mode
(fast 31 files, full 80): it enumerates nothing, but it pins
MODULE_ISLANDS, which 209B keeps equal to the tree. Wiring a module moved
the ledger, 244Z went red, and only the full regression reached it (356
bug fix #1). The ledger class is full-only, so fast mode, the push guard's
run, keeps its members.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "closeout"))

import wholetree as W  # noqa: E402

WALKER = "from support import gaps_ledger\ndef test_x():\n    list(SRC.rglob('*.py'))\n"


def _tree(tmp_path: pathlib.Path, files: dict[str, str]) -> pathlib.Path:
    for d in ("tests/support", "scripts", ".claude/skills"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    for rel, text in files.items():
        (tmp_path / rel).write_text(text)
    return tmp_path


class TestTheRule:
    def test_a_test_pinning_a_ledger_joins_full_not_fast(self, tmp_path):
        root = _tree(tmp_path, {
            "tests/support/gaps_ledger.py": '"""The gap table."""\nISLANDS = ["a", "b"]\n',
            "tests/test_walker.py": WALKER,
            "tests/test_pins.py": "from support.gaps_ledger import ISLANDS\n"
                                  "def test_y():\n    assert len(ISLANDS) == 2\n",
        })
        assert W.census(root)["ledger"] == ["tests/test_pins.py"]
        assert "tests/test_pins.py" in W.members("full", root)
        assert W.members("fast", root) == ["tests/test_walker.py"]

    def test_a_support_module_with_a_function_is_not_a_ledger(self, tmp_path):
        """The control on the exclusion: shared code (like source_guards) is
        not the tree's state; importing it does not make a test whole-tree."""
        root = _tree(tmp_path, {
            "tests/support/gaps_ledger.py": "ISLANDS = []\ndef helper():\n    return 1\n",
            "tests/test_walker.py": WALKER,
            "tests/test_pins.py": "from support.gaps_ledger import helper\n",
        })
        assert W.census(root)["ledger"] == []

    def test_a_data_module_no_member_imports_is_not_a_ledger(self, tmp_path):
        root = _tree(tmp_path, {
            "tests/support/gaps_ledger.py": "ISLANDS = []\n",
            "tests/test_walker.py": "def test_x():\n    list(SRC.rglob('*.py'))\n",
            "tests/test_pins.py": "from support.gaps_ledger import ISLANDS\n",
        })
        assert W.census(root)["ledger"] == []


class TestTheRealTree:
    def test_244Z_and_244Y_are_full_members_by_rule(self):
        c = W.census()
        assert {"tests/test_phase244Z_shelved_content.py",
                "tests/test_phase244Y_delete_pass.py"} <= set(c["ledger"])
        assert "integration_gaps_allowlist" in W.data_only_support()

    def test_fast_mode_gains_no_ledger_member(self):
        assert not set(W.census()["ledger"]) & set(W.members("fast"))
