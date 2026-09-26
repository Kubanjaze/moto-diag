"""Phase 272 — Gate 15: Track N's five workflows walked end-to-end through
the workflow door, once per powertrain.

ROADMAP row 272 read "Run PPI → tire service → winterization → valve
adjust → brake service end-to-end". No workflow can be run (F165): the
door is `motodiag workflow list` and `motodiag workflow show`. So the gate
walks the row's order through those two commands, on a freshly migrated
database, once per powertrain, reading applicability only from what the
commands print, and checks:

- W1 `list` and `show` print the same powertrains, and those are the
  repository's;
- W2 powertrain P's walk visits, in the row's order, exactly the row's
  templates whose printed powertrains name P;
- W3 every walked template shows its items numbered 1…n, each with a
  Pass and a Fail line;
- W4 no required step on P's walk has a title naming work P does not
  have (engine work on an electric, traction-battery work on an ICE);
  the one measured exception is `generic_ppi_v1` item 3 (F166);
- every reference from one template's text to another, in each form
  Step 0 censused, resolves to an active template and an existing item;
- every live template is reachable through `list --category` and `show`;
- the walk prints no build reference (F158);
- migrations from 067 on: fresh databases agree, and every rollback
  peels its successors. The head comes from SCHEMA_VERSION, never a
  literal (F124), so the next migration joins these checks.

Every checker has a planted control below. No test reads data/motodiag.db.
"""

import re
import sqlite3

import pytest
from click.testing import CliRunner

from motodiag.cli.main import cli as main_cli
from motodiag.cli.theme import reset_console
from motodiag.core.config import reset_settings
from motodiag.core.database import SCHEMA_VERSION, init_db
from motodiag.core.migrations import (
    MIGRATIONS,
    apply_migration,
    get_current_version,
    rollback_to_version,
)
from motodiag.workflows import get_checklist_items, list_templates


POWERTRAINS = ("ice", "electric", "hybrid")

# Row 272's order: each stage's templates, in the order a shop works them.
ROW = (
    ("PPI", ("generic_ppi_v1", "ppi_engine_v1", "ppi_chassis_v1")),
    ("tire service", ("tire_service_v1",)),
    ("winterization", (
        "generic_winterization_v1", "winterization_v1", "de_winterization_v1",
    )),
    ("valve adjustment", ("valve_adjustment_v1",)),
    ("brake service", ("brake_service_v1",)),
)

# W4's vocabularies, matched on a step's title (272_step0.md, S0-4).
ENGINE_WORK = re.compile(
    r"\b(engine|compression|leak-?down|valves?|carbur\w*|spark plugs?|fuel"
    r"|choke|idle|exhaust|emissions?|catalytic|evaporative)\b",
    re.IGNORECASE,
)
TRACTION_WORK = re.compile(
    r"\b(traction|high-voltage|HV|electric machine)\b", re.IGNORECASE,
)
# The work each powertrain does not have. A hybrid has both.
LACKS = {"electric": ENGINE_WORK, "ice": TRACTION_WORK, "hybrid": None}

# W4's one measured exception: a required engine compression test in a
# template that covers electric (F166). Equality, not a subset: a new
# violation fails, and so does fixing this one without updating the gate.
KNOWN_WRONG_POWERTRAIN_STEPS = {("electric", "generic_ppi_v1", 3)}

# The reference forms Step 0 censused (S0-3). A slug; an item, optionally
# qualified by a slug ("winterization_v1, item 7"), singly or as a range.
SLUG_REF = re.compile(r"\b[a-z][a-z0-9_]*_v\d+\b")
ITEM_REF = re.compile(
    r"\b(?:(?P<slug>[a-z][a-z0-9_]*_v\d+), )?[Ii]tems? (?P<a>\d+)"
    r"(?:(?: to | and |[–-])(?P<b>\d+))?\b"
)

