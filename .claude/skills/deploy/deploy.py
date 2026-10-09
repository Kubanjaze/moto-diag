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
    deploy.py apply-live <phase>   refuses unless: the phase log carries a
                                   regression of record with no code changed
                                   since its commit and none uncommitted
                                   (Phase 378, K18: one order); that file
                                   exists, is committed
                                   and unchanged, and records no scope problem;
                                   its backup still hashes as recorded; the
                                   scope file is the one it was made with; live
                                   equals the backup; and a fresh dry run on a
                                   new copy stays in scope and EQUALS the
                                   committed diff, field for field, clock
                                   values masked (F172, Phase 357). Then it
                                   migrates live, writes <phase>_live_diff.md
                                   and checks the scope and the equality again.
    deploy.py verify-live <phase>  read-only (Phase 378, K25): live against the
                                   phase's backup, the approved diff, integrity
                                   and foreign keys.

**The exact diff** (F172). The dry-run file ends with the whole diff as JSON:
every field of every added and removed row, the before and after of every
changed field, and every schema object (table, index, trigger, view) added,
removed or rewritten. The markdown report above it is for reading; the JSON
is what apply-live compares. A value is masked as `<clock>` when it is
shaped like a timestamp and lies within one day of the run's own UTC clock:
that is a value the migration's clock wrote (359's five `applied_at` and
`updated_at` values). A fixed date a migration writes is not masked.
**The ceiling:** a migration edited to write a different timestamp that also
falls within a day of the run is not told apart.

**Schema objects are scoped too** (Phase 357): a scope names each one the
migration adds, removes or rewrites, as `"schema": {"added": ["table t",
"index i"]}`. Any other schema change is a scope problem.

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
migration, and that row may change only in its `fields`. An entry may also
carry `"to": {field: value}`: that field must then hold exactly that value
after the migration (Phase 359). A table the scope
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
EXACT = "<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->"
CLOCK = "<clock>"
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$")


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


def _aligned(rows: dict, src: list[str], cols: list[str]) -> dict:
    """Each row as (rowid, its values in ``cols`` order), None for a column the
    row's own table does not have."""
    return {k: (r[0], *(dict(zip(src, r[1:])).get(c) for c in cols)) for k, r in rows.items()}


def diff(a: dict, b: dict) -> dict:
    """Every table's rows that were added, removed or changed, by rowid.

    Phase 380, bug fix #1: when a migration adds or drops a column, both
    sides are lined up on the union of the two column lists (the new table's
    order first), with None where a side has no such column. The diff kept
    only the old table's columns, so a new column's values were cut from the
    exact diff by `zip`, a `to` on it could not be checked, and a change in it
    was not counted as a moved field.
    """
    res = {}
    for t in sorted(set(a) | set(b)):
        cols_a, ra = a.get(t, ([], {}))
        cols_b, rb = b.get(t, ([], {}))
        cols = list(cols_b) + [c for c in cols_a if c not in cols_b] if cols_b else list(cols_a)
        if cols_a and list(cols_a) != cols:
            ra = _aligned(ra, cols_a, cols)
        if cols_b and list(cols_b) != cols:
            rb = _aligned(rb, cols_b, cols)
        added = sorted(set(rb) - set(ra))
        removed = sorted(set(ra) - set(rb))
        changed = sorted(k for k in set(ra) & set(rb) if ra[k] != rb[k])
        if added or removed or changed:
            res[t] = {"cols": cols, "added": added, "removed": removed, "changed": changed,
                      "a": ra, "b": rb}
    return res


def schema(path: pathlib.Path) -> dict[str, str]:
    """{"table t": its SQL, "index i": …} for every object SQLite did not make."""
    c = _ro(path)
    out = {f"{kind} {name}": sql for kind, name, sql in c.execute(
        "select type, name, sql from sqlite_master where name not like 'sqlite_%'")}
    c.close()
    return out


def schema_diff(a: dict[str, str], b: dict[str, str]) -> dict[str, list[str]]:
    return {"added": sorted(set(b) - set(a)), "removed": sorted(set(a) - set(b)),
            "changed": sorted(k for k in set(a) & set(b) if a[k] != b[k])}


def _clock_masked(v: object, clock: dt.datetime) -> object:
    """`<clock>` for a timestamp within a day of the run's UTC clock."""
    if not (isinstance(v, str) and _TIMESTAMP.match(v)):
        return v
    try:
        t = dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return v
    if t.tzinfo is not None:
        t = t.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return CLOCK if abs(t - clock) <= dt.timedelta(days=1) else v


