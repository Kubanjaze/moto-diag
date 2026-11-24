"""Phase 293, the database step — migration 092, the shop manual library.

Columns added to ``manual_references``, two indexes on it, the page table
with its unique index, the external-content FTS5 index with its four shadow
tables and three triggers, and the reviewers' table, on fresh databases. The
rows SQLite writes into the shadow tables when the index is made are
measured here, never remembered, and the deploy scope file must name exactly
them. A Phase 117 row keeps its fields; the rollback peels 092 back to 091's
schema; migrating again after it works. Never the live database.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sqlite3
import sys

import pytest

from motodiag.core.database import SCHEMA_VERSION, init_db
from motodiag.core.migrations import (
    MIGRATIONS,
    apply_migration,
    get_migration_by_version,
    rollback_to_version,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "deploy"))

import deploy as D  # noqa: E402

THIS = 92
SHADOWS = ["manual_pages_fts_config", "manual_pages_fts_data",
           "manual_pages_fts_docsize", "manual_pages_fts_idx"]
OBJECTS = {
    ("index", "idx_manuals_shop_status"),
    ("index", "idx_manuals_shop_sha"),
    ("table", "manual_pages"),
    ("index", "idx_manual_pages_manual_page"),
    ("table", "manual_pages_fts"),
    *(("table", t) for t in SHADOWS),
    ("trigger", "manual_pages_ai"),
    ("trigger", "manual_pages_ad"),
    ("trigger", "manual_pages_au"),
    ("table", "manual_reviewers"),
}
NEW_COLUMNS = ["shop_id", "file_path", "file_sha256", "file_size_bytes",
               "uploaded_by_user_id", "kind", "status", "reviewed_by_user_id",
               "reviewed_at", "review_reason", "rendered_pages", "render_error"]
PHASE_117_ROW = ("clymer", "Clymer Honda CBR600 1991-1998", "Clymer", "978-0892876693",
                 "Honda", "CBR600", 1991, 1998, 744, '["Engine"]', None, "a note")
PHASE_117_COLS = ("source, title, publisher, isbn, make, model, year_start, "
                  "year_end, page_count, section_titles, url, notes")


def _scope_file() -> pathlib.Path:
    for folder in ("in_progress", "completed"):
        p = ROOT / "docs" / "phases" / folder / "293_deploy_scope.json"
        if p.exists():
            return p
    raise AssertionError("293_deploy_scope.json is in neither phase folder")


def _objects(path: str) -> set[tuple[str, str]]:
    c = sqlite3.connect(path)
    rows = c.execute(
        "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND ("
        "name LIKE 'manual_pages%' OR name LIKE 'manual_reviewers%' "
        "OR name LIKE 'idx_manual_pages%' OR name LIKE 'idx_manuals_shop%')"
    ).fetchall()
    c.close()
    return {(t, n) for t, n in rows}


def _columns(path: str) -> list[str]:
    c = sqlite3.connect(path)
    cols = [r[1] for r in c.execute("PRAGMA table_info(manual_references)")]
    c.close()
    return cols


def _before(path: str) -> str:
    init_db(path, apply_migrations=False)
    for m in sorted(MIGRATIONS, key=lambda m: m.version):
        if 2 < m.version < THIS:
            apply_migration(m, path)
    return path


@pytest.fixture(scope="module")
def before(tmp_path_factory) -> str:
    return _before(str(tmp_path_factory.mktemp("m092") / "before.db"))


@pytest.fixture
def after(before, tmp_path) -> str:
    path = str(tmp_path / "after.db")
    shutil.copy(before, path)
    apply_migration(get_migration_by_version(THIS), path)
    return path


def _first_rows(path: str) -> dict[str, int]:
    """The shadow tables that hold rows once the index is made, and how many."""
    c = sqlite3.connect(path)
    out = {t: c.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in SHADOWS}
    c.close()
    return {t: n for t, n in out.items() if n}


def test_the_fence_sqlite_has_fts5():
    c = sqlite3.connect(":memory:")
    opts = [r[0] for r in c.execute("PRAGMA compile_options")]
    c.close()
    assert "ENABLE_FTS5" in opts


def test_the_constant_is_at_least_this_migration():
    assert SCHEMA_VERSION >= THIS


def test_before_it_none_of_the_objects(before):
    assert _objects(before) == set()
    assert not set(NEW_COLUMNS) & set(_columns(before))


def test_it_adds_every_object_and_no_content_table(before, after):
    assert _objects(after) == OBJECTS
    names = {n for _, n in _objects(after)}
    assert "manual_pages_fts_content" not in names
    assert _columns(after)[-len(NEW_COLUMNS):] == NEW_COLUMNS
    c = sqlite3.connect(after)
    assert [r[0] for r in c.execute("SELECT version FROM schema_version")].count(THIS) == 1
    without_rowid = sorted(r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%WITHOUT ROWID'"))
    assert without_rowid == ["manual_pages_fts_config", "manual_pages_fts_idx"]
    c.close()


def test_the_first_rows_are_sqlites_own_and_the_scope_names_them(before, after):
    first = _first_rows(after)
    assert set(first) <= set(SHADOWS)
    scope = json.loads(_scope_file().read_text())
    assert scope["tables"] == {"schema_version": {"added": 1},
                               **{t: {"added": n} for t, n in first.items()}}
    rows = D.diff(D.dump(pathlib.Path(before)), D.dump(pathlib.Path(after)))
    assert {t: len(x["added"]) for t, x in rows.items()} == {
        "schema_version": 1, **first}
    assert all(not x["removed"] and not x["changed"] for x in rows.values())


def test_the_scope_file_names_exactly_what_the_migration_adds(before, after):
    scope = json.loads(_scope_file().read_text())
    sch = D.schema_diff(D.schema(pathlib.Path(before)), D.schema(pathlib.Path(after)))
    assert sch["removed"] == []
    assert sch["changed"] == ["table manual_references"] == scope["schema"]["changed"]
    assert sch["added"] == sorted(scope["schema"]["added"])
    assert scope["schema"]["added"] == sorted(f"{t} {n}" for t, n in OBJECTS)
    rows = D.diff(D.dump(pathlib.Path(before)), D.dump(pathlib.Path(after)))
    assert D.check_scope(rows, scope, {}, None, sch) == []


def test_the_deploy_dump_reads_all_four_shadow_tables(after):
    d = D.dump(pathlib.Path(after))
    assert set(SHADOWS) <= set(d)
    assert list(d["manual_pages_fts_config"][1]) == ["version"]


def test_a_phase_117_row_keeps_its_fields_and_gains_the_defaults(before, tmp_path):
    path = str(tmp_path / "with_row.db")
    shutil.copy(before, path)
    c = sqlite3.connect(path)
    c.execute(f"INSERT INTO manual_references ({PHASE_117_COLS}) VALUES "
              f"({', '.join('?' * len(PHASE_117_ROW))})", PHASE_117_ROW)
    c.commit()
    old = c.execute(f"SELECT id, {PHASE_117_COLS}, created_at FROM manual_references").fetchone()
    c.close()
    apply_migration(get_migration_by_version(THIS), path)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    row = c.execute("SELECT * FROM manual_references").fetchone()
    assert tuple(row[k] for k in ["id", *PHASE_117_COLS.split(", "), "created_at"]) == old
    assert row["status"] == "pending_review"
    assert row["rendered_pages"] == 0
    assert all(row[k] is None for k in NEW_COLUMNS if k not in ("status", "rendered_pages"))
    c.close()
    rollback_to_version(THIS - 1, path)
    assert _columns(path) == ["id", *PHASE_117_COLS.split(", "), "created_at"]
    c = sqlite3.connect(path)
    again = c.execute(f"SELECT id, {PHASE_117_COLS}, created_at FROM manual_references").fetchone()
    c.close()
    assert again == old


def test_the_rollback_removes_everything_and_migrating_again_works(before, after):
    rollback_to_version(THIS - 1, after)
    assert _objects(after) == set()
    assert D.schema_diff(D.schema(pathlib.Path(before)), D.schema(pathlib.Path(after))) == {
        "added": [], "removed": [], "changed": []}
    apply_migration(get_migration_by_version(THIS), after)
    assert _objects(after) == OBJECTS


def test_the_triggers_keep_the_index_equal_to_the_pages(after):
    c = sqlite3.connect(after)
    c.execute("INSERT INTO manual_references (source, title) VALUES ('other', 'm')")
    mid = c.execute("SELECT id FROM manual_references").fetchone()[0]
    c.execute("INSERT INTO manual_pages (manual_id, page_number, image_path, thumb_path, text) "
              "VALUES (?, 1, 'a', 'b', 'caliper bolt torque')", (mid,))

    def hits(word: str) -> list:
        return c.execute("SELECT rowid, manual_id, page_number FROM manual_pages_fts "
                         "WHERE manual_pages_fts MATCH ?", (word,)).fetchall()

    pid = c.execute("SELECT id FROM manual_pages").fetchone()[0]
    assert hits("caliper") == [(pid, mid, 1)]
    c.execute("UPDATE manual_pages SET text = 'stator lead resistance' WHERE id = ?", (pid,))
    assert hits("caliper") == []
    assert hits("stator") == [(pid, mid, 1)]
    c.execute("DELETE FROM manual_pages WHERE id = ?", (pid,))
    assert hits("stator") == []
    c.close()


def test_a_fresh_install_has_it(tmp_path):
    path = str(tmp_path / "fresh.db")
    init_db(path)
    assert _objects(path) == OBJECTS
    c = sqlite3.connect(path)
    assert c.execute("SELECT max(version) FROM schema_version").fetchone()[0] >= THIS
    c.close()
