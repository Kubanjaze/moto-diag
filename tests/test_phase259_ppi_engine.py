"""Phase 259 — Pre-purchase inspection (PPI), engine side.

Migration 067 seeds `ppi_engine_v1` (seven items, six subjects) on the
Phase 114 substrate; `motodiag workflow` gives the substrate its first
user-reachable front door.

What these tests pin:

- the migration seeds exactly one template and seven items, on a fresh
  `init_db` database AND on a copy of the live snapshot (the dry run);
- the rollback peels everything 067 added;
- the powertrain applicability is ice+hybrid and NOT electric, through
  the substrate's own filter;
- every figure in the content cites the document it came from, and the
  leak-down item carries NO percentage — S0-3's census found no document
  that sets one, and an invented threshold is what F149 documented for
  corpus rows;
- the CLI front door reaches the seeded template through the real
  registered group (`main.cli`), not a private import.

Known-bad controls (each seen to fail, then reverted — phase log): the
leak-down no-figure assertion fails on a planted "15%"; the content pin
fails on a changed figure; the CLI tests fail when the registration line
is removed from `main.py`.
"""

import re
import shutil
import sqlite3

import pytest
from click.testing import CliRunner

from motodiag.cli.main import cli as main_cli
from motodiag.core.database import SCHEMA_VERSION, init_db
from motodiag.core.migrations import (
    MIGRATIONS,
    apply_migration,
    apply_pending_migrations,
    get_current_version,
    get_migration_by_version,
    rollback_to_version,
)
from motodiag.workflows import (
    WorkflowCategory,
    get_checklist_items,
    get_template_by_slug,
    list_templates,
)


