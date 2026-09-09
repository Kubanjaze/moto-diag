"""Phase 235B — a `regulation` provenance value for known_issues.

Migration 052 rebuilds `known_issues` to widen the `source` CHECK.
SQLite cannot alter a CHECK in place, so this is a
CREATE-COPY-DROP-RENAME, and the tests below are mostly about what a
rebuild can silently lose: rows, the autoincrement sequence, the
indexes, the foreign key that points at the table, and the constraint
itself.
"""
import json
import re
import sqlite3
from pathlib import Path
from typing import get_args

import pytest

from motodiag.api.routes.kb import IssueSource
from motodiag.cli.kb import VERIFIED_SOURCES
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.core.migrations import (
    apply_pending_migrations,
    get_current_version,
    get_migration_by_version,
    rollback_to_version,
)
from motodiag.knowledge.issues_repo import add_known_issue, get_known_issue

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
FILE = SEED / "known_issues_aprilia_mv_electrical.json"

SIX = {
    "unverified", "model-generated", "forum",
    "service-manual", "mechanic-verified", "regulation",
}


def _populated_v51(tmp_path, name="t.db"):
    """A v51 database with rows, a regulation-shaped row and — the part
    that matters — a child row whose foreign key points at the table
    about to be dropped."""
    path = str(tmp_path / name)
    init_db(path)
    rollback_to_version(51, db_path=path)
    with get_connection(path) as c:
        c.execute("INSERT INTO known_issues (title,description,source)"
                  " VALUES ('parent','body','service-manual')")
        kid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        for i in range(3):
            c.execute("INSERT INTO known_issues (title,description)"
                      " VALUES (?,?)", (f"filler{i}", "b"))
        c.execute("INSERT INTO repair_plans (title) VALUES ('p')")
        pid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        c.execute(
            "INSERT INTO repair_plan_items"
            " (plan_id,item_type,title,source_issue_id) VALUES (?,?,?,?)",
            (pid, "repair", "child", kid),
        )
    return path, kid


class TestTheMigrationItself:
    def test_schema_version_advanced(self):
        """`>=` rather than `==` so a later migration does not have to
        come back and edit this phase's test — the invariant is that 052
        has been applied, not that it is the newest thing in the tree."""
        assert SCHEMA_VERSION >= 52  # f9-noqa: ssot-pin contract-pin: 52 is this migration's own version, the fact under test; comparing the constant to itself would assert nothing.

    def test_052_exists_and_has_a_rollback(self):
        m = get_migration_by_version(52)  # f9-noqa: ssot-pin contract-pin: addressing migration 052 by its literal version is the lookup under test; any constant would be circular.
        assert m is not None and m.rollback_sql.strip()

    def test_a_fresh_database_accepts_regulation(self, tmp_path):
        path = str(tmp_path / "fresh.db")
        init_db(path)
        iid = add_known_issue("t", "d", db_path=path, source="regulation")
        assert get_known_issue(iid, db_path=path)["source"] == "regulation"

    def test_the_check_still_rejects_a_typo(self, tmp_path):
        """The point of the CHECK is that a misspelling cannot become a
        silent seventh category. Widening it must not weaken it."""
        path = str(tmp_path / "chk.db")
        init_db(path)
        with pytest.raises(sqlite3.IntegrityError):
            add_known_issue("t", "d", db_path=path, source="regulatory")


