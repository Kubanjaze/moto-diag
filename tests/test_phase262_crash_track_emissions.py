"""Phase 262 — Track N batch 3: crash support, track-day preparation, and
emissions compliance (California first).

Migration 071 seeds three templates on the Phase 114 substrate, one per
ROADMAP row (262 crash and insurance claim support, 263 track-day and race
prep, 267 emissions and smog compliance), reachable through `motodiag
workflow list/show`, and fixes live rows the operator scoped in:

- `generic_winterization_v1`'s uncited figures (F161) become pointers to
  `winterization_v1`;
- `ppi_chassis_v1`'s steering item reads the YW125Y's p. 93 as it is and
  names its KTM manual (F162).

What these tests pin:

- a fresh `init_db` database holds the three templates and 21 items;
- on an upgrade from a self-built 070 database, 071 changes exactly the
  scoped item rows and adds exactly the three templates and their items;
- `rollback_to_version(70)` restores every changed row byte-identical and
  removes the new rows; it re-applies;
- the optional items are exactly the planned ones, and the powertrains
  are D5's;
- every figure is present per field, beside the machine it belongs to,
  and every regulator rule beside its regulator;
- the negatives are stated where the items rely on them;
- F161's figures are gone and F162's sentences are as planned;
- no build reference in any new or changed text (F158);
- the CLI lists, filters and shows all three.

Migration tests are head-proof (F124): they build a 070 database by
applying migrations up to 070, apply 071 alone, and compare against
`m.version`, never a literal equal to the head. No test reads
data/motodiag.db.
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


ALL = ["ice", "electric", "hybrid"]
ENGINE = ["ice", "hybrid"]

TEMPLATES = {
    "crash_support_v1": (
        "crash_support",
        "Crash support — post-crash inspection and the California salvage decision",
        150, ALL,
    ),
    "track_prep_v1": ("track_prep", "Track-day preparation", 120, ENGINE),
    "emissions_v1": (
        "emissions", "Emissions and smog compliance — California first", 60, ENGINE,
    ),
}

TITLES = {
    "crash_support_v1": [
        "Safety, the law and the first look",
        "Frame — inspect it; KTM's rule is change, not repair",
        "Handlebar and controls — a bent handlebar is replaced, not straightened",
        "Front fork — tubes and legs",
        "Axles and wheels — runout against the machine's own limit",
        "Hidden damage — the full check before the machine is trusted",
        "The claim record — no photo or claim standard in the library",
        "California — total loss, the salvage certificate, and a repaired total loss",
    ],
    "track_prep_v1": [
        "The maker's intended use, and the warranty",
        "Road equipment off for the track — and back on for the road",
        "Suspension — set for the rider, then for the track",
        "Rider aids on a closed track",
        "Service intervals when the machine is raced",
        "Safety wire, coolant, inspection and race numbers — the event's rules",
    ],
    "emissions_v1": [
        "California Smog Check — motorcycles are exempt",
        "Which standard it was built to — the label and the California model",
        "Tampering — what counts, and what the law says",
        "Aftermarket parts — the CARB Executive Order and its label",
        "Catalytic converter — fuel, misfires and running dry",
        "Evaporative system (California and 50-state models)",
        "Emission maintenance, records and the warranty",
    ],
}

# Sequence numbers of the optional items (required = 0), per template.
OPTIONAL = {
    # the claim record: not every crash has a claim; California: only there.
    "crash_support_v1": {7, 8},
    # rider aids: only on machines that have them.
    "track_prep_v1": {4},
    # the canister: California and 50-state models only.
    "emissions_v1": {6},
}

FIELDS = (
    "title", "description", "instruction_text",
    "expected_pass", "expected_fail", "diagnosis_if_fail",
)

# Per-field figure and citation pins (259's bug fix #1).
PINS = {
    # crash support
    ("crash_support_v1", 1, "description"): ['"Personal safety is your first priority"', "follow applicable laws and regulations if another person or vehicle is involved in the crash", "(PDF p. 9)", '"A fall can damage the vehicle more seriously than it may first appear" (PDF p. 83)'],
    ("crash_support_v1", 1, "instruction_text"): ["KTM 690 Enduro 2010, PDF p. 53)","checks all functions thoroughly before starting up again (PDF p. 27)", "OFF and back to ON before the engine will restart (PDF p. 113)"],
    ("crash_support_v1", 1, "diagnosis_if_fail"): ["damage that is not immediately apparent", "qualified service facility as soon as possible (PDF p. 9)"],
    ("crash_support_v1", 2, "description"): ['"Repairs on the frame are not permitted"', "(PDF p. 94)", "(PDF p. 318)", "(PDF p. 325)", "beside a damaged steering head pipe (PDF p. 335)"],
    ("crash_support_v1", 2, "instruction_text"): ["No document in the research library gives frame dimensions to measure a frame against", "this template sets no frame measurement", "that list of places is the template's own"],
    ("crash_support_v1", 3, "description"): ['"A bent handlebar must always be replaced.', "(PDF p. 27)", "(PDF p. 65)", "(PDF p. 165)"],
    ("crash_support_v1", 3, "instruction_text"): ["loss of throttle control while riding (PDF p. 78)", "is the template's own"],
    ("crash_support_v1", 4, "description"): ["inner tube bending limit is 0.2 mm (PDF p. 34)", "(PDF p. 157)", "(PDF p. 35)"],
    ("crash_support_v1", 4, "instruction_text"): ["0.2 mm on the Yamaha YW125Y (PDF p. 34)", "do not straighten it (PDF p. 157)"],
    ("crash_support_v1", 5, "description"): [
        "the axle figures are for the front axle",
        "0.20 mm in the Honda CHF50/P/S Metropolitan (2002–2006) service manual (PDF p. 218)",
        "0.2 mm in the Honda PCX150 (2013–2017) service manual (PDF p. 326)",
        "0.2 mm in the Kymco People / People S 250 service manual (PDF p. 187)",
        "0.25 mm bending limit",
        "(PDF p. 117)",
        "half the total indicator reading",
    ],
    ("crash_support_v1", 5, "instruction_text"): [
        "Radial and axial 2.0 mm on the Honda CHF50 (front PDF p. 219, rear PDF p. 242)",
        "the Honda PCX150 (front PDF p. 326, rear PDF p. 355)",
        "Kymco People / People S 250 (front PDF p. 188, rear PDF p. 206)",
        "radial and lateral 1.0 mm for the Yamaha YW125Y front wheel (PDF p. 117)",
        "the actual runout is half the total indicator reading",
    ],
    ("crash_support_v1", 5, "diagnosis_if_fail"): ['"replace if over"', "People S 250, PDF pp. 187–188, 206)", "(Yamaha YW125Y, PDF p. 117)"],
    ("crash_support_v1", 8, "description"): [
        "Vehicle Industry Registration Procedures Manual, 19.015 Definitions",
        "(VC §544)", "uneconomical to repair", "(VC §431)", "cannot be titled or reregistered",
        "(VC §§11515 and 11515.2)",
    ],
    ("crash_support_v1", 8, "instruction_text"): [
        "within 10 days (DMV manual, 19.075 Salvage Certificate)",
        "(DMV, Total Loss Salvage & Non-Repairable Vehicles)",
        "(REG 343)", "(REG 31)", "(CHP 97C)", "(VSSI)",
        "(DMV, Junk/Revived Salvage Vehicles)",
    ],
    # track prep
    ("track_prep_v1", 1, "description"): ['"to meet the normal demands of regular road and race track operation"', "(PDF p. 10)", "(PDF p. 9)", '"Competition or racing use" (PDF p. 135)'],
    ("track_prep_v1", 2, "description"): ["(PDF p. 65)", "20 Nm with Multi-wax spray as joining compound (PDF p. 85)","EQIPWARNLAMP", "(PDF p. 86)", "(PDF p. 88)"],
    ("track_prep_v1", 3, "description"): [
        "on machines with Dynamic Damping Control (optional equipment), 6...10 mm at the front with an 85 kg rider (PDF pp. 80–81)",
        '("ERS (YZF-R1M)", PDF p. 41)',
        "position 1 comfortable, 3 normal and 7 sports, with an 85 kg rider (PDF p. 82)",
        "(rear wheel PDF p. 78, front wheel PDF p. 80)", "75 … 85 kg (PDF p. 55)",
        "for the rear shock absorber a static sag of 37 mm and a riding sag of 110 mm (PDF p. 58)",
        "T-2 and M-2 for track use with street tires (PDF pp. 41–42)",
    ],
    ("track_prep_v1", 3, "instruction_text"): ["an increase in preload requiring firmer damping (PDF p. 81)", "suspension_service_v1"],
    # Refute round 1: each figure keeps its model, equipment and condition.
    ("track_prep_v1", 1, "description"): ['"This vehicle is not suitable for use on race tracks" (PDF p. 10)', "continental United States", "for its EXC models"],
    ("track_prep_v1", 4, "instruction_text"): ["the mode last selected returns (PDF p. 106)", "with the coding plug inserted, a deactivated DTC stays off", "(PDF p. 132;", "switches DTC back on once the motorcycle passes 10 km/h, PDF pp. 62, 126)"],
    ("track_prep_v1", 6, "diagnosis_if_fail"): ["rear axle nut (PDF p. 129)", "parts-and-accessories approval note in two BMW booklets", "PDF p. 4 of each)"],
    ("emissions_v1", 3, "instruction_text"): ["secondary air injection system", '"to reduce or defeat"', "U.S. federal law"],
    ("emissions_v1", 4, "diagnosis_if_fail"): ['"shall not be liable for malfunctions'],
    ("emissions_v1", 7, "diagnosis_if_fail"): ["What a missing receipt costs depends on the machine's own warranty statement", "(PDF p. 17)"],
    ("crash_support_v1", 7, "description"): ["requires a written estimate in accordance with the Automotive Repair Act", "(PDF pp. 27, 32)"],
    # Phase 381 (F164): the papers clause now continues with the KTM and EPA pages.
    ("crash_support_v1", 7, "diagnosis_if_fail"): ["they mostly say where to keep the insurance papers;", "type-approval and recall paperwork"],
    ("track_prep_v1", 4, "description"): ["(PDF p. 107)", '"There is a possibility of the motorcycle flipping over backwards" (PDF p. 133)', '"is intended for track use on closed circuit race tracks only" (PDF p. 23)'],
    ("track_prep_v1", 5, "description"): ["(PDF p. 175)", '"If motorcycle is used for competition 7500 km service should be carried out after every race" (PDF p. 30)', '"Every 10 operating hours when used for motorsports" (PDF pp. 52–53)', "(PDF pp. 53–54)"],
    ("track_prep_v1", 5, "instruction_text"): ["the manual gives no figure", "brake_service_v1"],
    # emissions
    ("emissions_v1", 1, "description"): ["Smog Check Reference Guide 2025", "H&S §§ 44011, 44011(a)(6), VC § 4000.1 and CCR §§ 3340.5, 3340.42 (section 1.1.5, PDF p. 9)", '"Smog Check Required: None" (PDF p. 10)'],
    ("emissions_v1", 2, "description"): ['"ONMC - Executive Order Introduction"', "make, model and model year", "left side of the swingarm (PDF p. 121)", "(PDF p. 32)", "rear fender (PDF p. 109)", '"AC 50 state (meets California)" (PDF p. 8)'],
    ("emissions_v1", 3, "description"): ["Vehicle Code section 27156", "since the 1979 model year", "since the 1997 model year", "(PDF p. 45)", "(PDF p. 41)", "$4,819 per violative vehicle, engine or defeat device", "(PDF p. 2)"],
    ("emissions_v1", 3, "instruction_text"): ["(PDF pp. 122–123)", "(PDF p. 123)", "(PDF p. 124)"],
    ("emissions_v1", 4, "description"): ["D-XXX-XXX", "spark plugs, plug wires or air cleaner elements", "sold to an ultimate purchaser"],
    ("emissions_v1", 4, "instruction_text"): ["reasonable basis", "(PDF p. 2)"],
    ("emissions_v1", 4, "diagnosis_if_fail"): ["Section 27156 of the Vehicle Code", "(PDF p. 19)"],
    ("emissions_v1", 5, "description"): ["(PDF p. 125)", "(PDF p. 25)", "(PDF p. 31)", "(PDF p. 28)"],
    ("emissions_v1", 6, "description"): ["(PDF p. 122)", "(PDF p. 42)", "(PDF p. 79)"],
    ("emissions_v1", 7, "description"): ["(PDF p. 122)", "(PDF p. 45)", "(PDF p. 128)", "five years or 30,000 kilometers (18,641 miles)", "(PDF p. 17)"],
}

# A figure that belongs to one machine must sit in a field that names it.
MACHINE_OF = {
    "0.20 mm": "CHF50", "0.25 mm": "YW125Y", "1.0 mm": "YW125Y", "6...10 mm": "S 1000 R",
    "37 mm": "EXC TPI", "110 mm": "EXC TPI", "20 Nm": "S 1000 R", "7500 km": "950 Super Enduro R",
    "Every 10 operating hours": "EXC TPI", "M-1": "YZFR1T1/YZFR1MT", "30,000 kilometers": "GTS 310 HPE",
}

# A rule that belongs to a regulator must sit in a field that names it.
REGULATOR_OF = {
    "VC §544": "DMV", "within 10 days": "DMV", "REG 343": "DMV",
    "Smog Check Required: None": "Bureau of Automotive Repair",
    "D-XXX-XXX": "CARB", "Vehicle Code section 27156": "CARB",
    "$4,819": "EPA",
}

# The negatives (262_step0.md, N8-N12), each where the content relies on it.
NEGATIVE_SENTENCES = {
    ("crash_support_v1", 2, "instruction_text"):
        "No document in the research library gives frame dimensions to measure a frame against",
    ("crash_support_v1", 7, "description"):
        "No maker's or regulator's document in the research library sets a photo documentation standard, a damage-estimating method or an insurance-claim procedure",
    ("track_prep_v1", 6, "description"):
        "No maker's document in the research library gives a safety-wire or lockwire procedure, a coolant for track or race use, a technical-inspection list or a race-number rule",
}

# F161: the figures that go, and the pointer that replaces them.
F161_GONE = ("Sta-Bil", "5 minutes", "10W-40", "13.2", "13.6", "winter weight", "float voltage")
F161_OLD = {
    (1, "instruction_text"): "Add Sta-Bil or equivalent to fuel tank per manufacturer ratio. Run engine 5 minutes to circulate.",
    (1, "expected_pass"): "Stabilizer circulated through fuel system",
    (1, "expected_fail"): "Engine not run after adding — stabilizer did not reach carbs/injectors",
    (2, "instruction_text"): "Change engine oil and filter with recommended winter weight (typically 10W-40).",
    (3, "expected_pass"): "Battery on tender, reading float voltage (13.2V-13.6V)",
}
F162_OLD = (
    "the YW125Y service manual calls the same movement binding or looseness (PDF p. 93)",
    "the KTM 250/300 EXC owner's manual (PDF p. 76)",
)
F162_NEW = (
    "the YW125Y service manual checks the same movement for binding or looseness (PDF p. 93)",
    "the KTM 2022 250/300 EXC TPI owner's manual (PDF p. 76)",
)


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


def _build_at_70(path):
    """A 070 database built here: migrations up to 070 only, never a copy of
    data/motodiag.db and never a rollback of 071."""
    init_db(path, apply_migrations=False)
    for m in sorted(MIGRATIONS, key=lambda m: m.version):
        if get_current_version(path) < m.version <= 70:
            apply_migration(m, path)
    assert get_current_version(path) == 70


def _snapshot(path):
    """Templates keyed by slug with `updated_at` dropped; items keyed by id."""
    conn = sqlite3.connect(path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(workflow_templates)")]
    upd = cols.index("updated_at")
    templates = {
        r[1]: tuple(v for i, v in enumerate(r) if i != upd)
        for r in conn.execute("SELECT * FROM workflow_templates")
    }
    items = {r[0]: r for r in conn.execute("SELECT * FROM checklist_items")}
    conn.close()
    return templates, items


def _scoped_item_ids(path):
    """The live rows 071 is allowed to change: the generic winterization
    items that carried F161's figures, the chassis steering item (F162), and
    winterization_v1's battery item, whose W30 sentence gains its context."""
    conn = sqlite3.connect(path)
    w30 = {
        r[0] for r in conn.execute(
            "SELECT i.id FROM checklist_items i JOIN workflow_templates t "
            "ON t.id = i.template_id WHERE t.slug = 'winterization_v1' "
            "AND i.sequence_number = 5"
        )
    }
    generic = {
        r[0] for r in conn.execute(
            "SELECT i.id FROM checklist_items i JOIN workflow_templates t "
            "ON t.id = i.template_id WHERE t.slug = 'generic_winterization_v1' "
            "AND i.sequence_number IN (1, 2, 3)"
        )
    }
    steering = {
        r[0] for r in conn.execute(
            "SELECT i.id FROM checklist_items i JOIN workflow_templates t "
            "ON t.id = i.template_id WHERE t.slug = 'ppi_chassis_v1' "
            "AND i.title = 'Steering head bearings'"
        )
    }
    conn.close()
    return generic, steering, w30


