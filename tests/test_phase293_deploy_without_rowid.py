"""Phase 293, item 1a (K131) — the deploy tool reads a table without a rowid by its key.

Migration 092 adds an FTS5 index, and two of FTS5's shadow tables are
WITHOUT ROWID (`_idx`, keyed on `segid, term`; `_config`, keyed on `k`).
`deploy.dump()` read every table through `select rowid, *`, so the dry run,
`apply-live` and `verify-live` raised `no such column: rowid` on a database
holding one. The operator, 2026-11-22: "293 also teaches the deploy tool to
read tables without row numbers by their key, with tests".

The known-bad fixture is `.claude/skills/deploy/fixtures/without_rowid.sql`;
`_old_dump` is the read as it was, which must fail on it. Every case runs on
358's fixture repository form, on temporary databases.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from test_phase358_deploy_contract import D, ROOT, _git, record_regression

PHASE = "ZZZ"
FIXTURE = ROOT / ".claude" / "skills" / "deploy" / "fixtures" / "without_rowid.sql"

#: The FTS5 shape migration 092 builds: an external-content index over a
#: page table, so SQLite makes `_data`, `_idx`, `_config` and `_docsize`.
FTS = ("create virtual table pages_fts using fts5("
       "text, content='pages', content_rowid='id')")
SHADOWS = ["pages_fts_config", "pages_fts_data", "pages_fts_docsize", "pages_fts_idx"]


def _fixture(path) -> None:
    c = sqlite3.connect(path)
    c.executescript(FIXTURE.read_text())
    c.close()


def _old_dump(path):
    """deploy.dump() before K131, verbatim: every table by rowid."""
    c, out = D._ro(path), {}
    for (t,) in c.execute("select name from sqlite_master where type='table' "
                          "and name not like 'sqlite_%'").fetchall():
        cols = [r[1] for r in c.execute(f"pragma table_info('{t}')")]
        out[t] = (cols, {r[0]: r for r in c.execute(f"select rowid, * from '{t}'")})
    c.close()
    return out


def test_the_known_bad_fixture_fails_the_old_read(tmp_path):
    db = tmp_path / "bad.db"
    _fixture(db)
    with pytest.raises(sqlite3.OperationalError, match="no such column: rowid"):
        _old_dump(db)


def test_dump_reads_both_tables_by_their_key(tmp_path):
    db = tmp_path / "fixture.db"
    _fixture(db)
    d = D.dump(db)
    cols, rows = d["one_key"]
    assert cols == ["k", "v"]
    assert rows == {"pgsz": ("pgsz", "pgsz", 4050), "version": ("version", "version", 4)}
    cols, rows = d["two_key"]
    assert cols == ["segid", "term", "pgno"]
    assert sorted(rows) == [(1, b"\x00"), (1, b"0a"), (2, b"\x00")]
    assert rows[(1, b"0a")] == ((1, b"0a"), 1, b"0a", 2)
    # The rowid table beside them is read by its rowid, as before.
    assert d["items"] == (["id", "title"], {1: (1, 1, "first")})


def test_a_table_is_known_by_its_definition_not_its_name(tmp_path):
    db = tmp_path / "names.db"
    c = sqlite3.connect(db)
    c.executescript("create table looks_like_fts_config (k text primary key, v);"
                    "insert into looks_like_fts_config values ('version', 4);")
    c.close()
    rows = D.dump(db)["looks_like_fts_config"][1]
    assert list(rows) == [1], "a rowid table must stay keyed by its rowid"


def test_diff_names_a_row_added_removed_and_changed_by_its_key(tmp_path):
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    _fixture(a)
    _fixture(b)
    c = sqlite3.connect(b)
    c.executescript("""
        insert into one_key values ('crisismerge', 16);
        delete from one_key where k = 'pgsz';
        update one_key set v = 5 where k = 'version';
        insert into two_key values (3, x'00', 1);
        delete from two_key where segid = 2;
        update two_key set pgno = 9 where segid = 1 and term = x'3061';
    """)
    c.close()
    d = D.diff(D.dump(a), D.dump(b))
    assert d["one_key"]["added"] == ["crisismerge"]
    assert d["one_key"]["removed"] == ["pgsz"]
    assert d["one_key"]["changed"] == ["version"]
    assert d["two_key"]["added"] == [(3, b"\x00")]
    assert d["two_key"]["removed"] == [(2, b"\x00")]
    assert d["two_key"]["changed"] == [(1, b"0a")]
    assert "items" not in d
    scope = {"tables": {"one_key": {"added": 1, "removed": 1},
                        "two_key": {"added": 1, "removed": 1}}}
    probs = D.check_scope(d, scope, {})
    assert "one_key: changed rowids ['version'], scope names []" in probs
    assert "two_key: changed rowids [(1, b'0a')], scope names []" in probs
    assert len(probs) == 2
    assert "### one_key rowid version" in D.report(d)


def test_the_f158_census_the_dry_run_runs_reads_them_too(tmp_path):
    """The dry run's census (`scripts/f158_census.py`) read by rowid as well,
    found by this file's end-to-end case."""
    db = tmp_path / "census.db"
    _fixture(db)
    c = sqlite3.connect(db)
    c.execute("insert into one_key values ('note', 'see Phase 999')")
    c.commit()
    c.close()
    sys_path = str(ROOT / "scripts")
    import sys
    sys.path.insert(0, sys_path)
    import f158_census
    assert f158_census.census(db) == [("one_key", "v", "note", "Phase N", "Phase 999")]


