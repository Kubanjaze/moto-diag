"""Phase 405, K91 — the deploy check asks what the change did (F210, F259).

The operator chose option C: "the deploy check asks whether the change did
exactly what was approved, and whether anything else touched what it
changes; before the apply it refuses only a change since the dry run in a
table the change touches; after the apply, and in every later check, the
approved changes must hold, and other differences are listed, not failed."

The payments feed writes live all the time (F259), and a shop's own use will
too (F210). Here, stand-in tables carry those writes: `stripe_event_cursors`
and `stripe_feed_checkins` for the feed, `work_orders` for a shop. Fixture
databases only, through 358's deploy contract; never live.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import pathlib
import sqlite3
import sys

import pytest

from test_phase358_deploy_contract import (  # noqa: F401  (env is a fixture)
    D, PHASE, ROOT, SCOPE, _apply, _commit_diff, _dryrun, _git, _refusal, env,
    migrate_in_scope,
)
from test_phase379_verify_live_fails import _check_8

sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
import quartermaster as Q  # noqa: E402

TOUCHED = {"workflow_templates", "checklist_items", "schema_version"}
INDEX_SCOPE = {**SCOPE, "schema": {"added": ["index idx_x"]}}


def _sql(path, *stmts):
    c = sqlite3.connect(path)
    for s in stmts:
        c.execute(s)
    c.commit()
    c.close()


def _standins(env):
    """The feed's cursor and a shop's work order, beside 358's tables."""
    _sql(env["live"],
         "create table stripe_event_cursors (id integer primary key, cursor text)",
         "insert into stripe_event_cursors values (1, 'evt_1')",
         "create table work_orders (id integer primary key, title text)",
         "insert into work_orders values (1, 'first job')")


def _scope(env, scope: dict) -> None:
    D.scope_path(env["repo"], PHASE).write_text(json.dumps(scope, indent=1))
    _git(env["repo"], "commit", "-qam", "the phase's scope")


def _ready(env, migrate=migrate_in_scope, scope: dict | None = None):
    _standins(env)
    if scope is not None:
        _scope(env, scope)
    assert _dryrun(env, migrate) == 0
    _commit_diff(env)


def _deployed(env, migrate=migrate_in_scope, scope: dict | None = None):
    _ready(env, migrate, scope)
    assert _apply(env, migrate) == 0


def with_index(path) -> list[int]:
    """358's migration, and an index on `known_issues`, which the scope does
    not name as a table."""
    migrate_in_scope(path)
    _sql(path, "create index idx_x on known_issues (description)")
    return [71]


def with_checkins(path) -> list[int]:
    """As 404's migration: a new table for the feed's check-ins."""
    migrate_in_scope(path)
    _sql(path, "create table stripe_feed_checkins (id integer primary key, sent_at text)")
    return [71]


def _verify(env, capsys) -> tuple[int, str]:
    code = D.verify_live(PHASE, db=env["live"], repo=env["repo"])
    return code, capsys.readouterr().out


def _listed(out: str) -> str:
    return out.split("other differences, listed:", 1)[1].split("equals the approved", 1)[0]


def _instruction(env) -> str:
    c = sqlite3.connect(env["live"])
    (text,) = c.execute("select instruction_text from checklist_items where id = 1").fetchone()
    c.close()
    return text


def _live_diff(env) -> str:
    return D.diff_path(env["repo"], PHASE, "live").read_text()