# --- Migration 071 ---


class TestMigration071:
    def test_schema_version_floor_pin(self):
        """F124: never a literal equality to the head."""
        assert SCHEMA_VERSION >= 71

    def test_migration_071_exists_by_name(self):
        m = get_migration_by_version(71)
        assert m is not None
        assert m.name == "crash_track_emissions_workflows"

    def test_every_migration_keeps_its_rollback(self):
        assert [m.version for m in MIGRATIONS if not m.rollback_sql.strip()] == []
        rollback = get_migration_by_version(71).rollback_sql
        for slug in TEMPLATES:
            assert f"'{slug}'" in rollback
        assert "'generic_winterization_v1'" in rollback
        assert "'ppi_chassis_v1'" in rollback

    def test_fresh_init_seeds_the_three_templates(self, db):
        for slug, (category, name, minutes, powertrains) in TEMPLATES.items():
            t = get_template_by_slug(slug, db)
            assert t is not None, slug
            assert t["category"] == category
            assert t["name"] == name
            assert t["estimated_duration_minutes"] == minutes
            assert t["applicable_powertrains"] == powertrains
            assert t["is_active"] == 1
            assert t["required_tier"] == "individual"

    def test_items_in_contiguous_sequence(self, db):
        for slug, titles in TITLES.items():
            items = _items(db, slug)
            assert [i["sequence_number"] for i in items] == list(range(1, len(titles) + 1)), slug
            assert [i["title"] for i in items] == titles
            for item in items:
                for field in ("instruction_text", "expected_pass", "expected_fail", "diagnosis_if_fail"):
                    assert (item[field] or "").strip(), (slug, item["sequence_number"], field)

    def test_optional_items_are_exactly_the_planned_ones(self, db):
        for slug, optional in OPTIONAL.items():
            got = {i["sequence_number"] for i in _items(db, slug) if not i["required"]}
            assert got == optional, slug

    def test_upgrade_from_70_changes_exactly_the_scoped_rows(self, tmp_path):
        """The rule-1 scope, tested before any live run: 071 changes the
        three generic winterization items that carried F161's figures and
        the chassis steering item (F162), alters no template and nothing
        else, and adds exactly the three templates and their items."""
        path = str(tmp_path / "at_70.db")
        _build_at_70(path)
        templates_70, items_70 = _snapshot(path)
        generic, steering, w30 = _scoped_item_ids(path)
        assert len(generic) == 3 and len(steering) == 1 and len(w30) == 1
        m071 = get_migration_by_version(71)
        apply_migration(m071, path)
        assert get_current_version(path) == m071.version
        templates_71, items_71 = _snapshot(path)

        assert {k for k in templates_70 if templates_71[k] != templates_70[k]} == set()
        assert set(templates_71) - set(templates_70) == set(TEMPLATES)

        changed = {k for k in items_70 if items_71[k] != items_70[k]}
        assert changed == generic | steering | w30
        assert len(items_71) - len(items_70) == sum(len(t) for t in TITLES.values())

    def test_upgrade_changes_only_the_named_fields(self, tmp_path):
        """Within the changed rows, only the fields F161 and F162 name move."""
        path = str(tmp_path / "fields.db")
        _build_at_70(path)
        _, before = _snapshot(path)
        apply_migration(get_migration_by_version(71), path)
        _, after = _snapshot(path)
        conn = sqlite3.connect(path)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(checklist_items)")]
        conn.close()
        generic, steering, w30 = _scoped_item_ids(path)
        moved = {}
        for k in generic | steering | w30:
            moved[k] = {cols[i] for i, (a, b) in enumerate(zip(before[k], after[k])) if a != b}
        assert set().union(*(moved[k] for k in generic)) == {
            "instruction_text", "expected_pass", "expected_fail",
        }
        assert moved[next(iter(steering))] == {"description", "instruction_text"}
        assert moved[next(iter(w30))] == {"description"}

    def test_rollback_restores_every_changed_row(self, tmp_path):
        """Rollback to 70 on a database built at 70 and taken to 71 gives
        back the 70 rows byte-identical, then re-applies."""
        path = str(tmp_path / "round_trip.db")
        _build_at_70(path)
        before = _snapshot(path)
        apply_migration(get_migration_by_version(71), path)
        rollback_to_version(70, path)
        assert get_current_version(path) == 70
        assert _snapshot(path) == before
        conn = sqlite3.connect(path)
        orphans = conn.execute(
            "SELECT COUNT(*) FROM checklist_items WHERE template_id NOT IN "
            "(SELECT id FROM workflow_templates)"
        ).fetchone()[0]
        conn.close()
        assert orphans == 0
        assert 71 in apply_pending_migrations(path)
        for slug, titles in TITLES.items():
            assert len(_items(path, slug)) == len(titles)

    def test_rollback_from_head_peels_every_successor(self, tmp_path):
        path = str(tmp_path / "head.db")
        init_db(path)
        assert get_current_version(path) == SCHEMA_VERSION
        rollback_to_version(70, path)
        assert get_current_version(path) == 70
        for slug in TEMPLATES:
            assert get_template_by_slug(slug, path) is None
        generic = {i["sequence_number"]: i for i in _items(path, "generic_winterization_v1")}
        for (seq, field), old in F161_OLD.items():
            assert generic[seq][field] == old


