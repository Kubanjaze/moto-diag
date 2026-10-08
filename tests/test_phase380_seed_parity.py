"""Phase 380, the operator's 2A — a content migration's rows equal a fresh seed build.

"With 2A, each content migration's dry run shows the changed rows equal a
fresh seed build, by key, so the seed and live can't drift." `deploy.py`
compares every `known_issues` row a migration adds or changes with the row of
the same `row_key` in a fresh build of the seed at HEAD. A difference is a
scope problem: the dry run records it and the apply refuses.

Every case runs in a fixture repository on fixture databases; the fresh seed
build is injected, so this file never builds the real seed.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from test_phase358_deploy_contract import D, _git, record_regression

PHASE = "ZZZ"
SCHEMA = """
    create table known_issues (id integer primary key, row_key text unique, title text,
                               description text, make text, model text,
                               created_at text);
    create table schema_version (version integer);
"""
SEED_ROWS = [("honda-stator", "Stator failure", "the seed's description", "Honda", None),
             ("honda-regulator", "Regulator failure", "the regulator", "Honda", None)]
SCOPE = {"tables": {
    "known_issues": {"changed": [{"where": "row_key = ?", "params": ["honda-stator"],
                                  "fields": ["description"]}]},
    "schema_version": {"added": 1}}}


def _db(path, description: str) -> None:
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    c.execute("insert into known_issues values (1, 'honda-stator', 'Stator failure', ?, "
              "'Honda', NULL, 'x')", (description,))
    c.execute("insert into known_issues values (2, 'honda-regulator', 'Regulator failure', "
              "'the regulator', 'Honda', NULL, 'x')")
    c.execute("insert into schema_version values (84)")
    c.commit()
    c.close()


def fresh_seed(path) -> None:
    """The stand-in for a fresh seed build: what the seed says today."""
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    for i, (key, title, desc, make, model) in enumerate(SEED_ROWS, start=1):
        c.execute("insert into known_issues values (?, ?, ?, ?, ?, ?, 'fresh clock')",
                  (i, key, title, desc, make, model))
    c.commit()
    c.close()


def migrate_to(description: str):
    def _migrate(path) -> list[int]:
        c = sqlite3.connect(path)
        c.execute("update known_issues set description = ? where row_key = 'honda-stator'",
                  (description,))
        c.execute("insert into schema_version values (85)")
        c.commit()
        c.close()
        return [85]
    return _migrate


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
    record_regression(repo)
    live = tmp_path / "live.db"
    _db(live, "an old description the seed has since corrected")
    return {"repo": repo, "live": live, "backups": tmp_path / "backups"}


def _dryrun(env, migrate) -> str:
    D.dryrun(PHASE, db=env["live"], backups=env["backups"], repo=env["repo"],
             migrate=migrate, parity_build=fresh_seed)
    return D._header(D.diff_path(env["repo"], PHASE).read_text())["Scope problems"]


def test_a_migration_writing_what_the_seed_says_passes(env):
    assert _dryrun(env, migrate_to("the seed's description")) == "none"


def test_a_migration_writing_otherwise_is_a_scope_problem(env):
    problems = _dryrun(env, migrate_to("a description the seed does not say"))
    assert "seed parity: honda-stator description" in problems
    assert "the seed says \"the seed's description\"" in problems


def test_apply_live_refuses_it(env, capsys):
    """The dry run's own problem makes the apply refuse; and a fresh dry run
    at apply time runs the same check."""
    _dryrun(env, migrate_to("a description the seed does not say"))
    _git(env["repo"], "add", str(D.diff_path(env["repo"], PHASE)))
    _git(env["repo"], "commit", "-qm", "the diff")
    before = D.dump(env["live"])
    assert D.apply_live(PHASE, db=env["live"], repo=env["repo"],
                        migrate=migrate_to("a description the seed does not say"),
                        parity_build=fresh_seed) == 2
    assert D.dump(env["live"]) == before
    assert "seed parity" in capsys.readouterr().err


def test_apply_live_runs_it_again_on_its_own_fresh_dry_run(env, capsys):
    """The dry run was clean; by the apply, the seed says something else (it
    was edited after the approval). The apply's own fresh run catches it."""
    assert _dryrun(env, migrate_to("the seed's description")) == "none"
    _git(env["repo"], "add", str(D.diff_path(env["repo"], PHASE)))
    _git(env["repo"], "commit", "-qm", "the approved diff")

    def edited_seed(path) -> None:
        fresh_seed(path)
        c = sqlite3.connect(path)
        c.execute("update known_issues set description = 'edited after the approval' "
                  "where row_key = 'honda-stator'")
        c.commit()
        c.close()

    before = D.dump(env["live"])
    assert D.apply_live(PHASE, db=env["live"], repo=env["repo"],
                        migrate=migrate_to("the seed's description"),
                        parity_build=edited_seed) == 2
    assert D.dump(env["live"]) == before
    err = capsys.readouterr().err
    assert "a fresh dry run leaves the scope" in err and "seed parity" in err


def test_a_row_key_no_seed_holds_is_a_problem(env):
    def _migrate(path) -> list[int]:
        c = sqlite3.connect(path)
        c.execute("update known_issues set row_key = 'honda-renamed', description = "
                  "'the seed''s description' where id = 1")
        c.execute("insert into schema_version values (85)")
        c.commit()
        c.close()
        return [85]
    D.scope_path(env["repo"], PHASE).write_text(json.dumps({"tables": {
        "known_issues": {"changed": [{"where": "row_key = ?", "params": ["honda-stator"],
                                      "fields": ["description", "row_key"]}]},
        "schema_version": {"added": 1}}}))
    assert "row_key 'honda-renamed' is in no seed entry" in _dryrun(env, _migrate)


def test_a_migration_that_touches_no_known_issue_is_not_checked(tmp_path):
    called = []
    d = {"schema_version": {"cols": ["version"], "added": [1], "removed": [],
                            "changed": [], "a": {}, "b": {1: (1, 85)}}}
    assert D.seed_parity(tmp_path, tmp_path / "x.db", d,
                         build=lambda p: called.append(p)) == []
    assert called == []
