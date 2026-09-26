"""Phase 264 — Track N batch 2: winterization, de-winterization, engine
break-in and valve adjustment.

Migration 070 seeds four templates on the Phase 114 substrate, one per
ROADMAP row (264 winterization, 265 de-winterization, 266 engine break-in,
268 valve adjustment), reachable through `motodiag workflow list/show`, and
re-points two live rows the operator scoped in:

- `generic_winterization_v1`'s description loses its build reference
  (F158) and names `winterization_v1`;
- `ppi_chassis_v1`'s items name the Yamaha service manual by its title
  page's model code, YW125Y, not "Zuma" (F160).

What these tests pin:

- a fresh `init_db` database holds the four templates and 28 items;
- on an upgrade from a self-built 069 database, 070 changes exactly one
  template row and the three chassis items that said "Zuma", and adds
  exactly the four templates and their items;
- `rollback_to_version(69)` restores every changed row byte-identical (bar
  `updated_at`) and removes the new rows; it re-applies;
- the optional items are exactly the planned ones, and the powertrains
  are S0-5's;
- every figure is present per field, beside the machine it belongs to;
- the negatives are stated, and the no-figure engine-type item carries no
  clearance figure;
- no "Zuma" in any workflow row, and no build reference in the new text
  or the re-pointed description;
- the CLI lists, filters and shows all four.

Migration tests are head-proof (F124): they build a 069 database by
applying migrations up to 069, apply 070 alone, and compare against
`m.version`, never a literal equal to the head.
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
    "winterization_v1": ("winterization", "Winterization — seasonal storage", 90, ALL),
    "de_winterization_v1": (
        "de_winterization", "De-winterization — return to service", 75, ALL,
    ),
    "engine_break_in_v1": ("break_in", "Engine break-in", 30, ENGINE),
    "valve_adjustment_v1": (
        "valve_service", "Valve clearance check and adjustment", 120, ENGINE,
    ),
}

TITLES = {
    "winterization_v1": [
        "Before storage: service, clean and protect",
        "Fuel — full and stabilized, or empty: the machine's own way",
        "Carburetor float chambers (carbureted machines)",
        "Engine oil and cylinder protection",
        "12-V battery — charge it, and keep it charged",
        "Electric machine — the traction battery",
        "Stand, tires, cover and place",
    ],
    "de_winterization_v1": [
        "Uncover, clean and take it off the stand",
        "12-V battery — check the voltage, charge, install",
        "Electric machine — the traction battery",
        "Fuel and engine oil",
        "The maker's before-use checks",
        "Brakes and tire pressures",
        "Test ride",
    ],
    "engine_break_in_v1": [
        "Which break-in applies — new engine or new parts",
        "The limits, by distance — each maker's own measure",
        "How to ride it — vary the load",
        "Cool-down between runs (where the maker asks for it)",
        "First oil change and first service",
        "Trouble during break-in",
    ],
    "valve_adjustment_v1": [
        "Engine cold — by the maker's definition",
        "Piston at TDC on the compression stroke",
        "Measure with a feeler gauge",
        "Adjust — adjusting screw and lock nut",
        "Adjust — shims",
        "Recheck, close up and set the next interval",
        "V-twin — both cylinders, each at its own figure",
        "Inline-four, boxer twin and desmodromic engines — no figure in the library",
    ],
}

# Sequence numbers of the optional items (required = 0), per template.
OPTIONAL = {
    # fuel, carburetor, oil and cylinders: not on an electric machine;
    # the traction battery: only on one.
    "winterization_v1": {2, 3, 4, 6},
    "de_winterization_v1": {3, 4},
    # Only Genuine's manuals ask for cool-downs (N2 narrowed).
    "engine_break_in_v1": {4},
    # A machine has one adjustment method and one engine type.
    "valve_adjustment_v1": {4, 5, 7, 8},
}

FIELDS = (
    "title", "description", "instruction_text",
    "expected_pass", "expected_fail", "diagnosis_if_fail",
)

GENERIC_OLD = (
    "Seasonal storage: fuel stabilization, battery tender, oil change, "
    "storage position. Track N phase 264 expands."
)
GENERIC_NEW = (
    "Seasonal storage: fuel stabilization, battery tender, oil change, "
    "storage position. For the full protocol, with each maker's own figures "
    "cited, see winterization_v1."
)

# Per-field figure pins (259's bug fix #1: a pin over joined fields lets a
# figure corrupted in one field pass because another still carries it).
PINS = {
    # winterization
    ("winterization_v1", 1, "description"): ["checks all parts for function and wear", "(PDF p. 172)", "(PDF p. 117)", "(PDF p. 124)"],
    ("winterization_v1", 1, "instruction_text"): ["60 days or more (PDF pp. 80–81)", "water and humidity cause rust (PDF p. 80)"],
    ("winterization_v1", 1, "diagnosis_if_fail"): ["brake cleaner or acetone", "(PDF p. 80)"],
    ("winterization_v1", 2, "description"): [
        "The makers disagree",
        "runs the engine for 5 minutes to carry treated fuel through the fuel system (PDF p. 81)",
        "lowest-ethanol fuel available (PDF p. 157)",
        "leaves the tank as empty as possible",
        "(PDF p. 172)",
        "aerosol rust-inhibiting oil (PDF p. 60)",
    ],
    ("winterization_v1", 2, "instruction_text"): [
        "the four positions cannot be averaged",
        "5 minutes is the Yamaha XVS95CL's figure (PDF p. 81)",
        "2-stroke oil after it (PDF p. 154)",
        "That run is before storage, not during it",
        "(PDF p. 155)",
    ],
    ("winterization_v1", 2, "diagnosis_if_fail"): ["the fuel from deteriorating (PDF p. 81)", "(KTM 1290 Super Duke R, PDF p. 157)"],
    ("winterization_v1", 3, "description"): ["fuel deposits from building up", "(PDF p. 81)", "(PDF p. 60)"],
    ("winterization_v1", 4, "description"): [
        "No storage procedure in the research library names an oil grade for storage",
        "a teaspoonful of engine oil in each spark plug bore (PDF p. 81)",
        "a tablespoon (15 - 20 cc) into the cylinder (PDF p. 60)",
    ],
    ("winterization_v1", 4, "instruction_text"): ["changes the gear oil instead (PDF p. 154)", "a teaspoonful per cylinder on the Yamaha XVS95CL (PDF p. 81)", "a tablespoon (15 - 20 cc) on the Kymco People S (PDF p. 60)"],
    ("winterization_v1", 5, "description"): [
        "every two weeks in the Honda PCX150 (2013–2017) service manual (PDF p. 390)",
        "once a month in the Yamaha XVS95CL owner's manual (PDF p. 81)",
        "about every 4 months in store, and every 2 months at the latest if left connected",
        "(PDF p. 49)",
        "every six months for a sealed battery stored in open circuit",
        "(PDF p. 78)",
    ],
    ("winterization_v1", 5, "instruction_text"): [
        "limited to 14.4 V (R 850 R / R 1150 R, PDF p. 48)",
        "0–30 °C for the Yamaha XVS95CL (PDF p. 81)",
        "0–35 °C out of direct sunshine for the KTM 690 Enduro (PDF p. 172)",
        "10–20 °C for the lithium-ion battery of the KTM 2022 250/300 EXC TPI (PDF p. 154)",
        "(PDF p. 117)",
    ],
    ("winterization_v1", 6, "description"): ["at least once every three months (PDF p. 9)", "(PDF p. 163)"],
    ("winterization_v1", 6, "instruction_text"): ["about 6 hours to a 60 % state of charge (PDF p. 9)", "at 0 °C to -10 °C"],
    ("winterization_v1", 7, "description"): ["both tires are off the ground (PDF p. 117)", "no load on either wheel (PDF p. 124)", "once a month", "(PDF pp. 154–155)"],
    ("winterization_v1", 7, "instruction_text"): ["a stable (ammonia)", "(XVS95CL, PDF p. 80)", "(KTM EXC TPI, PDF p. 154)"],
    # de-winterization
    ("de_winterization_v1", 1, "instruction_text"): ["(BMW R 850 R / R 1150 R Maintenance Instructions, PDF p. 59)", "the template's own, not a cited document's"],
    ("de_winterization_v1", 2, "description"): ["above 12.60 V", "below 12.60 V", "14.40 ÷ 14.70 V, 10 to 12 hours recommended (PDF p. 78)", "(PDF p. 79)"],
    ("de_winterization_v1", 2, "instruction_text"): ["6 minimum and 24 maximum (PDF p. 78)", "(PDF p. 49)", "time and date if the battery was removed (PDF p. 206)"],
    ("de_winterization_v1", 2, "diagnosis_if_fail"): ["(PDF p. 48)", "deteriorates after 2-3 years even in normal use (PDF p. 390)"],
    ("de_winterization_v1", 3, "instruction_text"): ["to 100 %", "only above 0 °C (PDF p. 9)"],
    ("de_winterization_v1", 3, "diagnosis_if_fail"): ["Below a 10 % state of charge", "(PDF p. 90)"],
    ("de_winterization_v1", 4, "description"): ["if more than 1 month has passed since the start of storage", "(PDF p. 61)", "(PDF p. 173)"],
    ("de_winterization_v1", 5, "instruction_text"): ["(PDF p. 46)", "(PDF p. 25)", "(PDF p. 117)", "(PDF p. 59)"],
    ("de_winterization_v1", 5, "diagnosis_if_fail"): ["a leak or worn linings", "(PDF p. 101)"],
    ("de_winterization_v1", 6, "description"): ['"Check the brakes"', '"Check/correct tyre pressures" (PDF p. 59)', "(PDF p. 79)", "at ambient temperature (PDF p. 58)"],
    ("de_winterization_v1", 7, "description"): ["at low speeds in a safe riding area, away from traffic (PDF p. 61)", "(PDF p. 155)", "(PDF p. 173)"],
    # break-in
    ("engine_break_in_v1", 1, "description"): ['"When your engine is new or when you have installed new engine components" (PDF p. 25)', "the first 1600 km (1000 mi)", "(PDF p. 39)"],
    ("engine_break_in_v1", 1, "diagnosis_if_fail"): ["0 - 100 miles on PDF p. 25", "0~95 miles on PDF p. 27"],
    ("engine_break_in_v1", 2, "description"): [
        "6,000 rpm for the first 1,000 km and 7,800 rpm after (PDF p. 46)",
        "6,500 rpm and then 10,250 rpm (PDF p. 86)",
        "above 3500 r/min from 0 to 1000 km and above 4200 r/min from 1000 to 1600 km (PDF p. 39)",
        "below 5000 rpm until the running-in check (PDF p. 85)",
        "above 1/3 throttle from 0 to 1000 km and above 1/2 throttle from 1000 to 1600 km (PDF p. 41)",
        "less than 1/2 throttle for the initial 300 miles (600 km) and less than 3/4 up to 600 miles (1,000 km)",
        "(PDF p. 23)",
        "under 70 % for the first 3 operating hours (PDF p. 40)",
    ],
    ("engine_break_in_v1", 2, "instruction_text"): [
        "a throttle fraction is not an engine speed",
        "the first 300 miles (500 km)",
        "(PDF p. 14)",
        "below 25 MPH (40 KPH) for its first 600 miles (1,000 km) (PDF p. 40)",
    ],
    ("engine_break_in_v1", 2, "diagnosis_if_fail"): ["increased engine wear", "(PDF p. 66)"],
    ("engine_break_in_v1", 3, "instruction_text"): ["(BMW R 1200 GS, PDF p. 85)", "(PDF p. 66)", "(PDF p. 67)", "(PDF p. 39)", "(PDF p. 23)"],
    ("engine_break_in_v1", 4, "description"): ["no document names heat cycles", "10 minutes after every 30 minutes of operation for the first 100 miles (PDF p. 25)", "5-10 minutes per hour for the first 95 miles (PDF p. 27)"],
    ("engine_break_in_v1", 5, "instruction_text"): [
        "1000 km on the Yamaha XVS95CL, oil and filter (PDF p. 41)",
        "600 mi (1,000 km) or 1 month on the Honda PCX150 (PDF p. 77)",
        "one month or 200 miles (300 km) on the Kymco People S (PDF p. 25)",
        "(PDF p. 23)",
        "between 500 km and 1200 km for the BMW F800R's running-in check (PDF p. 141)",
        "gear oil after 200 miles (PDF p. 27)",
        "(PDF p. 67)",
    ],
    ("engine_break_in_v1", 5, "description"): ["(PDF p. 3)"],
    ("engine_break_in_v1", 6, "instruction_text"): ["immediately (Yamaha XVS95CL, PDF p. 42)", "1,400 … 1,500 rpm", "(PDF p. 40)"],
    # valve adjustment
    ("valve_adjustment_v1", 1, "description"): ["below 35 °C (95 °F)", "(PDF p. 82)", "(PDF p. 64)", "(PDF p. 59)", '"a cold engine, at room temperature"', "(PDF p. 62)", "20 °C (68 °F)", "(PDF p. 209)"],
    ("valve_adjustment_v1", 2, "instruction_text"): ["counterclockwise on the Yamaha YW125Y, PDF p. 62", "no slack means one more full turn (PDF p. 82)", "one more revolution (PDF p. 64)"],
    ("valve_adjustment_v1", 2, "description"): ["(PDF pp. 62–63)"],
    ("valve_adjustment_v1", 3, "description"): [
        "intake 0.10 ~ 0.14 mm and exhaust 0.16 ~ 0.20 mm (PDF p. 62)",
        "intake 0.10 ± 0.02 mm and exhaust 0.24 ± 0.02 mm (PDF p. 82)",
        "intake 0.10 ± 0.03 mm and exhaust 0.19 ± 0.03 mm (PDF p. 64)",
        "intake 0.1 mm and exhaust 0.1 mm (PDF p. 59)",
        "valve play cold 0.07… 0.13 mm (PDF p. 174)",
        "intake 0.10 mm and exhaust 0.15 mm (PDF p. 9)",
    ],
    ("valve_adjustment_v1", 3, "instruction_text"): ["(Honda PCX150, PDF p. 82)", "(Honda CHF50, PDF p. 64)", "slight drag on the feeler gauge (PCX150, PDF p. 83)"],
    ("valve_adjustment_v1", 3, "diagnosis_if_fail"): ["low compression", "(PDF p. 60)", "(PDF p. 58)"],
    ("valve_adjustment_v1", 4, "description"): ["7 Nm (PDF p. 63)", "(PDF p. 64)", "10 N·m (PDF p. 83)", "8.8 N-m with engine oil on the threads (PDF p. 81)", "(PDF p. 59)"],
    ("valve_adjustment_v1", 4, "instruction_text"): [
        "7 Nm on the Yamaha YW125Y (PDF p. 63)",
        "10 N·m on the Honda PCX150 (PDF p. 83)",
        "6 ÷ 8 Nm for the tappet set screw lock nut on the Vespa GTS Super 300 ie (PDF p. 16)",
        "90890-01311 (PDF p. 63)",
    ],
    ("valve_adjustment_v1", 5, "description"): ["A = (B - C) + D", "sixty-nine thicknesses", "from 1.200 mm to 2.900 mm in 0.025 mm increments (PDF p. 65)"],
    ("valve_adjustment_v1", 5, "diagnosis_if_fail"): ["over 2.900 mm", "(PDF p. 65)"],
    ("valve_adjustment_v1", 6, "description"): ["7 Nm and the spark plug at 13 Nm (PDF p. 64)", "(PDF p. 83)", "every 16000 mi (25000 km) on the Yamaha XVS95CL", "(PDF p. 45)"],
    ("valve_adjustment_v1", 7, "description"): [
        "75° V arrangement",
        "intake 0.10… 0.15 mm, exhaust 0.25… 0.30 mm (PDF p. 209)",
        "the same figures at 20 °C (PDF p. 161)",
        "V-type 2-cylinder (PDF p. 82)",
        "every 16000 mi (25000 km), by a Yamaha dealer (PDF p. 45)",
    ],
    ("valve_adjustment_v1", 7, "instruction_text"): ["that method is the template's own", "(PDF p. 103)", "(PDF p. 58)"],
    ("valve_adjustment_v1", 8, "description"): ["every 26600 mi (42000 km), by a Yamaha dealer (PDF p. 60)", "bucket-type tappets", "(PDF p. 63)", "tappets and short pushrods (PDF p. 80)", '"Check/adjust valve clearances" (PDF p. 7)'],
}

# A figure that belongs to one machine must sit in a field that names it.
MACHINE_OF = {
    "7,800 rpm": "690 Enduro", "10,250 rpm": "1190 Adventure", "4200 r/min": "SR400",
    "1/3 throttle": "XVS95CL", "3/4 up to": "People S", "70 %": "EXC TPI",
    "0.16 ~ 0.20 mm": "YW125Y", "0.24 ± 0.02 mm": "PCX150", "0.19 ± 0.03 mm": "CHF50",
    "0.07… 0.13 mm": "690 Enduro", "0.25… 0.30 mm": "1190 Adventure", "0.15 mm (PDF p. 9)": "GTS Super 300",
    "8.8 N-m": "People S 250", "10 N·m": "PCX150", "12.60 V": "Beverly", "14.4 V": "R 850 R / R 1150 R",
    "10–20 °C": "EXC TPI", "0–30 °C": "XVS95CL", "every two weeks": "PCX150", "60 %": "Elettrica",
    "15 - 20 cc": "People S", "26600 mi": "YZFR6L", "16000 mi": "XVS95CL", "13 Nm": "YW125Y",
}

# The negatives (264_step0.md), each where the content relies on it.
NEGATIVE_SENTENCES = {
    ("winterization_v1", 4, "description"):
        "No storage procedure in the research library names an oil grade for storage",
    ("de_winterization_v1", 6, "description"):
        "No maker's document in the research library asks for the brakes to be exercised after storage",
    ("engine_break_in_v1", 1, "description"):
        "No service manual in the research library gives a separate break-in after an engine or top-end rebuild",
    ("engine_break_in_v1", 4, "description"):
        "Only one maker in the research library prescribes a cool-down, and no document names heat cycles",
    ("valve_adjustment_v1", 8, "description"):
        "No document in the research library gives a valve clearance figure for an inline-four or a boxer twin, and none covers a desmodromic valve train",
}

CLEARANCE = re.compile(r"\d+(?:\.\d+)?\s*(?:…|~|-|–|±)?\s*\d*(?:\.\d+)?\s*mm\b")


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


def _build_at_69(path):
    """A 069 database built here: migrations up to 069 only, never a copy of
    data/motodiag.db and never a rollback of 070."""
    init_db(path, apply_migrations=False)
    for m in sorted(MIGRATIONS, key=lambda m: m.version):
        if get_current_version(path) < m.version <= 69:
            apply_migration(m, path)
    assert get_current_version(path) == 69


def _snapshot(path):
    """Templates keyed by slug with `updated_at` (column 11) dropped; items
    keyed by id."""
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


def _chassis_zuma_item_ids(path):
    conn = sqlite3.connect(path)
    ids = {
        r[0] for r in conn.execute(
            "SELECT i.id FROM checklist_items i JOIN workflow_templates t "
            "ON t.id = i.template_id WHERE t.slug = 'ppi_chassis_v1' AND "
            "(i.title || i.description || i.instruction_text || i.expected_pass "
            "|| i.expected_fail || i.diagnosis_if_fail) LIKE '%Zuma%'"
        )
    }
    conn.close()
    return ids


# --- Migration 070 ---


class TestMigration070:
    def test_schema_version_floor_pin(self):
        """F124: never a literal equality to the head."""
        assert SCHEMA_VERSION >= 70

    def test_migration_070_exists_by_name(self):
        m = get_migration_by_version(70)
        assert m is not None
        assert m.name == "seasonal_breakin_valve_workflows"

    def test_every_migration_keeps_its_rollback(self):
        """260's bug fix #1 guard, re-run with 070 inserted."""
        assert [m.version for m in MIGRATIONS if not m.rollback_sql.strip()] == []
        rollback = get_migration_by_version(70).rollback_sql
        for slug in TEMPLATES:
            assert f"'{slug}'" in rollback
        assert "'generic_winterization_v1'" in rollback
        assert "'ppi_chassis_v1'" in rollback

    def test_fresh_init_seeds_the_four_templates(self, db):
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

    def test_upgrade_from_69_changes_exactly_the_scoped_rows(self, tmp_path):
        """The rule-1 scope, tested before any live run: 070 changes one
        template (generic_winterization_v1's description) and the three
        ppi_chassis_v1 items that named "Zuma", alters nothing else, and
        adds exactly the four templates and their 28 items."""
        path = str(tmp_path / "at_69.db")
        _build_at_69(path)
        templates_69, items_69 = _snapshot(path)
        zuma_ids = _chassis_zuma_item_ids(path)
        assert len(zuma_ids) == 3
        m070 = get_migration_by_version(70)
        apply_migration(m070, path)
        assert get_current_version(path) == m070.version
        templates_70, items_70 = _snapshot(path)

        changed_t = {k for k in templates_69 if templates_70[k] != templates_69[k]}
        assert changed_t == {"generic_winterization_v1"}
        assert set(templates_70) - set(templates_69) == set(TEMPLATES)

        changed_i = {k for k in items_69 if items_70[k] != items_69[k]}
        assert changed_i == zuma_ids
        assert len(items_70) - len(items_69) == sum(len(t) for t in TITLES.values())
        assert _chassis_zuma_item_ids(path) == set()

    def test_rollback_restores_every_changed_row(self, tmp_path):
        """Rollback to 69 on a database built at 69 and taken to 70 gives
        back the 69 rows byte-identical (bar updated_at), then re-applies."""
        path = str(tmp_path / "round_trip.db")
        _build_at_69(path)
        before = _snapshot(path)
        apply_migration(get_migration_by_version(70), path)
        rollback_to_version(69, path)
        assert get_current_version(path) == 69
        assert _snapshot(path) == before
        conn = sqlite3.connect(path)
        orphans = conn.execute(
            "SELECT COUNT(*) FROM checklist_items WHERE template_id NOT IN "
            "(SELECT id FROM workflow_templates)"
        ).fetchone()[0]
        conn.close()
        assert orphans == 0
        assert 70 in apply_pending_migrations(path)
        for slug, titles in TITLES.items():
            assert len(_items(path, slug)) == len(titles)

    def test_rollback_from_head_peels_every_successor(self, tmp_path):
        path = str(tmp_path / "head.db")
        init_db(path)
        assert get_current_version(path) == SCHEMA_VERSION
        rollback_to_version(69, path)
        assert get_current_version(path) == 69
        for slug in TEMPLATES:
            assert get_template_by_slug(slug, path) is None
        assert get_template_by_slug("generic_winterization_v1", path)["description"] == GENERIC_OLD


