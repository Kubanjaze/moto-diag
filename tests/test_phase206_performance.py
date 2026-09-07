"""Phase 206 — performance defects, and the harness that pins them.

The dev database holds 6 work orders and 5 parts, and the measured API
baseline before this phase was 2-10ms across every endpoint. **Nothing
was slow.** So this suite asserts SHAPE, never duration:

- how many rows a query pulls out of SQLite
- how many statements a code path issues, and whether that number grows
  with N
- what EXPLAIN QUERY PLAN says about a sort
- whether a handler declares itself async without ever awaiting

Every one of those is true on any machine, on any dataset, forever. A
millisecond figure on a 16MB database would be fiction with a decimal
point, and is deliberately absent from this file.
"""

from __future__ import annotations

import inspect
import json
import sqlite3
from contextlib import contextmanager

import pytest

from motodiag.api.app import create_app
from motodiag.core.database import get_connection, init_db
from motodiag.knowledge.dtc_repo import get_dtc, get_dtcs
from motodiag.knowledge.issues_repo import (
    count_known_issues_matching, search_known_issues,
)
from motodiag.reporting.builders import build_session_report_doc


@contextmanager
def counting_queries():
    """Count sqlite statements executed inside the block.

    Query count is the honest metric for an N+1: it does not move with
    hardware, dataset size, or how warm the page cache happens to be.
    """
    counter = {"n": 0}
    original = sqlite3.connect

    def traced(*args, **kwargs):
        conn = original(*args, **kwargs)
        conn.set_trace_callback(
            lambda _stmt: counter.__setitem__("n", counter["n"] + 1),
        )
        return conn

    sqlite3.connect = traced
    try:
        yield counter
    finally:
        sqlite3.connect = original


@pytest.fixture
def seeded_db(tmp_path):
    """A database with enough rows that a per-row query is visible.

    Deliberately modest. It exists so a query COUNT can be compared
    across different N — not so latency can be graphed, which at this
    size would be meaningless.
    """
    path = str(tmp_path / "perf.db")
    init_db(path)
    with get_connection(path) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES ('perf', 'perf@ex.com', 'individual', 1)",
        ).lastrowid
        codes = [f"P{200 + i:04d}" for i in range(25)]
        for code in codes:
            conn.execute(
                "INSERT INTO dtc_codes (code, description, category, "
                " severity) VALUES (?, ?, 'engine', 'moderate')",
                (code, f"description for {code}"),
            )
        for i in range(120):
            conn.execute(
                "INSERT INTO known_issues (title, description, make, "
                " model, severity) VALUES (?, ?, 'Harley-Davidson', "
                " 'Road King', ?)",
                (f"issue {i:03d}", f"body {i}", "high" if i % 2 else "low"),
            )
    return path, uid, codes


# ===========================================================================
# 1. Pagination happens in SQL, not in Python
# ===========================================================================


class TestPaginationIsPushedDown:
    """The routes used to fetch every row and slice (`rows[:limit]`), so
    asking for 50 known-issues materialised all 6,600."""

    def test_a_page_pulls_only_the_page(self, seeded_db):
        path, _uid, _codes = seeded_db
        page = search_known_issues(db_path=path, limit=10)
        assert len(page) == 10, "LIMIT is not reaching SQL"

    def test_the_page_is_the_first_page_not_just_ten_rows(self, seeded_db):
        """A LIMIT applied before the ORDER BY would return ten
        arbitrary rows and still pass a length check."""
        path, _uid, _codes = seeded_db
        everything = search_known_issues(db_path=path)
        page = search_known_issues(db_path=path, limit=10)
        assert [r["id"] for r in page] == [r["id"] for r in everything[:10]]

    def test_the_total_is_counted_not_fetched(self, seeded_db):
        """`total` must reflect all matches while the body stays bounded
        — the reason a shared WHERE-clause helper exists."""
        path, _uid, _codes = seeded_db
        total = count_known_issues_matching(db_path=path)
        page = search_known_issues(db_path=path, limit=10)
        assert total == 120
        assert len(page) == 10

    def test_filters_apply_identically_to_page_and_count(self, seeded_db):
        path, _uid, _codes = seeded_db
        total = count_known_issues_matching(db_path=path, severity="high")
        rows = search_known_issues(db_path=path, severity="high")
        assert total == len(rows), (
            "count and search disagree — the WHERE clauses have drifted"
        )

    def test_unbounded_is_still_available(self, seeded_db):
        """`limit=None` must keep working for callers that want it all."""
        path, _uid, _codes = seeded_db
        assert len(search_known_issues(db_path=path)) == 120


# ===========================================================================
# 2. N+1: query count must not grow with N
# ===========================================================================


