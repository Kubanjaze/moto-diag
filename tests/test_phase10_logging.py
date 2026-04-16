"""Phase 10 — logging + audit trail tests."""

import logging
import pytest
from motodiag.core.logging import setup_logging, get_logger, reset_logging


@pytest.fixture(autouse=True)
def clean_logging():
    """Reset logging state between tests."""
    reset_logging()
    yield
    reset_logging()


class TestSetupLogging:
    def test_returns_logger(self):
        logger = setup_logging(level="DEBUG")
        assert logger.name == "motodiag"
        assert logger.level == logging.DEBUG

    def test_info_level(self):
        logger = setup_logging(level="INFO")
        assert logger.level == logging.INFO

    def test_idempotent(self):
        l1 = setup_logging()
        l2 = setup_logging()
        assert l1 is l2
        assert len(l1.handlers) == 1  # only one console handler

    def test_file_logging(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        logger = setup_logging(level="DEBUG", log_file=log_file)
        logger.info("test message")
        # Flush handlers
        for h in logger.handlers:
            h.flush()
        with open(log_file) as f:
            content = f.read()
        assert "test message" in content

    def test_file_creates_parent_dirs(self, tmp_path):
        log_file = str(tmp_path / "sub" / "dir" / "test.log")
        setup_logging(log_file=log_file)
        from pathlib import Path
        assert Path(log_file).parent.exists()


class TestGetLogger:
    def test_child_logger(self):
        setup_logging()
        logger = get_logger("sessions")
        assert logger.name == "motodiag.sessions"

    def test_child_inherits_level(self):
        setup_logging(level="DEBUG")
        logger = get_logger("test")
        assert logger.getEffectiveLevel() == logging.DEBUG


class TestSessionLogging:
    def test_session_create_logs(self, tmp_path, caplog):
        from motodiag.core.database import init_db
        from motodiag.core.session_repo import create_session

        db = str(tmp_path / "test.db")
        init_db(db)
        setup_logging(level="DEBUG")

        with caplog.at_level(logging.INFO, logger="motodiag.sessions"):
            create_session("Harley-Davidson", "Sportster", 2001, db_path=db)

        assert any("Session" in r.message and "created" in r.message for r in caplog.records)

    def test_session_close_logs(self, tmp_path, caplog):
        from motodiag.core.database import init_db
        from motodiag.core.session_repo import create_session, close_session

        db = str(tmp_path / "test.db")
        init_db(db)
        setup_logging(level="DEBUG")

        sid = create_session("Honda", "CBR929RR", 2001, db_path=db)
        with caplog.at_level(logging.INFO, logger="motodiag.sessions"):
            close_session(sid, db)

        assert any("closed" in r.message for r in caplog.records)
