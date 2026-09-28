"""Phase 357 — F172: apply-live refuses unless a fresh dry run EQUALS the
committed diff, field for field, clock values masked.

Before 357 the fresh run was checked against the scope only, so a migration
edited after the dry run, whose new change still fell inside the scope's
fields, would have been applied. 359 compared the two by hand.

Fixture databases only, 358's harness. The migrations here write a clock
value (microseconds, so two runs never agree on it) beside their content,
as a real migration's `applied_at` does.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3

from test_phase358_deploy_contract import (  # noqa: F401  (env is a fixture)
    D, PHASE, SCOPE, _commit_diff, _dryrun, _git, _refusal, env,
)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat(sep=" ")


def _migration(text: str = "check the thing, sourced", stamp: str | None = None,
               extra_sql: str = ""):
    def migrate(path) -> list[int]:
        c = sqlite3.connect(path)
        c.execute("insert into workflow_templates values (2, 'tpl_b', ?)", (stamp or _now(),))
        c.execute("update checklist_items set instruction_text = ? where id = 1", (text,))
        c.execute("insert into schema_version values (71)")
        if extra_sql:
            c.executescript(extra_sql)
        c.commit()
        c.close()
        return [71]
    return migrate


def _approve(env, migrate) -> None:
    assert _dryrun(env, migrate) == 0
    _commit_diff(env)


class TestTheExactComparison:
    def test_a_fresh_run_differing_only_in_its_clock_applies(self, env):
        """The good case: the clock value differs between the two runs (it
        carries microseconds) and is masked; everything else is equal."""
        _approve(env, _migration())
        assert D.apply_live(PHASE, db=env["live"], repo=env["repo"], migrate=_migration()) == 0
        live = D.diff_path(env["repo"], PHASE, "live").read_text()
        assert "Equals the approved exact diff:** `yes`" in live

    def test_a_fresh_run_differing_in_one_field_is_refused(self, env, capsys):
        """The known-bad case F172 names: the edit stays inside the scope
        (instruction_text is an allowed field) and 358's check passed it."""
        _approve(env, _migration())
        err = _refusal(env, capsys, _migration("check the thing, sourced!"))
        assert "differs from the approved diff in 1 field(s)" in err
        assert "/rows/checklist_items/changed/1/instruction_text" in err

    def test_the_same_edit_passed_the_scope_check_alone(self, env):
        """The control: the edited migration is in scope, so the refusal
        above is the exact comparison's doing, not the scope's."""
        allowed = D.resolve(SCOPE, env["live"])
        after = env["live"].with_name("after.db")
        D.backup(env["live"], after)
        _migration("check the thing, sourced!")(after)
        assert D.check_scope(D.diff(D.dump(env["live"]), D.dump(after)), SCOPE, allowed) == []

    def test_a_fixed_date_is_compared_not_masked(self, env, capsys):
        """Only the run's own clock is masked. A literal date the migration
        writes, edited after the dry run, is a difference."""
        _approve(env, _migration(stamp="2020-01-01 00:00:00"))
        err = _refusal(env, capsys, _migration(stamp="2020-01-02 00:00:00"))
        assert "/rows/workflow_templates/added/2/description" in err

    def test_a_diff_written_before_the_fix_is_refused(self, env, capsys):
        _approve(env, _migration())
        f = D.diff_path(env["repo"], PHASE)
        f.write_text(f.read_text().split(D.EXACT, 1)[0])
        _commit_diff(env)
        assert "has no exact diff" in _refusal(env, capsys)


def _scope_with_schema(env, names: list[str]) -> None:
    scope = json.loads(json.dumps(SCOPE))
    scope["schema"] = {"added": names}
    D.scope_path(env["repo"], PHASE).write_text(json.dumps(scope, indent=1))
    _git(env["repo"], "add", "-A")
    _git(env["repo"], "commit", "-qm", "scope with schema")


NEW_TABLE = "create table runs (id integer primary key, note text);"


class TestSchemaObjects:
    def test_a_named_new_table_is_in_scope_and_reported(self, env):
        _scope_with_schema(env, ["table runs"])
        assert _dryrun(env, _migration(extra_sql=NEW_TABLE)) == 0
        text = D.diff_path(env["repo"], PHASE).read_text()
        assert "## schema added: table runs" in text
        assert "CREATE TABLE runs (id integer primary key, note text)" in text.split(D.EXACT, 1)[1]

    def test_an_unnamed_new_table_is_a_scope_problem(self, env):
        assert _dryrun(env, _migration(extra_sql=NEW_TABLE)) == 1
        head = D._header(D.diff_path(env["repo"], PHASE).read_text())
        assert "schema added: ['table runs'], scope names []" in head["Scope problems"]

    def test_a_fresh_run_with_a_different_column_is_refused(self, env, capsys):
        """The table is still named in scope; its SQL differs."""
        _scope_with_schema(env, ["table runs"])
        _approve(env, _migration(extra_sql=NEW_TABLE))
        err = _refusal(env, capsys, _migration(
            extra_sql="create table runs (id integer primary key, notes text);"))
        assert "/schema/sql/table runs" in err
