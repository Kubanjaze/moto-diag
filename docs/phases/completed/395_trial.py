#!/usr/bin/env python3
"""Phase 395's trial, once, in the real place (389's rule; the prompt: "On
the desktop, run the whole path on a planted phase whose migration adds one
empty table. Use a copy of live standing in for live, never live itself,
and keep the trial's output as a fixture").

Run on the home desktop from this checkout, with its venv:

    .venv/bin/python docs/phases/in_progress/395_trial.py

What is real: the dispatcher's own methods (`stage_engineer`,
`engineer_deploy`, `stage_deployed`, `engineer_finish`), the push gate
(pushing to a local bare repository standing in for GitHub), the planted
phase's real migration (088, one empty table) on this checkout's
migrations, the operator's paste block exactly as the comment carries it,
run by bash in a terminal (a pty) and answered "yes" there, the real
`through_fleet.py`, `deploy.dryrun` / `apply_live` / `verify_live`, the
real `systemctl` reading of which database the API serves, `verify_deploy`,
`verify_after_apply`, `closeout_check` and Q1.

What stands in: live (a backup-API copy in the trial folder, named by the
trial's own `live.json`, with `HOME` the trial's folder, so the backups,
the retain-5 and the deploy checkout are the trial's); GitHub (`gh` is
389's stand-in in the dispatcher and a recording script in the block);
the Engineer's two sessions (planted commits, no model); the model-free
run (a recorded line: it is not new in 395).

Real live is only read: its schema and its row counts before and after
must be equal, and so must the real backup folder's listing.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import pty
import re
import shutil
import sqlite3
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[3]
REAL_HOME = pathlib.Path.home()
TRIAL = REAL_HOME / "motodiag" / "p395" / "trial"
REAL_LIVE = pathlib.Path(json.loads((REAL_HOME / ".config" / "motodiag" / "live.json")
                                    .read_text())["live"])
REAL_BACKUPS = REAL_HOME / "backups" / "motodiag"
REAL_VENV = REAL_HOME / ".local" / "state" / "motodiag" / "fleet" / "venv"
FIXTURE = REPO / ".claude" / "skills" / "fleet" / "fixtures" / "deploy" / "trial"
PHASE, N = "990", 95
BRANCH = f"phase-{PHASE}-one-empty-table"
OUT: list[str] = []


def say(*parts: object) -> None:
    line = " ".join(str(p) for p in parts)
    OUT.append(line)
    print(line, flush=True)


def git(repo: pathlib.Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def fingerprint(db: pathlib.Path) -> dict:
    """Live's schema and row counts, read only."""
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        schema = sorted(c.execute("select type, name, sql from sqlite_master").fetchall())
        counts = {t: c.execute(f"select count(*) from '{t}'").fetchone()[0]
                  for (t,) in c.execute("select name from sqlite_master where type='table'")}
        head = c.execute("select max(version) from schema_version").fetchone()[0]
    finally:
        c.close()
    return {"schema": schema, "counts": counts, "head": head}


