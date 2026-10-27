#!/usr/bin/env python3
"""The fleet's dispatcher: polls the labels, runs each rank, fenced.

    dispatcher.py run [--interval 300] [--sweep-hours 24]   the loop (the unit's command)
    dispatcher.py once [--sweep-hours 24]                   one cycle
    dispatcher.py usage                                     the parsed /usage lines
    dispatcher.py recover --dry-run                         what the search on start would do

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
  `merge:needs-review`      the Quartermaster (`quartermaster.py`), in shadow: its
                            verdict on the PR and in the digest; no label moved

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

**A stage a restart cuts off is resumed** (Phase 390, F219). Each stage
keeps a journal (`journal.py`) beside its clone, written before it starts
and after each step. On every start, before the first cycle, `recover`
resumes each unfinished journal from its run directory: finished model calls
and model-free runs are replayed, the cut call goes on with `--resume` and
the session its transcript names, and each GitHub write is checked for
before it is made. A `started` marker left open with nothing to resume from,
or a stage whose issue has moved on, gets a stop comment; the label stays.

**Free space is part of the method** (Phase 390, F221). The service hands
Ubuntu's freed blocks back to Windows (`fstrim`, its one sudoers line, the
disk image sparse) on a timer, at each merge and at each close-out. Each
reclaim logs the free space on C: and in Ubuntu before and after. No new
model stage or model-free run starts below either floor. Below a floor it
reclaims first. If it is still below, it holds the stage: the label stays,
a comment says why, and `needs-hands` is added.

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
import signal
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
sys.path.insert(0, str(HERE.parent / "finding"))
import captain  # noqa: E402
import closeout_check  # noqa: E402
import finding_check  # noqa: E402
import engineer  # noqa: E402
import fleet_git  # noqa: E402
import journal  # noqa: E402
import plan_order  # noqa: E402
import quartermaster  # noqa: E402
import red_team  # noqa: E402
import roadmap_check  # noqa: E402
import scout  # noqa: E402
import xo  # noqa: E402
import yeoman  # noqa: E402
from labels import LABELS  # noqa: E402
from rank_call import FABLE, OPUS, Runner, Stop  # noqa: E402

REPO = "Kubanjaze/moto-diag"
FOLLOWUPS = "docs/FOLLOWUPS.md"
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
#: The model-free run's limit. The operator's number, 2026-10-27 (K51):
#: "CHECK_TIMEOUT_S=5400 (measured regressions 24-38 min; #28 hit 3600 under load)".
CHECK_TIMEOUT_S = 5400
#: What a stage's `run/tmp` keeps when it is deleted (Phase 392, F226):
#: `tests/support/worker_loss.py`'s folders, which rule 6 reads first after
#: a lost worker.
WORKER_LOSS_PREFIX = "motodiag_worker_loss_"
#: Free space (Phase 390, F221): no new model stage or model-free run below
#: either floor, in GB, after a reclaim. The operator's numbers, 2026-10-25:
#: "50 GB on each", "every 3 hours".
SPACE_FLOOR_GB = {"C:": 50, "Ubuntu": 50}
RECLAIM_HOURS = 3.0
#: Where each floor is read on the home desktop: Windows' C: through WSL's mount.
DISKS = {"C:": pathlib.Path("/mnt/c"), "Ubuntu": pathlib.Path("/")}
#: The one command `ops/desktop/install_fstrim_sudoers.sh` allows without a
#: password: Ubuntu's freed blocks handed back through the sparse disk image.
FSTRIM = ["sudo", "-n", "/usr/sbin/fstrim", "-v", "/"]

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
    "merge:needs-review": "the Admiral, who merges (the Quartermaster, in shadow, gives its "
                          "verdict first and merges nothing)",
    "needs-admiral": "the Admiral", "needs-hands": "the Admiral",
    "merged": "whoever merged, to close the issue",
}
MARKER = "<!-- fleet-dispatcher:"
SWEEP_MARKER = "<!-- fleet-sweep:"
SCOUT_M, CAPTAIN_M = "<!-- fleet-scout:", "<!-- fleet-captain:"
ENGINEER_M, RED_M = "<!-- fleet-engineer:", "<!-- fleet-red-team:"
QM_M, QM_PR_M = "<!-- fleet-quartermaster:", "<!-- fleet-quartermaster-pr:"
QM = "merge:needs-review"
#: A comment by a rank on an issue: the XO's verdict, the XO's stop, ours (388).
RANK_COMMENT = (xo.MARKER, "Executive Officer, phase", MARKER)
#: The XO's own comments (`xo.py` writes them, with no ` run=`).
XO_OWN = (xo.MARKER, "Executive Officer, phase")
#: A stage's first comment (Phase 390). Its own prefix: no due rule reads it,
#: so a stage's start never makes its own label look handled.
STARTED_M = "<!-- fleet-started:"
#: A hold for free space. Its own prefix, read by no due rule: once the
#: operator takes `needs-hands` off, the stage it held is due again.
SPACE_M = "<!-- fleet-space:"
#: A stop the record answered (Phase 392, K50): read by the Engineer's due rule.
ANSWER_M = "<!-- fleet-answered:"
#: The next mission's own marks (Phase 392, K48, K49): on the issue it opens,
#: and its question to the operator when the plan says the phase needs them.
NEXT_M = "<!-- fleet-next:"
#: Every rank's comment: one stage runs at a time, so a later one ends an earlier stage.
RANK_PREFIXES = (STARTED_M, SCOUT_M, CAPTAIN_M, ENGINEER_M, RED_M, QM_M, *RANK_COMMENT)
_STARTED = re.compile(r"^<!-- fleet-started: rank=(\S+) run=(\S+) -->")
#: The Engineer's own `started` marker; before Phase 390 it had no ` run=`.
_ENG_STARTED = re.compile(r"^<!-- fleet-engineer: started round=\d+(?: run=(\S+))? -->")
#: The rank each journal's stage is said as, in markers and stop comments.
STAGE_RANK = {"scout": "scout", "captain": "captain", "xo": "xo", "engineer": "engineer",
              "recheck": "engineer",
              "red_team": "red-team", "recommend": "captain", "quartermaster": "quartermaster",
              "digest": "digest", "next": "next"}
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


class LowSpace(Stop):
    """Free space below a floor after a reclaim (F221): the stage is held for
    the operator (`needs-hands`), its label where it was."""


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
    this stage's clone, `gh` here with GH_REPO, anything else here.

    With a journal (Phase 390) it replays: the k-th model call of a resumed
    stage that finished returns its saved output; the one that was cut runs
    again with `--resume` and the session its transcript names."""

    def __init__(self, fleet: Fleet, clone: pathlib.Path, run_dir: pathlib.Path,
                 journal: journal.Journal | None = None):
        self.fleet, self.clone, self.run_dir, self.journal = fleet, clone, run_dir, journal
        self.k = 0

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
        return self.fleet.usage()

    @property
    def resumed(self) -> bool:
        return self.journal is not None and self.journal.resumed

    def gate_model(self, model: str | None) -> None:
        """No new Opus or Fable stage over its ceiling; a resumed one is not new."""
        if self.resumed or model not in (OPUS, FABLE):
            return
        usage = self.fleet.usage()
        why = opus_refusal(usage) if model == OPUS else fable_refusal(usage)
        if why:
            raise Stop(f"no new {'Opus' if model == OPUS else 'Fable'} stage: {why}")

    def transcripts(self) -> list[pathlib.Path]:
        return transcripts(self.run_dir)

    def replay(self, cmd: list[str]) -> tuple[int, dict | None, str | None]:
        """(k, the journal's finished entry or None, the session to resume or
        None) for the next model call, entering it in the journal."""
        k, self.k = self.k, self.k + 1
        j = self.journal
        if j is None:
            return k, None, None
        key, entry = journal.call_key(cmd), j.call(k)
        if entry is not None and entry["key"] not in (None, key):
            self.fleet.log(f"replay ended at model call {k}: its command differs from the "
                           f"journal's; this call and the rest run fresh")
            entry = None
        if entry is None:
            j.begin_call(k, key, [p.stem for p in self.transcripts()])
            return k, None, None
        if entry.get("done"):
            return k, entry, None
        session = cut_session(entry, self.run_dir)
        j.update_call(k, key=key, session=session)
        return k, None, session

    def __call__(self, cmd, **kw):
        cmd = list(cmd)
        if cmd[0] == "gh":
            return self.fleet.gh_run(cmd, **kw)
        if cmd[0] != "claude":
            return self.fleet.host(cmd, **kw)
        cwd = kw.get("cwd")
        if cwd is not None and pathlib.Path(cwd).resolve() != self.clone.resolve():
            raise Stop(f"a model call from {cwd}, outside the stage's clone")
        k, done, session = self.replay(cmd)
        if done is not None:
            d = json.loads(done["stdout"])
            d["fleet_replayed"] = True
            return subprocess.CompletedProcess(cmd, done["rc"], json.dumps(d), done["stderr"])
        self.gate_model(cmd[cmd.index("--model") + 1] if "--model" in cmd else None)
        if session:
            cmd = [cmd[0], "--resume", session, *cmd[1:]]
        r = self.fenced(cmd, timeout=kw.get("timeout", 1800))
        limited = rate_limit(r)
        if limited:
            if self.journal is not None:
                self.journal.update_call(k, session=limited[0] or session)
            raise RateLimited(limited[0] or session, limited[1])
        if self.journal is not None:
            try:
                sid = json.loads(r.stdout).get("session_id")
            except (ValueError, AttributeError):
                sid = None
            self.journal.update_call(k, done=True, rc=r.returncode, stdout=r.stdout or "{}",
                                     stderr=r.stderr or "", session=sid or session)
        return r

    def session(self, cmd: list[str], *, watch: Callable[[], str | None],
                timeout: int = engineer.SESSION_TIMEOUT_S, every: int = engineer.WATCH_EVERY_S
                ) -> tuple[subprocess.CompletedProcess, str | None]:
        """A long call (the Engineer's), watched from outside the model: every
        `every` seconds `watch()` may name a reason to end it. Returns the
        result and that reason (None when it ended by itself). Resumed, a
        finished session is read back from its files; a cut one goes on with
        `engineer.CONTINUE`."""
        out, err = self.run_dir / "session.json", self.run_dir / "session.err"
        k, done, session = self.replay(cmd)
        if done is None and self.resumed and session_ended(out):
            done = {"rc": 0, "reason": None}
            self.journal.update_call(k, done=True, rc=0, reason=None)
        if done is not None:
            r = subprocess.CompletedProcess(
                cmd, done["rc"], out.read_text(errors="replace"),
                err.read_text(errors="replace") if err.is_file() else "")
            limited = None if done.get("reason") else rate_limit(r)
            if limited:
                raise RateLimited(limited[0] or session, limited[1])
            return r, done.get("reason")
        self.gate_model(cmd[cmd.index("--model") + 1] if "--model" in cmd else None)
        if session:
            cmd = [cmd[0], "--resume", session, cmd[1], engineer.CONTINUE, *cmd[3:]]
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
            if self.journal is not None:
                self.journal.update_call(k, session=limited[0] or session)
            raise RateLimited(limited[0] or session, limited[1])
        if self.journal is not None:
            self.journal.update_call(k, done=True, rc=proc.returncode, reason=reason)
        return r, reason


