"""A stage's journal: what a resumed stage needs (Phase 390, F219).

`runs/<run>/stage.json`, beside `clone/` and `run/`. The fence binds only
`run/` (as `/fleet/run`), so no model can write it. It is written before the
stage does anything (`Fleet.new_run`) and after each thing it finishes:

- `record`: the stage and its arguments, the pause record's shape, so a
  pause and a kill resume through the same door (`Fleet.resume`);
- `calls`: each model call in order: a hash of its command, the transcripts
  there before it, its session id once known, and its output once it ended;
- `checks`: each finished model-free run, by commit and kind;
- `steps`: each commit, push and GitHub write the stage has made;
- `ended`, `outcome`: set when the stage is over. A paused stage is not.

A process killed by systemd runs no `finally` (Step 0, S0-1), so nothing is
written at the moment of death: every write here happens before the step it
covers is relied on.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib

FILE = "stage.json"
BOOT_ID = pathlib.Path("/proc/sys/kernel/random/boot_id")


def boot_id() -> str:
    try:
        return BOOT_ID.read_text().strip()
    except OSError:
        return ""


def call_key(cmd: list[str]) -> str:
    """The command's hash: its model, tools and schema, with the prompt and
    `--resume <id>` left out. Not the prompt: a rank's prompt can read what
    its own stage already wrote (the Science Officer's census counts its own
    committed Step 0), so a replay sees a different prompt for the same call.
    Since Phase 394 the prompt is on stdin and `-p` is followed by a flag; that
    flag stays, so a command from before and one from after key the same."""
    plain = list(cmd)
    for flag in ("--resume", "-p"):
        if flag in plain:
            k = plain.index(flag)
            after = plain[k + 1] if k + 1 < len(plain) else ""
            del plain[k:k + 1 if flag == "-p" and after.startswith("--") else k + 2]
    return hashlib.sha256(json.dumps(plain).encode()).hexdigest()[:16]


class Journal:
    def __init__(self, run: pathlib.Path, data: dict, *, resumed: bool = False):
        self.run, self.data, self.resumed = run, data, resumed

    @classmethod
    def create(cls, run: pathlib.Path, record: dict, now: dt.datetime) -> Journal:
        data = {"record": {**record, "run": str(run)}, "pid": os.getpid(), "boot": boot_id(),
                "started": now.isoformat(timespec="seconds"), "calls": [], "checks": {},
                "steps": {}, "ended": None, "outcome": None}
        if record.get("session"):
            # A pause record written before the journal existed: its one
            # session belongs to whichever call comes first.
            data["calls"].append({"key": None, "known": [], "session": record["session"],
                                  "done": False})
        j = cls(run, data)
        j.save()
        return j

    @classmethod
    def load(cls, run: pathlib.Path) -> Journal | None:
        p = run / FILE
        if not p.is_file():
            return None
        try:
            return cls(run, json.loads(p.read_text(encoding="utf-8")))
        except ValueError:
            return None

    def save(self) -> None:
        p = self.run / FILE
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
        tmp.replace(p)

    @property
    def record(self) -> dict:
        return self.data["record"]

    @property
    def started(self) -> dt.datetime:
        return dt.datetime.fromisoformat(self.data["started"])

    @property
    def unfinished(self) -> bool:
        return self.data.get("ended") is None

    # ---- steps
    def done(self, step: str) -> bool:
        return step in self.data["steps"]

    def value(self, step: str):
        return self.data["steps"].get(step)

    def mark(self, step: str, value=True) -> None:
        self.data["steps"][step] = value
        self.save()

    # ---- model-free runs
    def check(self, key: str) -> dict | None:
        return self.data["checks"].get(key)

    def put_check(self, key: str, value: dict) -> None:
        self.data["checks"][key] = value
        self.save()

    # ---- model calls
    def call(self, k: int) -> dict | None:
        calls = self.data["calls"]
        return calls[k] if k < len(calls) else None

    def begin_call(self, k: int, key: str, known: list[str]) -> dict:
        """Call k starts: every later entry is dropped (they belonged to a
        replay that has ended)."""
        del self.data["calls"][k:]
        entry = {"key": key, "known": known, "session": None, "done": False}
        self.data["calls"].append(entry)
        self.save()
        return entry

    def update_call(self, k: int, **fields) -> None:
        self.data["calls"][k].update(fields)
        self.save()

    def end(self, outcome: str, now: dt.datetime) -> None:
        self.data["ended"] = now.isoformat(timespec="seconds")
        self.data["outcome"] = outcome[:300]
        self.save()


HELD = "held.json"


def hold(run: pathlib.Path, info: dict) -> None:
    """An Engineer run kept for the operator: its model-free run failed and
    nothing else did. `info`: issue, phase, rnd, commit. `prune_runs` keeps it."""
    tmp = run / (HELD + ".tmp")
    tmp.write_text(json.dumps(info, indent=1), encoding="utf-8")
    tmp.replace(run / HELD)


def held(run: pathlib.Path) -> dict | None:
    try:
        return json.loads((run / HELD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def release(run: pathlib.Path) -> None:
    (run / HELD).unlink(missing_ok=True)


def held_runs(runs: pathlib.Path, issue: int) -> list[pathlib.Path]:
    """The issue's held Engineer runs, newest first."""
    if not runs.is_dir():
        return []
    return [p for p in sorted(runs.iterdir(), reverse=True)
            if (info := held(p)) is not None and info.get("issue") == issue]


def unreadable(runs: pathlib.Path) -> list[pathlib.Path]:
    """Runs whose `stage.json` is there and cannot be read: said, and kept."""
    if not runs.is_dir():
        return []
    return [p for p in sorted(runs.iterdir())
            if (p / FILE).is_file() and Journal.load(p) is None]


def unfinished(runs: pathlib.Path) -> list[Journal]:
    """Every journal under `runs` with no `ended`, oldest first."""
    if not runs.is_dir():
        return []
    found = [j for p in sorted(runs.iterdir()) if p.is_dir()
             for j in [Journal.load(p)] if j is not None and j.unfinished]
    return sorted(found, key=lambda j: j.data["started"])
