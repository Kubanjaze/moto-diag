"""Phase 379, F140 — no row declares `{manual}`, checked on a built database.

Phase 255's A1 forbids any known-issue row declaring a transmission set that
contains `manual` until manual coverage is sourced: such a row is withheld
from every machine resolving `unknown`. Two tests held it, both over seed
JSON; a migration hook or a direct write could put one in the table with no
test failing. This checks the database the loader and the migrations build.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from motodiag.core.database import init_db
from motodiag.knowledge.loader import load_known_issues_file
from support.phase274 import sql

SEED = Path(__file__).resolve().parent.parent / "src" / "motodiag" / "knowledge" / "seed"


def manual_rows(db_path: str) -> list[int]:
    """Known-issue rows whose declared transmission set contains `manual`."""
    found = []
    for row_id, applicability in sql(db_path, "SELECT id, applicability FROM known_issues "
                                              "WHERE applicability IS NOT NULL"):
        declared = json.loads(applicability)
        if "manual" in (declared.get("transmission") or []):
            found.append(row_id)
    return found


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("f140") / "built.db")
    init_db(path)
    for f in sorted((SEED / "knowledge").glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    return path


def test_the_built_database_holds_no_manual_row(built):
    assert sql(built, "SELECT COUNT(*) FROM known_issues WHERE applicability IS NOT NULL")[0][0] > 0
    assert manual_rows(built) == []


def test_a_planted_manual_row_is_seen(tmp_path):
    path = str(tmp_path / "planted.db")
    init_db(path)
    sql(path, "INSERT INTO known_issues (title, description, make, applicability) VALUES "
              "('planted', 'a direct write, past the loader', 'Honda', ?)",
        (json.dumps({"transmission": ["manual", "cvt"]}),))
    assert manual_rows(path) == [sql(path, "SELECT MAX(id) FROM known_issues")[0][0]]
