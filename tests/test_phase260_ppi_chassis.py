"""Phase 260 — Pre-purchase inspection (PPI), chassis side.

Migration 068 seeds `ppi_chassis_v1` (seven items, the ROADMAP row's seven
subjects) on the Phase 114 substrate, and re-points `ppi_engine_v1`'s
description — whose seeded text ended with the build reference "the
chassis protocol is Phase 260" (the F158 review miss) — at the new
template by name. No new module: `motodiag workflow list/show`, built in
259, renders the new template.

What these tests pin:

- the migration seeds exactly one template and seven items on a fresh
  `init_db` database, and alters exactly one existing row
  (`ppi_engine_v1`'s description, the operator-approved option-1 shape
  from 259's review);
- the rollback peels everything 068 added, restoring the seeded
  description verbatim;
- the powertrain applicability is ALL THREE powertrains — chassis
  subjects are powertrain-agnostic, unlike 259's ICE-only engine protocol;
- every figure in the content cites the document it came from, per field;
- the frame and swingarm items carry NO measurement figure — S0-3's
  censuses found no document that sets one (frame alignment, swingarm
  play, wheel-bearing play), and an invented threshold is what F149
  documented for corpus rows;
- no text this phase touches carries a build reference (F158), and the
  regex is exercised against a planted "Phase 999" so it cannot be S4.

Known-bad controls (each seen to fail, then reverted — phase log): the
frame no-figure assertion fails on a planted "0.5 mm"; the per-field pin
fails on a figure corrupted in one field only; the F158 pin fails on a
planted "Phase 999"; the re-point pin fails when the UPDATE is removed.
"""

import re
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
    rollback_migration,
)
from motodiag.workflows import (
    get_checklist_items,
    get_template_by_slug,
    list_templates,
)


ITEM_TITLES = [
    "Frame, straightness and crash evidence",
    "Steering head bearings",
    "Front fork — seals, stanchions and action",
    "Swingarm, linkage and rear suspension",
    "Wheel bearings and rims",
    "Brakes — pads or shoes, drums, discs and levers",
    "Tires — tread, pressure, damage and age",
]

# The no-figure items: nothing in the library sets a tolerance for these
# two subjects (step 0's C15/C16), so the content must not carry one.
NO_FIGURE_TITLES = {
    "Frame, straightness and crash evidence",
    "Swingarm, linkage and rear suspension",
}


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A fresh, fully-migrated database the CLI can reach via settings
    (Phase 123's `cli_db` pattern: the settings cache is reset around the
    env patch)."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "motodiag.db")
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    reset_settings()
    init_db(path)
    yield path
    reset_settings()


def _items(db_path, slug="ppi_chassis_v1"):
    template = get_template_by_slug(slug, db_path)
    assert template is not None, f"template {slug} missing"
    return get_checklist_items(template["id"], db_path)


def _whole_item(item):
    return " ".join(
        item[k] or ""
        for k in (
            "title", "description", "instruction_text",
            "expected_pass", "expected_fail", "diagnosis_if_fail",
        )
    )


# --- Migration 068 ---