class TestQueryCountDoesNotGrowWithN:

    def test_bulk_dtc_lookup_matches_single_lookups(self, seeded_db):
        """The batched resolver must agree with N single calls,
        including for unknown codes and mixed case — the report's
        content depends on the make → generic → any fallback order."""
        path, _uid, codes = seeded_db
        probe = codes[:5] + ["P9999", codes[0].lower()]
        singles = {c.upper(): get_dtc(c, db_path=path) for c in probe}
        bulk = get_dtcs(probe, db_path=path)
        for code, expected in singles.items():
            got = bulk.get(code)
            assert (expected is None) == (got is None), code
            if expected is not None:
                assert expected["id"] == got["id"], code

    @pytest.mark.parametrize("n_codes", [1, 5, 25])
    def test_report_query_count_is_flat_in_fault_codes(
        self, seeded_db, n_codes,
    ):
        """Before Phase 206 this grew by up to THREE queries per code,
        because get_dtc walks a make → generic → any fallback chain."""
        path, uid, codes = seeded_db
        with get_connection(path) as conn:
            sid = conn.execute(
                "INSERT INTO diagnostic_sessions (vehicle_make, "
                " vehicle_model, vehicle_year, status, user_id, "
                " fault_codes) VALUES ('Honda','CB',2020,'open',?,?)",
                (uid, json.dumps(codes[:n_codes])),
            ).lastrowid

        with counting_queries() as counter:
            doc = build_session_report_doc(sid, uid, db_path=path)

        section = next(
            (s for s in doc["sections"] if s.get("heading") == "Fault codes"),
            None,
        )
        # Guard the guard: if the section never renders, the count below
        # proves nothing. An unseeded dtc_codes table made exactly this
        # mistake during development.
        assert section is not None, "fault-code path did not run"
        assert len(section["table"]["rows"]) == n_codes

        # A generous ceiling: the point is that it does NOT scale with
        # n_codes, not the exact constant, which other sections affect.
        assert counter["n"] < 25, (
            f"{counter['n']} queries for {n_codes} fault codes — the "
            "count is growing with N again"
        )


# ===========================================================================
# 3. The sort is served by an index
# ===========================================================================


class TestKnownIssuesSortUsesAnIndex:

    def test_no_temp_btree_for_the_listing_sort(self, seeded_db):
        """`known_issues` is the only large table in the product. Its
        listing sorts by (severity DESC, title); without an index SQLite
        sorted every row to return a page."""
        path, _uid, _codes = seeded_db
        with get_connection(path) as conn:
            plan = [
                row[-1] for row in conn.execute(
                    "EXPLAIN QUERY PLAN SELECT * FROM known_issues "
                    "WHERE 1=1 ORDER BY severity DESC, title LIMIT 50",
                )
            ]
        joined = " | ".join(plan)
        assert "TEMP B-TREE" not in joined.upper(), (
            f"the listing sort is unindexed again: {joined}"
        )
        assert "idx_known_issues_sort" in joined, joined


# ===========================================================================
# 4. async means await
# ===========================================================================


class TestAsyncHandlersActuallyAwait:
    """FastAPI threadpools SYNC handlers and runs async ones on the
    event loop. An `async def` that never awaits does blocking IO
    directly on the loop, stalling every other in-flight request — a
    correctness defect wearing performance clothes."""

    def test_no_v1_handler_is_async_without_awaiting(self):
        app = create_app()
        offenders = []
        for route in app.routes:
            path = getattr(route, "path", "")
            handler = getattr(route, "endpoint", None)
            if not path.startswith("/v1") or handler is None:
                continue
            if not inspect.iscoroutinefunction(handler):
                continue
            try:
                source = inspect.getsource(handler)
            except OSError:  # pragma: no cover - source always available
                continue
            if "await " not in source:
                offenders.append(f"{path} [{handler.__name__}]")
        assert not offenders, (
            "these handlers block the event loop; make them `def`: "
            + ", ".join(offenders)
        )


# ===========================================================================
# 5. The KB export supports conditional GET
# ===========================================================================


class TestConditionalGet:
    """Mobile downloaded the whole export and only then compared stamps,
    so the common cold-start case paid a full transfer to learn nothing
    had changed."""

    @pytest.fixture
    def client(self, seeded_db, monkeypatch):
        from fastapi.testclient import TestClient
        from motodiag.auth.api_key_repo import create_api_key
        from motodiag.core.config import reset_settings

        path, uid, _codes = seeded_db
        monkeypatch.setenv("MOTODIAG_DB_PATH", path)
        for tier in ("anonymous", "individual", "shop", "company"):
            monkeypatch.setenv(
                f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
            )
        reset_settings()
        _, key = create_api_key(uid, db_path=path)
        yield TestClient(
            create_app(db_path_override=path),
            raise_server_exceptions=False,
        ), key
        reset_settings()

    def test_export_returns_an_etag(self, client):
        api, key = client
        r = api.get("/v1/kb/export", headers={"X-API-Key": key})
        assert r.status_code == 200
        assert r.headers.get("etag"), "no ETag to revalidate against"

    def test_matching_etag_returns_304_with_no_body(self, client):
        api, key = client
        first = api.get("/v1/kb/export", headers={"X-API-Key": key})
        etag = first.headers["etag"]
        second = api.get(
            "/v1/kb/export",
            headers={"X-API-Key": key, "If-None-Match": etag},
        )
        assert second.status_code == 304
        assert not second.content

    def test_a_stale_etag_still_returns_the_body(self, client):
        api, key = client
        r = api.get(
            "/v1/kb/export",
            headers={"X-API-Key": key, "If-None-Match": '"stale"'},
        )
        assert r.status_code == 200
        assert r.json()["dtcs"]

    def test_the_etag_changes_when_the_content_does(self, client, seeded_db):
        """A stamp that did not move on a content change would serve 304
        to a client that genuinely needs new data."""
        api, key = client
        path, _uid, _codes = seeded_db
        before = api.get(
            "/v1/kb/export", headers={"X-API-Key": key},
        ).headers["etag"]
        with get_connection(path) as conn:
            conn.execute(
                "INSERT INTO dtc_codes (code, description, category, "
                " severity) VALUES ('P8888', 'new code', 'engine', 'low')",
            )
        after = api.get(
            "/v1/kb/export", headers={"X-API-Key": key},
        ).headers["etag"]
        assert before != after
