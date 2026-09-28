"""Phase 359 — content clean-up: migration 072 and the seed edits with it.

The operator's pick at Step 0 (B, 2026-09-27), and what this file holds it to:
- the two starters migration 007 seeded are retired: inactive, listed
  nowhere, refused by `workflow show` with a line naming what replaces
  them, and named by no active template;
- `ppi_chassis_v1` loses F163's three unsupported steering sentences and
  gains a VIN step cited to two makers' documents;
- 26 live known-issue rows become their seed text, field by field: 24 lose
  F158's build references, and rows 31 and 4615 catch up with seed edits
  that never reached a database already holding them (F129). The
  operator's condition on 4615, shown here on a built database: after 072
  it equals its seed row, field for field, and nothing else changes.

Migration 072 is found by name, never by a literal head (F124), so the next
migration (357) joins these checks without an edit. No test reads
data/motodiag.db.
"""

from __future__ import annotations

import json
import pathlib
import re
import sqlite3

import pytest
from click.testing import CliRunner

from motodiag.cli.main import cli as main_cli
from motodiag.core.config import SEED_DATA_DIR
from motodiag.core.database import SCHEMA_VERSION, init_db
from motodiag.core.migration_072_live_rows import LIVE_ROWS_072
from motodiag.core.migrations import (
    MIGRATIONS,
    apply_migration,
    get_current_version,
    rollback_to_version,
)
from motodiag.knowledge.loader import load_dtc_directory, load_known_issues_file, load_symptom_file
from motodiag.knowledge.marques import rebuild_make_index_at
from motodiag.knowledge.models import rebuild_model_index_at
from motodiag.workflows import get_checklist_items, get_template_by_slug, list_templates

M072 = next(m for m in MIGRATIONS if m.name == "content_cleanup_starters_f158")
RETIRED = {"generic_ppi_v1": ("ppi_engine_v1", "ppi_chassis_v1"),
           "generic_winterization_v1": ("winterization_v1",)}
BUILD_REFERENCE = re.compile(r"\bPhase \d+|\bTrack [A-Z]\b|this phase", re.IGNORECASE)
#: The two rows that lag their seed (359 Step 0, S0-6), by title.
LAGGING = {
    "Thermostat failure — stuck closed causing overheating vs stuck open causing slow warmup",
    "What the regulator record shows for scooter CVTs — one campaign, and two indexes that "
    "disagree with each other and with the data",
}


def _seeded(path: pathlib.Path) -> str:
    """A database built as `motodiag db init` builds one."""
    init_db(str(path))
    load_dtc_directory(SEED_DATA_DIR / "dtc_codes", str(path))
    load_symptom_file(SEED_DATA_DIR / "knowledge" / "symptoms.json", str(path))
    for f in sorted((SEED_DATA_DIR / "knowledge").glob("known_issues_*.json")):
        load_known_issues_file(f, str(path))
    rebuild_make_index_at(str(path))
    rebuild_model_index_at(str(path))
    return str(path)


@pytest.fixture(scope="module")
def seeded(tmp_path_factory) -> str:
    return _seeded(tmp_path_factory.mktemp("s359") / "seeded.db")


@pytest.fixture
def db(tmp_path, monkeypatch) -> str:
    """A fresh database the CLI reads."""
    from motodiag.cli.theme import reset_console
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "10000")
    reset_settings()
    reset_console()
    yield path
    reset_settings()
    reset_console()


def _rows(path: str, table: str, order: str = "id") -> list[tuple]:
    c = sqlite3.connect(path)
    # Timestamps are when a row was written, which two builds never share.
    cols = [r[1] for r in c.execute(f"pragma table_info({table})")
            if r[1] not in ("created_at", "updated_at")]
    rows = c.execute(f"select {', '.join(cols)} from {table} order by {order}").fetchall()
    c.close()
    return rows


# --- The starters retire ---