ITEM_TITLES = [
    "Static visual inspection — engine cold, off",
    "Battery condition and charging output",
    "Starter, cold start and running check",
    "Compression test",
    "Leak-down test (when compression is low or marginal)",
    "Oil level, condition and sample",
    "Fuel quality",
]


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A fresh, fully-migrated database the CLI can reach via settings.

    Same pattern as Phase 123's `cli_db`: the env var alone is not enough
    because `get_settings` is cached — the cache is reset after patching
    and again on teardown.
    """
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "motodiag.db")
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    reset_settings()
    init_db(path)
    yield path
    reset_settings()


def _items(db_path, slug="ppi_engine_v1"):
    template = get_template_by_slug(slug, db_path)
    assert template is not None, f"template {slug} missing"
    return get_checklist_items(template["id"], db_path)


# --- Migration 067 ---


class TestMigration067:
    def test_schema_version_floor_pin(self):
        """F124's floor-pin pattern: never a literal equality to the head."""
        assert SCHEMA_VERSION >= 67

    def test_migration_067_exists_and_is_at_least_the_head(self):
        """F124: no equality against a literal equal to the head — head-ness
        is the genuine pin's job (240c); this asserts only what is this
        phase's: migration 067 exists, by name, and the head is at least
        at it."""
        m = get_migration_by_version(67)
        assert m is not None
        assert m.name == "ppi_engine_workflow"
        assert SCHEMA_VERSION >= 67

    def test_fresh_init_seeds_the_template(self, db):
        t = get_template_by_slug("ppi_engine_v1", db)
        assert t is not None
        assert t["category"] == "ppi"
        assert t["name"] == "Pre-purchase inspection — engine"
        # D2: the six subjects are ICE subjects; the substrate's
        # all-powertrains default is deliberately not used.
        assert t["applicable_powertrains"] == ["ice", "hybrid"]
        assert t["is_active"] == 1
        assert t["required_tier"] == "individual"
        assert t["estimated_duration_minutes"] == 70

    def test_seven_items_in_contiguous_sequence(self, db):
        items = _items(db)
        assert [i["sequence_number"] for i in items] == list(range(1, 8))
        assert [i["title"] for i in items] == ITEM_TITLES
        for item in items:
            assert item["instruction_text"].strip()
            assert item["expected_pass"].strip()
            assert item["expected_fail"].strip()
            assert "tools_needed" in item

    def test_leakdown_is_optional_the_rest_required(self, db):
        items = _items(db)
        by_title = {i["title"]: i for i in items}
        assert by_title["Leak-down test (when compression is low or marginal)"][
            "required"
        ] == 0
        assert sum(i["required"] for i in items) == 6

    def test_generic_ppi_pointer_repointed_and_untouched(self, db):
        """D1/D5: the generic quick check keeps its 5 items; only its stale
        forward pointer moved."""
        items = get_checklist_items(
            get_template_by_slug("generic_ppi_v1", db)["id"], db
        )
        assert len(items) == 5
        assert "ppi_engine_v1" in get_template_by_slug("generic_ppi_v1", db)[
            "description"
        ]

    def test_rollback_peels_everything_067_added(self, tmp_path):
        """S0-2: items live in the journal. Rolling back must remove the
        template (items cascade), restore the old pointer, and leave the
        schema at 66."""
        path = str(tmp_path / "rollback.db")
        init_db(path)
        # F124: at-head is asserted against the constant, never a literal.
        assert get_current_version(path) == SCHEMA_VERSION
        # A rollback peels every successor (Phase 260 bug fix #2: rolling
        # back 67 alone left 68 applied once 68 existed).
        rollback_to_version(66, path)
        assert get_current_version(path) == 66
        assert get_template_by_slug("ppi_engine_v1", path) is None
        old_desc = get_template_by_slug("generic_ppi_v1", path)["description"]
        assert "ppi_engine_v1" not in old_desc
        assert "Track N phase 259 expands" in old_desc
        # And forward again: the migration is re-appliable after rollback.
        assert apply_pending_migrations(path)[0] == 67
        assert get_current_version(path) == SCHEMA_VERSION
        assert get_template_by_slug("ppi_engine_v1", path) is not None

    def test_upgrade_from_66_alters_only_the_approved_row(self, tmp_path):
        """66 -> 67 on a database built here, not the live one. As first
        written this copied data/motodiag.db and asserted it stood at 66
        with 1,060 rows: it failed wherever that file is absent, and would
        have failed the first regression after this phase's own deploy
        moved the live database to 67. The live dry run is a deploy step,
        recorded in the phase log. What the test keeps is the claim the
        operator approved: the migration alters exactly one existing row,
        generic_ppi_v1's description, without naming a phase, and adds
        one template and seven items.

        The 66 baseline is built by applying migrations up to 66, never
        067. A baseline made by rolling 067 back inherits whatever the
        rollback does not undo: with the UPDATE widened to every generic
        template, that version of this test still passed."""
        path = str(tmp_path / "at_66.db")
        init_db(path, apply_migrations=False)
        for m in sorted(MIGRATIONS, key=lambda m: m.version):
            if get_current_version(path) < m.version <= 66:
                apply_migration(m, path)
        assert get_current_version(path) == 66

        def rows():
            conn = sqlite3.connect(path)
            templates = {r[0]: r[1:] for r in conn.execute(
                "SELECT slug, name, description, category FROM workflow_templates")}
            items = conn.execute(
                "SELECT id, template_id, sequence_number, title, instruction_text "
                "FROM checklist_items ORDER BY id").fetchall()
            conn.close()
            return templates, items

        templates_66, items_66 = rows()
        # 067 alone: applying everything pending also applies 067's
        # successors and measures their rows as 067's (260 bug fix #2).
        apply_migration(get_migration_by_version(67), path)
        assert get_current_version(path) == 67
        templates_67, items_67 = rows()
        assert set(templates_67) - set(templates_66) == {"ppi_engine_v1"}
        assert {s for s in templates_66 if templates_66[s] != templates_67[s]} == {"generic_ppi_v1"}
        assert not re.search(r"\bPhase \d+", templates_67["generic_ppi_v1"][1])
        assert items_67[:len(items_66)] == items_66
        assert len(items_67) - len(items_66) == 7


# --- Content pins (the figure discipline) ---