class TestMigration068:
    def test_schema_version_floor_pin(self):
        """F124's floor-pin pattern: never a literal equality to the head."""
        assert SCHEMA_VERSION >= 68

    def test_migration_068_exists_by_name(self):
        """F124: head-ness is the genuine pin's job (240c); this asserts
        only what is this phase's: migration 068 exists, by name."""
        m = get_migration_by_version(68)
        assert m is not None
        assert m.name == "ppi_chassis_workflow"
        assert SCHEMA_VERSION >= 68

    def test_fresh_init_seeds_the_template(self, db):
        t = get_template_by_slug("ppi_chassis_v1", db)
        assert t is not None
        assert t["category"] == "ppi"
        assert t["name"] == "Pre-purchase inspection — chassis"
        # D2 (S0-4): chassis subjects exist on an electric machine as
        # much as an ICE one — all three powertrains, unlike 259's
        # engine protocol.
        assert t["applicable_powertrains"] == ["ice", "electric", "hybrid"]
        assert t["is_active"] == 1
        assert t["required_tier"] == "individual"
        assert t["estimated_duration_minutes"] == 80

    def test_seven_items_in_contiguous_sequence(self, db):
        items = _items(db)
        assert [i["sequence_number"] for i in items] == list(range(1, 8))
        assert [i["title"] for i in items] == ITEM_TITLES
        for item in items:
            assert item["instruction_text"].strip()
            assert item["expected_pass"].strip()
            assert item["expected_fail"].strip()
            assert "tools_needed" in item

    def test_all_items_required(self, db):
        """D4: chassis has no conditional item (the engine protocol's
        leak-down is the optional one)."""
        assert sum(i["required"] for i in _items(db)) == 7

    def test_ppi_engine_pointer_repointed(self, db):
        """D3: the F158 review miss. The engine template's description
        named the chassis protocol by phase number; it now names it by
        slug, and the phase number is gone."""
        desc = get_template_by_slug("ppi_engine_v1", db)["description"]
        assert "for the full chassis-side protocol see ppi_chassis_v1" in desc
        assert "Phase 260" not in desc
        # The rest of the description is 067's text, unchanged.
        assert desc.startswith("Engine-side protocol for buying a used ICE")
        assert "nothing here is invented" in desc

    def test_generic_templates_untouched(self, db):
        """The migration's UPDATE is scoped to ppi_engine_v1: the generic
        PPI keeps 259's re-pointed description, and the winterization
        template keeps its own (F158's known offender — not this phase's)."""
        generic = get_template_by_slug("generic_ppi_v1", db)
        assert len(get_checklist_items(generic["id"], db)) == 5
        assert (
            "For the full engine-side protocol see ppi_engine_v1."
            in generic["description"]
        )
        winter = get_template_by_slug("generic_winterization_v1", db)
        assert len(get_checklist_items(winter["id"], db)) == 4

    def test_rollback_peels_everything_068_added(self, tmp_path):
        """Items live in the journal. Rolling back must remove the
        template (items cascade), restore ppi_engine_v1's seeded
        description verbatim, and leave the schema at 67 — a fixture
        state below the head, so a literal is legal here (F124)."""
        path = str(tmp_path / "rollback.db")
        init_db(path)
        # F124: at-head is asserted against the constant, never a literal.
        assert get_current_version(path) == SCHEMA_VERSION
        rollback_migration(get_migration_by_version(68), path)
        assert get_current_version(path) == 67
        assert get_template_by_slug("ppi_chassis_v1", path) is None
        engine = get_template_by_slug("ppi_engine_v1", path)
        assert engine is not None
        assert "the chassis protocol is Phase 260" in engine["description"]
        # And forward again: the migration is re-appliable after rollback.
        assert apply_pending_migrations(path) == [68]
        assert get_template_by_slug("ppi_chassis_v1", path) is not None
        assert len(_items(path)) == 7

    def test_upgrade_from_67_alters_only_the_approved_row(self, tmp_path):
        """67 -> 68 on a database built here, never a copy of
        data/motodiag.db (the 259 lesson, bug fix #3: a test that reads
        the live snapshot fails wherever the snapshot is absent). The
        67 baseline is built by applying migrations up to 67, never 068
        — a baseline built by rolling 068 back inherits whatever the
        rollback does not undo."""
        path = str(tmp_path / "at_67.db")
        init_db(path, apply_migrations=False)
        for m in sorted(MIGRATIONS, key=lambda m: m.version):
            if get_current_version(path) < m.version <= 67:
                apply_migration(m, path)
        assert get_current_version(path) == 67

        def rows():
            conn = sqlite3.connect(path)
            templates = {r[0]: r[1:] for r in conn.execute(
                "SELECT slug, name, description, category FROM workflow_templates")}
            items = conn.execute(
                "SELECT id, template_id, sequence_number, title, instruction_text "
                "FROM checklist_items ORDER BY id").fetchall()
            conn.close()
            return templates, items

        templates_67, items_67 = rows()
        assert apply_pending_migrations(path) == [68]
        templates_68, items_68 = rows()
        assert set(templates_68) - set(templates_67) == {"ppi_chassis_v1"}
        assert {
            s for s in templates_67 if templates_67[s] != templates_68[s]
        } == {"ppi_engine_v1"}
        assert not re.search(
            r"\bPhase \d+\b", templates_68["ppi_engine_v1"][1]
        ), "the re-pointed description still names a phase"
        assert items_68[: len(items_67)] == items_67
        assert len(items_68) - len(items_67) == 7


# --- Content pins (the figure discipline) ---


