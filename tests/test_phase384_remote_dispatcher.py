"""Phase 384 (the operator's 2A) — the desktop runs only the fixed list.

`ops/desktop/motodiag_remote.py` is the forced command for the Mac's key.
Each operation maps to its commands, run here through a stand-in shell; each
request outside the list is refused having run nothing; the checkout is
held to the Mac's exact commit and a clean tree; the files the deploy modes
write go to the outbox, outside the checkout (3A); every request is logged.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "motodiag_remote", ROOT / "ops" / "desktop" / "motodiag_remote.py")
R = importlib.util.module_from_spec(spec)
sys.modules["motodiag_remote"] = R   # a dataclass looks its module up while it is built
spec.loader.exec_module(R)

COMMIT = "a" * 40


class FakeShell(R.Shell):
    def __init__(self, *, dirty: str = "", head: str = COMMIT, branch: str = "master",
                 on_run=None) -> None:
        self.calls: list[list[str]] = []
        self.dirty, self.head, self.branch, self.on_run = dirty, head, branch, on_run

    def run(self, argv, cwd=None):
        self.calls.append(list(argv))
        return self.on_run(argv) if self.on_run else 0

    def capture(self, argv, cwd=None):
        self.calls.append(list(argv))
        if "status" in argv and "--porcelain" in argv:
            return 0, self.dirty
        if argv[-2:] == ["rev-parse", "HEAD"]:
            return 0, self.head
        if "--show-current" in argv:
            return 0, self.branch
        if "ls-files" in argv:
            return 1, ""
        return 0, "x"

    def healthz(self):
        return '{"status":"ok"}'


@pytest.fixture
def paths(tmp_path):
    p = R.Paths.under(tmp_path)
    (p.dev / "docs" / "phases" / "in_progress").mkdir(parents=True)
    return p


def _main(cmd, paths, shell):
    return R.main(cmd, paths, shell)


@pytest.mark.parametrize("cmd", [
    None, "", "   ",                                 # an interactive login
    "bash", "sh -c id", "status; id", "status && id", "status | cat",
    "sftp", "internal-sftp", "/usr/lib/openssh/sftp-server", "scp -t /tmp",
    "dryrun 384", f"dryrun 384 {COMMIT} extra",       # wrong number of arguments
    f"dryrun ../x {COMMIT}", f"dryrun 384 {'A' * 40}", f"dryrun 384 {COMMIT[:12]}",
    f"dryrun '384;id' {COMMIT}", "backup '../../etc'", "backup Upper",
    "fetch 384 other", "fetch ../../x dryrun", "status '",
    "git status", "api-stop now",
])
def test_outside_the_list_is_refused_and_runs_nothing(cmd, paths, capsys):
    shell = FakeShell()
    assert _main(cmd, paths, shell) == R.REFUSED
    assert shell.calls == []
    assert "REFUSED" in capsys.readouterr().err
    assert "refused" in paths.log.read_text()


def test_the_list_is_exactly_these():
    assert set(R.OPS) == {"status", "dryrun", "apply-live", "verify-live", "live-check",
                          "media-check", "backup", "backups", "fetch", "api-stop",
                          "api-start", "api-restart", "server-pull"}


def _deploy_calls(shell, paths):
    return [c for c in shell.calls if c and c[0].endswith("python")]


@pytest.mark.parametrize("mode", ["dryrun", "apply-live", "verify-live"])
def test_a_deploy_mode_runs_at_the_commit(mode, paths):
    shell = FakeShell()
    assert _main(f"{mode} 384 {COMMIT}", paths, shell) == 0
    dev = str(paths.dev)
    assert ["git", "-C", dev, "checkout", "--quiet", "--detach", COMMIT] in shell.calls
    i_checkout = shell.calls.index(["git", "-C", dev, "checkout", "--quiet", "--detach", COMMIT])
    run = _deploy_calls(shell, paths)
    assert run == [[str(paths.dev / ".venv" / "bin" / "python"), "-B",
                    str(paths.dev / ".claude" / "skills" / "deploy" / "deploy.py"), mode, "384"]]
    assert shell.calls.index(run[0]) > i_checkout


def test_a_dirty_checkout_refuses_before_any_deploy(paths):
    shell = FakeShell(dirty="?? stray.txt")
    assert _main(f"dryrun 384 {COMMIT}", paths, shell) == R.REFUSED
    assert _deploy_calls(shell, paths) == []
    assert not any("checkout" in c for c in shell.calls)


def test_a_head_not_at_the_commit_refuses(paths):
    shell = FakeShell(head="b" * 40)
    assert _main(f"apply-live 384 {COMMIT}", paths, shell) == R.REFUSED
    assert _deploy_calls(shell, paths) == []


def test_the_deploy_modes_exit_comes_back(paths):
    shell = FakeShell(on_run=lambda argv: 3 if argv[0].endswith("python") else 0)
    assert _main(f"verify-live 383 {COMMIT}", paths, shell) == 3


def _writes(paths, phase, kind, text):
    def on_run(argv):
        if argv[0].endswith("python"):
            (paths.dev / "docs" / "phases" / "in_progress"
             / f"{phase}_{kind}_diff.md").write_text(text)
        return 0
    return on_run


@pytest.mark.parametrize("mode,kind", [("dryrun", "dryrun"), ("apply-live", "live")])
def test_the_written_diff_moves_to_the_outbox_and_fetch_returns_it(mode, kind, paths, capsys):
    shell = FakeShell(on_run=_writes(paths, "384", kind, "the diff\n"))
    assert _main(f"{mode} 384 {COMMIT}", paths, shell) == 0
    assert not (paths.dev / "docs" / "phases" / "in_progress" / f"384_{kind}_diff.md").exists()
    assert (paths.outbox / f"384_{kind}_diff.md").read_text() == "the diff\n"
    capsys.readouterr()
    assert _main(f"fetch 384 {kind}", paths, FakeShell()) == 0
    sent = json.loads(capsys.readouterr().out)
    assert sent == {"name": f"384_{kind}_diff.md", "text": "the diff\n",
                    "sha256": hashlib.sha256(b"the diff\n").hexdigest()}


def test_a_tracked_diff_is_restored_not_deleted(paths):
    class Tracked(FakeShell):
        def capture(self, argv, cwd=None):
            if "ls-files" in argv:
                self.calls.append(list(argv))
                return 0, argv[-1]
            return super().capture(argv, cwd)
    shell = Tracked(on_run=_writes(paths, "384", "dryrun", "new\n"))
    assert _main(f"dryrun 384 {COMMIT}", paths, shell) == 0
    rel = "docs/phases/in_progress/384_dryrun_diff.md"
    assert ["git", "-C", str(paths.dev), "checkout", "--quiet", "--", rel] in shell.calls
    assert (paths.outbox / "384_dryrun_diff.md").read_text() == "new\n"


def test_fetch_with_nothing_in_the_outbox_fails(paths):
    assert _main("fetch 384 dryrun", paths, FakeShell()) == 1


@pytest.mark.parametrize("op,verb", [("api-stop", "stop"), ("api-start", "start"),
                                     ("api-restart", "restart")])
def test_the_service_operations_use_the_one_sudo_rule(op, verb, paths):
    shell = FakeShell()
    assert _main(op, paths, shell) == 0
    assert ["sudo", "-n", "systemctl", verb, "motodiag-api.service"] in shell.calls
    assert not [c for c in shell.calls if c[0] == "sudo" and c[3] != verb]


def test_server_pull_only_on_master(paths):
    shell = FakeShell(branch="phase-384")
    assert _main("server-pull", paths, shell) == R.REFUSED
    assert not any("pull" in c for c in shell.calls)
    shell = FakeShell()
    assert _main("server-pull", paths, shell) == 0
    assert ["git", "-C", str(paths.server), "pull", "--ff-only", "--quiet"] in shell.calls


def test_backup_takes_a_label(paths):
    shell = FakeShell()
    assert _main("backup pre384proof", paths, shell) == 0
    assert _deploy_calls(shell, paths)[0][-2:] == ["backup", "pre384proof"]


def _live(paths, tmp_path):
    db = tmp_path / "live.db"
    c = sqlite3.connect(db)
    c.executescript("create table schema_version (version integer); "
                    "insert into schema_version values (87); "
                    "create table known_issues (id integer); insert into known_issues values (1);")
    c.close()
    paths.live_config.parent.mkdir(parents=True)
    paths.live_config.write_text(json.dumps({"live": str(db)}))


def test_live_check_reads_live_and_verifies_a_deploy(paths, tmp_path, capsys):
    _live(paths, tmp_path)
    shell = FakeShell(on_run=lambda argv: 3 if argv[0].endswith("python") else 0)
    assert _main(f"live-check 384 {COMMIT}", paths, shell) == 0     # no dry-run diff
    assert "| schema 87 | rows 1" in capsys.readouterr().out
    (paths.dev / "docs" / "phases" / "in_progress" / "384_dryrun_diff.md").write_text("x")
    assert _main(f"live-check 384 {COMMIT}", paths, shell) == 3     # verify-live's exit
    assert _deploy_calls(shell, paths)[-1][-2:] == ["verify-live", "384"]


def test_live_check_with_live_elsewhere_exits_4(paths):
    assert _main(f"live-check 384 {COMMIT}", paths, FakeShell()) == 4


def test_status_is_read_only(paths, tmp_path, capsys):
    _live(paths, tmp_path)
    shell = FakeShell()
    assert _main("status", paths, shell) == 0
    out = capsys.readouterr().out
    assert "schema 87" in out and "integrity ok" in out and "healthz" in out
    assert not [c for c in shell.calls if set(c) & {"checkout", "pull", "sudo", "fetch"}]


def test_every_request_is_logged_with_its_outcome(paths, monkeypatch):
    monkeypatch.setenv("SSH_CONNECTION", "100.80.109.103 50000 100.1.2.3 22")
    _main("backups", paths, FakeShell())
    _main("bash", paths, FakeShell())
    lines = paths.log.read_text().splitlines()
    assert len(lines) == 2
    assert "from 100.80.109.103 'backups' -> exit 0" in lines[0]
    assert "'bash' -> refused" in lines[1]