# The links Step 0 found, which the link check must find before it is
# trusted to find none broken. de_winterization_v1 names five.
KNOWN_LINKS = {
    ("de_winterization_v1", "winterization_v1"),
    ("de_winterization_v1", "brake_service_v1"),
    ("de_winterization_v1", "tire_service_v1"),
    ("de_winterization_v1", "suspension_service_v1"),
    ("de_winterization_v1", "drivetrain_service_v1"),
    ("generic_ppi_v1", "ppi_engine_v1"),
    ("ppi_engine_v1", "generic_ppi_v1"),
    ("ppi_engine_v1", "ppi_chassis_v1"),
    ("ppi_chassis_v1", "generic_ppi_v1"),
    ("ppi_chassis_v1", "ppi_engine_v1"),
    ("generic_winterization_v1", "winterization_v1"),
    ("winterization_v1", "de_winterization_v1"),
    ("winterization_v1", "tire_service_v1"),
    ("crash_support_v1", "brake_service_v1"),
    ("track_prep_v1", "suspension_service_v1"),
    ("track_prep_v1", "brake_service_v1"),
}
# Step 0's counts, as floors: content may add references, never lose these.
CENSUS_SLUG_REFS = 22
CENSUS_ITEM_REFS = 13

BUILD_REFERENCES = (
    r"\bPhase \d+\b",
    r"\bTrack [A-Z]\b",
    r"this phase",
    r"\bF\d{2,3}\b",
)

# Wide enough that no item title or table row wraps (theme.get_console
# honours COLUMNS). One test below reads `list` at 80 columns as well.
WIDE = 10000

# Track N's content migrations start here. A floor, not the head.
TRACK_N_FIRST = 67


# --- The door ---


def _cli(db_path, *args, columns=WIDE):
    """`motodiag workflow <args>` against db_path, through the real CLI root.

    `reset_settings` rebuilds the settings at once, so the environment is
    set before it, and restored (and the settings rebuilt) after.
    """
    try:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("MOTODIAG_DB_PATH", db_path)
            mp.setenv("COLUMNS", str(columns))
            reset_settings()
            reset_console()
            return CliRunner().invoke(main_cli, ["workflow", *args])
    finally:
        reset_settings()
        reset_console()


def _powertrains(cell):
    return {p for p in cell.replace(" ", "").split(",") if p}


def parse_list(output):
    """{slug: {"category", "powertrains"}} from `workflow list`'s table.

    A row that wraps continues on lines whose Slug cell is empty; their
    Powertrains cells are joined to the row's.
    """
    rows = {}
    current = None
    for line in output.splitlines():
        if not line.startswith("│"):
            continue
        cells = [c.strip() for c in line.strip().strip("│").split("│")]
        if len(cells) != 5:
            continue
        if cells[0]:
            current = {"category": cells[1], "cells": [cells[3]]}
            rows[cells[0]] = current
        elif current is not None:
            current["cells"].append(cells[3])
    return {
        slug: {"category": r["category"], "powertrains": _powertrains("".join(r["cells"]))}
        for slug, r in rows.items()
    }


SHOW_HEADER = re.compile(
    r"^(?P<slug>[a-z0-9_]+) · category (?P<category>[a-z_]+)"
    r" · for (?P<powertrains>[a-z, ]+) · ~"
)
ITEM_HEADER = re.compile(r"^(?P<seq>\d+)\. (?P<title>.+?)(?P<optional> \(optional\))?(?: · \d+ min)?$")


def parse_show(output):
    """The header, the items and the body text of `workflow show <slug>`.

    An item starts at a numbered line after a blank line; its Pass and
    Fail lines follow it. The body is everything but the header line, so
    a template's own slug there is not read as a link.
    """
    lines = output.splitlines()
    header = next(SHOW_HEADER.match(line) for line in lines if SHOW_HEADER.match(line))
    items = []
    body = []
    for i, line in enumerate(lines):
        if SHOW_HEADER.match(line):
            continue
        body.append(line)
        m = ITEM_HEADER.match(line)
        if m and i > 0 and lines[i - 1] == "":
            items.append({
                "seq": int(m["seq"]),
                "title": m["title"],
                "required": m["optional"] is None,
                "pass": False,
                "fail": False,
            })
        elif items and line.startswith("  Pass: "):
            items[-1]["pass"] = True
        elif items and line.startswith("  Fail: "):
            items[-1]["fail"] = True
    return {
        "slug": header["slug"],
        "category": header["category"],
        "powertrains": _powertrains(header["powertrains"]),
        "items": items,
        "body": " ".join(" ".join(body).split()),
    }


