"""Phase 244U — the gate can see what a re-export hides.

Phase 209B's reachability gate counts identifiers, and a package re-export
writes a name twice: once in the ``from … import`` alias list, once in
``__all__``. So every name a package exported looked referenced whether or not
anything called it.

``SafetyChecker`` is the proof. Phase 241 recorded that it had no caller,
``engine/__init__`` re-exported it, and the gate said nothing for four phases
until 244T wired it up by hand.

The load-bearing test here is
:meth:`TestBothHalvesAreRequired.test_each_half_alone_hides_the_name`. Measured
on this tree, blanking the alias lists alone reveals **nothing** (46 orphans,
unchanged); blanking ``__all__`` alone reveals 3; together they reveal 20.
Someone who ships the first half, sees green and stops has learned the
opposite of the truth.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from support.integration_gaps import (
    blank_exports,
    find_orphans,
    find_unreachable_modules,
)


@pytest.fixture
def tree(tmp_path):
    """A package that re-exports one used name and one dead one."""
    pkg = tmp_path / "src" / "demo"
    (pkg / "cli").mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        "from demo.live import used_helper\n"
        # Parenthesised and multi-line, as this tree's packages actually
        # re-export. Phase 244X: the single-line form 244U pinned was the
        # one form its regex handled.
        "from demo.shelf import (\n"
        "    ShelfSitter,\n"
        ")\n"
        '__all__ = ["used_helper", "ShelfSitter"]\n'
    )
    (pkg / "cli" / "__init__.py").write_text("")
    (pkg / "cli" / "main.py").write_text(
        "from demo.live import used_helper\n\n\ndef cli():\n    used_helper()\n"
    )
    (pkg / "live.py").write_text("def used_helper():\n    return 1\n")
    (pkg / "shelf.py").write_text(
        '"""A capability nobody calls."""\n\n\nclass ShelfSitter:\n    pass\n'
    )
    return tmp_path / "src", pkg


class TestAREexportIsNotAUse:
    def test_the_dead_re_export_is_reported(self, tree):
        _src, pkg = tree
        assert "shelf.py::ShelfSitter" in find_orphans(pkg)

    def test_the_used_name_is_not(self, tree):
        _src, pkg = tree
        assert "live.py::used_helper" not in find_orphans(pkg)

    def test_a_name_listed_only_in_all_is_reported(self, tmp_path):
        """`__all__` is blanked in every file, not only package inits."""
        pkg = tmp_path / "src" / "demo2"
        (pkg / "cli").mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "cli" / "__init__.py").write_text("")
        (pkg / "cli" / "main.py").write_text("def cli():\n    pass\n")
        (pkg / "surface.py").write_text(
            '__all__ = ["exported_but_dead"]\n\n\ndef exported_but_dead():\n    pass\n'
        )
        assert "surface.py::exported_but_dead" in find_orphans(pkg)


class TestBothHalvesAreRequired:
    """The conjunctive proof. This is the test that stops someone shipping the
    obvious half, seeing a green gate, and concluding there was nothing here."""

    def _orphans_with(self, pkg: Path, *, blank_aliases: bool, blank_all: bool) -> set:
        import re
        from collections import Counter

        from support.integration_gaps import _IDENTIFIER, _public_defs, _source_files
        from support.source_guards import blank_comments_and_docstrings

        raw = {p: p.read_text(encoding="utf-8") for p in _source_files(pkg)}
        code = {}
        for p, s in raw.items():
            text = blank_comments_and_docstrings(s)
            if blank_all:
                text = re.sub(
                    r"__all__\s*=\s*\[[^\]]*\]",
                    lambda m: re.sub(r'"[^"]*"', lambda x: '"' + "_" * (len(x.group(0)) - 2) + '"', m.group(0)),
                    text, flags=re.S,
                )
            if blank_aliases and p.name == "__init__.py":
                text = re.sub(
                    r"(from\s+[\w\.]+\s+import\s*)(\([^)]*\)|[^\n]*)",
                    lambda m: m.group(1) + re.sub(r"[A-Za-z_][A-Za-z0-9_]*", lambda x: "_" * len(x.group(0)), m.group(2)),
                    text,
                )
            code[p] = text
        counts = {p: Counter(_IDENTIFIER.findall(t)) for p, t in code.items()}
        total: Counter = Counter()
        for c in counts.values():
            total.update(c)
        out = set()
        for path, source in raw.items():
            own = counts[path]
            for name in _public_defs(path, source):
                if total[name] - own[name] <= 0 and own[name] - 1 <= 0:
                    out.add(f"{path.relative_to(pkg).as_posix()}::{name}")
        return out

    def test_each_half_alone_hides_the_name(self, tree):
        _src, pkg = tree
        dead = "shelf.py::ShelfSitter"
        assert dead not in self._orphans_with(pkg, blank_aliases=False, blank_all=False)
        assert dead not in self._orphans_with(pkg, blank_aliases=True, blank_all=False), (
            "the alias list alone leaves the __all__ entry standing"
        )
        assert dead not in self._orphans_with(pkg, blank_aliases=False, blank_all=True), (
            "__all__ alone leaves the import alias standing"
        )
        assert dead in self._orphans_with(pkg, blank_aliases=True, blank_all=True)

    def test_the_helper_says_both_halves_are_needed(self):
        doc = blank_exports.__doc__ or ""
        assert "Both halves are required" in doc


class TestTheBlankingIsNarrow:
    def test_the_module_path_survives(self):
        """`find_unreachable_modules` walks imports; blanking the path would
        report every module as unreachable."""
        blanked = blank_exports(
            "from motodiag.engine.safety import SafetyChecker\n", is_init=True,
        )
        assert "motodiag.engine.safety" in blanked
        assert "SafetyChecker" not in blanked

    def test_a_non_init_module_keeps_its_imports(self):
        source = "from motodiag.engine.safety import SafetyChecker\n"
        assert blank_exports(source, is_init=False) == source

    def test_the_scope_is_package_inits_only(self, tmp_path):
        """A deliberate boundary, pinned because the mutation run walked
        straight through it: nothing tested WHERE the alias blanking applies.

        A bare re-export inside a normal module still counts as a use here.
        That is arguably the same masking problem one layer out, and widening
        the rule is a decision someone can take later — but it should be taken
        on purpose, with this test failing to say so."""
        pkg = tmp_path / "src" / "demo3"
        (pkg / "cli").mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "cli" / "__init__.py").write_text("")
        (pkg / "cli" / "main.py").write_text("def cli():\n    pass\n")
        (pkg / "shelf.py").write_text("class Sitter:\n    pass\n")
        # a NON-init module that imports the name and never uses it
        (pkg / "passthrough.py").write_text("from demo3.shelf import Sitter\n")
        assert "shelf.py::Sitter" not in find_orphans(pkg), (
            "a bare import outside __init__ still counts as a reference"
        )

    def test_a_re_export_is_still_an_import_edge(self, tree):
        """The two halves of the gate must disagree here, and that is correct.

        `demo/__init__` imports `demo.shelf`, so the MODULE is reachable — the
        import graph is real. What 244U changed is that the same line no longer
        counts as a USE of the name `ShelfSitter`, so the class shows up as an
        orphan inside a reachable module. A capability can be importable and
        still be something no user can reach."""
        src, pkg = tree
        dead = find_unreachable_modules(src, "demo", {"demo.cli.main"})
        assert "demo.shelf" not in dead, "the package init imports it"
        assert "shelf.py::ShelfSitter" in find_orphans(pkg), "nothing calls it"

    def test_an_all_in_a_docstring_is_not_touched(self):
        source = '"""Mentions __all__ = ["x"] in prose."""\n'
        assert blank_exports(source, is_init=False) == source or '"x"' not in blank_exports(source, is_init=False)


class TestTheKnownScale:
    """What the blind spot was hiding, pinned like 209B pinned its own."""

    def test_the_orphan_list_is_the_running_count(self):
        """46 before 244U could see through a re-export, 66 after, 58 once
        244V wired the reference lookups, 47 once 244W moved thirteen names
        into MODULE_ISLANDS (a dead file is one entry, not thirteen) and saw
        two more through prose strings, 104 once 244X made 244U's rule
        reach the multi-line re-exports it had missed. The literal moves with the tree —
        DOWN when a phase reaches or reclassifies something, UP only when a
        new gap lands."""
        from support.integration_gaps_allowlist import ORPHANS

        assert len(ORPHANS) == 104  # f9-noqa: ssot-pin fixture-data: the running count of live orphans — 46 (pre-244U) → 66 (244U opened the blind spot) → 58 (244V wired eight reference lookups) → 47 (244W: 13 reclassified as dead modules, +2 seen through prose strings) → 104 (244X: 244U's rule finally reached multi-line re-exports, +57). The stale/new-entry tests in test_phase209B_integration_gaps.py are what hold the tree to the list; this literal is the record of the trend.

    def test_what_was_hidden_was_a_layer_not_a_scattering(self):
        """What the blind spot hid was a LAYER: twenty engine capabilities a
        technician would want — torque specs, valve clearances, wiring
        references, cost estimates, parts recommendations, repair-procedure
        generation — none of them reachable.

        244V took five of them (the torque, clearance, interval and two
        circuit lookups, now behind `motodiag ref`). Fifteen remain, and this
        asserts the layer is still there rather than pretending it is not: the
        bound is a ceiling, so a phase that wires more of it passes, and one
        that adds engine capability nobody can reach fails."""
        from support.integration_gaps_allowlist import ORPHANS

        unwired = [
            k for k in ORPHANS
            if k.startswith("engine/") and ORPHANS[k][0] == "unwired-feature"
        ]
        assert 0 < len(unwired) <= 15, (
            "engine capability a technician would want, reachable by nothing: "
            f"{len(unwired)} entries — {sorted(unwired)}"
        )
