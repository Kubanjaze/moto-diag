"""Phase 358, K2 — one pin per allowlist size, in F124's shape.

`len(UNREACHABLE_MODULES)` was pinned as a literal in two files,
`len(MODULE_ISLANDS)` in three and `len(ORPHANS)` in one. Wiring a listed
module edits the allowlist, and in Phase 259 the builder updated one pin and
missed its duplicate, which cost a second red regression. Each size now has
one literal, in `tests/support/integration_gaps_counts.py`; tests compare
against the imported constant. This file fails on a literal pin anywhere
else in `tests/`.

Read with `ast`, not raw text: a size named in a comment or a docstring is
history, not a pin, and must pass.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

TESTS = pathlib.Path(__file__).resolve().parent
SELF = pathlib.Path(__file__).name

#: The allowlist tables whose sizes are pinned in integration_gaps_counts.
_TABLES = {"UNREACHABLE_MODULES", "MODULE_ISLANDS", "ORPHANS"}


def _is_table_len(node: ast.AST) -> bool:
    """`len(<table>)`, with the table named bare or as an attribute."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "len" and len(node.args) == 1):
        return False
    arg = node.args[0]
    name = arg.id if isinstance(arg, ast.Name) else getattr(arg, "attr", None)
    return name in _TABLES


def literal_size_pins(directory: pathlib.Path = TESTS) -> list[str]:
    """Every comparison of a table's size with an integer literal.

    `directory` is a parameter so the control plants into a tmp dir, never
    into the real tests/ (Phase 355 bug fix #2).
    """
    found = []
    for path in sorted(directory.rglob("*.py")):
        if path.name == SELF:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            operands = [node.left, *node.comparators]
            if any(_is_table_len(x) for x in operands) and any(
                    isinstance(x, ast.Constant) and type(x.value) is int
                    for x in operands):
                found.append(f"{path.relative_to(directory)}:{node.lineno}")
    return found


class TestOnePinPerCount:
    def test_no_test_pins_a_size_with_a_literal(self):
        pins = literal_size_pins()
        assert not pins, (
            "a test compares an allowlist size with a literal. Compare with "
            "the constant in tests/support/integration_gaps_counts.py "
            "instead, and record the change in its history:\n  "
            + "\n  ".join(pins))

    def test_each_size_is_asserted_where_fast_mode_runs(self):
        """The one assertion per size sits in a file the whole-tree fast mode
        runs, so a wrong count turns the push guard red (K1's fourth plant)."""
        from support.source_guards import code_of

        for fname, const in (
            ("test_phase209B_integration_gaps.py", "UNREACHABLE_COUNT"),
            ("test_phase244W_module_islands.py", "MODULE_ISLAND_COUNT"),
            ("test_phase244U_gate_blind_spot.py", "ORPHAN_COUNT"),
        ):
            assert f"== {const}" in code_of(TESTS / fname), fname


class TestTheScanSeesAPlantedPin:
    """The control: the scan finds what it exists to find, in each shape,
    and passes the comment and the constant."""

    @pytest.mark.parametrize("source", [
        "assert len(ORPHANS) == 102\n",
        "assert 14 == len(MODULE_ISLANDS)\n",
        "assert len(allow.UNREACHABLE_MODULES) >= 34\n",
    ])
    def test_a_literal_pin_is_found(self, tmp_path, source):
        (tmp_path / "test_planted.py").write_text(source)
        assert literal_size_pins(tmp_path) == ["test_planted.py:1"]

    @pytest.mark.parametrize("source", [
        "# assert len(ORPHANS) == 102\n",
        '"""len(ORPHANS) == 102 was the old pin."""\n',
        "assert len(ORPHANS) == ORPHAN_COUNT\n",
        "assert len(OTHER_TABLE) == 3\n",
    ])
    def test_history_and_the_constant_pass(self, tmp_path, source):
        (tmp_path / "test_planted.py").write_text(source)
        assert literal_size_pins(tmp_path) == []
