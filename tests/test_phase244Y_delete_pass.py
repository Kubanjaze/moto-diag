"""Phase 244Y — dead code leaves with its evidence.

The first phase that acts on what four phases of instrument work report.
Every `superseded` entry across the three allowlist tables — the allowlist's
own word for a removal candidate — plus the two engine modules the
2026-09-17 audit named for deletion with no dissent: seven modules and
twelve defs, 1,904 source lines, each with a table entry naming its live
replacement and its line count printed in the plan before anything moved.

Two things the mutation run taught, pinned here:

* **The gate suites are static.** They read files; they never import the
  package. A dead re-export left in `engine/__init__` passed all three of
  them (mutation M3) and would only have died in the full regression. So
  this file imports every package whose init was pruned — the check that had
  been run by hand after every step, made into a test.
* **The gate finds the second order only after the first is gone.** With the
  deleted code out, three names whose only callers had just left surfaced as
  new orphans. Two were cascade-deleted; one, a data model for a live table,
  joined its siblings on the list.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from support.integration_gaps_allowlist import MODULE_ISLANDS, ORPHANS, UNREACHABLE_MODULES
from support.source_guards import code_of

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src" / "motodiag"

DELETED_MODULES = [
    "motodiag.engine.cost", "motodiag.engine.evaluation", "motodiag.engine.history",
    "motodiag.engine.retrieval", "motodiag.auth.roles_repo", "motodiag.cli.registry",
    "motodiag.hardware.protocols.models",
]
DELETED_DEFS = {
    "motodiag.engine.symptoms": ["SymptomAnalyzer", "assess_urgency", "build_differential_prompt"],
    "motodiag.cli.subscription": ["has_feature", "requires_tier", "TierAccessDenied"],
    "motodiag.inventory.recall_repo": ["add_recall", "get_recall", "list_recalls", "delete_recall"],
    "motodiag.accounting.invoice_repo": ["recalculate_invoice_totals"],
    "motodiag.shop.extracted_symptom_repo": ["create_extracted_symptom"],
}
PRUNED_INITS = [
    "motodiag.engine", "motodiag.auth", "motodiag.hardware", "motodiag.hardware.protocols",
    "motodiag.inventory", "motodiag.accounting",
]


# ---------------------------------------------------------------------------
# 1. What left, and what the tree does about it
# ---------------------------------------------------------------------------


class TestTheCodeIsGone:
    @pytest.mark.parametrize("module", DELETED_MODULES)
    def test_a_deleted_module_cannot_be_imported(self, module):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module)

    @pytest.mark.parametrize(
        "module,name", [(m, n) for m, ns in DELETED_DEFS.items() for n in ns],
    )
    def test_a_deleted_def_is_not_on_its_module(self, module, name):
        assert not hasattr(importlib.import_module(module), name), f"{module}.{name} is back"

    def test_the_files_are_not_on_disk(self):
        for m in DELETED_MODULES:
            assert not (SRC / (m.replace("motodiag.", "").replace(".", "/") + ".py")).exists(), m


class TestEveryPrunedPackageStillImports:
    """Mutation M3: a `from motodiag.engine.history import DiagnosticHistory`
    left in `engine/__init__` passed every static gate suite. Only an import
    catches it, so this is the import."""

    @pytest.mark.parametrize("package", PRUNED_INITS)
    def test_the_package_imports(self, package):
        importlib.import_module(package)

    @pytest.mark.parametrize("package", PRUNED_INITS)
    def test_star_import_names_nothing_that_is_gone(self, package):
        """`__all__` naming a missing attribute only fails on `import *`."""
        mod = importlib.import_module(package)
        for name in getattr(mod, "__all__", []):
            assert hasattr(mod, name), f"{package}.__all__ names {name}, which does not exist"


class TestWhatSurvivedIsIntact:
    @pytest.mark.parametrize("module,name", [
        # live: media/transcript_extraction
        ("motodiag.engine.symptoms", "categorize_symptoms"),
        # live: advanced/recall_repo.py delegates to it
        ("motodiag.inventory.recall_repo", "list_recalls_for_vehicle"),
        # kept: 45 tests call it
        ("motodiag.memory.compile", "compile_vehicle"),
        ("motodiag.memory.compile", "compile_all"),
        ("motodiag.cli.subscription", "current_tier"),
        ("motodiag.cli.subscription", "get_enforcement_mode"),
        ("motodiag.accounting.invoice_repo", "create_invoice"),
        ("motodiag.shop.extracted_symptom_repo", "confirm_extracted_symptom"),
    ])
    def test_a_surviving_name_is_present(self, module, name):
        assert hasattr(importlib.import_module(module), name)

    def test_the_live_recall_repo_still_delegates(self):
        """S0-4: the file 244X had called a duplicate keeps the one function
        the Phase 155 repo imports lazily."""
        code = code_of(SRC / "advanced/recall_repo.py")
        assert "from motodiag.inventory.recall_repo import list_recalls_for_vehicle" in code

    def test_base_py_no_longer_points_at_the_deleted_models(self):
        src = (SRC / "hardware/protocols/base.py").read_text(encoding="utf-8")
        assert "protocols.models" not in src  # raw-source-ok: the references lived in Sphinx docstrings by design


# ---------------------------------------------------------------------------
# 2. The allowlist and the gates
# ---------------------------------------------------------------------------


class TestTheListsLetGo:
    def test_no_table_names_a_deleted_module(self):
        for m in DELETED_MODULES:
            assert m not in MODULE_ISLANDS and m not in UNREACHABLE_MODULES, m

    def test_no_orphan_entry_names_a_deleted_def(self):
        gone = {
            f"{m.replace('motodiag.', '').replace('.', '/')}.py::{n}"
            for m, ns in DELETED_DEFS.items() for n in ns
        }
        left = sorted(gone & set(ORPHANS))
        assert left == [], left

    def test_the_second_order_model_joined_its_siblings(self):
        """`Permission`: a data model for the live permissions table, whose
        only constructor was the deleted roles_repo. Its four siblings were
        already `public-api`; it is classified the same way, not deleted."""
        cls, reason = ORPHANS["auth/models.py::Permission"]
        assert cls == "public-api"
        assert "244Y" in reason

    def test_the_compile_wrappers_are_kept_not_superseded(self):
        for fn in ("compile_vehicle", "compile_all"):
            cls, reason = ORPHANS[f"memory/compile.py::{fn}"]
            assert cls == "public-api"
            assert "45 tests" in reason

    def test_the_known_scale(self):
        assert len(MODULE_ISLANDS) == 14  # f9-noqa: ssot-pin fixture-data: 19 → 13 at Phase 244Y (six superseded modules deleted) → 14 (inventory/models surfaced as a third-order island once its last live import went; substrate). The new/stale tests in test_phase244W hold the tree to the list; this literal records the drop.
        assert len(UNREACHABLE_MODULES) == 37  # f9-noqa: ssot-pin fixture-data: 38 → 37 at Phase 244Y (cli/registry deleted).


class TestTheGatesSayWhatChanged:
    @pytest.mark.parametrize("gate", [
        "test_phase95_gate3_integration.py", "test_phase133_gate_5.py", "test_phase121_gate_r.py",
    ])
    def test_an_edited_gate_carries_the_note(self, gate):
        """Three gate tests were edited. Each says so in its docstring, so
        the next reader does not wonder where the tests went."""
        src = (REPO / "tests" / gate).read_text(encoding="utf-8")
        assert "Phase 244Y removed" in src  # raw-source-ok: the note is a docstring, which is the point