def _json_value(v: object) -> object:
    return f"x'{v.hex()}'" if isinstance(v, bytes) else v


def exact(d: dict, sch: dict[str, list[str]], new_schema: dict[str, str],
          clock: dt.datetime) -> dict:
    """The whole diff as JSON-ready data, with the run's clock values masked.
    Only what the migration wrote is masked: added rows and changed fields'
    after-values. Before-values come from the backup both runs share."""
    rows = {}
    for t, x in d.items():
        cols = x["cols"]
        rows[t] = {
            "added": {str(k): {c: _json_value(_clock_masked(v, clock))
                               for c, v in zip(cols, x["b"][k][1:])} for k in x["added"]},
            "removed": {str(k): {c: _json_value(v) for c, v in zip(cols, x["a"][k][1:])}
                        for k in x["removed"]},
            "changed": {str(k): {c: [_json_value(va), _json_value(_clock_masked(vb, clock))]
                                 for c, va, vb in zip(["rowid"] + cols, x["a"][k], x["b"][k])
                                 if va != vb} for k in x["changed"]},
        }
    objects = {k: new_schema[k] for k in sch["added"] + sch["changed"]}
    return json.loads(json.dumps({"rows": rows, "schema": {**sch, "sql": objects}},
                                 sort_keys=True))


def _leaves(x: object, path: str = "") -> dict[str, object]:
    if isinstance(x, dict):
        out: dict[str, object] = {}
        for k, v in x.items():
            out.update(_leaves(v, f"{path}/{k}"))
        return out or {path: {}}
    return {path: x}


def exact_gaps(approved: dict, fresh: dict) -> list[str]:
    """Every field where two exact diffs disagree, by its path."""
    a, b = _leaves(approved), _leaves(fresh)
    return [f"{p}: approved {a.get(p, '(absent)')!r}, fresh {b.get(p, '(absent)')!r}"
            for p in sorted(set(a) | set(b)) if a.get(p, "(absent)") != b.get(p, "(absent)")]


def _approved_exact(text: str) -> dict | None:
    if EXACT not in text:
        return None
    body = text.split(EXACT, 1)[1].strip()
    return json.loads(body.removeprefix("```json").removesuffix("```"))


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


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


def expected(scope: dict, before: pathlib.Path) -> dict[str, dict[int, dict[str, object]]]:
    """{table: {rowid: {field: value}}} from the `to` of each `changed` entry
    that has one: the value the field must hold after the migration (Phase
    359: the operator approved row 4615 changing "only to its seed text")."""
    c, out = _ro(before), {}
    for t, spec in scope["tables"].items():
        for entry in spec.get("changed", []):
            if entry.get("to"):
                (rowid,), = c.execute(f"select rowid from '{t}' where {entry['where']}",
                                      entry.get("params", [])).fetchall()
                out.setdefault(t, {})[rowid] = dict(entry["to"])
    c.close()
    return out


def check_scope(d: dict, scope: dict, allowed: dict, to: dict | None = None,
                sch: dict[str, list[str]] | None = None) -> list[str]:
    probs = []
    for kind, names in (sch or {}).items():
        named = sorted(scope.get("schema", {}).get(kind, []))
        if names != named:
            probs.append(f"schema {kind}: {names}, scope names {named}")
    for t, rows in (to or {}).items():
        x = d.get(t)
        for k, values in rows.items():
            for field, value in values.items():
                if x is None or k not in x["b"]:
                    probs.append(f"{t} rowid {k}: absent after the migration, scope expects {field}")
                elif x["b"][k][1 + x["cols"].index(field)] != value:
                    # No backticks: the diff header's parser reads values between them.
                    probs.append(f"{t} rowid {k}: {field} is not the scope's 'to' value")
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


def report(d: dict, sch: dict[str, list[str]] | None = None,
           new_schema: dict[str, str] | None = None) -> str:
    out = []
    for kind, names in (sch or {}).items():
        for name in names:
            out.append(f"## schema {kind}: {name}\n\n")
            if new_schema and name in new_schema:
                out.append(f"```sql\n{new_schema[name].strip()}\n```\n\n")
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
           repo: pathlib.Path = ROOT, migrate: Callable = _default_migrate,
           parity_build: Callable | None = None) -> int:
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
        allowed, to = resolve(scope, copy), expected(scope, copy)
        clock = _utc_now()
        applied = migrate(copy)
        d = diff(dump(bk), dump(copy))
        new_schema = schema(copy)
        sch = schema_diff(schema(bk), new_schema)
        probs = check_scope(d, scope, allowed, to, sch)
        probs += seed_parity(repo, copy, d, parity_build or _default_fresh_seed)
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
        "The live apply refuses to run unless this file is committed and unchanged,",
        "and unless a fresh dry run equals the exact diff at its end.",
        "",
        MARK,
        report(d, sch, new_schema),
        EXACT,
        "```json",
        json.dumps(exact(d, sch, new_schema, clock), indent=1, sort_keys=True),
        "```",
        ""]))
    print("scope problems:", probs or "none")
    print("F158 census on the copy:", hits)
    print("wrote", out.relative_to(repo))
    return 1 if probs else 0


