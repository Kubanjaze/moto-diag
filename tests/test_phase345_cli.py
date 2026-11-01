"""Phase 345 — ``motodiag backup``, the desktop's timer, and the extra.

Each subcommand runs under ``CliRunner`` against ``S3Store`` over the fake
S3 transport (the seam: ``cli.backup.open_store``), with a key file of
planted values on a temp path. No output may carry a value from that file.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner
from support.phase345 import FAKE_VALUES, FakeS3, cheap_crypto, make_live, write_env

from motodiag.backup.settings import BUCKET, ENDPOINT, KEY_ID, PASSPHRASE, SECRET
from motodiag.backup.store import S3Store
from motodiag.cli import backup as cli_backup
from motodiag.cli.main import cli

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = ROOT / "ops" / "desktop"
VALUES = (FAKE_VALUES[KEY_ID], FAKE_VALUES[SECRET], FAKE_VALUES[PASSPHRASE])


@pytest.fixture
def env(tmp_path, monkeypatch):
    cheap_crypto(monkeypatch)
    path = write_env(tmp_path / "backup.env")
    monkeypatch.setenv("MOTODIAG_BACKUP_ENV", str(path))
    monkeypatch.setenv("MOTODIAG_BACKUP_WORK_DIR", str(tmp_path / "work"))
    fake = FakeS3()
    monkeypatch.setattr(cli_backup, "open_store", lambda s: S3Store(
        s.endpoint, s.bucket, s.key_id, s.secret, transport=fake))
    db, data = make_live(tmp_path)
    return {"fake": fake, "db": db, "data": data, "tmp": tmp_path, "path": path}


def run(*args):
    result = CliRunner().invoke(cli, list(args))
    for value in VALUES:
        assert value not in result.output, f"a value from backup.env in: {args}"
    return result


def _run_once(env, label="manual"):
    return run("backup", "run", "--label", label, "--db", str(env["db"]),
               "--data-dir", str(env["data"]))


def test_backup_help_lists_the_five_commands():
    result = run("backup", "--help")
    assert result.exit_code == 0
    assert set(cli.commands["backup"].commands) == {"run", "list", "restore", "verify", "status"}


def test_the_seam_is_the_real_client_by_default(tmp_path):
    from motodiag.backup.settings import BackupSettings
    store = cli_backup.open_store(BackupSettings(tmp_path, *FAKE_VALUES.values()))
    assert isinstance(store, S3Store) and store.region == "us-west-004"
    assert store.bucket == FAKE_VALUES[BUCKET]


class TestRun:
    def test_run_takes_a_snapshot_and_says_what_moved(self, env):
        result = _run_once(env, "nightly")
        assert result.exit_code == 0, result.output
        assert "3 uploaded, 0 already offsite" in result.output
        assert any(k.endswith("manifest.json.enc") for k in env["fake"].objects)
        again = _run_once(env)
        assert "0 uploaded, 3 already offsite" in again.output

    @pytest.mark.parametrize("name", [ENDPOINT, PASSPHRASE])
    def test_a_missing_name_exits_2_naming_it_and_touching_nothing(self, env, name):
        write_env(env["path"], {k: v for k, v in FAKE_VALUES.items() if k != name})
        result = _run_once(env)
        assert result.exit_code == 2 and name in result.output
        assert env["fake"].requests == [] and not (env["tmp"] / "work").exists()

    def test_a_group_readable_key_file_exits_2(self, env):
        env["path"].chmod(0o640)
        result = _run_once(env)
        assert result.exit_code == 2 and "must be 600" in result.output

    def test_a_synced_work_folder_exits_2(self, env, monkeypatch):
        monkeypatch.setenv("MOTODIAG_BACKUP_WORK_DIR", str(env["tmp"] / "OneDrive" / "w"))
        assert _run_once(env).exit_code == 2

    def test_a_failed_upload_exits_1_and_is_logged(self, env):
        env["fake"].fail = (403, "AccessDenied", "no")
        result = _run_once(env)
        assert result.exit_code == 1 and "403 AccessDenied" in result.output
        last = (env["tmp"] / "work" / "runs.log").read_text().splitlines()[-1]
        assert json.loads(last)["outcome"] == "failed"


class TestList:
    def test_an_empty_bucket(self, env):
        result = run("backup", "list")
        assert result.exit_code == 0 and "No snapshot has been taken yet" in result.output

    def test_list_and_json(self, env):
        _run_once(env)
        result = run("backup", "list")
        assert result.exit_code == 0 and "database" in result.output
        rows = json.loads(run("backup", "list", "--json").output)
        assert len(rows) == 1 and rows[0]["db_size"] > 0

    def test_a_store_error_exits_1(self, env):
        env["fake"].fail = (500, "InternalError", "down")
        assert run("backup", "list").exit_code == 1


class TestRestoreAndVerify:
    def test_restore_latest_into_an_empty_folder(self, env):
        _run_once(env)
        to = env["tmp"] / "restore_check"
        result = run("backup", "restore", "--at", "latest", "--to", str(to),
                     "--db", str(env["db"]), "--data-dir", str(env["data"]))
        assert result.exit_code == 0, result.output
        assert f"MOTODIAG_DB_PATH={to}/motodiag.db" in result.output
        assert f"MOTODIAG_DATA_DIR={to}" in result.output
        assert (to / "videos" / "shop_1" / "session_1" / "1.mp4").is_file()

    def test_restore_over_live_exits_1(self, env):
        _run_once(env)
        result = run("backup", "restore", "--at", "latest", "--to", str(env["data"] / "x"),
                     "--db", str(env["db"]), "--data-dir", str(env["data"]))
        assert result.exit_code == 1 and "never writes over live" in result.output

    def test_restore_before_the_first_snapshot_exits_1(self, env):
        _run_once(env)
        result = run("backup", "restore", "--at", "2000-01-01T00:00:00Z", "--to",
                     str(env["tmp"] / "r"), "--db", str(env["db"]),
                     "--data-dir", str(env["data"]))
        assert result.exit_code == 1 and "the oldest is" in result.output

    def test_a_time_that_is_not_a_time_exits_1(self, env):
        result = run("backup", "verify", "--at", "last tuesday")
        assert result.exit_code == 1

    def test_verify(self, env):
        _run_once(env)
        result = run("backup", "verify", "--at", "latest")
        assert result.exit_code == 0 and "Verified" in result.output

    def test_verify_a_tampered_snapshot_exits_1(self, env):
        _run_once(env)
        key = next(k for k in env["fake"].objects if k.endswith("motodiag.db.enc"))
        raw = bytearray(env["fake"].objects[key])
        raw[50] ^= 1
        env["fake"].objects[key] = bytes(raw)
        assert run("backup", "verify").exit_code == 1


class TestStatus:
    def test_no_run_logged_exits_1(self, env):
        result = run("backup", "status")
        assert result.exit_code == 1 and "no backup run is logged" in result.output
        assert "MOTODIAG_BACKUP_S3_SECRET" in result.output  # names only

    def test_after_a_good_run_exits_0(self, env):
        _run_once(env, "nightly")
        result = run("backup", "status")
        assert result.exit_code == 0 and "nightly, ok" in result.output
        assert "media uploaded 3" in result.output

    def test_after_a_failed_run_exits_1(self, env):
        _run_once(env)
        env["fake"].fail = (403, "AccessDenied", "no")
        _run_once(env)
        result = run("backup", "status")
        assert result.exit_code == 1 and "the last run failed" in result.output

    def test_a_synced_work_folder_exits_1(self, env, monkeypatch):
        monkeypatch.setenv("MOTODIAG_BACKUP_WORK_DIR", str(env["tmp"] / "Dropbox"))
        assert run("backup", "status").exit_code == 1


def _unit(path: Path) -> dict[str, list[tuple[str, str]]]:
    sections: dict[str, list[tuple[str, str]]] = {}
    current = ""
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            current = line.strip("[]")
            sections[current] = []
        else:
            key, value = line.split("=", 1)
            sections[current].append((key, value))
    return sections


class TestTheDesktop:
    def test_the_service(self):
        unit = _unit(DESKTOP / "motodiag-backup.service")
        assert ("ConditionPathExists", "/home/lilcu/.config/motodiag/backup.env") in unit["Unit"]
        svc = unit["Service"]
        assert ("Type", "oneshot") in svc and ("User", "lilcu") in svc
        api = _unit(DESKTOP / "motodiag-api.service")["Service"]
        assert [kv for kv in svc if kv[0] == "Environment"] == [
            kv for kv in api if kv[0] == "Environment"]
        assert ("ExecStart", "/home/lilcu/motodiag/server/.venv/bin/motodiag backup run "
                             "--label nightly") in svc
        assert not [k for k, _ in svc if k == "EnvironmentFile"]

    def test_the_timer(self):
        timer = _unit(DESKTOP / "motodiag-backup.timer")["Timer"]
        assert ("OnCalendar", "*-*-* 03:00:00") in timer
        assert ("Persistent", "true") in timer

    def test_the_installer_names_both_units(self):
        text = (DESKTOP / "install_backup_unit.sh").read_text()
        assert "motodiag-backup.service" in text and "motodiag-backup.timer" in text
        assert "systemctl enable --now motodiag-backup.timer" in text
        assert "systemctl list-timers motodiag-backup.timer" in text

    def test_the_server_extra_installs_the_backup_extra(self):
        extras = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
            "optional-dependencies"]
        assert extras["backup"] == ["cryptography>=42.0"]
        assert "backup" in extras["server"][0].split("[", 1)[1].rstrip("]").split(",")

    def test_the_guide_is_on_the_docs_drift_list(self):
        import test_phase208_docs as docs
        assert ROOT / "docs" / "guide" / "backups.md" in docs.BACKEND_DOCS
