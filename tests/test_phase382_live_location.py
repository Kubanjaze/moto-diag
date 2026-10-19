"""Phase 382: live moved to the home desktop; every tool asks where it is.

Each machine carries ~/.config/motodiag/live.json. On the Mac it is
{"live": null, "host": "desktop-76s9bqv"}, and every tool that read
data/motodiag.db by its path must refuse there before touching anything.
MOTODIAG_LIVE_CONFIG points the tools at a fixture file.
"""

import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import xml.dom.minidom

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEPLOY = ROOT / ".claude" / "skills" / "deploy"
TRANSMISSION = ROOT / ".claude" / "skills" / "source-transmission"
OPS = ROOT / "ops" / "desktop"
sys.path.insert(0, str(DEPLOY))
sys.path.insert(0, str(TRANSMISSION))

import live as L  # noqa: E402
import deploy as D  # noqa: E402


def _db(path: pathlib.Path) -> pathlib.Path:
    c = sqlite3.connect(path)
    c.execute("create table t (x)")
    c.execute("insert into t values (1)")
    c.commit()
    c.close()
    return path


@pytest.fixture
def mac(tmp_path, monkeypatch):
    cfg = tmp_path / "live.json"
    cfg.write_text(json.dumps({"live": None, "host": "desktop-76s9bqv"}))
    monkeypatch.setenv("MOTODIAG_LIVE_CONFIG", str(cfg))
    return cfg


@pytest.fixture
def desktop(tmp_path, monkeypatch):
    (tmp_path / "live").mkdir()
    db = _db(tmp_path / "live" / "motodiag.db")
    cfg = tmp_path / "live.json"
    cfg.write_text(json.dumps({"live": str(db)}))
    monkeypatch.setenv("MOTODIAG_LIVE_CONFIG", str(cfg))
    return db


class TestWhere:
    def test_the_desktop_file_names_live(self, desktop):
        assert L.where() == desktop

    def test_the_macs_file_refuses_and_names_the_host(self, mac):
        with pytest.raises(L.LiveElsewhere, match="desktop-76s9bqv"):
            L.where()

    def test_a_missing_file_refuses(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MOTODIAG_LIVE_CONFIG", str(tmp_path / "absent.json"))
        with pytest.raises(L.LiveElsewhere, match="missing"):
            L.where()

    def test_a_path_that_does_not_exist_refuses(self, tmp_path, monkeypatch):
        cfg = tmp_path / "live.json"
        cfg.write_text(json.dumps({"live": str(tmp_path / "gone.db")}))
        monkeypatch.setenv("MOTODIAG_LIVE_CONFIG", str(cfg))
        with pytest.raises(L.LiveElsewhere, match="does not exist"):
            L.where()

    def test_the_command_line_exits_4(self, mac):
        r = subprocess.run([sys.executable, "-B", str(DEPLOY / "live.py")],
                           capture_output=True, text=True)
        assert r.returncode == 4 and "desktop-76s9bqv" in r.stderr


class TestUnsynced:
    @pytest.mark.parametrize("folder", [
        "/mnt/c/Users/lilcu/backups", "/home/u/OneDrive/backups",
        "/Users/u/Library/Mobile Documents/com~apple~CloudDocs/b",
        "/Users/u/Library/CloudStorage/GoogleDrive-x/b", "/home/u/Dropbox/b",
    ])
    def test_a_synced_folder_is_refused(self, folder):
        with pytest.raises(L.LiveElsewhere):
            L.unsynced(pathlib.Path(folder))

    def test_the_backup_folder_passes(self):
        assert L.unsynced(D.BACKUPS) == D.BACKUPS


class TestDeployRefusesOnTheMac:
    @pytest.mark.parametrize("argv", [["dryrun", "ZZZ"], ["apply-live", "ZZZ"],
                                      ["verify-live", "381"], ["backup"]])
    def test_each_mode_exits_4_before_touching_anything(self, mac, tmp_path, argv):
        home = tmp_path / "home"
        home.mkdir()
        scratch = ROOT / "data" / "deploy_scratch"
        before = sorted(scratch.iterdir()) if scratch.exists() else []
        env = dict(os.environ, HOME=str(home))
        r = subprocess.run([sys.executable, "-B", str(DEPLOY / "deploy.py"), *argv],
                           capture_output=True, text=True, env=env, cwd=ROOT)
        assert r.returncode == 4, r.stdout + r.stderr
        assert "desktop-76s9bqv" in r.stderr
        assert not (home / "backups").exists()
        assert (sorted(scratch.iterdir()) if scratch.exists() else []) == before

    def test_live_is_no_longer_a_constant(self):
        assert not hasattr(D, "LIVE")


class TestBackup:
    def test_a_backup_lands_with_its_sha256_and_5_are_kept(self, desktop, tmp_path, capsys):
        backups = tmp_path / "backups"
        backups.mkdir()
        for i in range(5):
            (backups / f"motodiag_old{i}_x.db").write_bytes(b"x")
            os.utime(backups / f"motodiag_old{i}_x.db", (i, i))
        assert D.backup_live("probe", backups=backups) == 0
        out = capsys.readouterr().out
        made = [p for p in backups.glob("motodiag_probe_*.db")]
        assert len(made) == 1
        assert f"sha256: {D.sha256(made[0])}" in out
        assert len(list(backups.glob("motodiag_*.db"))) == 5
        assert not (backups / "motodiag_old0_x.db").exists()
        c = sqlite3.connect(made[0])
        assert c.execute("select x from t").fetchall() == [(1,)]
        c.close()

    def test_a_synced_backup_folder_is_refused(self, desktop, tmp_path):
        with pytest.raises(L.LiveElsewhere, match="OneDrive"):
            D.backup_live("probe", backups=tmp_path / "OneDrive" / "backups")
        assert not (tmp_path / "OneDrive").exists()


class TestSourceTransmission:
    def test_census_refuses_on_the_mac(self, mac):
        r = subprocess.run([sys.executable, "-B", str(TRANSMISSION / "census.py"), "--make", "Honda"],
                           capture_output=True, text=True)
        assert r.returncode == 4 and "desktop-76s9bqv" in r.stderr

    def test_census_reads_live_where_the_file_says(self, desktop):
        import census as C
        assert C.live_db() == desktop

    def test_acquire_refuses_on_the_mac(self, mac):
        import acquire
        with pytest.raises(L.LiveElsewhere):
            acquire.machine_names("Honda")

    def test_orchestrate_refuses_before_any_clone(self, mac, monkeypatch):
        import orchestrate
        monkeypatch.setattr(orchestrate, "make_run",
                            lambda *a: pytest.fail("make_run reached on the Mac"))
        assert orchestrate.main(["batch", "Honda"]) == 4


class TestNoToolReadsTheOldPath:
    PATTERN = re.compile(r"""["']data["']\s*/\s*["']motodiag\.db|data/motodiag\.db""")

    def _hits(self, root: pathlib.Path) -> list[str]:
        return [f"{p.relative_to(root)}:{i}" for p in sorted(root.rglob("*"))
                if p.suffix in (".py", ".sh") and "fixtures" not in p.parts
                for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
                if self.PATTERN.search(line) and not line.lstrip().startswith("#")]

    def test_no_skill_script_names_data_motodiag_db(self):
        assert self._hits(ROOT / ".claude" / "skills") == []

    def test_the_scan_finds_a_planted_one(self, tmp_path):
        (tmp_path / "x.py").write_text('LIVE = ROOT / "data" / "motodiag.db"\n')
        (tmp_path / "y.sh").write_text("sqlite3 'file:data/motodiag.db?mode=ro'\n")
        assert self._hits(tmp_path) == ["x.py:1", "y.sh:1"]

    def test_verify_phase_check_8_reads_live_py_and_fails_on_a_refusal(self):
        text = (ROOT / ".claude" / "skills" / "closeout" / "verify_phase.sh").read_text()
        check8 = text.split("=== 8.", 1)[1].split("=== 9.", 1)[0]
        assert "live.py" in check8
        assert re.search(r"else\s+echo \"  CHECK 8 FAILED: live is not on this machine.*\"\s+FAILED=1",
                         check8)


class TestTheTestsNeverReachLive:
    def test_an_explicit_db_path_naming_live_is_not_honoured(self, desktop, tmp_path):
        """Spawned: the conftest reads live.json at import."""
        probe = tmp_path / "test_probe.py"
        probe.write_text(
            "import os\n"
            "from motodiag.core.database import get_db_path\n"
            "def test_probe():\n"
            "    assert os.path.realpath(get_db_path()) != os.path.realpath(os.environ['PROBE_LIVE'])\n")
        env = dict(os.environ, MOTODIAG_DB_PATH=str(desktop), PROBE_LIVE=str(desktop),
                   PYTHONPATH=str(ROOT / "tests"))
        # The suite's conftest, loaded as a plugin, as it is imported for tests/.
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:xdist",
                            "-p", "no:cacheprovider", "-p", "conftest", str(probe)],
                           capture_output=True, text=True, env=env, cwd=tmp_path, timeout=300)
        assert r.returncode == 0, r.stdout[-2000:]