def transcripts(run_dir: pathlib.Path) -> list[pathlib.Path]:
    """The model's sessions in a run, oldest first: a killed call prints
    nothing, and its id is its transcript's name (390, S0-5)."""
    return sorted((run_dir / "claude" / "projects").glob("*/*.jsonl"),
                  key=lambda p: p.stat().st_mtime)


def nothing_back(disk: str, before: float | None, after: float | None, trimmed: str) -> str:
    """Said plainly when a reclaim gave Windows nothing (Phase 392, F226): the
    disk image is not sparse since 2026-10-26, so a trim frees space inside
    Ubuntu only, and "C: X -> X" beside a large trim is not a reclaim."""
    if disk != "C:" or before is None or after is None or trimmed.startswith(("failed", "not")):
        return ""
    return (" (nothing came back to Windows: the disk image is not sparse, so the trim freed "
            "space inside Ubuntu only)") if after - before < 0.1 else ""


def row_branch(phase: str) -> str:
    """The next mission's row branch: its own, so the work branch the issue
    names is made from master after the merge (the push gate's G1 shape)."""
    return f"phase-{phase}-row"


def mark_row_active(clone: pathlib.Path, phase: str) -> str:
    """The phase's ROADMAP row with its status cell 🚧 and nothing else changed."""
    path = clone / fleet_git.ROADMAP
    lines = path.read_text(encoding="utf-8").split("\n")
    hits = [k for k, ln in enumerate(lines) if re.match(rf"\| {re.escape(phase)} \|", ln)]
    if len(hits) != 1:
        raise Stop(f"phase {phase} has {len(hits)} ROADMAP rows, not one")
    cells = lines[hits[0]].split("|")
    cells[3] = f" {roadmap_check.ACTIVE} "
    lines[hits[0]] = "|".join(cells)
    path.write_text("\n".join(lines), encoding="utf-8")
    return fleet_git.ROADMAP


def mission_body(e: plan_order.Entry, work: str, cite: str) -> str:
    """The next mission's issue: what the Science Officer saves as the prompt."""
    return (f"**The plan of record's next mission**, opened by the fleet (Phase 392).\n\n"
            f"The plan of record puts phase {e.phase} next ('Next, in order' #{e.n}): "
            f"{e.line()}\n\n{cite}\n\nThe work branch is `{work}`: the Science Officer makes "
            f"it from master once this phase's row is 🚧 there, which the row's pull request "
            f"does when the operator merges it.\n\n{NEXT_M} phase={e.phase} -->")


def ask_text(e: plan_order.Entry, label: str) -> str:
    """The operator's question, plain English, the plan's entry quoted."""
    return (f"**Phase {e.phase} is next in the plan, and the plan says it needs you first.**\n\n"
            f"What it needs, in the plan of record's words: {e.needs}\n\n"
            f"The plan's entry: {e.line()}\n\n"
            f"When that is done, take the `{label}` label off this issue. The fleet then opens "
            f"one pull request that starts the phase, for you to merge.")


def row_pr_body(e: plan_order.Entry, issue: int, title: str, cite: str) -> str:
    """The row PR's body: plain English, one click or one paste block."""
    return (f"**Merging this starts {title}.** The plan of record puts it next "
            f"('Next, in order' #{e.n}), and the fleet's mission is #{issue}.\n\n"
            f"It changes one line, the phase's row in `docs/ROADMAP.md`: its status becomes "
            f"🚧. Nothing else.\n\n{cite}\n\n"
            f"To start it, merge this pull request on GitHub (the master rule lets your "
            f"account through). Or, in a terminal on any computer where `gh` is signed in as "
            f"you, paste:\n\n```\ngh pr merge {row_branch(e.phase)} -R {REPO} --merge --admin && "
            f"echo ALL GOOD || echo SOMETHING IS OFF\n```\n\n"
            f"After the merge the fleet begins Step 0 by itself at its next cycle.")


def clean_tmp(run: pathlib.Path) -> list[str]:
    """Delete a finished run's temporary files (Phase 392, F226; the operator's
    K45: "delete each run's temp files"): everything in `run/tmp` but the
    worker-loss folders. Returns what was kept."""
    tmp = run / "run" / "tmp"
    if not tmp.is_dir():
        return []
    kept = []
    for p in tmp.iterdir():
        if p.name.startswith(WORKER_LOSS_PREFIX):
            kept.append(p.name)
        elif p.is_dir() and not p.is_symlink():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink(missing_ok=True)
    return kept


def run_group(argv: list[str], *, timeout: float, **kw) -> subprocess.CompletedProcess:
    """`subprocess.run`, in a session of its own: a run past `timeout` has its
    whole process group killed, then `TimeoutExpired` is raised with what it
    printed (Phase 392, F225: before, only the direct child was killed)."""
    kw.pop("capture_output", None)
    with subprocess.Popen(argv, start_new_session=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, **kw) as p:
        try:
            out, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, err = p.communicate()
            raise subprocess.TimeoutExpired(argv, timeout, out, err) from None
        return subprocess.CompletedProcess(argv, p.returncode, out, err)


def cut_session(entry: dict, run_dir: pathlib.Path) -> str | None:
    """The session of a call that did not end: the journal's, or the newest
    transcript that was not there when the call began (`--resume` keeps the
    id and its file, S0-5). None: the call was cut before it had one."""
    return entry.get("session") or next(
        (p.stem for p in reversed(transcripts(run_dir)) if p.stem not in entry["known"]), None)


def session_ended(out: pathlib.Path) -> bool:
    """The Engineer's session wrote its final JSON: it ended, whatever came after."""
    try:
        lines = out.read_text(errors="replace").strip().splitlines()
        return bool(lines) and json.loads(lines[-1]).get("type") == "result"
    except (OSError, ValueError, AttributeError):
        return False


