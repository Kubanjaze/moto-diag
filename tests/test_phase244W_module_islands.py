"""Phase 244W — the gate can see a module that only talks to itself.

Phase 209B's gate has three checks and 244U closed the first blind spot. This
is the second: a module whose public names refer only to each other, inside a
package that is otherwise alive. The import walk cannot see it (the package
init's import edge is real), the package-level island check cannot (the
package is alive), and the orphan count cannot — a class that names itself
counts as used, and a dead module naming another launders it.

`engine/history.py` and `engine/retrieval.py` — 668 lines, no caller — were
invisible to all three. Four independent design prototypes then converged on
19 modules / 4,270 lines, every one verified by hand.

Two decisions are pinned here because both could be quietly reversed:

* **the surface definition.** A module's public surface keeps its
  framework-decorated names and its constants. Reusing `_public_defs`, which
  strips route handlers, leaves a route module vacuously dead and everything
  it calls follows: 55 modules, 15,669 lines, measured.
* **the one seed.** The island set starts as the import walk's dead set.
  With every other seed rule stripped the answer does not change; without
  this one, a name collision with an already-dead module shields a second
  dead module (`add_item` in `pricing/repair_plan` hid `inventory/item_repo`).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pytest
from support.integration_gaps import (
    blank_prose_strings,
    entry_points_from_pyproject,
    find_module_islands,
    module_map,
)
from support.integration_gaps_allowlist import (
    CLASSIFICATIONS,
    MODULE_ISLANDS,
    ORPHANS,
    UNREACHABLE_MODULES,
)

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
PACKAGE_ROOT = SRC / "motodiag"
PYPROJECT = (REPO / "pyproject.toml").read_text(encoding="utf-8")
ENTRY_POINTS = entry_points_from_pyproject(PYPROJECT) | {"motodiag", "motodiag.api"}


@lru_cache(maxsize=1)
def _current() -> frozenset[str]:
    return frozenset(find_module_islands(SRC, "motodiag", ENTRY_POINTS))


# ---------------------------------------------------------------------------
# 1. The real tree
# ---------------------------------------------------------------------------


class TestTheTreeMatchesTheTable:
    def test_no_new_module_island(self):
        new = _current() - set(MODULE_ISLANDS)
        assert not new, (
            "modules no live code uses, not in MODULE_ISLANDS. Wire them up, "
            "delete them, or record why:\n  " + "\n  ".join(sorted(new))
        )

    def test_no_stale_module_island_entry(self):
        stale = set(MODULE_ISLANDS) - _current()
        assert not stale, (
            "something now uses these; remove them from MODULE_ISLANDS:\n  "
            + "\n  ".join(sorted(stale))
        )

    def test_a_module_called_only_from_a_route_handler_is_not_reported(self):
        """The false positive the first prototype produced: `dispatch_event`
        is called at api/routes/billing.py:188 and nowhere else."""
        assert "motodiag.billing.webhook_handlers" not in _current()

    def test_no_entry_surface_is_reported(self):
        surfaces = [m for m in _current()
                    if m.startswith(("motodiag.api.routes.", "motodiag.cli."))]
        assert surfaces == []

    def test_learning_hook_is_seen_through_the_string_literal(self):
        """Its only mention outside its init is prose in a migration
        description (core/migrations.py:545). Identifier counting alone
        called that a use."""
        assert "motodiag.feedback.learning_hook" in _current()

    def test_item_repo_is_seen_past_the_dead_collision(self):
        """`pricing/repair_plan.py:125` defines its own `add_item`, and
        `pricing` is already dead. Without the pre-seed that mention is a
        live referrer."""
        assert "motodiag.inventory.item_repo" in _current()
        assert "motodiag.pricing.repair_plan" in UNREACHABLE_MODULES or any(
            k.startswith("motodiag.pricing") for k in UNREACHABLE_MODULES
        )

    def test_it_reports_only_what_the_other_checks_do_not(self):
        assert not (_current() & set(UNREACHABLE_MODULES))

    def test_the_known_scale(self):
        assert len(MODULE_ISLANDS) == 14  # f9-noqa: → 13 (244Y deleted six superseded modules) → 14 (244Y: inventory/models surfaced as substrate once its last live import went);: ssot-pin fixture-data: Phase 244W's finding — 19 modules / 4,270 lines invisible to the gate on 2026-09-17, converged on by four independent designs. The new/stale tests above are what hold the tree to the list; this literal is the record of what was found.


# ---------------------------------------------------------------------------
# 2. The table explains itself, and the convention holds
# ---------------------------------------------------------------------------


class TestEveryEntryExplainsItself:
    @pytest.mark.parametrize("name,entry", sorted(MODULE_ISLANDS.items()))
    def test_classification_and_reason(self, name, entry):
        classification, reason = entry
        assert classification in CLASSIFICATIONS, f"{name}: {classification!r}"
        assert len(reason.strip()) >= 20, f"{name}: a label, not a reason"

    @pytest.mark.parametrize(
        "name", sorted(n for n, (c, _) in MODULE_ISLANDS.items() if c == "substrate"),
    )
    def test_every_substrate_names_the_phase_it_waits_for(self, name):
        """Stricter than 209B's version, which checks top-level packages
        only: every substrate module here names its row, so the entry goes
        stale — and fails — the day that row lands."""
        _, reason = MODULE_ISLANDS[name]
        assert re.search(r"Phases? \d{2,3}", reason), name

    def test_no_orphan_entry_inside_a_dead_module(self):
        """A dead file is one entry, not thirteen. Eleven of the entries this
        phase removed from ORPHANS were added by 244U one phase earlier; they
        are reclassified from dead name to dead file, not forgotten."""
        mods = module_map(SRC, "motodiag")
        island_files = {
            mods[m].relative_to(PACKAGE_ROOT).as_posix() for m in MODULE_ISLANDS
        }
        inside = sorted(k for k in ORPHANS if k.split("::")[0] in island_files)
        assert inside == [], f"listed twice: {inside}"

    def test_the_audit_scores_are_carried_not_invented(self):
        """The eight engine entries quote the 2026-09-17 audit's consensus.
        None is above 4.3: the phase that deletes or wires them inherits a
        number, not a mood."""
        engine = {k: v for k, v in MODULE_ISLANDS.items()
                  if k.startswith("motodiag.engine.") and k != "motodiag.engine.history"}
        assert len(engine) == 6  # 244Y deleted cost, evaluation, retrieval
        scored = [v[1] for v in engine.values() if "onsensus" in v[1]]
        assert len(scored) == len(engine), "every remaining engine entry carries its audit score"


# ---------------------------------------------------------------------------
# 3. Synthetic trees — the scanner is not fooled
# ---------------------------------------------------------------------------


@pytest.fixture
def tree(tmp_path):
    """209B's fixture shape: `demo.cli.main` is the entry point."""
    pkg = tmp_path / "src" / "demo"
    (pkg / "cli").mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "cli" / "__init__.py").write_text("")
    (pkg / "cli" / "main.py").write_text("def cli():\n    pass\n")

    def write(rel, text):
        path = pkg / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def islands():
        # The package root is an entry surface, as 209B's real-tree
        # ENTRY_POINTS says: `import demo` runs its __init__. Without it the
        # init is unreachable, everything only it imports is already dead,
        # and this check correctly declines to report what the import walk
        # already does.
        return find_module_islands(tmp_path / "src", "demo", {"demo.cli.main", "demo"})

    return write, islands