class TestTheServerFiles:
    def test_the_unit_serves_loopback_and_never_migrates(self):
        unit = (OPS / "motodiag-api.service").read_text()
        start = next(line for line in unit.splitlines() if line.startswith("ExecStart="))
        assert "--skip-migrations" in start
        assert "--host 127.0.0.1" in start and "0.0.0.0" not in unit
        assert "Restart=always" in unit and "User=lilcu" in unit
        assert "Environment=MOTODIAG_DB_PATH=/home/lilcu/motodiag/live/motodiag.db" in unit
        assert "WantedBy=multi-user.target" in unit
        # serve would create a fresh database where the Mac's copy must land.
        assert "ConditionPathExists=/home/lilcu/motodiag/live/motodiag.db" in unit

    def test_the_boot_task_runs_at_startup_without_a_sign_in(self):
        doc = xml.dom.minidom.parse(str(OPS / "motodiag-wsl-boot.xml"))
        assert doc.getElementsByTagName("BootTrigger")
        logon = doc.getElementsByTagName("LogonType")[0].firstChild.data
        assert logon in ("S4U", "Password"), logon
        assert doc.getElementsByTagName("Command")[0].firstChild.data.endswith("wsl.exe")
        assert "Ubuntu-26.04" in doc.getElementsByTagName("Arguments")[0].firstChild.data
        assert doc.getElementsByTagName("ExecutionTimeLimit")[0].firstChild.data == "PT0S"

    def test_sudo_without_a_password_covers_only_the_units_three_verbs(self):
        text = (OPS / "install_sudoers.sh").read_text()
        rule = text.split("<<'RULES'\n", 1)[1].split("\nRULES", 1)[0]
        user, rest = rule.split(" NOPASSWD: ")
        assert user == "lilcu ALL=(root)"
        assert [c.strip() for c in rest.split(",")] == [
            f"/usr/bin/systemctl {verb} motodiag-api.service"
            for verb in ("start", "stop", "restart")]
        assert "visudo -cf" in text

    def test_wsl_never_idles_the_distribution_out(self):
        text = (OPS / "wslconfig").read_text()
        assert "instanceIdleTimeout=-1" in text and "vmIdleTimeout=-1" in text
