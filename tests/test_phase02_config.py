"""Phase 02 — configuration system tests."""

import pytest
from motodiag.core.config import Settings, Environment, ensure_directories, reset_settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.app_name == "motodiag"
        assert s.env == Environment.DEV
        assert s.ai_temperature == 0.3
        assert s.log_level == "INFO"

    def test_environment_enum(self):
        assert Environment.DEV.value == "dev"
        assert Environment.PROD.value == "prod"
        assert Environment.TEST.value == "test"

    def test_max_tokens_validation(self):
        with pytest.raises(Exception):
            Settings(max_tokens=50)
        with pytest.raises(Exception):
            Settings(max_tokens=10000)

    def test_temperature_validation(self):
        with pytest.raises(Exception):
            Settings(ai_temperature=1.5)
        with pytest.raises(Exception):
            Settings(ai_temperature=-0.1)

    def test_baud_rate_validation(self):
        with pytest.raises(Exception):
            Settings(baud_rate=12345)
        Settings(baud_rate=115200)  # valid

    def test_get_data_path(self):
        s = Settings()
        p = s.get_data_path("vehicles", "honda.json")
        assert str(p).endswith("vehicles/honda.json") or str(p).endswith("vehicles\\honda.json")

    def test_get_output_path(self):
        s = Settings()
        p = s.get_output_path("report.pdf")
        assert str(p).endswith("report.pdf")


class TestEnsureDirectories:
    def test_directories_created(self, tmp_path):
        s = Settings(data_dir=str(tmp_path / "data"), output_dir=str(tmp_path / "output"))
        results = ensure_directories(s)
        assert results["data"] is True
        assert (tmp_path / "data" / "dtc_codes").exists()
        assert (tmp_path / "data" / "vehicles").exists()
        assert (tmp_path / "data" / "knowledge").exists()
        assert (tmp_path / "output").exists()

    def test_idempotent(self, tmp_path):
        s = Settings(data_dir=str(tmp_path / "data"), output_dir=str(tmp_path / "output"))
        ensure_directories(s)
        results = ensure_directories(s)
        assert results["data"] is False  # already existed


class TestResetSettings:
    def test_reset_clears_cache(self):
        s1 = reset_settings()
        s2 = reset_settings()
        assert s1.app_name == s2.app_name


class TestConfigCLI:
    def test_config_show(self):
        from click.testing import CliRunner
        from motodiag.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0

    def test_config_paths(self):
        from click.testing import CliRunner
        from motodiag.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "paths"])
        assert result.exit_code == 0

    def test_config_init(self):
        from click.testing import CliRunner
        from motodiag.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "init"])
        assert result.exit_code == 0
