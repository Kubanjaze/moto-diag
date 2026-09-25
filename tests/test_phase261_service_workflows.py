"""Phase 261 — Track N batch 1: tire, brake, suspension and drivetrain service.

Migration 069 seeds four templates on the Phase 114 substrate, one per
ROADMAP row (261 tire, 269 brake, 270 suspension, 271 chain/belt/shaft),
reachable through `motodiag workflow list/show`. No new module.

What these tests pin:

- the migration seeds exactly four templates and 28 items on a fresh
  `init_db` database, and on an upgrade from 068 **alters and deletes no
  existing row** (inserts only);
- `rollback_to_version(68)` peels everything 069 added, and it re-applies;
- every template is for all three powertrains;
- the optional items are exactly the planned ones (the TPMS item; the
  caliper and master-cylinder overhauls; the fork air bleed; every
  drivetrain item, because a machine has one drive type);
- every figure an item states is present, per field, beside the machine
  it belongs to;
- the three negatives (N1 wear-pattern names, N2 universal-joint
  inspection, N3 belt alignment) are stated, and the u-joint item carries
  no measurement figure;
- no text carries a build reference (F158), with the pattern seen to catch
  a planted one;
- the CLI lists every new slug in full at an 80-column terminal (bug fix
  #1: rich elided `suspension_service_v1` to `suspension_se…`), filters by
  each new category, and shows every item.

Migration tests are head-proof (F124, 260's bug fixes #2/#3): they build a
068 database by applying migrations up to 068, apply 069 alone, and
compare against `m.version`, never a literal equal to the head.
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
    rollback_to_version,
)
from motodiag.workflows import (
    get_checklist_items,
    get_template_by_slug,
    list_templates,
)


TEMPLATES = {
    "tire_service_v1": ("tire_service", "Tire service", 60),
    "brake_service_v1": ("brake_service", "Brake service", 90),
    "suspension_service_v1": ("suspension_service", "Suspension service", 180),
    "drivetrain_service_v1": (
        "drivetrain_service", "Chain, belt and shaft drive service", 60,
    ),
}

TITLES = {
    "tire_service_v1": [
        "Read the old tire before it comes off",
        "Damage and age cracking",
        "Date code and age",
        "Tire pressure sensors (TPMS / BMW RDC)",
        "Fitting the replacement tire",
        "Balance",
        "Pressure, bead check and run-in",
    ],
    "brake_service_v1": [
        "Pads — measure, and replace in pairs",
        "Discs — thickness and runout",
        "Caliper overhaul — pistons and seals",
        "Master cylinder",
        "Brake fluid — type, age and change",
        "Bleeding",
        "Reassembly torques, pressure point and bedding-in",
    ],
    "suspension_service_v1": [
        "Record the settings and measure sag",
        "Spring rate for the rider",
        "Fork oil — drain, quantity and level",
        "Fork seals, dust wipers and springs",
        "Fork air bleed",
        "Rear shock — service or replace",
        "Damping and preload back to base",
    ],
    "drivetrain_service_v1": [
        "Chain drive — slack",
        "Chain drive — wear, sprockets and guides",
        "Chain drive — clean and lubricate",
        "Chain drive — adjust, align and replace",
        "Belt drive — slack and condition",
        "Shaft drive — final drive oil",
        "Shaft drive — universal joints and swinging arm bearings",
    ],
}

# Sequence numbers of the optional items (required = 0), per template.
OPTIONAL = {
    "tire_service_v1": {4},
    "brake_service_v1": {3, 4},
    "suspension_service_v1": {5},
    "drivetrain_service_v1": {1, 2, 3, 4, 5, 6, 7},
}

FIELDS = (
    "title", "description", "instruction_text",
    "expected_pass", "expected_fail", "diagnosis_if_fail",
)

# Per-field figure pins (259's bug fix #1 lesson: a pin over joined fields
# lets a figure corrupted in one field pass because another still carries
# it). Keyed (slug, sequence_number, field) -> needles that field must hold.
PINS = {
    # tire
    ("tire_service_v1", 1, "description"): ["abnormal wear and overheating", "PDF p. 116", "PDF p. 60"],
    ("tire_service_v1", 1, "instruction_text"): [
        "CB500F owner's manual sets 1.5 mm front and 2.0 mm rear (PDF p. 134)",
        "Honda PCX service manual the same, measured at the centre of the tread (PDF p. 97)",
        "at least 2 mm (PDF p. 115)", "TI or TWI", "(PDF p. 100)",
    ],
    ("tire_service_v1", 2, "description"): ["exposes fabric or cords", "PDF p. 60", "evidence of ageing", "PDF p. 56", "SR400"],
    ("tire_service_v1", 3, "description"): ["last four digits of the DOT number", "5 years at the latest", "PDF p. 116", '"22 09"', "PDF p. 63", "10 years", "PDF p. 62"],
    ("tire_service_v1", 3, "instruction_text"): ["week 22 of 2009 (PDF p. 63", "after 5 years at the latest", "after 10 years from manufacture"],
    ("tire_service_v1", 4, "description"): ["20 °C", "PDF p. 76", "approximately 30 km/h", "PDF p. 100", "PDF p. 103"],
    ("tire_service_v1", 4, "instruction_text"): ["approximately 30 km/h", "20 °C", "PDF p. 101"],
    ("tire_service_v1", 5, "instruction_text"): [
        "same size, construction, speed rating and load range (PDF p. 61)",
        "direction-of-rotation arrow", "PDF p. 178",
        "half the total indicator reading",
        "2.0 mm axial and 2.0 mm radial (PDF p. 326)", "PDF p. 188",
    ],
    ("tire_service_v1", 6, "description"): ["front max 5 g (PDF p. 205)", "rear max 45 g (PDF p. 206)", "max 80 g"],
    ("tire_service_v1", 6, "instruction_text"): ["5 g at the front and 45 g at the rear", "80 g", "PDF pp. 205–206"],
    ("tire_service_v1", 7, "instruction_text"): ["2.5 bar front and 2.9 bar rear", "PDF p. 206", "PDF p. 67", "PDF p. 85"],
    # brake
    ("brake_service_v1", 1, "instruction_text"): [
        "KTM EXC at least 1 mm (PDF p. 102)", "BMW F800R 1.0 mm", "(PDF p. 94)",
        "Yamaha Zuma 125 0.8 mm (PDF p. 134)", "Piaggio Beverly 125 1.5 mm (PDF p. 196)",
        "(PDF p. 104)", "(PDF p. 77)",
    ],
    ("brake_service_v1", 2, "instruction_text"): [
        "2.5 mm front and 3.5 mm rear (PDF p. 100)",
        "Honda PCX disc to 3.0 mm, with 0.30 mm warpage (PDF p. 371)",
        "Zuma 125 disc to 3.5 mm, with 0.15 mm deflection (PDF p. 119)",
        "from 4.0 mm new to 3.0 mm, with 0.30 mm runout (PDF p. 184)",
    ],
    ("brake_service_v1", 3, "instruction_text"): [
        "25.460 mm and 22.710 mm", "25.31 mm and 22.56 mm", "(PDF p. 384)",
        "25.30 mm", "PDF p. 194", "PDF p. 145", "PDF p. 146", "PDF p. 147", "PDF p. 193",
    ],
    ("brake_service_v1", 4, "instruction_text"): ["12.755 mm", "12.645 mm", "(PDF p. 373)", "12.75 mm", "PDF p. 191", "PDF p. 374", "PDF p. 201"],
    ("brake_service_v1", 5, "instruction_text"): [
        "DOT 4 / DOT 5.1", "PDF pp. 102, 170", "PDF p. 363", "PDF p. 48", "PDF p. 89",
        "every 2 years on the Honda CB500F (PDF p. 49)",
        "every 20,000 km or two years on the Beverly (PDF p. 49)",
    ],
    ("brake_service_v1", 6, "instruction_text"): ["half a turn", "5.4 N·m on the Honda PCX (PDF p. 367)", "6 Nm on the Yamaha Zuma 125 (PDF p. 92)", "PDF p. 91", "PDF p. 199"],
    ("brake_service_v1", 7, "instruction_text"): [
        "25 Nm with Loctite 243 (PDF p. 69)", "30 Nm (PDF p. 106)",
        "30 N·m, and its ALOC bolts are replaced with new ones (PDF p. 21)",
        "29–35 N·m", "PDF p. 195", "PDF p. 109", "PDF p. 67",
    ],
    # suspension
    ("suspension_service_v1", 1, "instruction_text"): [
        "static sag 37 mm and riding sag 110 mm (PDF p. 58)",
        "25 mm and 70–80 mm (PDF pp. 73–74)", "PDF pp. 57–58", "PDF p. 55", "PDF p. 60",
    ],
    ("suspension_service_v1", 2, "instruction_text"): [
        "4.2, 4.4 and 4.6 N/mm", "57–63, 60–66 and 63–69 N/mm",
        "65–75, 75–85 and 85–95 kg (PDF pp. 60, 166)",
        "5.2, 5.4 and 5.6 N/mm", "(PDF p. 183)",
        "fork spring as two rates, 7.1 N/mm (K1) and 15.4 N/mm (K2), with no optional spring available (PDF p. 34)",
    ],
    ("suspension_service_v1", 3, "instruction_text"): [
        "636 ± 10 ml of SAE 4", "(PDF p. 166)", "620 ml of SAE 5", "(PDF p. 183)",
        "122.0 ± 2.5 cm³", "75 mm (PDF p. 335)", "0.104 L of 10W", "(PDF p. 160)",
        "PDF p. 155", "PDF p. 158",
    ],
    ("suspension_service_v1", 4, "instruction_text"): [
        "252.1 mm standard and 247 mm limit (PDF p. 157)", "125.9 mm limit (PDF p. 227)",
        "PDF p. 156", "PDF p. 159", "PDF p. 334", "PDF p. 67",
    ],
    ("suspension_service_v1", 5, "instruction_text"): ["PDF p. 75", "PDF p. 69"],
    ("suspension_service_v1", 6, "instruction_text"): ["10 bar with SAE 2.5 shock fluid (PDF pp. 55, 167)", "(PDF p. 85)", "(PDF p. 175)", "PDF p. 95"],
    ("suspension_service_v1", 7, "instruction_text"): [
        "15 clicks low-speed compression, 2 turns high-speed compression (PDF p. 56)",
        "15 clicks rebound (PDF p. 57)", "9 mm spring preload (PDF p. 59)",
        "position 4 of 9", "(PDF p. 92)", "± 40 % (PDF p. 64)",
    ],
    # drivetrain
    ("drivetrain_service_v1", 1, "instruction_text"): [
        "55–58 mm on the KTM EXC (PDF p. 90)",
        "35–45 mm on the Honda CB500F with 60 mm as the do-not-ride limit (PDF p. 80)",
        "30–40 mm on the BMW F800R (PDF p. 101)",
    ],
    ("drivetrain_service_v1", 2, "instruction_text"): ["10–15 kg", "18 rollers", "272 mm at most (PDF p. 92)", "(PDF p. 83)", "(PDF p. 102)", "PDF pp. 92–93", "PDF p. 58"],
    ("drivetrain_service_v1", 3, "instruction_text"): ["(PDF p. 89)", "(PDF p. 59)", "every 1000 km at the latest", "(PDF p. 100)"],
    ("drivetrain_service_v1", 4, "instruction_text"): [
        "rear axle nut 80 Nm (PDF p. 91)", "axle nut 88 N·m and adjuster lock nuts 21 N·m (PDF p. 82)",
        "tensioner locknut 19 Nm and rear axle 100 Nm (PDF p. 102)",
        "DID520V0, 112 links, 15T/41T, PDF p. 134",
        "35 Nm and engine sprocket screw 60 Nm, Loctite 2701, PDF pp. 168, 163",
    ],
    ("drivetrain_service_v1", 5, "description"): ["45 N (4.5 kgf, 10 lbf)", "6.0–8.0 mm", "2500 mi (4000 km)", "5.0–7.0 mm", "5.0 mm apart"],
    ("drivetrain_service_v1", 5, "instruction_text"): [
        "6.0–8.0 mm under 45 N on the Yamaha XVS950 (PDF pp. 65–66)",
        "5.0–7.0 mm on the XVS1300, whose marks are 5.0 mm apart (PDF p. 64)",
        "every 2500 mi (4000 km) on the XVS950 (PDF p. 48)", "(XVS1300, PDF p. 82)",
    ],
    ("drivetrain_service_v1", 6, "description"): [
        "every 40,000 km (24,000 miles) or at the latest every 2 years (PDF p. 8)",
        "API class GL 5", "approx. 0.25 l", "SAE 90 above 5 °C and SAE 80 below (PDF p. 87)",
        "PDF p. 67", "PDF p. 70",
    ],
    ("drivetrain_service_v1", 6, "instruction_text"): [
        "(PDF p. 6)", "approximately 0.25 l", "SAE 90 above 5 °C and SAE 80 below (PDF p. 87)",
        "R 850 R / R 1150 R, PDF p. 67; K 1200 RS, PDF p. 70",
        "every 40,000 km or at the latest every 2 years on the R 1100 S (PDF p. 8)",
    ],
    ("drivetrain_service_v1", 7, "description"): ["two universal joints", "PDF p. 81", "PDF p. 7"],
}

# Each needle whose figure belongs to one machine must sit in a field that
# names that machine (the items say whose figure it is, never a universal).
MACHINE_OF = {
    "272 mm": "KTM", "55–58 mm": "KTM", "35–45 mm": "CB500F", "30–40 mm": "F800R",
    "6.0–8.0 mm": "XVS950", "5.0–7.0 mm": "XVS1300", "0.25 l": "R 1100 S",
    "45 g": "S 1000 XR", "12.755 mm": "PCX", "25.460 mm": "PCX", "0.15 mm": "Zuma 125",
    "636 ± 10 ml": "EXC", "75 mm": "PCX", "37 mm": "EXC", "252.1 mm": "Zuma 125",
}

# N1-N3, the negatives with their controls (261_step0.md): the sentence that
# says where no document sets a figure.
NEGATIVE_SENTENCES = {
    ("tire_service_v1", 1, "description"):
        "No maker's document in the research library names wear patterns such as cupping, feathering or squaring",
    ("drivetrain_service_v1", 5, "description"):
        "No document in the research library sets a belt alignment figure",
    ("drivetrain_service_v1", 5, "instruction_text"):
        "No document in the research library sets a belt alignment figure",
    ("drivetrain_service_v1", 7, "description"):
        "No document in the research library gives a universal-joint inspection procedure or a play figure",
    ("drivetrain_service_v1", 7, "instruction_text"):
        "No document in the research library gives a universal-joint inspection procedure or a play figure",
}

MEASUREMENT = re.compile(r"\d+(?:\.\d+)?\s*(?:mm|N·m|Nm|N/mm|g|kg|bar)\b")


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A fresh, fully-migrated database the CLI can reach via settings."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "motodiag.db")
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    reset_settings()
    init_db(path)
    yield path
    reset_settings()


def _items(db_path, slug):
    template = get_template_by_slug(slug, db_path)
    assert template is not None, f"template {slug} missing"
    return get_checklist_items(template["id"], db_path)


def _item(db_path, slug, seq):
    return next(i for i in _items(db_path, slug) if i["sequence_number"] == seq)


def _build_at_68(path):
    """A 068 database built here: migrations up to 068 only, never a copy of
    data/motodiag.db and never a rollback of 069."""
    init_db(path, apply_migrations=False)
    for m in sorted(MIGRATIONS, key=lambda m: m.version):
        if get_current_version(path) < m.version <= 68:
            apply_migration(m, path)
    assert get_current_version(path) == 68


def _snapshot(path):
    conn = sqlite3.connect(path)
    # Keyed by slug (column 1): ids are an insertion detail.
    templates = {r[1]: r for r in conn.execute("SELECT * FROM workflow_templates")}
    items = {r[0]: r for r in conn.execute("SELECT * FROM checklist_items")}
    conn.close()
    return templates, items


# --- Migration 069 ---


class TestMigration069:
    def test_schema_version_floor_pin(self):
        """F124: never a literal equality to the head."""
        assert SCHEMA_VERSION >= 69

    def test_migration_069_exists_by_name(self):
        m = get_migration_by_version(69)
        assert m is not None
        assert m.name == "chassis_drivetrain_service_workflows"

    def test_every_migration_keeps_its_rollback(self):
        """260's bug fix #1 guard, re-run with 069 inserted: no migration
        lost its rollback to its successor."""
        assert [m.version for m in MIGRATIONS if not m.rollback_sql.strip()] == []
        assert "'ppi_chassis_v1'" in get_migration_by_version(68).rollback_sql
        rollback = get_migration_by_version(69).rollback_sql
        for slug in TEMPLATES:
            assert f"'{slug}'" in rollback

    def test_fresh_init_seeds_the_four_templates(self, db):
        for slug, (category, name, minutes) in TEMPLATES.items():
            t = get_template_by_slug(slug, db)
            assert t is not None, slug
            assert t["category"] == category
            assert t["name"] == name
            assert t["estimated_duration_minutes"] == minutes
            # S0-5: tires, brakes, suspension and final drives exist on
            # every powertrain.
            assert t["applicable_powertrains"] == ["ice", "electric", "hybrid"]
            assert t["is_active"] == 1
            assert t["required_tier"] == "individual"

    def test_seven_items_each_in_contiguous_sequence(self, db):
        for slug, titles in TITLES.items():
            items = _items(db, slug)
            assert [i["sequence_number"] for i in items] == list(range(1, 8)), slug
            assert [i["title"] for i in items] == titles
            for item in items:
                assert item["instruction_text"].strip()
                assert item["expected_pass"].strip()
                assert item["expected_fail"].strip()
                assert item["diagnosis_if_fail"].strip()

    def test_optional_items_are_exactly_the_planned_ones(self, db):
        for slug, optional in OPTIONAL.items():
            got = {i["sequence_number"] for i in _items(db, slug) if not i["required"]}
            assert got == optional, slug

    def test_upgrade_from_68_inserts_only(self, tmp_path):
        """069 alters and deletes no existing row: every template and item
        present at 068 is byte-identical after it, and the only additions
        are the four templates and their 28 items. This is the property the
        live dry run must show before the live apply."""
        path = str(tmp_path / "at_68.db")
        _build_at_68(path)
        templates_68, items_68 = _snapshot(path)
        m069 = get_migration_by_version(69)
        apply_migration(m069, path)
        # Against the migration just applied, never a literal (F124).
        assert get_current_version(path) == m069.version
        templates_69, items_69 = _snapshot(path)
        assert {k: templates_69[k] for k in templates_68} == templates_68
        assert {k: items_69[k] for k in items_68} == items_68
        assert set(templates_69) - set(templates_68) == set(TEMPLATES)
        assert len(items_69) - len(items_68) == 28

    def test_rollback_peels_everything_069_added(self, tmp_path):
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert get_current_version(path) == SCHEMA_VERSION
        # A rollback peels every successor (260's bug fix #2).
        rollback_to_version(68, path)
        assert get_current_version(path) == 68
        for slug in TEMPLATES:
            assert get_template_by_slug(slug, path) is None
        conn = sqlite3.connect(path)
        orphans = conn.execute(
            "SELECT COUNT(*) FROM checklist_items WHERE template_id NOT IN "
            "(SELECT id FROM workflow_templates)"
        ).fetchone()[0]
        conn.close()
        assert orphans == 0
        assert get_template_by_slug("ppi_chassis_v1", path) is not None
        # And forward again.
        assert 69 in apply_pending_migrations(path)
        assert get_current_version(path) == SCHEMA_VERSION
        for slug in TEMPLATES:
            assert len(_items(path, slug)) == 7


# --- Content pins (the figure discipline) ---


class TestContentPins:
    def test_every_pinned_figure_is_in_its_field(self, db):
        for (slug, seq, field), needles in PINS.items():
            text = _item(db, slug, seq)[field] or ""
            for needle in needles:
                assert needle in text, f"{slug} item {seq} {field} lost '{needle}'"

    def test_figures_sit_beside_their_machine(self, db):
        """No item may present one machine's figure as universal: a field
        holding the figure also names its machine."""
        seen = set()
        for slug in TEMPLATES:
            for item in _items(db, slug):
                for field in FIELDS:
                    text = item[field] or ""
                    for figure, machine in MACHINE_OF.items():
                        if figure in text:
                            seen.add(figure)
                            assert machine in text, (
                                f"{slug} item {item['sequence_number']} {field} states "
                                f"'{figure}' without naming the {machine}"
                            )
        assert seen == set(MACHINE_OF), "a machine-bound figure is no longer seeded"

    def test_zuma_spring_rates_are_its_fork_spring(self, db):
        """Refute-before-ship: the Zuma 125 SM lists K1/K2 under Front
        suspension (PDF p. 34). A draft called them rear spring rates."""
        text = _item(db, "suspension_service_v1", 2)["instruction_text"]
        assert "fork spring as two rates" in text
        assert "rear spring rates" not in text

    def test_pcx_warpage_cited_in_millimetres_only(self, db):
        """The PCX SM prints "0.30 mm (0.001 in)"; the inch figure is its
        own conversion error, so the content carries millimetres only."""
        for field in FIELDS:
            assert "0.001 in" not in (_item(db, "brake_service_v1", 2)[field] or "")

    def test_the_negatives_are_stated(self, db):
        for (slug, seq, field), sentence in NEGATIVE_SENTENCES.items():
            assert sentence in (_item(db, slug, seq)[field] or ""), (slug, seq, field)

    def test_no_named_wear_pattern_is_asserted(self, db):
        """N1: the makers name no wear pattern, so the content names one
        only inside the sentence that says so."""
        for item in _items(db, "tire_service_v1"):
            for field in FIELDS:
                text = (item[field] or "").replace(
                    NEGATIVE_SENTENCES[("tire_service_v1", 1, "description")], ""
                )
                assert not re.search(r"cupp|feather|squar", text, re.IGNORECASE), (
                    item["sequence_number"], field,
                )

    def test_universal_joint_item_carries_no_measurement(self, db):
        """N2: no document sets a u-joint play figure, so the item states no
        measurement at all. A planted '0.2 mm' breaks this (phase log)."""
        item = _item(db, "drivetrain_service_v1", 7)
        for field in FIELDS:
            assert not MEASUREMENT.search(item[field] or ""), field

    def test_the_measurement_pattern_catches_a_planted_figure(self):
        assert MEASUREMENT.search("play of 0.2 mm at the joint")
        assert MEASUREMENT.search("torque 25 Nm")
        assert not MEASUREMENT.search("PDF p. 81")


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

    def test_all_four_templates_are_clean(self, db):
        for slug in TEMPLATES:
            t = get_template_by_slug(slug, db)
            self._assert_clean(t["name"], f"{slug} name")
            self._assert_clean(t["description"], f"{slug} description")
            for item in _items(db, slug):
                for field in FIELDS:
                    self._assert_clean(item[field], f"{slug} item {item['sequence_number']} {field}")

    def test_the_pattern_itself_catches_a_planted_reference(self):
        assert re.search(r"\bPhase \d+\b", "expanded in Phase 999")
        assert re.search(r"\bTrack [A-Z]\b", "Track N batch 1")
        assert re.search(r"\bF\d{2,3}\b", "filed under F99")
        # BMW model names must not trip the finding-number pattern.
        assert not re.search(r"\bF\d{2,3}\b", "the BMW F800R rider's manual")
        assert not re.search(r"\bF\d{2,3}\b", "the BMW F 800 GS rider's manual")


# --- Applicability ---


class TestApplicability:
    def test_offered_for_every_powertrain(self, db):
        for powertrain in ("ice", "electric", "hybrid"):
            slugs = {t["slug"] for t in list_templates(db, powertrain=powertrain)}
            assert set(TEMPLATES) <= slugs, powertrain

    def test_each_category_holds_its_template(self, db):
        for slug, (category, _, _) in TEMPLATES.items():
            assert [t["slug"] for t in list_templates(db, category=category)] == [slug]


# --- The CLI front door ---


class TestCliFrontDoor:
    def test_workflow_list_shows_every_slug_in_full(self, db):
        """Bug fix #1: at the 80-column test terminal rich elided the slug
        column ("suspension_se…"), so a user could not read the slug
        `workflow show` needs. Every slug must print whole."""
        result = CliRunner().invoke(main_cli, ["workflow", "list"])
        assert result.exit_code == 0, result.output
        for slug in [*TEMPLATES, "ppi_chassis_v1", "ppi_engine_v1",
                     "generic_ppi_v1", "generic_winterization_v1"]:
            assert slug in result.output, f"list elided '{slug}'"
        assert "…" not in result.output

    def test_list_by_each_new_category(self, db):
        for slug, (category, _, _) in TEMPLATES.items():
            result = CliRunner().invoke(main_cli, ["workflow", "list", "--category", category])
            assert result.exit_code == 0, result.output
            assert slug in result.output
            assert category in result.output
            others = set(TEMPLATES) - {slug}
            assert not any(o in result.output for o in others)

    @pytest.mark.parametrize("slug", sorted(TEMPLATES))
    def test_show_prints_every_item(self, db, slug):
        result = CliRunner().invoke(main_cli, ["workflow", "show", slug])
        assert result.exit_code == 0, result.output
        for title in TITLES[slug]:
            assert title in result.output, f"show {slug} lost '{title}'"
        assert result.output.count("(optional)") == len(OPTIONAL[slug])
        assert "Pass:" in result.output and "Fail:" in result.output
        # Provenance travels with the content; wrap-safe single tokens.
        assert "PDF" in result.output
