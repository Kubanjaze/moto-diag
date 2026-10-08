"""Phase 358, K3 — the deploy script, on fixture databases only.

The operator: "it writes the approved dry-run diff into the phase folder,
and the live apply refuses to run without that file. no more temp copies."
Accepted at v1.0: "live apply refuses unless the diff file is committed and
unchanged." From the triage: the scope is data, backups keep 5, the F158
census runs on the copy, and the apply refuses if live no longer equals the
backup or a fresh dry run leaves the scope.

Every case runs in a tmp git repository against a tmp database, with a
stand-in migration. Nothing here opens data/motodiag.db or ~/backups.
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

PHASE = "ZZZ"
SCOPE = {"tables": {
    "workflow_templates": {"added": 1},
    "checklist_items": {"changed": [{
        "where": "template_id = (select id from workflow_templates where slug = ?) "
                 "and sequence_number = ?",
        "params": ["tpl_a", 1], "fields": ["instruction_text"]}]},
    "schema_version": {"added": 1}}}


def _make_live(path: pathlib.Path) -> None:
    c = sqlite3.connect(path)
    c.executescript("""
        create table workflow_templates (id integer primary key, slug text, description text);
        create table checklist_items (id integer primary key, template_id integer,
            sequence_number integer, instruction_text text);
        create table known_issues (id integer primary key, description text);
        create table schema_version (version integer);
        insert into workflow_templates values (1, 'tpl_a', 'the first template');
        insert into checklist_items values (1, 1, 1, 'check the thing');
        insert into checklist_items values (2, 1, 2, 'check the other thing');
        insert into known_issues values (1, 'a known issue');
        insert into schema_version values (70);
    """)
    c.commit()
    c.close()


def migrate_in_scope(path) -> list[int]:
    c = sqlite3.connect(path)
    c.execute("insert into workflow_templates values (2, 'tpl_b', 'a new template')")
    c.execute("update checklist_items set instruction_text = 'check the thing, sourced' where id = 1")
    c.execute("insert into schema_version values (71)")
    c.commit()
    c.close()
    return [71]


def migrate_out_of_scope(path) -> list[int]:
    migrate_in_scope(path)
    c = sqlite3.connect(path)
    c.execute("update known_issues set description = 'rewritten' where id = 1")
    c.commit()
    c.close()
    return [71]


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def record_regression(repo, at: str = "HEAD") -> str:
    """Commit a phase log whose regression of record is at ``at``, as
    regression.sh prints it (Phase 378, K18). Returns that commit."""
    commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", at],
                            check=True, capture_output=True, text=True).stdout.strip()
    log = repo / "docs" / "phases" / "in_progress" / f"{PHASE}_phase_log.md"
    log.write_text(f"# log\n\nRegression of record: 10 passed, 0 failed, 0 skipped, 0 errors "
                   f"at `{commit}` (1 min 0 s wall, `python -m pytest -n auto --dist load`, "
                   f"exit 0)\n")
    _git(repo, "add", str(log))
    _git(repo, "commit", "-qm", "the regression of record")
    return commit


@pytest.fixture
def env(tmp_path):
    repo = tmp_path / "repo"
    (repo / "docs" / "phases" / "in_progress").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    D.scope_path(repo, PHASE).write_text(json.dumps(SCOPE, indent=1))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "scope")
    record_regression(repo)  # Phase 378, K18: the apply comes after the regression
    live = tmp_path / "live.db"
    _make_live(live)
    return {"repo": repo, "live": live, "backups": tmp_path / "backups"}


def _dryrun(env, migrate=migrate_in_scope):
    return D.dryrun(PHASE, db=env["live"], backups=env["backups"], repo=env["repo"],
                    migrate=migrate)


def _commit_diff(env):
    _git(env["repo"], "add", str(D.diff_path(env["repo"], PHASE)))
    _git(env["repo"], "commit", "-qm", "the approved diff")


def _apply(env, migrate=migrate_in_scope):
    return D.apply_live(PHASE, db=env["live"], repo=env["repo"], migrate=migrate)


def _refusal(env, capsys, migrate=migrate_in_scope) -> str:
    before = D.dump(env["live"])
    assert _apply(env, migrate) == 2
    assert D.dump(env["live"]) == before, "a refused apply touched live"
    return capsys.readouterr().err


class TestTheDryRun:
    def test_it_writes_the_diff_into_the_phase_folder(self, env):
        assert _dryrun(env) == 0
        text = D.diff_path(env["repo"], PHASE).read_text()
        head = D._header(text)
        assert head["Scope problems"] == "none"
        assert head["F158 census on the copy"] == "0"
        assert pathlib.Path(head["Backup"]).parent == env["backups"]
        assert "check the thing, sourced" in text.split(D.MARK, 1)[1]

    def test_live_is_only_read_and_no_copy_is_left(self, env):
        before = D.dump(env["live"])
        _dryrun(env)
        assert D.dump(env["live"]) == before
        assert not list((env["repo"] / "data" / "deploy_scratch").glob("*.db"))

    def test_an_out_of_scope_migration_is_reported_in_the_file(self, env):
        assert _dryrun(env, migrate_out_of_scope) == 1
        head = D._header(D.diff_path(env["repo"], PHASE).read_text())
        assert "known_issues: not in scope" in head["Scope problems"]

    def test_the_census_runs_on_the_copy(self, env):
        def planting(path):
            migrate_in_scope(path)
            c = sqlite3.connect(path)
            c.execute("update workflow_templates set description = 'added in Phase 358' where id = 2")
            c.commit()
            c.close()
            return [71]
        _dryrun(env, planting)
        assert D._header(D.diff_path(env["repo"], PHASE).read_text())[
            "F158 census on the copy"] == "1"

    def test_five_backups_are_kept(self, env):
        env["backups"].mkdir()
        for i in range(7):
            p = env["backups"] / f"motodiag_old{i}.db"
            p.write_text("x")
            import os
            os.utime(p, (1_000_000 + i, 1_000_000 + i))
        removed = D.retain(env["backups"])
        assert sorted(removed) == ["motodiag_old0.db", "motodiag_old1.db"]
        assert len(list(env["backups"].glob("motodiag_*.db"))) == 5


class TestTheApplyRefuses:
    def test_with_no_diff_file(self, env, capsys):
        assert "no approved dry-run diff" in _refusal(env, capsys)

    def test_with_an_uncommitted_diff_file(self, env, capsys):
        _dryrun(env)
        assert "not committed" in _refusal(env, capsys)

    def test_with_a_diff_file_changed_after_its_commit(self, env, capsys):
        _dryrun(env)
        _commit_diff(env)
        f = D.diff_path(env["repo"], PHASE)
        f.write_text(f.read_text() + "\nan edit after approval\n")
        assert "differs from its committed version" in _refusal(env, capsys)

    def test_when_the_approved_dry_run_was_out_of_scope(self, env, capsys):
        _dryrun(env, migrate_out_of_scope)
        _commit_diff(env)
        assert "records scope problems" in _refusal(env, capsys)

    def test_when_live_changed_since_the_backup(self, env, capsys):
        _dryrun(env)
        _commit_diff(env)
        c = sqlite3.connect(env["live"])
        c.execute("insert into known_issues values (2, 'written after the backup')")
        c.commit()
        c.close()
        assert "live differs from the backup" in _refusal(env, capsys)

    def test_when_a_fresh_dry_run_leaves_the_scope(self, env, capsys):
        _dryrun(env)
        _commit_diff(env)
        assert "fresh dry run leaves the scope" in _refusal(env, capsys, migrate_out_of_scope)

    def test_when_the_scope_file_changed(self, env, capsys):
        _dryrun(env)
        _commit_diff(env)
        D.scope_path(env["repo"], PHASE).write_text(json.dumps({"tables": {}}))
        assert "scope file changed" in _refusal(env, capsys)

    def test_when_the_backup_is_gone(self, env, capsys):
        _dryrun(env)
        _commit_diff(env)
        pathlib.Path(D._header(D.diff_path(env["repo"], PHASE).read_text())["Backup"]).unlink()
        assert "missing or no longer hashes" in _refusal(env, capsys)


class TestACleanApply:
    def test_it_applies_writes_the_live_diff_and_stays_in_scope(self, env):
        _dryrun(env)
        _commit_diff(env)
        assert _apply(env) == 0
        c = sqlite3.connect(env["live"])
        assert c.execute("select instruction_text from checklist_items where id = 1"
                         ).fetchone()[0] == "check the thing, sourced"
        c.close()
        live_diff = D.diff_path(env["repo"], PHASE, "live").read_text()
        assert "Scope problems:** `none`" in live_diff
        assert not list((env["repo"] / "data" / "deploy_scratch").glob("*.db"))


class TestTheScopeFixtures:
    FIX = ROOT / ".claude" / "skills" / "deploy" / "fixtures"

    def test_the_known_bad_scope_is_refused(self, env):
        """An entry that matches two rows names no single row; the dry run
        stops before migrating anything."""
        D.scope_path(env["repo"], PHASE).write_text((self.FIX / "scope_bad_ambiguous.json").read_text())
        with pytest.raises(SystemExit, match="matches 2 rows, not 1"):
            _dryrun(env)

    def test_262s_scope_is_expressible_as_data(self):
        """Phase 262's hand-coded SCOPE (358_step0.md), written as data:
        five changed rows, each with its fields; 3 templates and 21 items added."""
        s = json.loads((self.FIX / "scope_262.json").read_text())
        items = s["tables"]["checklist_items"]
        assert len(items["changed"]) == 5 and items["added"] == 21
        assert s["tables"]["workflow_templates"]["added"] == 3


class TestNoTempCopies:
    def test_the_defaults_name_the_repo_and_the_backup_folder(self):
        for p in (D.LIVE, D.BACKUPS):
            assert "/tmp" not in str(p) and "/private/" not in str(p), p
        assert D.BACKUPS == pathlib.Path.home() / "backups" / "motodiag"
        assert D.KEEP == 5

    def test_the_scratch_folder_is_gitignored(self):
        r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q",
                            "data/deploy_scratch/x.db"])
        assert r.returncode == 0
