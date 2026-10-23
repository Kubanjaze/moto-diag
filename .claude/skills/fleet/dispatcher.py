#!/usr/bin/env python3
"""The fleet's dispatcher: polls the labels, runs the read-only ranks, fenced.

    dispatcher.py run [--interval 300] [--sweep-hours 24]   the loop (the unit's command)
    dispatcher.py once [--sweep-hours 24]                   one cycle
    dispatcher.py usage                                     the parsed /usage lines

Not the 384 door's dispatcher (`ops/desktop/motodiag_remote.py`): this one
runs on the home desktop as the operator's user, one process (an exclusive
`flock`), and handles only what Phase 387 built:
  - `plan:needs-review` on an open issue runs the Executive Officer
    (`xo.review`), once per application of the label;
  - after 07:00 local, yesterday's digest (`yeoman.digest`), once a day;
  - the sweep: one comment on any open issue whose state label has sat for
    more than 24 hours.

**Every model call runs through `fence.sh`**, in a fresh clone of the
dispatcher's own GitHub mirror, with the fleet's OAuth token and nothing
else. The ranks' scripts run here against that clone; `gh` runs here, never
inside the fence, which cannot see the login it needs. The script, not the
model, moves a label (387): this file never moves one itself.

**A stage that cannot finish leaves the label where it found it.** A rank's
stop is its own (387's comment). A usage limit is the dispatcher's: it
records the reset time and the session, comments, starts no model stage
until the reset, then reruns the stage in the same run directory with
`--resume`. No new Opus stage starts at or above 70% of the weekly cap, or
when the usage cannot be read.

Exit 0 a cycle ran; 1 a cycle failed (the loop logs it and goes on); 4 a
refusal before any cycle: another dispatcher holds the lock, no token file,
a token that is not the fleet's OAuth class, or ANTHROPIC_API_KEY set.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import traceback
from collections.abc import Callable
from zoneinfo import ZoneInfo

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rank_call  # noqa: E402
import xo  # noqa: E402
import yeoman  # noqa: E402
from labels import LABELS  # noqa: E402
from rank_call import OPUS, Runner, Stop  # noqa: E402

REPO = "Kubanjaze/moto-diag"
REPO_URL = f"https://github.com/{REPO}.git"
FENCE = HERE / "fence.sh"
STATE = pathlib.Path(os.environ.get("FLEET_STATE")
                     or pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet")
TOKEN_FILE = pathlib.Path.home() / ".config" / "motodiag" / "anthropic.env"
WORKSPACE_DOCS = pathlib.Path(os.environ.get("FLEET_WORKSPACE_DOCS")
                              or pathlib.Path.home() / "Projects" / "workspace-docs")

INTERVAL_S = 300
#: The operator's numbers (the fleet proposal; the 388 prompt).
OPUS_CEILING = 70
SWEEP_HOURS = 24.0
DIGEST_HOUR = 7
RESET_UNKNOWN = dt.timedelta(hours=1)
KEEP_RUNS = 20

REVIEW = "plan:needs-review"
#: Every label but `mission`, which marks what the issue is for its whole life.
STATE_LABELS = tuple(name for name, _, _ in LABELS if name != "mission")
#: Who moves each label next (the proposal's label table).
NEXT_RANK = {
    "step0:done": "the Captain", "plan:needs-review": "the Executive Officer",
    "plan:approved": "the Chief Engineer", "build:open": "the Chief Engineer",
    "review:open": "the Red Team", "review:clear": "the Captain",
    "merge:needs-review": "the Quartermaster", "needs-admiral": "the Admiral",
    "needs-hands": "the Admiral", "merged": "whoever merged, to close the issue",
}
MARKER = "<!-- fleet-dispatcher:"
SWEEP_MARKER = "<!-- fleet-sweep:"
#: A comment by a rank on an issue: the XO's verdict, the XO's stop, ours.
RANK_COMMENT = (xo.MARKER, "Executive Officer, phase", MARKER)

_LIMIT = re.compile(r"\b(?:usage|rate|session|weekly)[ -]limit|\blimit (?:reached|exceeded)|"
                    r"hit your limit", re.I)
_USAGE = re.compile(r"^Current (?P<what>session|week \((?P<model>[^)]+)\)): (?P<pct>\d+)% used"
                    r" · resets (?P<reset>.+?) \((?P<tz>[^)]+)\)\s*$", re.M)
_RESET = re.compile(r"(?:(?P<mon>[A-Z][a-z]{2}) (?P<day>\d{1,2}), )?(?P<h>\d{1,2})"
                    r"(?::(?P<min>\d{2}))?(?P<ap>am|pm)")
#: One OAuth token and nothing else (2026-10-22: a first write held the
#: token five times and a stray escape character, and passed a prefix check).
_TOKEN = re.compile(r"sk-ant-oat[A-Za-z0-9_-]+")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
WEEK_ALL = "week (all models)"


class Refused(Exception):
    """The dispatcher will not start (exit 4)."""


class RateLimited(Exception):
    """A model call hit a usage limit. Not a `Stop`: it passes the rank, which
    neither comments nor moves the label; the dispatcher pauses the stage."""

    def __init__(self, session: str | None, text: str):
        super().__init__(text)
        self.session, self.text = session, text


# --------------------------------------------------------------- the usage
def parse_reset(text: str, tzname: str, now: dt.datetime) -> dt.datetime | None:
    """'Oct 28, 12pm' or '10pm' in the named zone. The year is the first that
    puts the reset no more than a day in the past; a bare time is the next."""
    m = _RESET.fullmatch(text.strip())
    if not m:
        return None
    try:
        tz = ZoneInfo(tzname)
    except (KeyError, ValueError):
        return None
    hour = int(m["h"]) % 12 + (12 if m["ap"] == "pm" else 0)
    minute = int(m["min"] or 0)
    local = now.astimezone(tz)
    if not m["mon"]:
        cand = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return cand if cand >= local else cand + dt.timedelta(days=1)
    for year in (local.year - 1, local.year, local.year + 1):
        try:
            cand = dt.datetime(year, MONTHS.index(m["mon"]) + 1, int(m["day"]), hour, minute,
                               tzinfo=tz)
        except ValueError:
            return None
        if cand >= local - dt.timedelta(days=1):
            return cand
    return None


def parse_usage(text: str, now: dt.datetime) -> dict[str, tuple[int, dt.datetime | None]]:
    """{'session' | 'week (all models)' | 'week (Fable)' …: (percent, reset)}."""
    return {m["what"]: (int(m["pct"]), parse_reset(m["reset"], m["tz"], now))
            for m in _USAGE.finditer(text)}


def opus_refusal(usage: dict | None) -> str | None:
    """Why a new Opus stage may not start, or None when it may."""
    if not usage or WEEK_ALL not in usage:
        return "the weekly usage could not be read"
    pct = usage[WEEK_ALL][0]
    if pct >= OPUS_CEILING:
        return f"the weekly all-models usage is {pct}%, at or above {OPUS_CEILING}%"
    return None


def reset_after_limit(usage: dict | None) -> dt.datetime | None:
    """The latest reset of a line at 100%; else the session line's reset."""
    if not usage:
        return None
    full = [reset for pct, reset in usage.values() if pct >= 100 and reset]
    if full:
        return max(full)
    return usage.get("session", (0, None))[1]


