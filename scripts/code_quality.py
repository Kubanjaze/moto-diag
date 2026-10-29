#!/usr/bin/env python3
"""The code's own quality, measured: one implementation (Phase 393, K54).

Until 393 nothing checked how the code is written: the linter was
configured and never run, the type hints never checked, coverage never
measured. This module measures, and four callers read it:

- the ratchet, `tests/test_phase393_quality_ratchet.py`, against the pins in
  `tests/support/quality_counts.py`;
- `regression.sh`, through `coverage-gate`: a total below the pin is a
  failed run, not of record;
- the Quartermaster's Q10-Q12 (`pr`, run in the fleet's fence with no
  model and no network; Q11 from the full run's coverage JSON);
- the weekly page, `.claude/skills/fleet/quality_report.py`.

**The seven counts** (`counts`), each by a rule, never a list:

  ruff        `ruff check src`, the rules `pyproject.toml` selects
  mypy        `mypy` with `[tool.mypy]`: `src/motodiag`, no site-packages,
              so the count is the same in every environment
  complex     functions over McCabe 20: `ruff check src --select C901`
  big         files in `src/` over 100 KB (100,000 bytes, the operator's KB)
  helpers     private functions named `_money`, `_now` or `_now_iso`
  swallowed   `except Exception` handlers whose body is only `pass`
  coverage    total line coverage, from a coverage JSON

    code_quality.py counts [--root DIR] [--coverage JSON]
    code_quality.py pr --base SHA [--root DIR]          # Q10 and Q12, JSON
    code_quality.py coverage-gate JSON COMMIT           # the regression's line
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = "src"
PACKAGE = "src/motodiag"
#: K54: "100 KB per file". KB as the prompt counts it: core/migrations.py,
#: 572,812 bytes, is its "573 KB".
SIZE_LIMIT = 100_000
#: K54: "McCabe 20". Set as `[tool.ruff.lint.mccabe] max-complexity` too,
#: read only when C901 is selected; passed here so a tree's own setting
#: cannot change it.
COMPLEXITY_LIMIT = 20
#: K54: "85% changed-line coverage".
CHANGED_COVERAGE = 85.0
HELPER_NAMES = frozenset({"_money", "_now", "_now_iso"})
#: `ruff check --fix` leaves the migrations alone (393's clean-up); the count
#: includes them.
FIX_EXCLUDE = ("src/motodiag/core/migrations.py", "src/motodiag/core/migration_*_rows.py")

_MYPY_LINE = re.compile(r"^(?P<file>[^:\n]+\.py):(?P<line>\d+): error: ", re.M)
_COMPLEX = re.compile(r"`(?P<name>[^`]+)` is too complex \((?P<n>\d+) > \d+\)")


def _tool(name: str) -> list[str]:
    """The tool beside this interpreter (the venv's), else on PATH."""
    here = pathlib.Path(sys.executable).parent / name
    return [str(here)] if here.exists() else [name]


def _py_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted((root / SRC).rglob("*.py"))


# ---------------------------------------------------------------- ruff
def ruff_findings(root: pathlib.Path, *, select: str | None = None,
                  config: pathlib.Path | None = None) -> list[dict]:
    """Every finding ruff reports over `src/`, as its JSON gives them."""
    cmd = [*_tool("ruff"), "check", SRC, "--no-cache", "--output-format", "json",
           "--exit-zero"]
    if config is not None:
        cmd += ["--config", str(config)]
    if select:
        cmd += ["--select", select, "--config", f"lint.mccabe.max-complexity={COMPLEXITY_LIMIT}"]
    r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ruff failed: {r.stderr.strip()[:300]}")
    found = json.loads(r.stdout or "[]")
    for f in found:
        f["path"] = pathlib.Path(f["filename"]).resolve().relative_to(root.resolve()).as_posix()
    return found


def by_file(found: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for f in found:
        out[f["path"]] = out.get(f["path"], 0) + 1
    return out


def complex_functions(root: pathlib.Path, config: pathlib.Path | None = None) -> list[dict]:
    """[{path, line, name, n}] for each function over the limit."""
    out = []
    for f in ruff_findings(root, select="C901", config=config):
        m = _COMPLEX.search(f["message"])
        if m:
            out.append({"path": f["path"], "line": f["location"]["row"],
                        "name": m.group("name"), "n": int(m.group("n"))})
    return out


# ---------------------------------------------------------------- mypy
def mypy_errors(root: pathlib.Path, config: pathlib.Path | None = None) -> dict[str, int]:
    """Errors per file (paths relative to `root`), with `[tool.mypy]`."""
    cfg = config if config is not None else root / "pyproject.toml"
    with tempfile.TemporaryDirectory(prefix="mypy-cache-") as cache:
        r = subprocess.run([sys.executable, "-m", "mypy", "--config-file", str(cfg),
                            "--cache-dir", cache, "--no-error-summary", PACKAGE],
                           cwd=root, capture_output=True, text=True)
    if r.returncode not in (0, 1):
        raise RuntimeError(f"mypy failed (exit {r.returncode}): {(r.stderr or r.stdout)[-300:]}")
    out: dict[str, int] = {}
    for m in _MYPY_LINE.finditer(r.stdout):
        p = m.group("file").replace("\\", "/")
        out[p] = out.get(p, 0) + 1
    return out


# ------------------------------------------------------------ by ast
def big_files(root: pathlib.Path) -> dict[str, int]:
    return {p.relative_to(root).as_posix(): p.stat().st_size
            for p in _py_files(root) if p.stat().st_size > SIZE_LIMIT}


def _trees(root: pathlib.Path):
    for p in _py_files(root):
        yield p.relative_to(root).as_posix(), ast.parse(p.read_text(encoding="utf-8"))


def helpers(root: pathlib.Path) -> list[str]:
    """`path:line name` for each private money or time helper."""
    return [f"{rel}:{n.lineno} {n.name}" for rel, tree in _trees(root) for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in HELPER_NAMES]


def is_swallowed(h: ast.ExceptHandler) -> bool:
    """`except Exception` (named or not) whose body is only `pass`."""
    return (isinstance(h.type, ast.Name) and h.type.id == "Exception"
            and all(isinstance(b, ast.Pass) for b in h.body))


def swallowed(root: pathlib.Path) -> list[str]:
    return [f"{rel}:{n.lineno}" for rel, tree in _trees(root) for n in ast.walk(tree)
            if isinstance(n, ast.ExceptHandler) and is_swallowed(n)]


# ------------------------------------------------------------ coverage
def coverage_total(cov_json: pathlib.Path) -> float:
    return float(json.loads(cov_json.read_text(encoding="utf-8"))["totals"]["percent_covered"])


def counts(root: pathlib.Path = ROOT, cov_json: pathlib.Path | None = None) -> dict[str, object]:
    out: dict[str, object] = {
        "ruff": len(ruff_findings(root)),
        "mypy": sum(mypy_errors(root).values()),
        "complex": len(complex_functions(root)),
        "big": len(big_files(root)),
        "helpers": len(helpers(root)),
        "swallowed": len(swallowed(root)),
    }
    if cov_json is not None:
        out["coverage"] = round(coverage_total(cov_json), 2)
    return out


# ------------------------------------------------- a pull request's lines
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.M)


def _git(root: pathlib.Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} failed: {r.stderr.strip()[:200]}")
    return r.stdout


def changed_lines(root: pathlib.Path, base: str) -> dict[str, set[int]]:
    """{path: the head's line numbers added or changed} for `.py` under `src/`."""
    out: dict[str, set[int]] = {}
    path = None
    for line in _git(root, "diff", "-U0", "--no-color", "-M", f"{base}...HEAD", "--",
                     SRC).splitlines():
        if line.startswith("+++ "):
            name = line[4:]
            path = name[2:] if name.startswith("b/") and name.endswith(".py") else None
        elif path and (m := _HUNK.match(line)):
            start, n = int(m.group(1)), int(m.group(2) or 1)
            if n:
                out.setdefault(path, set()).update(range(start, start + n))
    return out


def changed_coverage(cov_json: pathlib.Path, changed: dict[str, set[int]]
                     ) -> tuple[int, int, dict[str, tuple[int, int]]]:
    """(covered, measured, {path: (covered, measured)}) over the changed lines
    coverage can run: executed or missing in its JSON. A changed file the
    JSON does not hold at all counts every changed line as missed."""
    files = json.loads(cov_json.read_text(encoding="utf-8"))["files"]
    by = {pathlib.PurePosixPath(k.replace("\\", "/")).as_posix(): v for k, v in files.items()}
    per: dict[str, tuple[int, int]] = {}
    for path, lines in changed.items():
        entry = next((v for k, v in by.items() if k == path or k.endswith("/" + path)
                      or path.endswith("/" + k)), None)
        if entry is None:
            per[path] = (0, len(lines))
            continue
        ran, missed = set(entry["executed_lines"]), set(entry["missing_lines"])
        live = lines & (ran | missed)
        if live:
            per[path] = (len(live & ran), len(live))
    return sum(c for c, _ in per.values()), sum(m for _, m in per.values()), per


def _spans(path: pathlib.Path) -> dict[tuple[str, int], range]:
    """{(name, line): the lines of that def}, for every function in a file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {(n.name, n.lineno): range(n.lineno, (n.end_lineno or n.lineno) + 1)
            for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def base_tree(root: pathlib.Path, base: str, into: pathlib.Path) -> pathlib.Path:
    """The base's `src/` and `pyproject.toml`, unpacked under `into`."""
    tar = subprocess.run(["git", "-C", str(root), "archive", "--format=tar", base, SRC,
                          "pyproject.toml"], capture_output=True)
    if tar.returncode != 0:
        raise RuntimeError(f"git archive {base} failed: {tar.stderr.decode()[:200]}")
    subprocess.run(["tar", "-x", "-C", str(into)], input=tar.stdout, check=True)
    return into


def _config(base: pathlib.Path, head: pathlib.Path) -> pathlib.Path:
    """The base's pyproject.toml when it configures mypy, else the head's: a
    pull request is checked by the rules it came to, not by its own."""
    b = base / "pyproject.toml"
    return b if b.is_file() and "[tool.mypy]" in b.read_text(encoding="utf-8") else \
        head / "pyproject.toml"


def pr_checks(root: pathlib.Path, base: str, *, size_limit: int = SIZE_LIMIT
              ) -> dict[str, list[dict]]:
    """Q10 and Q12 over the head (`root`, checked out) against `base`.
    {"Q10": [...], "Q12": [...]}: each entry one failure, with its file and
    its numbers. `size_limit` is a parameter only so the size fixture can be
    small; every caller but its test takes K54's."""
    changed = changed_lines(root, base)
    touched = sorted(set(changed) | {
        p for p in _git(root, "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD",
                        "--", SRC).split() if p.endswith(".py")})
    q10: list[dict] = []
    q12: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="q10-base-") as tmp:
        b = base_tree(root, base, pathlib.Path(tmp))
        cfg = _config(b, root)
        ruff_h = by_file(ruff_findings(root, config=cfg))
        ruff_b = by_file(ruff_findings(b, config=cfg))
        mypy_h, mypy_b = mypy_errors(root, cfg), mypy_errors(b, cfg)
        for p in touched:
            for tool, h, bb in (("ruff", ruff_h, ruff_b), ("mypy", mypy_h, mypy_b)):
                if h.get(p, 0) > bb.get(p, 0):
                    q10.append({"file": p, "tool": tool, "head": h.get(p, 0),
                                "base": bb.get(p, 0)})
        for f in complex_functions(root, cfg):
            if f["path"] not in changed:
                continue
            span = _spans(root / f["path"]).get((f["name"].split(".")[-1], f["line"]))
            if span is not None and changed[f["path"]] & set(span):
                q12.append({"file": f["path"], "line": f["line"], "function": f["name"],
                            "complexity": f["n"], "limit": COMPLEXITY_LIMIT})
        for p in touched:
            head_size = (root / p).stat().st_size
            base_size = (b / p).stat().st_size if (b / p).is_file() else 0
            if head_size > size_limit and head_size > base_size:
                q12.append({"file": p, "bytes": head_size, "base_bytes": base_size,
                            "limit": size_limit})
    return {"Q10": q10, "Q12": q12}


