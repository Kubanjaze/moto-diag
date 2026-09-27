#!/usr/bin/env python3
"""The whole-tree command (Phase 358, K1). ONE implementation of rule 3.

A whole-tree check is one whose verdict depends on the whole tree, not on
the files a commit touches. Before 358 they were a list kept by hand: rule 3
named four, the GLM prompt thirteen, and five red regressions in 257–260
each came from one the builder's own choice of tests did not run.

**Membership is computed, never listed.** A test file is whole-tree when it
enumerates a repo directory (`glob`, `rglob`, `os.walk`, `iterdir`,
`listdir`, `scandir`, `git ls-files`, `walk_packages`, `iter_modules`), or
imports or loads a helper that does. A new whole-tree test joins by itself.
Each member falls in one class, by what its enumeration reaches:

  code     `src/`, `tests/`, the ledger, git's file list (or via a helper)
  seed     only the seed JSON under `src/motodiag/knowledge/seed/`
  outside  only a library outside the repo

Two modes (the operator, 2026-09-27, option 3):

  wholetree.sh          fast: the code class, minus gates (a file whose name
                        says gate re-runs earlier gates) and the wheel build
                        (`test_phase209_packaging.py`); then finding_check
                        over completed/ and in_progress/. The push guard.
  wholetree.sh --full   every member, then the same finding_check scopes.
                        Required before the regression of record and before
                        a commit that changes seed data or migrations.py.

**The record.** A passing run on a tree whose working copy equals its index
writes a record under `.git/motodiag_wholetree/`, bound to the commit, the
tree hash and the sha256 of this command's own scripts, and signed with an
HMAC whose key only this command creates (`~/.config/motodiag/`). The push
guard accepts a record only if all four match; otherwise it runs fast mode
itself, and blocks when that fails or outruns `FAST_LIMIT_S`.

**The ceiling, stated.** The HMAC stops a record written by hand or by a
script that does not hold the key. A process that reads the key file can
forge one; this is a guard against mistakes and shortcuts, not against a
deliberate forger on this machine.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import hmac
import json
import os
import pathlib
import re
import secrets
import signal
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent

#: The guard's own limit for a fast run it starts itself: 3x fast mode's
#: measured wall time (the operator: "~3x the AC time, not 2x"; Low Power
#: Mode measured ~2.5x slower on the regression). Measured 2026-09-27: on
#: battery, 29.5-41.1 s (26-27 files), which first set 96 s; then on AC (the
#: 70 W adapter, charging up from 6%), 93.2 s and 94.9 s (28 files). The
#: formula takes the AC time: 3 x 94.9 s = 285 s. The hook timeout in
#: .claude/settings.json is 600 s, above this plus the guard's 60 s alarm
#: margin, because a hook that outruns ITS timeout is killed and the
#: command proceeds (fails open). See 358_phase_log.md.
FAST_LIMIT_S = 285

#: Paths whose change makes a commit a content commit, which needs --full.
CONTENT_PATHS = ("src/motodiag/knowledge/seed/", "src/motodiag/core/migrations.py")

_ENUM = re.compile(r"\.rglob\(|\.glob\(|os\.walk\(|\.iterdir\(|ls-files|walk_packages"
                   r"|iter_modules|glob\.glob\(|os\.listdir\(|os\.scandir\(")
_SEED = re.compile(r"\b(?:K|SEED|SEED_DIR|knowledge_dir|DTC_SEED)\)?\.glob\("
                   r"|SEED_DATA_DIR / \"knowledge\"\)\.glob\(")
_OUTSIDE = re.compile(r"\bout\.glob\(|lib / \"acquired\"|REAL / \"acquired\"")
_HELPER_DIRS = ("tests/support", "scripts", ".claude/skills")
_WHEEL_BUILD = "test_phase209_packaging.py"
#: A gate file: `_gate12`, `_gate_5`, `_gate_r`. Not `_gate_blind_spot` (244U).
_GATE = re.compile(r"_gate(?:_?\d+|_[a-z])(?:_|\.py$)")


# ---------------------------------------------------------------- the census
def enumerating_helpers(root: pathlib.Path = ROOT) -> list[str]:
    """Module names of the helpers that enumerate the tree."""
    names = []
    for d in _HELPER_DIRS:
        for p in sorted((root / d).rglob("*.py")):
            if _ENUM.search(p.read_text(encoding="utf-8", errors="replace")):
                names.append(p.stem)
    return sorted(set(names))


def census(root: pathlib.Path = ROOT) -> dict[str, list[str]]:
    """Every whole-tree test file, by class. Paths are relative to root."""
    helpers = enumerating_helpers(root)
    via = re.compile(r"(?:import|from) +(?:support\.)?(?:%s)\b|(?:%s)\.py" % (
        "|".join(map(re.escape, helpers)), "|".join(map(re.escape, helpers))))
    out: dict[str, list[str]] = {"code": [], "seed": [], "outside": []}
    for p in sorted((root / "tests").glob("test_*.py")):
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = [ln for ln in text.splitlines() if _ENUM.search(ln)]
        rel = p.relative_to(root).as_posix()
        if lines:
            kinds = {"seed" if _SEED.search(ln) else "outside" if _OUTSIDE.search(ln)
                     else "code" for ln in lines}
            # A file that enumerates is classed by what its own lines reach.
            cls = "code" if "code" in kinds else "seed" if "seed" in kinds else "outside"
            out[cls].append(rel)
        elif helpers and via.search(text):
            out["code"].append(rel)
    return out


def members(mode: str, root: pathlib.Path = ROOT) -> list[str]:
    c = census(root)
    if mode == "full":
        return sorted(c["code"] + c["seed"] + c["outside"])
    return [f for f in c["code"]
            if not _GATE.search(pathlib.Path(f).name) and pathlib.Path(f).name != _WHEEL_BUILD]


# ---------------------------------------------------------------- the record
def script_hash(here: pathlib.Path = HERE) -> str:
    h = hashlib.sha256()
    for name in ("wholetree.sh", "wholetree.py"):
        h.update(name.encode() + b"\0" + (here / name).read_bytes() + b"\0")
    return h.hexdigest()


def _git(root: pathlib.Path, *args: str, env: dict | None = None) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          check=True, env=env).stdout.strip()


def records_dir(root: pathlib.Path = ROOT) -> pathlib.Path:
    common = pathlib.Path(_git(root, "rev-parse", "--git-common-dir"))
    return (common if common.is_absolute() else root / common) / "motodiag_wholetree"


def key_path() -> pathlib.Path:
    return pathlib.Path.home() / ".config" / "motodiag" / "wholetree.key"


def _mac(key: bytes, fields: dict) -> str:
    body = json.dumps({k: v for k, v in fields.items() if k != "mac"}, sort_keys=True)
    return hmac.new(key, body.encode(), hashlib.sha256).hexdigest()


def tested_state(root: pathlib.Path = ROOT) -> tuple[str, str] | None:
    """(HEAD commit, index tree) when the working copy equals the index and
    nothing untracked is present; None otherwise (the run tested something
    no hash names)."""
    if subprocess.run(["git", "-C", str(root), "diff", "--quiet"]).returncode != 0:
        return None
    if _git(root, "ls-files", "--others", "--exclude-standard"):
        return None
    return _git(root, "rev-parse", "HEAD"), _git(root, "write-tree")


def write_record(mode: str, commit: str, tree: str, summary: str, wall: float,
                 root: pathlib.Path = ROOT, key_file: pathlib.Path | None = None,
                 rec_dir: pathlib.Path | None = None) -> pathlib.Path:
    key_file = key_file or key_path()
    if not key_file.exists():
        key_file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(fd, secrets.token_hex(32).encode()); os.close(fd)
    fields = {"version": 1, "mode": mode, "commit": commit, "tree": tree,
              "script_sha256": script_hash(), "passed": True, "summary": summary,
              "wall_s": round(wall, 1), "written_at": dt.datetime.now().isoformat(timespec="seconds")}
    fields["mac"] = _mac(key_file.read_bytes(), fields)
    rec_dir = rec_dir or records_dir(root)
    rec_dir.mkdir(parents=True, exist_ok=True)
    path = rec_dir / f"{tree}_{mode}.json"
    path.write_text(json.dumps(fields, indent=1, sort_keys=True))
    return path


def valid_record(tree: str, modes: tuple[str, ...], commit: str | None = None,
                 root: pathlib.Path = ROOT, key_file: pathlib.Path | None = None,
                 rec_dir: pathlib.Path | None = None) -> tuple[dict | None, str]:
    """The record for this tree, and why none is accepted when it is not.
    `commit=None` accepts any commit (a pre-commit check, where the commit
    does not exist yet); a push passes the commit it pushes."""
    key_file = key_file or key_path()
    rec_dir = rec_dir or records_dir(root)
    reasons = []
    for mode in modes:
        p = rec_dir / f"{tree}_{mode}.json"
        if not p.exists():
            reasons.append(f"no {mode} record for tree {tree[:12]}")
            continue
        try:
            rec = json.loads(p.read_text())
        except ValueError:
            reasons.append(f"{p.name} is not JSON"); continue
        if not key_file.exists():
            reasons.append("no record key: only wholetree.sh writes records"); continue
        if not hmac.compare_digest(str(rec.get("mac", "")), _mac(key_file.read_bytes(), rec)):
            reasons.append(f"{p.name} was not written by wholetree.sh (bad signature)"); continue
        if rec.get("tree") != tree or rec.get("mode") != mode or rec.get("passed") is not True:
            reasons.append(f"{p.name} does not record a pass of this tree"); continue
        if rec.get("script_sha256") != script_hash():
            reasons.append(f"{p.name} was made by a different wholetree script"); continue
        if commit is not None and rec.get("commit") != commit:
            reasons.append(f"{p.name} records commit {str(rec.get('commit'))[:12]}, "
                           f"not {commit[:12]}"); continue
        return rec, "ok"
    return None, "; ".join(reasons)


# ---------------------------------------------------------------- the run
@dataclasses.dataclass
class Result:
    passed: bool
    summary: str
    wall: float
    timed_out: bool = False


def run(mode: str, root: pathlib.Path = ROOT, py: str = sys.executable) -> Result:
    files = members(mode, root)
    print(f"wholetree {mode}: {len(files)} test files", flush=True)
    t0 = time.monotonic()
    proc = subprocess.run([py, "-B", "-m", "pytest", "-q", "-n", "auto", "--dist", "load", *files],
                          cwd=root, capture_output=True, text=True)
    tail = [ln for ln in proc.stdout.splitlines() if ln.strip()][-15:]
    summary = next((ln for ln in reversed(tail) if re.search(r"passed|failed|error", ln)), "no summary")
    ok = proc.returncode == 0
    if not ok:
        print("\n".join(tail))
    sys.path.insert(0, str(root / ".claude" / "skills" / "finding"))
    import finding_check
    for scope in ("docs/phases/completed", "docs/phases/in_progress"):
        fails = finding_check.check(root, phase_docs=scope)
        if fails:
            ok = False
            print(f"finding_check over {scope}:\n  " + "\n  ".join(fails))
    return Result(ok, summary.strip("= "), time.monotonic() - t0)


def run_bounded(mode: str, limit: float, root: pathlib.Path = ROOT) -> Result:
    """Run the COMMAND (wholetree.sh) with a deadline, as the guard does, and
    kill its whole process group when the deadline passes. The command writes
    the record itself; the caller only reads it."""
    t0 = time.monotonic()
    args = [str(HERE / "wholetree.sh")] + (["--full"] if mode == "full" else [])
    proc = subprocess.Popen(args, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return Result(False, f"ran out of time after {limit:.0f} s", time.monotonic() - t0, True)
    return Result(proc.returncode == 0, out.strip()[-1500:], time.monotonic() - t0)


def main(argv: list[str]) -> int:
    if argv[:1] == ["verify"]:                    # used by regression.sh
        mode = "full"
        commit, tree = _git(ROOT, "rev-parse", "HEAD"), _git(ROOT, "rev-parse", "HEAD^{tree}")
        rec, why = valid_record(tree, (mode,), commit)
        if rec is None:
            print(f"no passing `wholetree.sh --full` record for HEAD {commit[:12]}: {why}.\n"
                  "Run .claude/skills/closeout/wholetree.sh --full on this commit first.",
                  file=sys.stderr)
            return 2
        return 0
    if argv not in ([], ["--full"]):
        print("usage: wholetree.sh [--full]", file=sys.stderr)
        return 2
    mode = "full" if argv == ["--full"] else "fast"
    before = tested_state()
    res = run(mode)
    after = tested_state()
    print(f"wholetree {mode}: {'PASSED' if res.passed else 'FAILED'} — {res.summary} "
          f"({res.wall:.1f} s wall)")
    if not res.passed:
        return 1
    if before is None or before != after:
        print("wholetree: passed, but no record written: the working copy differs from the "
              "index, or has untracked files, or changed during the run.")
        return 0
    path = write_record(mode, before[0], before[1], res.summary, res.wall)
    print(f"wholetree: record {path.name} for commit {before[0][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