def listing(folder: pathlib.Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []


MIGRATION = '''    Migration(
        version=88,
        name="trial_empty",
        description=(
            "Phase 395's trial (planted, never merged): one empty table, so "
            "the database step runs once in the real place."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS trial_empty (
                id INTEGER PRIMARY KEY,
                said TEXT NOT NULL
            );
        """,
        rollback_sql="DROP TABLE IF EXISTS trial_empty;",
    ),
]


def get_current_version('''

PLAN = f"""# Phase {PHASE} — The trial's one empty table

**Version:** 1.0 | **Tier:** Standard | **Date:** {dt.date.today()}

## Goal

Planted by Phase 395's trial. One empty table on live.

## The database step

It adds one new table, trial_empty (id, said), and one schema_version row.
It changes or deletes no existing live row.

## Logic

Migration 088.

## Planned items

- [ ] the migration
"""


def plant(origin: pathlib.Path) -> None:
    """GitHub, stood in: `master` is this checkout's HEAD (the code under
    trial, as master after the merge), and the planted phase's branch."""
    work = TRIAL / "work"
    git(TRIAL, "clone", "-q", "--no-hardlinks", str(REPO), str(work))
    git(work, "config", "user.name", "Phase 395 trial")
    git(work, "config", "user.email", "trial@motodiag.invalid")
    git(work, "checkout", "-q", "-B", "master", git(REPO, "rev-parse", "HEAD"))
    git(TRIAL, "init", "-q", "--bare", "-b", "master", str(origin))
    git(work, "push", "-q", str(origin), "master")
    git(work, "switch", "-q", "-c", BRANCH)
    road = work / "docs" / "ROADMAP.md"
    road.write_text(road.read_text().rstrip("\n")
                    + f"\n| {PHASE} | The trial's one empty table | 🚧 | Planted by 395's trial. |\n")
    inp = work / "docs" / "phases" / "in_progress"
    (inp / f"{PHASE}_implementation.md").write_text(PLAN)
    (inp / f"{PHASE}_step0.md").write_text(f"# Phase {PHASE} — Step 0\n\nClassification: "
                                           "**extension.** Planted by 395's trial.\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", f"Phase {PHASE}: Step 0, the row and v1.0")
    git(work, "push", "-q", str(origin), BRANCH)


def build(clone: pathlib.Path) -> None:
    """The Engineer's build, planted: migration 088, its scope file, then the
    regression of record, each committed in the stage's clone."""
    mig = clone / "src" / "motodiag" / "core" / "migrations.py"
    text = mig.read_text()
    tail = "]\n\n\ndef get_current_version("
    assert text.count(tail) == 1
    mig.write_text(text.replace(tail, MIGRATION, 1))
    inp = clone / "docs" / "phases" / "in_progress"
    (inp / f"{PHASE}_deploy_scope.json").write_text(json.dumps(
        {"tables": {"schema_version": {"added": 1}}, "schema": {"added": ["table trial_empty"]}},
        indent=1) + "\n")
    who = ["-c", "user.name=trial", "-c", "user.email=trial@motodiag.invalid"]
    git(clone, "add", "-A")
    git(clone, *who, "commit", "-qm", f"Phase {PHASE}: migration 088 and its scope")
    short = git(clone, "rev-parse", "--short", "HEAD")
    (inp / f"{PHASE}_phase_log.md").write_text(
        f"# Phase {PHASE} — phase log\n\n**Status:** In progress\n\n"
        f"Regression of record: 4321 passed, 0 failed, 0 skipped, 0 errors at `{short}` "
        "(1 min 0 s wall, `python -m pytest -n auto --dist load`, exit 0)\n\n"
        "No refute pass ran.\n")
    git(clone, "add", "-A")
    git(clone, *who, "commit", "-qm", f"Phase {PHASE}: the regression of record")


LINE_RE = re.compile(r"^Regression of record: .*$", re.M)


class Sessions:
    """The Engineer's two sessions, planted: the first ends `deploy` with no
    commit (the work is on the branch); the second closes out."""

    def __init__(self):
        self.runs = 0

    def __call__(self, cmd, stdout, stderr, **kw):
        self.runs += 1
        clone = pathlib.Path(cmd[cmd.index("--clone") + 1])
        run = pathlib.Path(cmd[cmd.index("--run") + 1])
        if self.runs == 1:
            build(clone)
        log = (clone / "docs" / "phases" / "in_progress" / f"{PHASE}_phase_log.md").read_text()
        line = LINE_RE.search(log).group(0)
        if self.runs == 1:
            result = {"outcome": "deploy", "summary": "One empty table, planted by the trial.",
                      "regression_line": line,
                      "live_change": "It adds one new, empty table, trial_empty, and changes "
                                     "no existing row."}
        else:
            close_out(clone, line)
            result = {"outcome": "pr-ready", "summary": "Closed out after the database step.",
                      "regression_line": line}
        (run / "engineer.json").write_text(json.dumps(result))
        stdout.write(json.dumps({"is_error": False, "result": "done"}))
        stdout.flush()
        return type("Proc", (), {"poll": lambda s: 0, "returncode": 0,
                                 "terminate": lambda s: None})()


def close_out(clone: pathlib.Path, line: str) -> None:
    """The close-out round, planted: documents only."""
    inp, done = clone / "docs" / "phases" / "in_progress", clone / "docs" / "phases" / "completed"
    answer = (inp / f"{PHASE}_deploy_answer.md").read_text()
    quote = re.search(r"^> .*$", answer, re.M).group(0)
    sha = re.search(r"sha256:\*\* `([0-9a-f]+)`", answer).group(1)
    live = (inp / f"{PHASE}_live_diff.md").read_text()
    log = inp / f"{PHASE}_phase_log.md"
    log.write_text(log.read_text().replace("**Status:** In progress", "**Status:** Complete")
                   + f"\n## {dt.date.today()} — the database step\n\nThe operator's answer, "
                   f"against the dry-run diff `{sha[:12]}`:\n\n{quote}\n\n"
                   f"{live.splitlines()[2]}\n")
    impl = inp / f"{PHASE}_implementation.md"
    impl.write_text(impl.read_text().replace("**Version:** 1.0", "**Version:** 1.1")
                    .replace("- [ ] the migration", "- [x] the migration")
                    + f"\n## Deviations\n\nNone.\n\n## Results\n\n- {line}\n- Live: "
                    f"{live.splitlines()[2]}\n")
    for p in sorted(inp.glob(f"{PHASE}_*")):
        git(clone, "mv", str(p.relative_to(clone)), str((done / p.name).relative_to(clone)))
    road = clone / "docs" / "ROADMAP.md"
    road.write_text(road.read_text().replace(
        f"| {PHASE} | The trial's one empty table | 🚧 | Planted by 395's trial. |",
        f"| {PHASE} | The trial's one empty table | ✅ | **CLOSED {dt.date.today()}.** "
        f"Planted by 395's trial. {line.replace('Regression of record: ', 'Regression ')} |"))
    hist = clone / "implementation.md"
    text = hist.read_text()
    text = re.sub(r"^\*\*Version:\*\*.*$", f"**Version:** trial — Phase {PHASE}", text,
                  count=1, flags=re.M)
    first = next(i for i, ln in enumerate(text.splitlines()) if ln.startswith("| **"))
    lines = text.splitlines()
    lines.insert(first, f"| **{PHASE}** | {dt.date.today()} | Planted by 395's trial. |")
    hist.write_text("\n".join(lines) + "\n")
    (clone / "docs" / "handoffs" / f"{dt.date.today()}_{PHASE}_closed.md").write_text(
        f"# Handoff — Phase {PHASE} closed (planted by 395's trial)\n\nWhat shipped: one empty "
        "table. What is open: nothing. What is next: nothing.\n")
    git(clone, "add", "-A")
    git(clone, "-c", "user.name=trial", "-c", "user.email=trial@motodiag.invalid", "commit",
        "-qm", f"Phase {PHASE}: the close-out after the database step")


def run_block(block: str, env: dict) -> tuple[int, str]:
    """The operator's paste, in a terminal: bash runs the block as the
    comment carries it, and "yes" is typed when it asks."""
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe("bash", ["bash", "-c", block], env)
    out, typed, end = b"", False, time.monotonic() + 900
    while time.monotonic() < end:
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
        if not typed and b"Type yes" in out:
            time.sleep(0.5)
            os.write(fd, b"yes\n")
            typed = True
    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status), out.decode(errors="replace").replace("\r", "")