class TestTheRebuildLosesNothing:
    def test_it_upgrades_with_a_live_foreign_key_child(self, tmp_path):
        """`repair_plan_items.source_issue_id` REFERENCES known_issues(id)
        and `get_connection` sets foreign_keys=ON, so DROP TABLE is
        refused outright while a child row points at it. This test is
        the reason the migration toggles the pragma at all."""
        path, kid = _populated_v51(tmp_path)
        assert get_current_version(path) == 51
        applied = apply_pending_migrations(db_path=path)
        # Phase 240C: was `== [52]`, a constant list that any later migration
        # breaks. What this test is about is that migration 052's table
        # rebuild survives a live foreign-key child -- so assert that 052 ran
        # and that the database lands at the current schema version, not the
        # exact set of migrations that happened to be pending.
        assert 52 in applied, applied
        assert get_current_version(path) == SCHEMA_VERSION
        with get_connection(path) as c:
            assert c.execute(
                "SELECT source_issue_id FROM repair_plan_items"
            ).fetchone()[0] == kid
            assert c.execute("PRAGMA foreign_key_check").fetchall() == []

    def test_rows_survive(self, tmp_path):
        path, _ = _populated_v51(tmp_path)
        with get_connection(path) as c:
            before = c.execute("SELECT count(*) FROM known_issues").fetchone()[0]
        apply_pending_migrations(db_path=path)
        with get_connection(path) as c:
            assert c.execute(
                "SELECT count(*) FROM known_issues").fetchone()[0] == before

    def test_the_autoincrement_sequence_survives(self, tmp_path):
        """`id INTEGER PRIMARY KEY AUTOINCREMENT` means sqlite_sequence
        tracks the high-water mark. A rebuild that loses it would start
        reissuing ids that repair plans already reference."""
        path, _ = _populated_v51(tmp_path)
        with get_connection(path) as c:
            before = c.execute(
                "SELECT seq FROM sqlite_sequence WHERE name='known_issues'"
            ).fetchone()[0]
        apply_pending_migrations(db_path=path)
        with get_connection(path) as c:
            assert c.execute(
                "SELECT seq FROM sqlite_sequence WHERE name='known_issues'"
            ).fetchone()[0] == before

    def test_both_indexes_are_recreated(self, tmp_path):
        path, _ = _populated_v51(tmp_path)
        apply_pending_migrations(db_path=path)
        with get_connection(path) as c:
            names = {r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
                " AND tbl_name='known_issues'")}
        assert {"idx_known_issues_make_model", "idx_known_issues_sort"} <= names

    def test_the_child_foreign_key_repoints_at_the_rebuilt_table(self, tmp_path):
        path, _ = _populated_v51(tmp_path)
        apply_pending_migrations(db_path=path)
        with get_connection(path) as c:
            targets = [fk[2] for fk in
                       c.execute("PRAGMA foreign_key_list(repair_plan_items)")]
        assert "known_issues" in targets

    def test_foreign_keys_is_left_on(self, tmp_path):
        """The migration turns the pragma off to drop the table. Leaving
        it off would silently disable referential integrity for every
        later connection that reused the same handle."""
        path, _ = _populated_v51(tmp_path)
        apply_pending_migrations(db_path=path)
        with get_connection(path) as c:
            assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_no_scratch_table_is_left_behind(self, tmp_path):
        path, _ = _populated_v51(tmp_path)
        apply_pending_migrations(db_path=path)
        with get_connection(path) as c:
            names = {r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        assert not {"known_issues_rebuild", "known_issues_rollback"} & names


class TestRollback:
    def test_regulation_rows_map_to_service_manual(self, tmp_path):
        """Rollback must land on a value the five-value CHECK accepts or
        it fails on real data. `service-manual` is what Phase 235 used
        as the stand-in, so this restores the pre-052 state exactly
        rather than inventing one."""
        path, _ = _populated_v51(tmp_path)
        apply_pending_migrations(db_path=path)
        with get_connection(path) as c:
            c.execute("INSERT INTO known_issues (title,description,source)"
                      " VALUES ('reg','b','regulation')")
        rollback_to_version(51, db_path=path)
        assert get_current_version(path) == 51
        with get_connection(path) as c:
            assert c.execute(
                "SELECT source FROM known_issues WHERE title='reg'"
            ).fetchone()[0] == "service-manual"

    def test_rollback_preserves_rows_and_the_child(self, tmp_path):
        path, kid = _populated_v51(tmp_path)
        apply_pending_migrations(db_path=path)
        with get_connection(path) as c:
            before = c.execute("SELECT count(*) FROM known_issues").fetchone()[0]
        rollback_to_version(51, db_path=path)
        with get_connection(path) as c:
            assert c.execute(
                "SELECT count(*) FROM known_issues").fetchone()[0] == before
            assert c.execute(
                "SELECT source_issue_id FROM repair_plan_items"
            ).fetchone()[0] == kid
            assert c.execute("PRAGMA foreign_key_check").fetchall() == []

    def test_the_five_value_check_is_restored(self, tmp_path):
        path, _ = _populated_v51(tmp_path)
        apply_pending_migrations(db_path=path)
        rollback_to_version(51, db_path=path)
        with get_connection(path) as c:
            with pytest.raises(sqlite3.IntegrityError):
                c.execute("INSERT INTO known_issues (title,description,source)"
                          " VALUES ('x','y','regulation')")


class TestTheVocabularyAgreesAcrossSurfaces:
    """F9 subtype-3: the same vocabulary is written down in the CHECK
    constraint, in a Pydantic Literal and in a CLI trust set. This phase
    is exactly the drift risk that guard covers, so the agreement is
    asserted rather than maintained by hand."""

    def _check_vocabulary(self, path):
        with get_connection(path) as c:
            ddl = c.execute(
                "SELECT sql FROM sqlite_master WHERE name='known_issues'"
            ).fetchone()[0]
        clause = re.search(r"CHECK\s*\(\s*source\s+IN\s*\((.*?)\)\s*\)",
                           ddl, re.S)
        assert clause, ddl
        return set(re.findall(r"'([^']+)'", clause.group(1)))

    def test_check_constraint_matches_the_api_literal(self, tmp_path):
        path = str(tmp_path / "v.db")
        init_db(path)
        assert self._check_vocabulary(path) == set(get_args(IssueSource))

    def test_the_vocabulary_is_the_expected_six(self, tmp_path):
        path = str(tmp_path / "v6.db")
        init_db(path)
        assert self._check_vocabulary(path) == SIX

    def test_verified_sources_is_a_subset_of_the_vocabulary(self, tmp_path):
        path = str(tmp_path / "v7.db")
        init_db(path)
        assert VERIFIED_SOURCES <= self._check_vocabulary(path)


class TestTrustPolicy:
    def test_regulation_is_treated_as_reviewed(self):
        """The stake is concrete: the reclassified entry renders
        warning-free today. Excluding `regulation` here would have made
        a pure relabelling start printing "Origin not recorded" over a
        verbatim regulation — false, and a silent regression."""
        assert "regulation" in VERIFIED_SOURCES

    def test_regulation_is_not_forum_derived(self):
        """Gate 2's FORUM_DERIVED is an allowlist, so `regulation` lands
        in the non-forum bucket automatically. Pinned so a later phase
        cannot quietly add it and hold a legal text to the forum-tip
        rule — which is the mistake Phase 235 avoided by hand."""
        import tests.test_phase78_gate2_integration as gate2  # noqa: F401
        src = Path(gate2.__file__).read_text(encoding="utf-8")
        for match in re.findall(r"FORUM_DERIVED = \{([^}]*)\}", src):
            assert "regulation" not in match

    def test_a_regulation_entry_prints_a_scope_note_not_a_warning(self, capsys):
        """Authoritative, but about a different object than a manual is:
        what is required, not what a given machine does."""
        from rich.console import Console

        from motodiag.cli.kb import _render_provenance
        _render_provenance(Console(width=200), "regulation")
        out = capsys.readouterr().out
        assert "Authoritative on what is required" in out
        assert "Origin not recorded" not in out
        assert "⚠" not in out


class TestTheContentThisWasBuiltFor:
    def test_exactly_one_phase_235_entry_is_regulation_sourced(self):
        raw = json.loads(FILE.read_text(encoding="utf-8"))
        regs = [e for e in raw if e["source"] == "regulation"]
        assert len(regs) == 1, [e["title"] for e in regs]
        assert "locked door" in regs[0]["title"]

    def test_it_cites_the_regulation_it_quotes(self):
        raw = json.loads(FILE.read_text(encoding="utf-8"))
        entry = next(e for e in raw if e["source"] == "regulation")
        assert "44/2014" in entry["description"]
        assert "2018/295" in entry["description"]

    def test_the_manual_sourced_siblings_were_not_swept_along(self):
        """Three sibling entries are also `service-manual` and cite
        Aprilia's manual, not a regulation. A relabelling that caught
        them too would be wrong in the other direction."""
        raw = json.loads(FILE.read_text(encoding="utf-8"))
        manual = [e for e in raw if e["source"] == "service-manual"]
        assert len(manual) == 3
        for e in manual:
            assert "Service Station Manual" in e["description"], e["title"]

    def test_the_seed_loads_the_new_value_end_to_end(self, tmp_path):
        from motodiag.knowledge.loader import load_known_issues_file
        from motodiag.knowledge.issues_repo import search_known_issues
        path = str(tmp_path / "seed.db")
        init_db(path)
        load_known_issues_file(FILE, path)
        rows = search_known_issues(db_path=path)
        assert "regulation" in {r["source"] for r in rows}
