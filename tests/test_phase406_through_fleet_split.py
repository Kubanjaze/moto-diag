"""Phase 406 (K93) — the fleet's database step in two calls, for the Mac.

The way in has no terminal, so the yes is asked on the Mac between the dry
run (`--dry-run-only`) and the apply (`--apply <sha256>`). The operator's
condition: the Mac shows the dry run's list before it asks. These cases hold
the second call to exactly the diff the first call showed: a wrong sha256, a
diff changed between the calls, a branch moved between them, or no dry run
at all is refused, with live untouched. Each runs on a real git mirror and a
tmp database standing in for live, as Phase 395's tests do.
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

PHASE = "991"
BRANCH = "phase-991-one-empty-table"
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


class FakeService:
    def __init__(self):
        self.calls = []

    def serves(self, db):
        return False

    def ctl(self, verb):
        self.calls.append(verb)
        return True

    def healthy(self, tries=30):
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
    c = sqlite3.connect(live)
    c.executescript("create table schema_version (version integer);"
                    "insert into schema_version values (87);")
    c.commit()
    c.close()
    return {"work": work, "mirror": mirror, "live": live, "root": tmp_path / "deploy",
            "backups": tmp_path / "backups", "commit": git(work, "rev-parse", "HEAD")}


def dry(w, said=None):
    lines = said if said is not None else []
    rc = T.dry_run_only(PHASE, BRANCH, w["commit"], mirror=w["mirror"], root=w["root"],
                        db=w["live"], backups=w["backups"], say=lines.append)
    return rc, lines


def approve(w, sha, said=None, service=None):
    lines = said if said is not None else []
    return T.apply_approved(PHASE, BRANCH, w["commit"], sha, root=w["root"], db=w["live"],
                            service=service or FakeService(), say=lines.append)


def tables(db):
    c = sqlite3.connect(db)
    try:
        return sorted(r[0] for r in c.execute("select name from sqlite_master where type='table'"))
    finally:
        c.close()


def shown_sha(lines):
    assert lines[-1].startswith(T.SHA_LINE), lines[-1]
    return lines[-1][len(T.SHA_LINE):]


def test_the_dry_run_alone_shows_the_list_and_its_sha256_and_changes_nothing(world):
    before = D.dump(world["live"])
    rc, said = dry(world)
    assert rc == 0
    text = "\n".join(said)
    assert "adds a new table, trial_empty, with 2 columns: id, said" in text
    assert text.index("adds a new table") < text.index(T.SHA_LINE), "the list comes first"
    co = world["root"] / PHASE
    assert shown_sha(said) == D.sha256(D.diff_path(co, PHASE))
    assert D.dump(world["live"]) == before
    assert not T.answer_path(co, PHASE).exists(), "the dry run alone wrote an answer"
    assert git(co, "rev-parse", "HEAD") == world["commit"], "the dry run alone committed"


def test_the_apply_of_that_sha256_makes_the_change_and_records_the_macs_yes(world):
    _, said = dry(world)
    applied: list[str] = []
    assert approve(world, shown_sha(said), said=applied) == 0
    assert "trial_empty" in tables(world["live"])
    co = world["root"] / PHASE
    files = git(co, "diff", "--name-only", f"{world['commit']}..HEAD").split()
    assert sorted(files) == sorted(T.deploy_files(PHASE)), files
    answer = T.answer_path(co, PHASE).read_text()
    assert "on the Mac, through the way in" in answer and "> yes" in answer
    assert shown_sha(said) in answer
    assert "equals the approved exact diff: yes" in "\n".join(applied)


def test_a_wrong_sha256_applies_nothing(world):
    dry(world)
    before = D.dump(world["live"])
    with pytest.raises(T.Off, match="not the one you said yes to"):
        approve(world, "0" * 64)
    assert D.dump(world["live"]) == before
    assert git(world["root"] / PHASE, "rev-parse", "HEAD") == world["commit"]


def test_a_diff_changed_between_the_calls_applies_nothing(world):
    _, said = dry(world)
    diff = D.diff_path(world["root"] / PHASE, PHASE)
    diff.write_text(diff.read_text() + "\n")
    before = D.dump(world["live"])
    with pytest.raises(T.Off, match="not the one you said yes to"):
        approve(world, shown_sha(said))
    assert D.dump(world["live"]) == before


def test_a_branch_moved_between_the_calls_applies_nothing(world):
    _, said = dry(world)
    work = world["work"]
    (work / "README.md").write_text("moved\n")
    git(work, "commit", "-qam", "the branch moves on")
    git(world["mirror"], "fetch", "-q", str(work), f"+{BRANCH}:{BRANCH}")
    before = D.dump(world["live"])
    with pytest.raises(T.Off, match="has moved since the dry run"):
        approve(world, shown_sha(said))
    assert D.dump(world["live"]) == before


def test_an_apply_with_no_dry_run_before_it_applies_nothing(world):
    before = D.dump(world["live"])
    with pytest.raises(T.Off, match="no dry run here"):
        approve(world, "0" * 64)
    assert D.dump(world["live"]) == before


def test_a_dry_run_of_another_commit_applies_nothing(world):
    _, said = dry(world)
    before = D.dump(world["live"])
    with pytest.raises(T.Off, match="not of"):
        T.apply_approved(PHASE, BRANCH, "f" * 40, shown_sha(said), root=world["root"],
                         db=world["live"], service=FakeService(), say=lambda s: None)
    assert D.dump(world["live"]) == before


def test_once_applied_both_calls_say_so_and_check(world):
    _, said = dry(world)
    approve(world, shown_sha(said))
    again: list[str] = []
    assert dry(world, said=again)[0] == 0
    assert "already on the live database" in "\n".join(again)
    assert approve(world, "0" * 64) == 0


def test_the_desktops_own_step_still_asks_there(world):
    asked: list[str] = []
    assert T.run(PHASE, BRANCH, world["commit"], mirror=world["mirror"], root=world["root"],
                 db=world["live"], backups=world["backups"],
                 ask=lambda q: asked.append(q) or "yes", service=FakeService(),
                 say=lambda s: None) == 0
    assert asked == [T.QUESTION]
    assert "on the home desktop" in T.answer_path(world["root"] / PHASE, PHASE).read_text()


@pytest.mark.parametrize("argv,why", [
    (["991", BRANCH, "a" * 40, "--apply", "abc"], "not one a dry run prints"),
    (["991", BRANCH, "short", "--dry-run-only"], "not one the fleet writes"),
])
def test_the_command_line_refuses_what_it_cannot_hold(capsys, argv, why):
    assert T.main(argv) == 1
    assert why in capsys.readouterr().out


def test_the_two_modes_cannot_be_asked_together():
    with pytest.raises(SystemExit):
        T.main(["991", BRANCH, "a" * 40, "--dry-run-only", "--apply", "b" * 64])