def q11(cov_json: pathlib.Path | None, root: pathlib.Path, base: str) -> dict:
    """{"ok", "covered", "measured", "percent", "worst": [...]}."""
    changed = changed_lines(root, base)
    if not changed:
        return {"ok": True, "covered": 0, "measured": 0, "percent": None, "worst": []}
    if cov_json is None or not cov_json.is_file():
        return {"ok": False, "covered": 0, "measured": 0, "percent": None, "worst": [],
                "why": "the full run on the head left no coverage data"}
    covered, measured, per = changed_coverage(cov_json, changed)
    pct = 100.0 * covered / measured if measured else 100.0
    worst = sorted(({"file": p, "covered": c, "measured": m} for p, (c, m) in per.items()
                    if c < m), key=lambda x: x["covered"] / x["measured"])[:5]
    return {"ok": pct >= CHANGED_COVERAGE, "covered": covered, "measured": measured,
            "percent": round(pct, 1), "worst": worst}


# ------------------------------------------------------ the coverage gate
COVERAGE_PREFIX = "Line coverage of record:"
COVERAGE_LINE = re.compile(rf"^{re.escape(COVERAGE_PREFIX)} (\d+\.\d+)% at `([0-9a-f]{{7,40}})`",
                           re.M)


def pins(root: pathlib.Path = ROOT):
    """`tests/support/quality_counts.py`, the one place each pin lives."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "quality_counts", root / "tests" / "support" / "quality_counts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def coverage_gate(total: float, pin: float, commit: str) -> tuple[bool, str]:
    """(passes, the line regression.sh prints). Coverage may not fall below
    its pin (K54); a rise is said, so the pin can be raised to lock it in."""
    line = f"{COVERAGE_PREFIX} {total:.2f}% at `{commit}` (the pin is {pin:.2f}%)"
    if total < pin:
        return False, line + f": below the pin by {pin - total:.2f} points, so not of record"
    if total >= pin + 0.5:
        return True, line + (f": {total - pin:.2f} points above it; raise COVERAGE_PERCENT "
                             "to lock it in")
    return True, line


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="code_quality.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("counts")
    c.add_argument("--root", type=pathlib.Path, default=ROOT)
    c.add_argument("--coverage", type=pathlib.Path)
    p = sub.add_parser("pr")
    p.add_argument("--base", required=True)
    p.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    g = sub.add_parser("coverage-gate")
    g.add_argument("json", type=pathlib.Path)
    g.add_argument("commit")
    a = ap.parse_args(argv)
    if a.cmd == "counts":
        print(json.dumps(counts(a.root.resolve(), a.coverage), indent=1))
        return 0
    if a.cmd == "pr":
        print(json.dumps(pr_checks(a.root.resolve(), a.base)))
        return 0
    if not a.json.is_file():
        print(f"{COVERAGE_PREFIX} none: the run wrote no coverage data ({a.json})")
        return 1
    ok, line = coverage_gate(coverage_total(a.json), pins().COVERAGE_PERCENT, a.commit)
    print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