class TestRetirement:
    def test_the_head_holds_072(self):
        assert SCHEMA_VERSION >= M072.version

    def test_both_starters_are_inactive_with_their_items_kept(self, db):
        for slug, items in (("generic_ppi_v1", 5), ("generic_winterization_v1", 4)):
            t = get_template_by_slug(slug, db)
            assert t["is_active"] == 0
            assert t["description"].startswith("Retired.")
            for successor in RETIRED[slug]:
                assert successor in t["description"]
            assert len(get_checklist_items(t["id"], db)) == items

    def test_list_prints_neither(self, db):
        result = CliRunner().invoke(main_cli, ["workflow", "list"])
        assert result.exit_code == 0, result.output
        assert not set(RETIRED) & {t["slug"] for t in list_templates(db, is_active=True)}
        for slug in RETIRED:
            assert slug not in result.output

    @pytest.mark.parametrize("slug", sorted(RETIRED))
    def test_show_refuses_a_retired_slug_and_names_its_replacements(self, db, slug):
        result = CliRunner().invoke(main_cli, ["workflow", "show", slug])
        assert result.exit_code == 1
        assert "Retired." in result.output
        for successor in RETIRED[slug]:
            assert successor in result.output
        # No checklist: F159's and F166's text stays unprinted.
        assert "Pass:" not in result.output
        assert "Pads >3mm" not in result.output

    def test_show_still_prints_an_active_template(self, db):
        """The control: the retired branch does not swallow active ones."""
        result = CliRunner().invoke(main_cli, ["workflow", "show", "ppi_chassis_v1"])
        assert result.exit_code == 0, result.output
        assert "Pass:" in result.output

    def test_no_active_template_names_a_starter(self, db):
        c = sqlite3.connect(db)
        texts = [" ".join(str(v) for v in r) for r in c.execute(
            "select t.name, t.description, i.title, i.description, i.instruction_text,"
            " i.expected_pass, i.expected_fail, i.diagnosis_if_fail"
            " from workflow_templates t left join checklist_items i on i.template_id = t.id"
            " where t.is_active = 1")]
        c.close()
        assert texts
        for slug in RETIRED:
            assert not [t for t in texts if slug in t]
        assert not [t for t in texts if "the quick check" in t]


# --- ppi_chassis_v1 ---


def _chassis(db: str, title: str) -> dict:
    t = get_template_by_slug("ppi_chassis_v1", db)
    return next(i for i in get_checklist_items(t["id"], db) if i["title"] == title)


class TestChassis:
    def test_f163_the_three_sentences_are_gone(self, db):
        item = _chassis(db, "Steering head bearings")
        text = " ".join(item[f] or "" for f in ("instruction_text", "diagnosis_if_fail"))
        for gone in ("dented bearing races", "hide the notch until the grease settles",
                     "brinelled", "dented races"):
            assert gone not in text, gone
        # What stays: the adjustment and its cited torques. What replaces the
        # notch sentences (refute round 1): KTM p. 76's own step for a detent,
        # and its warning as worded on the page.
        assert "38 N·m initial tightening torque and 14 N·m final (PDF p. 94)." in item["instruction_text"]
        diagnosis = item["diagnosis_if_fail"]
        assert ("Rocking play is loose adjustment; the KTM manual notes that running with play can"
                " damage the bearings and the bearing seats in the frame over time (PDF p. 76)") in diagnosis
        assert ("For a detent position the same manual says to adjust the steering head bearing play,"
                " then check the bearing and change it if necessary (PDF p. 76).") in diagnosis

    def test_the_vin_step_is_cited(self, db):
        item = _chassis(db, "Frame, straightness and crash evidence")
        text = item["instruction_text"]
        assert ('the Vespa GTS 300 i.e. ABS manual recommends "checking that the chassis registration'
                ' number stamped on the vehicle corresponds with that on the vehicle documentation"'
                ' (PDF p. 34)') in text
        assert ('the Honda 2018 CB500F/FA owner\'s manual says the VIN is "required in order to'
                ' register your motorcycle" (PDF p. 119)') in text
        assert "stamped frame number matching the title or registration" in item["expected_pass"]
        assert ("stamped frame number that does not match the title or registration, or that has"
                " been altered") in item["expected_fail"]


# --- The seed ---


class TestSeed:
    def test_no_seed_known_issue_carries_a_build_reference(self):
        """The rule the phase fixed by, over the seed files themselves."""
        found = []
        for f in sorted((SEED_DATA_DIR / "knowledge").glob("known_issues_*.json")):
            for entry in json.loads(f.read_text(encoding="utf-8")):
                for field, value in entry.items():
                    text = json.dumps(value, ensure_ascii=False) if isinstance(value, list) else str(value)
                    found += [(f.name, entry["title"][:40], field, m.group())
                              for m in BUILD_REFERENCE.finditer(text)]
        assert found == []

    def test_the_rule_catches_a_planted_reference(self):
        assert [m.group() for m in BUILD_REFERENCE.finditer("read this phase; see Phase 999")] == [
            "this phase", "Phase 999"]
        assert not BUILD_REFERENCE.search("a three-phase stator, BMW F800")


# --- The live rows, as data ---


