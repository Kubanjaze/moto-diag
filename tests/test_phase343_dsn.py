"""Phase 343, item 2: the DSN, the three settings and the mask in
``config show``."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from motodiag.core.config import Environment, Settings, reset_settings
from motodiag.telemetry.dsn import Dsn, DsnError, parse_dsn
from tests.support.phase343 import DSN_TEXT, HOST, PLANTED_KEY, PROJECT_ID

DOC_EXAMPLE = "https://examplePublicKey@o0.ingest.sentry.io/0"


class TestTheDsn:
    def test_the_documentation_example(self):
        dsn = parse_dsn(DOC_EXAMPLE)
        assert dsn.host == "o0.ingest.sentry.io"
        assert dsn.public_key == "examplePublicKey"
        assert dsn.project_id == "0"
        assert dsn.envelope_url == "https://o0.ingest.sentry.io/api/0/envelope/"
        assert dsn.envelope_url.endswith("/api/0/envelope/")

    def test_a_port_and_a_path_prefix(self):
        dsn = parse_dsn("http://abc@sentry.local:9000/base/sub/42")
        assert dsn.port == 9000
        assert dsn.path_prefix == "base/sub/"
        assert dsn.envelope_url == "http://sentry.local:9000/base/sub/api/42/envelope/"

    def test_the_auth_header(self):
        dsn = parse_dsn(DSN_TEXT)
        assert dsn.auth_header.startswith("Sentry sentry_version=7, sentry_client=motodiag/")
        assert dsn.auth_header.endswith(f"sentry_key={PLANTED_KEY}")

    @pytest.mark.parametrize("text, missing", [
        (f"https://{HOST}/{PROJECT_ID}", "public key"),
        (f"https://{PLANTED_KEY}@{HOST}/", "project id"),
        (f"https://{PLANTED_KEY}@{HOST}", "project id"),
        (f"ftp://{PLANTED_KEY}@{HOST}/1", "scheme"),
        (f"https://{PLANTED_KEY}@{HOST}:notaport/1", "port"),
        ("", "scheme"),
    ])
    def test_a_refusal_names_the_part_and_echoes_nothing(self, text, missing):
        with pytest.raises(DsnError) as info:
            parse_dsn(text)
        assert missing in str(info.value)
        assert PLANTED_KEY not in str(info.value)
        assert HOST not in str(info.value)

    def test_no_host_is_refused(self):
        with pytest.raises(DsnError, match="no host"):
            parse_dsn(f"https://{PLANTED_KEY}@/1")

    def test_the_repr_and_str_hold_no_key(self):
        dsn = parse_dsn(DSN_TEXT)
        assert not _shows_key(dsn)
        assert HOST in repr(dsn) and PROJECT_ID in str(dsn)

    def test_control_a_repr_printing_the_key_is_seen(self, monkeypatch):
        """The same assertion goes red when the key is printed on purpose."""
        dsn = parse_dsn(DSN_TEXT)
        monkeypatch.setattr(Dsn, "__repr__",
                            lambda self: f"Dsn(key={self.public_key!r})")
        assert _shows_key(dsn)


def _shows_key(dsn: Dsn) -> bool:
    shown = (repr(dsn), str(dsn), f"{dsn!r}", repr([dsn]))
    return any(PLANTED_KEY in s for s in shown)


class TestTheSettings:
    def test_an_empty_dsn_is_off_and_the_defaults(self, monkeypatch):
        monkeypatch.delenv("MOTODIAG_SENTRY_DSN", raising=False)
        s = Settings()
        assert s.sentry_dsn == ""
        assert s.telemetry_traces_sample_rate == 0.1
        assert s.telemetry_environment == ""

    def test_the_settings_read_the_environment(self, monkeypatch):
        monkeypatch.setenv("MOTODIAG_SENTRY_DSN", DSN_TEXT)
        monkeypatch.setenv("MOTODIAG_TELEMETRY_TRACES_SAMPLE_RATE", "1.0")
        monkeypatch.setenv("MOTODIAG_TELEMETRY_ENVIRONMENT", "shop")
        s = Settings()
        assert s.sentry_dsn == DSN_TEXT
        assert s.telemetry_traces_sample_rate == 1.0
        assert s.telemetry_environment_name == "shop"

    @pytest.mark.parametrize("rate", [0.0, 1.0])
    def test_the_bounds_are_read(self, rate):
        assert Settings(telemetry_traces_sample_rate=rate).telemetry_traces_sample_rate == rate

    @pytest.mark.parametrize("rate", [1.5, -0.1])
    def test_outside_the_bounds_is_refused(self, rate):
        with pytest.raises(ValueError, match="telemetry_traces_sample_rate"):
            Settings(telemetry_traces_sample_rate=rate)

    def test_the_environment_falls_back_to_env(self):
        s = Settings(env=Environment.PROD, telemetry_environment="")
        assert s.telemetry_environment_name == "prod"


def _config_show(monkeypatch) -> str:
    from motodiag.cli.main import cli
    monkeypatch.setenv("MOTODIAG_SENTRY_DSN", DSN_TEXT)
    monkeypatch.setenv("COLUMNS", "300")
    reset_settings()
    try:
        result = CliRunner().invoke(cli, ["config", "show"])
    finally:
        monkeypatch.delenv("MOTODIAG_SENTRY_DSN")
        reset_settings()
    assert result.exit_code == 0, result.output
    return result.output


class TestConfigShowMasksTheDsn:
    def test_the_row_is_masked_and_the_key_never_prints(self, monkeypatch):
        out = _config_show(monkeypatch)
        row = next(line for line in out.splitlines() if "sentry_dsn" in line)
        assert "****" + DSN_TEXT[-4:] in row
        assert PLANTED_KEY not in out

    def test_control_without_the_mask_the_key_prints(self, monkeypatch):
        import motodiag.cli.main as main
        monkeypatch.setattr(main, "SECRET_SETTING_NAMES", ("api_key",))
        out = _config_show(monkeypatch)
        assert PLANTED_KEY in out
