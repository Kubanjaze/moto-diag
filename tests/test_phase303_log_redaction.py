"""Phase 303 — uvicorn's own logs carry no session token (the operator's K56
requirement 3).

uvicorn 0.49 writes the HTTP request line, query string included, on
`uvicorn.access`, and a WebSocket handshake's path, query string included,
on `uvicorn.error` (`uvicorn/protocols/websockets/*_impl.py`). `motodiag
serve` passes `uvicorn.run` a `log_config` that attaches a redaction filter
to both. These tests take the config `serve` really passes, apply it, and
emit records the way uvicorn emits them.
"""

from __future__ import annotations

import logging
import logging.config
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from motodiag.cli.serve import REDACTED, RedactSessionTokens, uvicorn_log_config

TOKEN = "mds_AbCdEfGh1234-_xyzXYZ0987654321abcd"
KEY = "mdk_live_AbCdEfGhIjKlMnOpQrStUvWxYz012345"
NAMES = ("uvicorn", "uvicorn.access", "uvicorn.error")


class _Capture(logging.Handler):
    def __init__(self, formatter):
        super().__init__()
        self.setFormatter(formatter)
        self.lines: list[str] = []

    def emit(self, record):
        self.lines.append(self.format(record))


@pytest.fixture
def restore_uvicorn_loggers():
    saved = {}
    for name in NAMES:
        lg = logging.getLogger(name)
        saved[name] = (list(lg.handlers), list(lg.filters), lg.level, lg.propagate)
    yield
    for name, (handlers, filters, level, propagate) in saved.items():
        lg = logging.getLogger(name)
        lg.handlers[:] = handlers
        lg.filters[:] = filters
        lg.setLevel(level)
        lg.propagate = propagate


@pytest.fixture
def served_config(tmp_path, monkeypatch):
    """The log_config `motodiag serve` passes to uvicorn.run."""
    from motodiag.cli.main import cli
    from motodiag.core.config import reset_settings

    monkeypatch.setenv("MOTODIAG_DB_PATH", str(tmp_path / "serve.db"))
    reset_settings()
    with patch("uvicorn.run") as run:
        result = CliRunner().invoke(cli, ["serve"])
    reset_settings()
    assert result.exit_code == 0, result.output
    return run.call_args.kwargs["log_config"]


def _emit(config, credential):
    """Apply ``config``, then log the three lines uvicorn writes for a
    socket opened with ``credential`` in its query string."""
    from uvicorn.logging import AccessFormatter, DefaultFormatter

    logging.config.dictConfig(config)
    access = _Capture(AccessFormatter(
        '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        use_colors=False))
    error = _Capture(DefaultFormatter("%(levelprefix)s %(message)s", use_colors=False))
    logging.getLogger("uvicorn.access").addHandler(access)
    logging.getLogger("uvicorn").addHandler(error)
    path = f"/v1/live/1?api_key={credential}"
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d', "127.0.0.1:50000", "GET", path, "1.1", 200)
    logging.getLogger("uvicorn.error").info(
        '%s - "WebSocket %s" [accepted]', "127.0.0.1:50000", path)
    logging.getLogger("uvicorn.error").info(
        '%s - "WebSocket %s" 403', "127.0.0.1:50000", path)
    return access.lines + error.lines


def test_serve_passes_a_config_with_the_filter_on_both_loggers(served_config):
    assert served_config["filters"]["redact_session_tokens"]["()"] == (
        "motodiag.cli.serve.RedactSessionTokens")
    for name in ("uvicorn.access", "uvicorn.error"):
        assert "redact_session_tokens" in served_config["loggers"][name]["filters"]


def test_the_served_config_removes_a_session_token(served_config, restore_uvicorn_loggers):
    lines = _emit(served_config, TOKEN)
    assert len(lines) == 3
    assert not any("mds_" in line for line in lines), lines
    assert all(REDACTED in line for line in lines)
    assert "GET /v1/live/1?api_key=" in lines[0] and "200" in lines[0]
    assert '"WebSocket /v1/live/1?api_key=' in lines[1] and "[accepted]" in lines[1]


def test_a_key_in_the_same_place_is_unchanged(served_config, restore_uvicorn_loggers):
    lines = _emit(served_config, KEY)
    assert len(lines) == 3 and all(KEY in line for line in lines)


def test_the_control_uvicorns_default_config_carries_the_token(restore_uvicorn_loggers):
    from uvicorn.config import LOGGING_CONFIG

    lines = _emit(LOGGING_CONFIG, TOKEN)
    assert len(lines) == 3 and all(TOKEN in line for line in lines)


def test_the_filter_takes_the_message_and_dict_arguments():
    f = RedactSessionTokens()
    rec = logging.LogRecord("x", logging.INFO, __file__, 1, f"saw {TOKEN}", None, None)
    f.filter(rec)
    assert "mds_" not in rec.getMessage()
    rec = logging.LogRecord("x", logging.INFO, __file__, 1, "saw %(t)s", ({"t": TOKEN},), None)
    f.filter(rec)
    assert "mds_" not in rec.getMessage()


def test_the_config_does_not_change_uvicorns_own():
    from uvicorn.config import LOGGING_CONFIG

    assert "filters" not in LOGGING_CONFIG
    assert "filters" not in LOGGING_CONFIG["loggers"]["uvicorn.access"]
    assert uvicorn_log_config()["loggers"]["uvicorn"] == LOGGING_CONFIG["loggers"]["uvicorn"]