def main() -> int:
    shutil.rmtree(TRIAL, ignore_errors=True)
    home = TRIAL / "home"
    state = home / ".local" / "state" / "motodiag" / "fleet"
    state.mkdir(parents=True)
    (home / "motodiag" / "fleet").mkdir(parents=True)
    (home / "motodiag" / "fleet" / "code").symlink_to(REPO)
    (state / "venv").symlink_to(REAL_VENV)
    stand_in = TRIAL / "live" / "motodiag.db"
    stand_in.parent.mkdir()
    (home / ".config" / "motodiag").mkdir(parents=True)
    (home / ".config" / "motodiag" / "live.json").write_text(json.dumps({"live": str(stand_in)}))
    fake_gh = TRIAL / "bin" / "gh"
    fake_gh.parent.mkdir()
    fake_gh.write_text(f'#!/bin/sh\necho "$@" >> {TRIAL}/gh_calls.txt\n')
    fake_gh.chmod(0o755)

    say(f"# Phase 395's trial — {dt.datetime.now().astimezone().isoformat(timespec='seconds')}")
    say(f"code under trial: {git(REPO, 'rev-parse', 'HEAD')} ({git(REPO, 'branch', '--show-current')})")
    before_live, before_backups = fingerprint(REAL_LIVE), listing(REAL_BACKUPS)
    say(f"real live (read only): schema head {before_live['head']}, "
        f"{len(before_live['counts'])} tables; real backups: {len(before_backups)} files")
    src = sqlite3.connect(f"file:{REAL_LIVE}?mode=ro", uri=True)
    dst = sqlite3.connect(stand_in)
    src.backup(dst)
    src.close()
    dst.close()
    say(f"stand-in for live: {stand_in}, a backup-API copy, schema head "
        f"{fingerprint(stand_in)['head']}")

    os.environ["HOME"] = str(home)
    os.environ.pop("MOTODIAG_LIVE_CONFIG", None)
    os.environ.pop("FLEET_STATE", None)
    sys.path.insert(0, str(REPO / "tests"))
    sys.path.insert(0, str(REPO / ".claude" / "skills" / "fleet"))
    import dispatcher as D
    import journal as J
    import quartermaster as Q
    from test_phase388_dispatcher import Clock
    from test_phase390_resume import Hub

    origin = TRIAL / "origin.git"
    plant(origin)
    clock = Clock(dt.datetime.now().astimezone())
    host = Hub(clock, TRIAL / "fence.sh")
    body = f"The trial.\n\n{D.fleet_git.TRIAL_MARKER}"
    host.issue(N, f"Phase {PHASE}: the trial's one empty table", body,
               {"mission": clock.t, "plan:approved": clock.t})
    sessions = Sessions()

    def check(clone, commit, *, full, command=None):
        """The model-free run, stood in: it counts what the phase log's line counts."""
        if not full:
            return D.Check(True, commit, None, "recorded: the model-free run stands in")
        for folder in ("completed", "in_progress"):
            r = subprocess.run(["git", "-C", str(clone), "show",
                                f"{commit}:docs/phases/{folder}/{PHASE}_phase_log.md"],
                               capture_output=True, text=True)
            if r.returncode == 0:
                break
        return D.Check(True, commit, LINE_RE.search(r.stdout).group(0), "recorded")

    fleet = D.Fleet(state=state, token="sk-ant-oat01-trial", host=host, fence=TRIAL / "fence.sh",
                    workspace_docs=TRIAL / "wsd", repo_url=str(origin), now=clock,
                    out=lambda s: None, identity_file=TRIAL / "no-identity.env",
                    popen=sessions, check=check, sleep=lambda s: None,
                    mobile=TRIAL / "no-mobile")
    say(f"the dispatcher's deploy root: {fleet.deploy_root}")
    fleet.update_mirror()

    say("\n## 1. The Engineer ends `deploy`; the dispatcher checks, pushes, holds, hands over")
    out = fleet.run_stage(N, "engineer", lambda: fleet.stage_engineer(N, PHASE, body, BRANCH))
    say(f"stage outcome: {out}")
    (held,) = J.held_runs(fleet.runs, N)
    say(f"held.json: {json.dumps(J.held(held))}")
    say(f"labels: {sorted(host.issues[N]['labels'])}")
    say(f"pushed: {BRANCH} at {git(origin, 'rev-parse', BRANCH)}")
    comment = host.comments(N)[-1]
    say("the comment, as the operator reads it:\n" + comment)
    block = comment.split("```bash\n", 1)[1].split("```", 1)[0]

    say("\n## 2. The operator's paste block, in a terminal, answered yes")
    env = {"HOME": str(home), "PATH": f"{fake_gh.parent}:{os.environ['PATH']}",
           "TERM": "dumb", "LANG": os.environ.get("LANG", "C.UTF-8")}
    rc, said = run_block(block, env)
    say(said.rstrip())
    say(f"block exit: {rc}")
    calls = (TRIAL / "gh_calls.txt").read_text() if (TRIAL / "gh_calls.txt").is_file() else ""
    say(f"gh, as the block called it: {calls.strip()}")
    if rc != 0 or "ALL GOOD" not in said:
        say("TRIAL FAILED at the block")
        return finish(1, before_live, before_backups, stand_in)
    if f"issue edit {N} -R Kubanjaze/moto-diag --remove-label needs-hands" in calls:
        host.issues[N]["labels"].remove("needs-hands")

    say("\n## 3. needs-hands off: the resume")
    clock.t += dt.timedelta(minutes=5)
    route = fleet.next_stage(N, PHASE, set(host.issues[N]["labels"]), body, "")
    say(f"the stage due: {route and route[0]}, held for {J.held(held).get('why')}")
    out = fleet.run_stage(N, "engineer", route[1])
    say(f"stage outcome: {out}")
    say(f"labels: {sorted(host.issues[N]['labels'])}; held runs left: "
        f"{[p.name for p in J.held_runs(fleet.runs, N)]}; sessions: {sessions.runs}")
    head = git(origin, "rev-parse", BRANCH)
    say(f"the branch on the stand-in GitHub: {head}")
    for ln in git(origin, "log", "--format=%h %an: %s", f"master..{BRANCH}").splitlines():
        say(f"  {ln}")
    if not out.startswith("PR "):
        say("TRIAL FAILED at the resume")
        return finish(1, before_live, before_backups, stand_in)

    say("\n## 4. Q1 on the pull request's head, verify-live outside the fence")
    clone = held / "clone"
    q1 = Q.scope(clone, PHASE, live_check=lambda: fleet.live_check(clone, PHASE))
    say(q1.line())
    rc_v, text = fleet.live_check(clone, PHASE)
    say(f"verify-live exit {rc_v}:\n{text.rstrip()}")
    q1_fence = Q.scope(clone, PHASE)
    say(f"the same in the fence, with no live: {q1_fence.line()}")

    say("\n## 5. The block pasted a second time: nothing applied again")
    rc2, said2 = run_block(block, env)
    say(said2.rstrip())
    say(f"block exit: {rc2}")
    ok = q1.ok and not q1_fence.ok and rc2 == 0 and "already on the live database" in said2
    return finish(0 if ok else 1, before_live, before_backups, stand_in)


