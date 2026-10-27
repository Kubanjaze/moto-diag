#!/usr/bin/env python3
"""Phase 392, F227: one fenced xdist run, each process's open files sampled
from outside the fence once a second.

    fd_probe.py <run-dir> <commit> [--limit N] [-- pytest args…]

A fresh clone of the operator's checkout at <commit> goes to <run-dir>/clone;
the fence (fence.sh, --net none, the fleet's venv) runs pytest -n auto in it.
Every process descended from fence.sh is read: /proc/<pid>/fd counted, the
peak kept per pid, with the test the worker had started at that moment (its
worker_loss `<gw>.last` file). `--limit N` runs the fence under `prlimit
--nofile=N` (the planted small-limit case). Prints one JSON summary.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time

REPO = pathlib.Path.home() / "Projects" / "moto-diag"
FENCE = REPO / ".claude" / "skills" / "fleet" / "fence.sh"
STATE = pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet"


def children(root: int) -> set[int]:
    parent: dict[int, int] = {}
    for p in pathlib.Path("/proc").iterdir():
        if p.name.isdigit():
            try:
                parent[int(p.name)] = int((p / "stat").read_text().rsplit(")", 1)[1].split()[1])
            except (OSError, IndexError, ValueError):
                pass
    out, todo = set(), [root]
    while todo:
        x = todo.pop()
        for c, pp in parent.items():
            if pp == x and c not in out:
                out.add(c)
                todo.append(c)
    return out


def fds(pid: int) -> int | None:
    try:
        return len(os.listdir(f"/proc/{pid}/fd"))
    except OSError:
        return None


def cmd(pid: int) -> str:
    try:
        return pathlib.Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode()[:160]
    except OSError:
        return ""


def last_tests(run: pathlib.Path) -> dict[str, str]:
    """{inner pid: the test it started} from worker_loss's files."""
    out = {}
    for f in (run / "tmp").glob("motodiag_worker_loss_*/gw*.last"):
        try:
            lines = f.read_text().splitlines()
        except OSError:
            continue
        if lines and lines[0].startswith("pid "):
            out[lines[0][4:]] = (f.stem, lines[1][8:] if len(lines) > 1 else "")
    return out


def nspid(pid: int) -> str | None:
    try:
        for ln in pathlib.Path(f"/proc/{pid}/status").read_text().splitlines():
            if ln.startswith("NSpid:"):
                return ln.split()[-1]
    except OSError:
        return None
    return None


def main(argv: list[str]) -> int:
    run = pathlib.Path(argv[0]).resolve()
    commit = argv[1]
    limit = None
    rest = argv[2:]
    if rest[:1] == ["--limit"]:
        limit, rest = int(rest[1]), rest[2:]
    if rest[:1] == ["--"]:
        rest = rest[1:]
    pytest_args = rest or ["-n", "auto", "--dist", "load", "-q", "-p", "no:cacheprovider"]
    (run / "run").mkdir(parents=True, exist_ok=True)
    clone = run / "clone"
    if not clone.exists():
        subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(REPO), str(clone)], check=True)
        subprocess.run(["git", "-C", str(clone), "checkout", "-q", "--detach", commit], check=True)
    argv_f = [str(FENCE), "--clone", str(clone), "--run", str(run / "run"),
              "--workspace-docs", str(pathlib.Path.home() / "Projects" / "workspace-docs"),
              "--net", "none", "--venv", str(STATE / "venv"), "--",
              ".venv/bin/python", "-m", "pytest", *pytest_args]
    if limit:
        argv_f = ["prlimit", f"--nofile={limit}:{limit}", "--", *argv_f]
    out = (run / "run" / "pytest.txt").open("w")
    t0 = time.time()
    p = subprocess.Popen(argv_f, stdout=out, stderr=subprocess.STDOUT, cwd=clone,
                         env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                         stdin=subprocess.DEVNULL)
    peak: dict[int, dict] = {}
    samples = 0
    while p.poll() is None:
        tests = last_tests(run / "run")
        for pid in children(p.pid):
            n = fds(pid)
            if n is None:
                continue
            if n > peak.get(pid, {}).get("fds", -1):
                inner = nspid(pid)
                gw, test = tests.get(inner or "", ("", ""))
                peak[pid] = {"fds": n, "at_s": round(time.time() - t0), "worker": gw,
                             "test": test, "cmd": cmd(pid)}
        samples += 1
        time.sleep(1)
    out.close()
    text = (run / "run" / "pytest.txt").read_text(errors="replace").strip().splitlines()
    top = sorted(peak.items(), key=lambda kv: -kv[1]["fds"])[:12]
    print(json.dumps({"commit": commit, "limit": limit, "exit": p.returncode,
                      "wall_s": round(time.time() - t0), "samples": samples,
                      "processes_seen": len(peak),
                      "summary": text[-1] if text else "",
                      "errno24": sum("Too many open files" in ln for ln in text),
                      "peaks": [{"pid": k, **v} for k, v in top]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
