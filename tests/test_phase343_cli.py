"""Phase 343, items 6 and 7: ``motodiag telemetry`` and the documents."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

import motodiag.cli.telemetry as cli_telemetry
from motodiag.cli.main import cli
from motodiag.core.config import reset_settings
from tests.support.phase343 import DSN_TEXT, HOST, PLANTED_KEY, PROJECT_ID, FakeTransport

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def run(monkeypatch):
    """Invoke the CLI with a DSN (or none) and a fake transport."""
    fake = FakeTransport()
    monkeypatch.setattr(cli_telemetry, "TRANSPORT", fake)

    def invoke(args: list[str], dsn: str | None = DSN_TEXT):
        if dsn is None:
            monkeypatch.delenv("MOTODIAG_SENTRY_DSN", raising=False)
        else:
            monkeypatch.setenv("MOTODIAG_SENTRY_DSN", dsn)
        reset_settings()
        try:
            return CliRunner().invoke(cli, args)
        finally:
            reset_settings()

    invoke.fake = fake  # type: ignore[attr-defined]
    yield invoke
    reset_settings()


class TestStatus:
    def test_on_names_the_project_and_never_the_key(self, run):
        r = run(["telemetry", "status"])
        assert r.exit_code == 0, r.output
        assert "telemetry: on" in r.output
        assert f"{HOST}/{PROJECT_ID}" in r.output
        assert "sample rate: 0.1" in r.output
        assert PLANTED_KEY not in r.output

    def test_control_the_key_check_sees_a_printed_key(self, run, monkeypatch):
        monkeypatch.setattr(cli_telemetry.Dsn, "__str__",
                            lambda self: f"{self.public_key}@{self.host}")
        r = run(["telemetry", "status"])
        assert PLANTED_KEY in r.output

    def test_off_exits_1(self, run):
        r = run(["telemetry", "status"], dsn=None)
        assert r.exit_code == 1 and "off" in r.output

    def test_malformed_exits_2_naming_the_part(self, run):
        r = run(["telemetry", "status"], dsn=f"https://{PLANTED_KEY}@{HOST}/")
        assert r.exit_code == 2 and "project id" in r.output
        assert PLANTED_KEY not in r.output


class TestCheck:
    def test_sends_one_event_and_prints_its_id(self, run):
        r = run(["telemetry", "check"])
        assert r.exit_code == 0, r.output
        fake = run.fake
        assert len(fake.requests) == 1
        _, _, body = fake.requests[0]
        header, item, payload = body.split(b"\n")[:3]
        assert json.loads(item)["type"] == "event"
        event_id = json.loads(payload)["event_id"]
        assert json.loads(header)["event_id"] == event_id
        assert event_id in r.output
        assert f"{HOST}/{PROJECT_ID}" in r.output
        assert "telemetry check from" in json.loads(payload)["message"]["formatted"]
        assert PLANTED_KEY not in r.output

    def test_a_401_exits_1_naming_it(self, run):
        run.fake.status, run.fake.reason = 401, "Unauthorized"
        r = run(["telemetry", "check"])
        assert r.exit_code == 1 and "401" in r.output

    def test_a_transport_error_exits_1(self, run):
        run.fake.raises = OSError("refused")
        r = run(["telemetry", "check"])
        assert r.exit_code == 1 and "OSError" in r.output

    def test_no_dsn_exits_2(self, run):
        r = run(["telemetry", "check"], dsn=None)
        assert r.exit_code == 2
        assert run.fake.requests == []


def test_help_lists_both_commands():
    r = CliRunner().invoke(cli, ["telemetry", "--help"])
    assert r.exit_code == 0
    assert "status" in r.output and "check" in r.output


class TestTheDocuments:
    def test_the_guide_is_on_backend_docs(self):
        from tests.test_phase208_docs import BACKEND_DOCS
        assert ROOT / "docs" / "guide" / "telemetry.md" in BACKEND_DOCS

    def test_the_checklist_note_is_dated_and_names_the_phase(self):
        text = (ROOT / "docs" / "launch-checklist.md").read_text(encoding="utf-8")
        assert "2026-11-01" in text and "Phase 343" in text

    def test_the_install_guide_points_to_the_guide(self):
        text = (ROOT / "docs" / "guide" / "install.md").read_text(encoding="utf-8")
        assert "telemetry.md" in text
