"""Phase 392, F226: C: free and the disk image's size, before and after a stage.

    .venv/bin/python docs/phases/in_progress/392_disk_proof.py <state-dir> <commit> [--full|--fast]

One model-free run of <commit> exactly as the dispatcher makes it (this
branch's `Fleet.check_run`: a fresh clone in the fence, no model, no token;
`--full` is `wholetree.sh --full` then `regression.sh`), in its own state
folder so the service's runs are not touched. Before and after: C: free
(`shutil.disk_usage("/mnt/c")`), the image's size (`C:\\WSL\\Ubuntu-26.04\\ext4.vhdx`
through `/mnt/c`), Ubuntu's root free, and what the run's `run/tmp` holds
after the stage (F226 deletes all but the worker-loss folders). Prints one
JSON record. The operator's rule for the proof (392's prompt): if the image
still grows with each stage once the files are deleted, that is a stop.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
import dispatcher as D  # noqa: E402

IMAGE = pathlib.Path("/mnt/c/WSL/Ubuntu-26.04/ext4.vhdx")


def disk() -> dict:
    return {"at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "c_free_gb": round(shutil.disk_usage("/mnt/c").free / 1e9, 2),
            "image_gb": round(IMAGE.stat().st_size / 1e9, 2),
            "ubuntu_free_gb": round(shutil.disk_usage("/").free / 1e9, 2)}


def main(argv: list[str]) -> int:
    state, commit = pathlib.Path(argv[0]).resolve(), argv[1]
    full = "--fast" not in argv
    clone = state / "source"
    if not clone.exists():
        subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(ROOT), str(clone)], check=True)
    subprocess.run(["git", "-C", str(clone), "fetch", "-q", str(ROOT), commit], check=True)
    fleet = D.Fleet(state=state, token="", venv=D.STATE / "venv", out=lambda s: None)
    before = disk()
    c = fleet.check_run(clone, commit, full=full)
    after = disk()
    run = max(p for p in fleet.runs.iterdir() if p.name.endswith("_check"))
    tmp = run / "run" / "tmp"
    print(json.dumps({"commit": commit, "full": full, "ok": c.ok, "line": c.line, "why": c.why[-300:],
                      "run": str(run), "before": before, "after": after,
                      "tmp_left": sorted(p.name for p in tmp.iterdir()) if tmp.is_dir() else [],
                      "pid": os.getpid()}, indent=1))
    return 0 if c.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