def rate_limit(r: subprocess.CompletedProcess) -> tuple[str | None, str] | None:
    """(session id, text) when a claude call ended on a usage limit."""
    out = r.stdout or ""
    try:
        d = json.loads(out.strip().splitlines()[-1]) if out.strip() else {}
    except ValueError:
        d = {}
    if not isinstance(d, dict):
        d = {}
    text = str(d.get("result") or "")
    if d.get("is_error") and _LIMIT.search(text):
        return d.get("session_id"), text
    if r.returncode != 0 and _LIMIT.search(out + (r.stderr or "")):
        return d.get("session_id"), (text or (r.stderr or out)).strip()[:300]
    return None


# --------------------------------------------------------------- the token
def load_token(path: pathlib.Path = TOKEN_FILE, environ: dict | None = None) -> str:
    """The fleet's OAuth token, from 386's mode-600 file; refused otherwise."""
    env = os.environ if environ is None else environ
    if "ANTHROPIC_API_KEY" in env:
        raise Refused("ANTHROPIC_API_KEY is set in the dispatcher's environment: it would bill "
                      "API rates (the fleet proposal's cost model). Remove it first.")
    if not path.is_file():
        raise Refused(f"no token file at {path}: the operator's setup-token step comes first")
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    if len(lines) != 1 or not lines[0].startswith("CLAUDE_CODE_OAUTH_TOKEN="):
        raise Refused(f"{path} must hold exactly one line, CLAUDE_CODE_OAUTH_TOKEN=…")
    token = lines[0].split("=", 1)[1]
    if not token.startswith("sk-ant-oat"):
        raise Refused(f"the token in {path} is not of the OAuth class (sk-ant-oat…)")
    if not _TOKEN.fullmatch(token) or token.count("sk-ant-oat") != 1:
        raise Refused(f"{path} must hold exactly one token and nothing else on its line: "
                      "a doubled paste or a stray character fails here")
    return token


