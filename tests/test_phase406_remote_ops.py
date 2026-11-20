"""Phase 406 (K93) — the Mac runs the rest of the desktop's steps.

The ten operations Phase 406 adds to `ops/desktop/motodiag_remote.py`'s fixed
list, each run here through a stand-in desktop: its units, its checkouts,
GitHub's master, live's check-in rows, the fleet's log and its search on
start. Each refusal is planted, and a refusal changes nothing: no move, no
restart, no reset. Each failure after a change puts the old code back, and a
put-back that does not take is said, never claimed. A step runs to its end
when the Mac goes away mid-step, and two changing steps never run at once.
Nothing reaches a desktop.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import pathlib
import signal
import sqlite3
import subprocess
import sys
import time

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


class Gone(io.StringIO):
    """The Mac's channel after the Mac went away: every write fails."""

    def write(self, s):
        raise BrokenPipeError(32, "Broken pipe")

    def flush(self):
        raise BrokenPipeError(32, "Broken pipe")


class Desktop(R.Shell):
    """A stand-in desktop. Every command is recorded; the state it answers
    from is plain attributes a test sets before the call."""

    def __init__(self, paths: R.Paths, live: pathlib.Path) -> None:
        self.p, self.live = paths, live
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
        self.fail: set[str] = set()    # "fetch", "merge", "reset", "restart <unit>"
        self.feed_comes_back = True
        self.feed_new_pid = True        # False: running, but on the process it had
        self.feed_checks_in = True      # False: running, but no check-in row
        self.feed_dies = False          # True: gone a few seconds after its check-in
        self.feed_respawns = False      # True: crashed and restarted by systemd, a new PID
        self.unreadable_after = False   # True: live's check-ins and server.env gone at the
                                        # feed's restart, after the change
        self.fleet_logs_start = True
        self.fleet_stays_up = True      # False: starts, logs it, then is not active

    def _check_in(self) -> None:
        c = sqlite3.connect(self.live)
        c.execute("INSERT INTO stripe_feed_checkins (sent_at, ok, answer, slug) "
                  "VALUES ('2026-11-19T21:00:00Z', 1, '202 Accepted', 'motodiag-payments-feed')")
        c.commit()
        c.close()

    def run(self, argv, cwd=None, env=None):
        argv = list(argv)
        self.calls.append(argv)
        self.envs.append(env)
        if argv[0].endswith("motodiag"):
            return self.status_codes.pop(0) if self.status_codes else 1
        if argv[:3] == ["sudo", "-n", "systemctl"]:
            verb, unit = argv[3], argv[4]
            if f"{verb} {unit}" in self.fail:
                return 1
            if verb == "stop":
                self.units[unit] = "inactive"
            elif unit == R.FEED and verb == "restart":
                self.pid += 1 if self.feed_comes_back and self.feed_new_pid else 0
                self.units[unit] = "active" if self.feed_comes_back else "failed"
                if self.unreadable_after:
                    sqlite3.connect(self.live).execute("DROP TABLE stripe_feed_checkins")
                    self.p.server_env.unlink()
                elif self.feed_comes_back and self.feed_checks_in:
                    self._check_in()
            else:
                self.units[unit] = "active"
            if unit == R.FLEET and self.fleet_logs_start:
                log = self.p.fleet_state / "dispatcher.log"
                log.parent.mkdir(parents=True, exist_ok=True)
                with log.open("ab") as f:
                    f.write(b"2026-11-19T18:00:00-05:00 the search on start: nothing to resume\n")
                if not self.fleet_stays_up:
                    self.units[R.FLEET] = "failed"
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
                if "reset" in self.fail:
                    return 128
                if "reset-silent" in self.fail:      # exits 0, and HEAD did not move
                    return 0
                self.heads[repo] = argv[-1]
                return 0
            return 0
        return 0

    def capture(self, argv, cwd=None, env=None):
        argv = list(argv)
        self.calls.append(argv)
        self.envs.append(env)
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
        self.envs.append(None)
        if self.feed_dies and seconds == 3:
            self.units[R.FEED] = "failed"
        if self.feed_respawns and seconds == 3:
            self.pid += 1

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
    c = sqlite3.connect(live)
    c.execute("CREATE TABLE stripe_feed_checkins (id INTEGER PRIMARY KEY AUTOINCREMENT, "
              "sent_at TEXT NOT NULL, ok INTEGER NOT NULL, answer TEXT NOT NULL, "
              "slug TEXT NOT NULL)")
    c.commit()
    c.close()
    p.live_config.parent.mkdir(parents=True, exist_ok=True)
    p.live_config.write_text(json.dumps({"live": str(live)}))
    p.server_env.write_text("# the server's settings\n\nMOTODIAG_ENV=\"prod\"\n"
                            "; a comment\nSTRIPE_POLL_CHECKIN_S='300'\nNOT A SETTING\n")
    return Desktop(p, live)


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


