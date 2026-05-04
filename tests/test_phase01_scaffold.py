"""Phase 01 — verify project scaffold is correctly set up."""

import pytest

from motodiag.engine.client import MODEL_ALIASES


class TestPackageImports:
    """All subpackages should be importable."""

    @pytest.mark.parametrize("module", [
        "motodiag",
        "motodiag.core",
        "motodiag.core.config",
        "motodiag.core.models",
        "motodiag.vehicles",
        "motodiag.knowledge",
        "motodiag.engine",
        "motodiag.cli",
        "motodiag.cli.main",
        "motodiag.hardware",
        "motodiag.advanced",
        "motodiag.api",
    ])
    def test_import(self, module):
        __import__(module)


class TestVersion:
    def test_version_exists(self):
        from motodiag import __version__
        assert __version__ == "0.1.0"

    def test_app_name(self):
        from motodiag import __app_name__
        assert __app_name__ == "motodiag"


class TestConfig:
    def test_settings_defaults(self):
        from motodiag.core.config import Settings
        s = Settings()
        assert s.app_name == "motodiag"
        assert s.version == "0.1.0"
        assert s.debug is False
        assert s.ai_model == MODEL_ALIASES["haiku"]

    def test_project_root(self):
        from motodiag.core.config import PROJECT_ROOT
        assert PROJECT_ROOT.exists()
        assert (PROJECT_ROOT / "pyproject.toml").exists()


class TestModels:
    def test_vehicle_base(self, sample_vehicle):
        assert sample_vehicle.make == "Harley-Davidson"
        assert sample_vehicle.year == 2001
        assert sample_vehicle.engine_cc == 1200

    def test_dtc_code(self, sample_dtc):
        assert sample_dtc.code == "P0115"
        assert len(sample_dtc.common_causes) == 3

    def test_diagnostic_session(self):
        from motodiag.core.models import DiagnosticSessionBase
        session = DiagnosticSessionBase(
            vehicle_make="Honda",
            vehicle_model="CBR929RR",
            vehicle_year=2001,
            symptoms=["won't start when cold"],
        )
        assert session.status.value == "open"
        assert len(session.symptoms) == 1

    def test_severity_enum(self):
        from motodiag.core.models import Severity
        assert Severity.CRITICAL.value == "critical"
        assert Severity.LOW.value == "low"

    def test_protocol_enum(self):
        from motodiag.core.models import ProtocolType
        assert ProtocolType.CAN.value == "can"
        assert ProtocolType.K_LINE.value == "k_line"
        assert ProtocolType.J1850.value == "j1850"


class TestCLI:
    def test_cli_help(self):
        from click.testing import CliRunner
        from motodiag.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "MotoDiag" in result.output

    def test_cli_version(self):
        from click.testing import CliRunner
        from motodiag.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_info(self):
        from click.testing import CliRunner
        from motodiag.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0