class TestTheTouchedSet:
    def test_the_fixture_scope_s_three_tables(self, env):
        assert D.touched(SCOPE, None, {}) == TOUCHED
        _ready(env)
        approved = D._approved_exact(D.diff_path(env["repo"], PHASE).read_text())
        assert D.touched(SCOPE, approved, {}) == TOUCHED

    def test_an_index_the_scope_names_adds_its_table_read_from_the_migrated_copy(
            self, env, capsys):
        _ready(env, with_index, INDEX_SCOPE)
        assert _apply(env, with_index) == 0
        assert ("tables this change touches: checklist_items, known_issues, schema_version, "
                "workflow_templates") in capsys.readouterr().out

    def test_a_table_only_the_approved_diff_names_is_in_and_one_in_neither_is_out(self):
        approved = {"rows": {"invoices": {"added": {"1": {"id": 1}}}},
                    "schema": {"added": ["trigger g"], "removed": [], "changed": []}}
        got = D.touched({"tables": {}}, approved, {"trigger g": "payments"})
        assert got == {"invoices", "payments"}
        assert "known_issues" not in got

    def test_a_view_names_no_table(self, tmp_path):
        db = tmp_path / "v.db"
        _sql(db, "create table t (a)", "create view v as select a from t",
             "create index i on t (a)")
        names = D.tbl_names(db)
        assert names == {"table t": "t", "index i": "t"}
        assert D.touched({"tables": {}, "schema": {"added": ["view v"]}}, None, names) == set()

    def test_a_scope_naming_an_index_the_migration_never_creates_is_refused_first(
            self, env, capsys):
        """Approved with the index; the fresh dry run's migration lacks it.
        The fresh dry run's scope gate refuses before the split is reached."""
        _ready(env, with_index, INDEX_SCOPE)
        err = _refusal(env, capsys, migrate_in_scope)
        assert "a fresh dry run leaves the scope" in err
        assert "tables this change touches" not in capsys.readouterr().out

    def test_a_listed_server_write_in_a_touched_table_is_still_set_aside(self, env, capsys):
        """SERVER_WRITES still decides a verdict here: `api_keys` is touched
        (the scope names it), and a request writes `last_used_at` between the
        dry run and the apply."""
        _sql(env["live"], "create table api_keys (id integer primary key, last_used_at text)",
             "insert into api_keys values (2, '2026-09-16T15:30:24Z')")
        _ready(env, scope={"tables": {**SCOPE["tables"], "api_keys": {}}})
        _sql(env["live"], "update api_keys set last_used_at = '2026-10-19T22:27:00Z' where id = 2")
        assert _apply(env) == 0
        assert "api_keys 2 last_used_at" in _live_diff(env)


#: A write between the dry run and the apply, in a table the change does not
#: touch, and how the output counts it.
OUTSIDE = {
    "feed_cursor": ("update stripe_event_cursors set cursor = 'evt_2' where id = 1",
                    "stripe_event_cursors +0 ~1 -0"),
    "shop_work_order": ("insert into work_orders values (2, 'a shop job')",
                        "work_orders +1 ~0 -0"),
    "known_issue": ("insert into known_issues values (2, 'written after the backup')",
                    "known_issues +1 ~0 -0"),
}

#: A write between the dry run and the apply, in a table the change touches.
INSIDE = {
    "checklist_added": "insert into checklist_items values (3, 1, 3, 'later')",
    "checklist_changed": "update checklist_items set instruction_text = 'later' where id = 2",
    "checklist_removed": "delete from checklist_items where id = 2",
    "template_added": "insert into workflow_templates values (5, 'tpl_z', 'later')",
}


class TestBeforeTheApply:
    @pytest.mark.parametrize("case", sorted(OUTSIDE))
    def test_a_change_outside_the_touched_tables_is_listed_and_applied(self, env, capsys, case):
        stmt, counts = OUTSIDE[case]
        _ready(env)
        _sql(env["live"], stmt)
        assert _apply(env) == 0
        assert ("changed since the dry run, outside the tables this change touches: "
                + counts) in capsys.readouterr().out
        assert _instruction(env) == "check the thing, sourced"
        live = _live_diff(env)
        assert "Equals the approved exact diff:** `yes`" in live
        assert counts.split()[0] in live.split("Other differences, listed:**", 1)[1].splitlines()[0]

    @pytest.mark.parametrize("case", sorted(INSIDE))
    def test_a_change_in_a_touched_table_is_refused(self, env, capsys, case):
        _ready(env)
        _sql(env["live"], INSIDE[case])
        err = _refusal(env, capsys)
        assert "changed since the dry run" in err and err.rstrip().endswith("Stop and ask.")

    def test_a_table_touched_only_through_an_index_is_refused(self, env, capsys):
        _ready(env, with_index, INDEX_SCOPE)
        _sql(env["live"], "update known_issues set description = 'later' where id = 1")
        err = _refusal(env, capsys, with_index)
        assert "changed since the dry run" in err and "known_issues +0 ~1 -0" in err


