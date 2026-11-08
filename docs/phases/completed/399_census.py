"""Phase 399's census (F254): which test files write rows into the cost ledger.

    .venv/bin/python docs/phases/in_progress/399_census.py [pytest args...]

The whole suite runs under a throwaway HOME, with FLEET_LEDGER unset, so the
default ledger (`rank_call.LEDGER`, `~/.local/state/motodiag/fleet/calls.jsonl`)
is a file under that HOME and nothing real can be written. Each xdist worker
gets its own HOME below the throwaway one, so no two tests append to the same
file at once, and a small plugin counts the worker's ledger rows before and
after each test. A file that writes is named with its rows, and how many of
them carry the stand-in's session id (`sess-1`).

Every ledger file under the throwaway HOME is counted at the end too, so a
row written outside any one test's window (a subprocess that outlives its
test) is still in the total. The operator's real ledger is hashed before and
after; the fleet may append to it meanwhile, and the rows it appended are
listed by rank and session so they can be told from a test's.

Only ~/.gitconfig is copied into the throwaway HOMEs (name and e-mail, so the
tests that commit can commit). Nothing reads live, reaches GitHub or makes a
model call. Run it only when `pgrep -x bwrap` is empty (F220).
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
REAL = pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet" / "calls.jsonl"
REL = pathlib.Path(".local") / "state" / "motodiag" / "fleet" / "calls.jsonl"
STAND_IN = "sess-1"
CHUNK = 40


def busy() -> bool:
    """A fleet sandbox is running (F220)."""
    return subprocess.run(["pgrep", "-x", "bwrap"], capture_output=True).returncode == 0

PLUGIN = '''
import json, os, pathlib, shutil
import pytest

REL = pathlib.Path(".local") / "state" / "motodiag" / "fleet" / "calls.jsonl"


def pytest_configure(config):
    wid = os.environ.get("PYTEST_XDIST_WORKER")
    if wid:
        home = pathlib.Path(os.environ["CENSUS_BASE"]) / wid
        home.mkdir(parents=True, exist_ok=True)
        git = pathlib.Path(os.environ["CENSUS_BASE"]) / "controller" / ".gitconfig"
        if git.is_file():
            shutil.copy(git, home / ".gitconfig")
        os.environ["HOME"] = str(home)


def _rows(p):
    try:
        return p.read_text(errors="replace").splitlines()
    except OSError:
        return []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    p = pathlib.Path(os.environ["HOME"]) / REL
    before = len(_rows(p))
    yield
    rows = _rows(p)[before:]
    if rows:
        sess = 0
        for ln in rows:
            try:
                sess += json.loads(ln).get("session_id") == "sess-1"
            except ValueError:
                pass
        out = pathlib.Path(os.environ["CENSUS_BASE"]) / "hits.jsonl"
        with out.open("a") as f:
            f.write(json.dumps({"nodeid": item.nodeid, "rows": len(rows), "sess1": sess,
                                "worker": os.environ.get("PYTEST_XDIST_WORKER", "-")}) + "\\n")
'''


def digest(p: pathlib.Path) -> tuple[int, int, str]:
    if not p.is_file():
        return 0, 0, "absent"
    b = p.read_bytes()
    return len(b), b.count(b"\n"), hashlib.sha256(b).hexdigest()


def main(argv: list[str]) -> int:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = pathlib.Path(tempfile.mkdtemp(prefix=f"399_census_{stamp}_",
                                         dir=pathlib.Path.home() / ".cache" / "motodiag"))
    plugin_dir = base / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "ledger_census.py").write_text(PLUGIN)
    controller = base / "controller"
    controller.mkdir()
    git = pathlib.Path.home() / ".gitconfig"
    if git.is_file():
        shutil.copy(git, controller / ".gitconfig")
    env = {k: v for k, v in os.environ.items() if k not in ("FLEET_LEDGER", "FLEET_STATE")}
    env.update(HOME=str(controller), CENSUS_BASE=str(base), PYTHONUTF8="1",
               PYTHONPATH=os.pathsep.join(filter(None, [str(plugin_dir),
                                                        env.get("PYTHONPATH", "")])))
    real_before = digest(REAL)
    real_rows_before = real_before[1]
    cmd = [str(ROOT / ".venv" / "bin" / "python"), "-m", "pytest", "-n", "auto", "--dist",
           "load", "-p", "ledger_census", "-q", "-o", "addopts=", "-p", "no:cacheprovider"]
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    print(f"census at {head}, throwaway HOME {base}", flush=True)
    print("command, per chunk of test files:", " ".join(cmd[1:]), "<files>", flush=True)
    # The suite in chunks, each started only while no fleet sandbox runs
    # (F220): a fleet stage is minutes long and polls every 5 minutes, so a
    # whole-suite run would overlap one. Whether a sandbox started during a
    # chunk is said for each chunk.
    files = argv or sorted(str(p.relative_to(ROOT)) for p in (ROOT / "tests").glob("test_*.py"))
    chunks = [files[i:i + CHUNK] for i in range(0, len(files), CHUNK)]
    t0, overlaps, worst = time.monotonic(), [], 0
    for n, chunk in enumerate(chunks, 1):
        while busy():
            time.sleep(30)
        c0, seen = time.monotonic(), False
        with (base / "pytest.out").open("a") as out:
            p = subprocess.Popen([*cmd, *chunk], cwd=ROOT, env=env, stdout=out,
                                 stderr=subprocess.STDOUT, text=True)
            while p.poll() is None:
                seen = seen or busy()
                time.sleep(5)
        worst = max(worst, p.returncode)
        if seen:
            overlaps.append(n)
        print(f"chunk {n}/{len(chunks)}: {len(chunk)} files, exit {p.returncode}, "
              f"{time.monotonic() - c0:.0f} s{', a fleet sandbox ran beside it' if seen else ''}",
              flush=True)
    wall = time.monotonic() - t0
    summary = [ln for ln in (base / "pytest.out").read_text(errors="replace").splitlines()
               if " in " in ln and ("passed" in ln or "failed" in ln)]
    counts = collections.Counter()
    for ln in summary:
        for num, word in re.findall(r"(\d+) (passed|failed|skipped|errors?)", ln):
            counts[word.rstrip("s") if word.startswith("error") else word] += int(num)
    print(f"pytest: {len(chunks)} chunks, worst exit {worst}, {wall / 60:.1f} min of chunks; "
          f"{dict(counts)}; a fleet sandbox beside chunks {overlaps or 'none'}")

    hits = [json.loads(ln) for ln in (base / "hits.jsonl").read_text().splitlines()] \
        if (base / "hits.jsonl").is_file() else []
    by_file: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0, 0])
    for h in hits:
        f = by_file[h["nodeid"].split("::", 1)[0]]
        f[0] += 1
        f[1] += h["rows"]
        f[2] += h["sess1"]
    total = sum(v[1] for v in by_file.values())
    print(f"\nfiles that wrote to the default ledger: {len(by_file)}; tests: {len(hits)}; "
          f"rows: {total}; of them {sum(v[2] for v in by_file.values())} carry {STAND_IN}")
    for name, (tests, rows, sess) in sorted(by_file.items(), key=lambda kv: (-kv[1][1], kv[0])):
        print(f"  {name}: {rows} rows from {tests} tests ({sess} {STAND_IN})")
    on_disk = 0
    for p in sorted(base.rglob("calls.jsonl")):
        if p.relative_to(base).parts[1:] == REL.parts:
            on_disk += digest(p)[1]
    print(f"rows in every default ledger under the throwaway HOME at the end: {on_disk}")

    real_after = digest(REAL)
    print(f"\nthe real ledger before: {real_before[0]} bytes, {real_before[1]} rows, "
          f"sha256 {real_before[2]}")
    print(f"the real ledger after:  {real_after[0]} bytes, {real_after[1]} rows, "
          f"sha256 {real_after[2]}")
    if real_after[2] != real_before[2]:
        new = REAL.read_text(errors="replace").splitlines()[real_rows_before:]
        kinds = collections.Counter()
        for ln in new:
            try:
                d = json.loads(ln)
                kinds[(d.get("rank"), d.get("session_id") == STAND_IN)] += 1
            except ValueError:
                kinds[("unreadable", False)] += 1
        print("  appended meanwhile (rank, stand-in?):", dict(kinds))
    print(f"\nkept: {base}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