class TestContentPins:
    """259's bug fix #1 lesson: a pin that joins an item's fields lets a
    corrupted figure in one field pass because another still carries it.
    These pins demand each needle in each field that states it."""

    def test_steering_item_carries_the_cited_figures(self, db):
        item = _items(db)[1]
        for needle in ("PDF p. 93", "PDF p. 76", "gently rock the front fork"):
            assert needle in (item["description"] or ""), (
                f"steering item's description lost '{needle}'"
            )
        for needle in (
            "38 N·m", "14 N·m", "PDF p. 76", "PDF p. 93", "PDF p. 94",
        ):
            assert needle in (item["instruction_text"] or ""), (
                f"steering item's instruction lost '{needle}'"
            )

    def test_fork_item_carries_the_cited_figures(self, db):
        item = _items(db)[2]
        for needle in (
            "252.1 mm", "247 mm", "0.2 mm", "PDF p. 95", "PDF p. 34",
        ):
            assert needle in (item["description"] or ""), (
                f"fork item's description lost '{needle}'"
            )
        for needle in ("PDF p. 95",):
            assert needle in (item["instruction_text"] or ""), (
                f"fork item's instruction lost '{needle}'"
            )
        for needle in (
            "252.1 mm", "247 mm", "0.2 mm", "128.5 mm", "125.9 mm",
            "PDF p. 34", "PDF p. 12",
        ):
            assert needle in (item["diagnosis_if_fail"] or ""), (
                f"fork item's diagnosis lost '{needle}'"
            )

    def test_wheels_item_carries_the_cited_figures(self, db):
        item = _items(db)[4]
        for needle in (
            "0.20 mm", "2.0 mm", "PDF p. 55", "PDF p. 218", "PDF p. 314",
        ):
            assert needle in (item["description"] or ""), (
                f"wheels item's description lost '{needle}'"
            )
        for needle in (
            "0.20 mm", "2.0 mm", "PDF p. 314", "PDF p. 55",
        ):
            assert needle in (item["instruction_text"] or ""), (
                f"wheels item's instruction lost '{needle}'"
            )

    def test_brakes_item_carries_the_cited_figures(self, db):
        item = _items(db)[5]
        for needle in (
            "95.0 mm", "95.5 mm", "3.5 mm", "1.0 mm", "10-20 mm",
            "2.5 mm", "PDF p. 164", "PDF p. 99",
        ):
            assert needle in (item["description"] or ""), (
                f"brakes item's description lost '{needle}'"
            )
        for needle in (
            "95.0 mm", "95.5 mm", "1.0 mm", "2.5 mm", "3.5 mm",
            "10-20 mm", "3 mm", "PDF p. 12", "PDF p. 94", "PDF p. 101",
        ):
            assert needle in (item["instruction_text"] or ""), (
                f"brakes item's instruction lost '{needle}'"
            )

    def test_tires_item_carries_the_cited_figures(self, db):
        item = _items(db)[6]
        for needle in (
            "0.8 mm", "125 kPa", "18 psi", "29 psi", "200 kPa",
            "5 years", "PDF p. 116",
        ):
            assert needle in (item["description"] or ""), (
                f"tires item's description lost '{needle}'"
            )
        for needle in (
            "18 psi", "29 psi", "0.8 mm", "2 mm", "5 years",
            "PDF p. 121", "PDF p. 65", "PDF p. 64", "PDF p. 116", "PDF p. 39",
        ):
            assert needle in (item["instruction_text"] or ""), (
                f"tires item's instruction lost '{needle}'"
            )

    def test_no_figure_items_carry_no_figure(self, db):
        """C15/C16: no document in the library sets a frame-alignment
        figure or a swingarm/engine-hanger play tolerance, so neither item
        carries a measurement figure. This is the assertion a planted
        '0.5 mm' breaks (phase log)."""
        for item in _items(db):
            if item["title"] in NO_FIGURE_TITLES:
                whole = _whole_item(item)
                assert not re.search(r"\d+(?:\.\d+)?\s*mm", whole), (
                    f"'{item['title']}' carries an mm figure; the S0-3 "
                    "censuses found no document that sets one"
                )
                assert not re.search(r"\d+\s*%", whole)
                assert not "N·m" in whole
                # And each says where the figure belongs instead.
                assert "research library sets" in whole
                assert "service manual" in whole

    def test_figures_name_their_machines(self, db):
        """The worked-example figures belong to cited machines; no item
        may present one machine's numbers as universal."""
        by_title = {i["title"]: i for i in _items(db)}
        fork_text = " ".join(
            by_title["Front fork — seals, stanchions and action"][k] or ""
            for k in ("description", "diagnosis_if_fail")
        )
        assert "Zuma 125" in fork_text and "CHF50" in fork_text
        steering_text = by_title["Steering head bearings"]["instruction_text"]
        assert "KTM" in steering_text and "Zuma 125" in steering_text
        brakes_text = by_title[
            "Brakes — pads or shoes, drums, discs and levers"
        ]["instruction_text"]
        for machine in ("CHF50", "F800R", "KTM"):
            assert machine in brakes_text
        tires_text = by_title[
            "Tires — tread, pressure, damage and age"
        ]["instruction_text"]
        for machine in ("Metropolitan", "CHF50", "KTM"):
            assert machine in tires_text
        wheels_text = by_title["Wheel bearings and rims"]["instruction_text"]
        assert "CHF50" in wheels_text and "Zuma 125" in wheels_text


# --- F158: no build references in text users see ---