class TestAfterTheApplyListed:
    """Every approved change holds; what else live holds is listed, exit 0."""

    @staticmethod
    def _passes(env, capsys, item: str) -> str:
        code, out = _verify(env, capsys)
        assert code == 0, out
        assert "equals the approved exact diff: yes" in out
        assert item in _listed(out), out
        return _listed(out)

    def test_a_new_known_issues_row(self, env, capsys):
        _deployed(env)
        _sql(env["live"], "insert into known_issues values (2, 'later')")
        self._passes(env, capsys, "known_issues +1 ~0 -0")

    def test_a_feed_cursor_rewritten(self, env, capsys):
        _deployed(env)
        _sql(env["live"], "update stripe_event_cursors set cursor = 'evt_9' where id = 1")
        self._passes(env, capsys, "stripe_event_cursors +0 ~1 -0")

    def test_rows_the_running_code_writes_to_a_table_the_change_created(self, env, capsys):
        """404's check-ins, written by the feed into the table 404 created."""
        _deployed(env, with_checkins,
                  {**SCOPE, "schema": {"added": ["table stripe_feed_checkins"]}})
        for i in (1, 2, 3):
            _sql(env["live"],
                 f"insert into stripe_feed_checkins values ({i}, '2026-11-1{i}T08:00:00Z')")
        self._passes(env, capsys, "stripe_feed_checkins +3 ~0 -0")

    def test_a_later_phase_s_rows_in_touched_tables(self, env, capsys):
        _deployed(env)
        _sql(env["live"], "insert into schema_version values (72)",
             "insert into checklist_items values (3, 1, 3, 'a later phase')")
        assert "schema_version +1 ~0 -0" in self._passes(env, capsys, "checklist_items +1 ~0 -0")

    def test_a_field_the_approved_diff_does_not_name_in_a_row_it_names(self, env, capsys):
        _deployed(env)
        _sql(env["live"], "update checklist_items set sequence_number = 9 where id = 1")
        self._passes(env, capsys, "checklist_items 1 sequence_number")

    def test_a_later_migration_s_schema_object(self, env, capsys):
        """The handoff's run for 404 needs this: live holds 334's objects."""
        _deployed(env)
        _sql(env["live"], "create table later_t (id integer primary key)")
        self._passes(env, capsys, "schema added: table later_t")

    def test_a_row_removed_from_a_touched_table_whose_approved_removed_is_empty(self, env, capsys):
        _deployed(env)
        _sql(env["live"], "delete from checklist_items where id = 2")
        self._passes(env, capsys, "checklist_items +0 ~0 -1")

    def test_an_approved_diff_with_no_entries_lists_every_difference(self, env, capsys):
        """384's shape: a change that changed nothing."""
        _deployed(env, lambda path: [], {"tables": {}})
        _sql(env["live"], "insert into known_issues values (2, 'later')",
             "insert into work_orders values (2, 'a shop job')")
        code, out = _verify(env, capsys)
        assert code == 0, out
        assert "known_issues +1 ~0 -0" in _listed(out) and "work_orders +1 ~0 -0" in _listed(out)

    def test_an_approved_changed_field_masked_as_the_clock_holds(self, env, capsys):
        """The migration writes the run's time; the approved diff masks it.
        verify-live reads live unmasked (against 1970), so the value it reads
        back lies outside any masking day, and still matches."""
        def stamping(path) -> list[int]:
            migrate_in_scope(path)
            now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat(sep=" ")
            _sql(path, f"update checklist_items set instruction_text = '{now}' where id = 1")
            return [71]
        _deployed(env, stamping)
        approved = D._approved_exact(D.diff_path(env["repo"], PHASE).read_text())
        assert approved["rows"]["checklist_items"]["changed"]["1"]["instruction_text"][1] == D.CLOCK
        assert D._TIMESTAMP.match(_instruction(env))
        code, out = _verify(env, capsys)
        assert code == 0, out
        assert "equals the approved exact diff: yes" in out


#: After the apply, a write that alters an approved entry.
ALTERS = {
    "approved_row_deleted": "delete from workflow_templates where id = 2",
    "approved_field_written_back": "update checklist_items set instruction_text = "
                                   "'check the thing' where id = 1",
    "approved_row_s_other_field": "update workflow_templates set description = 'edited' "
                                  "where id = 2",
}


class TestAfterTheApplyFailing:
    @staticmethod
    def _fails(env, capsys) -> str:
        code, out = _verify(env, capsys)
        assert code == 3, out
        assert "equals the approved exact diff: no" in out
        assert "the difference is not a later migration's" in out
        return out

    @pytest.mark.parametrize("case", sorted(ALTERS))
    def test_an_approved_entry_altered_or_missing(self, env, capsys, case):
        _deployed(env)
        _sql(env["live"], ALTERS[case])
        self._fails(env, capsys)

    def test_an_approved_index_dropped(self, env, capsys):
        _deployed(env, with_index, INDEX_SCOPE)
        _sql(env["live"], "drop index idx_x")
        assert "/schema/added/index idx_x" in self._fails(env, capsys)

    def test_a_migration_that_writes_otherwise_on_live_fails_the_apply_s_own_check(
            self, env, capsys):
        def two_faced(path) -> list[int]:
            migrate_in_scope(path)
            if pathlib.Path(path) == env["live"]:
                _sql(path, "update checklist_items set instruction_text = 'not as approved' "
                           "where id = 1")
            return [71]
        _ready(env)
        assert _apply(env, two_faced) == 1
        assert "Equals the approved exact diff:** `no`" in _live_diff(env)
        assert _verify(env, capsys)[0] == 3


