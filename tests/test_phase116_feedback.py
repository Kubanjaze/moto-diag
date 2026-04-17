"""Phase 116 — Feedback/learning hooks tests.

Tests cover:
- Migration 009 creates diagnostic_feedback + session_overrides tables
- FeedbackOutcome enum (4 members), OverrideField enum (6 members)
- Submit + read feedback; parts_used JSON round trip
- FK CASCADE: deleting a session cascades feedback/overrides
- record_override + get_overrides_for_session
- count_feedback_by_outcome returns all 4 outcomes including zeros
- FeedbackReader: iter_feedback, get_accuracy_metrics, get_common_overrides
- Forward-compat schema version (>= 9)
"""

from datetime import datetime

import pytest

from motodiag.core.database import (
    init_db, get_schema_version, SCHEMA_VERSION, get_connection,
)
from motodiag.core.migrations import (
    get_migration_by_version, rollback_migration,
)
from motodiag.core.session_repo import create_session
from motodiag.feedback import (
    FeedbackOutcome, OverrideField, DiagnosticFeedback, SessionOverride,
    submit_feedback, get_feedback, get_feedback_for_session, list_feedback,
    count_feedback_by_outcome, record_override, get_overrides_for_session,
    count_overrides_for_field, FeedbackReader,
)


# --- Migration 009 ---