def walk(db_path, powertrain):
    """Row 272's order for one powertrain, through `list` and `show` only.

    A template is walked when its printed powertrains name the powertrain,
    and skipped otherwise; both are recorded with the stage.
    """
    record = {"visited": [], "skipped": [], "outputs": [], "listed": {}}
    listing = _cli(db_path, "list")
    assert listing.exit_code == 0, listing.output
    record["outputs"].append(listing.output)
    listed = parse_list(listing.output)
    for stage, slugs in ROW:
        for slug in slugs:
            shown = _cli(db_path, "show", slug)
            assert shown.exit_code == 0, f"show {slug}: {shown.output}"
            record["outputs"].append(shown.output)
            template = parse_show(shown.output)
            by_category = _cli(db_path, "list", "--category", template["category"])
            assert by_category.exit_code == 0, by_category.output
            record["outputs"].append(by_category.output)
            record["listed"][slug] = (listed.get(slug), parse_list(by_category.output).get(slug))
            if powertrain in template["powertrains"]:
                record["visited"].append((stage, slug, template))
            else:
                record["skipped"].append((stage, slug))
    return record


def wrong_powertrain_steps(walks):
    """(powertrain, slug, seq) for each required step whose title names
    work that powertrain does not have (W4)."""
    found = set()
    for powertrain, record in walks.items():
        lacks = LACKS[powertrain]
        if lacks is None:
            continue
        for _stage, slug, template in record["visited"]:
            for item in template["items"]:
                if item["required"] and lacks.search(item["title"]):
                    found.add((powertrain, slug, item["seq"]))
    return found


def _item_numbers(match):
    a = int(match["a"])
    b = int(match["b"]) if match["b"] else a
    return range(a, b + 1)


def template_links(db_path):
    """Every live template's references, read from its `show` output.

    Returns (listed slugs, {slug: parsed show}, slug refs, item refs),
    where a slug ref is (source, target) and an item ref is
    (source, target, seq).
    """
    listing = _cli(db_path, "list")
    assert listing.exit_code == 0, listing.output
    listed = set(parse_list(listing.output))
    shows = {}
    slug_refs = []
    item_refs = []
    for slug in sorted(listed):
        shown = _cli(db_path, "show", slug)
        assert shown.exit_code == 0, shown.output
        template = parse_show(shown.output)
        shows[slug] = template
        for m in SLUG_REF.finditer(template["body"]):
            slug_refs.append((slug, m.group()))
        for m in ITEM_REF.finditer(template["body"]):
            target = m["slug"] or slug
            item_refs.extend((slug, target, n) for n in _item_numbers(m))
    return listed, shows, slug_refs, item_refs


def broken_links(db_path):
    """References that do not resolve: a slug `list` does not print, or an
    item number the target's `show` does not print."""
    listed, shows, slug_refs, item_refs = template_links(db_path)
    broken = [(s, t) for s, t in slug_refs if t not in listed]
    for source, target, seq in item_refs:
        if target not in shows or seq not in {i["seq"] for i in shows[target]["items"]}:
            broken.append((source, f"{target} item {seq}"))
    return broken


def build_references(outputs):
    text = " ".join(" ".join(o.split()) for o in outputs)
    return [
        m.group()
        for pattern in BUILD_REFERENCES
        for m in re.finditer(pattern, text, re.IGNORECASE)
    ]


# --- Fixtures ---


@pytest.fixture(scope="module")
def gate_db(tmp_path_factory):
    """One freshly migrated database for the whole walk."""
    path = str(tmp_path_factory.mktemp("gate15") / "motodiag.db")
    init_db(path)
    return path


@pytest.fixture(scope="module")
def walks(gate_db):
    return {p: walk(gate_db, p) for p in POWERTRAINS}


@pytest.fixture
def fresh_db(tmp_path):
    path = str(tmp_path / "motodiag.db")
    init_db(path)
    return path