class TestNoBuildReferences:
    PATTERNS = (
        r"\bPhase \d+\b",
        r"\bTrack [A-Z]\b",
        r"this phase",
        r"\bF\d{2,3}\b",
    )

    def _assert_clean(self, text, label):
        for pat in self.PATTERNS:
            m = re.search(pat, text or "", re.IGNORECASE)
            assert m is None, f"{label} carries build reference {m!r}"

    def test_new_template_text_is_clean(self, db):
        t = get_template_by_slug("ppi_chassis_v1", db)
        self._assert_clean(t["description"], "ppi_chassis_v1 description")
        self._assert_clean(t["name"], "ppi_chassis_v1 name")
        for item in _items(db):
            for field in (
                "title", "description", "instruction_text",
                "expected_pass", "expected_fail", "diagnosis_if_fail",
            ):
                self._assert_clean(item[field], f"item '{item['title']}' {field}")

    def test_repointed_engine_description_is_clean(self, db):
        desc = get_template_by_slug("ppi_engine_v1", db)["description"]
        self._assert_clean(desc, "ppi_engine_v1 description")

    def test_the_pattern_itself_catches_a_planted_reference(self):
        """S4 discipline: the pattern must be seen to catch. 'Phase 999'
        and 'Track Z' are caught; a BMW F800R model name is not (the
        F-number pattern must not eat it — F800 has no boundary at the
        trailing R)."""
        assert re.search(r"\bPhase \d+\b", "closed at Phase 999")
        assert re.search(r"\bTrack [A-Z]\b", "Track N expands")
        assert re.search(r"\bF\d{2,3}\b", "filed under F99 for this")
        assert not re.search(r"\bF\d{2,3}\b", "the BMW F800R owner's manual")


# --- Applicability (D2, through the substrate's own filter) ---


class TestApplicability:
    def test_offered_for_electric(self, db):
        electric = list_templates(db, powertrain="electric")
        assert any(t["slug"] == "ppi_chassis_v1" for t in electric)

    def test_offered_for_ice_and_hybrid(self, db):
        ice = list_templates(db, powertrain="ice")
        assert any(t["slug"] == "ppi_chassis_v1" for t in ice)
        hybrid = list_templates(db, powertrain="hybrid")
        assert any(t["slug"] == "ppi_chassis_v1" for t in hybrid)

    def test_the_engine_protocol_still_excludes_electric(self, db):
        """The deliberate contrast with 259: the chassis protocol is for
        every machine, the engine protocol stays ICE-only."""
        electric = list_templates(db, powertrain="electric")
        assert all(t["slug"] != "ppi_engine_v1" for t in electric)


# --- The CLI front door (259's commands, this phase's content) ---


class TestCliFrontDoor:
    def test_workflow_list_shows_the_chassis_template(self, db):
        result = CliRunner().invoke(main_cli, ["workflow", "list"])
        assert result.exit_code == 0, result.output
        assert "ppi_chassis_v1" in result.output
        assert "ppi_engine_v1" in result.output
        assert "generic_ppi_v1" in result.output
        # The slug column can wrap at the narrow test terminal, so the
        # winterization row is asserted by its category, not its slug.
        assert "winterization" in result.output

    def test_workflow_list_category_ppi_shows_chassis(self, db):
        result = CliRunner().invoke(main_cli, ["workflow", "list", "--category", "ppi"])
        assert result.exit_code == 0, result.output
        assert "ppi_chassis_v1" in result.output
        assert "winterization" not in result.output

    def test_workflow_show_prints_every_item_and_the_provenance(self, db):
        result = CliRunner().invoke(main_cli, ["workflow", "show", "ppi_chassis_v1"])
        assert result.exit_code == 0, result.output
        for title in ITEM_TITLES:
            assert title in result.output, f"show lost item '{title}'"
        # The provenance travels with the content (the 244V rule).
        assert "PDF p. 94" in result.output
        assert "PDF p. 116" in result.output
        assert "Pass:" in result.output
        assert "Fail:" in result.output
        # And the description, with its companion pointers by name.
        # Needles are single tokens: rich wraps the long description at
        # the 80-column test terminal, so a spaced phrase can break
        # between its words.
        assert "Companion" in result.output
        assert "generic_ppi_v1" in result.output

    def test_show_engine_now_points_at_chassis_by_name(self, db):
        """The user-visible surface F158 was filed over: what the engine
        protocol's screen says about the chassis protocol. Wrap-safe
        needles (the description is one long line at an 80-column
        terminal); the description's exact text is pinned at the DB
        level in TestMigration068."""
        result = CliRunner().invoke(main_cli, ["workflow", "show", "ppi_engine_v1"])
        assert result.exit_code == 0, result.output
        assert "ppi_chassis_v1" in result.output
        assert "Phase" not in result.output