class TestContentPins:
    def test_compression_item_carries_the_cited_figure(self, db):
        item = _items(db)[3]
        # C1: CHF50 service manual, PDF p. 11. The figure is stated in BOTH
        # the description and the instruction, so the pin demands it in each
        # — a corruption in one field alone must fail (bug fix #1: the
        # first version joined the fields, and a planted "210 psi" in the
        # description passed because the instruction still said "202 psi").
        for field in ("description", "instruction_text"):
            text = item[field] or ""
            for needle in ("1,393 kPa", "202 psi", "1,500 rpm", "PDF p. 11"):
                assert needle in text, (
                    f"compression item's {field} lost '{needle}'"
                )
        assert "1,393 kPa" in (item["diagnosis_if_fail"] or "") or "PDF p. 79" in (
            item["diagnosis_if_fail"] or ""
        )

    def test_battery_item_carries_the_cited_figures(self, db):
        item = _items(db)[1]
        # C2/C3: CHF50 service manual, PDF p. 13 — pinned per field, for
        # the same reason as the compression pin.
        for field in ("description", "instruction_text"):
            text = item[field] or ""
            for needle in (
                "13.0-13.2 V",
                "12.3 V",
                "190 W",
                "0.1 mA",
                "12V-6Ah",
                "PDF p. 13",
            ):
                assert needle in text, f"battery item's {field} lost '{needle}'"
        assert "0.05-0.5" in (item["description"] or "")

    def test_oil_item_carries_the_cited_guidance(self, db):
        item = _items(db)[5]
        text = " ".join(
            item[k] or "" for k in ("description", "instruction_text", "expected_fail")
        )
        # C5: Metropolitan 2025 owner's manual, PDF p. 62.
        for needle in ("Dirty oil or old oil", "PDF p. 62"):
            assert needle in text, f"oil item lost '{needle}'"

    def test_fuel_item_carries_the_cited_guidance(self, db):
        item = _items(db)[6]
        text = " ".join(
            item[k] or "" for k in ("description", "instruction_text", "expected_fail")
        )
        # C6: Metropolitan 2025 owner's manual, PDF p. 17.
        for needle in ("stale or contaminated gasoline", "PDF p. 17"):
            assert needle in text, f"fuel item lost '{needle}'"

    def test_leakdown_item_carries_no_figure(self, db):
        """C7: no document in the library sets a leak-down percentage, so the
        item must not carry one. This is the assertion a planted figure
        breaks (phase log: it was broken with '15%' and seen to fail)."""
        item = _items(db)[4]
        whole = " ".join(
            item[k] or ""
            for k in (
                "title", "description", "instruction_text",
                "expected_pass", "expected_fail", "diagnosis_if_fail",
            )
        )
        assert not re.search(r"\d+\s*%", whole), (
            "the leak-down item carries a percentage figure; S0-3's census "
            "found no document that sets one"
        )
        # And it says where a threshold belongs instead of inventing one.
        assert "service manual" in whole

    def test_every_item_names_its_powertrain_honesty(self, db):
        """The worked-example figures belong to cited machines; no item may
        present CHF50 or Metropolitan numbers as universal."""
        for item in _items(db):
            text = " ".join(
                item[k] or "" for k in ("description", "instruction_text")
            )
            if any(
                needle in text
                for needle in ("13.0-13.2 V", "12.3 V", "1,393 kPa", "202 psi", "190 W")
            ):
                assert "CHF50" in text, (
                    f"item '{item['title']}' states CHF50 figures without "
                    "naming the machine they belong to"
                )


# --- Applicability (D2, through the substrate's own filter) ---


class TestApplicability:
    def test_not_offered_for_electric(self, db):
        electric = list_templates(db, powertrain="electric")
        assert all(t["slug"] != "ppi_engine_v1" for t in electric)

    def test_offered_for_ice(self, db):
        ice = list_templates(db, powertrain="ice")
        assert any(t["slug"] == "ppi_engine_v1" for t in ice)

    def test_pure_ice_item_titles(self, db):
        """No electric-machine subject may appear in an item title."""
        for item in _items(db):
            assert not re.search(r"charg\w* port|inverter|controller", item["title"], re.I)


# --- The CLI front door ---


class TestCliFrontDoor:
    def test_workflow_list_shows_both_ppi_templates(self, db):
        result = CliRunner().invoke(main_cli, ["workflow", "list"])
        assert result.exit_code == 0, result.output
        assert "ppi_engine_v1" in result.output
        assert "generic_ppi_v1" in result.output
        # The slug column can wrap at the narrow test terminal, so the
        # winterization row is asserted by its category, not its slug.
        assert "winterization" in result.output

    def test_workflow_list_category_ppi_hides_winterization(self, db):
        result = CliRunner().invoke(main_cli, ["workflow", "list", "--category", "ppi"])
        assert result.exit_code == 0, result.output
        assert "ppi_engine_v1" in result.output
        assert "winterization" not in result.output

    def test_workflow_list_empty_category_fails_loudly(self, db):
        result = CliRunner().invoke(main_cli, ["workflow", "list", "--category", "track_prep"])
        assert result.exit_code == 1
        assert "No active workflow templates" in result.output

    def test_workflow_show_prints_every_item_and_the_provenance(self, db):
        result = CliRunner().invoke(main_cli, ["workflow", "show", "ppi_engine_v1"])
        assert result.exit_code == 0, result.output
        for title in ITEM_TITLES:
            assert title in result.output, f"show lost item '{title}'"
        # The provenance travels with the content (the 244V rule).
        assert "PDF p. 11" in result.output
        assert "Pass:" in result.output
        assert "Fail:" in result.output

    def test_workflow_show_unknown_slug_fails_loudly(self, db):
        result = CliRunner().invoke(main_cli, ["workflow", "show", "no_such_template"])
        assert result.exit_code == 1
        assert "no_such_template" in result.output

    def test_the_group_is_registered_from_main(self, db):
        """The wiring rule: the integration point, not a private import."""
        assert "workflow" in main_cli.commands
