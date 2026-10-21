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
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REFUSED = 64
UNIT = "motodiag-api.service"
HEALTHZ = "http://127.0.0.1:8000/healthz"
PATTERNS = {
    "phase": r"\d{3}[A-Z]?",
    "commit": r"[0-9a-f]{40}",
    "label": r"[a-z0-9_-]{1,32}",
    "kind": r"dryrun|live",
}


class Refused(Exception):
    """The request is not one of the operations, or an argument is off its pattern."""


@dataclass(frozen=True)
class Paths:
    dev: Path
    server: Path
    outbox: Path
    log: Path
    backups: Path
    live_config: Path

    @classmethod
    def under(cls, home: Path) -> "Paths":
        return cls(dev=home / "Projects" / "moto-diag", server=home / "motodiag" / "server",
                   outbox=home / "motodiag" / "outbox", log=home / "motodiag" / "remote.log",
                   backups=home / "backups" / "motodiag",
                   live_config=home / ".config" / "motodiag" / "live.json")


class Shell:
    """Runs a command with no shell. Tests replace it."""

    def run(self, argv: list[str], cwd: Path | None = None) -> int:
        sys.stdout.flush()
        return subprocess.run(argv, cwd=cwd).returncode

    def capture(self, argv: list[str], cwd: Path | None = None) -> tuple[int, str]:
        r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
        return r.returncode, r.stdout.strip()

    def healthz(self) -> str:
        try:
            with urllib.request.urlopen(HEALTHZ, timeout=5) as r:
                return r.read().decode()
        except OSError as e:
            return f"no answer ({e})"


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
}


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
        print(f"development checkout at {commit}")

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
        print(f"outbox: {dst.name} sha256 {hashlib.sha256(dst.read_bytes()).hexdigest()}")

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
            print("  CHECK 8 FAILED: live is not on this machine")
            return 4
        c = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
        q = lambda s: c.execute(s).fetchone()[0]  # noqa: E731
        print("live", live, "| schema", q("select max(version) from schema_version"),
              "| rows", q("select count(*) from known_issues"))
        c.close()
        if not list(self.p.dev.glob(f"docs/phases/*/{phase}_dryrun_diff.md")):
            print(f"  {phase} has no dry-run diff: no deploy to verify")
            return 0
        return self.sh.run([self.python, "-B", self.deploy, "verify-live", phase],
                           cwd=self.p.dev)

    def status(self) -> int:
        _, host = self.sh.capture(["hostname"])
        print("host:", host, "| user:", os.environ.get("USER", "?"))
        live = self.live()
        print("live.json:", self.p.live_config.read_text().strip()
              if self.p.live_config.is_file() else "missing")
        if live is not None:
            c = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
            print("live:", live, "| schema", c.execute(
                "select max(version) from schema_version").fetchone()[0],
                "| integrity", c.execute("pragma quick_check").fetchone()[0])
            c.close()
        for name, repo in (("development", self.p.dev), ("server", self.p.server)):
            _, head = self.sh.capture(["git", "-C", str(repo), "log", "-1", "--format=%h %s"])
            _, branch = self.sh.capture(["git", "-C", str(repo), "branch", "--show-current"])
            _, dirty = self.sh.capture(["git", "-C", str(repo), "status", "--porcelain"])
            print(f"{name} checkout: {branch or '(detached)'} {head} | "
                  f"{'clean' if not dirty else 'NOT CLEAN'}")
        _, active = self.sh.capture(["systemctl", "is-active", UNIT])
        print(f"{UNIT}: {active}")
        print("healthz:", self.sh.healthz())
        _, ip = self.sh.capture(["tailscale", "ip", "-4"])
        print("this device's tailnet address:", ip)
        return self.backups()

    def backups(self) -> int:
        files = sorted(self.p.backups.glob("*.db")) if self.p.backups.is_dir() else []
        print(f"backups ({self.p.backups}): {len(files)}")
        for f in files:
            print(f"  {f.name}  {f.stat().st_size} bytes")
        return 0

    def fetch(self, phase: str, kind: str) -> int:
        f = self.p.outbox / f"{phase}_{kind}_diff.md"
        if not f.is_file():
            print(f"no {f.name} in the outbox", file=sys.stderr)
            return 1
        data = f.read_bytes()
        print(json.dumps({"name": f.name, "sha256": hashlib.sha256(data).hexdigest(),
                          "text": data.decode()}))
        return 0

    def api(self, verb: str) -> int:
        code = self.sh.run(["sudo", "-n", "systemctl", verb, UNIT])
        _, active = self.sh.capture(["systemctl", "is-active", UNIT])
        print(f"{UNIT}: {active}")
        return code

    def server_pull(self) -> int:
        srv = str(self.p.server)
        _, branch = self.sh.capture(["git", "-C", srv, "branch", "--show-current"])
        if branch != "master":
            raise Refused(f"the server's checkout is on {branch or '(detached)'}, not master")
        code = self.sh.run(["git", "-C", srv, "pull", "--ff-only", "--quiet"])
        _, head = self.sh.capture(["git", "-C", srv, "log", "-1", "--format=%h %s"])
        print("server checkout:", head)
        return code

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


def main(command: str | None, paths: Paths, shell: Shell) -> int:
    try:
        name, args = parse(command)
        code = Desk(paths, shell).dispatch(name, args)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        log(paths, command, f"refused ({e})".splitlines()[0])
        return REFUSED
    log(paths, command, f"exit {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main(os.environ.get("SSH_ORIGINAL_COMMAND"),
                          Paths.under(Path.home()), Shell()))
