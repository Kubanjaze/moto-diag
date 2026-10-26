"""Phase 390's kill test: one dispatcher process on 389's stand-ins.

    python fleet_kill_driver.py first  BASE   a cycle; its first model call hangs
    python fleet_kill_driver.py second BASE   a new process: recover(), then a cycle

The stand-in GitHub lives in BASE/github.json, written after every `gh`
call, so it outlives a SIGKILL. In `first`, the Science Officer's first
model call writes its transcript and then never returns: the test kills the
process group there, as systemd does. Each model call's command is appended
to BASE/model_calls.jsonl.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
sys.path.insert(0, str(ROOT / "tests"))

import dispatcher as D  # noqa: E402
from test_phase390_resume import SCOUT, Hub, transcript  # noqa: E402


class Now:
    def __call__(self) -> dt.datetime:
        return dt.datetime.now().astimezone()


class DiskHub(Hub):
    def __init__(self, base: pathlib.Path, hang: bool):
        super().__init__(Now(), base / "fence.sh")
        self.base, self.hang = base, hang
        self.issues = {int(k): v for k, v in json.loads((base / "github.json").read_text()).items()}
        self.replies = [] if hang else list(SCOUT)

    def __call__(self, cmd, **kw):
        cmd = list(cmd)
        if cmd[0] == self.fence:
            inner = cmd[cmd.index("--") + 1:]
            with (self.base / "model_calls.jsonl").open("a") as f:
                f.write(json.dumps(inner[:3]) + "\n")
            if self.hang:
                transcript(cmd)
                (self.base / "hanging").write_text("in the model call\n")
                while True:
                    time.sleep(1)
        r = super().__call__(cmd, **kw)
        if cmd[0] == "gh":
            (self.base / "github.json").write_text(json.dumps(self.issues))
        return r


def main(mode: str, base: pathlib.Path) -> int:
    host = DiskHub(base, hang=mode == "first")
    fleet = D.Fleet(state=base / "state", token="sk-ant-oat01-test-token", host=host,
                    fence=base / "fence.sh", workspace_docs=base / "wsd",
                    repo_url=str(base / "origin"), now=host.clock, out=print,
                    identity_file=base / "no-identity.env",
                    check=lambda clone, commit, *, full, command=None: D.Check(True, commit),
                    sleep=lambda s: None, venv=base / "no-venv", mobile=base / "no-mobile")
    if mode == "second":
        fleet.recover()         # what a start does before its first cycle
    else:
        fleet.cycle()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], pathlib.Path(sys.argv[2])))