# --------------------------------------------------------------- the fence
class FencedRunner:
    """The `run=` callable a rank's script gets: `claude` through fence.sh in
    this stage's clone, `gh` here with GH_REPO, anything else here."""

    def __init__(self, fleet: Fleet, clone: pathlib.Path, run_dir: pathlib.Path,
                 resume: str | None = None):
        self.fleet, self.clone, self.run_dir, self.resume = fleet, clone, run_dir, resume

    def fence_argv(self, cmd: list[str]) -> list[str]:
        return [str(self.fleet.fence), "--clone", str(self.clone), "--run", str(self.run_dir),
                "--workspace-docs", str(self.fleet.workspace_docs), "--", *cmd]

    def fenced(self, cmd: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
               "CLAUDE_CODE_OAUTH_TOKEN": self.fleet.token}
        return self.fleet.host(self.fence_argv(cmd), capture_output=True, text=True,
                               cwd=self.clone, env=env, timeout=timeout)

    def usage(self) -> dict | None:
        r = self.fenced(["claude", "-p", "/usage", "--output-format", "json",
                         "--strict-mcp-config"], timeout=300)
        try:
            text = str(json.loads(r.stdout).get("result") or "")
        except (ValueError, AttributeError):
            return None
        return parse_usage(text, self.fleet.now()) or None

    def __call__(self, cmd, **kw):
        cmd = list(cmd)
        if cmd[0] == "gh":
            return self.fleet.gh_run(cmd, **kw)
        if cmd[0] != "claude":
            return self.fleet.host(cmd, **kw)
        cwd = kw.get("cwd")
        if cwd is not None and pathlib.Path(cwd).resolve() != self.clone.resolve():
            raise Stop(f"a model call from {cwd}, outside the stage's clone")
        model = cmd[cmd.index("--model") + 1] if "--model" in cmd else None
        if model == OPUS and self.resume is None:
            why = opus_refusal(self.usage())
            if why:
                raise Stop(f"no new Opus stage: {why}")
        if self.resume:
            cmd = [cmd[0], "--resume", self.resume, *cmd[1:]]
        r = self.fenced(cmd, timeout=kw.get("timeout", 1800))
        limited = rate_limit(r)
        if limited:
            raise RateLimited(limited[0] or self.resume, limited[1])
        return r