def finish(rc: int, before_live: dict, before_backups: list[str], stand_in: pathlib.Path) -> int:
    say("\n## 6. Real live and the real backups, after")
    after_live, after_backups = fingerprint(REAL_LIVE), listing(REAL_BACKUPS)
    same = after_live["schema"] == before_live["schema"] and after_live["head"] == before_live["head"]
    say(f"real live's schema unchanged: {same} (head {after_live['head']}); "
        f"row counts unchanged: {after_live['counts'] == before_live['counts']}; "
        f"trial_empty on real live: {'table' in str([s for s in after_live['schema'] if s[1] == 'trial_empty'])}")
    say(f"real backups unchanged: {after_backups == before_backups}")
    st = fingerprint(stand_in)
    say(f"the stand-in: schema head {st['head']}, trial_empty "
        f"{'present' if 'trial_empty' in st['counts'] else 'absent'} "
        f"({st['counts'].get('trial_empty')} rows)")
    say(f"trial backups (retain-5 on the trial's own folder): "
        f"{listing(TRIAL / 'home' / 'backups' / 'motodiag')}")
    if not (same and after_backups == before_backups):
        rc = 1
    say(f"\nTRIAL {'PASSED' if rc == 0 else 'FAILED'}")
    FIXTURE.mkdir(parents=True, exist_ok=True)
    (FIXTURE / "trial_output.txt").write_text("\n".join(OUT) + "\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
