"""Phase 406 (K93) — the Mac runs the rest of the desktop's steps.

The ten operations Phase 406 adds to `ops/desktop/motodiag_remote.py`'s fixed
list, each run here through a stand-in desktop: its units, its checkouts,
GitHub's master, the fleet's log and its search on start. Each refusal is
planted, and a refusal changes nothing: no move, no restart, no reset. Each
failure after a change puts the old code back. Nothing reaches a desktop.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "motodiag_remote_406", ROOT / "ops" / "desktop" / "motodiag_remote.py")
R = importlib.util.module_from_spec(spec)
sys.modules["motodiag_remote_406"] = R   # a dataclass looks its module up while it is built
spec.loader.exec_module(R)

OLD, NEW = "a" * 40, "b" * 40
SHA = "c" * 64
BRANCH = "phase-334-terms-of-service-liability-framework"


class Desktop(R.Shell):
    """A stand-in desktop. Every command is recorded; the state it answers
    from is plain attributes a test sets before the call."""

    def __init__(self, paths: R.Paths) -> None:
        self.p = paths
        self.calls: list[list[str]] = []
        self.envs: list[dict | None] = []
        self.units = {R.UNIT: "active", R.FEED: "active", R.FLEET: "active"}
        self.pid = 100
        self.heads = {str(paths.server): OLD, str(paths.fleet_code): OLD}
        self.branch, self.dirty, self.master, self.ancestor = "master", "", NEW, True
        self.healthy_from = 1          # the healthz call that first says ok; 0: never
        self.health_calls = 0
        self.bwrap = False
        self.recover = (0, "nothing to resume")
        self.status_codes = [0]
        self.fail: set[str] = set()    # "fetch", "merge", "restart <unit>"
        self.feed_comes_back = True
        self.feed_new_pid = True        # False: running, but on the process it had
        self.fleet_logs_start = True

    def run(self, argv, cwd=None, env=None):
        argv = list(argv)
        self.calls.append(argv)
        self.envs.append(env)
        if argv[:3] == ["sudo", "-n", "systemctl"]:
            verb, unit = argv[3], argv[4]
            if f"{verb} {unit}" in self.fail:
                return 1
            if verb == "stop":
                self.units[unit] = "inactive"
            elif unit == R.FEED and verb == "restart":
                self.pid += 1 if self.feed_comes_back and self.feed_new_pid else 0
                self.units[unit] = "active" if self.feed_comes_back else "failed"
            else:
                self.units[unit] = "active"
            if unit == R.FLEET and self.fleet_logs_start:
                log = self.p.fleet_state / "dispatcher.log"
                log.parent.mkdir(parents=True, exist_ok=True)
                with log.open("ab") as f:
                    f.write(b"2026-11-19T18:00:00-05:00 the search on start: nothing to resume\n")
            return 0
        if argv[:1] == ["git"]:
            repo, sub = argv[2], argv[3]
            if sub == "fetch":
                return 1 if "fetch" in self.fail else 0
            if sub == "merge":
                if "merge" in self.fail:
                    return 1
                self.heads[repo] = argv[-1]
                return 0
            if sub == "reset":
                self.heads[repo] = argv[-1]
                return 0
            return 0
        if argv[0].endswith("motodiag"):
            return self.status_codes.pop(0) if self.status_codes else 1
        return 0

    def capture(self, argv, cwd=None, env=None):
        argv = list(argv)
        self.calls.append(argv)
        if argv[:2] == ["systemctl", "is-active"]:
            state = self.units.get(argv[2], "inactive")
            return (0 if state == "active" else 3), state
        if argv[:2] == ["systemctl", "show"]:
            return 0, str(self.pid)
        if argv[:2] == ["pgrep", "-x"]:
            return (0 if self.bwrap else 1), ""
        if argv[:1] == ["/usr/bin/python3"] and argv[-2:] == ["recover", "--dry-run"]:
            return self.recover
        if argv[:1] == ["git"]:
            repo, rest = argv[2], argv[3:]
            if rest == ["branch", "--show-current"]:
                return 0, self.branch
            if rest[:2] == ["status", "--porcelain"]:
                return 0, self.dirty
            if rest == ["rev-parse", "HEAD"]:
                return 0, self.heads[repo]
            if rest == ["rev-parse", "refs/remotes/origin/master"]:
                return 0, self.master
            if rest[:2] == ["merge-base", "--is-ancestor"]:
                return (0 if self.ancestor else 1), ""
            if rest[:2] == ["log", "-1"]:
                return 0, f"{self.heads[repo][:7]} the subject"
        return 0, ""

    def healthz(self):
        self.health_calls += 1
        ok = self.healthy_from and self.health_calls >= self.healthy_from
        return '{"status":"ok"}' if ok else "no answer (refused)"

    def sleep(self, seconds):
        self.calls.append(["sleep", str(seconds)])

    # what a test reads back
    def did(self, *prefix: str) -> list[list[str]]:
        return [c for c in self.calls if c[:len(prefix)] == list(prefix)]

    def changed(self) -> bool:
        return bool(self.did("sudo") or [c for c in self.calls if c[:1] == ["git"]
                                         and c[3] in ("merge", "reset")])


@pytest.fixture
def desk(tmp_path):
    p = R.Paths.under(tmp_path)
    live = tmp_path / "motodiag" / "live" / "motodiag.db"
    live.parent.mkdir(parents=True)
    live.write_bytes(b"")
    p.live_config.parent.mkdir(parents=True, exist_ok=True)
    p.live_config.write_text(json.dumps({"live": str(live)}))
    p.server_env.write_text("# the server's settings\n\nMOTODIAG_ENV=\"prod\"\n"
                            "; a comment\nSTRIPE_POLL_CHECKIN_S='300'\nNOT A SETTING\n")
    return Desktop(p)


def call(desk: Desktop, command: str) -> int:
    return R.main(command, desk.p, desk)


# ---------------------------------------------------------------- the list
@pytest.mark.parametrize("command", [
    "fleet-log 72 abc",                            # a count that is not one
    "fleet-log 72; 5",                             # a word with a semicolon
    f"deploy-apply 334 main {NEW} {SHA}",          # a branch that is not a phase's
    f"deploy-apply 334 {BRANCH} {NEW} cafe",       # a sha256 that is not one
    "server-update HEAD",                          # a commit that is not 40 hex
    f"deploy-dryrun 334 {BRANCH}",                 # an argument missing
    "feed-status now",                             # an argument too many
    "feed-reload",                                 # not an operation
])
def test_a_request_off_the_list_runs_nothing(desk, command):
    assert call(desk, command) == R.REFUSED
    assert desk.calls == []


def test_every_request_is_logged(desk):
    call(desk, "feed-stop")
    call(desk, "feed-reload")
    lines = desk.p.log.read_text().splitlines()
    assert "'feed-stop' -> exit 0" in lines[0] and "'feed-reload' -> refused" in lines[1]


# ---------------------------------------------------------------- the feed
@pytest.mark.parametrize("verb", ["stop", "start", "restart"])
def test_the_feed_verbs_touch_the_feed_unit_only(desk, verb):
    assert call(desk, f"feed-{verb}") == 0
    assert desk.did("sudo") == [["sudo", "-n", "systemctl", verb, R.FEED]]


def test_a_feed_verb_sudo_refuses_comes_back_as_its_exit(desk):
    desk.fail.add(f"stop {R.FEED}")
    assert call(desk, "feed-stop") == 1


def test_feed_status_runs_the_cli_with_the_server_settings(desk, monkeypatch):
    monkeypatch.setenv("MOTODIAG_PLANTED", "from the caller")
    assert call(desk, "feed-status") == 0
    (argv,) = [c for c in desk.calls if c[0].endswith("motodiag")]
    assert argv == [str(desk.p.server / ".venv" / "bin" / "motodiag"), "payments", "feed",
                    "status"]
    env = desk.envs[desk.calls.index(argv)]
    live = json.loads(desk.p.live_config.read_text())["live"]
    assert env["MOTODIAG_DB_PATH"] == live
    assert env["MOTODIAG_DATA_DIR"] == str(pathlib.Path(live).parent)
    assert env["MOTODIAG_ENV"] == "prod" and env["STRIPE_POLL_CHECKIN_S"] == "300"
    assert "MOTODIAG_PLANTED" not in env and "NOT A SETTING" not in env


def test_feed_status_passes_the_clis_exit_through(desk):
    desk.status_codes = [1]
    assert call(desk, "feed-status") == 1


def test_feed_status_refused_when_live_is_elsewhere(desk):
    desk.p.live_config.unlink()
    assert call(desk, "feed-status") == R.REFUSED
    assert desk.calls == []


# ---------------------------------------------------------------- server-update
def test_server_update_moves_restarts_and_reads_the_status(desk):
    assert call(desk, f"server-update {NEW}") == 0
    srv = str(desk.p.server)
    assert desk.did("git", "-C", srv, "merge", "--quiet", "--ff-only") == [
        ["git", "-C", srv, "merge", "--quiet", "--ff-only", NEW]]
    assert desk.did("sudo") == [["sudo", "-n", "systemctl", "restart", R.UNIT],
                                ["sudo", "-n", "systemctl", "restart", R.FEED]]
    assert not desk.did("git", "-C", srv, "reset")
    assert desk.heads[srv] == NEW


def test_server_update_already_there_restarts_without_moving(desk):
    desk.heads[str(desk.p.server)] = NEW
    assert call(desk, f"server-update {NEW}") == 0
    assert not [c for c in desk.calls if c[:1] == ["git"] and c[3] == "merge"]
    assert len(desk.did("sudo")) == 2


@pytest.mark.parametrize("plant,why", [
    (lambda d: d.units.__setitem__(R.UNIT, "inactive"), "app server is not running"),
    (lambda d: d.units.__setitem__(R.FEED, "inactive"), "payments feed is not running"),
    (lambda d: setattr(d, "branch", "phase-404-x"), "not master"),
    (lambda d: setattr(d, "dirty", " M src/x.py"), "changes made by hand"),
    (lambda d: setattr(d, "master", "d" * 40), "not at bbbbbbbbbbbb"),
    (lambda d: d.fail.add("fetch"), "could not fetch"),
    (lambda d: setattr(d, "ancestor", False), "commits that are not on master"),
    (lambda d: d.fail.add("merge"), "could not be moved"),
])
def test_server_update_refusals_change_nothing(desk, capsys, plant, why):
    plant(desk)
    assert call(desk, f"server-update {NEW}") == R.REFUSED
    assert why in capsys.readouterr().err
    assert not desk.did("sudo") and not desk.did("git", "-C", str(desk.p.server), "reset")


def test_server_update_puts_the_code_back_when_the_server_is_not_healthy(desk, capsys):
    desk.healthy_from = 0
    assert call(desk, f"server-update {NEW}") == 1
    srv = str(desk.p.server)
    assert desk.did("git", "-C", srv, "reset") == [["git", "-C", srv, "reset", "--quiet",
                                                    "--keep", OLD]]
    assert desk.heads[srv] == OLD
    assert "did not answer healthy" in capsys.readouterr().out


def test_server_update_puts_the_code_back_when_the_feed_does_not_come_back(desk, capsys):
    desk.feed_comes_back = False
    assert call(desk, f"server-update {NEW}") == 1
    assert desk.heads[str(desk.p.server)] == OLD
    out = capsys.readouterr().out
    assert "payments feed did not come back" in out and "even on the old code" in out


def test_server_update_puts_the_code_back_when_the_feed_kept_its_old_process(desk, capsys):
    desk.feed_new_pid = False
    assert call(desk, f"server-update {NEW}") == 1
    assert desk.heads[str(desk.p.server)] == OLD
    assert "payments feed did not come back" in capsys.readouterr().out


def test_server_update_a_status_not_right_keeps_the_new_code(desk, capsys):
    desk.status_codes = [1] * 6
    assert call(desk, f"server-update {NEW}") == 1
    assert desk.heads[str(desk.p.server)] == NEW
    assert not desk.did("git", "-C", str(desk.p.server), "reset")
    assert "says something is not right" in capsys.readouterr().out


def test_server_update_waits_for_the_status_to_come_right(desk):
    desk.status_codes = [1, 1, 0]
    assert call(desk, f"server-update {NEW}") == 0


# ---------------------------------------------------------------- the fleet
def test_fleet_status_reads_only(desk, capsys):
    desk.recover = (0, "1 stage(s) to act on")
    assert call(desk, "fleet-status") == 0
    assert not desk.changed()
    out = capsys.readouterr().out
    assert f"{R.FLEET}: active" in out and "no stage is running" in out
    assert "1 stage(s) to act on" in out


def test_fleet_log_reads_past_zero_bytes(desk, capsys):
    log = desk.p.fleet_state / "dispatcher.log"
    log.parent.mkdir(parents=True)
    log.write_bytes(b"2026-11-18T22:14:20-05:00 issue 72: first\n"
                    + b"\x00" * 200
                    + b"2026-11-18T22:14:27-05:00 issue 72: verify-live 334: exit 0\n"
                    + b"2026-11-18T22:15:00-05:00 issue 7: another issue\n"
                    + b"2026-11-18T22:16:00-05:00 issue 72: third\n")
    assert call(desk, "fleet-log 72 2") == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["2026-11-18T22:14:27-05:00 issue 72: verify-live 334: exit 0",
                   "2026-11-18T22:16:00-05:00 issue 72: third",
                   "(3 line(s) name issue 72; 2 shown)"]
    assert not desk.changed()


def test_fleet_log_with_no_log_says_so(desk):
    assert call(desk, "fleet-log 72 5") == 1


def test_fleet_move_moves_restarts_and_sees_the_start(desk, capsys):
    assert call(desk, f"fleet-move {NEW}") == 0
    code = str(desk.p.fleet_code)
    assert desk.heads[code] == NEW
    assert desk.did("sudo") == [["sudo", "-n", "systemctl", "restart", R.FLEET]]
    assert "the fleet restarted and is on" in capsys.readouterr().out


@pytest.mark.parametrize("plant,why", [
    (lambda d: setattr(d, "bwrap", True), "a stage of the fleet is running"),
    (lambda d: setattr(d, "recover", (0, "1 stage(s) to act on")), "would act on something"),
    (lambda d: setattr(d, "recover", (1, "")), "would act on something"),
    (lambda d: setattr(d, "branch", ""), "(detached)"),
    (lambda d: setattr(d, "dirty", " M x"), "changes made by hand"),
    (lambda d: setattr(d, "master", "d" * 40), "not at bbbbbbbbbbbb"),
    (lambda d: setattr(d, "ancestor", False), "commits that are not on master"),
])
def test_fleet_move_refusals_change_nothing(desk, capsys, plant, why):
    plant(desk)
    assert call(desk, f"fleet-move {NEW}") == R.REFUSED
    assert why in capsys.readouterr().err
    assert not desk.changed()


def test_fleet_move_puts_the_code_back_when_the_fleet_does_not_start(desk, capsys):
    desk.fleet_logs_start = False
    assert call(desk, f"fleet-move {NEW}") == 1
    code = str(desk.p.fleet_code)
    assert desk.heads[code] == OLD
    assert len(desk.did("sudo")) == 2
    assert "not running even on the old code" in capsys.readouterr().out


def test_fleet_move_a_restart_sudo_refuses_puts_the_code_back(desk):
    desk.fail.add(f"restart {R.FLEET}")
    assert call(desk, f"fleet-move {NEW}") == 1
    assert desk.heads[str(desk.p.fleet_code)] == OLD


# ---------------------------------------------------------------- the database step
def test_deploy_dryrun_runs_the_fleets_step_alone(desk):
    assert call(desk, f"deploy-dryrun 334 {BRANCH} {NEW}") == 0
    (argv,) = [c for c in desk.calls if c[0].endswith("python")]
    assert argv == [str(desk.p.fleet_state / "venv" / "bin" / "python"),
                    str(desk.p.fleet_code / ".claude" / "skills" / "deploy" / "through_fleet.py"),
                    "334", BRANCH, NEW, "--dry-run-only"]


def test_deploy_apply_names_the_sha256_the_mac_showed(desk):
    assert call(desk, f"deploy-apply 334 {BRANCH} {NEW} {SHA}") == 0
    (argv,) = [c for c in desk.calls if c[0].endswith("python")]
    assert argv[-5:] == ["334", BRANCH, NEW, "--apply", SHA]
    assert not desk.did("sudo")