# --------------------------------------------------------------- the fleet
def _time(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


class Fleet:
    def __init__(self, *, state: pathlib.Path = STATE, token: str = "",
                 host: Runner = subprocess.run, fence: pathlib.Path = FENCE,
                 workspace_docs: pathlib.Path = WORKSPACE_DOCS, repo_url: str = REPO_URL,
                 now: Callable[[], dt.datetime] | None = None, sweep_hours: float = SWEEP_HOURS,
                 out=print):
        self.state_dir, self.token, self.host, self.fence = state, token, host, fence
        self.workspace_docs, self.repo_url, self.sweep_hours = workspace_docs, repo_url, sweep_hours
        self.now = now or (lambda: dt.datetime.now().astimezone())
        self.out = out
        self.mirror = state / "mirror.git"
        self.runs = state / "runs"

    # ---- plumbing
    def log(self, msg: str) -> None:
        line = f"{self.now().isoformat(timespec='seconds')} {msg}"
        self.out(line)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with (self.state_dir / "dispatcher.log").open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def load(self) -> dict:
        p = self.state_dir / "state.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}

    def save(self, state: dict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        p = self.state_dir / "state.json"
        p.with_suffix(".tmp").write_text(json.dumps(state, indent=2), encoding="utf-8")
        p.with_suffix(".tmp").replace(p)

    def gh_run(self, cmd: list[str], **kw) -> subprocess.CompletedProcess:
        kw.pop("cwd", None)
        kw.setdefault("capture_output", True)
        kw.setdefault("text", True)
        kw.setdefault("timeout", 120)
        return self.host(cmd, env={**os.environ, "GH_REPO": REPO}, **kw)

    def gh(self, *args: str) -> str:
        r = self.gh_run(["gh", *args])
        if r.returncode != 0:
            raise Stop(f"gh {' '.join(args[:3])} failed: {r.stderr.strip()[:200]}")
        return r.stdout

    def git(self, *args: str) -> subprocess.CompletedProcess:
        return self.host(["git", *args], capture_output=True, text=True, timeout=600)

    def comment(self, issue: int, kind: str, text: str) -> None:
        self.gh("issue", "comment", str(issue), "--body", f"{MARKER} {kind} -->\n{text}")

    # ---- GitHub reads
    def label_events(self, issue: int) -> list[dict]:
        out = self.gh("api", "--paginate", f"repos/{REPO}/issues/{issue}/events", "--jq",
                      '.[] | select(.event == "labeled") | {label: .label.name, at: .created_at}')
        return [json.loads(ln) for ln in out.splitlines() if ln.strip()]

    def comments(self, issue: int) -> list[dict]:
        return json.loads(self.gh("issue", "view", str(issue), "--json", "comments"))["comments"]

    @staticmethod
    def last_applied(events: list[dict], label: str) -> str | None:
        times = [e["at"] for e in events if e["label"] == label]
        return max(times, key=_time) if times else None

    def due(self, issue: int) -> bool:
        """The label was applied after the rank's last comment here."""
        applied = self.last_applied(self.label_events(issue), REVIEW)
        if applied is None:
            return False
        ranks = [_time(c["createdAt"]) for c in self.comments(issue)
                 if c.get("body", "").lstrip().startswith(RANK_COMMENT)]
        return not ranks or _time(applied) > max(ranks)

    # ---- the mirror and the stage clones
    def update_mirror(self) -> None:
        if (self.mirror / "HEAD").is_file():
            r = self.git("-C", str(self.mirror), "remote", "update", "--prune")
        else:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            r = self.git("clone", "-q", "--mirror", self.repo_url, str(self.mirror))
        if r.returncode != 0:
            raise Stop(f"the mirror could not be updated: {r.stderr.strip()[:200]}")

    def branch_for(self, phase: str, body: str) -> tuple[str | None, str]:
        """(the phase branch, why not)."""
        named = re.search(rf"`(phase-{re.escape(phase)}-[A-Za-z0-9._-]+)`", body or "")
        if named:
            b = named.group(1)
            ok = self.git("-C", str(self.mirror), "rev-parse", "--verify", "-q", f"refs/heads/{b}")
            return (b, "") if ok.returncode == 0 else (None, f"the branch `{b}` the issue names "
                                                              "is not on GitHub")
        heads = self.git("-C", str(self.mirror), "for-each-ref", "--format=%(refname:short)",
                         f"refs/heads/phase-{phase}-*").stdout.split()
        if len(heads) == 1:
            return heads[0], ""
        return None, (f"no branch `phase-{phase}-…` on GitHub" if not heads else
                      f"{len(heads)} branches match `phase-{phase}-…`: {', '.join(heads)}")

    def new_run(self, name: str) -> pathlib.Path:
        stamp = self.now().strftime("%Y%m%d_%H%M%S")
        run = self.runs / f"{stamp}_{name}"
        n = 1
        while run.exists():
            n += 1
            run = self.runs / f"{stamp}_{name}_{n}"
        (run / "run").mkdir(parents=True)
        return run

    def clone(self, run: pathlib.Path, branch: str) -> pathlib.Path:
        r = self.git("clone", "-q", "--no-hardlinks", "--branch", branch, str(self.mirror),
                     str(run / "clone"))
        if r.returncode != 0:
            raise Stop(f"the stage clone of {branch} failed: {r.stderr.strip()[:200]}")
        return run / "clone"

    def prune_runs(self, keep_also: set[str]) -> None:
        if not self.runs.is_dir():
            return
        runs = sorted(p for p in self.runs.iterdir() if p.is_dir())
        for p in runs[:-KEEP_RUNS]:
            if str(p) not in keep_also:
                shutil.rmtree(p, ignore_errors=True)

    # ---- the stages
    def stage_xo(self, issue: int, phase: str, *, branch: str | None = None,
                 resume: dict | None = None) -> str:
        if resume:
            run = pathlib.Path(resume["run"])
            clone, session = run / "clone", resume["session"]
        else:
            run = self.new_run(f"xo_{phase}")
            clone, session = self.clone(run, branch), None
        self.log(f"issue {issue}: the Executive Officer on phase {phase}, {clone}"
                 + (f", resuming session {session}" if session else ""))
        runner = FencedRunner(self, clone, run / "run", resume=session)
        try:
            code = xo.review(phase, issue, repo=clone, run=runner, out=self.log)
        except RateLimited as e:
            self.pause({"stage": "xo", "issue": issue, "phase": phase, "run": str(run),
                        "session": e.session}, e.text, runner)
            return "rate-limited"
        return {0: "verdict applied", 2: "plan unreadable", 3: "stopped"}.get(code, f"exit {code}")

    def stage_digest(self, day: dt.date, *, resume: dict | None = None) -> str:
        if resume:
            run = pathlib.Path(resume["run"])
            clone, session = run / "clone", resume["session"]
        else:
            run = self.new_run("digest")
            clone, session = self.clone(run, "master"), None
        self.log(f"the digest for {day}, {clone}")
        runner = FencedRunner(self, clone, run / "run", resume=session)
        try:
            code = yeoman.digest(day, root=clone, run=runner, out=self.log)
        except RateLimited as e:
            self.pause({"stage": "digest", "day": day.isoformat(), "run": str(run),
                        "session": e.session}, e.text, runner)
            return "rate-limited"
        if code != 0:
            return "stopped"
        page = clone / yeoman.DIGESTS / f"{day.isoformat()}.md"
        (self.state_dir / "digests").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(page, self.state_dir / "digests" / page.name)
        state = self.load()
        state["last_digest"] = day.isoformat()
        self.save(state)
        return f"written, {self.state_dir / 'digests' / page.name}"

    def pause(self, record: dict, why: str, runner: FencedRunner) -> None:
        try:
            usage = runner.usage()
        except (subprocess.SubprocessError, OSError):
            usage = None
        until = reset_after_limit(usage) or self.now() + RESET_UNKNOWN
        state = self.load()
        state["paused"] = {**record, "until": until.isoformat(), "why": why[:300]}
        self.save(state)
        self.log(f"rate-limited: {record['stage']} paused until {until.isoformat()}, "
                 f"session {record.get('session')}: {why[:200]}")
        if record.get("issue") is not None:
            self.comment(record["issue"], f"rate-limited stage={record['stage']} "
                         f"session={record.get('session')} until={until.isoformat()}",
                         f"**Fleet dispatcher: stopped on a usage limit, label unchanged.** "
                         f"{why[:300]}\n\nThe stage resumes after {until:%Y-%m-%d %H:%M %Z}, "
                         f"session `{record.get('session')}`.")

    def resume(self, paused: dict) -> str:
        self.log(f"resuming {paused['stage']} after {paused['until']}")
        if paused["stage"] == "xo":
            return self.stage_xo(paused["issue"], paused["phase"], resume=paused)
        return self.stage_digest(dt.date.fromisoformat(paused["day"]), resume=paused)

    # ---- the sweep
    def sweep(self) -> int:
        issues = json.loads(self.gh("issue", "list", "--state", "open", "--limit", "200",
                                    "--json", "number,labels"))
        posted = 0
        for issue in issues:
            on = [lab["name"] for lab in issue["labels"] if lab["name"] in STATE_LABELS]
            if not on:
                continue
            n = issue["number"]
            events, bodies = self.label_events(n), [c.get("body", "") for c in self.comments(n)]
            for label in on:
                applied = self.last_applied(events, label)
                if applied is None:
                    continue
                hours = (self.now() - _time(applied)).total_seconds() / 3600
                marker = f"{SWEEP_MARKER} label={label} applied={applied} -->"
                if hours <= self.sweep_hours or any(marker in b for b in bodies):
                    continue
                self.gh("issue", "comment", str(n), "--body",
                        f"{marker}\n**Fleet dispatcher: `{label}` has sat on this issue for "
                        f"{hours:.0f} hours** (applied {applied}). Nothing has moved it. "
                        f"Next to move it: {NEXT_RANK[label]}.")
                self.log(f"issue {n}: swept `{label}`, {hours:.0f} h")
                posted += 1
        return posted

    # ---- one cycle
    def digest_day(self) -> dt.date | None:
        now = self.now()
        day = now.date() - dt.timedelta(days=1)
        if now.hour < DIGEST_HOUR or self.load().get("last_digest") == day.isoformat():
            return None
        return day

    def cycle(self) -> None:
        self.update_mirror()
        self.sweep()
        state = self.load()
        paused = state.get("paused")
        if paused:
            if self.now() < _time(paused["until"]):
                self.log(f"paused until {paused['until']}: no model stage this cycle")
                return
            state.pop("paused")
            self.save(state)
            self.log(f"resume: {self.resume(paused)}")
        for issue in json.loads(self.gh("issue", "list", "--label", REVIEW, "--state", "open",
                                        "--limit", "100", "--json", "number,title,body")):
            if self.load().get("paused"):
                return
            n = issue["number"]
            if not self.due(n):
                continue
            m = re.match(r"Phase (\d{2,3}[A-Z]?)\b", issue["title"])
            branch, why = self.branch_for(m.group(1), issue.get("body", "")) if m else (
                None, f"the title {issue['title']!r} names no `Phase <N>`")
            if branch is None:
                self.comment(n, "stopped", f"**Fleet dispatcher: the Executive Officer did not "
                             f"run, label unchanged.** {why}. Apply `{REVIEW}` again once fixed.")
                self.log(f"issue {n}: not run: {why}")
                continue
            try:
                self.log(f"issue {n}: {self.stage_xo(n, m.group(1), branch=branch)}")
            except Stop as e:
                self.comment(n, "stopped", f"**Fleet dispatcher: the Executive Officer could not "
                             f"finish, label unchanged.** {e}")
                self.log(f"issue {n}: stopped: {e}")
        day = None if self.load().get("paused") else self.digest_day()
        if day is not None:
            self.log(f"digest: {self.stage_digest(day)}")
        keep = self.load().get("paused", {}).get("run")
        self.prune_runs({keep} if keep else set())


# --------------------------------------------------------------- the CLI
def lock(state: pathlib.Path):
    state.mkdir(parents=True, exist_ok=True)
    f = (state / "dispatcher.lock").open("w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        raise Refused(f"another dispatcher holds {state / 'dispatcher.lock'}") from None
    return f


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--interval", type=int, default=INTERVAL_S)
    r.add_argument("--sweep-hours", type=float, default=SWEEP_HOURS)
    o = sub.add_parser("once")
    o.add_argument("--sweep-hours", type=float, default=SWEEP_HOURS)
    sub.add_parser("usage")
    a = ap.parse_args(argv)
    try:
        held = lock(STATE)
        fleet = Fleet(state=STATE, token=load_token(TOKEN_FILE),
                      sweep_hours=getattr(a, "sweep_hours", SWEEP_HOURS))
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 4
    with held:
        if a.cmd == "usage":
            fleet.update_mirror()
            run = fleet.new_run("usage")
            usage = FencedRunner(fleet, fleet.clone(run, "master"), run / "run").usage()
            for what, (pct, reset) in (usage or {}).items():
                print(f"{what}: {pct}% used, resets {reset.isoformat() if reset else 'unknown'}")
            return 0 if usage else 1
        if a.sweep_hours != SWEEP_HOURS:
            fleet.log(f"the sweep at {a.sweep_hours} hours, not {SWEEP_HOURS}: a proof run")
        while True:
            try:
                fleet.cycle()
                code = 0
            except Exception:  # noqa: BLE001 — the loop logs every failure and goes on
                fleet.log("cycle failed:\n" + traceback.format_exc())
                code = 1
            if a.cmd == "once":
                return code
            time.sleep(a.interval)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
