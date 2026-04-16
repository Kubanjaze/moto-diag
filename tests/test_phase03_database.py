"""Phase 03 — database schema + SQLite tests."""

import pytest
import sqlite3
from pathlib import Path
from motodiag.core.database import (
    init_db, get_connection, get_schema_version, table_exists, SCHEMA_VERSION,
)


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


class TestInitDB:
    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "new.db")
        assert not Path(path).exists()
        init_db(path)
        assert Path(path).exists()

    def test_creates_parent_dirs(self, tmp_path):
        path = str(tmp_path / "sub" / "dir" / "test.db")
        init_db(path)
        assert Path(path).exists()

    def test_idempotent(self, db_path):
        init_db(db_path)  # second call should not fail


class TestSchema:
    def test_schema_version(self, db_path):
        assert get_schema_version(db_path) == SCHEMA_VERSION

    def test_tables_exist(self, db_path):
        for table in ["vehicles", "dtc_codes", "symptoms", "known_issues",
                       "diagnostic_sessions", "schema_version"]:
            assert table_exists(table, db_path), f"Table {table} missing"

    def test_table_exists_false(self, db_path):
        assert not table_exists("nonexistent_table", db_path)


class TestConnection:
    def test_context_manager(self, db_path):
        with get_connection(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM vehicles")
            assert cursor.fetchone()[0] == 0

    def test_row_factory(self, db_path):
        with get_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO vehicles (make, model, year) VALUES (?, ?, ?)",
                ("Harley-Davidson", "Sportster 1200", 2001),
            )
        with get_connection(db_path) as conn:
            cursor = conn.execute("SELECT * FROM vehicles")
            row = cursor.fetchone()
            assert row["make"] == "Harley-Davidson"
            assert row["year"] == 2001

    def test_rollback_on_error(self, db_path):
        try:
            with get_connection(db_path) as conn:
                conn.execute(
                    "INSERT INTO vehicles (make, model, year) VALUES (?, ?, ?)",
                    ("Honda", "CBR929RR", 2001),
                )
                raise ValueError("Simulated error")
        except ValueError:
            pass

        with get_connection(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM vehicles")
            assert cursor.fetchone()[0] == 0

    def test_insert_dtc(self, db_path):
        with get_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO dtc_codes (code, description, category, severity) VALUES (?, ?, ?, ?)",
                ("P0115", "Engine Coolant Temp Circuit", "cooling", "medium"),
            )
        with get_connection(db_path) as conn:
            cursor = conn.execute("SELECT * FROM dtc_codes WHERE code = ?", ("P0115",))
            row = cursor.fetchone()
            assert row["description"] == "Engine Coolant Temp Circuit"

    def test_insert_session(self, db_path):
        with get_connection(db_path) as conn:
            conn.execute(
                """INSERT INTO diagnostic_sessions
                   (vehicle_make, vehicle_model, vehicle_year, status, symptoms)
                   VALUES (?, ?, ?, ?, ?)""",
                ("Kawasaki", "ZX-6R", 2003, "open", '["wont start"]'),
            )
        with get_connection(db_path) as conn:
            cursor = conn.execute("SELECT * FROM diagnostic_sessions")
            row = cursor.fetchone()
            assert row["vehicle_make"] == "Kawasaki"
            assert row["status"] == "open"


class TestSchemaVersionNoDB:
    def test_no_db_returns_none(self, tmp_path):
        assert get_schema_version(str(tmp_path / "nope.db")) is None