def _execute(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    conn.execute(sql, params)
    conn.commit()
    conn.close()


# --- The walk, per powertrain ---


class TestTheWalk:
    def test_list_and_show_agree_with_the_repository(self, gate_db, walks):
        """W1, and the parser's control: what the walk read from the
        printed text is what the repository holds."""
        repo = {t["slug"]: t for t in list_templates(gate_db, is_active=True)}
        record = walks["ice"]
        for _stage, slugs in ROW:
            for slug in slugs:
                in_list, in_category = record["listed"][slug]
                shown = next(
                    (t for _, s, t in record["visited"] if s == slug), None
                )
                assert in_list is not None, f"list did not print {slug}"
                assert in_category is not None, f"list --category did not print {slug}"
                expected = set(repo[slug]["applicable_powertrains"])
                assert in_list["powertrains"] == expected, slug
                assert in_category["powertrains"] == expected, slug
                assert in_list["category"] == repo[slug]["category"], slug
                if shown is not None:
                    assert shown["powertrains"] == expected, slug

    @pytest.mark.parametrize("powertrain", POWERTRAINS)
    def test_the_walk_visits_exactly_the_templates_that_name_it(self, walks, powertrain):
        """W2: in the row's order, the walked templates are exactly those
        whose printed powertrains name the powertrain."""
        record = walks[powertrain]
        visited = [slug for _, slug, _ in record["visited"]]
        in_order = [s for _, slugs in ROW for s in slugs]
        assert visited == [s for s in in_order if s in visited]
        for _stage, slug, template in record["visited"]:
            assert powertrain in template["powertrains"], slug
        for _stage, slug in record["skipped"]:
            in_list, _ = record["listed"][slug]
            assert powertrain not in in_list["powertrains"], slug
        assert len(visited) + len(record["skipped"]) == len(in_order)
        assert visited, f"the {powertrain} walk visited nothing"

    @pytest.mark.parametrize("powertrain", POWERTRAINS)
    def test_every_walked_template_shows_its_whole_checklist(self, gate_db, walks, powertrain):
        """W3: items 1…n without a gap, each with Pass and Fail, and n is
        the repository's item count."""
        for _stage, slug, template in walks[powertrain]["visited"]:
            seqs = [i["seq"] for i in template["items"]]
            assert seqs == list(range(1, len(seqs) + 1)), f"{slug}: {seqs}"
            repo_items = get_checklist_items(
                next(t["id"] for t in list_templates(gate_db) if t["slug"] == slug), gate_db,
            )
            assert len(seqs) == len(repo_items), slug
            for item, row in zip(template["items"], repo_items):
                assert item["pass"] and item["fail"], f"{slug} item {item['seq']}"
                # W4 reads these two from the print: they must be the rows'.
                assert item["title"] == row["title"], f"{slug} item {item['seq']}"
                assert item["required"] == bool(row["required"]), f"{slug} item {item['seq']}"

    def test_no_required_step_names_work_its_powertrain_lacks(self, walks):
        """W4, with its one measured exception (F166)."""
        assert wrong_powertrain_steps(walks) == KNOWN_WRONG_POWERTRAIN_STEPS

    def test_the_vocabularies_find_the_known_powertrain_steps(self, walks):
        """W4's control: the vocabularies find the engine-only and
        traction-battery steps Step 0 found, so the only thing keeping the
        optional ones off the violation list is that they are optional."""
        titles = {
            (slug, item["seq"]): item
            for _, slug, template in walks["ice"]["visited"] + walks["electric"]["visited"]
            for item in template["items"]
        }
        engine = {k for k, i in titles.items() if ENGINE_WORK.search(i["title"])}
        traction = {k for k, i in titles.items() if TRACTION_WORK.search(i["title"])}
        optional_engine = {
            ("winterization_v1", 2), ("winterization_v1", 3),
            ("winterization_v1", 4), ("de_winterization_v1", 4),
        }
        optional_traction = {("winterization_v1", 6), ("de_winterization_v1", 3)}
        assert optional_engine | {("generic_ppi_v1", 3), ("valve_adjustment_v1", 1)} <= engine
        assert optional_traction <= traction
        for key in optional_engine | optional_traction:
            assert not titles[key]["required"], key


class TestTheWalkControls:
    """The checkers, fed planted input. The phase log records the same
    plants made in the gate's own fixture, red, then removed."""

    def test_a_valve_adjustment_step_on_an_electric_walk_is_caught(self, fresh_db):
        _execute(
            fresh_db,
            "INSERT INTO checklist_items (template_id, sequence_number, title,"
            " instruction_text, expected_pass, expected_fail, required)"
            " SELECT id, 99, 'Valve clearance — check and adjust', 'x', 'x', 'x', 1"
            " FROM workflow_templates WHERE slug = 'brake_service_v1'",
        )
        found = wrong_powertrain_steps({"electric": walk(fresh_db, "electric")})
        assert ("electric", "brake_service_v1", 99) in found

    def test_valve_adjustment_made_to_cover_electric_is_caught(self, fresh_db):
        _execute(
            fresh_db,
            "UPDATE workflow_templates SET applicable_powertrains ="
            " '[\"ice\",\"electric\",\"hybrid\"]' WHERE slug = 'valve_adjustment_v1'",
        )
        record = walk(fresh_db, "electric")
        assert "valve_adjustment_v1" in [s for _, s, _ in record["visited"]]
        found = wrong_powertrain_steps({"electric": record})
        assert ("electric", "valve_adjustment_v1", 1) in found

    def test_the_parser_joins_a_wrapped_row(self, gate_db):
        """At 80 columns `list` folds the Powertrains cell over lines."""
        narrow = _cli(gate_db, "list", columns=80)
        assert narrow.exit_code == 0, narrow.output
        assert "ice,\n" in narrow.output.replace(" ", "").replace("│", "\n")
        wide = _cli(gate_db, "list")
        assert parse_list(narrow.output) == parse_list(wide.output)
        assert len(parse_list(wide.output)) == len(list_templates(gate_db, is_active=True))


# --- The links between templates ---


class TestTheLinks:
    def test_the_check_finds_the_known_links(self, gate_db):
        listed, shows, slug_refs, item_refs = template_links(gate_db)
        assert KNOWN_LINKS <= set(slug_refs)
        named = {t for s, t in slug_refs if s == "de_winterization_v1"}
        assert len(named) == 5, named
        assert len(slug_refs) >= CENSUS_SLUG_REFS
        assert ("de_winterization_v1", "winterization_v1", 7) in item_refs
        assert sum(1 for m in shows.values() for _ in ITEM_REF.finditer(m["body"])) >= CENSUS_ITEM_REFS

    def test_every_link_resolves(self, gate_db):
        _, _, slug_refs, _ = template_links(gate_db)
        assert KNOWN_LINKS <= set(slug_refs), "the extractor lost a known link"
        assert broken_links(gate_db) == []

    def test_a_misspelt_slug_is_caught(self, fresh_db):
        _execute(
            fresh_db,
            "UPDATE checklist_items SET diagnosis_if_fail ="
            " replace(diagnosis_if_fail, 'brake_service_v1', 'brake_servce_v1')"
            " WHERE sequence_number = 6 AND template_id ="
            " (SELECT id FROM workflow_templates WHERE slug = 'de_winterization_v1')",
        )
        assert ("de_winterization_v1", "brake_servce_v1") in broken_links(fresh_db)

    def test_a_link_to_an_inactive_template_is_caught(self, fresh_db):
        _execute(fresh_db, "UPDATE workflow_templates SET is_active = 0 WHERE slug = 'tire_service_v1'")
        broken = broken_links(fresh_db)
        assert ("winterization_v1", "tire_service_v1") in broken
        assert ("de_winterization_v1", "tire_service_v1") in broken

    def test_an_item_that_does_not_exist_is_caught(self, fresh_db):
        _execute(
            fresh_db,
            "UPDATE checklist_items SET diagnosis_if_fail ="
            " replace(diagnosis_if_fail, 'winterization_v1, item 7', 'winterization_v1, item 9')"
            " WHERE sequence_number = 1 AND template_id ="
            " (SELECT id FROM workflow_templates WHERE slug = 'de_winterization_v1')",
        )
        assert ("de_winterization_v1", "winterization_v1 item 9") in broken_links(fresh_db)


# --- Breadth ---


class TestBreadth:
    def test_every_live_template_is_reachable_by_category_and_show(self, gate_db):
        list_cmd = main_cli.commands["workflow"].commands["list"]
        categories = next(p for p in list_cmd.params if p.name == "category").type.choices
        by_category = {}
        for category in categories:
            result = _cli(gate_db, "list", "--category", category)
            if result.exit_code == 1:
                assert "No active workflow templates" in result.output, category
                continue
            assert result.exit_code == 0, result.output
            for slug, row in parse_list(result.output).items():
                assert row["category"] == category, slug
                by_category[slug] = category
        everything = _cli(gate_db, "list")
        live = {t["slug"] for t in list_templates(gate_db, is_active=True)}
        assert set(by_category) == set(parse_list(everything.output)) == live
        for slug in live:
            shown = _cli(gate_db, "show", slug)
            assert shown.exit_code == 0, shown.output
            assert parse_show(shown.output)["items"], slug

    def test_every_template_in_the_row_is_live(self, gate_db):
        live = {t["slug"] for t in list_templates(gate_db, is_active=True)}
        assert {s for _, slugs in ROW for s in slugs} <= live


# --- No build reference in what the walk prints (F158) ---


class TestNoBuildReferences:
    def test_the_walks_print_none(self, walks):
        outputs = [o for record in walks.values() for o in record["outputs"]]
        assert len(outputs) >= 3 * (1 + 2 * sum(len(s) for _, s in ROW))
        assert build_references(outputs) == []

    def test_a_planted_reference_is_caught(self, fresh_db):
        _execute(
            fresh_db,
            "UPDATE workflow_templates SET description = description"
            " || ' Expanded in Phase 999.' WHERE slug = 'tire_service_v1'",
        )
        assert build_references(walk(fresh_db, "electric")["outputs"]) == ["Phase 999"]

    def test_a_motorcycle_model_is_not_a_finding(self):
        assert build_references(["the BMW F800R rider's manual, below 95 °F"]) == []


# --- Migrations from 067 on ---


def _workflow_state(db_path):
    """Schema and rows of the two workflow tables, timestamps aside, and
    the applied versions."""
    conn = sqlite3.connect(db_path)
    state = {
        "schema": sorted(
            (r[0], r[1]) for r in conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE tbl_name IN"
                " ('workflow_templates', 'checklist_items') AND sql IS NOT NULL"
            )
        ),
        "versions": [r[0] for r in conn.execute("SELECT version FROM schema_version ORDER BY version")],
    }
    for table in ("workflow_templates", "checklist_items"):
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        keep = [c for c in cols if c not in ("created_at", "updated_at")]
        state[table] = conn.execute(
            f"SELECT {', '.join(keep)} FROM {table} ORDER BY id"
        ).fetchall()
    conn.close()
    return state