# --- The three fixes ---


class TestFixes:
    def test_f161_the_figures_are_gone(self, db):
        items = _items(db, "generic_winterization_v1")
        assert len(items) == 4
        for item in items:
            for field in FIELDS:
                for gone in F161_GONE:
                    assert gone not in (item[field] or ""), (item["sequence_number"], field, gone)

    def test_f161_each_changed_field_points_at_the_cited_protocol(self, db):
        generic = {i["sequence_number"]: i for i in _items(db, "generic_winterization_v1")}
        # Refute round 3: the pointer claims only what it points at.
        assert "winterization_v1 gives the fuel steps of the makers it cites" in generic[1]["instruction_text"]
        assert "winterization_v1 gives the oil steps of the makers it cites" in generic[2]["instruction_text"]
        assert "winterization_v1 compares several makers' battery steps, with their pages" in generic[3]["expected_pass"]
        for s in (1, 2, 3):
            assert "each maker's" not in " ".join(generic[s][f] or "" for f in FIELDS)
        # Refute rounds 1-2: each enumeration of the makers here was wrong
        # once; the fix is a pointer and states no maker's step itself.
        assert "after it, or both" not in generic[2]["instruction_text"]
        assert "some makers" not in generic[2]["instruction_text"]
        assert "the makers differ on whether and when" in generic[2]["instruction_text"]
        assert generic[3]["expected_pass"].startswith("Battery kept as the machine's own manual says;")
        # The untouched starter titles and the fourth item stay as seeded.
        assert [generic[s]["title"] for s in (1, 2, 3, 4)] == [
            "Add fuel stabilizer", "Oil change", "Connect battery tender", "Storage position and cover",
        ]

    def test_w30_keeps_its_words_and_gains_its_context(self, db):
        text = _item(db, "winterization_v1", 5)["description"]
        assert "the same manual says that if the vehicle" not in text
        assert "in a caution box on the same page, which also warns about a low electrolyte level before first use" in text
        assert "runs down completely in the course of three months (PDF p. 78; the same words are in its troubleshooting table, PDF p. 55)" in text
        assert text.endswith(
            "The manual gives both figures and does not reconcile them: the six-month check is for a "
            "vehicle stored in open circuit, and the caution does not say whether the battery is connected."
        )

    def test_f162_the_two_sentences(self, db):
        steering = next(
            i for i in _items(db, "ppi_chassis_v1") if i["title"] == "Steering head bearings"
        )
        text = steering["description"] + steering["instruction_text"]
        for old in F162_OLD:
            assert old not in text
        assert F162_NEW[0] in steering["instruction_text"]
        assert F162_NEW[1] in steering["description"]


