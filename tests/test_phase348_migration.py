"""Phase 348, Logic item 2 — migration 088, `audit_events`, on fresh databases.

The table, its index and two triggers and one `schema_version` row; the
triggers refusing UPDATE and DELETE; the rollback; and the deploy scope file
naming exactly what `deploy.schema_diff` reports between a fresh database at
087 and the same at 088. Never the live database.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sqlite3
import sys

import pytest

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
    ("table", "audit_events"),
    ("index", "idx_audit_events_shop"),
    ("trigger", "audit_events_no_update"),
    ("trigger", "audit_events_no_delete"),
}


def _scope_file() -> pathlib.Path:
    for folder in ("in_progress", "completed"):
        p = ROOT / "docs" / "phases" / folder / "348_deploy_scope.json"
        if p.exists():
            return p
    raise AssertionError("348_deploy_scope.json is in neither phase folder")


def _objects(path: str) -> set[tuple[str, str]]:
    c = sqlite3.connect(path)
    rows = c.execute(
        "SELECT type, name FROM sqlite_master WHERE name LIKE '%audit_events%'"
    ).fetchall()
    c.close()
    return {(t, n) for t, n in rows}


def _db_at_087(path: str) -> str:
    init_db(path, apply_migrations=False)
    for m in sorted(MIGRATIONS, key=lambda m: m.version):
        if 2 < m.version <= 87:
            apply_migration(m, path)
    return path


@pytest.fixture(scope="module")
def at_087(tmp_path_factory) -> str:
    return _db_at_087(str(tmp_path_factory.mktemp("m088") / "at087.db"))


@pytest.fixture
def at_088(at_087, tmp_path) -> str:
    path = str(tmp_path / "at088.db")
    shutil.copy(at_087, path)
    apply_migration(get_migration_by_version(88), path)
    return path


def _insert(path: str) -> None:
    c = sqlite3.connect(path)
    c.execute(
        "INSERT INTO audit_events (occurred_at, method, path, status, prev_hash, row_hash) "
        "VALUES ('2026-10-30T00:00:00.000+00:00', 'POST', '/v1/x', 200, 'p', 'h')"
    )
    c.commit()
    c.close()


def test_087_has_none_of_the_objects(at_087):
    assert _objects(at_087) == set()


def test_088_adds_the_four_objects_and_one_version_row(at_087, at_088):
    assert _objects(at_088) == OBJECTS
    c = sqlite3.connect(at_088)
    versions = [r[0] for r in c.execute("SELECT version FROM schema_version")]
    c.close()
    assert versions.count(88) == 1
    c = sqlite3.connect(at_087)
    before = c.execute("SELECT count(*) FROM schema_version").fetchone()[0]
    c.close()
    assert len(versions) == before + 1


def test_the_table_is_empty(at_088):
    c = sqlite3.connect(at_088)
    assert c.execute("SELECT count(*) FROM audit_events").fetchone()[0] == 0
    c.close()


@pytest.mark.parametrize("stmt", [
    "UPDATE audit_events SET status = 999",
    "DELETE FROM audit_events",
])
def test_the_triggers_refuse_a_change_and_a_removal(at_088, stmt):
    _insert(at_088)
    c = sqlite3.connect(at_088)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        c.execute(stmt)
    c.rollback()
    assert c.execute("SELECT status, count(*) FROM audit_events").fetchone() == (200, 1)
    c.close()


def test_with_the_triggers_dropped_the_same_statements_go_through(at_088):
    """The control: the refusal above is the triggers', not something else's."""
    _insert(at_088)
    c = sqlite3.connect(at_088)
    c.execute("DROP TRIGGER audit_events_no_update")
    c.execute("DROP TRIGGER audit_events_no_delete")
    c.execute("UPDATE audit_events SET status = 999")
    c.execute("DELETE FROM audit_events")
    c.commit()
    c.close()


def test_the_rollback_removes_all_four(at_088):
    rollback_migration(get_migration_by_version(88), at_088)
    assert _objects(at_088) == set()
    c = sqlite3.connect(at_088)
    assert c.execute("SELECT count(*) FROM schema_version WHERE version = 88").fetchone()[0] == 0
    c.close()


def test_a_fresh_install_reaches_088(tmp_path):
    path = str(tmp_path / "fresh.db")
    init_db(path)
    assert _objects(path) == OBJECTS


def test_the_scope_file_names_exactly_what_the_schema_diff_reports(at_087, at_088):
    scope = json.loads(_scope_file().read_text())
    sch = D.schema_diff(D.schema(pathlib.Path(at_087)), D.schema(pathlib.Path(at_088)))
    assert sch["removed"] == [] and sch["changed"] == []
    assert sch["added"] == sorted(scope["schema"]["added"])
    assert scope["tables"] == {"schema_version": {"added": 1}}
    rows = D.diff(D.dump(pathlib.Path(at_087)), D.dump(pathlib.Path(at_088)))
    assert {t: len(x["added"]) for t, x in rows.items()} == {"schema_version": 1}
    assert all(not x["removed"] and not x["changed"] for x in rows.values())
