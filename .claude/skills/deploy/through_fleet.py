#!/usr/bin/env python3
"""The database step through the fleet (Phase 395, K58, F232).

A phase whose plan names the database step is built by the Chief Engineer
in the fence, which never sees live. The Engineer stops after the
regression of record; the dispatcher pushes the branch, holds the run and
hands the operator one paste block for the home desktop. This is that
block's work, run there by the operator with the fleet's own copy of the
code (master's), never the branch's:

    through_fleet.py <phase> <branch> <commit>

1. Live must be on this machine (`live.py`; exit 4 otherwise).
2. A fresh clone of the fleet's mirror at `~/motodiag/deploy/<phase>`, at
   the commit the dispatcher pushed, which must still be the branch's head.
3. Refused: a branch that changes the deploy or close-out tools (the
   checks that guard live must be master's), or has no scope file.
4. `deploy.dryrun` on a copy, with the branch's `src/` for the migration
   and the seed build, in a separate process. A scope problem stops here.
5. The change, in plain words. Nothing is applied until the operator types
   yes on the terminal; the answer is written verbatim to
   `<phase>_deploy_answer.md` and committed with the dry-run diff.
6. The API is stopped if it serves this database; `deploy.apply_live`,
   with every refusal it has; the API started and `/healthz` read; the live
   diff committed; `deploy.verify_live` must exit 0.

Nothing is pushed from here. On the resume, the dispatcher fetches these
commits into the Engineer's held clone and they reach GitHub with the
close-out, through the push gate. Run again after the apply, it changes
nothing: it says so and runs `verify-live`.

Every failure prints `SOMETHING IS OFF: <reason>` and exits non-zero: 1 a
problem, 2 the operator did not type yes, 4 live is not on this machine.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import json
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback
import urllib.request
from collections.abc import Callable

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import deploy as D  # noqa: E402
import live as L  # noqa: E402

#: The tools that guard live: a branch that changes them is refused (395 S0-3).
TOOLS = (".claude/skills/deploy/", ".claude/skills/closeout/")
UNIT = "motodiag-api.service"
HEALTHZ = "http://127.0.0.1:8000/healthz"
YES = "yes"
#: Who the step's commits name: the operator's paste, not a rank.
AUTHOR = {"user.name": "MotoDiag operator (the database step)",
          "user.email": "operator@motodiag.invalid"}
OFF = "SOMETHING IS OFF"

#: Run in a process of its own, so the branch's `src/` is the one imported.
_MIGRATE = ("import json, sys; sys.path.insert(0, sys.argv[1]); "
            "from motodiag.core.migrations import apply_pending_migrations as m; "
            "print(json.dumps(m(sys.argv[2])))")
_SEED = ("import sys, pathlib; sys.path.insert(0, sys.argv[1]); "
         "from motodiag.core.database import init_db; "
         "from motodiag.knowledge.loader import load_known_issues_file as load; "
         "init_db(sys.argv[2]); "
         "[load(f, sys.argv[2]) for f in sorted((pathlib.Path(sys.argv[1]) / 'motodiag' / "
         "'knowledge' / 'seed' / 'knowledge').glob('known_issues_*.json'))]")


#: No `__pycache__` in the checkout: apply-live refuses uncommitted code.
_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


class Off(Exception):
    """The step stops; the message is said to the operator as it is."""

    def __init__(self, why: str, code: int = 1):
        super().__init__(why)
        self.code = code


def deploy_root() -> pathlib.Path:
    """Where each phase's deploy checkout is made; the dispatcher reads it too."""
    return pathlib.Path.home() / "motodiag" / "deploy"


def mirror_path() -> pathlib.Path:
    """The fleet's mirror of GitHub, as the dispatcher keeps it."""
    state = os.environ.get("FLEET_STATE") or pathlib.Path.home() / ".local" / "state" \
        / "motodiag" / "fleet"
    return pathlib.Path(state) / "mirror.git"


def answer_path(repo: pathlib.Path, phase: str) -> pathlib.Path:
    return repo / "docs" / "phases" / "in_progress" / f"{phase}_deploy_answer.md"


def deploy_files(phase: str) -> tuple[str, ...]:
    """The three files the database step adds to the branch, and nothing else."""
    return tuple(f"docs/phases/in_progress/{phase}_{k}.md"
                 for k in ("dryrun_diff", "deploy_answer", "live_diff"))