class TestTheTwoHalvesAlone:
    APPROVED = {"rows": {"t": {"added": {"1": {"a": 1}}}}}

    def test_a_leaf_only_live_holds(self):
        now = {"rows": {"t": {"added": {"1": {"a": 1}, "2": {"a": 2}}}}}
        assert D.shape_gaps(self.APPROVED, now) == []
        assert D.listed_differences(self.APPROVED, now) == ["t +1 ~0 -0"]

    def test_an_approved_leaf_absent(self):
        now = {"rows": {"t": {"added": {}}}}
        assert D.shape_gaps(self.APPROVED, now) == [
            "/rows/t/added/1/a: approved 1, live '(absent)'"]
        assert D.listed_differences(self.APPROVED, now) == []

    def test_entries(self):
        d = {"rows": {"t": {"added": {}, "removed": {},
                            "changed": {"3": {"c": ["x", "y"]}}},
                      "u": {"added": {}, "removed": {}, "changed": {}}},
             "schema": {"added": ["table v"], "removed": [], "changed": [],
                        "sql": {"table v": "create table v (a)"}}}
        before = copy.deepcopy(d)
        assert D.entries(d) == {
            "rows": {"t": {"changed": {"3": {"c": {"before": "x", "after": "y"}}}}},
            "schema": {"added": {"table v": True}, "sql": {"table v": "create table v (a)"}}}
        assert d == before, "entries modified its input"

    def test_exact_gaps_still_compares_both_ways_and_empty_dicts(self):
        """`_leaves` is unchanged: the fresh dry run must still equal the
        approved diff exactly."""
        assert D.exact_gaps({"rows": {"t": {"added": {}}}}, {"rows": {}})
        assert D.exact_gaps({"rows": {}}, {"rows": {"t": {"added": {"1": {"a": 1}}}}})


class TestTheOtherGatesUnchanged:
    def test_a_fresh_dry_run_differing_in_one_field(self, env, capsys):
        def edited(path) -> list[int]:
            migrate_in_scope(path)
            _sql(path, "update checklist_items set instruction_text = 'edited' where id = 1")
            return [71]
        _ready(env)
        assert "differs from the approved diff in 1 field(s)" in _refusal(env, capsys, edited)

    def test_the_scope_file_changed(self, env, capsys):
        _ready(env)
        D.scope_path(env["repo"], PHASE).write_text(json.dumps({"tables": {}}))
        assert "scope file changed" in _refusal(env, capsys)

    def test_the_backup_gone(self, env, capsys):
        _ready(env)
        pathlib.Path(D._header(D.diff_path(env["repo"], PHASE).read_text())["Backup"]).unlink()
        assert "missing or no longer hashes" in _refusal(env, capsys)

    def test_a_foreign_key_break(self, env, capsys):
        _deployed(env)
        _sql(env["live"], "create table child (id integer primary key, template_id integer "
                          "references workflow_templates(id))",
             "insert into child values (1, 999)")
        assert _verify(env, capsys)[0] == 1

    def test_the_fresh_dry_run_s_gap_refuses_before_the_drift_split(self, env, capsys):
        def edited(path) -> list[int]:
            migrate_in_scope(path)
            _sql(path, "update checklist_items set instruction_text = 'edited' where id = 1")
            return [71]
        _ready(env)
        _sql(env["live"], INSIDE["checklist_added"])
        err = _refusal(env, capsys, edited)
        assert "differs from the approved diff" in err
        assert "changed since the dry run" not in err


class TestTheCallers:
    def test_verify_phase_check_8_reads_only_the_exit(self, tmp_path):
        """379's harness: 0 (listed lines and all) passes, 3 fails."""
        assert _check_8(tmp_path / "listed", 0)[0] == 0
        assert _check_8(tmp_path / "gap", 3)[0] == 1

    @staticmethod
    def _committed(env) -> None:
        (env["repo"] / "docs" / "phases" / "in_progress" / f"{PHASE}_deploy_answer.md"
         ).write_text("yes\n")
        _git(env["repo"], "add", "-A")
        _git(env["repo"], "commit", "-qm", "the live diff and the answer")

    def test_the_quartermaster_passes_a_listed_difference(self, env, capsys):
        _ready(env)
        _sql(env["live"], OUTSIDE["feed_cursor"][0])
        assert _apply(env) == 0
        self._committed(env)
        result = _verify(env, capsys)
        assert result[0] == 0
        assert Q.database_step(env["repo"], PHASE, lambda: result) == []

    def test_the_quartermaster_refuses_an_approved_change_missing(self, env, capsys):
        _deployed(env)
        self._committed(env)
        _sql(env["live"], ALTERS["approved_row_deleted"])
        result = _verify(env, capsys)
        why = Q.database_step(env["repo"], PHASE, lambda: result)
        assert any("verify-live exits 3" in w for w in why), why