def test_two_changing_steps_never_run_at_once(desk, capsys):
    held = R.one_at_a_time(desk.p)
    try:
        assert call(desk, f"server-update {NEW}") == R.REFUSED
        assert call(desk, "feed-stop") == R.REFUSED
        assert "another step is running" in capsys.readouterr().err
        assert not desk.changed()
        assert call(desk, "fleet-status") == 0, "a step that only reads takes no lock"
    finally:
        held.close()
    assert call(desk, "feed-stop") == 0, "the lock goes with the step that held it"


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
    assert env["MOTODIAG_DB_PATH"] == str(desk.live)
    assert env["MOTODIAG_DATA_DIR"] == str(desk.live.parent)
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
def test_server_update_moves_restarts_waits_for_a_check_in_and_reads_the_status(desk):
    assert call(desk, f"server-update {NEW}") == 0
    srv = str(desk.p.server)
    assert desk.did("git", "-C", srv, "merge", "--quiet", "--ff-only") == [
        ["git", "-C", srv, "merge", "--quiet", "--ff-only", NEW]]
    assert desk.did("sudo") == [["sudo", "-n", "systemctl", "restart", R.UNIT],
                                ["sudo", "-n", "systemctl", "restart", R.FEED]]
    assert not desk.did("git", "-C", srv, "reset")
    assert desk.heads[srv] == NEW
    assert len([c for c in desk.calls if c[0].endswith("motodiag")]) == 1


def test_server_update_already_there_restarts_without_moving(desk):
    desk.heads[str(desk.p.server)] = NEW
    assert call(desk, f"server-update {NEW}") == 0
    assert not [c for c in desk.calls if c[:1] == ["git"] and c[3] == "merge"]
    assert len(desk.did("sudo")) == 2