# --------------------------------------------------------- model-free runs
@dataclass
class Check:
    """A run no model touched: its verdict, and the regression line it printed."""
    ok: bool
    commit: str
    line: str | None = None
    why: str = ""
    #: A command run's whole output (Phase 391: `verify_phase.sh`, read section by section).
    out: str = ""


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
                 check: Callable[..., Check] | None = None, sleep: Callable[[float], None] = time.sleep,
                 disks: dict[str, pathlib.Path] | None = None, trim: list[str] | None = None,
                 disk_usage: Callable[[pathlib.Path], tuple] = shutil.disk_usage,
                 group_run: Callable[..., subprocess.CompletedProcess] = run_group):
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
        self.group_run = group_run
        #: Free space is watched only where `main` names the disks (the desktop).
        self.disks, self.trim, self.disk_usage = disks or {}, trim, disk_usage
        self._skipped: set[tuple[int, str]] = set()
        #: The running stage's journal (one stage runs at a time).
        self.journal: journal.Journal | None = None

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

    # ---- free space (Phase 390, F221)
    def free_gb(self) -> dict[str, float | None]:
        """Each watched disk's free space in GB; None where it cannot be read."""
        free: dict[str, float | None] = {}
        for name, path in self.disks.items():
            try:
                free[name] = round(self.disk_usage(path)[2] / 1e9, 1)
            except OSError:
                free[name] = None
        return free

    @staticmethod
    def below(free: dict[str, float | None]) -> list[str]:
        return [f"{name} {'cannot be read' if gb is None else f'has {gb} GB free'} "
                f"(floor {SPACE_FLOOR_GB[name]} GB)"
                for name, gb in free.items() if gb is None or gb < SPACE_FLOOR_GB[name]]

    def reclaim(self, why: str, *, record: bool = True) -> str:
        """`fstrim` through its one sudoers line, which hands Ubuntu's freed
        blocks back to Windows; free space on each disk before and after,
        logged, and (`record`) the time kept for the timer. A failed trim is
        said, not raised."""
        before = self.free_gb()
        if not self.trim:
            trimmed = "not set up"
        else:
            try:
                r = self.host(self.trim, capture_output=True, text=True, timeout=900,
                              stdin=subprocess.DEVNULL)
                said = " ".join(((r.stdout or "") + (r.stderr or "")).split())[:200]
                trimmed = said if r.returncode == 0 else f"failed (exit {r.returncode}): {said}"
            except (OSError, subprocess.TimeoutExpired) as e:
                trimmed = f"failed: {e}"
        after = self.free_gb()
        line = "; ".join(f"{name} {before[name]} -> {after[name]} GB free"
                         + nothing_back(name, before[name], after[name], trimmed)
                         for name in self.disks) + f"; fstrim: {trimmed}"
        self.log(f"reclaim ({why}): {line}")
        if not record:
            return line
        state = self.load()
        state["last_reclaim"] = self.now().isoformat(timespec="seconds")
        self.save(state)
        return line

    def reclaim_due(self) -> bool:
        last = self.load().get("last_reclaim")
        return bool(self.disks) and (last is None or self.now() - _time(last)
                                     >= dt.timedelta(hours=RECLAIM_HOURS))

    def space_refusal(self) -> str | None:
        """Why no new model stage or model-free run may start: a disk below
        its floor even after a reclaim, or one that cannot be read."""
        if not self.disks or not self.below(self.free_gb()):
            return None
        self.reclaim("below the floor")
        low = self.below(self.free_gb())
        return "free space is below the floor after a reclaim: " + "; ".join(low) if low else None

    def hold_for_space(self, n: int | None, rank: str, why: str) -> None:
        """A stage held for free space: said on its issue, `needs-hands`
        added, its label left where it was (the digest has no issue: its
        hold is the log line, and the day is tried again next cycle)."""
        if n is None:
            return
        marker = self.tag(f"{SPACE_M} rank={rank} -->")
        self.step("space", lambda: self.say(
            n, marker, f"**Fleet dispatcher: the {rank} is held, label unchanged.** {why}. "
                       "Free some space on the home desktop, then take `needs-hands` off: the "
                       "fleet reclaims and checks again before it goes on."),
                  lambda: self.has_comment(n, marker))
        self.step("space-label", lambda: self.gh("issue", "edit", str(n), "--add-label",
                                                 "needs-hands"),
                  lambda: "needs-hands" in self.labels_of(n))
        self.log(f"issue {n}: held ({rank}): {why}")

    def usage(self) -> dict | None:
        """The 5-hour and weekly figures, read on the operator's own sign-in,
        outside the fence: `claude -p "/usage"`, a slash command with no
        model call (0 turns, no cost). The fleet's setup-token cannot read
        them (F218: inside the fence `/usage` prints a cost summary, and
        `api/oauth/usage` answers it 403); the operator, 2026-10-25: "Use my
        sign-in to read (Recommended)". The sign-in never enters the fence;
        the token the fleet runs on plays no part here."""
        env = {k: v for k, v in os.environ.items()
               if k not in ("CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR",
                            "ANTHROPIC_API_KEY")}
        self.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            r = self.host(["claude", "-p", "/usage", "--output-format", "json",
                           "--strict-mcp-config"], capture_output=True, text=True, timeout=300,
                          cwd=self.state_dir, env=env, stdin=subprocess.DEVNULL)
            text = str(json.loads(r.stdout).get("result") or "")
        except (ValueError, AttributeError, OSError, subprocess.SubprocessError):
            return None
        return parse_usage(text, self.now()) or None

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
        kind = self.tag(f"{label} rank={rank} -->")[:-4]
        self.step("escalate", lambda: self.comment(
            issue, kind, f"**{text.strip()}**\n\nThe fleet leaves this issue alone until the "
                         f"operator takes `{label}` off."),
            lambda: (label in self.labels_of(issue)
                     or self.has_comment(issue, f"{MARKER} {kind} -->")))
        self.step("escalate-label", lambda: self.gh("issue", "edit", str(issue), "--add-label",
                                                    label),
                  lambda: label in self.labels_of(issue))
        self.log(f"issue {issue}: {label} ({rank}): {text[:200]}")

    # ---- GitHub reads
    def label_events(self, issue: int) -> list[dict]:
        out = self.gh("api", "--paginate", f"repos/{REPO}/issues/{issue}/events", "--jq",
                      '.[] | select(.event == "labeled") | {label: .label.name, at: .created_at}')
        return [json.loads(ln) for ln in out.splitlines() if ln.strip()]

    def comments(self, issue: int) -> list[dict]:
        """The issue's comments a rank may read (Phase 392, F223): the fleet's
        account's, and the operator's on a trial issue. Every due rule, round
        count, marker search and model brief reads through this."""
        data = json.loads(self.gh("issue", "view", str(issue), "--json", "comments,body"))
        return fleet_git.from_trusted(data["comments"],
                                      fleet_git.trusted_authors(data.get("body", ""),
                                                                self.identity_file))

    def own_logins(self) -> set[str]:
        """Whose comment on a pull request is one of ours: the fleet's and the
        operator's (in whose name the fleet comments without an account)."""
        return fleet_git.trusted_authors(fleet_git.TRIAL_MARKER, self.identity_file)

    def issues_open(self) -> list[dict]:
        """The open issues a rank may work: opened by the fleet's account or
        the operator (F223); a third account's is logged once and left."""
        out = []
        for i in json.loads(self.gh("issue", "list", "--state", "open", "--limit", "200",
                                    "--json", "number,title,body,labels,author")):
            if fleet_git.opened_by_trusted(i, self.identity_file):
                out.append(i)
            elif (i["number"], "author") not in self._skipped:
                self._skipped.add((i["number"], "author"))
                who = (i.get("author") or {}).get("login", "?")
                self.log(f"issue {i['number']}: opened by {who}, not the fleet or the operator: "
                         "no stage")
        return out

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

    def new_run(self, name: str, record: dict | None = None) -> pathlib.Path:
        """A run directory; with a stage's record, its journal written
        before anything else happens in it (Phase 390)."""
        stamp = self.now().strftime("%Y%m%d_%H%M%S")
        run = self.runs / f"{stamp}_{name}"
        n = 1
        while run.exists():
            n += 1
            run = self.runs / f"{stamp}_{name}_{n}"
        (run / "run").mkdir(parents=True)
        if record is not None:
            journal.Journal.create(run, record, self.now())
        return run

    def begin(self, name: str, record: dict, resume: dict | None) -> tuple[pathlib.Path,
                                                                           journal.Journal]:
        """The stage's run directory and journal: new, or the resumed one's."""
        if resume:
            run = pathlib.Path(resume["run"])
            j = journal.Journal.load(run) or journal.Journal.create(run, resume, self.now())
            j.resumed = True
        else:
            run = self.new_run(name, record)
            j = journal.Journal.load(run)
        self.journal = j
        return run, j

    def finish(self, outcome: str) -> None:
        """The running stage is over, unless it paused (its journal stays open)."""
        j, self.journal = self.journal, None
        if j is not None and outcome != "rate-limited":
            j.end(outcome, self.now())
            if not (j.run / journal.HELD).is_file():
                clean_tmp(j.run)       # F226; a held run keeps its own until released

    def step(self, name: str, do: Callable[[], object],
             done: Callable[[], object] | None = None):
        """One commit, push or GitHub write, made once. Resumed, a step the
        journal lacks asks `done()` first: a kill can fall between the write
        and its record."""
        j = self.journal
        if j is None:
            return do()
        if j.done(name):
            return j.value(name)
        if j.resumed and done is not None:
            found = done()
            if found:
                j.mark(name, found)
                return found
        value = do()
        j.mark(name, True if value is None else value)
        return value

    def tag(self, marker: str) -> str:
        """A marker with the running stage's run: `<!-- x: … run=<run> -->`."""
        if self.journal is None:
            return marker
        return marker.replace(" -->", f" run={self.journal.run.name} -->", 1)

    def has_comment(self, issue: int, marker: str) -> bool:
        return any(c.get("body", "").lstrip().startswith(marker) for c in self.comments(issue))

    def pr_has_comment(self, pr: int, marker: str) -> bool:
        bodies = fleet_git.from_trusted(json.loads(self.gh("pr", "view", str(pr), "--json",
                                                           "comments"))["comments"],
                                        self.own_logins())
        return any(marker in c.get("body", "") for c in bodies)

    def stage_clone(self, run: pathlib.Path, branch: str, *, new_branch: str | None = None
                    ) -> pathlib.Path:
        """The stage's clone, once: a clone cut half way is made again."""
        def do() -> dict:
            shutil.rmtree(run / "clone", ignore_errors=True)
            clone = self.clone(run, branch)
            if new_branch:
                self.git("-C", str(clone), "switch", "-q", "-c", new_branch)
            return {"base": self.git("-C", str(clone), "rev-parse", "HEAD").stdout.strip()}
        self.step("clone", do)
        return run / "clone"

    def committed(self, clone: pathlib.Path, subject: str) -> str | None:
        """HEAD, when it is a commit past the clone's base with this subject."""
        base = (self.journal.value("clone") or {}).get("base") if self.journal else None
        head = self.git("-C", str(clone), "rev-parse", "HEAD").stdout.strip()
        subj = self.git("-C", str(clone), "log", "-1", "--format=%s").stdout.strip()
        return head if head != base and subj == subject else None

    def commit_once(self, clone: pathlib.Path, paths: Callable[[], list[str]], subject: str,
                    rank: str) -> str:
        return self.step("commit", lambda: self.commit(clone, paths(), subject, rank),
                         lambda: self.committed(clone, subject))

    def pushed(self, branch: str, head: str) -> str | None:
        self.update_mirror()
        return head if self.ref(branch) == head else None

    def push_once(self, clone: pathlib.Path, head: str, **kw) -> str:
        return self.step("push", lambda: self.push_rank(clone, **kw),
                         lambda: self.pushed(kw["branch"], head))

    def say_once(self, issue: int, marker: str, text: str, step: str = "marker") -> None:
        marker = self.tag(marker)
        self.step(step, lambda: self.say(issue, marker, text),
                  lambda: self.has_comment(issue, marker))

    def label_once(self, issue: int, label: str, step: str = "label") -> None:
        self.step(step, lambda: self.set_state(issue, label),
                  lambda: label in self.labels_of(issue))

    def started(self, issue: int, rank: str, text: str) -> None:
        """Every rank's first GitHub step: what the search on start reads."""
        self.say_once(issue, f"{STARTED_M} rank={rank} -->", text, step="started")

    def checked(self, clone: pathlib.Path, commit: str, *, full: bool,
                command: list[str] | None = None) -> Check:
        """A model-free run, once per commit and kind in this stage: a finished
        one is read from the journal; an unfinished one runs again."""
        key = f"{commit}|{'full' if full else 'fast'}|{' '.join(command or [])}"
        saved = self.journal.check(key) if self.journal else None
        if saved is not None:
            return Check(**saved)
        why = self.space_refusal()
        if why:
            raise LowSpace(f"no model-free run: {why}")
        c = self.check(clone, commit, full=full, command=command)
        if self.journal is not None:
            self.journal.put_check(key, {"ok": c.ok, "commit": c.commit, "line": c.line,
                                         "why": c.why, "out": c.out})
        return c

    def clone(self, run: pathlib.Path, branch: str) -> pathlib.Path:
        r = self.git("clone", "-q", "--no-hardlinks", "--branch", branch, str(self.mirror),
                     str(run / "clone"))
        if r.returncode != 0:
            raise Stop(f"the stage clone of {branch} failed: {r.stderr.strip()[:200]}")
        # A local master, as every checkout a plan is written for has one: a
        # `--branch` clone has only that one head, so a plan's `git diff
        # master` could never run in it (Phase 389, bug fix #3: the XO's
        # round-2 item on 389A).
        if branch != "master":
            self.git("-C", str(run / "clone"), "branch", "-q", "--track", "master", "origin/master")
        return run / "clone"

    def prune_runs(self, keep_also: set[str]) -> None:
        """The newest KEEP_RUNS, the paused run, and every unfinished run
        (Phase 390: a run whose journal has no `ended` is what a resume needs)."""
        if not self.runs.is_dir():
            return
        runs = sorted(p for p in self.runs.iterdir() if p.is_dir())
        for p in runs[:-KEEP_RUNS]:
            j = journal.Journal.load(p)
            if j is None and (p / journal.FILE).is_file():
                continue                      # unreadable: the search on start names it
            if (p / journal.HELD).is_file():
                continue                      # held for the operator (F220)
            if str(p) not in keep_also and not (j and j.unfinished):
                shutil.rmtree(p, ignore_errors=True)
        # The kept runs' temporary files, once each has ended (F226): a stage
        # with an ended journal, or a check run that wrote its result. Held,
        # paused and unfinished runs keep theirs; so does an unreadable one.
        for p in sorted(p for p in self.runs.iterdir() if p.is_dir()):
            if str(p) in keep_also or (p / journal.HELD).is_file():
                continue
            j = journal.Journal.load(p)
            if j is not None and not j.unfinished:
                clean_tmp(p)
            elif not (p / journal.FILE).exists() and (p / "run" / "check.txt").is_file():
                clean_tmp(p)

    # ---- commits, checks, pushes
    def author(self, clone: pathlib.Path, rank: str, ident: fleet_git.Identity | None) -> None:
        name, email = (ident or fleet_git.Identity("operator", None)).author(rank)
        for k, v in (("user.name", name), ("user.email", email)):
            self.git("-C", str(clone), "config", k, v)

    def commit(self, clone: pathlib.Path, paths: list[str], subject: str, rank: str) -> str:
        self.git("-C", str(clone), "add", "--", *paths)
        # A model's work names the model; the next mission's row is the script's.
        msg = (f"{subject}\n\nCo-Authored-By: {CO_AUTHOR[rank]} <noreply@anthropic.com>\n"
               if rank in CO_AUTHOR else f"{subject}\n")
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
        try:
            r = self.group_run(runner.fence_argv(["/bin/bash", "-c", script], net="none",
                                                 token=False),
                               text=True, cwd=target,
                               env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                               timeout=CHECK_TIMEOUT_S, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired as e:
            # F225: a failed run, said through the stage's usual stop, never an
            # exception the cycle would end the stage on and start it again from.
            said = "".join(x.decode(errors="replace") if isinstance(x, bytes) else (x or "")
                           for x in (e.stdout, e.stderr))
            why = (f"the run with no model passed its time limit of {CHECK_TIMEOUT_S} s "
                   f"({CHECK_TIMEOUT_S // 60} min) and was stopped, so it has no result")
            (run / "run" / "check.txt").write_text(f"{said}\n{why}\n", encoding="utf-8")
            clean_tmp(run)
            return Check(False, commit, why=why, out=said)
        text = (r.stdout or "") + (r.stderr or "")
        (run / "run" / "check.txt").write_text(text, encoding="utf-8")
        clean_tmp(run)                 # F226: the run has ended; its result is written
        if command:
            return Check(r.returncode == 0, commit, why=text[-2000:], out=text)
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
            c = self.checked(clone, commit, full=False)
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
        branch = (resume or {}).get("branch") or branch
        run, j = self.begin(f"xo_{phase}", {"stage": "xo", "issue": issue, "phase": phase,
                                            "branch": branch}, resume)
        self.started(issue, "xo", f"**Executive Officer, phase {phase}: started.**")
        clone = self.stage_clone(run, branch)
        self.log(f"issue {issue}: the Executive Officer on phase {phase}, {clone}")
        runner = FencedRunner(self, clone, run / "run", journal=j)
        if j.resumed:
            # xo.review comments its verdict, then sets the label: a verdict
            # already posted is not reviewed again, only its label set.
            verdict = [m for c in self.comments(issue)
                       if _time(c["createdAt"]) >= j.started
                       for m in [_XO.match(c.get("body", "").lstrip())] if m]
            if verdict:
                lab = xo.LABEL[verdict[-1].group(1)]
                self.step("label", lambda: xo.set_label(issue, lab, runner),
                          lambda: lab in self.labels_of(issue))
                return "verdict applied"
        try:
            code = xo.review(phase, issue, repo=clone, run=runner, out=self.log,
                             identity_file=self.identity_file)
        except RateLimited as e:
            self.pause(j, e, runner)
            return "rate-limited"
        return {0: "verdict applied", 2: "plan unreadable", 3: "stopped"}.get(code, f"exit {code}")

    def stage_scout(self, issue: int, phase: str, title: str, body: str, *,
                    resume: dict | None = None) -> str:
        ident = self.identity_for(issue, body, "scout")
        if ident is None:
            return "needs hands"
        if resume and "branch" in resume:
            branch, new = resume["branch"], resume["new"]
        else:
            branch, _ = self.branch_for(phase, body)
            new = branch is None
            # A branch the body names and GitHub lacks yet is the one made: two
            # issues for one phase each name theirs (Phase 389's planted proofs).
            named = re.search(rf"`(phase-{re.escape(phase)}-[A-Za-z0-9._-]+)`", body or "")
            branch = branch or (named.group(1) if named else
                                f"phase-{phase}-{scout.slug(title).replace('_', '-')}")
        run, j = self.begin(f"scout_{phase}", {"stage": "scout", "issue": issue, "phase": phase,
                                               "title": title, "body": body, "branch": branch,
                                               "new": new}, resume)
        self.started(issue, "scout", f"**Science Officer, phase {phase}: started** on `{branch}`.")
        clone = self.stage_clone(run, "master" if new else branch,
                                 new_branch=branch if new else None)
        self.author(clone, "scout", ident if ident.is_fleet else None)
        rows = (clone / "docs" / "ROADMAP.md").read_text(encoding="utf-8").splitlines()
        row = next((ln for ln in rows if re.match(rf"\| *{re.escape(phase)} *\|", ln)), "")
        k = rows.index(row) if row in rows else 0
        handoffs = sorted((clone / "docs" / "handoffs").glob("*.md"))
        context = "\n".join(rows[max(0, k - 3):k + 3]) + (
            "\n\n" + handoffs[-1].read_text(encoding="utf-8")[:6000] if handoffs else "")
        runner = FencedRunner(self, clone, run / "run", journal=j)
        self.log(f"issue {issue}: the Science Officer on phase {phase}, {clone}")
        today = dt.date.fromisoformat(j.data["started"][:10])
        try:
            written = scout.run_scout(phase, title, issue, body, row, clone=clone, run=runner,
                                      mobile=self.mobile if self.mobile.is_dir() else None,
                                      context=context, today=today)
        except RateLimited as e:
            self.pause(j, e, runner)
            return "rate-limited"
        head = self.commit_once(clone, lambda: written,
                                f"Phase {phase} Step 0: the Science Officer's report", "scout")
        self.push_once(clone, head, rank="scout", phase=phase, branch=branch, ident=ident,
                       tested=self.fast(clone))
        self.say_once(issue, f"{SCOUT_M} step0 commit={head[:12]} -->",
                      f"**Science Officer, phase {phase}: Step 0 written** on `{branch}` "
                      f"(`{written[0]}`). Next: the Captain writes v1.0.")
        self.label_once(issue, "step0:done")
        return f"step 0 pushed on {branch}"

    def stage_captain(self, issue: int, phase: str, body: str, branch: str, *,
                      items: list[str] | None = None, rnd: int = 0, resume: dict | None = None) -> str:
        ident = self.identity_for(issue, body, "captain")
        if ident is None:
            return "needs hands"
        run, j = self.begin(f"captain_{phase}", {"stage": "captain", "issue": issue,
                                                 "phase": phase, "body": body, "branch": branch,
                                                 "items": items, "rnd": rnd}, resume)
        self.started(issue, "captain", f"**Captain, phase {phase}: started**"
                     + (f", revision round {rnd}." if items else ", v1.0."))
        clone = self.stage_clone(run, branch)
        self.author(clone, "captain", ident if ident.is_fleet else None)
        step0 = clone / "docs" / "phases" / "in_progress" / f"{phase}_step0.md"
        if not step0.is_file():
            raise Stop(f"no {step0.name} on {branch}: the Captain writes from Step 0")
        prompts = sorted((clone / "docs" / "prompts").glob(f"{phase}_*.txt"))
        row = next((ln for ln in (clone / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
                    .splitlines() if re.match(rf"\| *{re.escape(phase)} *\|", ln)), "")
        runner = FencedRunner(self, clone, run / "run", journal=j)
        self.log(f"issue {issue}: the Captain on phase {phase}"
                 + (f", revision round {rnd}" if items else ""))
        try:
            calls = captain.write_plan(phase, row, prompts[0].read_text(encoding="utf-8")
                                       if prompts else "", step0.read_text(encoding="utf-8"),
                                       clone=clone, run=runner, items=items)
        except RateLimited as e:
            self.pause(j, e, runner)
            return "rate-limited"
        subject = (f"Phase {phase} v1.0: the plan" if not items else
                   f"Phase {phase} v1.0, revised for the Executive Officer (round {rnd})")
        impl = f"docs/phases/in_progress/{phase}_implementation.md"
        head = self.commit_once(clone, lambda: [impl], subject, "captain")
        self.push_once(clone, head, rank="captain", phase=phase, branch=branch, ident=ident,
                       tested=self.fast(clone))
        kind = "revision" if items else "v1.0"
        marker = f"{CAPTAIN_M} {kind} round={rnd} commit={head[:12]} -->"
        self.say_once(issue, marker,
                      f"**Captain, phase {phase}: {subject}** (`{head[:12]}`), `plan_check` P1–P8 "
                      f"passed.\n\n" + "\n".join(c.line() for c in calls))
        if items:
            self.step("label", lambda: self.reapply(issue, REVIEW),
                      lambda: self.reapplied_after(issue, REVIEW, self.tag(marker)))
        else:
            self.label_once(issue, REVIEW)
        return subject

    def reapplied_after(self, issue: int, label: str, marker: str) -> bool:
        """`label` is on, and was applied after the comment `marker` begins."""
        if label not in self.labels_of(issue):
            return False
        said = self.newest(issue, marker)
        applied = self.last_applied(self.label_events(issue), label)
        return bool(said and applied and _time(applied) >= said[0])

    def stage_engineer(self, issue: int, phase: str, body: str, branch: str, *,
                       findings: str | None = None, rnd: int = 0, resume: dict | None = None,
                       answer: str | None = None) -> str:
        ident = self.identity_for(issue, body, "engineer")
        if ident is None:
            return "needs hands"
        answer = (resume or {}).get("answer", answer)
        run, j = self.begin(f"engineer_{phase}", {"stage": "engineer", "issue": issue,
                                                  "phase": phase, "body": body, "branch": branch,
                                                  "findings": findings, "rnd": rnd,
                                                  "answer": answer}, resume)
        self.say_once(issue, f"{ENGINEER_M} started round={rnd} -->",
                      f"**Chief Engineer, phase {phase}: building**"
                      + (f", fix round {rnd} for the Red Team's findings" if findings else "")
                      + (", again, with the record's answer to its stop" if answer else "")
                      + f", in a fenced clone of `{branch}`.", step="started")
        clone = self.stage_clone(run, branch)
        self.author(clone, "engineer", ident if ident.is_fleet else None)
        self.label_once(issue, "build:open", step="label-build")
        runner = FencedRunner(self, clone, run / "run", journal=j)
        argv = engineer.session_argv(phase, issue, findings=findings, rnd=rnd, answer=answer)
        self.log(f"issue {issue}: the Chief Engineer on phase {phase}, round {rnd}, {clone}")
        try:
            r, reason = runner.session(argv, watch=lambda: engineer.watch(clone, run / "run", phase))
        except RateLimited as e:
            self.pause(j, e, runner)
            return "rate-limited"
        if reason:
            if self.answer_stop(issue, phase, reason.split(":", 1)[0], clone):
                return "stopped, answered from the record"
            self.escalate(issue, "engineer", "needs-admiral",
                          f"Chief Engineer, phase {phase}: stopped. {reason}")
            return f"stopped: {reason[:80]}"
        result = engineer.read_result(run / "run")
        if result["outcome"] == "stop":
            if self.answer_stop(issue, phase, result["kind"], clone):
                return "stopped, answered from the record"
            self.escalate(issue, "engineer", "needs-admiral",
                          f"Chief Engineer, phase {phase}: stopped ({result['kind']}). "
                          f"{result['question']}")
            return f"stopped: {result['kind']}"
        return self.engineer_finish(issue, phase, branch, ident, run, result, rnd)

    def answer_stop(self, issue: int, phase: str, kind: str, clone: pathlib.Path) -> bool:
        """A stop the record answers (Phase 392, the operator's K50): one K-id
        whose Covers line names this kind of stop and this phase, never a
        rule-1 kind. Its words are said on the issue verbatim, and the
        Engineer runs again with them (`next_stage`). One answer per K-id and
        stop on an issue: the same stop again goes to the operator."""
        d = plan_order.answer(clone, kind, phase)
        if d is None:
            return False
        mark = f"{ANSWER_M} kid={d.kid} stop={kind}"
        if self.has_comment(issue, mark):
            self.log(f"issue {issue}: {d.kid} already answered {kind} here: to the operator")
            return False
        self.say_once(issue, f"{mark} -->",
                      f"**Answered from the record, not by the operator.** The Chief Engineer "
                      f"stopped on phase {phase} ({kind}). {d.kid}, dated {d.date}, covers this "
                      f"stop on this phase. The operator's words, verbatim:\n\n> {d.words}\n\n"
                      "The Engineer runs again with those words, applied literally. If the same "
                      "thing stops it again, that comes to the operator.", step="answered")
        self.log(f"issue {issue}: {kind} answered from the record by {d.kid}")
        return True

    def engineer_finish(self, issue: int, phase: str, branch: str, ident: fleet_git.Identity,
                        run: pathlib.Path, result: dict, rnd: int) -> str:
        """A `pr-ready`, checked: the model-free run on HEAD, then the push,
        the PR and `review:open`. When the model-free run is all that failed
        (the Engineer's own line passes every other check: F220, a run lost
        to load), the run is held (`journal.hold`): the operator taking
        `needs-admiral` off runs it again on the same commit (`stage_recheck`)."""
        clone = run / "clone"
        head = self.git("-C", str(clone), "rev-parse", "HEAD").stdout.strip()
        self.log(f"issue {issue}: the model-free run on {head[:12]}")
        try:
            check = self.checked(clone, head, full=True)
        except LowSpace as e:
            # Held like F220's run: `needs-hands` off runs it on this commit.
            self.step("hold", lambda: journal.hold(run, {"issue": issue, "phase": phase,
                                                         "rnd": rnd, "commit": head,
                                                         "why": "space"}))
            self.hold_for_space(issue, "engineer", str(e))
            return "held: free space"
        # The close-out's reclaim (the operator: "as a part of the overall
        # process phase to phase"): its line goes in the PR, for the handoff.
        space = self.reclaim(f"phase {phase}'s close-out") if check.ok and self.disks else None
        fails = engineer.verify(clone, phase, result, check.line if check.ok else None)
        if not check.ok:
            fails.append(f"the model-free run did not pass: {check.line or check.why}"[:400])
        if fails:
            again = not check.ok and not engineer.verify(clone, phase, result,
                                                         result["regression_line"])
            if again:
                self.step("hold", lambda: journal.hold(run, {"issue": issue, "phase": phase,
                                                             "rnd": rnd, "commit": head}))
            self.escalate(issue, "engineer", "needs-admiral",
                          f"Chief Engineer, phase {phase}: the work says it is ready, and the "
                          f"checks say it is not. " + " ".join(f"({i + 1}) {f}" for i, f in
                                                              enumerate(fails))[:1500]
                          + (" Only the run with no model failed: take `needs-admiral` off to "
                             f"run it again on the same commit ({head[:12]})." if again else ""))
            return "checks failed"
        self.push_once(clone, head, rank="engineer", phase=phase, branch=branch, ident=ident,
                       tested=lambda c: (check.ok and c == check.commit,
                                         "not the commit the model-free run tested"))
        text = (f"{result['summary'].strip()}\n\nMission: #{issue}\n\n"
                f"The Engineer's regression of record:\n\n    {result['regression_line']}\n\n"
                f"The same commit, run again with no model (`wholetree.sh --full`, "
                f"`regression.sh`, in the fence):\n\n    {check.line}\n"
                + (f"\nFree space after the close-out's reclaim:\n\n    {space}\n" if space else ""))
        # Whether this stage opens the PR or comments on it, decided once: a
        # PR this stage opened is there when it resumes.
        mode = self.step("pr-mode", lambda: "create" if self.pr_for(branch) is None else "comment")
        if mode == "create":
            self.step("pr", lambda: self.gh_as(ident, "pr", "create", "--head", branch, "--base",
                                               "master", "--title",
                                               f"Phase {phase}: {self.title_of(issue)}",
                                               "--body", text),
                      lambda: self.pr_for(branch) is not None)
            pr = self.pr_for(branch)
        else:
            pr = self.pr_for(branch)
            if pr is None:
                raise Stop(f"the pull request for `{branch}` is no longer open")
            marker = self.tag(f"<!-- fleet-engineer-pr: round={rnd} -->")
            self.step("pr", lambda: self.gh_as(ident, "pr", "comment", str(pr["number"]), "--body",
                                               f"{marker}\n**Chief Engineer, fix round {rnd}.**"
                                               f"\n\n{text}"),
                      lambda: self.pr_has_comment(pr["number"], marker))
        self.say_once(issue, f"{ENGINEER_M} pr-ready round={rnd} pr={pr and pr['number']} -->",
                      f"**Chief Engineer, phase {phase}: pull request ready** "
                      f"({pr and pr['url']}). The model-free run: {check.line}")
        self.label_once(issue, "review:open")
        return f"PR {pr and pr['number']} ready"

    def stage_recheck(self, issue: int, phase: str, body: str, branch: str, held: pathlib.Path,
                      *, resume: dict | None = None) -> str:
        """The operator took `needs-admiral` off an Engineer stop whose only
        failure was the model-free run: that run again, on the commit the
        Engineer left in its held run, then the rest of a `pr-ready`."""
        ident = self.identity_for(issue, body, "engineer")
        if ident is None:
            return "needs hands"
        info = journal.held(held)
        if info is None:
            raise Stop(f"the held run {held.name} is no longer held")
        run, j = self.begin(f"recheck_{phase}", {"stage": "recheck", "issue": issue,
                                                 "phase": phase, "body": body, "branch": branch,
                                                 "held": str(held)}, resume)
        self.started(issue, "engineer", f"**Chief Engineer, phase {phase}: the run with no model, "
                                        f"again**, on `{info['commit'][:12]}`, as the operator "
                                        "took `needs-admiral` off.")
        head = self.git("-C", str(held / "clone"), "rev-parse", "HEAD").stdout.strip()
        if head != info["commit"]:
            raise Stop(f"the held clone is at {head[:12]}, not {info['commit'][:12]}")
        out = self.engineer_finish(issue, phase, branch, ident, held,
                                   engineer.read_result(held / "run"), info["rnd"])
        if out.startswith("PR "):
            self.step("release", lambda: journal.release(held))
            clean_tmp(held)            # F226: released, the held run has ended
        return out

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
        """Comments are made as every rank's are (387, 388); only the push of
        a cleared table needs a push identity."""
        pr = self.pr_for(branch)
        if pr is None:
            raise Stop(f"no open pull request for `{branch}`")
        rnd = resume["rnd"] if resume and "rnd" in resume else len(self.red_rounds(issue)) + 1
        run, j = self.begin(f"red_team_{phase}", {"stage": "red_team", "issue": issue,
                                                  "phase": phase, "body": body, "branch": branch,
                                                  "rnd": rnd}, resume)
        self.started(issue, "red-team", f"**Red Team, phase {phase}: started**, round {rnd}.")
        clone = self.stage_clone(run, branch)
        head = j.value("clone")["base"]          # the PR's head, before any refute commit
        f9 = self.checked(clone, head, full=False,
                          command=[".venv/bin/python", "scripts/check_f9_patterns.py", "--all"])
        runner = FencedRunner(self, clone, run / "run", journal=j)
        self.log(f"issue {issue}: the Red Team on phase {phase}, round {rnd}")
        try:
            v, call = red_team.review(phase, rnd, red_team.gather(clone, phase, f9.why),
                                      clone=clone, run=runner)
        except RateLimited as e:
            self.pause(j, e, runner)
            return "rate-limited"
        cite = plan_order.cite_line(clone, phase)
        # F228: the one finding open wording defects go to, filed here, outside
        # the model; its number chosen once (journaled) and written into each row.
        rows = v.get("wording_open") or []
        fnum = self.step("finding-number", lambda: self.next_f(clone)) if rows else None
        table = red_team.with_finding(v["refuter_pass"], fnum) if fnum else v["refuter_pass"]
        filed = (f"\n\nThe wording left open goes to {fnum}, one finding, filed by the "
                 f"dispatcher (K9)." if fnum else "")
        pr_marker = self.tag(f"<!-- fleet-red-team-pr: verdict={v['verdict']} round={rnd} -->")
        self.step("pr-comment", lambda: self.gh(
            "pr", "comment", str(pr["number"]), "--body",
            f"{pr_marker}\n**Red Team, round {rnd}: {v['verdict']}**\n\nFindings:\n"
            f"{red_team.findings_text(v)}\n\n{table.strip()}{filed}\n\n{cite}\n\n"
            f"{call.line()}"),
                  lambda: self.pr_has_comment(pr["number"], pr_marker))
        self.say_once(issue, f"{RED_M} verdict={v['verdict']} round={rnd} -->",
                      f"**Red Team, phase {phase}, round {rnd}: {v['verdict']}** "
                      f"(PR #{pr['number']}).\n\n{red_team.findings_text(v)}{filed}\n\n{cite}")
        if v["verdict"] == red_team.BACK:
            if rnd >= red_team.MAX_ROUNDS:
                unfiled = ""
                if fnum:
                    ident = self.identity_for(issue, body, "red-team")
                    if ident is None:
                        return "back, rounds exhausted; the wording finding waits for a push identity"
                    self.author(clone, "red-team-record", ident if ident.is_fleet else None)
                    head = self.commit_once(
                        clone, lambda: self.write_finding(clone, fnum, phase, rnd, rows),
                        f"Phase {phase}: the Red Team's round-{rnd} wording, filed as {fnum}",
                        "red-team-record")
                    self.push_once(clone, head, rank="red-team-record", phase=phase,
                                   branch=branch, ident=ident, tested=self.fast(clone))
                    unfiled = f" The wording it left open is filed as {fnum}, on the branch."
                self.escalate(issue, "red-team", "needs-admiral",
                              f"Red Team, phase {phase}: round {rnd} of {red_team.MAX_ROUNDS} "
                              "still finds factual, citation or code defects; under K9 the "
                              "phase does not ship as it stands. The operator decides." + unfiled)
                return "back, rounds exhausted"
            self.label_once(issue, "build:open")
            return f"back, round {rnd}"
        ident = self.identity_for(issue, body, "red-team")
        if ident is None:
            return "clear; the refute table waits for a push identity"
        self.author(clone, "red-team-record", ident if ident.is_fleet else None)
        subject = f"Phase {phase}: the Red Team's refuter pass, round {rnd}"
        new = self.commit_once(clone, lambda: [red_team.record_in_log(clone, phase, table),
                                               *(self.write_finding(clone, fnum, phase, rnd, rows)
                                                 if fnum else [])],
                               subject, "red-team-record")
        self.push_once(clone, new, rank="red-team-record", phase=phase, branch=branch,
                       ident=ident, tested=self.fast(clone))
        self.label_once(issue, "review:clear")
        return f"clear, round {rnd}"

    def next_f(self, clone: pathlib.Path) -> str:
        """The next free F-number: one sequence over the branch's, master's and
        the mobile repository's `FOLLOWUPS.md` (the finding skill's rule)."""
        texts = [(clone / FOLLOWUPS).read_text(encoding="utf-8"),
                 self.git("-C", str(clone), "show", f"origin/master:{FOLLOWUPS}").stdout]
        mobile = self.mobile / FOLLOWUPS
        if mobile.is_file():
            texts.append(mobile.read_text(encoding="utf-8"))
        seen = {int(n) for text in texts for _, n in finding_check._ENTRY.findall(text)}
        return f"F{max(seen, default=0) + 1}"

    def write_finding(self, clone: pathlib.Path, fnum: str, phase: str, rnd: int,
                      rows: list[dict]) -> list[str]:
        """The wording finding appended to the branch's `FOLLOWUPS.md`, and its
        header's highest number (B1); once, however often a resumed stage asks."""
        path = clone / FOLLOWUPS
        text = path.read_text(encoding="utf-8")
        if not re.search(rf"^#{{2,3}}\s*{fnum}\b", text, re.M):
            text = text.rstrip("\n") + "\n\n" + red_team.wording_entry(
                fnum, phase, rnd, rows, f"the Red Team's round {rnd} on phase {phase}")
        text = finding_check._HEADER.sub(f"highest assigned is **{fnum}**", text, count=1)
        path.write_text(text, encoding="utf-8")
        return [FOLLOWUPS]

    def stage_recommend(self, issue: int, phase: str, body: str, branch: str, *,
                        resume: dict | None = None) -> str:
        pr = self.pr_for(branch)
        if pr is None:
            raise Stop(f"no open pull request for `{branch}`")
        run, j = self.begin(f"recommend_{phase}", {"stage": "recommend", "issue": issue,
                                                   "phase": phase, "body": body,
                                                   "branch": branch}, resume)
        self.started(issue, "captain", f"**Captain, phase {phase}: started**, the merge "
                                       "recommendation.")
        clone = self.stage_clone(run, branch)
        pr_text = self.gh("pr", "view", str(pr["number"]), "--json", "body", "--jq", ".body")
        clear = self.newest(issue, RED_M)
        impl = next((p for p in (clone / "docs" / "phases" / d / f"{phase}_implementation.md"
                                 for d in ("completed", "in_progress")) if p.is_file()), None)
        summary = (f"=== the pull request ===\n{pr_text}\n\n=== the Red Team's last word ===\n"
                   f"{clear[1] if clear else '(none)'}\n\n=== v1.1 ===\n"
                   f"{impl.read_text(encoding='utf-8') if impl else '(missing)'}")
        runner = FencedRunner(self, clone, run / "run", journal=j)
        try:
            v, call = captain.recommend(phase, summary, clone=clone, run=runner)
        except RateLimited as e:
            self.pause(j, e, runner)
            return "rate-limited"
        lines = "\n".join(v["lines"])
        cite = plan_order.cite_line(clone, phase)
        pr_marker = self.tag(f"<!-- fleet-captain-pr: recommendation={v['decision']} -->")
        self.step("pr-comment", lambda: self.gh(
            "pr", "comment", str(pr["number"]), "--body",
            f"{pr_marker}\n**The Captain's recommendation: {v['decision']}**\n\n{lines}\n\n"
            f"{cite}\n\n{call.line()}"),
                  lambda: self.pr_has_comment(pr["number"], pr_marker))
        self.say_once(issue, f"{CAPTAIN_M} recommendation={v['decision']} -->",
                      f"**Captain, phase {phase}: recommends {v['decision']}** "
                      f"(PR #{pr['number']}).\n\n{lines}\n\n{cite}\n\nThe operator merges.")
        self.label_once(issue, "merge:needs-review")
        return f"recommendation: {v['decision']}"

    # ---- the Quartermaster, in shadow (Phase 391)
    def quartermaster_due(self, n: int) -> bool:
        """`merge:needs-review` applied after the Quartermaster's last word
        here, and after it first came up on this machine."""
        since = self.load().get("quartermaster_since")
        applied = self.last_applied(self.label_events(n), QM)
        return (since is not None and applied is not None and _time(applied) > _time(since)
                and self.due_for(n, QM, self.markers(QM_M, "quartermaster")))

    def verdicts(self) -> pathlib.Path:
        return self.state_dir / "quartermaster.jsonl"

    def stage_quartermaster(self, issue: int, phase: str, body: str, branch: str, *,
                            resume: dict | None = None) -> str:
        """The verdict on the PR, the issue and in `quartermaster.jsonl`. It
        merges nothing and moves no label: the operator merges."""
        pr = self.pr_for(branch)
        if pr is None:
            raise Stop(f"no open pull request for `{branch}`")
        run, j = self.begin(f"quartermaster_{phase}", {"stage": "quartermaster", "issue": issue,
                                                       "phase": phase, "body": body,
                                                       "branch": branch}, resume)
        self.started(issue, "quartermaster", f"**Quartermaster, phase {phase}: started**, in "
                                             "shadow: a verdict, and nothing merged.")
        clone = self.stage_clone(run, branch)
        head = j.value("clone")["base"]
        q1 = quartermaster.scope(clone, phase)
        judged, call = None, None
        if not q1.ok:
            found = [q1]
            summary = "Out of the Quartermaster's scope, so it ran nothing: the operator decides."
            self.log(f"issue {issue}: the Quartermaster on phase {phase}: out of scope: {q1.why}")
        else:
            self.log(f"issue {issue}: the Quartermaster on phase {phase}, {head[:12]}")
            full = self.checked(clone, head, full=True)
            reg = quartermaster.regression_hash(clone, phase) or head
            ver = self.checked(clone, head, full=False,
                               command=[quartermaster.VERIFY, phase, reg, head])
            found, extra = quartermaster.scripted(
                clone, phase, head, self.comments(issue), full_ok=full.ok, full_line=full.line,
                full_why=full.why, verify_text=ver.out, sibling=self.mobile)
            found = [q1, *found]
            pr_body = self.gh("pr", "view", str(pr["number"]), "--json", "body", "--jq", ".body")
            runner = FencedRunner(self, clone, run / "run", journal=j)
            try:
                judged, call = quartermaster.judge(
                    phase, quartermaster.gather(clone, phase, found, extra, ver.out, pr_body),
                    clone=clone, run=runner)
            except RateLimited as e:
                self.pause(j, e, runner)
                return "rate-limited"
            summary = judged["summary"]
        verdict, failed, note = quartermaster.compose(found, judged)
        text = quartermaster.verdict_text(phase, verdict, failed, summary, note,
                                          call.line() if call else "",
                                          plan_order.cite_line(clone, phase))
        checks = " ".join(c for c, _ in failed) or "none"
        pr_marker = self.tag(f"{QM_PR_M} verdict={verdict} -->")
        self.step("pr-comment", lambda: self.gh("pr", "comment", str(pr["number"]), "--body",
                                                f"{pr_marker}\n{text}"),
                  lambda: self.pr_has_comment(pr["number"], pr_marker))
        self.say_once(issue, f"{QM_M} verdict={verdict} failed={checks.replace(' ', ',')} -->",
                      f"{text}\n\n(PR #{pr['number']}.)")
        record = {"at": self.now().isoformat(timespec="seconds"), "issue": issue,
                  "pr": pr["number"], "phase": phase, "head": head, "verdict": verdict,
                  "failed": [c for c, _ in failed], "run": run.name}

        def write() -> None:
            with self.verdicts().open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        self.step("record", write, lambda: any(
            json.loads(ln).get("run") == run.name for ln in self.verdicts().read_text(
                encoding="utf-8").splitlines()) if self.verdicts().is_file() else False)
        return f"verdict: {verdict} ({checks})"

    def verdicts_on(self, day: dt.date) -> list[dict]:
        """The Quartermaster's verdicts given on one local day."""
        if not self.verdicts().is_file():
            return []
        rows = [json.loads(ln) for ln in self.verdicts().read_text(encoding="utf-8").splitlines()
                if ln.strip()]
        return [r for r in rows if _time(r["at"]).astimezone(self.now().tzinfo).date() == day]

    def stage_digest(self, day: dt.date, *, resume: dict | None = None) -> str:
        run, j = self.begin("digest", {"stage": "digest", "day": day.isoformat()}, resume)
        clone = self.stage_clone(run, "master")
        self.log(f"the digest for {day}, {clone}")
        runner = FencedRunner(self, clone, run / "run", journal=j)
        try:
            code = yeoman.digest(day, root=clone, run=runner, out=self.log,
                                 verdicts=self.verdicts_on(day))
        except RateLimited as e:
            self.pause(j, e, runner)
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

    def pause(self, j: journal.Journal, limited: RateLimited, runner: FencedRunner) -> None:
        """A usage limit: `paused` names the stage's journal, which stays open."""
        record, why = {**j.record, "session": limited.session}, limited.text
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
                         f"session={record.get('session')} until={until.isoformat()} "
                         f"run={j.run.name}",
                         f"**Fleet dispatcher: stopped on a usage limit, label unchanged.** "
                         f"{why[:300]}\n\nThe stage resumes after {until:%Y-%m-%d %H:%M %Z}, "
                         f"session `{record.get('session')}`.")

    def resume(self, paused: dict) -> str:
        """The stage a record names, again, from its run directory and journal."""
        s, n, ph = paused["stage"], paused.get("issue"), paused.get("phase")
        if s == "xo":
            return self.stage_xo(n, ph, resume=paused)
        if s == "digest":
            return self.stage_digest(dt.date.fromisoformat(paused["day"]), resume=paused)
        if s == "next":
            return self.stage_next(paused["entry"], resume=paused)
        if s == "scout":
            return self.stage_scout(n, ph, paused["title"], paused["body"], resume=paused)
        if s == "captain":
            return self.stage_captain(n, ph, paused["body"], paused["branch"],
                                      items=paused.get("items"), rnd=paused.get("rnd", 0),
                                      resume=paused)
        if s == "engineer":
            return self.stage_engineer(n, ph, paused["body"], paused["branch"],
                                       findings=paused.get("findings"), rnd=paused.get("rnd", 0),
                                       resume=paused, answer=paused.get("answer"))
        if s == "recheck":
            return self.stage_recheck(n, ph, paused["body"], paused["branch"],
                                      pathlib.Path(paused["held"]), resume=paused)
        if s == "red_team":
            return self.stage_red_team(n, ph, paused["body"], paused["branch"], resume=paused)
        if s == "quartermaster":
            return self.stage_quartermaster(n, ph, paused["body"], paused["branch"], resume=paused)
        return self.stage_recommend(n, ph, paused["body"], paused["branch"], resume=paused)

    # ---- the next mission, from the plan (Phase 392, K48, K49)
    def master_text(self, rel: str) -> str:
        r = self.git("-C", str(self.mirror), "show", f"master:{rel}")
        return r.stdout if r.returncode == 0 else ""

    def once(self, key: str, msg: str) -> None:
        """A log line said once per run of the service, not every cycle."""
        if ("once", key) not in self._skipped:
            self._skipped.add(("once", key))
            self.log(msg)

    def mission_issue(self, phase: str) -> dict | None:
        """The open issue for `phase`, opened by the fleet or the operator."""
        return next((i for i in self.issues_open()
                     if re.match(rf"Phase {re.escape(phase)}\b", i["title"])), None)

    def next_due(self, rows: dict[str, str]) -> plan_order.Entry | None:
        """The plan's next entry, when the fleet has something to do for it:
        open its issue, ask the operator what the plan says it needs, or open
        its row's pull request. None while it waits (for a builder's phase,
        for the operator, for the row's merge) or when the list cannot be read."""
        texts = {rel: self.master_text(rel) for rel in plan_order.FILES}
        fails = plan_order.check_texts(texts)
        if fails:
            self.once("order:" + fails[0], "next: the plan's 'Next, in order' cannot be read "
                      "exactly on master, so no mission is started: " + "; ".join(fails)[:300])
            return None
        e = plan_order.next_entry(plan_order.parse_order(texts[plan_order.PLAN]),
                                  plan_order.rows_of(texts["docs/ROADMAP.md"]))
        if e is None:
            return None
        if e.built_by != "fleet":
            self.once(f"builder:{e.phase}", f"next: phase {e.phase} is a builder's (the plan's "
                      f"#{e.n}); the fleet waits for it")
            return None
        issue = self.mission_issue(e.phase)
        if issue is None:
            return e
        n, labels = issue["number"], {x["name"] for x in issue.get("labels", [])}
        if labels & set(OPERATOR):
            return None
        if e.need and not self.has_comment(n, f"{NEXT_M} asked"):
            return e
        if rows.get(e.phase) == roadmap_check.ACTIVE:
            return None
        return e if self.pr_for(row_branch(e.phase)) is None else None

    def stage_next(self, entry: dict, *, resume: dict | None = None) -> str:
        """The next mission's issue, the operator's question when the plan
        says the phase needs them, and the one-row pull request that marks its
        row 🚧, which the operator merges by hand (K49). Never a push to master."""
        e = plan_order.Entry(**{k: entry[k] for k in ("n", "phase", "kind", "built_by", "needs",
                                                      "entry")})
        run, j = self.begin(f"next_{e.phase}", {"stage": "next", "issue": None, "phase": e.phase,
                                                "entry": entry}, resume)
        ident = fleet_git.read_identity_file(self.identity_file)
        if ident is None:
            self.once("next-account", "next: the fleet has no GitHub account of its own, so it "
                      "opens no mission")
            return "no account"
        title = f"Phase {e.phase}: {self.master_rows_titles().get(e.phase, 'the next mission')}"
        work = f"phase-{e.phase}-{scout.slug(title).replace('_', '-')}"
        cite = plan_order.cite_line(self.mirror_root(), e.phase)

        def find() -> int | None:
            i = self.mission_issue(e.phase)
            return i["number"] if i else None
        # The issue may be there from an earlier cycle (the operator's question
        # asked and answered): found first, opened only when it is not.
        n = self.step("issue", lambda: find() or self.open_mission(
            ident, title, mission_body(e, work, cite)), find)
        j.record["issue"] = n
        if e.need:
            label = plan_order.NEEDS[e.need]
            if not self.has_comment(n, f"{NEXT_M} asked"):
                self.say_once(n, f"{NEXT_M} asked need={label} -->", ask_text(e, label),
                              step="ask")
                self.step("ask-label", lambda: self.gh("issue", "edit", str(n), "--add-label",
                                                       label),
                          lambda: label in self.labels_of(n))
                return f"asked the operator ({label})"
            if label in self.labels_of(n):
                return "waiting for the operator"
        if self.master_rows().get(e.phase) == roadmap_check.ACTIVE:
            return "the row is on master"
        branch = row_branch(e.phase)
        clone = self.stage_clone(run, "master", new_branch=branch)
        self.author(clone, "row", ident)
        head = self.commit_once(clone, lambda: [mark_row_active(clone, e.phase)],
                                f"Phase {e.phase}: its row, in progress (the plan's next)", "row")
        self.push_once(clone, head, rank="row", phase=e.phase, branch=branch, ident=ident,
                       tested=self.fast(clone))
        self.step("pr", lambda: self.gh_as(ident, "pr", "create", "--head", branch, "--base",
                                           "master", "--title",
                                           f"Phase {e.phase}: start it (its row, in progress)",
                                           "--body", row_pr_body(e, n, title, cite)),
                  lambda: self.pr_for(branch) is not None)
        pr = self.pr_for(branch)
        self.say_once(n, f"{NEXT_M} row-pr pr={pr and pr['number']} -->",
                      f"**The fleet: phase {e.phase} is next in the plan.** Merging "
                      f"{pr and pr['url']} starts it: the row becomes 🚧 on master, and the "
                      "Science Officer begins Step 0 at the next cycle.", step="row-pr")
        return f"row PR {pr and pr['number']} for phase {e.phase}"

    def master_rows_titles(self) -> dict[str, str]:
        return {p: title for p, (_, title) in
                plan_order.rows_of(self.master_text("docs/ROADMAP.md")).items()}

    def mirror_root(self) -> pathlib.Path:
        """A folder holding master's record files, for `plan_order`'s readers."""
        root = self.state_dir / "record"
        for rel in plan_order.FILES:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(self.master_text(rel), encoding="utf-8")
        return root

    def open_mission(self, ident: fleet_git.Identity, title: str, body: str) -> int:
        url = self.gh_as(ident, "issue", "create", "--title", title, "--body", body,
                         "--label", "mission").strip()
        m = re.search(r"/issues/(\d+)\s*$", url)
        if not m:
            raise Stop(f"gh issue create printed no issue: {url[:200]}")
        self.log(f"next: opened issue {m.group(1)}: {title}")
        return int(m.group(1))

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

    def held_for(self, n: int) -> pathlib.Path | None:
        """The issue's held Engineer run, when the operator has taken
        `needs-admiral` off the stop that held it: that stop is still the
        issue's last rank comment (the cycle never looks at an issue the
        operator holds)."""
        runs = journal.held_runs(self.runs, n)
        if not runs:
            return None
        if (journal.held(runs[0]) or {}).get("why") == "space":
            # Held for free space (F221): the cycle reaches the issue only once
            # `needs-hands` is off, and the hold is due while its comment is
            # newer than any rank comment but a `started` one (a recheck that
            # then stops does not run again every cycle).
            spaced = self.newest(n, SPACE_M)
            later = [_time(c["createdAt"]) for c in self.comments(n)
                     if (b := c.get("body", "").lstrip()).startswith(RANK_PREFIXES)
                     and not (_STARTED.match(b) or _ENG_STARTED.match(b))]
            return runs[0] if spaced and (not later or spaced[0] > max(later)) else None
        ranked = [c["body"].lstrip() for c in self.comments(n)
                  if c.get("body", "").lstrip().startswith(RANK_PREFIXES)]
        stop = f"{MARKER} needs-admiral rank=engineer"
        return runs[0] if ranked and ranked[-1].startswith(stop) else None

    def next_stage(self, n: int, phase: str, labels: set[str], body: str, title: str
                   ) -> tuple[str, Callable[[], str]] | None:
        """The one stage the labels ask for on this issue, latest state first."""
        def branch() -> str:
            b, why = self.branch_for(phase, body)
            if b is None:
                raise Stop(why)
            return b

        if QM in labels and self.quartermaster_due(n):
            return "quartermaster", lambda: self.stage_quartermaster(n, phase, body, branch())
        if "review:clear" in labels and self.due_for(n, "review:clear",
                                                     self.markers(CAPTAIN_M, "captain")):
            return "captain", lambda: self.stage_recommend(n, phase, body, branch())
        if "review:open" in labels and self.due_for(n, "review:open",
                                                    self.markers(RED_M, "red-team")):
            return "red-team", lambda: self.stage_red_team(n, phase, body, branch())
        if "build:open" in labels and (held := self.held_for(n)) is not None:
            return "engineer", lambda: self.stage_recheck(n, phase, body, branch(), held)
        if "build:open" in labels:
            back, mine = self.newest(n, f"{RED_M} verdict=back"), self.newest(n, ENGINEER_M)
            stop = self.newest(n, f"{MARKER} stopped rank=engineer")
            latest_mine = max([t for t in (mine, stop) if t], default=None)
            said = self.newest(n, ANSWER_M)
            # At least as new: the answer is said by the stage that stopped, in
            # its own minute; the answered run's own start comes a cycle later.
            if said and (latest_mine is None or said[0] >= latest_mine[0]):
                rnd = sum(1 for v, _ in self.red_rounds(n) if v == "back")
                return "engineer", lambda: self.stage_engineer(
                    n, phase, body, branch(), findings=back[1] if back and rnd else None,
                    rnd=rnd, answer=said[1])
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

    # ---- running a stage to its end
    def say_stopped(self, n: int, rank: str, why: str, *, kind: str | None = None) -> None:
        """A stage's stop on its issue, label unchanged; said once."""
        if rank == "xo":
            kind = kind or "stopped"
            text = (f"**Fleet dispatcher: the Executive Officer "
                    f"{'did not run' if 'branch' in why else 'could not finish'}, label "
                    f"unchanged.** {why}. Apply `{REVIEW}` again once fixed.")
        else:
            kind = kind or f"stopped rank={rank}"
            text = f"**Fleet dispatcher: the {rank} could not finish, label unchanged.** {why}"
        kind = self.tag(f"{kind} -->")[:-4]
        self.step("stopped", lambda: self.comment(n, kind, text),
                  lambda: self.has_comment(n, f"{MARKER} {kind} -->"))

    def run_stage(self, n: int | None, rank: str, go: Callable[[], str], *,
                  recovering: bool = False) -> str:
        """One stage to its end: its outcome logged, a `Stop` said on its
        issue, its journal ended (a pause leaves it open). Resuming on start,
        any other error is said the same way (Phase 390: never quiet); in a
        cycle it ends the journal and goes on up, as in 389."""
        try:
            out = go()
        except LowSpace as e:
            out = f"held: {e}"
            self.hold_for_space(n, rank, str(e))
        except Stop as e:
            out = f"stopped: {e}"
            if n is not None:
                self.say_stopped(n, rank, str(e))
        except Exception as e:
            if not recovering:
                self.finish(f"failed: {type(e).__name__}: {e}")
                raise
            out = f"failed: {type(e).__name__}: {e}"
            self.log(f"the resumed stage failed:\n{traceback.format_exc()}")
            if n is not None:
                self.say_stopped(n, rank, f"the resumed stage failed: {type(e).__name__}: {e}")
        self.log(f"issue {n}: {out}" if n is not None else f"{rank}: {out}")
        self.finish(out)
        return out

    # ---- the search on start (Phase 390, F219)
    def watched(self, issue: dict, rows: dict[str, str]) -> str | None:
        """The phase of an issue the cycle would run a stage on, else None."""
        labels = {x["name"] for x in issue.get("labels", [])}
        if labels & set(OPERATOR) or not labels & {"mission", *STATE_LABELS}:
            return None
        m = re.match(r"Phase (\d{2,3}[A-Z]?)\b", issue["title"])
        return m.group(1) if m and rows.get(m.group(1)) == roadmap_check.ACTIVE else None

    def not_resumable(self, j: journal.Journal, issues: dict[int, dict],
                      rows: dict[str, str]) -> str | None:
        """Why a cut-off stage must not be resumed, or None."""
        n = j.record.get("issue")
        if n is None:
            return None
        issue = issues.get(n)
        if issue is None:
            return f"issue {n} is closed"
        labels = {x["name"] for x in issue.get("labels", [])}
        held = sorted(labels & set(OPERATOR))
        if held and not j.done("escalate"):
            return f"the operator holds it (`{'`, `'.join(held)}`)"
        m = re.match(r"Phase (\d{2,3}[A-Z]?)\b", issue["title"])
        if not m or rows.get(m.group(1)) != roadmap_check.ACTIVE:
            return "its phase's row on master is not 🚧"
        mine = f"run={j.run.name}"
        for c in self.comments(n):
            body = c.get("body", "").lstrip()
            first = body.split("\n", 1)[0]
            if (_time(c["createdAt"]) >= j.started and body.startswith(RANK_PREFIXES)
                    and mine not in first
                    and not (j.record["stage"] == "xo" and body.startswith(XO_OWN))):
                return f"another stage has run on it since: {first[:120]}"
        return None

    def open_started(self, n: int) -> tuple[str, str | None, dt.datetime] | None:
        """(rank, run or None, when) of a `started` marker nothing ends: the
        issue's last rank comment is it (one stage runs at a time, so any
        later rank comment ends it)."""
        ranked = [c for c in self.comments(n)
                  if c.get("body", "").lstrip().startswith(RANK_PREFIXES)]
        if not ranked:
            return None
        body = ranked[-1]["body"].lstrip()
        m, e = _STARTED.match(body), _ENG_STARTED.match(body)
        if not (m or e):
            return None
        rank, run = (m.group(1), m.group(2)) if m else ("engineer", e.group(1))
        return rank, run, _time(ranked[-1]["createdAt"])

    def stalled(self, n: int, phase: str, issue: dict) -> bool:
        """No stage is due on the issue: F219's stall. A label applied by hand
        after the cut (#14 at 15:50, `review:open` again) makes one due, and
        the cycle runs it; nothing needs saying then."""
        labels = {x["name"] for x in issue.get("labels", [])}
        try:
            return self.next_stage(n, phase, labels, issue.get("body", ""), issue["title"]) is None
        except Stop:
            return True

    def recover(self, *, dry_run: bool = False) -> list[str]:
        """Before the first cycle: every stage a restart, a power cut or a
        crash cut off. Unfinished journals are resumed (or, when the issue
        has moved on, ended with a comment); then any `started` marker left
        open with nothing to resume from gets a stop comment. One line per
        stage. `dry_run`: say what would be done, write nothing."""
        said: list[str] = []

        def act(line: str) -> None:
            said.append(line)
            (self.out if dry_run else self.log)(("would " if dry_run else "") + line)

        if not dry_run:
            self.update_mirror()
        rows = self.master_rows()
        issues = {i["number"]: i for i in self.issues_open()}
        paused = (self.load().get("paused") or {}).get("run")
        for p in journal.unreadable(self.runs):
            act(f"leave {p.name}: its journal cannot be read, so its stage is not resumed; "
                "the run is kept for the operator")
        for j in journal.unfinished(self.runs):
            rec, n = j.record, j.record.get("issue")
            rank, where = STAGE_RANK[rec["stage"]], f"{rec['stage']} from {j.run.name}"
            whose = f" (issue {n})" if n is not None else ""      # the digest has none
            if str(j.run) == paused:
                act(f"leave {where}: paused, it resumes after its reset")
                continue
            why = self.not_resumable(j, issues, rows)
            if why:
                act(f"not resume {where}{whose}: {why}")
                if not dry_run:
                    if n in issues:
                        self.comment(n, f"stopped rank={rank} run={j.run.name}",
                                     f"**Fleet dispatcher: the {rank}'s stage started "
                                     f"{j.data['started']} was cut off and is not resumed, "
                                     f"label unchanged.** {why}.")
                    j.end(f"abandoned: {why}", self.now())
                continue
            cut = [c for c in j.data["calls"] if not c.get("done")]
            act(f"resume {where}{whose}, after {', '.join(j.data['steps']) or 'nothing'}"
                + (f", session {cut_session(cut[0], j.run / 'run') or 'fresh'}" if cut else ""))
            if not dry_run:
                self.run_stage(n, rank, lambda r=rec: self.resume(r), recovering=True)
        for n, issue in sorted(issues.items()):
            phase = self.watched(issue, rows)
            if phase is None:
                continue
            found = self.open_started(n)
            if found is None:
                continue
            rank, run, at = found
            j = journal.Journal.load(self.runs / run) if run else None
            if j is not None and (not j.unfinished or str(j.run) == paused):
                continue
            if not self.stalled(n, phase, issue):
                act(f"leave the {rank}'s cut stage on issue {n}: a stage is due, the cycle runs it")
                continue
            labels = {x["name"] for x in issue.get("labels", [])}
            again = next((lab for lab in reversed(FLOW) if lab in labels), "mission")
            if again == "build:open":
                again = "review:open"
            act(f"stop the {rank} on issue {n}: started {at.isoformat()}, nothing to resume from")
            if not dry_run:
                self.comment(n, f"stopped rank={rank} run={run or 'none'}",
                             f"**Fleet dispatcher: the {rank}'s stage started {at.isoformat()} "
                             f"was cut off and left nothing to resume from; label unchanged.** "
                             f"To run it again, apply `{again}` again.")
        (self.out if dry_run else self.log)(
            f"the search on start: {len(said)} stage(s) acted on" if said
            else "the search on start: nothing to resume")
        return said

    def reclaim_boundaries(self, rows: dict[str, str]) -> None:
        """A reclaim on the timer, and at each merge: a phase whose row was 🚧
        on master at the last cycle and is ✅ now (Phase 390, F221)."""
        if not self.disks or not rows:
            return
        merged = [p for p in self.load().get("active", []) if rows.get(p) == roadmap_check.DONE]
        for p in merged:
            self.reclaim(f"phase {p} merged")
        if not merged and self.reclaim_due():
            self.reclaim(f"the {RECLAIM_HOURS:g}-hour timer")
        state = self.load()
        state["active"] = sorted(p for p, s in rows.items() if s == roadmap_check.ACTIVE)
        self.save(state)

    def cycle(self) -> None:
        self.update_mirror()
        self.sweep()
        self.reclaim_boundaries(self.master_rows())
        state = self.load()
        if "quartermaster_since" not in state:
            # The Quartermaster judges a `merge:needs-review` applied from now on
            # (Phase 391): not #14's, nor any older issue's, until the operator
            # applies the label again.
            state["quartermaster_since"] = self.now().isoformat(timespec="seconds")
            self.save(state)
            self.log(f"the Quartermaster judges merge:needs-review applied after "
                     f"{state['quartermaster_since']}")
        paused = state.get("paused")
        if paused:
            if self.now() < _time(paused["until"]):
                self.log(f"paused until {paused['until']}: no model stage this cycle")
                return
            self.log(f"resume: {paused['stage']} from {paused.get('run')}, after its reset "
                     f"{paused['until']}")
            # `paused` stays until the stage ends (389 removed it first, and a
            # kill during the resumed stage lost it: Step 0, S0-2).
            self.run_stage(paused.get("issue"), STAGE_RANK[paused["stage"]],
                           lambda: self.resume(paused), recovering=True)
            state = self.load()
            if state.get("paused") == paused:
                state.pop("paused")
                self.save(state)
            if state.get("paused"):
                return
        rows = self.master_rows()
        for issue in self.issues_open():
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
            except Stop as e:
                self.say_stopped(n, rank, str(e))
                self.log(f"issue {n}: stopped: {e}")
                continue
            if chosen is not None:
                why = self.space_refusal()
                if why:
                    self.hold_for_space(n, chosen[0], f"no new stage: {why}")
                    continue
                self.run_stage(n, *chosen)
        if not self.load().get("paused"):
            entry = self.next_due(rows)
            if entry is not None:
                why = self.space_refusal()
                if why:
                    self.log(f"next: phase {entry.phase} held, no new stage: {why}")
                else:
                    self.run_stage(None, "next", lambda: self.stage_next(dict(entry.__dict__)))
        day = None if self.load().get("paused") else self.digest_day()
        if day is not None:
            why = self.space_refusal()
            if why:
                self.log(f"digest: held, no new stage: {why}")
            else:
                self.run_stage(None, "digest", lambda: self.stage_digest(day))
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
    rc = sub.add_parser("recover")
    rc.add_argument("--dry-run", action="store_true", required=True,
                    help="print what the search on start would do; write nothing")
    sub.add_parser("reclaim", help="hand Ubuntu's freed space back to Windows; print the line "
                                   "a handoff records")
    a = ap.parse_args(argv)
    if a.cmd == "recover":
        # Read-only beside a running service: no lock, no token, no mirror update.
        said = Fleet(state=STATE, token="").recover(dry_run=True)
        print(f"{len(said)} stage(s) to act on" if said else "nothing to resume")
        return 0
    if a.cmd == "reclaim":
        # Beside a running service, which holds the lock: the log line only.
        line = Fleet(state=STATE, token="", disks=DISKS, trim=FSTRIM,
                     out=lambda s: None).reclaim("by hand", record=False)
        print(line)
        return 1 if "fstrim: failed" in line else 0
    try:
        held = lock(STATE)
        fleet = Fleet(state=STATE, token=load_token(TOKEN_FILE),
                      sweep_hours=getattr(a, "sweep_hours", SWEEP_HOURS), disks=DISKS,
                      trim=FSTRIM)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 4
    with held:
        if a.cmd == "usage":
            usage = fleet.usage()
            for what, (pct, reset) in (usage or {}).items():
                print(f"{what}: {pct}% used, resets {reset.isoformat() if reset else 'unknown'}")
            return 0 if usage else 1
        if a.sweep_hours != SWEEP_HOURS:
            fleet.log(f"the sweep at {a.sweep_hours} hours, not {SWEEP_HOURS}: a proof run")
        try:
            fleet.recover()
        except Exception:  # noqa: BLE001 — logged, and the loop starts all the same
            fleet.log("the search on start failed:\n" + traceback.format_exc())
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