# ------------------------------------------------- the whole deploy, end to end
def _live(path) -> None:
    c = sqlite3.connect(path)
    c.executescript("create table items (id integer primary key, title text);"
                    "insert into items values (1, 'front brake caliper torque');"
                    "create table schema_version (version integer);"
                    "insert into schema_version values (91);")
    c.close()


def add_the_index(path) -> list[int]:
    c = sqlite3.connect(path)
    c.execute("create table pages (id integer primary key, text text)")
    c.execute(FTS)
    c.execute("insert into schema_version values (92)")
    c.commit()
    c.close()
    return [92]


def _first_rows(tmp_path) -> dict[str, int]:
    """The rows SQLite writes into the shadow tables when the index is made,
    measured, never remembered."""
    db = tmp_path / "measure.db"
    _live(db)
    add_the_index(db)
    c = sqlite3.connect(db)
    out = {t: c.execute(f"select count(*) from '{t}'").fetchone()[0] for t in SHADOWS}
    c.close()
    return {t: n for t, n in out.items() if n}


@pytest.fixture
def env(tmp_path):
    first = _first_rows(tmp_path)
    assert set(first) == {"pages_fts_config", "pages_fts_data"}
    repo = tmp_path / "repo"
    (repo / "docs" / "phases" / "in_progress").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    scope = {"tables": {"schema_version": {"added": 1},
                        **{t: {"added": n} for t, n in first.items()}},
             "schema": {"added": ["table pages", "table pages_fts",
                                  *(f"table {t}" for t in SHADOWS)]}}
    D.scope_path(repo, PHASE).write_text(json.dumps(scope, indent=1))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "scope")
    record_regression(repo)
    live = tmp_path / "live.db"
    _live(live)
    return {"repo": repo, "live": live, "backups": tmp_path / "backups"}


def test_dryrun_apply_live_and_verify_live_pass_on_an_fts5_index(env, capsys):
    assert D.dryrun(PHASE, db=env["live"], backups=env["backups"], repo=env["repo"],
                    migrate=add_the_index) == 0
    text = D.diff_path(env["repo"], PHASE).read_text()
    assert D._header(text)["Scope problems"] == "none"
    approved = D._approved_exact(text)
    assert set(approved["rows"]["pages_fts_config"]["added"]) == {"version"}
    _git(env["repo"], "add", str(D.diff_path(env["repo"], PHASE)))
    _git(env["repo"], "commit", "-qm", "the approved diff")
    assert D.apply_live(PHASE, db=env["live"], repo=env["repo"], migrate=add_the_index) == 0
    capsys.readouterr()
    assert D.verify_live(PHASE, db=env["live"], repo=env["repo"]) == 0
    out = capsys.readouterr().out
    assert "equals the approved exact diff: yes" in out
