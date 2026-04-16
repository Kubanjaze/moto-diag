"""Phase 07 — diagnostic session lifecycle tests."""

import pytest
from motodiag.core.database import init_db
from motodiag.core.session_repo import (
    create_session, get_session, update_session,
    add_symptom_to_session, add_fault_code_to_session,
    set_diagnosis, close_session, list_sessions, count_sessions,
)


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture
def session_id(db_path):
    return create_session(
        "Harley-Davidson", "Sportster 1200", 2001,
        symptoms=["won't start when cold"],
        db_path=db_path,
    )


class TestCreateSession:
    def test_returns_id(self, session_id):
        assert session_id > 0

    def test_initial_status(self, db_path, session_id):
        s = get_session(session_id, db_path)
        assert s["status"] == "open"
        assert s["vehicle_make"] == "Harley-Davidson"

    def test_with_symptoms(self, db_path, session_id):
        s = get_session(session_id, db_path)
        assert "won't start when cold" in s["symptoms"]

    def test_with_fault_codes(self, db_path):
        sid = create_session("Honda", "CBR929RR", 2001,
                             fault_codes=["P0115", "P0120"], db_path=db_path)
        s = get_session(sid, db_path)
        assert len(s["fault_codes"]) == 2


class TestSessionUpdates:
    def test_add_symptom(self, db_path, session_id):
        add_symptom_to_session(session_id, "rough idle", db_path)
        s = get_session(session_id, db_path)
        assert "rough idle" in s["symptoms"]
        assert len(s["symptoms"]) == 2  # original + new

    def test_add_duplicate_symptom_ignored(self, db_path, session_id):
        add_symptom_to_session(session_id, "won't start when cold", db_path)
        s = get_session(session_id, db_path)
        assert s["symptoms"].count("won't start when cold") == 1

    def test_add_fault_code(self, db_path, session_id):
        add_fault_code_to_session(session_id, "P0562", db_path)
        s = get_session(session_id, db_path)
        assert "P0562" in s["fault_codes"]

    def test_update_status(self, db_path, session_id):
        update_session(session_id, {"status": "in_progress"}, db_path)
        s = get_session(session_id, db_path)
        assert s["status"] == "in_progress"

    def test_update_rejects_invalid_field(self, db_path, session_id):
        assert not update_session(session_id, {"hacker": "drop"}, db_path)


class TestDiagnosis:
    def test_set_diagnosis(self, db_path, session_id):
        set_diagnosis(
            session_id,
            diagnosis="Faulty stator — not charging battery",
            confidence=0.85,
            severity="high",
            repair_steps=["Test stator AC output", "Replace stator", "Test charging"],
            db_path=db_path,
        )
        s = get_session(session_id, db_path)
        assert s["status"] == "diagnosed"
        assert s["confidence"] == 0.85
        assert len(s["repair_steps"]) == 3

    def test_close_session(self, db_path, session_id):
        close_session(session_id, db_path)
        s = get_session(session_id, db_path)
        assert s["status"] == "closed"
        assert s["closed_at"] is not None


class TestListAndCount:
    def test_list_all(self, db_path, session_id):
        create_session("Honda", "CBR929RR", 2001, db_path=db_path)
        results = list_sessions(db_path=db_path)
        assert len(results) == 2

    def test_filter_by_status(self, db_path, session_id):
        close_session(session_id, db_path)
        create_session("Honda", "CBR929RR", 2001, db_path=db_path)
        open_sessions = list_sessions(status="open", db_path=db_path)
        assert len(open_sessions) == 1
        assert open_sessions[0]["vehicle_make"] == "Honda"

    def test_filter_by_make(self, db_path, session_id):
        create_session("Honda", "CBR929RR", 2001, db_path=db_path)
        results = list_sessions(vehicle_make="Harley", db_path=db_path)
        assert len(results) == 1

    def test_count(self, db_path, session_id):
        assert count_sessions(db_path=db_path) == 1
        assert count_sessions(status="open", db_path=db_path) == 1
        assert count_sessions(status="closed", db_path=db_path) == 0

    def test_get_nonexistent(self, db_path):
        assert get_session(999, db_path) is None
