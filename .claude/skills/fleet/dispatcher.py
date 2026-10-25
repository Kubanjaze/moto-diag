#!/usr/bin/env python3
"""The fleet's dispatcher: polls the labels, runs each rank, fenced.

    dispatcher.py run [--interval 300] [--sweep-hours 24]   the loop (the unit's command)
    dispatcher.py once [--sweep-hours 24]                   one cycle
    dispatcher.py usage                                     the parsed /usage lines

Not the 384 door's dispatcher (`ops/desktop/motodiag_remote.py`): this one
runs on the home desktop as the operator's user, one process (an exclusive
`flock`). On each open issue titled `Phase <N>: …` whose ROADMAP row on
`master` is 🚧, and that carries neither `needs-admiral` nor `needs-hands`,
it runs the one stage the labels ask for (Phase 389's table):

  `mission` only            the Science Officer (`scout.py`)   → `step0:done`
  `step0:done`              the Captain, v1.0 (`captain.py`)   → `plan:needs-review`
  `plan:needs-review`       the Executive Officer (`xo.py`, 387), or the
                            Captain's revision after its back-to-captain
  `plan:approved`           the Chief Engineer (`engineer.py`) → `review:open`
  `review:open`             the Red Team (`red_team.py`)       → `review:clear` or `build:open`
  `build:open`, sent back   the Chief Engineer, a fix round    → `review:open`
  `review:clear`            the Captain's recommendation       → `merge:needs-review`

and, as in 388: after 07:00 local, yesterday's digest (`yeoman.digest`);
the sweep, one comment on any state label that has sat for more than 24
hours. A stage runs once per application of its label: the label's last
`labeled` event must be newer than that rank's last marker comment.

**Every model call runs through `fence.sh`**, in a fresh clone of the
dispatcher's own GitHub mirror, with the fleet's OAuth token on a pipe
(Phase 389, S0-4) and nothing else. `gh` runs here, never inside the fence.
**Nothing a model wrote is pushed unchecked**: `fleet_git.gate` (the push
guard's checks, outside any session) and a whole-tree run no model touched;
before a PR, the full regression run again the same way.

**A stage that cannot finish leaves the label where it found it**, and
comments why. A usage limit records the reset and the session, comments,
starts no model stage until the reset, then resumes the stage with
`--resume`. No new Opus stage at or above 70% of the weekly cap, and no new
Fable stage at or above 70% of Fable's own week, or when either cannot be
read. A stage that needs the operator adds `needs-admiral` (a decision) or
`needs-hands` (a login) and comments in plain English; the dispatcher then
leaves the issue alone until the operator takes the label off.

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
from dataclasses import dataclass
from zoneinfo import ZoneInfo

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "closeout"))
import captain  # noqa: E402
import closeout_check  # noqa: E402
import engineer  # noqa: E402
import fleet_git  # noqa: E402
import red_team  # noqa: E402
import roadmap_check  # noqa: E402
import scout  # noqa: E402
import xo  # noqa: E402
import yeoman  # noqa: E402
from labels import LABELS  # noqa: E402
from rank_call import FABLE, OPUS, Runner, Stop  # noqa: E402

REPO = "Kubanjaze/moto-diag"
REPO_URL = f"https://github.com/{REPO}.git"
FENCE = HERE / "fence.sh"
STATE = pathlib.Path(os.environ.get("FLEET_STATE")
                     or pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet")
TOKEN_FILE = pathlib.Path.home() / ".config" / "motodiag" / "anthropic.env"
WORKSPACE_DOCS = pathlib.Path(os.environ.get("FLEET_WORKSPACE_DOCS")
                              or pathlib.Path.home() / "Projects" / "workspace-docs")
#: The fleet's virtualenv, installed editable at the fence's own path (389 S0-5).
VENV = STATE / "venv"

INTERVAL_S = 300
#: The operator's numbers (the fleet proposal; the 388 and 389 prompts).
OPUS_CEILING = 70
FABLE_CEILING = 70
SWEEP_HOURS = 24.0
DIGEST_HOUR = 7
RESET_UNKNOWN = dt.timedelta(hours=1)
KEEP_RUNS = 20
CHECK_TIMEOUT_S = 3600

REVIEW = "plan:needs-review"
#: Every label but `mission`, which marks what the issue is for its whole life.
STATE_LABELS = tuple(name for name, _, _ in LABELS if name != "mission")
#: The labels one stage sets in place of another; the operator's two are added beside them.
FLOW = ("step0:done", REVIEW, "plan:approved", "build:open", "review:open", "review:clear",
        "merge:needs-review")
OPERATOR = ("needs-admiral", "needs-hands")
#: Who moves each label next (the proposal's label table).
NEXT_RANK = {
    "step0:done": "the Captain", "plan:needs-review": "the Executive Officer",
    "plan:approved": "the Chief Engineer", "build:open": "the Chief Engineer",
    "review:open": "the Red Team", "review:clear": "the Captain",
    "merge:needs-review": "the Admiral, who merges (the Quartermaster is not built yet)",
    "needs-admiral": "the Admiral", "needs-hands": "the Admiral",
    "merged": "whoever merged, to close the issue",
}
MARKER = "<!-- fleet-dispatcher:"
SWEEP_MARKER = "<!-- fleet-sweep:"
SCOUT_M, CAPTAIN_M = "<!-- fleet-scout:", "<!-- fleet-captain:"
ENGINEER_M, RED_M = "<!-- fleet-engineer:", "<!-- fleet-red-team:"
#: A comment by a rank on an issue: the XO's verdict, the XO's stop, ours (388).
RANK_COMMENT = (xo.MARKER, "Executive Officer, phase", MARKER)
_RED = re.compile(r"^<!-- fleet-red-team: verdict=(\w+) round=(\d+)", re.M)
_XO = re.compile(r"^<!-- xo-verdict: \S+ round=\d+ applied=(\S+)", re.M)

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
WEEK_FABLE = "week (Fable)"
CO_AUTHOR = {"scout": "Claude Haiku 5.5", "captain": "Claude Fable 5.1",
             "engineer": "Claude Opus 5.5", "red-team-record": "Claude Opus 5.5"}


class Refused(Exception):
    """The dispatcher will not start (exit 4)."""


class RateLimited(Exception):
    """A model call hit a usage limit. Not a `Stop`: it passes the rank, which
    neither comments nor moves the label; the dispatcher pauses the stage."""

    def __init__(self, session: str | None, text: str):
        super().__init__(text)
        self.session, self.text = session, text


class Escalated(Exception):
    """A stage handed the issue to the operator (`needs-admiral`)."""


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


def fable_refusal(usage: dict | None) -> str | None:
    """Why a new Fable stage may not start (the 389 prompt: "the 70% headroom
    rule on Fable's own cap too"), or None when it may."""
    if not usage or WEEK_FABLE not in usage:
        return "Fable's weekly usage could not be read"
    pct = usage[WEEK_FABLE][0]
    if pct >= FABLE_CEILING:
        return f"Fable's weekly usage is {pct}%, at or above {FABLE_CEILING}%"
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


def token_pipe(token: str) -> tuple[int, dict]:
    """A pipe holding the token, and the subprocess arguments that put its
    read end on the child's fd 3 (subprocess closes descriptors after
    preexec_fn, so 3 is kept explicitly). The caller closes the fd."""
    r_fd, w_fd = os.pipe()
    os.write(w_fd, token.encode())
    os.close(w_fd)
    return r_fd, {"pass_fds": (3,), "preexec_fn": lambda: os.dup2(r_fd, 3),
                  "stdin": subprocess.DEVNULL}


# --------------------------------------------------------------- the fence
class FencedRunner:
    """The `run=` callable a rank's script gets: `claude` through fence.sh in
    this stage's clone, `gh` here with GH_REPO, anything else here."""

    def __init__(self, fleet: Fleet, clone: pathlib.Path, run_dir: pathlib.Path,
                 resume: str | None = None):
        self.fleet, self.clone, self.run_dir, self.resume = fleet, clone, run_dir, resume

    def fence_argv(self, cmd: list[str], *, net: str = "model", token: bool = True) -> list[str]:
        argv = [str(self.fleet.fence), "--clone", str(self.clone), "--run", str(self.run_dir),
                "--workspace-docs", str(self.fleet.workspace_docs), "--net", net]
        if self.fleet.venv.is_dir():
            argv += ["--venv", str(self.fleet.venv)]
        if self.fleet.mobile.is_dir():
            argv += ["--mobile", str(self.fleet.mobile)]
        if token:
            argv.append("--token-fd")
        return [*argv, "--", *cmd]

    def fenced(self, cmd: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
        r_fd, kw = token_pipe(self.fleet.token)
        try:
            return self.fleet.host(self.fence_argv(cmd), capture_output=True, text=True,
                                   cwd=self.clone, env=env, timeout=timeout, **kw)
        finally:
            os.close(r_fd)

    def usage(self) -> dict | None:
        r = self.fenced(["claude", "-p", "/usage", "--output-format", "json",
                         "--strict-mcp-config"], timeout=300)
        try:
            text = str(json.loads(r.stdout).get("result") or "")
        except (ValueError, AttributeError):
            return None
        return parse_usage(text, self.fleet.now()) or None

    def gate_model(self, model: str | None) -> None:
        """No new Opus or Fable stage over its ceiling; a resumed one is not new."""
        if self.resume is not None or model not in (OPUS, FABLE):
            return
        usage = self.usage()
        why = opus_refusal(usage) if model == OPUS else fable_refusal(usage)
        if why:
            raise Stop(f"no new {'Opus' if model == OPUS else 'Fable'} stage: {why}")

    def __call__(self, cmd, **kw):
        cmd = list(cmd)
        if cmd[0] == "gh":
            return self.fleet.gh_run(cmd, **kw)
        if cmd[0] != "claude":
            return self.fleet.host(cmd, **kw)
        cwd = kw.get("cwd")
        if cwd is not None and pathlib.Path(cwd).resolve() != self.clone.resolve():
            raise Stop(f"a model call from {cwd}, outside the stage's clone")
        self.gate_model(cmd[cmd.index("--model") + 1] if "--model" in cmd else None)
        if self.resume:
            cmd = [cmd[0], "--resume", self.resume, *cmd[1:]]
        r = self.fenced(cmd, timeout=kw.get("timeout", 1800))
        limited = rate_limit(r)
        if limited:
            raise RateLimited(limited[0] or self.resume, limited[1])
        return r

    def session(self, cmd: list[str], *, watch: Callable[[], str | None],
                timeout: int = engineer.SESSION_TIMEOUT_S, every: int = engineer.WATCH_EVERY_S
                ) -> tuple[subprocess.CompletedProcess, str | None]:
        """A long call (the Engineer's), watched from outside the model: every
        `every` seconds `watch()` may name a reason to end it. Returns the
        result and that reason (None when it ended by itself)."""
        self.gate_model(cmd[cmd.index("--model") + 1] if "--model" in cmd else None)
        if self.resume:
            cmd = [cmd[0], "--resume", self.resume, *cmd[1:]]
        out, err = self.run_dir / "session.json", self.run_dir / "session.err"
        r_fd, kw = token_pipe(self.fleet.token)
        try:
            with out.open("w") as o, err.open("w") as e:
                proc = self.fleet.popen(self.fence_argv(cmd), stdout=o, stderr=e, cwd=self.clone,
                                        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                                        **kw)
        finally:
            os.close(r_fd)
        start, reason = time.monotonic(), None
        while proc.poll() is None:
            reason = watch() or (f"the session ran past {timeout // 3600} hours"
                                 if time.monotonic() - start > timeout else None)
            if reason:
                proc.terminate()
                try:
                    proc.wait(60)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                break
            self.fleet.sleep(every)
        reason = reason or watch()
        r = subprocess.CompletedProcess(cmd, proc.returncode, out.read_text(errors="replace"),
                                        err.read_text(errors="replace"))
        limited = None if reason else rate_limit(r)
        if limited:
            raise RateLimited(limited[0] or self.resume, limited[1])
        return r, reason


# --------------------------------------------------------- model-free runs
@dataclass
class Check:
    """A run no model touched: its verdict, and the regression line it printed."""
    ok: bool
    commit: str
    line: str | None = None
    why: str = ""


def _time(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


class Fleet:
    def __init__(self, *, state: pathlib.Path = STATE, token: str = "",
                 host: Runner = subprocess.run, fence: pathlib.Path = FENCE,
                 workspace_docs: pathlib.Path = WORKSPACE_DOCS, repo_url: str = REPO_URL,
                 now: Callable[[], dt.datetime] | None = None, sweep_hours: float = SWEEP_HOURS,
                 out=print, venv: pathlib.Path | None = None, mobile: pathlib.Path | None = None,
                 identity_file: pathlib.Path = fleet_git.IDENTITY_FILE, push_url: str | None = None,
                 popen: Callable[..., subprocess.Popen] = subprocess.Popen,
                 check: Callable[..., Check] | None = None, sleep: Callable[[float], None] = time.sleep):
        self.state_dir, self.token, self.host, self.fence = state, token, host, fence
        self.workspace_docs, self.repo_url, self.sweep_hours = workspace_docs, repo_url, sweep_hours
        self.now = now or (lambda: dt.datetime.now().astimezone())
        self.out = out
        self.mirror = state / "mirror.git"
        self.runs = state / "runs"
        self.venv = venv if venv is not None else state / "venv"
        self.mobile = mobile if mobile is not None else fleet_git.MOBILE
        self.identity_file, self.push_url = identity_file, push_url or repo_url
        self.popen, self.sleep = popen, sleep
        self.check = check or self.check_run
        self._skipped: set[tuple[int, str]] = set()

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

    def fleet_identity(self) -> fleet_git.Identity | None:
        try:
            return fleet_git.read_identity_file(self.identity_file)
        except fleet_git.NeedsHands as e:
            self.log(f"the fleet's GitHub identity file is not usable: {e}")
            return None

    def gh_run(self, cmd: list[str], **kw) -> subprocess.CompletedProcess:
        kw.pop("cwd", None)
        kw.setdefault("capture_output", True)
        kw.setdefault("text", True)
        kw.setdefault("timeout", 120)
        ident = self.fleet_identity()
        return self.host(cmd, env={**os.environ, "GH_REPO": REPO, **(ident.env() if ident else {})},
                         **kw)

    def gh(self, *args: str) -> str:
        r = self.gh_run(["gh", *args])
        if r.returncode != 0:
            raise Stop(f"gh {' '.join(args[:3])} failed: {r.stderr.strip()[:200]}")
        return r.stdout

    def git(self, *args: str) -> subprocess.CompletedProcess:
        return self.host(["git", *args], capture_output=True, text=True, timeout=600)

    def comment(self, issue: int, kind: str, text: str) -> None:
        self.gh("issue", "comment", str(issue), "--body", f"{MARKER} {kind} -->\n{text}")

    def say(self, issue: int, marker: str, text: str) -> None:
        """A rank's marker comment: what the due rule reads."""
        self.gh("issue", "comment", str(issue), "--body", f"{marker}\n{text}")

    def labels_of(self, issue: int) -> list[str]:
        return [x["name"] for x in json.loads(self.gh("issue", "view", str(issue), "--json",
                                                      "labels"))["labels"]]

    def set_state(self, issue: int, label: str) -> None:
        """`label` in place of the issue's other flow labels."""
        have = self.labels_of(issue)
        args = ["issue", "edit", str(issue), "--add-label", label]
        for old in FLOW:
            if old != label and old in have:
                args += ["--remove-label", old]
        self.gh(*args)

    def reapply(self, issue: int, label: str) -> None:
        """Removed then added, so GitHub records a new `labeled` event (388
        measured: adding a label already present records none)."""
        self.gh("issue", "edit", str(issue), "--remove-label", label)
        self.gh("issue", "edit", str(issue), "--add-label", label)

    def escalate(self, issue: int, rank: str, label: str, text: str) -> None:
        self.comment(issue, f"{label} rank={rank}",
                     f"**{text.strip()}**\n\nThe fleet leaves this issue alone until the operator "
                     f"takes `{label}` off.")
        self.gh("issue", "edit", str(issue), "--add-label", label)
        self.log(f"issue {issue}: {label} ({rank}): {text[:200]}")

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

    def due_for(self, issue: int, label: str, markers: tuple[str, ...]) -> bool:
        """The label was applied after the rank's last marker here."""
        applied = self.last_applied(self.label_events(issue), label)
        if applied is None:
            return False
        ranks = [_time(c["createdAt"]) for c in self.comments(issue)
                 if c.get("body", "").lstrip().startswith(markers)]
        return not ranks or _time(applied) > max(ranks)

    def due(self, issue: int) -> bool:
        """The Executive Officer's (388): REVIEW newer than any rank comment."""
        return self.due_for(issue, REVIEW, RANK_COMMENT)

    @staticmethod
    def markers(rank_marker: str, rank: str) -> tuple[str, ...]:
        return (rank_marker, f"{MARKER} stopped rank={rank}")

    def newest(self, issue: int, prefix: str) -> tuple[dt.datetime, str] | None:
        found = [(_time(c["createdAt"]), c["body"]) for c in self.comments(issue)
                 if c.get("body", "").lstrip().startswith(prefix)]
        return max(found) if found else None

    def red_rounds(self, issue: int) -> list[tuple[str, int]]:
        return [(m.group(1), int(m.group(2))) for c in self.comments(issue)
                for m in [_RED.match(c.get("body", "").lstrip())] if m]

    def pr_for(self, branch: str) -> dict | None:
        prs = json.loads(self.gh("pr", "list", "--head", branch, "--state", "open", "--json",
                                 "number,url"))
        return prs[0] if prs else None

    # ---- the mirror and the stage clones
    def update_mirror(self) -> None:
        if (self.mirror / "HEAD").is_file():
            r = self.git("-C", str(self.mirror), "remote", "update", "--prune")
        else:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            r = self.git("clone", "-q", "--mirror", self.repo_url, str(self.mirror))
        if r.returncode != 0:
            raise Stop(f"the mirror could not be updated: {r.stderr.strip()[:200]}")

    def master_rows(self) -> dict[str, str]:
        """{phase: status} on the mirror's master, the last row winning (387)."""
        r = self.git("-C", str(self.mirror), "show", "master:docs/ROADMAP.md")
        return {n: s for n, s in reversed(roadmap_check.rows(r.stdout))} if r.returncode == 0 else {}

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

    def ref(self, branch: str) -> str | None:
        r = self.git("-C", str(self.mirror), "rev-parse", "--verify", "-q", f"refs/heads/{branch}")
        return r.stdout.strip() if r.returncode == 0 else None

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

    # ---- commits, checks, pushes
    def author(self, clone: pathlib.Path, rank: str, ident: fleet_git.Identity | None) -> None:
        name, email = (ident or fleet_git.Identity("operator", None)).author(rank)
        for k, v in (("user.name", name), ("user.email", email)):
            self.git("-C", str(clone), "config", k, v)

    def commit(self, clone: pathlib.Path, paths: list[str], subject: str, rank: str) -> str:
        self.git("-C", str(clone), "add", "--", *paths)
        msg = f"{subject}\n\nCo-Authored-By: {CO_AUTHOR[rank]} <noreply@anthropic.com>\n"
        r = self.git("-C", str(clone), "commit", "-q", "-m", msg)
        if r.returncode != 0:
            raise Stop(f"the commit failed: {(r.stderr or r.stdout).strip()[:200]}")
        return self.git("-C", str(clone), "rev-parse", "HEAD").stdout.strip()

    def check_run(self, clone: pathlib.Path, commit: str, *, full: bool,
                  command: list[str] | None = None) -> Check:
        """`commit` tested in a fresh fenced clone with no model and no token:
        `wholetree.sh` (fast), or `--full` then `regression.sh`; or `command`."""
        run = self.new_run("check")
        target = run / "clone"
        for args in (("clone", "-q", "--no-hardlinks", str(clone), str(target)),
                     ("-C", str(target), "checkout", "-q", "--detach", commit)):
            r = self.git(*args)
            if r.returncode != 0:
                return Check(False, commit, why=f"the check clone failed: {r.stderr.strip()[:200]}")
        wt = ".claude/skills/closeout/wholetree.sh"
        script = (" ".join(command) if command else
                  f"{wt} --full && .claude/skills/closeout/regression.sh" if full else wt)
        runner = FencedRunner(self, target, run / "run")
        r = self.host(runner.fence_argv(["/bin/bash", "-c", script], net="none", token=False),
                      capture_output=True, text=True, cwd=target,
                      env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                      timeout=CHECK_TIMEOUT_S, stdin=subprocess.DEVNULL)
        text = (r.stdout or "") + (r.stderr or "")
        (run / "run" / "check.txt").write_text(text, encoding="utf-8")
        if command:
            return Check(r.returncode == 0, commit, why=text[-2000:])
        if not full:
            return Check(r.returncode == 0, commit, why=text.strip().splitlines()[-1][:300]
                         if text.strip() else f"exit {r.returncode}")
        line = next((ln for ln in text.splitlines()
                     if ln.startswith((closeout_check.PREFIX, closeout_check.FAILED_PREFIX))), None)
        parsed, why = closeout_check.regression_record(text)
        return Check(r.returncode == 0 and parsed is not None, commit, line, why or "")

    def push_rank(self, clone: pathlib.Path, *, rank: str, phase: str, branch: str,
                  ident: fleet_git.Identity, tested: Callable[[str], tuple[bool, str]]) -> str:
        base = self.ref(branch) or self.ref("master")
        fails = fleet_git.gate(clone, rank=rank, phase=phase, branch=branch, base=base,
                               tested=tested, mobile=self.mobile)
        if fails:
            raise Stop("the push gate refused: " + "; ".join(fails)[:600])
        r = fleet_git.push(clone, branch, ident, run=self.host, url=self.push_url)
        if r.returncode != 0:
            raise Stop(f"the push failed: {(r.stderr or r.stdout).strip()[:300]}")
        self.update_mirror()
        head = self.git("-C", str(clone), "rev-parse", "HEAD").stdout.strip()
        self.log(f"pushed {branch} at {head[:12]} as {ident.login} ({rank})")
        return head

    def fast(self, clone: pathlib.Path) -> Callable[[str], tuple[bool, str]]:
        def tested(commit: str) -> tuple[bool, str]:
            c = self.check(clone, commit, full=False)
            return c.ok, c.why
        return tested

    def identity_for(self, issue: int, body: str, rank: str) -> fleet_git.Identity | None:
        try:
            return fleet_git.identity(body, self.identity_file)
        except fleet_git.NeedsHands as e:
            self.escalate(issue, rank, "needs-hands", str(e))
            return None

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

    def stage_scout(self, issue: int, phase: str, title: str, body: str, *,
                    resume: dict | None = None) -> str:
        ident = self.identity_for(issue, body, "scout")
        if ident is None:
            return "needs hands"
        branch, _ = self.branch_for(phase, body)
        new = branch is None
        branch = branch or f"phase-{phase}-{scout.slug(title).replace('_', '-')}"
        run = pathlib.Path(resume["run"]) if resume else self.new_run(f"scout_{phase}")
        clone = run / "clone" if resume else self.clone(run, "master" if new else branch)
        if new and not resume:
            self.git("-C", str(clone), "switch", "-q", "-c", branch)
        self.author(clone, "scout", ident if ident.is_fleet else None)
        rows = (clone / "docs" / "ROADMAP.md").read_text(encoding="utf-8").splitlines()
        row = next((ln for ln in rows if re.match(rf"\| *{re.escape(phase)} *\|", ln)), "")
        k = rows.index(row) if row in rows else 0
        handoffs = sorted((clone / "docs" / "handoffs").glob("*.md"))
        context = "\n".join(rows[max(0, k - 3):k + 3]) + (
            "\n\n" + handoffs[-1].read_text(encoding="utf-8")[:6000] if handoffs else "")
        runner = FencedRunner(self, clone, run / "run", resume=resume and resume.get("session"))
        self.log(f"issue {issue}: the Science Officer on phase {phase}, {clone}")
        try:
            written = scout.run_scout(phase, title, issue, body, row, clone=clone, run=runner,
                                      mobile=self.mobile if self.mobile.is_dir() else None,
                                      context=context, today=self.now().date())
        except RateLimited as e:
            self.pause({"stage": "scout", "issue": issue, "phase": phase, "title": title,
                        "body": body, "run": str(run), "session": e.session}, e.text, runner)
            return "rate-limited"
        self.commit(clone, written, f"Phase {phase} Step 0: the Science Officer's report", "scout")
        head = self.push_rank(clone, rank="scout", phase=phase, branch=branch, ident=ident,
                              tested=self.fast(clone))
        self.say(issue, f"{SCOUT_M} step0 commit={head[:12]} -->",
                 f"**Science Officer, phase {phase}: Step 0 written** on `{branch}` "
                 f"(`{written[0]}`). Next: the Captain writes v1.0.")
        self.set_state(issue, "step0:done")
        return f"step 0 pushed on {branch}"

    def stage_captain(self, issue: int, phase: str, body: str, branch: str, *,
                      items: list[str] | None = None, rnd: int = 0, resume: dict | None = None) -> str:
        ident = self.identity_for(issue, body, "captain")
        if ident is None:
            return "needs hands"
        run = pathlib.Path(resume["run"]) if resume else self.new_run(f"captain_{phase}")
        clone = run / "clone" if resume else self.clone(run, branch)
        self.author(clone, "captain", ident if ident.is_fleet else None)
        step0 = clone / "docs" / "phases" / "in_progress" / f"{phase}_step0.md"
        if not step0.is_file():
            raise Stop(f"no {step0.name} on {branch}: the Captain writes from Step 0")
        prompts = sorted((clone / "docs" / "prompts").glob(f"{phase}_*.txt"))
        row = next((ln for ln in (clone / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
                    .splitlines() if re.match(rf"\| *{re.escape(phase)} *\|", ln)), "")
        runner = FencedRunner(self, clone, run / "run", resume=resume and resume.get("session"))
        self.log(f"issue {issue}: the Captain on phase {phase}"
                 + (f", revision round {rnd}" if items else ""))
        try:
            calls = captain.write_plan(phase, row, prompts[0].read_text(encoding="utf-8")
                                       if prompts else "", step0.read_text(encoding="utf-8"),
                                       clone=clone, run=runner, items=items)
        except RateLimited as e:
            self.pause({"stage": "captain", "issue": issue, "phase": phase, "body": body,
                        "branch": branch, "items": items, "rnd": rnd, "run": str(run),
                        "session": e.session}, e.text, runner)
            return "rate-limited"
        subject = (f"Phase {phase} v1.0: the plan" if not items else
                   f"Phase {phase} v1.0, revised for the Executive Officer (round {rnd})")
        impl = f"docs/phases/in_progress/{phase}_implementation.md"
        self.commit(clone, [impl], subject, "captain")
        head = self.push_rank(clone, rank="captain", phase=phase, branch=branch, ident=ident,
                              tested=self.fast(clone))
        kind = "revision" if items else "v1.0"
        self.say(issue, f"{CAPTAIN_M} {kind} round={rnd} commit={head[:12]} -->",
                 f"**Captain, phase {phase}: {subject}** (`{head[:12]}`), `plan_check` P1–P8 "
                 f"passed.\n\n" + "\n".join(c.line() for c in calls))
        if items:
            self.reapply(issue, REVIEW)
        else:
            self.set_state(issue, REVIEW)
        return subject

    def stage_engineer(self, issue: int, phase: str, body: str, branch: str, *,
                       findings: str | None = None, rnd: int = 0, resume: dict | None = None) -> str:
        ident = self.identity_for(issue, body, "engineer")
        if ident is None:
            return "needs hands"
        if resume:
            run = pathlib.Path(resume["run"])
            clone = run / "clone"
        else:
            run = self.new_run(f"engineer_{phase}")
            clone = self.clone(run, branch)
            self.author(clone, "engineer", ident if ident.is_fleet else None)
            self.say(issue, f"{ENGINEER_M} started round={rnd} -->",
                     f"**Chief Engineer, phase {phase}: building**"
                     + (f", fix round {rnd} for the Red Team's findings" if findings else "")
                     + f", in a fenced clone of `{branch}`.")
            self.set_state(issue, "build:open")
        runner = FencedRunner(self, clone, run / "run", resume=resume and resume.get("session"))
        argv = engineer.session_argv(phase, issue, findings=findings, rnd=rnd)
        if resume:
            argv[2] = ("You were stopped by a usage limit. Continue the work from where you "
                       "were, and finish as the brief says.")
        self.log(f"issue {issue}: the Chief Engineer on phase {phase}, round {rnd}, {clone}")
        try:
            r, reason = runner.session(argv, watch=lambda: engineer.watch(clone, run / "run", phase))
        except RateLimited as e:
            self.pause({"stage": "engineer", "issue": issue, "phase": phase, "body": body,
                        "branch": branch, "findings": findings, "rnd": rnd, "run": str(run),
                        "session": e.session}, e.text, runner)
            return "rate-limited"
        if reason:
            self.escalate(issue, "engineer", "needs-admiral",
                          f"Chief Engineer, phase {phase}: stopped. {reason}")
            return f"stopped: {reason[:80]}"
        result = engineer.read_result(run / "run")
        if result["outcome"] == "stop":
            self.escalate(issue, "engineer", "needs-admiral",
                          f"Chief Engineer, phase {phase}: stopped ({result['kind']}). "
                          f"{result['question']}")
            return f"stopped: {result['kind']}"
        head = self.git("-C", str(clone), "rev-parse", "HEAD").stdout.strip()
        self.log(f"issue {issue}: the model-free run on {head[:12]}")
        check = self.check(clone, head, full=True)
        fails = engineer.verify(clone, phase, result, check.line if check.ok else None)
        if not check.ok:
            fails.append(f"the model-free run did not pass: {check.line or check.why}"[:400])
        if fails:
            self.escalate(issue, "engineer", "needs-admiral",
                          f"Chief Engineer, phase {phase}: the work says it is ready, and the "
                          f"checks say it is not. " + " ".join(f"({i + 1}) {f}" for i, f in
                                                              enumerate(fails))[:1500])
            return "checks failed"
        self.push_rank(clone, rank="engineer", phase=phase, branch=branch, ident=ident,
                       tested=lambda c: (check.ok and c == check.commit,
                                         "not the commit the model-free run tested"))
        pr = self.pr_for(branch)
        text = (f"{result['summary'].strip()}\n\nMission: #{issue}\n\n"
                f"The Engineer's regression of record:\n\n    {result['regression_line']}\n\n"
                f"The same commit, run again with no model (`wholetree.sh --full`, "
                f"`regression.sh`, in the fence):\n\n    {check.line}\n")
        if pr is None:
            self.gh_as(ident, "pr", "create", "--head", branch, "--base", "master", "--title",
                       f"Phase {phase}: {self.title_of(issue)}", "--body", text)
            pr = self.pr_for(branch)
        else:
            self.gh_as(ident, "pr", "comment", str(pr["number"]), "--body",
                       f"**Chief Engineer, fix round {rnd}.**\n\n{text}")
        self.say(issue, f"{ENGINEER_M} pr-ready round={rnd} pr={pr and pr['number']} -->",
                 f"**Chief Engineer, phase {phase}: pull request ready** "
                 f"({pr and pr['url']}). The model-free run: {check.line}")
        self.set_state(issue, "review:open")
        return f"PR {pr and pr['number']} ready"

    def gh_as(self, ident: fleet_git.Identity, *args: str) -> str:
        r = self.host(["gh", *args], capture_output=True, text=True, timeout=120,
                      env={**os.environ, "GH_REPO": REPO, **ident.env()})
        if r.returncode != 0:
            raise Stop(f"gh {' '.join(args[:2])} failed: {r.stderr.strip()[:200]}")
        return r.stdout

    def title_of(self, issue: int) -> str:
        t = json.loads(self.gh("issue", "view", str(issue), "--json", "title"))["title"]
        return t.split(":", 1)[-1].strip()

    def stage_red_team(self, issue: int, phase: str, body: str, branch: str, *,
                       resume: dict | None = None) -> str:
        ident = self.identity_for(issue, body, "red-team")
        if ident is None:
            return "needs hands"
        pr = self.pr_for(branch)
        if pr is None:
            raise Stop(f"no open pull request for `{branch}`")
        rnd = len(self.red_rounds(issue)) + 1
        run = pathlib.Path(resume["run"]) if resume else self.new_run(f"red_team_{phase}")
        clone = run / "clone" if resume else self.clone(run, branch)
        head = self.git("-C", str(clone), "rev-parse", "HEAD").stdout.strip()
        f9 = self.check(clone, head, full=False,
                        command=[".venv/bin/python", "scripts/check_f9_patterns.py", "--all"])
        runner = FencedRunner(self, clone, run / "run", resume=resume and resume.get("session"))
        self.log(f"issue {issue}: the Red Team on phase {phase}, round {rnd}")
        try:
            v, call = red_team.review(phase, rnd, red_team.gather(clone, phase, f9.why), clone=clone,
                                      run=runner)
        except RateLimited as e:
            self.pause({"stage": "red_team", "issue": issue, "phase": phase, "body": body,
                        "branch": branch, "run": str(run), "session": e.session}, e.text, runner)
            return "rate-limited"
        self.gh_as(ident, "pr", "comment", str(pr["number"]), "--body",
                   f"<!-- fleet-red-team-pr: verdict={v['verdict']} round={rnd} -->\n"
                   f"**Red Team, round {rnd}: {v['verdict']}**\n\nFindings:\n"
                   f"{red_team.findings_text(v)}\n\n{v['refuter_pass'].strip()}\n\n{call.line()}")
        self.say(issue, f"{RED_M} verdict={v['verdict']} round={rnd} -->",
                 f"**Red Team, phase {phase}, round {rnd}: {v['verdict']}** (PR #{pr['number']}).\n\n"
                 f"{red_team.findings_text(v)}")
        if v["verdict"] == red_team.BACK:
            if rnd >= red_team.MAX_ROUNDS:
                self.escalate(issue, "red-team", "needs-admiral",
                              f"Red Team, phase {phase}: round {rnd} of {red_team.MAX_ROUNDS} "
                              "still finds factual, citation or code defects; under K9 the "
                              "phase does not ship as it stands. The operator decides.")
                return "back, rounds exhausted"
            self.set_state(issue, "build:open")
            return f"back, round {rnd}"
        self.author(clone, "red-team-record", ident if ident.is_fleet else None)
        log = red_team.record_in_log(clone, phase, v["refuter_pass"])
        self.commit(clone, [log], f"Phase {phase}: the Red Team's refuter pass, round {rnd}",
                    "red-team-record")
        self.push_rank(clone, rank="red-team-record", phase=phase, branch=branch, ident=ident,
                       tested=self.fast(clone))
        self.set_state(issue, "review:clear")
        return f"clear, round {rnd}"

    def stage_recommend(self, issue: int, phase: str, body: str, branch: str, *,
                        resume: dict | None = None) -> str:
        ident = self.identity_for(issue, body, "captain")
        if ident is None:
            return "needs hands"
        pr = self.pr_for(branch)
        if pr is None:
            raise Stop(f"no open pull request for `{branch}`")
        run = pathlib.Path(resume["run"]) if resume else self.new_run(f"recommend_{phase}")
        clone = run / "clone" if resume else self.clone(run, branch)
        pr_text = self.gh("pr", "view", str(pr["number"]), "--json", "body", "--jq", ".body")
        clear = self.newest(issue, RED_M)
        impl = next((p for p in (clone / "docs" / "phases" / d / f"{phase}_implementation.md"
                                 for d in ("completed", "in_progress")) if p.is_file()), None)
        summary = (f"=== the pull request ===\n{pr_text}\n\n=== the Red Team's last word ===\n"
                   f"{clear[1] if clear else '(none)'}\n\n=== v1.1 ===\n"
                   f"{impl.read_text(encoding='utf-8') if impl else '(missing)'}")
        runner = FencedRunner(self, clone, run / "run", resume=resume and resume.get("session"))
        try:
            v, call = captain.recommend(phase, summary, clone=clone, run=runner)
        except RateLimited as e:
            self.pause({"stage": "recommend", "issue": issue, "phase": phase, "body": body,
                        "branch": branch, "run": str(run), "session": e.session}, e.text, runner)
            return "rate-limited"
        lines = "\n".join(v["lines"])
        self.gh_as(ident, "pr", "comment", str(pr["number"]), "--body",
                   f"<!-- fleet-captain-pr: recommendation={v['decision']} -->\n"
                   f"**The Captain's recommendation: {v['decision']}**\n\n{lines}\n\n{call.line()}")
        self.say(issue, f"{CAPTAIN_M} recommendation={v['decision']} -->",
                 f"**Captain, phase {phase}: recommends {v['decision']}** (PR #{pr['number']}).\n\n"
                 f"{lines}\n\nThe operator merges.")
        self.set_state(issue, "merge:needs-review")
        return f"recommendation: {v['decision']}"

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
        s, n, ph = paused["stage"], paused.get("issue"), paused.get("phase")
        if s == "xo":
            return self.stage_xo(n, ph, resume=paused)
        if s == "digest":
            return self.stage_digest(dt.date.fromisoformat(paused["day"]), resume=paused)
        if s == "scout":
            return self.stage_scout(n, ph, paused["title"], paused["body"], resume=paused)
        if s == "captain":
            return self.stage_captain(n, ph, paused["body"], paused["branch"],
                                      items=paused.get("items"), rnd=paused.get("rnd", 0),
                                      resume=paused)
        if s == "engineer":
            return self.stage_engineer(n, ph, paused["body"], paused["branch"],
                                       findings=paused.get("findings"), rnd=paused.get("rnd", 0),
                                       resume=paused)
        if s == "red_team":
            return self.stage_red_team(n, ph, paused["body"], paused["branch"], resume=paused)
        return self.stage_recommend(n, ph, paused["body"], paused["branch"], resume=paused)

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

    def next_stage(self, n: int, phase: str, labels: set[str], body: str, title: str
                   ) -> tuple[str, Callable[[], str]] | None:
        """The one stage the labels ask for on this issue, latest state first."""
        def branch() -> str:
            b, why = self.branch_for(phase, body)
            if b is None:
                raise Stop(why)
            return b

        if "review:clear" in labels and self.due_for(n, "review:clear",
                                                     self.markers(CAPTAIN_M, "captain")):
            return "captain", lambda: self.stage_recommend(n, phase, body, branch())
        if "review:open" in labels and self.due_for(n, "review:open",
                                                    self.markers(RED_M, "red-team")):
            return "red-team", lambda: self.stage_red_team(n, phase, body, branch())
        if "build:open" in labels:
            back, mine = self.newest(n, f"{RED_M} verdict=back"), self.newest(n, ENGINEER_M)
            stop = self.newest(n, f"{MARKER} stopped rank=engineer")
            latest_mine = max([t for t in (mine, stop) if t], default=None)
            if back and (latest_mine is None or back[0] > latest_mine[0]):
                rnd = sum(1 for v, _ in self.red_rounds(n) if v == "back")
                return "engineer", lambda: self.stage_engineer(
                    n, phase, body, branch(), findings=back[1], rnd=rnd)
        if "plan:approved" in labels and self.due_for(n, "plan:approved",
                                                      self.markers(ENGINEER_M, "engineer")):
            return "engineer", lambda: self.stage_engineer(n, phase, body, branch())
        if REVIEW in labels:
            if self.due(n):
                return "xo", lambda: self.stage_xo(n, phase, branch=branch())
            verdict = self.newest(n, xo.MARKER)
            mine = max([t for t in (self.newest(n, CAPTAIN_M),
                                    self.newest(n, f"{MARKER} stopped rank=captain")) if t],
                       default=None)
            m = _XO.match(verdict[1]) if verdict else None
            if m and m.group(1) == xo.BACK and (mine is None or verdict[0] > mine[0]):
                items = [ln[2:] for ln in verdict[1].splitlines() if ln.startswith("- ")]
                rnd = sum(1 for c in self.comments(n)
                          if (x := _XO.match(c.get("body", ""))) and x.group(1) == xo.BACK)
                return "captain", lambda: self.stage_captain(n, phase, body, branch(),
                                                             items=items or ["see the XO's verdict"],
                                                             rnd=rnd)
        if "step0:done" in labels and self.due_for(n, "step0:done",
                                                   self.markers(CAPTAIN_M, "captain")):
            return "captain", lambda: self.stage_captain(n, phase, body, branch())
        if not labels & set(STATE_LABELS) and "mission" in labels and self.due_for(
                n, "mission", self.markers(SCOUT_M, "scout")):
            return "scout", lambda: self.stage_scout(n, phase, title, body)
        return None

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
            try:
                self.log(f"resume: {self.resume(paused)}")
            except Stop as e:
                if paused.get("issue") is not None:
                    self.comment(paused["issue"], f"stopped rank={paused['stage']}",
                                 f"**Fleet dispatcher: the resumed stage could not finish, label "
                                 f"unchanged.** {e}")
                self.log(f"resume stopped: {e}")
        rows = self.master_rows()
        issues = json.loads(self.gh("issue", "list", "--state", "open", "--limit", "200",
                                    "--json", "number,title,body,labels"))
        for issue in issues:
            if self.load().get("paused"):
                return
            n, labels = issue["number"], {x["name"] for x in issue.get("labels", [])}
            if labels & set(OPERATOR) or not labels & {"mission", *STATE_LABELS}:
                continue
            m = re.match(r"Phase (\d{2,3}[A-Z]?)\b", issue["title"])
            if not m:
                if REVIEW in labels and self.due(n):
                    why = f"the title {issue['title']!r} names no `Phase <N>`"
                    self.comment(n, "stopped", f"**Fleet dispatcher: the Executive Officer did not "
                                 f"run, label unchanged.** {why}. Apply `{REVIEW}` again once fixed.")
                    self.log(f"issue {n}: not run: {why}")
                continue
            phase = m.group(1)
            if rows.get(phase) != roadmap_check.ACTIVE:
                if (n, phase) not in self._skipped:
                    self._skipped.add((n, phase))
                    self.log(f"issue {n}: phase {phase}'s row on master is "
                             f"{rows.get(phase, 'missing')!r}, not {roadmap_check.ACTIVE}: no stage")
                continue
            rank = "xo" if REVIEW in labels else "stage"
            try:
                chosen = self.next_stage(n, phase, labels, issue.get("body", ""), issue["title"])
                if chosen is None:
                    continue
                rank, go = chosen
                self.log(f"issue {n}: {go()}")
            except Stop as e:
                if rank == "xo":
                    self.comment(n, "stopped", f"**Fleet dispatcher: the Executive Officer "
                                 f"{'did not run' if 'branch' in str(e) else 'could not finish'}"
                                 f", label unchanged.** {e}. Apply `{REVIEW}` again once fixed.")
                else:
                    self.comment(n, f"stopped rank={rank}", f"**Fleet dispatcher: the {rank} "
                                 f"could not finish, label unchanged.** {e}")
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