# --- Content pins (the figure discipline) ---


class TestContentPins:
    def test_every_pinned_figure_is_in_its_field(self, db):
        for (slug, seq, field), needles in PINS.items():
            text = _item(db, slug, seq)[field] or ""
            for needle in needles:
                assert needle in text, f"{slug} item {seq} {field} lost '{needle}'"

    def test_figures_sit_beside_their_machine(self, db):
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

    def test_rules_sit_beside_their_regulator(self, db):
        seen = set()
        for slug in TEMPLATES:
            for item in _items(db, slug):
                for field in FIELDS:
                    text = item[field] or ""
                    for rule, regulator in REGULATOR_OF.items():
                        if rule in text:
                            seen.add(rule)
                            assert regulator in text, (
                                f"{slug} item {item['sequence_number']} {field} states "
                                f"'{rule}' without naming {regulator}"
                            )
        assert seen == set(REGULATOR_OF), "a regulator-bound rule is no longer seeded"

    def test_the_negatives_are_stated(self, db):
        for (slug, seq, field), sentence in NEGATIVE_SENTENCES.items():
            assert sentence in (_item(db, slug, seq)[field] or ""), (slug, seq, field)

    def test_no_frame_measurement_is_invented(self, db):
        """N8: the frame item states no millimetre figure. A planted
        '2 mm' of frame twist breaks this."""
        item = _item(db, "crash_support_v1", 2)
        for field in FIELDS:
            assert not re.search(r"\d\s*mm\b", item[field] or ""), field

    def test_the_insurance_sentence_ships_without_its_killed_words(self, db):
        """Refute round 5, the operator's last, killed calling KTM's ABS notes
        and EPA's line "warnings", and the sentence was dropped (F164). Phase
        381's refute shipped its last wording through migration 086, with
        the DMV clause its round 1 killed deleted; neither killed word
        returns."""
        text = _item(db, "crash_support_v1", 7)["diagnosis_if_fail"]
        assert "690 Duke owner's manual (PDF p. 54)" in text
        assert '"Tampering can void manufacturer warranties and insurance agreements" (PDF p. 2)' in text
        assert "warning" not in text.lower()
        assert "DMV" not in text

    def test_no_race_rule_is_invented(self, db):
        """N10-N12: the event-rules item names no torque, no coolant and no
        wire gauge."""
        item = _item(db, "track_prep_v1", 6)
        for field in FIELDS:
            text = item[field] or ""
            assert not re.search(r"\d\s*(N·?m|mm|%|gauge|AWG)", text), field
            assert "glycol" not in text.lower() and "water only" not in text.lower(), field

    def test_machines_are_named_as_their_documents_name_them(self, db):
        """Names from title pages: YW125Y, never Zuma; Ténéré 700 only
        beside its model code XTZ7T; GTS 310 HPE, the USA edition."""
        for slug in TEMPLATES:
            t = get_template_by_slug(slug, db)
            texts = [t["description"]] + [
                item[f] or "" for item in _items(db, slug) for f in FIELDS
            ]
            for text in texts:
                assert "Zuma" not in text, slug
                if "Ténéré" in text:
                    assert "XTZ7T (Ténéré 700)" in text, slug
                assert not re.search(r"\bPCX(?!150)\b", text), f"{slug} names a bare PCX"


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

    def test_all_three_templates_are_clean(self, db):
        for slug in TEMPLATES:
            t = get_template_by_slug(slug, db)
            self._assert_clean(t["name"], f"{slug} name")
            self._assert_clean(t["description"], f"{slug} description")
            for item in _items(db, slug):
                for field in FIELDS:
                    self._assert_clean(item[field], f"{slug} item {item['sequence_number']} {field}")

    def test_the_fixed_rows_are_clean(self, db):
        for slug in ("generic_winterization_v1", "ppi_chassis_v1"):
            for item in _items(db, slug):
                for field in FIELDS:
                    self._assert_clean(item[field], f"{slug} item {item['sequence_number']} {field}")

    def test_the_pattern_itself_catches_a_planted_reference(self):
        assert re.search(r"\bPhase \d+\b", "expanded in Phase 999")
        assert not re.search(r"\bF\d{2,3}\b", "the BMW F800R rider's manual")