def _git(repo: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def _must(r: subprocess.CompletedProcess, what: str) -> str:
    if r.returncode != 0:
        raise Off(f"{what}: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout.strip()


# ---------------------------------------------------------- the checkout
def applied(co: pathlib.Path, phase: str) -> bool:
    """The checkout already holds a committed live diff: the change is on live."""
    rel = f"docs/phases/in_progress/{phase}_live_diff.md"
    return co.is_dir() and _git(co, "ls-files", "--error-unmatch", rel).returncode == 0


def checkout(phase: str, branch: str, commit: str, mirror: pathlib.Path,
             root: pathlib.Path) -> pathlib.Path:
    co = root / phase
    shutil.rmtree(co, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    _must(subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(mirror), str(co)],
                         capture_output=True, text=True), "could not copy the fleet's mirror")
    head = _git(co, "rev-parse", "--verify", "-q", f"refs/remotes/origin/{branch}").stdout.strip()
    if not head:
        raise Off(f"the branch {branch} is not in the fleet's copy of GitHub")
    if head != commit:
        raise Off(f"the branch {branch} is at {head[:12]}, not at {commit[:12]} as the fleet's "
                  "comment says: the branch moved after the comment. Ask before going on")
    _must(_git(co, "checkout", "-q", "-B", branch, commit), "could not check out the branch")
    for k, v in AUTHOR.items():
        _git(co, "config", k, v)
    return co


def refusals(co: pathlib.Path, phase: str, commit: str) -> list[str]:
    """Why the step must not run on this branch at all."""
    why = []
    base = _git(co, "merge-base", "refs/remotes/origin/master", commit).stdout.strip()
    paths = _git(co, "diff", "--name-only", f"{base}..{commit}").stdout.split() if base else []
    if not base:
        why.append("the branch shares no history with master")
    touched = [p for p in paths if p.startswith(TOOLS)]
    if touched:
        why.append(f"the branch changes the tools that guard the live database ({touched[0]}); "
                   "the database step runs only master's")
    if not D.scope_path(co, phase).is_file():
        why.append(f"the branch has no scope file (docs/phases/in_progress/{phase}"
                   "_deploy_scope.json): nothing says what the change may touch")
    return why


# ---------------------------------------------------------- the branch's code
def branch_migrate(co: pathlib.Path, python: str = sys.executable) -> Callable:
    def migrate(path: pathlib.Path) -> list[int]:
        r = subprocess.run([python, "-c", _MIGRATE, str(co / "src"), str(path)],
                           capture_output=True, text=True, env=_ENV)
        if r.returncode != 0:
            raise Off(f"the branch's migration failed: {r.stderr.strip()[-400:]}")
        return json.loads(r.stdout.strip().splitlines()[-1])
    return migrate


def branch_seed(co: pathlib.Path, python: str = sys.executable) -> Callable:
    def build(path: pathlib.Path) -> None:
        r = subprocess.run([python, "-c", _SEED, str(co / "src"), str(path)],
                           capture_output=True, text=True, env=_ENV)
        if r.returncode != 0:
            raise Off(f"the branch's seed build failed: {r.stderr.strip()[-400:]}")
    return build


# ---------------------------------------------------------- plain words
def _columns(sql: str, table: str) -> list[str]:
    c = sqlite3.connect(":memory:")
    try:
        c.execute(sql)
        return [r[1] for r in c.execute(f"pragma table_info('{table}')")]
    finally:
        c.close()


def plain_words(diff_text: str) -> list[str]:
    """The approved exact diff, said as a person would read it."""
    exact = D._approved_exact(diff_text) or {"rows": {}, "schema": {}}
    backup = pathlib.Path(D._header(diff_text).get("Backup", ""))
    before = D.schema(backup) if backup.is_file() else {}
    sch, sql = exact.get("schema", {}), exact.get("schema", {}).get("sql", {})
    out = []
    for name in sch.get("added", []):
        kind, obj = name.split(" ", 1)
        if kind == "table":
            cols = _columns(sql[name], obj)
            out.append(f"adds a new table, {obj}, with {len(cols)} columns: {', '.join(cols)}")
        else:
            out.append(f"adds the {kind} {obj}")
    for name in sch.get("removed", []):
        out.append(f"REMOVES the {name.replace(' ', ' named ', 1)}")
    for name in sch.get("changed", []):
        kind, obj = name.split(" ", 1)
        if kind == "table" and name in before:
            old, new = _columns(before[name], obj), _columns(sql[name], obj)
            added = [c for c in new if c not in old]
            gone = [c for c in old if c not in new]
            out.append(f"changes the table {obj}: "
                       + "; ".join(x for x in (
                           f"adds the column(s) {', '.join(added)}" if added else "",
                           f"REMOVES the column(s) {', '.join(gone)}" if gone else "")
                                   if x) or f"changes the table {obj}'s definition")
        else:
            out.append(f"changes the {kind} {obj}")
    changed_any = removed_any = False
    for table, rows in sorted(exact.get("rows", {}).items()):
        a, c, r = (len(rows.get(k, {})) for k in ("added", "changed", "removed"))
        if a:
            out.append(f"adds {a} row{'s' * (a != 1)} to {table}")
        if c:
            changed_any = True
            fields = sorted({f for v in rows["changed"].values() for f in v})
            out.append(f"CHANGES {c} existing row{'s' * (c != 1)} in {table} "
                       f"({', '.join(fields)})")
        if r:
            removed_any = True
            out.append(f"REMOVES {r} row{'s' * (r != 1)} from {table}")
    if not changed_any:
        out.append("changes no existing row")
    if not removed_any:
        out.append("removes no row")
    return out


# ---------------------------------------------------------- the API
class Service:
    """`motodiag-api.service`, stopped for the apply only when it serves the
    database being changed: a stand-in for live leaves the real one alone."""

    def serves(self, db: pathlib.Path) -> bool:
        r = subprocess.run(["systemctl", "show", UNIT, "-p", "Environment", "--value"],
                           capture_output=True, text=True)
        m = re.search(r"(?:^|\s)MOTODIAG_DB_PATH=(\S+)", r.stdout or "")
        return bool(m) and pathlib.Path(m.group(1)).resolve() == db.resolve()

    def ctl(self, verb: str) -> bool:
        return subprocess.run(["sudo", "-n", "systemctl", verb, UNIT],
                              capture_output=True).returncode == 0

    def healthy(self, tries: int = 30) -> tuple[bool, str]:
        """`/healthz` says `"status": "ok"`, within `tries` seconds of a start."""
        said = ""
        for _ in range(tries):
            try:
                with urllib.request.urlopen(HEALTHZ, timeout=5) as r:
                    said = r.read().decode()
                if json.loads(said).get("status") == "ok":
                    return True, said
            except (OSError, ValueError) as e:
                said = f"no answer ({e})"
            time.sleep(1)
        return False, said


def ask_tty(prompt: str) -> str:
    """The operator's answer, from the terminal itself: the paste block's
    own standard input is the block, never an answer. Two opens: a text
    file opened "r+" on a terminal refuses ("not seekable"; Phase 395's
    trial, bug fix #1)."""
    with open("/dev/tty", "w") as out, open("/dev/tty") as tty:
        out.write(prompt)
        out.flush()
        return tty.readline().rstrip("\n")


def _quiet(fn: Callable[[], int]) -> tuple[int, str]:
    """A deploy step's return code and everything it printed."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            rc = fn()
        except SystemExit as e:           # deploy.resolve: a scope entry that is not one row
            print(e)
            rc = 1
    return rc, out.getvalue()


def _commit(co: pathlib.Path, paths: list[str], subject: str) -> str:
    _must(_git(co, "add", "--", *paths), "could not stage the deploy files")
    _must(_git(co, "commit", "-q", "-m", subject), "could not commit the deploy files")
    return _git(co, "rev-parse", "HEAD").stdout.strip()


# ---------------------------------------------------------- the step
def run(phase: str, branch: str, commit: str, *, mirror: pathlib.Path | None = None,
        root: pathlib.Path | None = None, db: pathlib.Path | None = None,
        backups: pathlib.Path = D.BACKUPS, ask: Callable[[str], str] = ask_tty,
        service: Service | None = None, python: str = sys.executable,
        now: Callable[[], dt.datetime] = lambda: dt.datetime.now().astimezone(),
        say: Callable[[str], None] = print) -> int:
    db = db or L.where()
    root, service = root or deploy_root(), service or Service()
    co = root / phase
    if applied(co, phase):
        say("This change is already on the live database; nothing is applied again.")
        rc, text = _quiet(lambda: D.verify_live(phase, db=db, repo=co))
        say(text.rstrip())
        if rc != 0:
            raise Off("the live database does not match the change that was approved")
        return 0
    co = checkout(phase, branch, commit, mirror or mirror_path(), root)
    why = refusals(co, phase, commit)
    if why:
        raise Off("; ".join(why))
    migrate, seed = branch_migrate(co, python), branch_seed(co, python)
    say("Step 1 of 3: trying the change on a copy of the live database (live is only read)...")
    rc, text = _quiet(lambda: D.dryrun(phase, db=db, backups=backups, repo=co, migrate=migrate,
                                       parity_build=seed))
    if rc != 0:
        raise Off(f"the change does not stay inside what the phase said it would touch:\n{text}")
    diff = D.diff_path(co, phase)
    say("\nOn the copy, this change:")
    for line in plain_words(diff.read_text()):
        say(f"  - {line}")
    say(f"\nThe full record is {diff.relative_to(co)} in {co}.")
    words = ask("\nType yes and press Enter to make this change to the live database "
                "(anything else stops here, and nothing changes): ")
    answer = answer_path(co, phase)
    answer.write_text(
        f"# Phase {phase}: the operator's answer to the database step\n\n"
        f"- **Asked:** `{now().isoformat(timespec='seconds')}`, on the home desktop, after "
        f"the dry run on a copy\n"
        f"- **Dry-run diff sha256:** `{D.sha256(diff)}`\n"
        f"- **Commit:** `{commit}`\n\n"
        f"The operator typed, verbatim:\n\n> {words}\n")
    if words.strip().lower() != YES:
        raise Off(f"you typed {words!r}, not yes: nothing was applied, and the live database "
                  "is as it was", 2)
    _commit(co, [str(diff.relative_to(co)), str(answer.relative_to(co))],
            f"Phase {phase}: the dry-run diff, and the operator's yes")
    say("\nStep 2 of 3: making the change on the live database...")
    stopped, started = service.serves(db), False
    if stopped and not service.ctl("stop"):
        raise Off("could not stop the app server (motodiag-api) for the change; nothing applied")
    try:
        rc, text = _quiet(lambda: D.apply_live(phase, db=db, repo=co, migrate=migrate,
                                               parity_build=seed))
    finally:
        if stopped:
            started = service.ctl("start")
    say(text.rstrip())
    live_diff = D.diff_path(co, phase, "live")
    if live_diff.is_file():
        _commit(co, [str(live_diff.relative_to(co))], f"Phase {phase}: the live diff")
    if rc == 2:
        raise Off("the change was refused before the live database was touched (the line "
                  "above says why); nothing changed")
    if rc != 0:
        raise Off("the live database changed, but not exactly as approved (the lines above "
                  "say how): stop here and ask")
    if stopped:
        if not started:
            raise Off("the change is made, but the app server (motodiag-api) did not start")
        ok, health = service.healthy()
        if not ok:
            raise Off(f"the change is made, but the app server does not answer: {health[:200]}")
        say(f"The app server is back: {health.strip()[:200]}")
    say("\nStep 3 of 3: checking the live database against the approved change...")
    rc, text = _quiet(lambda: D.verify_live(phase, db=db, repo=co))
    say(text.rstrip())
    if rc != 0:
        raise Off("the live database does not match the change that was approved")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("phase")
    ap.add_argument("branch")
    ap.add_argument("commit")
    a = ap.parse_args(argv)
    if not re.fullmatch(r"\d{3}[A-Z]?", a.phase) or not re.fullmatch(r"[0-9a-f]{40}", a.commit):
        print(f"{OFF}: the phase or the commit is not one the fleet writes")
        return 1
    try:
        return run(a.phase, a.branch, a.commit)
    except L.LiveElsewhere as e:
        print(f"{OFF}: the live database is not on this computer ({e})")
        return L.REFUSED
    except Off as e:
        print(f"{OFF}: {e}")
        return e.code
    except Exception as e:      # the block must still end in its verdict (bug fix #1)
        traceback.print_exc()
        print(f"{OFF}: the database step failed unexpectedly ({type(e).__name__}: {e}); "
              "the lines above say where")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
