"""F126 — the work-order scorer's knowledge-base lookup had never returned a row.

`shop/priority_scorer._find_kb_matches_safe` selected a column named `fix`.
The column is `fix_procedure`, and `fix` has never existed in any version of
the schema. Every call raised `sqlite3.OperationalError`, and a bare
`except Exception: return []` turned that into an empty result — so the AI
work-order priority scorer was told the knowledge base had nothing on the
machine, for every work order, always.

Nothing caught it because **nothing called it**. A `grep` for the function
across `tests/` returned nothing before this file.

The tests below are in two halves, and the second is the one that matters:

* the **positive** half — it now returns rows, and the counts are the ones
  measured on the operator's database;
* the **negative** half — a query naming a column that does not exist
  **raises** instead of reading as an empty corpus. That is the defect, not
  the typo. A typo is a five-minute fix; a fallback that makes every failure
  indistinguishable from "no data" is what let it live undetected.
"""

from __future__ import annotations

import sqlite3

import pytest

from motodiag.core.database import init_db
from motodiag.knowledge.marques import rebuild_make_index_at
from motodiag.knowledge.models import rebuild_model_index_at
from motodiag.shop.priority_scorer import _find_kb_matches_safe


@pytest.fixture
def db(tmp_path):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "f126.db")
    init_db(path)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO vehicles (id, make, model, year) VALUES (1, 'Honda', 'CB500', 2020)"
        )
        conn.execute(
            "INSERT INTO known_issues (title, description, make, model, severity, fix_procedure)"
            " VALUES ('CB500 thing', 'd', 'Honda', 'CB500', 'high', 'do the thing')"
        )
        conn.execute(
            "INSERT INTO known_issues (title, description, make, model, severity, fix_procedure)"
            " VALUES ('Honda-wide thing', 'd', 'Honda', NULL, 'medium', 'do the other thing')"
        )
        conn.execute(
            "INSERT INTO known_issues (title, description, make, model, severity, fix_procedure)"
            " VALUES ('Yamaha thing', 'd', 'Yamaha', 'MT07', 'high', 'not this one')"
        )
    # Door 4 retrieves through the resolver since Phase 256, and the
    # resolver reads the make/model junctions. The raw query it replaced
    # did not, which is why this fixture did not build them.
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    reset_settings()
    return path


class TestItReturnsRowsAtAll:
    def test_a_known_vehicle_matches(self, db):
        """The whole bug in one assertion: this used to be zero."""
        rows = _find_kb_matches_safe(1, db)
        assert rows, "the lookup returned nothing — F126 has regressed"
        assert {r["title"] for r in rows} == {"CB500 thing", "Honda-wide thing"}

    def test_it_selects_the_column_that_exists(self, db):
        """`fix_procedure`, not `fix`."""
        rows = _find_kb_matches_safe(1, db)
        assert "fix_procedure" in rows[0]
        assert "fix" not in rows[0]

    def test_another_makes_rows_are_not_returned(self, db):
        assert all(r["title"] != "Yamaha thing" for r in _find_kb_matches_safe(1, db))

    def test_no_vehicle_id_is_empty_not_an_error(self, db):
        assert _find_kb_matches_safe(None, db) == []

    def test_an_unknown_vehicle_is_empty_not_an_error(self, db):
        assert _find_kb_matches_safe(9999, db) == []


def _bare_vehicles_db(tmp_path, *, with_known_issues: bool):
    """A database whose shape predates the schema this door now needs.

    Built by hand rather than mocked: a REAL schema mismatch must reach the
    caller, and a mocked driver would prove only that the mock works.
    """
    path = str(tmp_path / f"shape_{with_known_issues}.db")
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE vehicles (id INTEGER PRIMARY KEY, make TEXT, model TEXT, year INTEGER)"
        )
        conn.execute("INSERT INTO vehicles VALUES (1, 'Honda', 'CB500', 2020)")
        if with_known_issues:
            conn.execute(
                "CREATE TABLE known_issues (id INTEGER PRIMARY KEY, title TEXT, "
                "severity TEXT, make TEXT, model TEXT, fix_procedure TEXT)"
            )
    return path


class TestAFailureNoLongerReadsAsAnEmptyCorpus:
    def test_an_unexpected_database_error_propagates(self, db, monkeypatch):
        """The property F126 was really about, re-aimed after the rewire.

        The original defect -- a query naming a column called `fix` -- is
        structurally gone: Phase 256 deleted the raw SQL and this door now
        retrieves through the resolver, which selects `known_issues.*` and
        degrades gracefully when the junction tables are absent. So there
        is no longer a wrong-column shape to plant.

        What must still hold is the policy that let the defect hide for as
        long as it did: **anything other than a missing table surfaces.** A
        bare `except` that turns every failure into `[]` is how a dead
        query looked exactly like an empty knowledge base.
        """
        import motodiag.shop.priority_scorer as mod

        def boom(*_a, **_kw):
            raise sqlite3.OperationalError("database disk image is malformed")

        monkeypatch.setattr(
            "motodiag.knowledge.vehicle_resolver.known_issues_for_vehicle", boom
        )
        with pytest.raises(sqlite3.OperationalError):
            _find_kb_matches_safe(1, db)

    def test_a_missing_knowledge_table_is_still_an_empty_list(self, db, monkeypatch):
        """The one case the original fallback was written for is preserved."""
        def no_table(*_a, **_kw):
            raise sqlite3.OperationalError("no such table: known_issues")

        monkeypatch.setattr(
            "motodiag.knowledge.vehicle_resolver.known_issues_for_vehicle", no_table
        )
        assert _find_kb_matches_safe(1, db) == []

    def test_a_missing_table_is_still_an_empty_list(self, tmp_path):
        """The one case the original fallback was written for is preserved.

        An older install without the Phase 08 schema gets an empty list,
        not a crash. Neither narrowing the except nor the rewire may
        remove that.
        """
        path = _bare_vehicles_db(tmp_path, with_known_issues=False)
        assert _find_kb_matches_safe(1, path) == []