class TestTheBlindSpotItself:
    def test_a_class_that_names_itself_imported_only_by_an_init_is_reported(self, tree):
        """`CaseRetriever`'s shape: own=3, total=3, two self-references."""
        write, islands = tree
        write("__init__.py",
              "from demo.shelf import Sitter\n__all__ = ['Sitter']\n")
        write("shelf.py",
              "class Sitter:\n"
              "    @classmethod\n"
              "    def make(cls) -> 'Sitter':\n"
              "        return Sitter()\n")
        assert "demo.shelf" in islands()

    def test_a_dead_module_importing_a_dead_module_reports_both(self, tree):
        """`DiagnosticHistory`'s shape: three references, all from a file
        that is itself dead."""
        write, islands = tree
        write("__init__.py", "from demo.a import A\nfrom demo.b import B\n")
        write("a.py",
              "from demo.b import B\n\n\nclass A:\n"
              "    def go(self):\n        return B(), B()\n")
        write("b.py", "class B:\n    pass\n")
        assert {"demo.a", "demo.b"} <= islands()

    def test_the_stale_direction_a_caller_revives_the_module(self, tree):
        write, islands = tree
        write("__init__.py", "from demo.shelf import Sitter\n")
        write("shelf.py", "class Sitter:\n    pass\n")
        assert "demo.shelf" in islands()
        write("cli/main.py",
              "from demo.shelf import Sitter\n\n\ndef cli():\n    Sitter()\n")
        assert "demo.shelf" not in islands()


