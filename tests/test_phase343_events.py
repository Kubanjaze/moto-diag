"""Phase 343, item 3: what an event carries, by the operator's rule."""

from __future__ import annotations

import inspect
import json
import re

import pytest

from motodiag.telemetry import events
from motodiag.telemetry.events import (
    error_event,
    message_event,
    redact,
    transaction_event,
)

CTX = {"release": "motodiag@9.9.9", "environment": "test",
       "server_name": "bench-host"}
TEMPLATE = "/v1/shop/{shop_id}/work-orders/{wo_id}"
TOKEN = "mds_PlantedSessionToken0343"


def _planted_failure(message: str) -> BaseException:
    try:
        raise RuntimeError(message)
    except RuntimeError as exc:
        return exc


def _event(message: str = "boom", route: str = TEMPLATE) -> dict:
    return error_event(_planted_failure(message), request_id="rid-1",
                       method="GET", route=route, status=500,
                       clock=lambda: "2026-11-01T00:00:00.000+00:00", **CTX)


class TestTheErrorEvent:
    def test_the_raising_function_is_an_in_app_frame(self):
        ev = _event()
        frames = ev["exception"]["values"][0]["stacktrace"]["frames"]
        mine = [f for f in frames if f["function"] == "_planted_failure"]
        assert len(mine) == 1
        line = inspect.getsourcelines(_planted_failure)[1] + 2
        assert mine[0]["lineno"] == line
        assert mine[0]["filename"] == "test_phase343_events.py"
        for f in frames:
            assert set(f) == {"filename", "function", "lineno", "in_app"}
            assert "vars" not in f and "context_line" not in f

    def test_a_package_frame_is_in_app_and_relative(self):
        from motodiag.telemetry.dsn import parse_dsn
        try:
            parse_dsn("")
        except ValueError as exc:
            frames = events.frames(exc)
        pkg = [f for f in frames if f["function"] == "parse_dsn"]
        assert pkg[0]["in_app"] is True
        assert pkg[0]["filename"] == "motodiag/telemetry/dsn.py"

    def test_a_site_packages_frame_keeps_no_home(self):
        name, in_app = events._frame_file(
            "/home/someone/.venv/lib/python3.14/site-packages/starlette/routing.py")
        assert (name, in_app) == ("starlette/routing.py", False)
        assert events._frame_file("/home/someone/x.py") == ("x.py", False)

    def test_the_shape(self):
        ev = _event()
        assert re.fullmatch(r"[0-9a-f]{32}", ev["event_id"])
        assert ev["timestamp"] == "2026-11-01T00:00:00.000+00:00"
        assert ev["level"] == "error" and ev["platform"] == "python"
        assert ev["tags"] == {"request_id": "rid-1", "route": TEMPLATE,
                              "method": "GET", "status": "500"}
        assert ev["release"] == "motodiag@9.9.9"
        assert ev["exception"]["values"][0]["type"] == "RuntimeError"
        json.dumps(ev)

    def test_the_url_is_the_template_not_the_path(self):
        ev = _event()
        assert ev["request"]["url"] == TEMPLATE
        assert not re.search(r"\d{5}", json.dumps(ev["request"]))
        assert not re.search(r"\d{5}", json.dumps(ev["tags"]))

    def test_the_signature_takes_no_request(self):
        for fn in (error_event, transaction_event, message_event):
            names = set(inspect.signature(fn).parameters)
            assert not names & {"request", "headers", "body", "query"}


class TestRedaction:
    def test_a_session_token_is_blanked(self):
        value = _event(f"bad token {TOKEN} seen")["exception"]["values"][0]["value"]
        assert TOKEN not in value and "[session token redacted]" in value

    def test_control_without_redact_the_token_shows(self, monkeypatch):
        monkeypatch.setattr(events, "redact", lambda text: text)
        value = _event(f"bad token {TOKEN} seen")["exception"]["values"][0]["value"]
        assert TOKEN in value

    @pytest.mark.parametrize("planted", [
        "jo.mechanic+bench@shop.example.com", "555-867-5309",
        "+1 (555) 867-5309", "8675309", "+44 20 7946 0958",
    ])
    def test_an_email_or_phone_is_blanked(self, planted):
        out = redact(f"customer {planted} not found")
        assert planted not in out
        assert "redacted]" in out

    @pytest.mark.parametrize("kept", [
        "work order 42 not found", "line 1234", "shop 123456",
        "version 1.2.3", "id 12345678901234567890",
    ])
    def test_short_numbers_and_long_ids_are_kept(self, kept):
        assert redact(kept) == kept

    def test_a_long_message_is_cut_to_500(self):
        value = _event("x" * 2000)["exception"]["values"][0]["value"]
        assert len(value) == 500


class TestTheTransaction:
    @pytest.mark.parametrize("status, word", [(200, "ok"), (404, "ok"),
                                              (500, "internal_error")])
    def test_the_status(self, status, word):
        tx = transaction_event(route=TEMPLATE, method="GET", status=status,
                               started=100.0, ended=100.25,
                               request_id="rid-2", **CTX)
        assert tx["contexts"]["trace"]["status"] == word
        assert tx["type"] == "transaction"
        assert tx["transaction"] == f"GET {TEMPLATE}"
        assert (tx["start_timestamp"], tx["timestamp"]) == (100.0, 100.25)
        assert re.fullmatch(r"[0-9a-f]{32}", tx["contexts"]["trace"]["trace_id"])
        assert re.fullmatch(r"[0-9a-f]{16}", tx["contexts"]["trace"]["span_id"])
        assert tx["contexts"]["trace"]["op"] == "http.server"
        assert tx["spans"] == []


class TestTheMessage:
    def test_the_check_message(self):
        ev = message_event("telemetry check from bench-host", clock=lambda: "T",
                           **CTX)
        assert ev["message"]["formatted"] == "telemetry check from bench-host"
        assert ev["timestamp"] == "T" and "type" not in ev