def _build_to(db_path, version):
    """A database built up to `version` only, never a rollback."""
    init_db(db_path, apply_migrations=False)
    for m in sorted(MIGRATIONS, key=lambda m: m.version):
        if get_current_version(db_path) < m.version <= version:
            apply_migration(m, db_path)
    assert get_current_version(db_path) == version


class TestMigrations:
    def test_the_head_is_at_least_track_n(self):
        """F124: a floor, never the head."""
        assert SCHEMA_VERSION >= TRACK_N_FIRST
        track_n = [m for m in MIGRATIONS if m.version >= TRACK_N_FIRST]
        assert track_n and all(m.rollback_sql.strip() for m in track_n)

    def test_two_fresh_databases_are_identical(self, tmp_path):
        a, b = str(tmp_path / "a.db"), str(tmp_path / "b.db")
        init_db(a)
        init_db(b)
        state = _workflow_state(a)
        assert state == _workflow_state(b)
        assert state["workflow_templates"] and state["checklist_items"]

    @pytest.mark.parametrize("version", range(TRACK_N_FIRST - 1, SCHEMA_VERSION))
    def test_rolling_back_peels_every_successor(self, tmp_path, version):
        head = str(tmp_path / "head.db")
        init_db(head)
        assert get_current_version(head) == SCHEMA_VERSION
        rollback_to_version(version, head)
        assert get_current_version(head) == version
        built = str(tmp_path / "built.db")
        _build_to(built, version)
        assert _workflow_state(head) == _workflow_state(built)