class TestWhatIsNotAnIsland:
    def test_a_module_called_only_from_a_route_handler(self, tree):
        """The real idiom: app.py includes `mod.router`, the handler calls
        the helper. The route module lives through `router`; the helper
        lives through the handler's body."""
        write, islands = tree
        write("cli/main.py", "from demo import app\n\n\ndef cli():\n    app.create()\n")
        write("app.py",
              "from demo.routes import billing\n\n\n"
              "def create():\n    return [billing.router]\n")
        write("routes/__init__.py", "")
        write("routes/billing.py",
              "from demo.handlers import dispatch\nrouter = object()\n\n\n"
              "def webhook():\n    return dispatch()\n")
        write("handlers.py", "def dispatch():\n    return 1\n")
        assert "demo.handlers" not in islands()
        assert "demo.routes.billing" not in islands()

    def test_module_object_access_is_a_use(self, tree):
        write, islands = tree
        write("cli/main.py", "from demo import util\n\n\ndef cli():\n    util.helper()\n")
        write("util.py", "def helper():\n    pass\n")
        assert "demo.util" not in islands()

    def test_a_lazy_import_inside_a_live_function_is_a_use(self, tree):
        write, islands = tree
        write("cli/main.py", "def cli():\n    from demo.lazy import go\n    go()\n")
        write("lazy.py", "def go():\n    pass\n")
        assert "demo.lazy" not in islands()

    def test_a_public_constant_keeps_a_module_alive(self, tree):
        """`hardware/scenarios::BUILTIN_NAMES`, imported at cli/hardware.py:61,
        is that module's only live name and it is not a def."""
        write, islands = tree
        write("cli/main.py",
              "from demo.names import BUILTIN\n\n\ndef cli():\n    return BUILTIN\n")
        write("names.py", "BUILTIN = ('a', 'b')\n\n\ndef builtin_path():\n    pass\n")
        assert "demo.names" not in islands()

    def test_an_aliased_import_is_a_use(self, tree):
        write, islands = tree
        write("cli/main.py",
              "from demo.sched import schedule as bay_schedule\n\n\n"
              "def cli():\n    bay_schedule()\n")
        write("sched.py", "def schedule():\n    pass\n")
        assert "demo.sched" not in islands()

    def test_an_annotation_is_a_use(self, tree):
        """41 pydantic request models in api/routes/ are referenced only as a
        handler's parameter annotation."""
        write, islands = tree
        write("cli/main.py",
              "from demo.models import Req\n\n\ndef cli(r: Req) -> Req:\n    return r\n")
        write("models.py", "class Req:\n    pass\n")
        assert "demo.models" not in islands()

    def test_a_signature_default_is_a_use(self, tree):
        write, islands = tree
        write("cli/main.py",
              "from demo.consts import INTERVAL\n\n\ndef cli(ms=INTERVAL):\n    return ms\n")
        write("consts.py", "INTERVAL = 250\n")
        assert "demo.consts" not in islands()

    def test_a_mention_inside_a_nested_def_is_a_use(self, tree):
        write, islands = tree
        write("cli/main.py",
              "def cli():\n    def inner():\n        from demo.deep import go\n"
              "        return go()\n    return inner\n")
        write("deep.py", "def go():\n    pass\n")
        assert "demo.deep" not in islands()

    def test_a_framework_subclass_added_by_the_app_is_a_use(self, tree):
        write, islands = tree
        write("cli/main.py",
              "from demo.middleware import RequestId\n\n\ndef cli():\n    return [RequestId]\n")
        write("middleware.py", "class RequestId(object):\n    def dispatch(self):\n        pass\n")
        assert "demo.middleware" not in islands()

    def test_a_module_with_no_public_surface_is_never_flagged(self, tree):
        """No name-level evidence either way; it may exist for a side effect.
        The import walk still reports it if nothing imports it."""
        write, islands = tree
        write("__init__.py", "from demo import effects\n")
        write("effects.py", "_registry = {}\n_registry['x'] = 1\n")
        assert "demo.effects" not in islands()

    def test_a_dotted_path_string_is_left_alone(self, tree):
        """A `post_apply="mod:attr"`-shaped literal has no space and is not
        prose; the name inside it still counts."""
        write, islands = tree
        write("cli/main.py", "HOOK = 'demo.hook:run'\n\n\ndef cli():\n    return HOOK\n")
        write("hook.py", "def run():\n    pass\n")
        assert "demo.hook" not in islands()