# --- The two live re-points ---


class TestRepoints:
    def test_generic_winterization_names_the_protocol(self, db):
        """F158: the build reference goes, and the text names the slug."""
        t = get_template_by_slug("generic_winterization_v1", db)
        assert t["description"] == GENERIC_NEW
        assert len(get_checklist_items(t["id"], db)) == 4

    def test_no_zuma_in_any_workflow_row(self, db):
        """F160: the YW125Y service manual's title page carries "Model :
        YW125Y" and "Zuma" is on none of its 338 pages."""
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT slug, name, description FROM workflow_templates"
        ).fetchall()
        items = conn.execute(
            f"SELECT {', '.join(FIELDS)} FROM checklist_items"
        ).fetchall()
        conn.close()
        for row in rows + items:
            for text in row:
                assert "Zuma" not in (text or ""), row[0]

    def test_chassis_items_name_the_yw125y(self, db):
        by_title = {i["title"]: i for i in _items(db, "ppi_chassis_v1")}
        steering = by_title["Steering head bearings"]
        assert "the Yamaha YW125Y 2009 service manual (PDF p. 93)" in steering["description"]
        assert "The YW125Y manual's adjustment" in steering["instruction_text"]
        assert "the YW125Y service manual calls" in steering["instruction_text"]
        fork = by_title["Front fork — seals, stanchions and action"]
        assert "the YW125Y's fork spring measures 252.1 mm" in fork["diagnosis_if_fail"]
        wheels = by_title["Wheel bearings and rims"]
        assert "the YW125Y manual's table check" in wheels["instruction_text"]
        total = sum(
            (i[f] or "").count("YW125Y") for i in by_title.values() for f in FIELDS
        )
        assert total == 8


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

    def test_machines_are_named_as_their_documents_name_them(self, db):
        """Names from title pages: YW125Y, never Zuma; PCX150, never a bare
        PCX; XVS95CL and XV250T1; YZFR6L; the Buddy 125."""
        for slug in TEMPLATES:
            t = get_template_by_slug(slug, db)
            texts = [t["description"]] + [
                item[f] or "" for item in _items(db, slug) for f in FIELDS
            ]
            for text in texts:
                for wrong in ("Zuma", "XVS950", "XVS1300", "Bolt", "V Star", "Vino"):
                    assert wrong not in text, f"{slug} names '{wrong}'"
                assert not re.search(r"\bPCX(?!150)\b", text), f"{slug} names a bare PCX"

    def test_the_negatives_are_stated(self, db):
        for (slug, seq, field), sentence in NEGATIVE_SENTENCES.items():
            assert sentence in (_item(db, slug, seq)[field] or ""), (slug, seq, field)

    def test_no_figure_item_carries_no_clearance(self, db):
        """N1, N4, N5: the inline-four / boxer / desmodromic item states no
        millimetre figure at all. A planted '0.15 mm' breaks this."""
        item = _item(db, "valve_adjustment_v1", 8)
        for field in FIELDS:
            assert not CLEARANCE.search(item[field] or ""), field

    def test_the_clearance_pattern_catches_a_planted_figure(self):
        assert CLEARANCE.search("intake 0.15 mm")
        assert CLEARANCE.search("0.10… 0.15 mm")
        assert not CLEARANCE.search("every 26600 mi (42000 km)")

    def test_chf50_intake_tolerance_is_the_rendered_one(self, db):
        """The CHF50 page's text layer reads "0.10 + 0.03"; the rendered page
        reads ±. The content carries the rendered figure."""
        text = _item(db, "valve_adjustment_v1", 3)["description"]
        assert "0.10 + 0.03" not in text
        assert "intake 0.10 ± 0.03 mm" in text

    def test_rebuild_advice_is_marked_as_the_templates_own(self, db):
        text = _item(db, "engine_break_in_v1", 1)["instruction_text"]
        assert "the template's own recommendation, not a cited document's" in text


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

    def test_the_repointed_description_is_clean(self, db):
        t = get_template_by_slug("generic_winterization_v1", db)
        self._assert_clean(t["description"], "generic_winterization_v1 description")

    def test_the_pattern_itself_catches_a_planted_reference(self):
        assert re.search(r"\bTrack [A-Z]\b", GENERIC_OLD)
        assert re.search(r"\bPhase \d+\b", "expanded in Phase 999")
        assert not re.search(r"\bF\d{2,3}\b", "the BMW F800R rider's manual")