def _git_lines(repo: pathlib.Path, *args: str) -> list[str]:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return [ln for ln in r.stdout.splitlines() if ln] if r.returncode == 0 else []


def regression_problem(repo: pathlib.Path, phase: str) -> str | None:
    """Why the phase may not apply live yet, or None (Phase 378, K18).

    One order: the regression of record, then the apply from the branch, then
    the close-out commit that moves the deploy files, then the merge. So the
    phase log in `in_progress/` must carry a regression line A5 can parse, no
    code path may have changed between its commit and HEAD (verify_phase's
    check 2 scope: `.claude/` and `scripts/` are code too), and no code path may
    be uncommitted, since the apply migrates with the working tree's `src/`.
    """
    sys.path.insert(0, str(HERE.parent / "closeout"))
    import closeout_check
    import code_after_regression

    log = repo / "docs" / "phases" / "in_progress" / f"{phase}_phase_log.md"
    rel = log.relative_to(repo)
    if not log.is_file():
        return f"no phase log {rel}: the regression of record comes before the live apply"
    line = closeout_check.regression_line(log.read_text(encoding="utf-8"))
    if line is None:
        return (f"{rel} has no regression of record that A5 can read: run "
                f"`.claude/skills/closeout/regression.sh` and record its line before the "
                f"live apply")
    commit = line[1]
    if not _git_lines(repo, "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}"):
        return f"the regression of record names `{commit}`, which is not a commit here"
    after = code_after_regression.code_paths(
        _git_lines(repo, "diff", "--name-only", f"{commit}..HEAD"))
    if after:
        return (f"code changed after the regression of record at `{commit}`: "
                f"{after[:5]}. Run the regression again before the live apply")
    pending = code_after_regression.code_paths(
        _git_lines(repo, "diff", "--name-only", "HEAD")
        + _git_lines(repo, "ls-files", "--others", "--exclude-standard"))
    if pending:
        return (f"uncommitted code in the working tree: {pending[:5]}. The apply migrates "
                f"with the working tree's code; commit it and run the regression again")
    return None


def preflight(phase: str, *, db: pathlib.Path, repo: pathlib.Path, migrate: Callable,
              parity_build: Callable | None = None) -> dict:
    """Every refusal, before live is touched. Returns the header on success."""
    problem = regression_problem(repo, phase)
    if problem:
        raise Refused(problem)
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
    approved = _approved_exact(f.read_text())
    if approved is None:
        raise Refused(f"{rel} has no exact diff: it was written before F172's fix. "
                      "Run `deploy.py dryrun` again and commit its diff.")
    fresh = _scratch(repo, f"{phase}_preapply_copy.db")
    backup(bk, fresh)
    try:
        scope = json.loads(scope_path(repo, phase).read_text())
        allowed, to = resolve(scope, fresh), expected(scope, fresh)
        clock = _utc_now()
        migrate(fresh)
        d = diff(dump(bk), dump(fresh))
        new_schema = schema(fresh)
        sch = schema_diff(schema(bk), new_schema)
        probs = check_scope(d, scope, allowed, to, sch)
        probs += seed_parity(repo, fresh, d, parity_build or _default_fresh_seed)
    finally:
        _drop(fresh)
    if probs:
        raise Refused(f"a fresh dry run leaves the scope: {probs}. Stop and ask.")
    gaps = exact_gaps(approved, exact(d, sch, new_schema, clock))
    if gaps:
        raise Refused(f"a fresh dry run differs from the approved diff in {len(gaps)} "
                      f"field(s): {gaps[:10]}. Stop and ask.")
    return head


