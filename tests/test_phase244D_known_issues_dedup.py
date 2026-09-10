"""Phase 244D — known_issues deduplication + idempotent loading.

The defect: 6,600 rows for 660 distinct issues, every entry exactly ten times.
No uniqueness constraint on the table, no idempotency in the loader, so each
run of the seed loop duplicated the whole corpus. It degraded retrieval
silently — a request for 20 corpus rows returned two distinct facts repeated.

The guards here lean on two things a naive implementation gets wrong:
NULL handling in a UNIQUE constraint, and re-declaring an inherited EXPRESSION
index during a table rebuild.
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from motodiag.core import database as db_mod
from motodiag.core.config import SEED_DATA_DIR
from motodiag.core.database import init_db, SCHEMA_VERSION
from motodiag.core.migrations import get_migration_by_version
from motodiag.knowledge.issues_repo import add_known_issue, count_known_issues
from motodiag.knowledge.loader import load_known_issues_file

SEED = SEED_DATA_DIR / "knowledge"
COLS = ("title, description, make, model, year_start, year_end, severity, "
        "symptoms, dtc_codes, causes, fix_procedure, parts_needed, "
        "estimated_hours, created_at, created_by_user_id, source")


def _legacy_table(path):
    """A pre-054 known_issues carrying the duplication the phase exists for."""
    c = sqlite3.connect(path)
    c.execute("""CREATE TABLE known_issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
        description TEXT NOT NULL, make TEXT, model TEXT, year_start INTEGER,
        year_end INTEGER, severity TEXT NOT NULL DEFAULT 'medium',
        symptoms TEXT, dtc_codes TEXT, causes TEXT, fix_procedure TEXT,
        parts_needed TEXT, estimated_hours REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_user_id INTEGER DEFAULT 1,
        source TEXT NOT NULL DEFAULT 'unverified'
            CHECK (source IN ('unverified','model-generated','forum',
                              'service-manual','mechanic-verified','regulation')))""")
    c.execute("CREATE INDEX idx_known_issues_make_model ON known_issues(make, model)")
    c.execute("CREATE INDEX idx_known_issues_sort ON known_issues(severity DESC, title)")
    rows = [
        ("Cam chain tensioner", "d", "Honda", "CBR600F4i", "high"),
        ("Float bowl seep", "d", "Honda", "CBR600F4i", "medium"),
        ("Stator connector", "d", "Harley-Davidson", "Sportster", "critical"),
        ("Cross-make advisory", "d", "Honda", None, "low"),   # NULL model
        ("Second null-model row", "d", "Yamaha", None, "medium"),
    ]
    for _ in range(10):  # ten copies of each, as the live corpus had
        for title, desc, mk, md, sev in rows:
            c.execute(f"INSERT INTO known_issues ({COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (title, desc, mk, md, None, None, sev, "[]", "[]", "[]",
                       None, "[]", None, "2026-01-01", 1, "unverified"))
    c.commit()
    return c


@pytest.fixture
def legacy(tmp_path):
    p = tmp_path / "legacy.db"
    c = _legacy_table(p)
    yield p, c
    c.close()


class TestTheMigrationDeduplicates:
    def test_it_collapses_to_the_distinct_set(self, legacy):
        p, c = legacy
        assert c.execute("select count(*) from known_issues").fetchone()[0] == 50
        c.executescript(get_migration_by_version(54).upgrade_sql)
        assert c.execute("select count(*) from known_issues").fetchone()[0] == 5

    def test_it_keeps_the_lowest_id_per_key(self, legacy):
        p, c = legacy
        want = {r[0] for r in c.execute(
            "select min(id) from known_issues group by COALESCE(make,''),COALESCE(model,''),title")}
        c.executescript(get_migration_by_version(54).upgrade_sql)
        got = {r[0] for r in c.execute("select id from known_issues")}
        assert got == want

    def test_null_model_rows_are_deduplicated(self, legacy):
        """The case a plain UNIQUE(make, model, title) silently misses:
        SQLite treats NULLs as distinct, so those rows would survive in
        tenfold behind a constraint that looked like a fix."""
        p, c = legacy
        assert c.execute("select count(*) from known_issues where model is null").fetchone()[0] == 20
        c.executescript(get_migration_by_version(54).upgrade_sql)
        assert c.execute("select count(*) from known_issues where model is null").fetchone()[0] == 2

    def test_no_distinct_entry_is_lost(self, legacy):
        p, c = legacy
        before = {(r[0], r[1], r[2]) for r in c.execute("select make, model, title from known_issues")}
        c.executescript(get_migration_by_version(54).upgrade_sql)
        after = {(r[0], r[1], r[2]) for r in c.execute("select make, model, title from known_issues")}
        assert after == before


class TestTheRebuildPreservesWhatItInherits:
    def test_the_sort_index_survives_in_its_240C_expression_form(self, legacy):
        """Migration 053 replaced `severity DESC` with an expression index
        because SQLite only uses one when the ORDER BY expression matches.
        Recreating the older form here would undo it with no error."""
        p, c = legacy
        c.executescript(get_migration_by_version(54).upgrade_sql)
        sql = c.execute("select sql from sqlite_master where name='idx_known_issues_sort'").fetchone()[0]
        assert "CASE severity" in sql, "the rebuild recreated the pre-240C index and silently undid migration 053"

    def test_the_severity_listing_still_uses_the_index(self, legacy):
        p, c = legacy
        c.executescript(get_migration_by_version(54).upgrade_sql)
        plan = c.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM known_issues ORDER BY "
            "(CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 "
            "WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END) DESC, title LIMIT 50"
        ).fetchall()
        assert any("idx_known_issues_sort" in str(r[-1]) for r in plan), (
            f"severity listing no longer uses the index: {plan}")

    def test_the_make_model_index_survives(self, legacy):
        p, c = legacy
        c.executescript(get_migration_by_version(54).upgrade_sql)
        names = {r[0] for r in c.execute("select name from sqlite_master where type='index'")}
        assert "idx_known_issues_make_model" in names

    def test_the_identity_index_is_unique_and_null_safe(self, legacy):
        p, c = legacy
        c.executescript(get_migration_by_version(54).upgrade_sql)
        sql = c.execute("select sql from sqlite_master where name='idx_known_issues_identity'").fetchone()[0]
        assert "UNIQUE" in sql.upper()
        assert "COALESCE" in sql.upper(), (
            "a plain column constraint leaves NULL-model rows free to duplicate")


class TestLoadingIsIdempotent:
    def test_loading_one_file_twice_changes_nothing(self, tmp_path):
        db = str(tmp_path / "a.db"); init_db(db)
        f = next(SEED.glob("known_issues_*.json"))
        first = load_known_issues_file(f, db)
        n1 = count_known_issues(db_path=db)
        second = load_known_issues_file(f, db)
        assert count_known_issues(db_path=db) == n1
        assert first > 0 and second == 0, "a repeat load must report zero inserted, not the file's length"

    def test_loading_the_whole_corpus_twice_changes_nothing(self, tmp_path):
        db = str(tmp_path / "b.db"); init_db(db)
        files = sorted(SEED.glob("known_issues_*.json"))
        for f in files:
            load_known_issues_file(f, db)
        n1 = count_known_issues(db_path=db)
        for f in files:
            load_known_issues_file(f, db)
        assert count_known_issues(db_path=db) == n1
        assert n1 == sum(len(json.loads(f.read_text(encoding="utf-8"))) for f in files)

    def test_a_duplicate_identity_returns_the_existing_id(self, tmp_path):
        """`INSERT OR IGNORE` leaves lastrowid stale, so the id must be
        resolved rather than returned blind."""
        db = str(tmp_path / "c.db"); init_db(db)
        a = add_known_issue(title="T", description="d", make="Honda", model="CBR", db_path=db)
        b = add_known_issue(title="T", description="d", make="Honda", model="CBR", db_path=db)
        assert a == b and count_known_issues(db_path=db) == 1

    def test_a_duplicate_identity_with_a_null_model_also_returns_it(self, tmp_path):
        db = str(tmp_path / "d.db"); init_db(db)
        a = add_known_issue(title="T", description="d", make="Honda", model=None, db_path=db)
        b = add_known_issue(title="T", description="d", make="Honda", model=None, db_path=db)
        assert a == b and count_known_issues(db_path=db) == 1

    def test_distinct_issues_still_insert(self, tmp_path):
        """Idempotency must not become 'refuses to add anything'."""
        db = str(tmp_path / "e.db"); init_db(db)
        add_known_issue(title="T", description="d", make="Honda", model="CBR", db_path=db)
        add_known_issue(title="T", description="d", make="Honda", model="CB", db_path=db)
        add_known_issue(title="U", description="d", make="Honda", model="CBR", db_path=db)
        assert count_known_issues(db_path=db) == 3


class TestTheSchemaContract:
    def test_schema_version_is_current(self):
        assert SCHEMA_VERSION == 58  # f9-noqa: ssot-pin contract-pin: Phase 244D schema-bump pin. The literal is the point — importing the constant alone would make this assert x == x and it could never fail. Bumped 53→54 by migration 054 (known_issues dedup + UNIQUE expression index over (COALESCE(make,''), COALESCE(model,''), title)). Bumping requires a corresponding new migration in src/motodiag/core/migrations.py. Bumped 54→55 at Phase 244F (migration 055 adds the known_issue_makes junction: `known_issues.make` is one free-text column holding a marque, a list of marques, a scope phrase and in one row a whole sentence of findings, so LiveWire and Damon were not queryable makes AT ALL — all 24 LiveWire rows sit inside 'Harley-Davidson, LiveWire' and Phase 243's entire output was unreachable. The column is not modified; the junction is derived from it by knowledge/marques.extract_marques). Bumped 55→56 at Phase 244I (migration 056 adds the known_issue_models junction; the model column has the same list-and-prose disease as make, plus entries that name models in order to EXCLUDE them, so extraction is clause-scoped). Bumped 56→57 at Phase 244L (migration 057 widens the cost_events kind CHECK to accept vision_sweep and vision_guidance: vision spent money from Phase 191B but the constraint rejected the rows, so the ledger sat empty). Bumped 57→58 at Phase 244M (migration 058 adds memory_facts, the per-machine compiled memory: keyed on vehicle_id and deliberately NOT on customer_id, because `customers` row 1 is the `Unassigned` sentinel that every vehicle row carries by DEFAULT, so a customer key would compile one memory holding every bike in the shop -- the exact cross-contamination the feature exists to prevent; fact_key is a UNIQUE hash that COALESCEs its nullable origin_id, because SQLite treats NULLs as DISTINCT and the naive form would let every re-compile duplicate).

    def test_a_fresh_database_carries_the_identity_index(self, tmp_path):
        db = str(tmp_path / "f.db"); init_db(db)
        c = sqlite3.connect(db)
        names = {r[0] for r in c.execute("select name from sqlite_master where type='index'")}
        c.close()
        assert "idx_known_issues_identity" in names

    def test_migration_053_still_declares_the_expression_index(self):
        """Phase 240C shipped a bug where an edit to this file rewrote 053's
        own rollback into a no-op. Pinned so it cannot recur silently."""
        m = get_migration_by_version(53)
        assert "CASE severity" in m.upgrade_sql
        assert "severity DESC" in m.rollback_sql

    def test_the_migration_admits_it_is_irreversible(self):
        m = get_migration_by_version(54)
        assert "IRREVERSIBLE" in m.description.upper() or "NOT recoverable" in m.description


class TestIdempotencyDidNotCostConstraintEnforcement:
    """A bug this phase introduced and the regression caught.

    The first implementation used `INSERT OR IGNORE`, which suppresses EVERY
    constraint violation — CHECK included. A typo in `source` would have been
    dropped in silence rather than raising, losing the row and its provenance
    with no signal. Phases 211 and 235B both pin that the CHECK rejects a typo,
    and both went red.

    `ON CONFLICT DO NOTHING` conflicts only on uniqueness. These guards pin the
    distinction so the cheaper spelling cannot come back."""

    def test_a_bad_source_still_raises(self, tmp_path):
        db = str(tmp_path / "g.db"); init_db(db)
        with pytest.raises(sqlite3.IntegrityError):
            add_known_issue(title="T", description="d", make="Honda",
                            model="CBR", source="servicemanual", db_path=db)

    def test_a_bad_source_is_not_silently_dropped(self, tmp_path):
        """The failure mode is a row that vanishes without an error."""
        db = str(tmp_path / "h.db"); init_db(db)
        try:
            add_known_issue(title="T", description="d", make="Honda",
                            model="CBR", source="not-a-vocabulary-value", db_path=db)
        except sqlite3.IntegrityError:
            pass
        assert count_known_issues(db_path=db) == 0

    def test_the_insert_does_not_use_or_ignore(self):
        """Checks the SQL, not the file.

        The first version of this guard matched the raw source text and fired
        on the comment above the statement, which names `INSERT OR IGNORE` in
        order to explain why it is not used — the fourth mention-versus-use
        failure in this line of work. Reading string constants out of the AST
        fixes it structurally: comments are not in the tree, so only the SQL
        that actually runs is examined."""
        import ast, inspect, textwrap
        from motodiag.knowledge import issues_repo

        tree = ast.parse(textwrap.dedent(inspect.getsource(issues_repo.add_known_issue)))
        sql = " ".join(
            n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and "INTO known_issues" in n.value
        )
        assert sql, "could not find the INSERT statement"
        assert "OR IGNORE" not in sql.upper(), (
            "OR IGNORE suppresses CHECK violations too — use ON CONFLICT DO NOTHING")
        assert "ON CONFLICT DO NOTHING" in sql.upper()

    def test_a_valid_source_still_inserts(self):
        """Guarding the rejection must not reject the whole vocabulary."""
        import tempfile, os
        db = os.path.join(tempfile.mkdtemp(), "i.db"); init_db(db)
        for s in ("unverified", "model-generated", "forum",
                  "service-manual", "mechanic-verified", "regulation"):
            add_known_issue(title=f"T-{s}", description="d", make="Honda",
                            model="CBR", source=s, db_path=db)
        assert count_known_issues(db_path=db) == 6