class TestMentionIsNotUse:
    def test_a_docstring_mention_is_not_a_use(self, tree):
        write, islands = tree
        write("__init__.py", "from demo.shelf import Sitter\n")
        write("shelf.py", "class Sitter:\n    pass\n")
        write("cli/main.py", 'def cli():\n    """Uses Sitter, honestly."""\n')
        assert "demo.shelf" in islands()

    def test_a_prose_string_mention_is_not_a_use(self, tree):
        """`learning_hook`'s shape: the name appears in a migration's
        description string and nowhere else."""
        write, islands = tree
        write("__init__.py", "from demo.hook import Reader\n")
        write("hook.py", "class Reader:\n    pass\n")
        write("cli/main.py",
              "NOTE = 'phases 318-327 consume this via Reader read-only hook.'\n"
              "\n\ndef cli():\n    return NOTE\n")
        assert "demo.hook" in islands()

    def test_a_name_collision_with_a_dead_module_does_not_shield(self, tree):
        """The one seed that matters. `dead.py` is unreachable and defines
        its own `add_item`; `repo.py` must still be an island."""
        write, islands = tree
        write("__init__.py", "from demo.repo import add_item\n")
        write("repo.py", "def add_item():\n    pass\n")
        write("dead.py", "def add_item():\n    pass\n\n\ndef plan():\n    add_item()\n")
        assert "demo.repo" in islands()
        assert "demo.dead" not in islands(), "already reported by the import walk"


class TestTheCheckComposes:
    def test_a_missing_entry_point_is_an_error_not_an_empty_answer(self, tree):
        write, _ = tree
        with pytest.raises(ValueError):
            find_module_islands(REPO / "nowhere", "demo", {"demo.cli.main"})

    def test_the_already_dead_set_is_not_re_reported(self, tree):
        write, islands = tree
        write("lonely.py", "def f():\n    pass\n")
        assert "demo.lonely" not in islands()


# ---------------------------------------------------------------------------
# 4. Prose strings
# ---------------------------------------------------------------------------


class TestProseStringBlanking:
    def test_a_spaced_literal_is_blanked(self):
        out = blank_prose_strings('msg = "consume this via Reader read-only hook."\n')
        assert "Reader" not in out
        assert 'msg = "' in out, "the string stays a string"

    def test_a_dotted_path_is_kept(self):
        src = 'hook = "demo.knowledge.loader:backfill"\n'
        assert blank_prose_strings(src) == src

    def test_an_f_string_expression_stays_code(self):
        out = blank_prose_strings('m = f"update_adapter got unknown fields: {sorted(unknown)!r}"\n')
        assert "update_adapter" not in out
        assert "sorted(unknown)" in out

    def test_unparseable_source_is_returned_unchanged(self):
        src = 'x = "unterminated\n'
        assert blank_prose_strings(src) == src

    def test_positions_are_preserved(self):
        """Blanking must not move anything: the loader's other passes and
        the identifier index assume the text keeps its shape."""
        src = 'a = "two words"\nb = a\n'
        assert len(blank_prose_strings(src)) == len(src)
