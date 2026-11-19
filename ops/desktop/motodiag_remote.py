#!/usr/bin/env python3
"""The one thing the Mac's key may run on the desktop (Phase 384, the operator's 2A).

Installed by install_remote.sh, root-owned, as /usr/local/libexec/motodiag-remote,
and named by both `ForceCommand` and the key's `command=`: whatever the Mac
asks for arrives here in SSH_ORIGINAL_COMMAND. It runs one operation from
OPS, its arguments held by a pattern each, or refuses (exit 64) having run
nothing. No argument reaches a shell. Every request is logged.

Each operation that runs repository code names the exact commit the Mac
pushed; the development checkout is fetched, must be clean, and is checked
out detached at it. A diff file a deploy mode writes is moved to the outbox,
outside the checkout, and the Mac fetches it (the operator's 3A: the desktop
never commits).

    ssh motodiag-ops status
    ssh motodiag-ops dryrun 384 <40-hex commit>
    ssh motodiag-ops fetch 384 dryrun

Phase 406 (K93) adds the steps the operator did in the desktop's Ubuntu
window: the payments feed's status, stop, start and restart; the server's
update after a merge; the fleet's state, its log for one issue, and the move
of its code copy; and the fleet's database step in two calls, the dry run
and the apply of exactly the diff the Mac showed. No request has a terminal,
so the yes is asked on the Mac between the two. The steps that change
something hold one lock, so two cannot run at once. Every operation runs
to its end, a put-back included, even when the Mac goes away mid-step: a
line that can no longer reach the Mac is dropped, and the outcome is
logged.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import shlex
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Callable

REFUSED = 64
UNIT = "motodiag-api.service"
FEED = "motodiag-payments.service"
FLEET = "motodiag-fleet.service"
HEALTHZ = "http://127.0.0.1:8000/healthz"
#: The line the fleet's dispatcher logs each time it starts (Phase 390).
FLEET_STARTED = b"the search on start:"
PATTERNS = {
    "phase": r"\d{3}[A-Z]?",
    "commit": r"[0-9a-f]{40}",
    "label": r"[a-z0-9_-]{1,32}",
    "kind": r"dryrun|live",
    "issue": r"\d{1,5}",
    "count": r"\d{1,3}",
    "branch": r"phase-\d{3}[A-Z]?-[a-z0-9-]{1,80}",
    "sha256": r"[0-9a-f]{64}",
}


class Refused(Exception):
    """The request is not one of the operations, or an argument is off its pattern."""


def say(*args: object, file: IO[str] | None = None) -> None:
    """print, except that a Mac gone away mid-step does not end the step:
    the line is dropped and the step goes on to its end (Phase 406)."""
    try:
        print(*args, file=file if file is not None else sys.stdout, flush=True)
    except (BrokenPipeError, OSError):
        pass


@dataclass(frozen=True)
class Paths:
    dev: Path
    server: Path
    outbox: Path
    log: Path
    backups: Path
    live_config: Path
    fleet_code: Path
    fleet_state: Path
    server_env: Path
    home: Path

    @classmethod
    def under(cls, home: Path) -> "Paths":
        return cls(dev=home / "Projects" / "moto-diag", server=home / "motodiag" / "server",
                   outbox=home / "motodiag" / "outbox", log=home / "motodiag" / "remote.log",
                   backups=home / "backups" / "motodiag",
                   live_config=home / ".config" / "motodiag" / "live.json",
                   fleet_code=home / "motodiag" / "fleet" / "code",
                   fleet_state=home / ".local" / "state" / "motodiag" / "fleet",
                   server_env=home / ".config" / "motodiag" / "server.env", home=home)


class Shell:
    """Runs a command with no shell. Tests replace it."""

    def run(self, argv: list[str], cwd: Path | None = None,
            env: dict[str, str] | None = None) -> int:
        """Its lines passed on as they come, through `say` (Phase 406): no
        command writes to the Mac's channel itself, so a Mac gone away cannot
        end one mid-step."""
        with subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, errors="replace") as p:
            assert p.stdout is not None
            for line in p.stdout:
                say(line.rstrip("\n"))
        return p.returncode

    def capture(self, argv: list[str], cwd: Path | None = None,
                env: dict[str, str] | None = None) -> tuple[int, str]:
        r = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
        return r.returncode, r.stdout.strip()

    def healthz(self) -> str:
        try:
            with urllib.request.urlopen(HEALTHZ, timeout=5) as r:
                return r.read().decode()
        except OSError as e:
            return f"no answer ({e})"

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


# name -> the pattern of each argument, in order
OPS: dict[str, tuple[str, ...]] = {
    "status": (),
    "dryrun": ("phase", "commit"),
    "apply-live": ("phase", "commit"),
    "verify-live": ("phase", "commit"),
    "live-check": ("phase", "commit"),
    "media-check": ("commit",),
    "backup": ("label",),
    "backups": (),
    "fetch": ("phase", "kind"),
    "api-stop": (),
    "api-start": (),
    "api-restart": (),
    "server-pull": (),
    # Phase 406 (K93)
    "feed-status": (),
    "feed-stop": (),
    "feed-start": (),
    "feed-restart": (),
    "server-update": ("commit",),
    "fleet-status": (),
    "fleet-log": ("issue", "count"),
    "fleet-move": ("commit",),
    "deploy-dryrun": ("phase", "branch", "commit"),
    "deploy-apply": ("phase", "branch", "commit", "sha256"),
}
#: Phase 406's operations that change something: one at a time (`main`'s lock).
CHANGING = frozenset({"feed-stop", "feed-start", "feed-restart", "server-update",
                      "fleet-move", "deploy-dryrun", "deploy-apply"})


def parse(command: str | None) -> tuple[str, list[str]]:
    if not command or not command.strip():
        raise Refused("an interactive login is not offered; name an operation")
    try:
        words = shlex.split(command)
    except ValueError as e:
        raise Refused(f"cannot read the request: {e}") from None
    name, args = words[0], words[1:]
    if name not in OPS:
        raise Refused(f"{name!r} is not an operation; the operations are: {', '.join(OPS)}")
    kinds = OPS[name]
    if len(args) != len(kinds):
        raise Refused(f"{name} takes {len(kinds)} argument(s) ({', '.join(kinds) or 'none'}), "
                      f"got {len(args)}")
    for kind, value in zip(kinds, args):
        if not re.fullmatch(PATTERNS[kind], value):
            raise Refused(f"{name}: {value!r} is not a {kind}")
    return name, args


class Desk:
    def __init__(self, paths: Paths, shell: Shell) -> None:
        self.p, self.sh = paths, shell

    @property
    def python(self) -> str:
        return str(self.p.dev / ".venv" / "bin" / "python")

    @property
    def deploy(self) -> str:
        return str(self.p.dev / ".claude" / "skills" / "deploy" / "deploy.py")

    def live(self) -> Path | None:
        try:
            entry = json.loads(self.p.live_config.read_text())
        except (OSError, ValueError):
            return None
        path = Path(entry["live"]).expanduser() if entry.get("live") else None
        return path if path and path.is_file() else None

    def at(self, commit: str) -> None:
        """The development checkout, clean, detached at `commit`."""
        dev = self.p.dev
        if self.sh.run(["git", "-C", str(dev), "fetch", "--quiet", "origin"]) != 0:
            raise Refused("git fetch failed in the development checkout")
        _, dirty = self.sh.capture(["git", "-C", str(dev), "status", "--porcelain"])
        if dirty:
            raise Refused(f"the development checkout is not clean:\n{dirty}")
        if self.sh.run(["git", "-C", str(dev), "checkout", "--quiet", "--detach", commit]) != 0:
            raise Refused(f"cannot check out {commit}: is it pushed?")
        _, head = self.sh.capture(["git", "-C", str(dev), "rev-parse", "HEAD"])
        if head != commit:
            raise Refused(f"the checkout is at {head}, not {commit}")
        say(f"development checkout at {commit}")

    def to_outbox(self, phase: str, kind: str) -> None:
        rel = f"docs/phases/in_progress/{phase}_{kind}_diff.md"
        src = self.p.dev / rel
        if not src.is_file():
            return
        self.p.outbox.mkdir(parents=True, exist_ok=True)
        dst = self.p.outbox / src.name
        dst.write_bytes(src.read_bytes())
        tracked = self.sh.capture(["git", "-C", str(self.p.dev), "ls-files",
                                   "--error-unmatch", rel])[0] == 0
        if tracked:
            self.sh.run(["git", "-C", str(self.p.dev), "checkout", "--quiet", "--", rel])
        else:
            src.unlink()
        say(f"outbox: {dst.name} sha256 {hashlib.sha256(dst.read_bytes()).hexdigest()}")

    def deploy_mode(self, mode: str, phase: str, commit: str) -> int:
        self.at(commit)
        code = self.sh.run([self.python, "-B", self.deploy, mode, phase], cwd=self.p.dev)
        if mode in ("dryrun", "apply-live"):
            self.to_outbox(phase, "dryrun" if mode == "dryrun" else "live")
        return code

    def live_check(self, phase: str, commit: str) -> int:
        """verify_phase.sh's check 8, here (the operator's (i))."""
        self.at(commit)
        live = self.live()
        if live is None:
            say("  CHECK 8 FAILED: live is not on this machine")
            return 4
        c = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
        q = lambda s: c.execute(s).fetchone()[0]  # noqa: E731
        say("live", live, "| schema", q("select max(version) from schema_version"),
            "| rows", q("select count(*) from known_issues"))
        c.close()
        if not list(self.p.dev.glob(f"docs/phases/*/{phase}_dryrun_diff.md")):
            say(f"  {phase} has no dry-run diff: no deploy to verify")
            return 0
        return self.sh.run([self.python, "-B", self.deploy, "verify-live", phase],
                           cwd=self.p.dev)

    def status(self) -> int:
        _, host = self.sh.capture(["hostname"])
        say("host:", host, "| user:", os.environ.get("USER", "?"))
        live = self.live()
        say("live.json:", self.p.live_config.read_text().strip()
            if self.p.live_config.is_file() else "missing")
        if live is not None:
            c = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
            say("live:", live, "| schema", c.execute(
                "select max(version) from schema_version").fetchone()[0],
                "| integrity", c.execute("pragma quick_check").fetchone()[0])
            c.close()
        for name, repo in (("development", self.p.dev), ("server", self.p.server)):
            _, head = self.sh.capture(["git", "-C", str(repo), "log", "-1", "--format=%h %s"])
            _, branch = self.sh.capture(["git", "-C", str(repo), "branch", "--show-current"])
            _, dirty = self.sh.capture(["git", "-C", str(repo), "status", "--porcelain"])
            say(f"{name} checkout: {branch or '(detached)'} {head} | "
                f"{'clean' if not dirty else 'NOT CLEAN'}")
        _, active = self.sh.capture(["systemctl", "is-active", UNIT])
        say(f"{UNIT}: {active}")
        say("healthz:", self.sh.healthz())
        _, ip = self.sh.capture(["tailscale", "ip", "-4"])
        say("this device's tailnet address:", ip)
        return self.backups()

    def backups(self) -> int:
        files = sorted(self.p.backups.glob("*.db")) if self.p.backups.is_dir() else []
        say(f"backups ({self.p.backups}): {len(files)}")
        for f in files:
            say(f"  {f.name}  {f.stat().st_size} bytes")
        return 0

    def fetch(self, phase: str, kind: str) -> int:
        f = self.p.outbox / f"{phase}_{kind}_diff.md"
        if not f.is_file():
            say(f"no {f.name} in the outbox", file=sys.stderr)
            return 1
        data = f.read_bytes()
        say(json.dumps({"name": f.name, "sha256": hashlib.sha256(data).hexdigest(),
                        "text": data.decode()}))
        return 0

    def api(self, verb: str) -> int:
        return self.unit(UNIT, verb)

    def unit(self, unit: str, verb: str) -> int:
        """`sudo -n systemctl <verb> <unit>`, then what systemd says of it. Only
        the verbs and units the password-free rules name can pass sudo -n."""
        code = self.sh.run(["sudo", "-n", "systemctl", verb, unit])
        _, active = self.sh.capture(["systemctl", "is-active", unit])
        say(f"{unit}: {active}")
        return code

    def server_pull(self) -> int:
        srv = str(self.p.server)
        _, branch = self.sh.capture(["git", "-C", srv, "branch", "--show-current"])
        if branch != "master":
            raise Refused(f"the server's checkout is on {branch or '(detached)'}, not master")
        code = self.sh.run(["git", "-C", srv, "pull", "--ff-only", "--quiet"])
        _, head = self.sh.capture(["git", "-C", srv, "log", "-1", "--format=%h %s"])
        say("server checkout:", head)
        return code

    # ---- Phase 406 (K93): the steps done in the desktop's Ubuntu window
    def active(self, unit: str) -> bool:
        return self.sh.capture(["systemctl", "is-active", unit])[1] == "active"

    def git(self, repo: Path, *args: str) -> tuple[int, str]:
        return self.sh.capture(["git", "-C", str(repo), *args])

    def server_settings(self) -> dict[str, str]:
        """The environment the server's CLI runs with, as the paste blocks
        built it: no `MOTODIAG_*` from here, live's database and folder, then
        `server.env`, line by line."""
        live = self.live()
        if live is None:
            raise Refused("live is not on this machine; nothing was changed")
        env = {k: v for k, v in os.environ.items() if not k.startswith("MOTODIAG_")}
        env["MOTODIAG_DB_PATH"] = str(live)
        env["MOTODIAG_DATA_DIR"] = str(live.parent)
        try:
            text = self.p.server_env.read_text(encoding="utf-8")
        except OSError:
            raise Refused(f"the server's settings ({self.p.server_env}) cannot be read; "
                          "nothing was changed") from None
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line[0] in "#;" or "=" not in line:
                continue
            k, v = (part.strip() for part in line.split("=", 1))
            if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            env[k] = v
        return env

    def feed_status(self) -> int:
        """`motodiag payments feed status`, its lines and its exit code."""
        env = self.server_settings()
        cli = str(self.p.server / ".venv" / "bin" / "motodiag")
        return self.sh.run([cli, "payments", "feed", "status"], cwd=self.p.server, env=env)

    def checkins(self) -> int:
        """The payments feed's check-in rows on live (Phase 404's table)."""
        live = self.live()
        if live is None:
            raise Refused("live is not on this machine; nothing was changed")
        try:
            c = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
            try:
                return int(c.execute("SELECT COUNT(*) FROM stripe_feed_checkins").fetchone()[0])
            finally:
                c.close()
        except sqlite3.Error as e:
            raise Refused(f"live's check-ins cannot be read ({e}); nothing was changed") from None

    def master_clean(self, repo: Path, what: str) -> str:
        """The checkout's HEAD, when it is on master with nothing changed by hand."""
        _, branch = self.git(repo, "branch", "--show-current")
        if branch != "master":
            raise Refused(f"{what} is on {branch or '(detached)'}, not master; nothing was changed")
        _, dirty = self.git(repo, "status", "--porcelain", "--untracked-files=no")
        if dirty:
            raise Refused(f"{what} has changes made by hand; nothing was changed:\n{dirty}")
        return self.git(repo, "rev-parse", "HEAD")[1]

    def master_is(self, repo: Path, commit: str, what: str) -> None:
        """Master on GitHub is at `commit`: the Mac names what it checked."""
        if self.sh.run(["git", "-C", str(repo), "fetch", "--quiet", "origin",
                        "+refs/heads/master:refs/remotes/origin/master"]) != 0:
            raise Refused(f"could not fetch master from GitHub into {what}; nothing was changed")
        _, master = self.git(repo, "rev-parse", "refs/remotes/origin/master")
        if master != commit:
            raise Refused(f"master on GitHub is at {master[:12]}, not at {commit[:12]}, the "
                          "commit named; nothing was changed")

    def forward(self, repo: Path, before: str, commit: str, what: str) -> None:
        if before == commit:
            say(f"{what} is already at {commit[:12]}")
            return
        if self.git(repo, "merge-base", "--is-ancestor", before, commit)[0] != 0:
            raise Refused(f"{what} has commits that are not on master; nothing was changed")
        if self.sh.run(["git", "-C", str(repo), "merge", "--quiet", "--ff-only", commit]) != 0:
            raise Refused(f"{what} could not be moved to {commit[:12]}; nothing was changed")
        say(f"{what} moved from {before[:12]} to {commit[:12]}")

    def back(self, repo: Path, before: str, what: str) -> bool:
        """The checkout put back at `before`, and seen there."""
        rc = self.sh.run(["git", "-C", str(repo), "reset", "--quiet", "--keep", before])
        if rc != 0 or self.git(repo, "rev-parse", "HEAD")[1] != before:
            say(f"{what} could NOT be put back at {before[:12]}: it stays on the new code. "
                "Bring this to the advisor now")
            return False
        say(f"{what} is back at {before[:12]}")
        return True

    def healthy(self, tries: int = 30) -> bool:
        for _ in range(tries):
            if '"status":"ok"' in self.sh.healthz():
                return True
            self.sh.sleep(2)
        return False

    def main_pid(self, unit: str) -> str:
        return self.sh.capture(["systemctl", "show", "-p", "MainPID", "--value", unit])[1]

    def restart_server(self) -> tuple[str | None, str]:
        """The app server, then the payments feed, restarted: what failed, or
        None; and the feed's new main PID."""
        if self.sh.run(["sudo", "-n", "systemctl", "restart", UNIT]) != 0:
            return "the app server could not be restarted", ""
        if not self.healthy():
            return "the app server did not answer healthy", ""
        old = self.main_pid(FEED)
        if self.sh.run(["sudo", "-n", "systemctl", "restart", FEED]) != 0:
            return "the payments feed could not be restarted", ""
        self.sh.sleep(5)
        new = self.main_pid(FEED)
        if not self.active(FEED) or new in ("", "0", old):
            return "the payments feed did not come back", ""
        return None, new

    def server_update(self, commit: str) -> int:
        """The server's update after a merge (404's step 1, as one name)."""
        srv, what = self.p.server, "the server's checkout"
        if not self.active(UNIT):
            raise Refused("the app server is not running; nothing was changed")
        if not self.active(FEED):
            raise Refused("the payments feed is not running; nothing was changed")
        self.server_settings()
        seen = self.checkins()
        before = self.master_clean(srv, what)
        self.master_is(srv, commit, what)
        self.forward(srv, before, commit, what)
        problem, pid = self.restart_server()
        if problem is None:
            for _ in range(60):
                self.sh.sleep(3)
                if self.checkins() > seen:
                    break
            if not self.active(FEED) or self.main_pid(FEED) != pid:
                problem = "the payments feed did not keep running on the new code"
            elif self.checkins() <= seen:
                say("the payments feed runs the new code, but wrote down no check-in in 3 "
                    "minutes; it asks Stripe as before, so bring this to the advisor")
                return 1
        if problem:
            say(f"{problem}: putting the code back at {before[:12]} and restarting both")
            if not self.back(srv, before, what):
                return 1
            again, _ = self.restart_server()
            say("both are back on the old code and running" if again is None else
                f"{again}, even on the old code: bring this to the advisor now")
            return 1
        say("the app server answers healthy, and the payments feed checked in on the new code")
        status = self.feed_status()
        _, head = self.git(srv, "log", "-1", "--format=%h %s")
        say(f"the server and the payments feed are on: {head}")
        if status != 0:
            say("the payments feed's status says something is not right (its lines above)")
        return status

    def recover_dry_run(self) -> tuple[int, str]:
        """What the fleet's search on start would do; it writes nothing. Run
        with the fleet unit's PATH (`motodiag-fleet.service`), where `gh` is."""
        script = self.p.fleet_code / ".claude" / "skills" / "fleet" / "dispatcher.py"
        env = {**os.environ,
               "PATH": f"{self.p.home / '.local' / 'bin'}:/usr/local/bin:/usr/bin:/bin"}
        return self.sh.capture(["/usr/bin/python3", str(script), "recover", "--dry-run"],
                               cwd=self.p.fleet_code, env=env)

    def stage_running(self) -> bool:
        return self.sh.capture(["pgrep", "-x", "bwrap"])[0] == 0

    def fleet_status(self) -> int:
        say(f"{FLEET}: {self.sh.capture(['systemctl', 'is-active', FLEET])[1]}")
        say("a stage is running" if self.stage_running() else "no stage is running")
        code = self.p.fleet_code
        _, branch = self.git(code, "branch", "--show-current")
        _, head = self.git(code, "log", "-1", "--format=%H %s")
        _, dirty = self.git(code, "status", "--porcelain", "--untracked-files=no")
        say(f"the fleet's code copy: {branch or '(detached)'} {head} | "
            f"{'clean' if not dirty else 'NOT CLEAN'}")
        _, said = self.recover_dry_run()
        say(f"the fleet's search on start would say: {said}")
        return 0

    def fleet_log(self, issue: str, count: str) -> int:
        """The fleet's log lines that name `issue <n>:`, read as bytes: a zero
        byte in the file cannot hide them (F284)."""
        path = self.p.fleet_state / "dispatcher.log"
        try:
            data = path.read_bytes()
        except OSError:
            say(f"the fleet's log is not here ({path})", file=sys.stderr)
            return 1
        want = f"issue {issue}:".encode()
        lines = [ln for ln in data.split(b"\n") if want in ln]
        shown = lines[-int(count):] if int(count) else []
        for ln in shown:
            say(ln.replace(b"\x00", b"").decode("utf-8", "replace"))
        say(f"({len(lines)} line(s) name issue {issue}; {len(shown)} shown)")
        return 0

    def starts(self) -> int:
        try:
            return (self.p.fleet_state / "dispatcher.log").read_bytes().count(FLEET_STARTED)
        except OSError:
            return 0

    def restart_fleet(self) -> bool:
        """The fleet restarted, and its start seen in its log within 2 minutes."""
        seen = self.starts()
        if self.sh.run(["sudo", "-n", "systemctl", "restart", FLEET]) != 0:
            return False
        for _ in range(60):
            self.sh.sleep(2)
            if self.starts() > seen and self.active(FLEET):
                return True
        return False

    def fleet_move(self, commit: str) -> int:
        """The fleet's code copy moved to `commit` (403's step 2, as one name)."""
        code, what = self.p.fleet_code, "the fleet's code copy"
        if self.stage_running():
            raise Refused("a stage of the fleet is running; nothing was changed, so try again "
                          "when it has ended")
        rc, said = self.recover_dry_run()
        if rc != 0 or said.strip().splitlines()[-1:] != ["nothing to resume"]:
            raise Refused(f"the fleet's search on start would act on something, or could not "
                          f"say ({said.strip()[-300:] or 'no answer'}); nothing was changed")
        before = self.master_clean(code, what)
        self.master_is(code, commit, what)
        self.forward(code, before, commit, what)
        if self.restart_fleet():
            _, head = self.git(code, "log", "-1", "--format=%h %s")
            say(f"the fleet restarted and is on: {head}")
            return 0
        say(f"the fleet did not come back on {commit[:12]}: putting its code back at "
            f"{before[:12]} and restarting it")
        if self.back(code, before, what):
            say("the fleet is back on the old code" if self.restart_fleet() else
                "the fleet is not running even on the old code: bring this to the advisor now")
        return 1

    def through_fleet(self, *args: str) -> int:
        """The fleet's database step, run as its paste block runs it: the
        fleet's venv and its own code copy (master's), never a branch's.
        Unbuffered, so its lines reach the Mac as they come."""
        python = str(self.p.fleet_state / "venv" / "bin" / "python")
        step = str(self.p.fleet_code / ".claude" / "skills" / "deploy" / "through_fleet.py")
        return self.sh.run([python, "-u", step, *args])

    def dispatch(self, name: str, args: list[str]) -> int:
        handlers: dict[str, Callable[[], int]] = {
            "status": self.status,
            "dryrun": lambda: self.deploy_mode("dryrun", *args),
            "apply-live": lambda: self.deploy_mode("apply-live", *args),
            "verify-live": lambda: self.deploy_mode("verify-live", *args),
            "live-check": lambda: self.live_check(*args),
            "media-check": lambda: self.media_check(*args),
            "backup": lambda: self.sh.run([self.python, "-B", self.deploy, "backup", *args],
                                          cwd=self.p.dev),
            "backups": self.backups,
            "fetch": lambda: self.fetch(*args),
            "api-stop": lambda: self.api("stop"),
            "api-start": lambda: self.api("start"),
            "api-restart": lambda: self.api("restart"),
            "server-pull": self.server_pull,
            "feed-status": self.feed_status,
            "feed-stop": lambda: self.unit(FEED, "stop"),
            "feed-start": lambda: self.unit(FEED, "start"),
            "feed-restart": lambda: self.unit(FEED, "restart"),
            "server-update": lambda: self.server_update(*args),
            "fleet-status": self.fleet_status,
            "fleet-log": lambda: self.fleet_log(*args),
            "fleet-move": lambda: self.fleet_move(*args),
            "deploy-dryrun": lambda: self.through_fleet(*args, "--dry-run-only"),
            "deploy-apply": lambda: self.through_fleet(*args[:3], "--apply", args[3]),
        }
        return handlers[name]()

    def media_check(self, commit: str) -> int:
        self.at(commit)
        return self.sh.run([self.python, "-B", str(
            self.p.dev / ".claude" / "skills" / "deploy" / "media_check.py")], cwd=self.p.dev)


