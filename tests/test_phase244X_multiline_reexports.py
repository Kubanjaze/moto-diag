"""Phase 244X — 244U's rule reaches the imports it was written for.

244U established that a package-init re-export is not a use, and blanked the
alias list with a regex whose alias group could not cross a newline. The
parenthesised multi-line ``from … import (…)`` that most packages in this
tree use for their exports was therefore never blanked, and for `auth`,
`inventory`, `billing`, `feedback` and the rest the rule had never applied.

One of 244W's design prototypes found it; 244W's Step 0 verified it and
measured the cost; this phase fixes it. 57 names surfaced — every one
re-exported by exactly one init and referenced by nothing else — and two of
them this repo had already pinned as callerless by other means:
`submit_feedback` (the audit: `diagnostic_feedback` has 0 rows) and
`load_recalls_from_json` (F86's `test_nothing_in_the_product_seeds_them`).

The fixture I wrote for 244U used single-line imports. It passed, and it was
pinning the one shape the regex handled.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest
from support.integration_gaps import (
    blank_exports,
    entry_points_from_pyproject,
    find_module_islands,
    find_orphans,
    find_unreachable_modules,
    module_map,
)
from support.integration_gaps_allowlist import ORPHANS

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
PACKAGE_ROOT = SRC / "motodiag"
PYPROJECT = (REPO / "pyproject.toml").read_text(encoding="utf-8")
ENTRY_POINTS = entry_points_from_pyproject(PYPROJECT) | {"motodiag", "motodiag.api"}


@lru_cache(maxsize=1)
def _live_orphans() -> frozenset[str]:
    """209B's pipeline, inline: orphans outside every dead module."""
    dead = (find_unreachable_modules(SRC, "motodiag", ENTRY_POINTS)
            | find_module_islands(SRC, "motodiag", ENTRY_POINTS))
    mods = module_map(SRC, "motodiag")
    dead_files = {mods[m].relative_to(PACKAGE_ROOT).as_posix() for m in dead}
    return frozenset(
        o for o in find_orphans(PACKAGE_ROOT, extra_reference_text=PYPROJECT)
        if o.split("::")[0] not in dead_files
    )


# ---------------------------------------------------------------------------
# 1. Every form of the import statement
# ---------------------------------------------------------------------------


class TestEveryFormIsBlanked:
    @pytest.mark.parametrize("source", [
        "from demo.shelf import ShelfSitter, Other\n",
        "from demo.shelf import (ShelfSitter, Other)\n",
        "from demo.shelf import (\n    ShelfSitter,\n    Other,\n)\n",
        "from demo.shelf import (\n    ShelfSitter,\n    Other\n)\n",
        "from demo.shelf import (ShelfSitter as SS,\n                        Other)\n",
        "from demo.shelf import (\n    ShelfSitter,  # kept for callers\n    Other,\n)\n",
    ], ids=["single-line", "paren-single-line", "multi-line", "no-trailing-comma",
            "as-alias", "comment-inside"])
    def test_the_alias_list_is_blanked_in_an_init(self, source):
        out = blank_exports(source, is_init=True)
        assert "ShelfSitter" not in out
        assert "Other" not in out

    def test_the_multi_line_form_was_the_defect(self):
        """Pinned as a pair so the fix cannot regress to handling one form:
        the regex 244U shipped blanked the first and not the second."""
        one = "from demo.shelf import ShelfSitter\n"
        many = "from demo.shelf import (\n    ShelfSitter,\n)\n"
        assert "ShelfSitter" not in blank_exports(one, is_init=True)
        assert "ShelfSitter" not in blank_exports(many, is_init=True)

    def test_an_as_alias_is_blanked_on_both_sides(self):
        out = blank_exports("from demo.shelf import (\n    ShelfSitter as SS,\n)\n", is_init=True)
        assert "SS" not in out.replace("__", "")

    def test_the_module_path_survives(self):
        """The import walk reads it; blanking it would make every module
        unreachable — 244U's `test_the_module_path_survives`, on the
        multi-line form."""
        out = blank_exports("from demo.shelf.deep import (\n    ShelfSitter,\n)\n", is_init=True)
        assert "demo.shelf.deep" in out

    def test_a_non_init_module_keeps_its_imports(self):
        """Unchanged from 244U: widening this is its explicitly deferred
        decision, not this phase's to take."""
        source = "from demo.shelf import (\n    ShelfSitter,\n)\n"
        assert blank_exports(source, is_init=False) == source

    def test_positions_are_preserved(self):
        source = "from demo.shelf import (\n    ShelfSitter,\n    Other,\n)\nx = 1\n"
        out = blank_exports(source, is_init=True)
        assert len(out) == len(source)
        assert out.count("\n") == source.count("\n")

    def test_two_imports_are_blanked_independently(self):
        source = ("from demo.a import (\n    A,\n)\n"
                  "from demo.b import B\n"
                  "from demo.c import (\n    C,\n    D,\n)\n")
        out = blank_exports(source, is_init=True)
        for name in ("A", "B", "C", "D"):
            assert f" {name}" not in out and f"\n{name}" not in out


# ---------------------------------------------------------------------------
# 2. The real tree
# ---------------------------------------------------------------------------


class TestWhatTheRuleFindsNow:
    @pytest.mark.parametrize("name", [
        "feedback/feedback_repo.py::submit_feedback",
        "advanced/recall_repo.py::load_recalls_from_json",
        "inventory/recall_repo.py::add_recall",
        "memory/compile.py::compile_all",
        "auth/users_repo.py::create_user",
    ])
    def test_a_name_this_repo_already_knew_was_callerless_is_reported(self, name):
        """Each of these was established as callerless by some other means —
        an audit, F86's tripwire, 209C's wiring — and the gate could not say
        so, because a multi-line re-export stood in the way."""
        assert name in _live_orphans()

    def test_the_new_entries_match_the_tree_in_both_directions(self):
        """209B's stale/new tests hold the whole list; this holds the 57."""
        new = {k for k, (_, r) in ORPHANS.items() if "Phase 244X" in r}
        assert len(new) == 57  # f9-noqa: ssot-pin fixture-data: Phase 244X's finding — 57 names only a multi-line re-export ever mentioned, on 2026-09-18. The stale/new tests in test_phase209B_integration_gaps.py hold the tree to the list; this literal is the record.
        assert new <= _live_orphans(), sorted(new - _live_orphans())

    @pytest.mark.parametrize("name,entry", sorted(
        (k, v) for k, v in ORPHANS.items() if "Phase 244X" in v[1]
    ))
    def test_every_new_entry_names_the_init_that_hid_it(self, name, entry):
        pkg = name.split("/")[0]
        assert f"{pkg}/__init__.py" in entry[1], name

    def test_the_duplicate_recall_repo_is_recorded_as_superseded(self):
        """Phase 118 and Phase 155 each wrote a recall repository over the
        same table; only the second has a command. The entries say so."""
        for fn in ("add_recall", "delete_recall", "get_recall", "list_recalls"):
            cls, reason = ORPHANS[f"inventory/recall_repo.py::{fn}"]
            assert cls == "superseded"
            assert "advanced/recall_repo" in reason

    def test_submit_feedback_is_recorded_as_unwired_not_as_a_helper(self):
        """Nothing writes diagnostic_feedback. Calling that a library helper
        would hide the one fact a future feedback phase needs."""
        cls, reason = ORPHANS["feedback/feedback_repo.py::submit_feedback"]
        assert cls == "unwired-feature"
        assert "0 rows" in reason
