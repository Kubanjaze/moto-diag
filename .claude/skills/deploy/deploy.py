#!/usr/bin/env python3
"""The live-migration deploy, ONE implementation (Phase 358, K3).

Seven data phases (353, 354, 259, 260, 261, 264, 262) each wrote this step
again in a session scratchpad under /private/tmp, and the diff the operator
approved for migration 071 survived only by luck. This script is built from
Phase 262's `deploy262.py` (kept verbatim in `358_step0.md`). The operator's
requirements: "it writes the approved dry-run diff into the phase folder,
and the live apply refuses to run without that file. no more temp copies."
And, accepted at v1.0: "live apply refuses unless the diff file is committed
and unchanged."

    deploy.py dryrun <phase>       live is only read. Back up (SQLite backup
                                   API; ~/backups/motodiag/, 5 kept), migrate
                                   a copy, diff every table by rowid, check the
                                   scope, run the F158 census on the copy, and
                                   write docs/phases/in_progress/<phase>_dryrun_diff.md
    deploy.py apply-live <phase>   refuses unless: that file exists, is committed
                                   and unchanged, and records no scope problem;
                                   its backup still hashes as recorded; the
                                   scope file is the one it was made with; live
                                   equals the backup; and a fresh dry run on a
                                   new copy stays in scope. Then it migrates
                                   live, writes <phase>_live_diff.md and checks
                                   the scope again.

**The scope is data**, `docs/phases/in_progress/<phase>_deploy_scope.json`:

    {"tables": {
       "workflow_templates": {"added": 3},
       "checklist_items": {"added": 21, "changed": [
          {"where": "template_id = (select id from workflow_templates where slug = ?)
                     and sequence_number = ?",
           "params": ["generic_winterization_v1", 1],
           "fields": ["instruction_text", "expected_pass"]}]},
       "schema_version": {"added": 1}}}

Each `changed` entry must match exactly one row of the database BEFORE the
migration, and that row may change only in its `fields`. A table the scope
does not name may not change at all; no row may be removed unless the table
says `"removed": N`.

Copies live in `data/deploy_scratch/` (gitignored) and are deleted after
use. Paths are arguments, so tests run it on fixture databases; Phase 358
never ran it against live.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sqlite3
import subprocess
import sys
from collections.abc import Callable

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LIVE = ROOT / "data" / "motodiag.db"
BACKUPS = pathlib.Path.home() / "backups" / "motodiag"
KEEP = 5
MARK = "<!-- dry-run diff below; everything above is its header -->"


class Refused(Exception):
    """The apply stops before touching live; the message says why."""


# ------------------------------------------------------------ the database
def _ro(path: pathlib.Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def backup(src: pathlib.Path, dst: pathlib.Path) -> None:
    s, d = _ro(src), sqlite3.connect(dst)
    s.backup(d)
    s.close()
    d.close()


def dump(path: pathlib.Path) -> dict[str, tuple[list[str], dict]]:
    c, out = _ro(path), {}
    for (t,) in c.execute("select name from sqlite_master where type='table' "
                          "and name not like 'sqlite_%'").fetchall():
        cols = [r[1] for r in c.execute(f"pragma table_info('{t}')")]
        out[t] = (cols, {r[0]: r for r in c.execute(f"select rowid, * from '{t}'")})
    c.close()
    return out


def diff(a: dict, b: dict) -> dict:
    res = {}
    for t in sorted(set(a) | set(b)):
        cols, ra = a.get(t, ([], {}))
        cols_b, rb = b.get(t, ([], {}))
        cols = cols or cols_b
        added = sorted(set(rb) - set(ra))
        removed = sorted(set(ra) - set(rb))
        changed = sorted(k for k in set(ra) & set(rb) if ra[k] != rb[k])
        if added or removed or changed:
            res[t] = {"cols": cols, "added": added, "removed": removed, "changed": changed,
                      "a": ra, "b": rb}
    return res


def state(path: pathlib.Path) -> dict:
    c = _ro(path)
    counts = {t: c.execute(f"select count(*) from '{t}'").fetchone()[0]
              for (t,) in c.execute("select name from sqlite_master where type='table' "
                                    "and name not like 'sqlite_%'").fetchall()}
    integrity = c.execute("pragma integrity_check").fetchone()[0]
    c.close()
    return {"rows": sum(counts.values()), "tables": len(counts), "integrity": integrity}


# ------------------------------------------------------------ the scope
def scope_path(repo: pathlib.Path, phase: str) -> pathlib.Path:
    return repo / "docs" / "phases" / "in_progress" / f"{phase}_deploy_scope.json"


def diff_path(repo: pathlib.Path, phase: str, kind: str = "dryrun") -> pathlib.Path:
    return repo / "docs" / "phases" / "in_progress" / f"{phase}_{kind}_diff.md"


def resolve(scope: dict, before: pathlib.Path) -> dict[str, dict[int, set[str]]]:
    """{table: {rowid: allowed fields}}, found on the database BEFORE migration."""
    c, out = _ro(before), {}
    for t, spec in scope["tables"].items():
        for entry in spec.get("changed", []):
            rows = c.execute(f"select rowid from '{t}' where {entry['where']}",
                             entry.get("params", [])).fetchall()
            if len(rows) != 1:
                c.close()
                raise SystemExit(f"scope entry in {t} matches {len(rows)} rows, not 1: {entry}")
            out.setdefault(t, {})[rows[0][0]] = set(entry["fields"])
    c.close()
    return out


def check_scope(d: dict, scope: dict, allowed: dict) -> list[str]:
    probs = []
    for t, x in d.items():
        spec = scope["tables"].get(t)
        if spec is None:
            probs.append(f"{t}: not in scope, but {len(x['added'])} added, "
                         f"{len(x['changed'])} changed, {len(x['removed'])} removed")
            continue
        if len(x["removed"]) != spec.get("removed", 0):
            probs.append(f"{t}: {len(x['removed'])} removed, scope says {spec.get('removed', 0)}")
        if len(x["added"]) != spec.get("added", 0):
            probs.append(f"{t}: {len(x['added'])} added, scope says {spec.get('added', 0)}")
        want = allowed.get(t, {})
        if set(x["changed"]) != set(want):
            probs.append(f"{t}: changed rowids {x['changed']}, scope names {sorted(want)}")
        cols = ["rowid"] + x["cols"]
        for k in set(x["changed"]) & set(want):
            moved = {cols[i] for i in range(len(cols)) if x["a"][k][i] != x["b"][k][i]}
            if not moved <= want[k]:
                probs.append(f"{t} rowid {k}: changed {sorted(moved)}, allowed {sorted(want[k])}")
    for t, spec in scope["tables"].items():
        if t not in d and (spec.get("added") or spec.get("removed") or spec.get("changed")):
            probs.append(f"{t}: scope expects a change and there is none")
    return probs


def report(d: dict) -> str:
    out = []
    for t, x in d.items():
        out.append(f"## {t}: +{len(x['added'])} added, {len(x['changed'])} changed, "
                   f"{len(x['removed'])} removed\n")
        cols = ["rowid"] + x["cols"]
        for k in x["changed"]:
            out.append(f"\n### {t} rowid {k}\n")
            for i, col in enumerate(cols):
                va, vb = x["a"][k][i], x["b"][k][i]
                if va != vb:
                    out.append(f"\n**{col}**\n\n- before: {va}\n- after:  {vb}\n")
        for k in x["added"]:
            out.append(f"- added rowid {k}: {x['b'][k][1:4]}\n")
        for k in x["removed"]:
            out.append(f"- removed rowid {k}: {x['a'][k][1:4]}\n")
    return "".join(out)


# ------------------------------------------------------------ helpers
def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retain(backups: pathlib.Path, keep: int = KEEP) -> list[str]:
    dbs = sorted(backups.glob("motodiag_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in dbs[keep:]:
        for q in (p, p.with_name(p.name + "-shm"), p.with_name(p.name + "-wal")):
            q.unlink(missing_ok=True)
    return [p.name for p in dbs[keep:]]


def census(db: pathlib.Path) -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    import f158_census
    return len(f158_census.census(db))


def _scratch(repo: pathlib.Path, name: str) -> pathlib.Path:
    d = repo / "data" / "deploy_scratch"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    for q in (p, p.with_name(p.name + "-wal"), p.with_name(p.name + "-shm")):
        q.unlink(missing_ok=True)
    return p


def _drop(p: pathlib.Path) -> None:
    for q in (p, p.with_name(p.name + "-wal"), p.with_name(p.name + "-shm")):
        q.unlink(missing_ok=True)


def _default_migrate(path: pathlib.Path) -> list[int]:
    sys.path.insert(0, str(ROOT / "src"))
    from motodiag.core.migrations import apply_pending_migrations
    return apply_pending_migrations(str(path))


def _header(text: str) -> dict[str, str]:
    head = text.split(MARK, 1)[0]
    return dict(re.findall(r"^- \*\*(\w[\w ]*):\*\* `?([^`\n]*)`?$", head, re.M))


# ------------------------------------------------------------ the two steps
def dryrun(phase: str, *, db: pathlib.Path = LIVE, backups: pathlib.Path = BACKUPS,
           repo: pathlib.Path = ROOT, migrate: Callable = _default_migrate) -> int:
    scope_file = scope_path(repo, phase)
    scope = json.loads(scope_file.read_text())
    print("before (live, read only):", json.dumps(state(db)))
    backups.mkdir(parents=True, exist_ok=True)
    bk = backups / f"motodiag_pre{phase}_{dt.datetime.now():%Y%m%d_%H%M%S}.db"
    backup(db, bk)
    print("backup:", bk, "removed by retain-5:", retain(backups))
    copy = _scratch(repo, f"{phase}_dryrun_copy.db")
    backup(bk, copy)
    try:
        allowed = resolve(scope, copy)
        applied = migrate(copy)
        d = diff(dump(bk), dump(copy))
        probs = check_scope(d, scope, allowed)
        hits = census(copy)
    finally:
        _drop(copy)
    out = diff_path(repo, phase)
    out.write_text("\n".join([
        f"# Phase {phase}: the dry-run diff for the live migration",
        "",
        f"- **Written:** `{dt.datetime.now().isoformat(timespec='seconds')}`",
        f"- **Backup:** `{bk}`",
        f"- **Backup sha256:** `{sha256(bk)}`",
        f"- **Scope sha256:** `{sha256(scope_file)}`",
        f"- **Migrations applied on the copy:** `{applied}`",
        f"- **F158 census on the copy:** `{hits}`",
        f"- **Scope problems:** `{'; '.join(probs) or 'none'}`",
        "",
        "The live apply refuses to run unless this file is committed and unchanged.",
        "",
        MARK,
        report(d)]))
    print("scope problems:", probs or "none")
    print("F158 census on the copy:", hits)
    print("wrote", out.relative_to(repo))
    return 1 if probs else 0


def preflight(phase: str, *, db: pathlib.Path, repo: pathlib.Path, migrate: Callable) -> dict:
    """Every refusal, before live is touched. Returns the header on success."""
    f = diff_path(repo, phase)
    if not f.exists():
        raise Refused(f"no approved dry-run diff: {f.relative_to(repo)} does not exist. "
                      "Run `deploy.py dryrun` and commit its diff first.")
    rel = str(f.relative_to(repo))
    tracked = subprocess.run(["git", "-C", str(repo), "ls-files", "--error-unmatch", rel],
                             capture_output=True).returncode == 0
    if not tracked:
        raise Refused(f"{rel} is not committed: the diff the operator approved must be in git.")
    if subprocess.run(["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--", rel]).returncode:
        raise Refused(f"{rel} differs from its committed version: it is not the approved diff.")
    head = _header(f.read_text())
    if head.get("Scope problems") != "none":
        raise Refused(f"the approved dry run records scope problems: {head.get('Scope problems')}")
    bk = pathlib.Path(head.get("Backup", ""))
    if not bk.is_file() or sha256(bk) != head.get("Backup sha256"):
        raise Refused(f"the backup {bk} is missing or no longer hashes as recorded")
    if sha256(scope_path(repo, phase)) != head.get("Scope sha256"):
        raise Refused("the scope file changed since the dry run")
    drift = diff(dump(bk), dump(db))
    if drift:
        raise Refused(f"live differs from the backup in {sorted(drift)}: it changed since "
                      "the dry run. Stop and ask.")
    fresh = _scratch(repo, f"{phase}_preapply_copy.db")
    backup(bk, fresh)
    try:
        scope = json.loads(scope_path(repo, phase).read_text())
        allowed = resolve(scope, fresh)
        migrate(fresh)
        probs = check_scope(diff(dump(bk), dump(fresh)), scope, allowed)
    finally:
        _drop(fresh)
    if probs:
        raise Refused(f"a fresh dry run leaves the scope: {probs}. Stop and ask.")
    return head


def apply_live(phase: str, *, db: pathlib.Path = LIVE, repo: pathlib.Path = ROOT,
               migrate: Callable = _default_migrate) -> int:
    try:
        head = preflight(phase, db=db, repo=repo, migrate=migrate)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    bk = pathlib.Path(head["Backup"])
    scope = json.loads(scope_path(repo, phase).read_text())
    allowed = resolve(scope, bk)
    print("preflight passed; applying live:", migrate(db))
    d = diff(dump(bk), dump(db))
    probs = check_scope(d, scope, allowed)
    diff_path(repo, phase, "live").write_text(
        f"# Phase {phase}: live after the apply, against the backup\n\n"
        f"- **Scope problems:** `{'; '.join(probs) or 'none'}`\n"
        f"- **F158 census on live:** `{census(db)}`\n\n" + report(d))
    print("after (live):", json.dumps(state(db)), "scope problems:", probs or "none")
    return 1 if probs else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", choices=["dryrun", "apply-live"])
    ap.add_argument("phase")
    a = ap.parse_args(argv)
    return dryrun(a.phase) if a.mode == "dryrun" else apply_live(a.phase)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