class TestMigration009:
    def test_migration_exists(self):
        m = get_migration_by_version(9)
        assert m is not None
        assert "diagnostic_feedback" in m.upgrade_sql.lower()
        assert "session_overrides" in m.upgrade_sql.lower()

    def test_tables_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('diagnostic_feedback', 'session_overrides')"
            )
            tables = {row[0] for row in cursor.fetchall()}
        assert tables == {"diagnostic_feedback", "session_overrides"}

    def test_indexes_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND name LIKE 'idx_feedback%' OR name LIKE 'idx_overrides%'"
            )
            indexes = {row[0] for row in cursor.fetchall()}
        for expected in (
            "idx_feedback_session", "idx_feedback_outcome",
            "idx_overrides_session", "idx_overrides_field",
        ):
            assert expected in indexes

    def test_rollback_drops_tables(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        m = get_migration_by_version(9)
        rollback_migration(m, db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('diagnostic_feedback', 'session_overrides')"
            )
            assert cursor.fetchall() == []


# --- Enums ---


class TestEnums:
    def test_feedback_outcome_has_4_members(self):
        assert len(FeedbackOutcome) == 4
        assert {o.value for o in FeedbackOutcome} == {
            "correct", "partially_correct", "incorrect", "inconclusive",
        }

    def test_override_field_has_6_members(self):
        assert len(OverrideField) == 6
        assert {f.value for f in OverrideField} == {
            "diagnosis", "severity", "cost_estimate",
            "confidence", "repair_steps", "parts",
        }


# --- Feedback CRUD ---


def _make_session(db):
    """Helper: create a diagnostic session and return its id."""
    return create_session(
        "Harley-Davidson", "Sportster 1200", 2001,
        symptoms=["won't start"], fault_codes=["P0562"], db_path=db,
    )


class TestFeedbackCRUD:
    def test_submit_and_get(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        fb = DiagnosticFeedback(
            session_id=sid,
            ai_suggested_diagnosis="Stator failure",
            ai_confidence=0.78,
            actual_diagnosis="Regulator failure",
            actual_fix="Replaced regulator with MOSFET unit",
            outcome=FeedbackOutcome.PARTIALLY_CORRECT,
            mechanic_notes="AI flagged charging system correctly, wrong root cause",
            parts_used=["Regulator (MOSFET)", "Connector"],
            actual_labor_hours=1.5,
        )
        fid = submit_feedback(fb, db)
        assert fid > 0

        row = get_feedback(fid, db)
        assert row["outcome"] == "partially_correct"
        assert row["parts_used"] == ["Regulator (MOSFET)", "Connector"]
        assert row["actual_labor_hours"] == 1.5

    def test_feedback_defaults_to_system_user(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        fb = DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.CORRECT)
        fid = submit_feedback(fb, db)
        row = get_feedback(fid, db)
        assert row["submitted_by_user_id"] == 1

    def test_get_feedback_for_session(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        for outcome in (FeedbackOutcome.CORRECT, FeedbackOutcome.INCORRECT):
            submit_feedback(
                DiagnosticFeedback(session_id=sid, outcome=outcome), db,
            )
        rows = get_feedback_for_session(sid, db)
        assert len(rows) == 2

    def test_get_missing_returns_none(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_feedback(99999, db) is None

    def test_empty_parts_used(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        fb = DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.CORRECT)
        fid = submit_feedback(fb, db)
        row = get_feedback(fid, db)
        assert row["parts_used"] == []

    def test_list_feedback_filters(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        submit_feedback(DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.CORRECT), db)
        submit_feedback(DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.CORRECT), db)
        submit_feedback(DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.INCORRECT), db)

        assert len(list_feedback(outcome="correct", db_path=db)) == 2
        assert len(list_feedback(outcome=FeedbackOutcome.INCORRECT, db_path=db)) == 1
        assert len(list_feedback(db_path=db)) == 3
        assert len(list_feedback(limit=2, db_path=db)) == 2

    def test_count_by_outcome_includes_zeros(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        counts = count_feedback_by_outcome(db)
        assert counts == {
            "correct": 0, "partially_correct": 0,
            "incorrect": 0, "inconclusive": 0,
        }

    def test_count_by_outcome_tallies(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        for _ in range(3):
            submit_feedback(DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.CORRECT), db)
        submit_feedback(DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.INCORRECT), db)
        counts = count_feedback_by_outcome(db)
        assert counts["correct"] == 3
        assert counts["incorrect"] == 1
        assert counts["partially_correct"] == 0


# --- FK CASCADE ---


class TestCascadeBehavior:
    def test_delete_session_cascades_feedback(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        submit_feedback(DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.CORRECT), db)
        assert len(get_feedback_for_session(sid, db)) == 1

        with get_connection(db) as conn:
            conn.execute("DELETE FROM diagnostic_sessions WHERE id = ?", (sid,))

        assert get_feedback_for_session(sid, db) == []

    def test_delete_session_cascades_overrides(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        record_override(SessionOverride(
            session_id=sid, field_name=OverrideField.DIAGNOSIS,
            ai_value="Stator", override_value="Regulator",
        ), db)
        assert len(get_overrides_for_session(sid, db)) == 1

        with get_connection(db) as conn:
            conn.execute("DELETE FROM diagnostic_sessions WHERE id = ?", (sid,))

        assert get_overrides_for_session(sid, db) == []


# --- Overrides ---


class TestOverrides:
    def test_record_and_read(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        oid = record_override(SessionOverride(
            session_id=sid, field_name=OverrideField.DIAGNOSIS,
            ai_value="Stator failure", override_value="Regulator failure",
            reason="Charging voltage test showed regulator at fault",
        ), db)
        assert oid > 0
        rows = get_overrides_for_session(sid, db)
        assert len(rows) == 1
        assert rows[0]["field_name"] == "diagnosis"
        assert rows[0]["override_value"] == "Regulator failure"

    def test_count_overrides_for_field(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        for _ in range(3):
            record_override(SessionOverride(
                session_id=sid, field_name=OverrideField.DIAGNOSIS,
            ), db)
        record_override(SessionOverride(
            session_id=sid, field_name=OverrideField.SEVERITY,
        ), db)
        assert count_overrides_for_field(OverrideField.DIAGNOSIS, db) == 3
        assert count_overrides_for_field("severity", db) == 1
        assert count_overrides_for_field(OverrideField.COST_ESTIMATE, db) == 0


# --- FeedbackReader ---


class TestFeedbackReader:
    def test_iter_feedback_chronological(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        outcomes = [
            FeedbackOutcome.CORRECT,
            FeedbackOutcome.PARTIALLY_CORRECT,
            FeedbackOutcome.INCORRECT,
        ]
        for o in outcomes:
            submit_feedback(DiagnosticFeedback(session_id=sid, outcome=o), db)

        reader = FeedbackReader(db)
        rows = list(reader.iter_feedback())
        assert [r["outcome"] for r in rows] == [o.value for o in outcomes]

    def test_iter_feedback_filtered_by_outcome(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        submit_feedback(DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.CORRECT), db)
        submit_feedback(DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.INCORRECT), db)
        submit_feedback(DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.CORRECT), db)

        reader = FeedbackReader(db)
        correct_rows = list(reader.iter_feedback(outcome=FeedbackOutcome.CORRECT))
        assert len(correct_rows) == 2
        assert all(r["outcome"] == "correct" for r in correct_rows)

    def test_accuracy_metrics_empty(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        metrics = FeedbackReader(db).get_accuracy_metrics()
        assert metrics["total"] == 0
        assert metrics["correct_ratio"] == 0.0

    def test_accuracy_metrics_populated(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        for _ in range(7):
            submit_feedback(DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.CORRECT), db)
        for _ in range(2):
            submit_feedback(
                DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.PARTIALLY_CORRECT), db,
            )
        submit_feedback(DiagnosticFeedback(session_id=sid, outcome=FeedbackOutcome.INCORRECT), db)

        metrics = FeedbackReader(db).get_accuracy_metrics()
        assert metrics["total"] == 10
        assert metrics["correct"] == 7
        assert metrics["partially_correct"] == 2
        assert metrics["incorrect"] == 1
        assert metrics["correct_ratio"] == 0.7
        assert metrics["partial_plus_correct_ratio"] == 0.9

    def test_get_common_overrides(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        for _ in range(4):
            record_override(SessionOverride(
                session_id=sid, field_name=OverrideField.DIAGNOSIS,
            ), db)
        for _ in range(2):
            record_override(SessionOverride(
                session_id=sid, field_name=OverrideField.SEVERITY,
            ), db)
        record_override(SessionOverride(
            session_id=sid, field_name=OverrideField.COST_ESTIMATE,
        ), db)

        top = FeedbackReader(db).get_common_overrides(top_n=3)
        assert top[0] == {"field_name": "diagnosis", "count": 4}
        assert top[1] == {"field_name": "severity", "count": 2}
        assert top[2] == {"field_name": "cost_estimate", "count": 1}

    def test_get_common_overrides_limit(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = _make_session(db)
        for f in (OverrideField.DIAGNOSIS, OverrideField.SEVERITY, OverrideField.PARTS):
            record_override(SessionOverride(session_id=sid, field_name=f), db)
        top = FeedbackReader(db).get_common_overrides(top_n=2)
        assert len(top) == 2


# --- Forward compat ---


class TestSchemaVersionForwardCompat:
    def test_schema_version_at_least_9(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_schema_version(db) >= 9

    def test_schema_version_constant_at_least_9(self):
        assert SCHEMA_VERSION >= 9
