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


def _stripped_db(tmp_path, *, with_known_issues: bool, column: str | None):
    """A database whose `known_issues` is genuinely the wrong shape.

    Built by hand rather than mocked: the point is that a REAL schema
    mismatch reaches the caller, and a mock of the driver would prove only
    that the mock works.
    """
    path = str(tmp_path / f"shape_{with_known_issues}_{column}.db")
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE vehicles (id INTEGER PRIMARY KEY, make TEXT, model TEXT, year INTEGER)"
        )
        conn.execute("INSERT INTO vehicles VALUES (1, 'Honda', 'CB500', 2020)")
        if with_known_issues:
            conn.execute(
                f"CREATE TABLE known_issues (id INTEGER PRIMARY KEY, title TEXT, "
                f"severity TEXT, make TEXT, model TEXT{', ' + column + ' TEXT' if column else ''})"
            )
            conn.execute(
                "INSERT INTO known_issues (title, severity, make, model) "
                "VALUES ('t', 'high', 'Honda', 'CB500')"
            )
    return path


class TestAFailureNoLongerReadsAsAnEmptyCorpus:
    def test_a_missing_column_raises(self, tmp_path):
        """The negative control, and the actual subject of F126.

        A schema error must not be reportable as "this machine has no known
        issues". Here `known_issues` exists but has no `fix_procedure`
        column -- exactly the shape the original code hit on every call,
        against a real database rather than a mock.
        """
        path = _stripped_db(tmp_path, with_known_issues=True, column=None)
        with pytest.raises(sqlite3.OperationalError) as caught:
            _find_kb_matches_safe(1, path)
        assert "no such column" in str(caught.value)

    def test_the_same_database_with_the_column_returns_rows(self, tmp_path):
        """Positive control for the test above.

        Without this, `test_a_missing_column_raises` would also pass if the
        function raised for some unrelated reason -- or always.
        """
        path = _stripped_db(tmp_path, with_known_issues=True, column="fix_procedure")
        rows = _find_kb_matches_safe(1, path)
        assert len(rows) == 1 and rows[0]["title"] == "t"

    def test_a_missing_table_is_still_an_empty_list(self, tmp_path):
        """The one case the fallback was written for is preserved.

        An older install without the Phase 08 schema gets an empty list,
        not a crash. Narrowing the except must not remove that.
        """
        path = _stripped_db(tmp_path, with_known_issues=False, column=None)
        assert _find_kb_matches_safe(1, path) == []
