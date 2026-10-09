"""Phase 380, F129 — a known-issue row's identity is a frozen key, not its prose.

The identity was `(make, model, title)`, so correcting any of the three added
a second row on the next seed load (measured in 255B: 12 rows became 13,
the over-claiming row still there). The operator's 1A: every seed entry
carries a key, generated once and frozen; "a test fails on any seed entry
with no key or a duplicate key". 2A: a load is insert-only, by key.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from motodiag.core.database import get_connection, init_db
from motodiag.knowledge.issues_repo import (
    add_known_issue, derived_row_key, update_known_issue_by_key,
)
from motodiag.knowledge.loader import load_known_issues_file
from support.phase274 import sql

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEED = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
FIXTURES = ROOT / "tests" / "fixtures" / "phase380"
KEY_SHAPE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def seed_key_problems(seed_dir: pathlib.Path) -> list[str]:
    """Every seed entry has a well-formed key, and no key repeats across files."""
    problems, seen = [], {}
    for path in sorted(seed_dir.glob("known_issues_*.json")):
        for i, entry in enumerate(json.loads(path.read_text(encoding="utf-8"))):
            key = entry.get("key")
            where = f"{path.name}[{i}] {entry.get('title', '')[:40]!r}"
            if not key:
                problems.append(f"no key: {where}")
            elif not KEY_SHAPE.match(key):
                problems.append(f"malformed key {key!r}: {where}")
            elif key in seen:
                problems.append(f"duplicate key {key!r}: {where} and {seen[key]}")
            else:
                seen[key] = where
    return problems


class TestTheSeedKeys:
    def test_every_entry_has_a_unique_well_formed_key(self):
        assert seed_key_problems(SEED) == []
        # 1057 since Phase 381 retired F149's three rows.
        assert sum(len(json.loads(p.read_text())) for p in SEED.glob("known_issues_*.json")) \
            >= 1057

    def test_a_missing_key_fails(self):
        assert seed_key_problems(FIXTURES / "missing_key") == [
            "no key: known_issues_planted.json[1] "
            "'A planted row whose key was never writte'"]

    def test_a_duplicate_key_fails(self):
        problems = seed_key_problems(FIXTURES / "duplicate_key")
        assert len(problems) == 1 and problems[0].startswith(
            "duplicate key 'honda-the-same-key-twice'")

    def test_the_good_fixture_passes(self):
        assert seed_key_problems(FIXTURES / "good") == []


class TestACorrectionNoLongerDuplicates:
    """F129's measured case, with keys: the CVT file seeded, a row's model,
    make and title edited in a copy of the file, and the copy seeded again."""

    @pytest.mark.parametrize("field, value", [
        ("model", "Agility 50, Agility 125"), ("title", "A corrected title"),
        ("make", "Kymco, SYM")])
    def test_an_edited_seed_entry_reloads_without_a_second_row(self, tmp_path, field, value):
        db = str(tmp_path / "f129.db")
        init_db(db)
        load_known_issues_file(SEED / "known_issues_cvt.json", db)
        before = sql(db, "SELECT COUNT(*) FROM known_issues")[0][0]
        entries = json.loads((SEED / "known_issues_cvt.json").read_text())
        entries[0][field] = value
        edited = tmp_path / "known_issues_cvt.json"
        edited.write_text(json.dumps(entries))
        load_known_issues_file(edited, db)
        assert sql(db, "SELECT COUNT(*) FROM known_issues")[0][0] == before
        assert sql(db, "SELECT COUNT(*) FROM known_issues WHERE row_key = ?",
                   (entries[0]["key"],)) == [(1,)]

    def test_insert_only_the_row_keeps_what_live_holds(self, tmp_path):
        """2A: a reload never rewrites a live row; a content change is a
        migration on the key."""
        db = str(tmp_path / "f129.db")
        init_db(db)
        load_known_issues_file(SEED / "known_issues_cvt.json", db)
        entries = json.loads((SEED / "known_issues_cvt.json").read_text())
        original = entries[0]["title"]
        entries[0]["title"] = "A corrected title"
        edited = tmp_path / "known_issues_cvt.json"
        edited.write_text(json.dumps(entries))
        load_known_issues_file(edited, db)
        assert sql(db, "SELECT title FROM known_issues WHERE row_key = ?",
                   (entries[0]["key"],)) == [(original,)]


class TestKeylessCallers:
    def test_the_same_prose_twice_is_one_row(self, tmp_path):
        db = str(tmp_path / "k.db")
        init_db(db)
        first = add_known_issue("Stator", "d", make="Honda", model="CB500", db_path=db)
        again = add_known_issue("Stator", "d", make="Honda", model="CB500", db_path=db)
        other = add_known_issue("Stator", "d", make="Honda", model="CB650", db_path=db)
        assert first == again != other
        assert sql(db, "SELECT row_key FROM known_issues WHERE id = ?", (first,)) == [
            (derived_row_key("Honda", "CB500", "Stator"),)]

    def test_update_by_key(self, tmp_path):
        db = str(tmp_path / "k.db")
        init_db(db)
        add_known_issue("Stator", "d", make="Honda", symptoms=["a"], key="honda-stator",
                        db_path=db)
        with get_connection(db) as conn:
            assert update_known_issue_by_key(conn, "honda-stator",
                                             {"title": "Stator, corrected", "symptoms": ["b"]}) == 1
            with pytest.raises(ValueError, match="not a known_issues content field"):
                update_known_issue_by_key(conn, "honda-stator", {"id": 9})
        assert sql(db, "SELECT title, symptoms FROM known_issues") == [
            ("Stator, corrected", '["b"]')]


class TestMigration085:
    def test_keys_from_the_seed_auto_for_the_rest_and_the_rollback(self, tmp_path):
        from motodiag.core.migrations import (
            apply_migration, get_migration_by_version, rollback_to_version,
        )

        db = str(tmp_path / "m085.db")
        init_db(db)
        rollback_to_version(84, db)
        entry = json.loads((SEED / "known_issues_cvt.json").read_text())[0]
        add_known_issue(entry["title"], entry["description"], make=entry["make"],
                        model=entry["model"], db_path=db)
        add_known_issue("An operator's own row", "d", make="Honda", db_path=db)
        assert "row_key" not in [r[1] for r in sql(db, "PRAGMA table_info(known_issues)")]

        apply_migration(get_migration_by_version(85), db)
        assert sql(db, "SELECT title, row_key FROM known_issues ORDER BY id") == [
            (entry["title"], entry["key"]),
            ("An operator's own row", derived_row_key("Honda", None, "An operator's own row"))]
        indexes = {r[0] for r in sql(db, "SELECT name FROM sqlite_master WHERE type='index'")}
        assert "idx_known_issues_row_key" in indexes
        assert "idx_known_issues_identity" not in indexes

        rollback_to_version(84, db)
        assert "row_key" not in [r[1] for r in sql(db, "PRAGMA table_info(known_issues)")]
        indexes = {r[0] for r in sql(db, "SELECT name FROM sqlite_master WHERE type='index'")}
        assert "idx_known_issues_identity" in indexes
        assert sql(db, "SELECT COUNT(*) FROM known_issues") == [(2,)]

    def test_it_removes_a_wrong_junction_pair_and_keeps_the_rest_in_place(self, tmp_path):
        """F142 on an existing database: a pair putting Energica's Ego under
        Harley-Davidson leaves, and every pair that stays keeps its rowid, so
        the dry run shows only the rows that move."""
        from motodiag.core.migrations import (
            apply_migration, get_migration_by_version, rollback_to_version,
        )

        db = str(tmp_path / "j085.db")
        init_db(db)
        rollback_to_version(84, db)
        add_known_issue("Energica's own row", "d", make="Energica",
                        model="Energica Ego, Eva", db_path=db)
        shared = add_known_issue("A row on four electric makes", "d",
                                 make="Energica, Harley-Davidson", model="Ego", db_path=db)
        # The wrong pair goes in first, so the pairs that stay sit at rowids a
        # rewrite of the whole table would not give them back.
        right = sql(db, "SELECT issue_id, make, model FROM known_issue_models ORDER BY rowid")
        sql(db, "DELETE FROM known_issue_models")
        sql(db, "INSERT INTO known_issue_models (issue_id, make, model) "
                "VALUES (?, 'Harley-Davidson', 'Ego')", (shared,))
        for pair in right:
            if pair != (shared, "Harley-Davidson", "Ego"):
                sql(db, "INSERT INTO known_issue_models (issue_id, make, model) VALUES (?, ?, ?)",
                    pair)
        kept_before = sql(db, "SELECT rowid, issue_id, make, model FROM known_issue_models "
                              "WHERE NOT (make = 'Harley-Davidson' AND model = 'Ego')")
        apply_migration(get_migration_by_version(85), db)
        assert sql(db, "SELECT COUNT(*) FROM known_issue_models WHERE make = 'Harley-Davidson' "
                       "AND model = 'Ego'") == [(0,)]
        assert sql(db, "SELECT rowid, issue_id, make, model FROM known_issue_models "
                       "ORDER BY rowid") == sorted(kept_before)

    def test_a_built_database_keys_every_row_uniquely(self, tmp_path):
        db = str(tmp_path / "built.db")
        init_db(db)
        for f in sorted(SEED.glob("known_issues_*.json"))[:5]:
            load_known_issues_file(f, db)
        assert sql(db, "SELECT COUNT(*) FROM known_issues WHERE row_key IS NULL") == [(0,)]
        assert sql(db, "SELECT COUNT(*) = COUNT(DISTINCT row_key) FROM known_issues") == [(1,)]
        assert sql(db, "SELECT COUNT(*) FROM known_issues WHERE row_key LIKE 'auto-%'") == [(0,)]


def test_the_generator_is_committed_with_its_output():
    """K24: the script whose output ships is in the phase folder."""
    found = list((ROOT / "docs" / "phases").glob("*/380_add_keys.py"))
    assert len(found) == 1
    assert "frozen" in found[0].read_text()
