"""Phase 380, bug fix #1 — the deploy diff sees a column a migration adds.

`deploy.diff` kept only the old table's columns. Migration 085 adds
`known_issues.row_key`, so its dry run crashed on the scope's `to` check
(`list.index(x): x not in list`), and the exact diff would have dropped the
new column's values (`zip` truncates to the shorter side). Both sides are
now lined up on the union of the two column lists.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from test_phase358_deploy_contract import D, _git, record_regression

PHASE = "ZZZ"


def _live(path) -> None:
    c = sqlite3.connect(path)
    c.executescript("create table items (id integer primary key, title text);"
                    "insert into items values (1, 'first'), (2, 'second');"
                    "create table schema_version (version integer);"
                    "insert into schema_version values (84);")
    c.close()


def add_a_key(values: dict):
    def _migrate(path) -> list[int]:
        c = sqlite3.connect(path)
        c.execute("alter table items add column key text")
        for row_id, key in values.items():
            c.execute("update items set key = ? where id = ?", (key, row_id))
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
    scope = {"tables": {
        "items": {"changed": [
            {"where": "id = ?", "params": [1], "fields": ["key"], "to": {"key": "k-first"}},
            {"where": "id = ?", "params": [2], "fields": ["key"], "to": {"key": "k-second"}}]},
        "schema_version": {"added": 1}},
        "schema": {"changed": ["table items"]}}
    D.scope_path(repo, PHASE).write_text(json.dumps(scope))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "scope")
    record_regression(repo)
    live = tmp_path / "live.db"
    _live(live)
    return {"repo": repo, "live": live, "backups": tmp_path / "backups"}


def _dryrun(env, migrate) -> str:
    D.dryrun(PHASE, db=env["live"], backups=env["backups"], repo=env["repo"], migrate=migrate)
    return D.diff_path(env["repo"], PHASE).read_text()


def test_a_new_column_is_scoped_and_kept_in_the_exact_diff(env):
    text = _dryrun(env, add_a_key({1: "k-first", 2: "k-second"}))
    assert D._header(text)["Scope problems"] == "none"
    approved = D._approved_exact(text)
    assert approved["rows"]["items"]["changed"]["1"]["key"] == [None, "k-first"]
    assert approved["rows"]["items"]["changed"]["2"]["key"] == [None, "k-second"]


def test_a_wrong_value_in_the_new_column_is_a_problem(env):
    text = _dryrun(env, add_a_key({1: "k-first", 2: "not-the-scopes-key"}))
    assert "items rowid 2: key is not the scope's 'to' value" in D._header(text)["Scope problems"]


def test_the_rows_line_up_by_name():
    a = {"t": (["id", "title"], {1: (1, 1, "x")})}
    b = {"t": (["id", "title", "key"], {1: (1, 1, "x", "k")})}
    d = D.diff(a, b)
    assert d["t"]["cols"] == ["id", "title", "key"]
    assert d["t"]["a"][1] == (1, 1, "x", None) and d["t"]["changed"] == [1]
    dropped = D.diff(b, a)
    assert dropped["t"]["cols"] == ["id", "title", "key"]
    assert dropped["t"]["b"][1] == (1, 1, "x", None)
