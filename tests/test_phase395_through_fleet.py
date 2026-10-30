"""Phase 395 — the database step's paste block, `through_fleet.py`.

The operator (K58): "the fleet stops at the right point and hands me one
paste block for the PC; that block tries the change on a copy, shows me
what changes, applies it and checks it". The prompt: "nothing applied
until I type yes"; "only my paste changes live, and the deploy skill's
refusals stay as they are".

Each case runs on a real git mirror (a phase branch with a scope file, a
regression of record and a stand-in migration in its own `src/`) and a
tmp database standing in for live. Nothing here opens live, the real
backups or the real API.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "deploy"))

import deploy as D  # noqa: E402
import through_fleet as T  # noqa: E402

PHASE = "990"
BRANCH = "phase-990-one-empty-table"
SCOPE = {"tables": {"schema_version": {"added": 1}},
         "schema": {"added": ["table trial_empty"]}}
MIGRATIONS = '''\
import sqlite3


def apply_pending_migrations(path):
    c = sqlite3.connect(path)
    c.execute("create table trial_empty (id integer primary key, said text not null)")
    c.execute("insert into schema_version values (88)")
    c.commit()
    c.close()
    return [88]
'''


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def make_live(path: pathlib.Path) -> None:
    c = sqlite3.connect(path)
    c.executescript("""
        create table schema_version (version integer);
        create table api_keys (id integer primary key, last_used_at text);
        insert into schema_version values (87);
        insert into api_keys values (1, null);
    """)
    c.commit()
    c.close()


class FakeService:
    def __init__(self, serves: bool = False, ok: bool = True):
        self._serves, self.ok, self.calls = serves, ok, []

    def serves(self, db):
        return self._serves

    def ctl(self, verb):
        self.calls.append(verb)
        return self.ok

    def healthy(self, tries=30):
        self.calls.append("healthz")
        return True, '{"status":"ok"}'


@pytest.fixture
def world(tmp_path):
    """A repository with master and the phase branch, its mirror, and live."""
    work = tmp_path / "work"
    (work / "docs" / "phases" / "in_progress").mkdir(parents=True)
    git(tmp_path, "init", "-q", "-b", "master", str(work))
    git(work, "config", "user.email", "t@t")
    git(work, "config", "user.name", "t")
    (work / ".gitignore").write_text("__pycache__/\ndata/\n")
    (work / "README.md").write_text("master\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "master")
    git(work, "switch", "-q", "-c", BRANCH)
    pkg = work / "src" / "motodiag" / "core"
    pkg.mkdir(parents=True)
    (work / "src" / "motodiag" / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    (pkg / "migrations.py").write_text(MIGRATIONS)
    D.scope_path(work, PHASE).write_text(json.dumps(SCOPE, indent=1))
    git(work, "add", "-A")
    git(work, "commit", "-qm", "the migration and its scope")
    short = git(work, "rev-parse", "--short", "HEAD")
    (work / "docs" / "phases" / "in_progress" / f"{PHASE}_phase_log.md").write_text(
        f"# log\n\nRegression of record: 10 passed, 0 failed, 0 skipped, 0 errors at `{short}` "
        "(1 min 0 s wall, `python -m pytest -n auto --dist load`, exit 0)\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "the regression of record")
    mirror = tmp_path / "mirror.git"
    git(tmp_path, "clone", "-q", "--mirror", str(work), str(mirror))
    live = tmp_path / "live.db"
    make_live(live)
    return {"work": work, "mirror": mirror, "live": live, "root": tmp_path / "deploy",
            "backups": tmp_path / "backups", "commit": git(work, "rev-parse", "HEAD")}


def step(w, *, answer="yes", service=None, commit=None, said=None):
    lines = said if said is not None else []
    return T.run(PHASE, BRANCH, commit or w["commit"], mirror=w["mirror"], root=w["root"],
                 db=w["live"], backups=w["backups"], ask=lambda _: answer,
                 service=service or FakeService(), say=lines.append)


def tables(db):
    c = sqlite3.connect(db)
    try:
        return sorted(r[0] for r in c.execute("select name from sqlite_master where type='table'"))
    finally:
        c.close()


def test_yes_applies_commits_each_file_and_verifies(world):
    said: list[str] = []
    assert step(world, said=said) == 0
    assert "trial_empty" in tables(world["live"])
    co = world["root"] / PHASE
    files = git(co, "diff", "--name-only", f"{world['commit']}..HEAD").split()
    assert sorted(files) == sorted(T.deploy_files(PHASE)), files
    assert git(co, "status", "--porcelain") == ""
    answer = T.answer_path(co, PHASE).read_text()
    assert "> yes" in answer and D.sha256(D.diff_path(co, PHASE)) in answer
    text = "\n".join(said)
    assert "adds a new table, trial_empty, with 2 columns: id, said" in text
    assert "adds 1 row to schema_version" in text
    assert "changes no existing row" in text and "removes no row" in text
    assert "equals the approved exact diff: yes" in text


def test_anything_but_yes_applies_nothing(world):
    before = D.dump(world["live"])
    with pytest.raises(T.Off) as e:
        step(world, answer="y")
    assert e.value.code == 2 and "nothing was applied" in str(e.value)
    assert D.dump(world["live"]) == before
    co = world["root"] / PHASE
    assert "> y\n" in T.answer_path(co, PHASE).read_text()
    assert git(co, "rev-parse", "HEAD") == world["commit"], "a no was committed"


def test_a_branch_with_no_scope_file_is_refused(world):
    work = world["work"]
    git(work, "rm", "-q", str(D.scope_path(work, PHASE)))
    git(work, "commit", "-qm", "no scope")
    git(world["mirror"], "fetch", "-q", str(work), f"+{BRANCH}:{BRANCH}")
    before = D.dump(world["live"])
    with pytest.raises(T.Off, match="no scope file"):
        step(world, commit=git(work, "rev-parse", "HEAD"))
    assert D.dump(world["live"]) == before
    assert not world["backups"].exists(), "a refused step took a backup"


def test_a_branch_that_changes_the_deploy_tools_is_refused(world):
    work = world["work"]
    tool = work / ".claude" / "skills" / "deploy" / "deploy.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("# loosened\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "a changed tool")
    git(world["mirror"], "fetch", "-q", str(work), f"+{BRANCH}:{BRANCH}")
    with pytest.raises(T.Off, match="tools that guard the live database"):
        step(world, commit=git(work, "rev-parse", "HEAD"))
    assert "trial_empty" not in tables(world["live"])


def test_a_commit_that_is_not_the_branch_head_is_refused(world):
    with pytest.raises(T.Off, match="the branch moved after the comment"):
        step(world, commit="0" * 40)
    assert "trial_empty" not in tables(world["live"])


def test_a_scope_problem_stops_before_the_question(world):
    work = world["work"]
    D.scope_path(work, PHASE).write_text(json.dumps({"tables": {"schema_version": {"added": 1}}}))
    git(work, "commit", "-qam", "a scope that does not name the table")
    git(world["mirror"], "fetch", "-q", str(work), f"+{BRANCH}:{BRANCH}")
    asked = []
    with pytest.raises(T.Off, match="does not stay inside"):
        T.run(PHASE, BRANCH, git(work, "rev-parse", "HEAD"), mirror=world["mirror"],
              root=world["root"], db=world["live"], backups=world["backups"],
              ask=lambda p: asked.append(p) or "yes", service=FakeService(), say=lambda s: None)
    assert asked == [] and "trial_empty" not in tables(world["live"])


def test_a_live_that_moved_since_the_dry_run_is_refused_by_apply_live(world):
    """apply-live's own refusal, kept: live changed between the dry run and
    the apply (here, between the question and the answer)."""
    def answer(_):
        c = sqlite3.connect(world["live"])
        c.execute("insert into api_keys values (2, null)")
        c.commit()
        c.close()
        return "yes"
    with pytest.raises(T.Off, match="refused before the live database was touched"):
        T.run(PHASE, BRANCH, world["commit"], mirror=world["mirror"], root=world["root"],
              db=world["live"], backups=world["backups"], ask=answer, service=FakeService(),
              say=lambda s: None)
    assert "trial_empty" not in tables(world["live"])


def test_the_api_is_stopped_and_started_only_when_it_serves_this_database(world):
    stand_in = FakeService(serves=False)
    assert step(world, service=stand_in) == 0
    assert stand_in.calls == [], "a stand-in for live stopped the real API"


def test_the_api_that_serves_live_is_stopped_for_the_apply(world):
    serving = FakeService(serves=True)
    assert step(world, service=serving) == 0
    assert serving.calls == ["stop", "start", "healthz"]


def test_an_api_that_will_not_stop_means_nothing_is_applied(world):
    with pytest.raises(T.Off, match="could not stop the app server"):
        step(world, service=FakeService(serves=True, ok=False))
    assert "trial_empty" not in tables(world["live"])


def test_a_second_run_applies_nothing_and_verifies(world):
    assert step(world) == 0
    after = D.dump(world["live"])
    said: list[str] = []
    assert step(world, answer="never asked", said=said) == 0
    assert D.dump(world["live"]) == after
    assert any("already on the live database" in s for s in said)


def test_live_elsewhere_refuses_with_exit_4(world, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MOTODIAG_LIVE_CONFIG", str(tmp_path / "none.json"))
    assert T.main([PHASE, BRANCH, world["commit"]]) == 4
    assert capsys.readouterr().out.startswith(T.OFF)


def test_the_branchs_migration_is_the_one_run(world):
    """The branch's `src/`, in a process of its own: master's would not add
    `trial_empty`."""
    co = T.checkout(PHASE, BRANCH, world["commit"], world["mirror"], world["root"])
    copy = world["root"] / "copy.db"
    make_live(copy)
    assert T.branch_migrate(co)(copy) == [88]
    assert "trial_empty" in tables(copy)
    assert git(co, "status", "--porcelain") == "", "the migration left files in the checkout"


def test_plain_words_name_a_removal_and_a_change():
    exact = {"rows": {"known_issues": {"added": {}, "changed": {"4": {"title": ["a", "b"]}},
                                       "removed": {"7": {"title": "x"}}}},
             "schema": {"added": [], "removed": ["index idx_old"], "changed": [], "sql": {}}}
    text = f"{D.MARK}\n{D.EXACT}\n```json\n{json.dumps(exact)}\n```\n"
    words = T.plain_words(text)
    assert "REMOVES the index named idx_old" in words
    assert "CHANGES 1 existing row in known_issues (title)" in words
    assert "REMOVES 1 row from known_issues" in words
    assert "changes no existing row" not in words


def test_the_question_is_asked_and_answered_on_a_real_terminal():
    """Bug fix #1 (the trial): `/dev/tty` opened "r+" as text refuses on a
    terminal. A child process with a pty as its terminal, its stdin not
    the terminal, is asked and answers."""
    import os
    import pty
    import time

    code = ("import sys; sys.path.insert(0, sys.argv[1]); import through_fleet as T; "
            "print('ANSWER=' + repr(T.ask_tty('Type yes: ')))")
    pid, fd = pty.fork()
    if pid == 0:
        devnull = os.open(os.devnull, os.O_RDONLY)
        os.dup2(devnull, 0)
        os.execv(sys.executable, [sys.executable, "-c", code,
                                  str(ROOT / ".claude" / "skills" / "deploy")])
    out, end = b"", time.monotonic() + 60
    while b"ANSWER=" not in out and time.monotonic() < end:
        try:
            chunk = os.read(fd, 1024)
        except OSError:
            break
        out += chunk
        if b"Type yes: " in chunk:
            os.write(fd, b"yes\n")
    os.waitpid(pid, 0)
    assert b"ANSWER='yes'" in out, out


def test_a_live_that_verify_live_does_not_agree_with_is_off(world, monkeypatch):
    real = D.verify_live
    monkeypatch.setattr(D, "verify_live", lambda *a, **k: (real(*a, **k), 3)[1])
    with pytest.raises(T.Off, match="does not match the change that was approved"):
        step(world)


def test_an_unexpected_error_still_ends_in_the_verdict(world, monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("planted")
    monkeypatch.setattr(T, "run", boom)
    assert T.main([PHASE, BRANCH, world["commit"]]) == 1
    assert capsys.readouterr().out.strip().splitlines()[-1].startswith(T.OFF)