@pytest.mark.parametrize("plant,why", [
    (lambda d: d.units.__setitem__(R.UNIT, "inactive"), "app server is not running"),
    (lambda d: d.units.__setitem__(R.FEED, "inactive"), "payments feed is not running"),
    (lambda d: d.p.server_env.unlink(), "settings"),
    (lambda d: d.p.live_config.unlink(), "live is not on this machine"),
    (lambda d: sqlite3.connect(d.live).execute("DROP TABLE stripe_feed_checkins"),
     "check-ins cannot be read"),
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
    assert not [c for c in desk.calls if c[:1] == ["git"] and c[3] == "merge"] or why == \
        "could not be moved"


def test_server_update_puts_the_code_back_when_the_server_is_not_healthy(desk, capsys):
    desk.healthy_from = 0
    assert call(desk, f"server-update {NEW}") == 1
    srv = str(desk.p.server)
    assert desk.did("git", "-C", srv, "reset") == [["git", "-C", srv, "reset", "--quiet",
                                                    "--keep", OLD]]
    assert desk.heads[srv] == OLD
    out = capsys.readouterr().out
    assert "did not answer healthy" in out and "is back at aaaaaaaaaaaa" in out


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


def test_server_update_puts_the_code_back_when_the_feed_dies_after_starting(desk, capsys):
    desk.feed_dies = True
    assert call(desk, f"server-update {NEW}") == 1
    assert desk.heads[str(desk.p.server)] == OLD
    assert "did not keep running on the new code" in capsys.readouterr().out


def test_server_update_puts_the_code_back_when_systemd_restarted_the_feed(desk, capsys):
    """The feed's unit restarts it on a crash (Restart=on-failure): running
    again, on a new PID, is a crash on the new code."""
    desk.feed_respawns = True
    assert call(desk, f"server-update {NEW}") == 1
    assert desk.heads[str(desk.p.server)] == OLD
    assert "did not keep running on the new code" in capsys.readouterr().out


def test_server_update_no_check_in_keeps_the_new_code_and_says_so(desk, capsys):
    desk.feed_checks_in = False
    assert call(desk, f"server-update {NEW}") == 1
    assert desk.heads[str(desk.p.server)] == NEW
    assert not desk.did("git", "-C", str(desk.p.server), "reset")
    assert "no new check-in could be seen" in capsys.readouterr().out


def test_server_update_never_says_nothing_changed_after_the_change(desk, capsys):
    """Live's check-ins and the server's settings, readable before the
    change, are gone after it: the step is not refused (a refusal says
    nothing was changed), it says what it could not see, and the feed's
    status runs with the settings read before the change."""
    desk.unreadable_after = True
    assert call(desk, f"server-update {NEW}") == 1
    out, err = capsys.readouterr()
    assert "REFUSED" not in err and "no new check-in could be seen" in out
    assert f"'server-update {NEW}' -> exit 1" in desk.p.log.read_text()
    assert desk.heads[str(desk.p.server)] == NEW, "a check-in not seen puts nothing back"


def test_server_update_reads_the_settings_once_before_the_change(desk):
    """The feed's status at the end runs with the settings read before the
    change, not with a second read that could fail after it: server.env goes
    once the feed has restarted and checked in."""
    real_run = desk.run

    def run(argv, cwd=None, env=None):
        code = real_run(argv, cwd, env)
        if argv == ["sudo", "-n", "systemctl", "restart", R.FEED]:
            desk.p.server_env.unlink()
        return code

    desk.run = run  # type: ignore[method-assign]
    assert call(desk, f"server-update {NEW}") == 0
    (argv,) = [c for c in desk.calls if c[0].endswith("motodiag")]
    assert desk.envs[desk.calls.index(argv)]["MOTODIAG_ENV"] == "prod"


@pytest.mark.parametrize("how", ["reset", "reset-silent"])
def test_server_update_a_failed_put_back_is_said_not_claimed(desk, capsys, how):
    desk.healthy_from = 0
    desk.fail.add(how)
    assert call(desk, f"server-update {NEW}") == 1
    out = capsys.readouterr().out
    assert "could NOT be put back" in out and "back on the old code" not in out
    assert len(desk.did("sudo")) == 1, "nothing restarted on the new code after a failed put-back"


def test_server_update_a_status_not_right_keeps_the_new_code(desk, capsys):
    desk.status_codes = [1]
    assert call(desk, f"server-update {NEW}") == 1
    assert desk.heads[str(desk.p.server)] == NEW
    assert not desk.did("git", "-C", str(desk.p.server), "reset")
    assert "says something is not right" in capsys.readouterr().out


def test_server_update_runs_to_its_put_back_when_the_mac_goes_away(desk, monkeypatch):
    """The Mac pressed Ctrl-C: every write to the closed channel fails, and
    the step still puts the code back and restarts both (the review's 1)."""
    monkeypatch.setattr(sys, "stdout", Gone())
    monkeypatch.setattr(sys, "stderr", Gone())
    desk.healthy_from = 0
    assert call(desk, f"server-update {NEW}") == 1
    srv = str(desk.p.server)
    assert desk.heads[srv] == OLD
    assert desk.did("git", "-C", srv, "reset") and len(desk.did("sudo")) == 2
    assert f"'server-update {NEW}' -> exit 1" in desk.p.log.read_text()


@pytest.mark.parametrize("command", ["backups", "fetch 406 dryrun"])
def test_384s_operations_also_run_to_their_end_when_the_mac_goes_away(desk, monkeypatch,
                                                                     command):
    """384's own operations print through `say` too: a Mac gone away does not
    end one at its next line, and its outcome is logged."""
    desk.p.outbox.mkdir(parents=True)
    (desk.p.outbox / "406_dryrun_diff.md").write_text("# the diff\n")
    monkeypatch.setattr(sys, "stdout", Gone())
    monkeypatch.setattr(sys, "stderr", Gone())
    assert call(desk, command) == 0
    assert f"'{command}' -> exit 0" in desk.p.log.read_text()


# ---------------------------------------------------------------- the fleet
def test_fleet_status_reads_only(desk, capsys):
    desk.recover = (0, "1 stage(s) to act on")
    assert call(desk, "fleet-status") == 0
    assert not desk.changed()
    out = capsys.readouterr().out
    assert f"{R.FLEET}: active" in out and "no stage is running" in out
    assert "1 stage(s) to act on" in out


def test_the_search_on_start_runs_with_the_fleet_units_path(desk):
    """The review's 7: sshd's PATH has no ~/.local/bin, where gh may be; the
    search on start runs with the PATH the fleet's own unit gives it."""
    unit = (ROOT / "ops" / "desktop" / "motodiag-fleet.service").read_text()
    (line,) = [ln for ln in unit.splitlines() if ln.startswith("Environment=PATH=")]
    units = line.removeprefix("Environment=PATH=").replace("/home/lilcu", str(desk.p.home))
    call(desk, "fleet-status")
    (argv,) = [c for c in desk.calls if c[-2:] == ["recover", "--dry-run"]]
    env = desk.envs[desk.calls.index(argv)]
    assert env["PATH"] == units


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
    (lambda d: setattr(d, "recover", (1, "nothing to resume")), "could not say"),
    (lambda d: setattr(d, "recover", (1, "")), "could not say"),
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


def test_fleet_move_a_start_logged_but_not_running_is_not_a_start(desk, capsys):
    desk.fleet_stays_up = False
    assert call(desk, f"fleet-move {NEW}") == 1
    assert desk.heads[str(desk.p.fleet_code)] == OLD


def test_fleet_move_a_restart_sudo_refuses_puts_the_code_back(desk):
    desk.fail.add(f"restart {R.FLEET}")
    assert call(desk, f"fleet-move {NEW}") == 1
    assert desk.heads[str(desk.p.fleet_code)] == OLD


@pytest.mark.parametrize("how", ["reset", "reset-silent"])
def test_fleet_move_a_failed_put_back_is_said_not_claimed(desk, capsys, how):
    desk.fleet_logs_start = False
    desk.fail.add(how)
    assert call(desk, f"fleet-move {NEW}") == 1
    out = capsys.readouterr().out
    assert "could NOT be put back" in out and "back on the old code" not in out
    assert len(desk.did("sudo")) == 1


# ---------------------------------------------------------------- the database step
def test_deploy_dryrun_runs_the_fleets_step_alone_unbuffered(desk):
    assert call(desk, f"deploy-dryrun 334 {BRANCH} {NEW}") == 0
    (argv,) = [c for c in desk.calls if c[0].endswith("python")]
    assert argv == [str(desk.p.fleet_state / "venv" / "bin" / "python"), "-u",
                    str(desk.p.fleet_code / ".claude" / "skills" / "deploy" / "through_fleet.py"),
                    "334", BRANCH, NEW, "--dry-run-only"]


def test_deploy_apply_names_the_sha256_the_mac_showed(desk):
    assert call(desk, f"deploy-apply 334 {BRANCH} {NEW} {SHA}") == 0
    (argv,) = [c for c in desk.calls if c[0].endswith("python")]
    assert argv[-5:] == ["334", BRANCH, NEW, "--apply", SHA]
    assert not desk.did("sudo")


def test_run_passes_each_line_on_and_survives_a_closed_channel(monkeypatch):
    shell = R.Shell()
    got = io.StringIO()
    monkeypatch.setattr(sys, "stdout", got)
    code = shell.run([sys.executable, "-c",
                      "import sys; print('one', flush=True); print('two', file=sys.stderr)"])
    assert code == 0 and got.getvalue() == "one\ntwo\n"
    monkeypatch.setattr(sys, "stdout", Gone())
    assert shell.run([sys.executable, "-c", "import sys; print('x'); sys.exit(3)"]) == 3
    assert shell.run([sys.executable, "-c", "import sys; "
                      "sys.stdout.buffer.write(b'\\xff\\xfe not utf-8\\n'); sys.exit(4)"]) == 4


def test_the_dispatcher_runs_to_its_end_when_the_mac_hangs_up(tmp_path):
    """The real dispatcher, run as the way in runs it (the request in
    SSH_ORIGINAL_COMMAND), its stdout and stderr with no reader and SIGHUP
    sent mid-step, as when the Mac's ssh ends: the step still runs to its
    end, and its outcome is logged."""
    home = tmp_path / "home"
    marks = tmp_path / "marks"
    marks.mkdir()
    live = home / "motodiag" / "live" / "motodiag.db"
    live.parent.mkdir(parents=True)
    sqlite3.connect(live).close()
    cfg = home / ".config" / "motodiag"
    cfg.mkdir(parents=True)
    (cfg / "live.json").write_text(json.dumps({"live": str(live)}))
    (cfg / "server.env").write_text("MOTODIAG_ENV=prod\n")
    cli = home / "motodiag" / "server" / ".venv" / "bin" / "motodiag"
    cli.parent.mkdir(parents=True)
    cli.write_text('#!/bin/sh\necho started > "$MARKS/started"\n'
                   'i=0; while [ $i -lt 500 ]; do echo "feed line $i"; i=$((i+1)); done\n'
                   'sleep 1\n'
                   'i=0; while [ $i -lt 500 ]; do echo "feed line $i"; i=$((i+1)); done\n'
                   'echo done > "$MARKS/done"\n')
    cli.chmod(0o755)
    p = subprocess.Popen([sys.executable, str(ROOT / "ops" / "desktop" / "motodiag_remote.py")],
                         env={"HOME": str(home), "PATH": "/usr/bin:/bin", "MARKS": str(marks),
                              "SSH_ORIGINAL_COMMAND": "feed-status"},
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert p.stdout is not None and p.stderr is not None
    p.stdout.close()
    p.stderr.close()
    for _ in range(200):
        if (marks / "started").exists():
            break
        time.sleep(0.05)
    assert (marks / "started").exists(), "the step never started"
    os.kill(p.pid, signal.SIGHUP)
    p.wait(timeout=60)
    assert (marks / "done").exists()
    log = (home / "motodiag" / "remote.log").read_text()
    assert "'feed-status' -> exit 0" in log, log


def test_a_command_outlives_the_macs_closed_channel(tmp_path):
    """The real pipe, as when the Mac's ssh ends mid-step: the dispatcher's
    stdout has no reader. A command it runs that writes lines (as git and
    sudo do when they fail) runs to its end and its exit comes back; writing
    to that pipe itself, it would die of SIGPIPE."""
    out = tmp_path / "rc"
    child = (
        "import importlib.util, sys, time\n"
        f"spec = importlib.util.spec_from_file_location('r', "
        f"{str(ROOT / 'ops' / 'desktop' / 'motodiag_remote.py')!r})\n"
        "r = importlib.util.module_from_spec(spec)\n"
        "sys.modules['r'] = r\n"
        "spec.loader.exec_module(r)\n"
        "time.sleep(0.5)\n"
        "rc = r.Shell().run(['/bin/sh', '-c', "
        "'i=0; while [ $i -lt 2000 ]; do echo line $i; i=$((i+1)); done; exit 3'])\n"
        f"open({str(out)!r}, 'w').write(str(rc))\n")
    p = subprocess.Popen([sys.executable, "-c", child], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    assert p.stdout is not None
    p.stdout.close()
    p.wait(timeout=60)
    assert out.read_text() == "3"
