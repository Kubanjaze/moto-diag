"""Phase 209B — code that was built and never connected, found on purpose.

The 244 series kept finding this by accident: the `feedback/` package had no
caller for nine phases, `diagnose quick` had never completed, `SafetyChecker`
and the `VehicleContext` builder were stubs that nothing noticed. The first
deliberate look found **38 of 256 modules unreachable** from any entry point
-- most of Track C2 among them, under roadmap rows marked done.

``TestTheTreeMatchesTheAllowlist`` is the gate. It fails in BOTH directions:
something newly unreachable, or something listed that has since been
connected. The second direction is what keeps the allowlist from turning into
a list of excuses nobody revisits.

``TestTheScannerIsNotFooled`` pins the traps a scanner like this falls into:
a name that is only mentioned in prose, lazy imports inside functions, and
modules loaded by a string.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pytest

from support.integration_gaps import (
    entry_points_from_pyproject,
    find_orphans,
    find_module_islands,
    find_unreachable_modules,
    module_map,
)
from support.integration_gaps_allowlist import (
    CLASSIFICATIONS,
    ORPHANS,
    UNREACHABLE_MODULES,
)

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
PACKAGE_ROOT = SRC / "motodiag"
PYPROJECT = (REPO / "pyproject.toml").read_text(encoding="utf-8")

# The package root and the API factory are entry surfaces alongside the
# console script: `import motodiag` runs its __init__, and uvicorn imports the
# app from `motodiag.api`.
ENTRY_POINTS = entry_points_from_pyproject(PYPROJECT) | {"motodiag", "motodiag.api"}


@lru_cache(maxsize=1)
def _current_unreachable() -> frozenset[str]:
    return frozenset(find_unreachable_modules(SRC, "motodiag", ENTRY_POINTS))


@lru_cache(maxsize=1)
def _current_module_islands() -> frozenset[str]:
    return frozenset(find_module_islands(SRC, "motodiag", ENTRY_POINTS))


@lru_cache(maxsize=1)
def _current_live_orphans() -> frozenset[str]:
    # Phase 244W: an orphan inside a dead module is implied by the module
    # entry — in UNREACHABLE_MODULES or MODULE_ISLANDS — and not reported
    # a second time by name.
    dead = _current_unreachable() | _current_module_islands()
    mods = module_map(SRC, "motodiag")
    dead_files = {mods[m].relative_to(PACKAGE_ROOT).as_posix() for m in dead}
    return frozenset(
        o for o in find_orphans(PACKAGE_ROOT, extra_reference_text=PYPROJECT)
        if o.split("::")[0] not in dead_files
    )


# ---------------------------------------------------------------------------


class TestTheTreeMatchesTheAllowlist:
    def test_the_console_script_is_found(self):
        assert "motodiag.cli.main" in ENTRY_POINTS, (
            "if the entry point cannot be read, every module looks dead"
        )

    def test_no_new_unreachable_module(self):
        new = _current_unreachable() - set(UNREACHABLE_MODULES)
        assert not new, (
            "these modules cannot be reached from any entry point and are not "
            "in the allowlist. Wire them up, delete them, or record why:\n  "
            + "\n  ".join(sorted(new))
        )

    def test_no_stale_unreachable_entry(self):
        """A listed module that something now imports has been connected, and
        its entry is out of date. Leaving it would let the list rot."""
        stale = set(UNREACHABLE_MODULES) - _current_unreachable()
        assert not stale, (
            "these modules are now reachable -- remove them from "
            "UNREACHABLE_MODULES:\n  " + "\n  ".join(sorted(stale))
        )

    def test_no_new_orphan(self):
        new = _current_live_orphans() - set(ORPHANS)
        assert not new, (
            "these public definitions are referenced by no code anywhere else "
            "in src/ and are not in the allowlist:\n  "
            + "\n  ".join(sorted(new))
        )

    def test_no_stale_orphan_entry(self):
        stale = set(ORPHANS) - _current_live_orphans()
        assert not stale, (
            "these definitions now have a caller (or were removed) -- remove "
            "them from ORPHANS:\n  " + "\n  ".join(sorted(stale))
        )

    def test_the_known_scale(self):
        """The number this phase found. Pinned so a change to it is a
        deliberate edit someone has to explain, not drift."""
        assert len(UNREACHABLE_MODULES) == 38  # f9-noqa: ssot-pin fixture-data: Phase 209B's finding — 38 of 256 modules unreachable from any entry point on 2026-09-17. The literal is the record of what was found; the stale/new-entry tests above are what actually hold the tree to the list.


class TestEveryEntryExplainsItself:
    @pytest.mark.parametrize(
        "name,entry", sorted({**UNREACHABLE_MODULES, **ORPHANS}.items()),
    )
    def test_classification_and_reason(self, name, entry):
        classification, reason = entry
        assert classification in CLASSIFICATIONS, f"{name}: {classification!r}"
        assert len(reason.strip()) >= 20, (
            f"{name}: a reason under 20 characters is a label, not a reason"
        )

    @pytest.mark.parametrize(
        "name",
        sorted(n for n, (c, _) in UNREACHABLE_MODULES.items()
               if c == "substrate" and n.count(".") == 1),
    )
    def test_a_substrate_names_the_phase_it_waits_for(self, name):
        """A substrate is only legitimate while its phase has not landed.
        Naming the phase is what lets someone check."""
        _, reason = UNREACHABLE_MODULES[name]
        assert re.search(r"Phases? \d{2,3}", reason), (
            f"{name}: a substrate reason must name the phase it is waiting for"
        )

    def test_the_c2_layer_is_recorded_as_unwired_not_as_done(self):
        """The roadmap marks Track C2 complete. The allowlist must not."""
        c2 = [n for n in UNREACHABLE_MODULES if n.startswith("motodiag.media.")
              and not n.startswith("motodiag.media.sim")]
        assert c2 and all(UNREACHABLE_MODULES[n][0] == "unwired-feature" for n in c2)


class TestTheScannerIsNotFooled:
    """Synthetic trees, because the real one can only prove the scanner agrees
    with itself."""

    @pytest.fixture
    def tree(self, tmp_path):
        pkg = tmp_path / "src" / "demo"
        (pkg / "cli").mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "cli" / "__init__.py").write_text("")

        def write(rel, text):
            path = pkg / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            return path

        return tmp_path / "src", pkg, write

    def test_an_unimported_module_is_unreachable(self, tree):
        src, pkg, write = tree
        write("cli/main.py", "def cli():\n    pass\n")
        write("lonely.py", "def f():\n    pass\n")
        dead = find_unreachable_modules(src, "demo", {"demo.cli.main"})
        assert "demo.lonely" in dead

    def test_a_lazy_import_inside_a_function_is_an_edge(self, tree):
        """This codebase imports inside functions all the time to keep
        optional dependencies optional. Missing those would flag most of it."""
        src, pkg, write = tree
        write("cli/main.py",
              "def cli():\n    from demo import lazy\n    lazy.go()\n")
        write("lazy.py", "def go():\n    pass\n")
        assert "demo.lazy" not in find_unreachable_modules(
            src, "demo", {"demo.cli.main"})

    def test_an_island_is_unreachable_even_though_it_calls_itself(self, tree):
        """`scheduling`'s shape: every member used, by other members only."""
        src, pkg, write = tree
        write("cli/main.py", "def cli():\n    pass\n")
        write("island/__init__.py", "from demo.island.a import a\n")
        write("island/a.py", "from demo.island.b import b\ndef a():\n    b()\n")
        write("island/b.py", "def b():\n    pass\n")
        dead = find_unreachable_modules(src, "demo", {"demo.cli.main"})
        assert {"demo.island", "demo.island.a", "demo.island.b"} <= dead

    def test_a_dynamic_import_by_literal_is_an_edge(self, tree):
        src, pkg, write = tree
        write("cli/main.py",
              "import importlib\ndef cli():\n"
              "    importlib.import_module('demo.plugin')\n")
        write("plugin.py", "X = 1\n")
        assert "demo.plugin" not in find_unreachable_modules(
            src, "demo", {"demo.cli.main"})

    def test_a_post_apply_hook_is_an_edge(self, tree):
        """How migrations 055 and 056 reach their backfill modules."""
        src, pkg, write = tree
        write("cli/main.py", "from demo import migrations\n")
        write("migrations.py", "M = dict(post_apply='demo.backfill:run')\n")
        write("backfill.py", "def run(conn):\n    pass\n")
        assert "demo.backfill" not in find_unreachable_modules(
            src, "demo", {"demo.cli.main"})

    def test_an_import_named_only_in_a_comment_is_not_an_edge(self, tree):
        src, pkg, write = tree
        write("cli/main.py",
              "# we used to import_module('demo.ghost') here\n"
              "def cli():\n    pass\n")
        write("ghost.py", "X = 1\n")
        assert "demo.ghost" in find_unreachable_modules(
            src, "demo", {"demo.cli.main"})

    def test_a_function_mentioned_only_in_a_docstring_is_still_an_orphan(self, tree):
        """The dangerous direction. A description is not a call; this is the
        mention-vs-use family, and 19 real names in this tree fell into it."""
        src, pkg, write = tree
        write("cli/main.py",
              'def cli():\n    """See helper() for the details."""\n    pass\n')
        write("util.py", "def helper():\n    pass\n")
        assert "util.py::helper" in find_orphans(pkg)

    def test_a_called_function_is_not_an_orphan(self, tree):
        src, pkg, write = tree
        write("cli/main.py",
              "from demo.util import helper\ndef cli():\n    helper()\n")
        write("util.py", "def helper():\n    pass\n")
        assert "util.py::helper" not in find_orphans(pkg)

    def test_a_route_handler_is_not_an_orphan(self, tree):
        """The framework calls it; nothing in the tree has to."""
        src, pkg, write = tree
        write("cli/main.py", "def cli():\n    pass\n")
        write("routes.py",
              "@router.get('/x')\ndef handler():\n    pass\n")
        assert "routes.py::handler" not in find_orphans(pkg)

    def test_a_console_script_is_not_an_orphan(self):
        assert entry_points_from_pyproject(
            '[project.scripts]\nmotodiag = "motodiag.cli.main:cli"\n'
        ) == {"motodiag.cli.main"}

    def test_a_missing_entry_point_is_an_error_not_an_empty_answer(self, tree):
        """If the entry point is wrong, every module looks dead. That must be
        loud: 'everything is unreachable' reads like a finding."""
        src, pkg, write = tree
        with pytest.raises(ValueError, match="entry points not found"):
            find_unreachable_modules(src, "demo", {"demo.nope"})