def log(paths: Paths, command: str | None, outcome: str) -> None:
    paths.log.parent.mkdir(parents=True, exist_ok=True)
    src = (os.environ.get("SSH_CONNECTION") or "?").split(" ")[0]
    with paths.log.open("a") as f:
        f.write(f"{dt.datetime.now().isoformat(timespec='seconds')} from {src} "
                f"{command!r} -> {outcome}\n")


def one_at_a_time(paths: Paths) -> IO[str]:
    """The lock Phase 406's changing operations hold; refused when held."""
    paths.log.parent.mkdir(parents=True, exist_ok=True)
    f = (paths.log.parent / "remote.lock").open("w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        raise Refused("another step is running on the desktop; nothing was changed, so try "
                      "again when it has ended") from None
    return f


def main(command: str | None, paths: Paths, shell: Shell) -> int:
    lock: IO[str] | None = None
    try:
        name, args = parse(command)
        if name in CHANGING:
            lock = one_at_a_time(paths)
        code = Desk(paths, shell).dispatch(name, args)
    except Refused as e:
        say(f"REFUSED: {e}", file=sys.stderr)
        log(paths, command, f"refused ({e})".splitlines()[0])
        return REFUSED
    finally:
        if lock is not None:
            lock.close()
    log(paths, command, f"exit {code}")
    return code


if __name__ == "__main__":
    # A Mac gone away mid-step: the step still runs to its end (Phase 406).
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    raise SystemExit(main(os.environ.get("SSH_ORIGINAL_COMMAND"),
                          Paths.under(Path.home()), Shell()))
