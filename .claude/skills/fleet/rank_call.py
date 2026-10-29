"""One read-only `claude -p` call for a fleet rank, and the stops around it.

Two callers: `xo.py` (the verdict on a plan) and `yeoman.py digest` (the
day's summary). Both ranks are read-only, and the fence is the tool list
itself, measured in Phase 387's Step 0 (S0-2): with these flags the
session is offered Glob, Grep and Read and nothing else, and a planted Bash
call made no file while the control, with Bash allowed, made it.

**The model's text is never acted on unchecked.** A call is a stop, raised
as `Stop` and never turned into a verdict, when:
  - claude exits non-zero, prints no JSON, or reports `is_error`;
  - the model asked for is not among the models served (`modelUsage`);
  - the JSON carries no token usage ("a call with no recorded usage is a
    stop", the operator's prompt for 387);
  - a schema was asked for and `structured_output` is missing.

Every call that returns is recorded: session id, served model, the four
token counts, list cost, turns and wall time, appended to a ledger outside
the repository (`LEDGER`, or `$FLEET_LEDGER`).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]

#: The full ids, never the aliases: a moved alias cannot change the model
#: silently. Measured served on this login at Step 0 (S0-1).
FABLE, OPUS, HAIKU = "claude-fable-5-1", "claude-opus-5-5", "claude-haiku-5-5"

#: Where credentials live on this Mac. Reading needs no permission, so
#: without these a rank could Read the login token in
#: ~/.config/motodiag/anthropic.env and quote it into a public issue comment
#: (the XO's own observation on 387's v1.0; Bug fix #1). Denied to Read,
#: Grep and Glob alike, measured with a canary under ~/.config. A denylist,
#: not a confinement: a path not named here can still be read (F215).
SECRET_HOMES = ("~/.config/**", "~/.ssh/**", "~/.claude/**", "~/.claude.json",
                "~/.subconscious/**", "~/.aws/**", "~/.gnupg/**", "~/.docker/**", "~/.netrc",
                "~/.npmrc", "~/.pypirc", "~/Library/**", "~/.zsh_history", "~/.bash_history")
DENIED = ",".join(["Bash"] + [f"{tool}({path})" for tool in ("Read", "Grep", "Glob")
                              for path in SECRET_HOMES])

#: The read-only fence. `--tools` decides which tools exist; the rest are a
#: second lock if it is ever dropped (S0-2's "second lock alone" case).
FENCE = ("--tools", "Read,Grep,Glob", "--allowedTools", "Read,Grep,Glob",
         "--disallowedTools", DENIED, "--permission-mode", "dontAsk", "--strict-mcp-config")
#: One turn and no tools (Phase 389, the Science Officer): what the model
#: reads is bounded by what the script hands it, 257's candidates shape.
NO_TOOLS = ("--tools", "", "--permission-mode", "dontAsk", "--strict-mcp-config")

LEDGER = pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet" / "calls.jsonl"

Runner = Callable[..., subprocess.CompletedProcess]


class Stop(Exception):
    """The call cannot be acted on; the stage leaves the label where it was."""


class LaunchFailed(Stop):
    """The model call could not be started (Phase 394): an `OSError` from the
    launch, such as a brief over Linux's 128 KiB limit on one argument. A
    `Stop`, so the stage stops once and the cycle goes on."""

    def __init__(self, e: OSError):
        super().__init__(f"the model call could not start: {e}")


@dataclass
class Call:
    rank: str
    model: str
    session_id: str
    served: list[str]
    input_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    output_tokens: int
    cost_usd: float
    turns: int
    wall_s: float
    at: str
    structured: dict | None
    result: str

    def line(self) -> str:
        return (f"{self.rank}: {self.model}, session `{self.session_id}`, input {self.input_tokens}, "
                f"cache write {self.cache_write_tokens}, cache read {self.cache_read_tokens}, "
                f"output {self.output_tokens}, {self.turns} turns, {self.wall_s:.0f} s, "
                f"${self.cost_usd:.2f} at list price")


def command(model: str, schema: dict | None = None,
            tools: tuple[str, ...] = FENCE) -> list[str]:
    """The call's argv. The brief is not in it: `call` hands it to `claude -p`
    on standard input (Phase 394), which has no size limit an argument has."""
    cmd = ["claude", "-p", "--model", model, *tools, "--output-format", "json"]
    if schema is not None:
        cmd += ["--json-schema", json.dumps(schema)]
    return cmd


def call(rank: str, prompt: str, model: str, schema: dict | None = None, *,
         cwd: pathlib.Path = ROOT, run: Runner = subprocess.run, timeout: int = 1800,
         ledger: pathlib.Path | None = None, tools: tuple[str, ...] = FENCE) -> Call:
    """One fenced call. Returns the recorded Call, or raises Stop."""
    try:
        r = run(command(model, schema, tools), input=prompt, capture_output=True, text=True,
                cwd=cwd, timeout=timeout)
    except OSError as e:
        raise LaunchFailed(e) from e
    if r.returncode != 0:
        raise Stop(f"claude exited {r.returncode}: {(r.stderr or r.stdout).strip()[:300]}")
    try:
        d = json.loads(r.stdout)
    except ValueError:
        raise Stop(f"claude printed no JSON: {r.stdout.strip()[:200]!r}") from None
    if d.get("is_error"):
        raise Stop(f"claude reported an error: {str(d.get('result'))[:300]}")
    served = sorted((d.get("modelUsage") or {}).keys())
    if model not in served:
        raise Stop(f"asked for {model}, served {served or 'nothing'}")
    u = d.get("usage") or {}
    counts = [int(u.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens",
                                           "cache_read_input_tokens", "output_tokens")]
    if not d.get("session_id") or sum(counts) == 0:
        raise Stop("the call recorded no token usage or no session id")
    if schema is not None and not isinstance(d.get("structured_output"), dict):
        raise Stop("a schema was asked for and the JSON has no structured_output")
    c = Call(rank, model, d["session_id"], served, *counts, float(d.get("total_cost_usd") or 0),
             int(d.get("num_turns") or 0), (d.get("duration_ms") or 0) / 1000,
             dt.datetime.now().astimezone().isoformat(timespec="seconds"),
             d.get("structured_output"), str(d.get("result") or ""))
    # A call a resumed stage replays from its journal was recorded when it ran (Phase 390).
    if not d.get("fleet_replayed"):
        record(c, ledger)
    return c


def record(c: Call, ledger: pathlib.Path | None = None) -> pathlib.Path:
    path = ledger or pathlib.Path(os.environ.get("FLEET_LEDGER") or LEDGER)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({k: v for k, v in asdict(c).items() if k != "result"}) + "\n")
    return path


def gh(args: list[str], *, run: Runner = subprocess.run, cwd: pathlib.Path = ROOT
       ) -> subprocess.CompletedProcess:
    """`gh` with the arguments given; the caller reads the return code."""
    return run(["gh", *args], capture_output=True, text=True, cwd=cwd, timeout=120)
