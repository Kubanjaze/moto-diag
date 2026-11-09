"""Phase 371, Logic item 1 — migration 089, the payments feed's tables.

Two tables and one index and one `schema_version` row on fresh databases;
the rollback peels 089 and leaves 088's `audit_events`; every row already
in a seeded database is unchanged; the deploy scope file names exactly what
`deploy.schema_diff` reports between 088 and 089. Never the live database.
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

OBJECTS = {
    ("table", "stripe_event_cursors"),
    ("table", "stripe_feed_notices"),
    ("index", "idx_stripe_feed_notices_line"),
}
CURSOR_COLUMNS = [
    ("account", "TEXT", 0, 1),
    ("last_created", "INTEGER", 1, 0),
    ("last_event_id", "TEXT", 0, 0),
    ("polled_at", "TEXT", 1, 0),
    ("last_error", "TEXT", 0, 0),
    ("livemode", "INTEGER", 1, 0),
]
NOTICE_COLUMNS = [
    ("id", "INTEGER", 0, 1),
    ("line", "TEXT", 1, 0),
    ("sent_at", "TEXT", 1, 0),
    ("detail", "TEXT", 0, 0),
    ("delivered", "INTEGER", 1, 0),
]


def _scope_file() -> pathlib.Path:
    for folder in ("in_progress", "completed"):
        p = ROOT / "docs" / "phases" / folder / "371_deploy_scope.json"
        if p.exists():
            return p
    raise AssertionError("371_deploy_scope.json is in neither phase folder")


def _objects(path: str) -> set[tuple[str, str]]:
    c = sqlite3.connect(path)
    rows = c.execute(
        "SELECT type, name FROM sqlite_master WHERE name LIKE '%stripe_event_cursors%' "
        "OR name LIKE '%stripe_feed_notices%'"
    ).fetchall()
    c.close()
    return {(t, n) for t, n in rows if not n.startswith("sqlite_autoindex")}


def _columns(path: str, table: str) -> list[tuple]:
    c = sqlite3.connect(path)
    rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    c.close()
    return [(r[1], r[2], r[3], r[5]) for r in rows]


def _db_at_088(path: str) -> str:
    init_db(path, apply_migrations=False)
    for m in sorted(MIGRATIONS, key=lambda m: m.version):
        if 2 < m.version <= 88:
            apply_migration(m, path)
    return path


@pytest.fixture(scope="module")
def at_088(tmp_path_factory) -> str:
    return _db_at_088(str(tmp_path_factory.mktemp("m089") / "at088.db"))


@pytest.fixture
def at_089(at_088, tmp_path) -> str:
    path = str(tmp_path / "at089.db")
    shutil.copy(at_088, path)
    apply_migration(get_migration_by_version(89), path)
    return path


def _counts(path: str) -> dict[str, int]:
    c = sqlite3.connect(path)
    tables = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%'")]
    out = {t: c.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables}
    c.close()
    return out


def test_088_has_none_of_the_objects(at_088):
    assert _objects(at_088) == set()


def test_089_adds_the_three_objects_and_one_version_row(at_088, at_089):
    assert _objects(at_089) == OBJECTS
    c = sqlite3.connect(at_089)
    versions = [r[0] for r in c.execute("SELECT version FROM schema_version")]
    c.close()
    assert versions.count(89) == 1
    assert max(versions) >= 89
    c = sqlite3.connect(at_088)
    before = c.execute("SELECT count(*) FROM schema_version").fetchone()[0]
    c.close()
    assert len(versions) == before + 1


def test_the_columns_are_exactly_the_plans(at_089):
    assert _columns(at_089, "stripe_event_cursors") == CURSOR_COLUMNS
    assert _columns(at_089, "stripe_feed_notices") == NOTICE_COLUMNS
    c = sqlite3.connect(at_089)
    cols = [r[2] for r in c.execute("PRAGMA index_info(idx_stripe_feed_notices_line)")]
    c.close()
    assert cols == ["line", "sent_at"]


def test_the_tables_are_empty(at_089):
    c = sqlite3.connect(at_089)
    assert c.execute("SELECT count(*) FROM stripe_event_cursors").fetchone()[0] == 0
    assert c.execute("SELECT count(*) FROM stripe_feed_notices").fetchone()[0] == 0
    c.close()


@pytest.mark.parametrize("stmt", [
    "INSERT INTO stripe_event_cursors (account, last_created, polled_at, livemode) "
    "VALUES ('platform', 1, 'x', 2)",
    "INSERT INTO stripe_feed_notices (line, sent_at, delivered) VALUES ('news_late', 'x', 2)",
])
def test_the_flags_are_zero_or_one(at_089, stmt):
    c = sqlite3.connect(at_089)
    with pytest.raises(sqlite3.IntegrityError):
        c.execute(stmt)
    c.close()


def test_the_rollback_peels_089_and_leaves_088(at_089):
    rollback_migration(get_migration_by_version(89), at_089)
    assert _objects(at_089) == set()
    c = sqlite3.connect(at_089)
    assert c.execute("SELECT count(*) FROM schema_version WHERE version = 89").fetchone()[0] == 0
    assert c.execute(
        "SELECT count(*) FROM sqlite_master WHERE name = 'audit_events'").fetchone()[0] == 1
    c.close()


def test_a_fresh_install_reaches_089(tmp_path):
    path = str(tmp_path / "fresh.db")
    init_db(path)
    assert _objects(path) == OBJECTS
    c = sqlite3.connect(path)
    assert c.execute("SELECT max(version) FROM schema_version").fetchone()[0] >= 89
    c.close()


def test_every_existing_row_is_unchanged_on_a_seeded_copy(at_088, tmp_path):
    path = str(tmp_path / "seeded.db")
    shutil.copy(at_088, path)
    ids = seed_invoice(path)
    seed_account(path, ids["shop_id"])
    before_rows = D.dump(pathlib.Path(path))
    before = _counts(path)
    apply_migration(get_migration_by_version(89), path)
    after = _counts(path)
    assert {t: after[t] for t in before} == {
        **before, "schema_version": before["schema_version"] + 1}
    rows = D.diff(before_rows, D.dump(pathlib.Path(path)))
    assert {t: len(x["added"]) for t, x in rows.items()} == {"schema_version": 1}
    assert all(not x["removed"] and not x["changed"] for x in rows.values())


def test_the_scope_file_names_exactly_what_the_schema_diff_reports(at_088, at_089):
    scope = json.loads(_scope_file().read_text())
    sch = D.schema_diff(D.schema(pathlib.Path(at_088)), D.schema(pathlib.Path(at_089)))
    assert sch["removed"] == [] and sch["changed"] == []
    assert sch["added"] == sorted(scope["schema"]["added"])
    assert scope["schema"]["added"] == sorted(
        f"{t} {n}" for t, n in OBJECTS)
    assert scope["tables"] == {"schema_version": {"added": 1}}