class TestLiveRowsData:
    def test_the_shape_step_0_measured(self):
        assert len({e[0] for e in LIVE_ROWS_072}) == 26
        assert len(LIVE_ROWS_072) == 35
        assert {e[4] for e in LIVE_ROWS_072} <= {"description", "fix_procedure", "causes", "symptoms"}
        assert {e[3] for e in LIVE_ROWS_072} >= LAGGING

    def test_each_f158_row_loses_a_reference_and_gains_none(self):
        by_row: dict = {}
        for _id, _make, _model, title, _field, old, new in LIVE_ROWS_072:
            assert old != new
            assert not BUILD_REFERENCE.search(new)
            by_row.setdefault(title, []).append(bool(BUILD_REFERENCE.search(old)))
        f158 = {t for t, flags in by_row.items() if any(flags)}
        assert len(f158) == 24
        assert set(by_row) - f158 == LAGGING

    def test_each_new_value_is_the_seed_builds(self, seeded):
        c = sqlite3.connect(seeded)
        for _id, make, model, title, field, _old, new in LIVE_ROWS_072:
            rows = c.execute(f"select {field} from known_issues where make = ? and model is ?"
                             " and title = ?", (make, model, title)).fetchall()
            assert rows == [(new,)], (title[:50], field)
        c.close()


# --- The migration on known-issue rows: live's shape, rebuilt from the seed ---


def _at_previous_with_live_text(tmp_path: pathlib.Path) -> str:
    """A seeded database rolled back to 071. The rollback writes the old
    (live) text into the 26 rows, so this is live's state for them."""
    path = _seeded(tmp_path / "at071.db")
    rollback_to_version(M072.version - 1, path)
    assert get_current_version(path) == M072.version - 1
    return path


class TestTheMigration:
    def test_072_brings_every_row_to_its_seed_and_changes_nothing_else(self, tmp_path, seeded):
        path = _at_previous_with_live_text(tmp_path)
        before = {r[0]: r for r in _rows(path, "known_issues")}
        changed_back = {i for i in before if before[i] != {r[0]: r for r in _rows(seeded, "known_issues")}[i]}
        assert len(changed_back) == 26
        apply_migration(M072, path)
        after = {r[0]: r for r in _rows(path, "known_issues")}
        assert after == {r[0]: r for r in _rows(seeded, "known_issues")}
        assert {i for i in before if before[i] != after[i]} == changed_back

    def test_the_operators_4615_condition_field_for_field(self, tmp_path, seeded):
        """4615 changes only to its seed text, field for field."""
        title = next(t for t in LAGGING if t.startswith("What the regulator record"))
        path = _at_previous_with_live_text(tmp_path)
        c = sqlite3.connect(path)
        cols = [r[1] for r in c.execute("pragma table_info(known_issues)") if r[1] != "created_at"]
        q = f"select {', '.join(cols)} from known_issues where title = ?"
        old = c.execute(q, (title,)).fetchone()
        c.close()
        apply_migration(M072, path)
        c, s = sqlite3.connect(path), sqlite3.connect(seeded)
        new, seed = c.execute(q, (title,)).fetchone(), s.execute(q, (title,)).fetchone()
        c.close()
        s.close()
        assert new == seed
        assert {cols[i] for i in range(len(cols)) if old[i] != new[i]} == {
            "description", "symptoms", "causes", "fix_procedure"}

    def test_a_drifted_row_is_left_alone(self, tmp_path, seeded):
        """Keyed on the exact old text: a row that differs from it is not
        touched, so the dry run's diff shows it instead."""
        path = _at_previous_with_live_text(tmp_path)
        _id, make, model, title, field, old, _new = LIVE_ROWS_072[0]
        c = sqlite3.connect(path)
        c.execute(f"update known_issues set {field} = ? where make = ? and model is ? and title = ?",
                  (old + " (edited)", make, model, title))
        c.commit()
        c.close()
        apply_migration(M072, path)
        c = sqlite3.connect(path)
        got = c.execute(f"select {field} from known_issues where make = ? and model is ? and title = ?",
                        (make, model, title)).fetchone()[0]
        c.close()
        assert got == old + " (edited)"

    def test_the_round_trip_restores_the_workflow_tables(self, tmp_path):
        head = _seeded(tmp_path / "head.db")
        tables = ("workflow_templates", "checklist_items")
        at_head = {t: _rows(head, t) for t in tables}
        rollback_to_version(M072.version - 1, head)
        assert get_template_by_slug("generic_ppi_v1", head)["is_active"] == 1
        assert "Companion to generic_ppi_v1" in get_template_by_slug("ppi_chassis_v1", head)["description"]
        apply_migration(M072, head)
        assert {t: _rows(head, t) for t in tables} == at_head
