"""Phase 334, the database step — migration 091, the terms acceptances.

One table, one unique index and one ``schema_version`` row on fresh
databases; the rollback peels 091 and leaves 090's tables; every row already
in a seeded database is unchanged; the deploy scope file names exactly what
``deploy.schema_diff`` reports between 090 and 091. Never the live database.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sqlite3
import sys

import pytest
from support.phase273 import seed_account, seed_invoice

from motodiag.core.database import init_db
from motodiag.core.migrations import (
    MIGRATIONS,
    apply_migration,
    get_migration_by_version,
    rollback_migration,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "deploy"))

import deploy as D  # noqa: E402

THIS = 91
OBJECTS = {
    ("table", "terms_acceptances"),
    ("index", "idx_terms_acceptances_user_version"),
}
COLUMNS = [
    ("id", "INTEGER", 0, 1),
    ("user_id", "INTEGER", 1, 0),
    ("version", "TEXT", 1, 0),
    ("accepted_at", "TEXT", 1, 0),
]


def _scope_file() -> pathlib.Path:
    for folder in ("in_progress", "completed"):
        p = ROOT / "docs" / "phases" / folder / "334_deploy_scope.json"
        if p.exists():
            return p
    raise AssertionError("334_deploy_scope.json is in neither phase folder")


def _objects(path: str) -> set[tuple[str, str]]:
    c = sqlite3.connect(path)
    rows = c.execute(
        "SELECT type, name FROM sqlite_master WHERE name LIKE '%terms_acceptances%'"
    ).fetchall()
    c.close()
    return {(t, n) for t, n in rows if not n.startswith("sqlite_autoindex")}


def _before(path: str) -> str:
    init_db(path, apply_migrations=False)
    for m in sorted(MIGRATIONS, key=lambda m: m.version):
        if 2 < m.version < THIS:
            apply_migration(m, path)
    return path


@pytest.fixture(scope="module")
def before(tmp_path_factory) -> str:
    return _before(str(tmp_path_factory.mktemp("m091") / "before.db"))


@pytest.fixture
def after(before, tmp_path) -> str:
    path = str(tmp_path / "after.db")
    shutil.copy(before, path)
    apply_migration(get_migration_by_version(THIS), path)
    return path


def _counts(path: str) -> dict[str, int]:
    c = sqlite3.connect(path)
    tables = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
    out = {t: c.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables}
    c.close()
    return out


def test_before_it_none_of_the_objects(before):
    assert _objects(before) == set()


def test_it_adds_the_two_objects_and_one_version_row(before, after):
    assert _objects(after) == OBJECTS
    c = sqlite3.connect(after)
    versions = [r[0] for r in c.execute("SELECT version FROM schema_version")]
    cols = [(r[1], r[2], r[3], r[5]) for r in c.execute("PRAGMA table_info(terms_acceptances)")]
    idx = [r[2] for r in c.execute("PRAGMA index_info(idx_terms_acceptances_user_version)")]
    unique = [r[2] for r in c.execute("PRAGMA index_list(terms_acceptances)")
              if r[1] == "idx_terms_acceptances_user_version"]
    fks = [(r[2], r[3], r[4]) for r in c.execute("PRAGMA foreign_key_list(terms_acceptances)")]
    empty = c.execute("SELECT count(*) FROM terms_acceptances").fetchone()[0]
    c.close()
    assert versions.count(THIS) == 1
    assert cols == COLUMNS
    assert idx == ["user_id", "version"]
    assert unique == [1]
    assert fks == [("users", "user_id", "id")]
    assert empty == 0


def test_one_row_per_user_per_version(after):
    c = sqlite3.connect(after)
    c.execute("INSERT INTO users (username, email) VALUES ('u', 'u@ex.com')")
    uid = c.execute("SELECT id FROM users WHERE username = 'u'").fetchone()[0]
    c.execute("INSERT INTO terms_acceptances (user_id, version, accepted_at) "
              "VALUES (?, '1.0', 't')", (uid,))
    c.execute("INSERT INTO terms_acceptances (user_id, version, accepted_at) "
              "VALUES (?, '1.1', 't')", (uid,))
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO terms_acceptances (user_id, version, accepted_at) "
                  "VALUES (?, '1.0', 't2')", (uid,))
    c.close()


def test_the_rollback_removes_both_and_nothing_else(before, after):
    rollback_migration(get_migration_by_version(THIS), after)
    assert _objects(after) == set()
    assert D.schema_diff(D.schema(pathlib.Path(before)), D.schema(pathlib.Path(after))) == {
        "added": [], "removed": [], "changed": []}
    c = sqlite3.connect(after)
    assert c.execute("SELECT count(*) FROM schema_version WHERE version = ?",
                     (THIS,)).fetchone()[0] == 0
    c.close()


def test_a_fresh_install_has_it(tmp_path):
    path = str(tmp_path / "fresh.db")
    init_db(path)
    assert _objects(path) == OBJECTS
    c = sqlite3.connect(path)
    assert c.execute("SELECT max(version) FROM schema_version").fetchone()[0] >= THIS
    c.close()


def test_every_existing_row_is_unchanged_on_a_seeded_copy(before, tmp_path):
    path = str(tmp_path / "seeded.db")
    shutil.copy(before, path)
    ids = seed_invoice(path)
    seed_account(path, ids["shop_id"])
    before_rows = D.dump(pathlib.Path(path))
    counts = _counts(path)
    apply_migration(get_migration_by_version(THIS), path)
    after_counts = _counts(path)
    assert {t: after_counts[t] for t in counts} == {
        **counts, "schema_version": counts["schema_version"] + 1}
    rows = D.diff(before_rows, D.dump(pathlib.Path(path)))
    assert {t: len(x["added"]) for t, x in rows.items()} == {"schema_version": 1}
    assert all(not x["removed"] and not x["changed"] for x in rows.values())


def test_the_scope_file_names_exactly_what_the_migration_adds(before, after):
    scope = json.loads(_scope_file().read_text())
    sch = D.schema_diff(D.schema(pathlib.Path(before)), D.schema(pathlib.Path(after)))
    assert sch["removed"] == [] and sch["changed"] == []
    assert sch["added"] == sorted(scope["schema"]["added"])
    assert scope["schema"]["added"] == sorted(f"{t} {n}" for t, n in OBJECTS)
    assert scope["tables"] == {"schema_version": {"added": 1}}