def apply_live(phase: str, *, db: pathlib.Path = LIVE, repo: pathlib.Path = ROOT,
               migrate: Callable = _default_migrate,
               parity_build: Callable | None = None) -> int:
    try:
        head = preflight(phase, db=db, repo=repo, migrate=migrate, parity_build=parity_build)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    bk = pathlib.Path(head["Backup"])
    scope = json.loads(scope_path(repo, phase).read_text())
    allowed, to = resolve(scope, bk), expected(scope, bk)
    clock = _utc_now()
    print("preflight passed; applying live:", migrate(db))
    d = diff(dump(bk), dump(db))
    new_schema = schema(db)
    sch = schema_diff(schema(bk), new_schema)
    probs = check_scope(d, scope, allowed, to, sch)
    gaps = exact_gaps(_approved_exact(diff_path(repo, phase).read_text()),
                      exact(d, sch, new_schema, clock))
    probs += [f"live differs from the approved diff: {g}" for g in gaps]
    diff_path(repo, phase, "live").write_text(
        f"# Phase {phase}: live after the apply, against the backup\n\n"
        f"- **Scope problems:** `{'; '.join(probs) or 'none'}`\n"
        f"- **Equals the approved exact diff:** `{'no' if gaps else 'yes'}`\n"
        f"- **F158 census on live:** `{census(db)}`\n\n" + report(d, sch, new_schema))
    print("after (live):", json.dumps(state(db)), "scope problems:", probs or "none")
    return 1 if probs else 0


# ------------------------------------------------------------ seed parity
#: Columns a seed build cannot reproduce: the row's id and its clocks.
PARITY_SKIP = frozenset({"id", "created_at", "updated_at"})


def _default_fresh_seed(path: pathlib.Path) -> None:
    """A fresh build of the seed at HEAD: the schema, then every known-issue
    seed file, as `db init` loads them."""
    sys.path.insert(0, str(ROOT / "src"))
    from motodiag.core.database import init_db
    from motodiag.knowledge.loader import load_known_issues_file

    init_db(str(path))
    seed = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
    for f in sorted(seed.glob("known_issues_*.json")):
        load_known_issues_file(f, str(path))


def seed_parity(repo: pathlib.Path, copy: pathlib.Path, d: dict,
                build: Callable = _default_fresh_seed) -> list[str]:
    """Phase 380, the operator's 2A: every `known_issues` row the migration
    adds or changes must equal the row with the same `row_key` in a fresh
    seed build, every column but the id and the clocks, so the seed and live
    cannot drift. [] when the migration touches no known-issue row, or when
    the copy has no `row_key` yet."""
    x = d.get("known_issues")
    if not x:
        return []
    # The copy's own columns, which the touched rows follow: the diff's
    # `cols` are the backup's, and a migration that adds `row_key` (085)
    # would read as one that has none (Phase 380, found by its first run).
    c = _ro(copy)
    cols = [r[1] for r in c.execute("pragma table_info('known_issues')")]
    c.close()
    if "row_key" not in cols:
        return []
    touched = [x["b"][k] for k in x["added"] + x["changed"]]
    # Phase 381: a row the migration removes must be gone from the seed too,
    # or the next fresh build brings it back.
    removed = [dict(zip(x["cols"], x["a"][k][1:])).get("row_key") for k in x["removed"]]
    if not touched and not removed:
        return []
    fresh = _scratch(repo, "seed_parity_fresh.db")
    try:
        build(fresh)
        c = _ro(fresh)
        fresh_cols = [r[1] for r in c.execute("pragma table_info('known_issues')")]
        by_key = {r[fresh_cols.index("row_key")]: dict(zip(fresh_cols, r))
                  for r in c.execute("select * from known_issues")}
        c.close()
    finally:
        _drop(fresh)
    probs = [f"seed parity: removed row_key {key!r} is still a seed entry"
             for key in removed if key in by_key]
    for row in touched:
        live = dict(zip(cols, row[1:]))
        seeded = by_key.get(live["row_key"])
        if seeded is None:
            probs.append(f"seed parity: row_key {live['row_key']!r} is in no seed entry")
            continue
        for col in cols:
            if col in PARITY_SKIP or col not in seeded:
                continue
            if live[col] != seeded[col]:
                probs.append(f"seed parity: {live['row_key']} {col}: the migration wrote "
                             f"{str(live[col])[:60]!r}, the seed says {str(seeded[col])[:60]!r}")
    return probs


# ------------------------------------------------------------ reading it back
def _immutable_copy(src: pathlib.Path, dst: pathlib.Path) -> None:
    """Copy a backup opened with `immutable=1`: SQLite then leaves no `-shm`
    or `-wal` beside it, as a plain read-only open does (Phase 378, K25)."""
    s = sqlite3.connect(f"file:{src}?mode=ro&immutable=1", uri=True)
    d = sqlite3.connect(dst)
    s.backup(d)
    s.close()
    d.close()