# --- Applicability ---


class TestApplicability:
    def test_powertrain_filters(self, db):
        electric = {t["slug"] for t in list_templates(db, powertrain="electric")}
        assert {"winterization_v1", "de_winterization_v1"} <= electric
        assert not {"engine_break_in_v1", "valve_adjustment_v1"} & electric
        for powertrain in ("ice", "hybrid"):
            slugs = {t["slug"] for t in list_templates(db, powertrain=powertrain)}
            assert set(TEMPLATES) <= slugs, powertrain

    def test_each_category_holds_its_template(self, db):
        for slug, (category, _, _, _) in TEMPLATES.items():
            got = {t["slug"] for t in list_templates(db, category=category)}
            expected = {slug} | ({"generic_winterization_v1"} if category == "winterization" else set())
            assert got == expected, category


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
            # A word boundary: winterization_v1 is inside de_winterization_v1.
            others = set(TEMPLATES) - {slug}
            assert not any(re.search(rf"(?<![a-z_]){o}", result.output) for o in others)

    @pytest.mark.parametrize("slug", sorted(TEMPLATES))
    def test_show_prints_every_item(self, db, slug):
        result = CliRunner().invoke(main_cli, ["workflow", "show", slug])
        assert result.exit_code == 0, result.output
        for title in TITLES[slug]:
            assert title in result.output, f"show {slug} lost '{title}'"
        assert result.output.count("(optional)") == len(OPTIONAL[slug])
        assert "PDF" in result.output
