"""Phase 390's live proofs: restart the fleet's service in the middle of one stage.

    python3 docs/phases/in_progress/390_proof.py STAGE ISSUE [--at model|check] [--close]

STAGE is the journal's stage name (scout, captain, xo, engineer, red_team,
recommend, digest). The script, on the home desktop, beside the service:

1. waits for that stage's journal to appear in the fleet's `runs/` (a run
   directory named `<stamp>_<stage>_390A`, or `<stamp>_digest`) with no
   `ended`, and then for the cut point: `model` (default), a transcript in
   its run (the model call is under way, S0-5), or `check`, the journal's
   model call done and its full model-free run started (F219's point);
2. refuses unless no #14 stage is running (the operator's rule) and
   nothing but that stage is running (the unit's processes);
3. restarts the service as 389 did: SIGTERM to its main process, which
   `Restart=always` brings back (no sudo for this unit);
4. waits for the new process's search on start to log `resume <stage> from
   <run>`, and with `--close` closes the planted ISSUE then, while the
   resumed stage runs, so the next cycle starts no other rank on it;
5. prints the times, the run, the session resumed and the resume line.

It never touches #14, PR #15 or the 389A branch.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

STATE = pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet"
LOG = STATE / "dispatcher.log"
UNIT = "motodiag-fleet.service"
REPO = "Kubanjaze/moto-diag"


def say(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def main_pid() -> int:
    return int(subprocess.run(["systemctl", "show", "-p", "MainPID", "--value", UNIT],
                              capture_output=True, text=True).stdout.strip() or 0)


def journal(run: pathlib.Path) -> dict | None:
    try:
        return json.loads((run / "stage.json").read_text())
    except (OSError, ValueError):
        return None


def find_run(stage: str, since: float) -> pathlib.Path | None:
    name = "digest" if stage == "digest" else f"{stage}_390A"
    for p in sorted((STATE / "runs").glob(f"*_{name}*"), reverse=True):
        j = journal(p)
        if j and j.get("ended") is None and p.stat().st_mtime >= since - 5:
            return p
    return None


def fourteen_running() -> bool:
    """A #14 stage started with no end line after it (the operator's rule)."""
    lines = [ln for ln in LOG.read_text().splitlines() if " issue 14: " in ln]
    return bool(lines) and not any(w in lines[-1] for w in (
        "checks failed", "stopped", "ready", "back,", "clear,", "recommendation:",
        "verdict applied", "needs hands", "step 0 pushed", "rate-limited", "failed:"))


def at_cut(run: pathlib.Path, at: str) -> bool:
    j = journal(run) or {}
    calls = j.get("calls") or []
    if at == "model":
        # A call under way: the journal's latest call unfinished, and its own
        # transcript there (a transcript alone may be a finished call's: the
        # first scout proof was cut between two calls that way).
        if not calls or calls[-1].get("done"):
            return False
        known = set(calls[-1].get("known") or [])
        return any(p.stem not in known
                   for p in (run / "run" / "claude" / "projects").glob("*/*.jsonl"))
    return bool(calls) and all(c.get("done") for c in calls) and not j.get("checks") \
        and any(p.name.endswith("_check") and p.stat().st_mtime >= run.stat().st_mtime
                for p in (STATE / "runs").iterdir())


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("issue", type=int)
    ap.add_argument("--at", choices=("model", "check"), default="model")
    ap.add_argument("--close", action="store_true")
    ap.add_argument("--wait", type=int, default=7200, help="seconds to wait for the stage")
    a = ap.parse_args(argv)
    if a.issue == 14:
        print("refused: #14 is the operator's")
        return 2
    start = time.time()
    run = None
    while time.time() - start < a.wait:
        run = run or find_run(a.stage, start)
        if run and at_cut(run, a.at):
            break
        time.sleep(2)
    else:
        print(f"SOMETHING IS OFF: no {a.stage} stage reached its cut point")
        return 1
    time.sleep(1 if a.at == "model" else 5)          # inside the call, or well inside the run
    if a.at == "model" and not at_cut(run, a.at):
        print(f"SOMETHING IS OFF: {run.name}'s call ended before the restart; run it again")
        return 1
    if (journal(run) or {}).get("ended"):
        print(f"SOMETHING IS OFF: {run.name} ended before the restart")
        return 1
    if fourteen_running():
        print("refused: a #14 stage is running")
        return 2
    pid = main_pid()
    say(f"cut point reached in {run.name} ({a.at}); restarting the service (PID {pid})")
    os.kill(pid, signal.SIGTERM)
    marker = f"resume {a.stage} from {run.name}"
    seen = LOG.stat().st_size
    t0 = time.time()
    while time.time() - t0 < 300:
        with LOG.open() as f:
            f.seek(seen)
            new = f.read()
        hit = next((ln for ln in new.splitlines() if marker in ln), None)
        if hit:
            say(f"service back: PID {main_pid()}")
            say(f"log: {hit}")
            if a.close:
                subprocess.run(["gh", "issue", "close", str(a.issue), "-R", REPO, "--comment",
                                "Closed by the Phase 390 planter: this issue's one rank has "
                                "been restarted and resumed; no other rank runs on it."],
                               check=True, capture_output=True)
                say(f"issue {a.issue} closed")
            print("ALL GOOD")
            return 0
        time.sleep(1)
    print("SOMETHING IS OFF: no resume line within five minutes")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