def find_diff(repo: pathlib.Path, phase: str) -> pathlib.Path | None:
    """The phase's dry-run diff, in `in_progress/` before its close-out or
    `completed/` after."""
    for folder in ("in_progress", "completed"):
        p = repo / "docs" / "phases" / folder / f"{phase}_dryrun_diff.md"
        if p.is_file():
            return p
    return None


def shape_gaps(approved: dict, now: dict) -> list[str]:
    """Where live, read now, differs from the approved exact diff. A field the
    approved diff masked as `<clock>` matches any timestamp-shaped value: the
    clock it was masked against is long past."""
    a, b = _leaves(approved), _leaves(now)
    gaps = []
    for p in sorted(set(a) | set(b)):
        va, vb = a.get(p, "(absent)"), b.get(p, "(absent)")
        if va == vb or (va == CLOCK and isinstance(vb, str) and _TIMESTAMP.match(vb)):
            continue
        gaps.append(f"{p}: approved {va!r}, live {vb!r}")
    return gaps


def verify_live(phase: str, *, db: pathlib.Path = LIVE, repo: pathlib.Path = ROOT) -> int:
    """Read-only: live against the phase's backup (Phase 378, K25).

    Copies both through SQLite's backup API (the backup opened immutable),
    and prints the schema objects added, removed and changed, each table whose
    rows differ, whether that equals the approved exact diff, and live's
    integrity and foreign keys.

    Exit codes: 1 on an integrity or foreign-key failure or a missing backup;
    2 when the phase has no deploy; 3 when live does not equal the approved
    diff (F197, Phase 379: it printed "no" and exited 0), saying whether
    live's schema is past the phase's own migrations, which then explains the
    difference; else 0.
    """
    f = find_diff(repo, phase)
    if f is None:
        print(f"verify-live {phase}: no dry-run diff in in_progress/ or completed/; "
              "the phase has no deploy")
        return 2
    text = f.read_text()
    bk = pathlib.Path(_header(text).get("Backup", ""))
    if not bk.is_file():
        print(f"verify-live {phase}: the backup {bk} named in {f.name} is missing")
        return 1
    live_copy = _scratch(repo, f"{phase}_verify_live.db")
    bk_copy = _scratch(repo, f"{phase}_verify_backup.db")
    try:
        backup(db, live_copy)
        _immutable_copy(bk, bk_copy)
        d = diff(dump(bk_copy), dump(live_copy))
        new_schema = schema(live_copy)
        sch = schema_diff(schema(bk_copy), new_schema)
        c = _ro(live_copy)
        integrity = c.execute("pragma integrity_check").fetchone()[0]
        fk = c.execute("pragma foreign_key_check").fetchall()
        live_head = c.execute("select max(version) from schema_version").fetchone()[0]
        c.close()
    finally:
        _drop(live_copy)
        _drop(bk_copy)
    approved = _approved_exact(text)
    gaps = (shape_gaps(approved, exact(d, sch, new_schema, dt.datetime(1970, 1, 1)))
            if approved is not None else None)
    print(f"verify-live {phase}: live against {bk.name} (both copied read-only; "
          "the copies are deleted)")
    for kind in ("added", "removed", "changed"):
        print(f"  schema {kind}: {', '.join(sch[kind]) or 'none'}")
    if not d:
        print("  rows: no table differs")
    for t, x in d.items():
        print(f"  rows: {t} +{len(x['added'])} ~{len(x['changed'])} -{len(x['removed'])}")
    if gaps is None:
        print("  equals the approved exact diff: cannot tell (the diff predates F172)")
    else:
        print(f"  equals the approved exact diff: {'yes' if not gaps else 'no'}")
        for g in gaps[:10]:
            print(f"    {g}")
        if gaps:
            applied = [int(v) for v in re.findall(r"\d+", _header(text).get(
                "Migrations applied on the copy", ""))]
            phase_head = max(applied) if applied else None
            if phase_head is not None and live_head is not None and live_head > phase_head:
                print(f"  live is at schema {live_head}, past this phase's {phase_head}: "
                      "later migrations explain the difference")
            else:
                print(f"  live is at schema {live_head}, this phase's own head "
                      f"({phase_head}): the difference is not a later migration's")
    print(f"  integrity: {integrity}; foreign keys: "
          f"{'ok' if not fk else f'{len(fk)} violation(s)'}")
    if integrity != "ok" or fk:
        return 1
    return 3 if gaps else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", choices=["dryrun", "apply-live", "verify-live"])
    ap.add_argument("phase")
    a = ap.parse_args(argv)
    if a.mode == "verify-live":
        return verify_live(a.phase)
    return dryrun(a.phase) if a.mode == "dryrun" else apply_live(a.phase)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