# --- Applicability ---


class TestApplicability:
    def test_powertrain_filters(self, db):
        electric = {t["slug"] for t in list_templates(db, powertrain="electric")}
        assert "crash_support_v1" in electric
        assert not {"track_prep_v1", "emissions_v1"} & electric
        for powertrain in ("ice", "hybrid"):
            slugs = {t["slug"] for t in list_templates(db, powertrain=powertrain)}
            assert set(TEMPLATES) <= slugs, powertrain

    def test_each_category_holds_its_template(self, db):
        for slug, (category, _, _, _) in TEMPLATES.items():
            got = {t["slug"] for t in list_templates(db, category=category)}
            assert got == {slug}, category


# --- The CLI front door ---


class TestCliFrontDoor:
    def test_workflow_list_shows_every_slug_in_full(self, db):
        result = CliRunner().invoke(main_cli, ["workflow", "list"])
        assert result.exit_code == 0, result.output
        for slug in TEMPLATES:
            assert slug in result.output, f"list elided '{slug}'"
        assert "…" not in result.output

    def test_list_by_each_new_category(self, db):
        for slug, (category, _, _, _) in TEMPLATES.items():
            result = CliRunner().invoke(main_cli, ["workflow", "list", "--category", category])
            assert result.exit_code == 0, result.output
            assert slug in result.output
            assert not any(o in result.output for o in set(TEMPLATES) - {slug})

    @pytest.mark.parametrize("slug", sorted(TEMPLATES))
    def test_show_prints_every_item(self, db, slug):
        result = CliRunner().invoke(main_cli, ["workflow", "show", slug])
        assert result.exit_code == 0, result.output
        for title in TITLES[slug]:
            assert title in result.output, f"show {slug} lost '{title}'"
        assert result.output.count("(optional)") == len(OPTIONAL[slug])
        assert "PDF" in result.output
