"""Phase 383, F208 — the live gates hold on a live the API is writing.

The API writes `api_keys.last_used_at` on every authenticated request. One
request between the dry run and the apply made apply-live refuse ("it
changed since the dry run"); one after it made verify-live exit 3, which
failed 382's verify_phase check 8. The operator's 2A, with apply-live
following it: `deploy.SERVER_WRITES` names the columns the running API
writes, and every comparison of live with a backup sets aside a change
confined to them. The controls: any other change still refuses and still
fails, and the dry runs (on copies no server writes) do not mask.

Fixture databases only, through 358's deploy contract.
"""

from __future__ import annotations

import json
import sqlite3

from test_phase358_deploy_contract import (  # noqa: F401  (env is a fixture)
    D, PHASE, SCOPE, _apply, _commit_diff, _dryrun, _git, _refusal, env,
)


def _sql(path, *stmts):
    c = sqlite3.connect(path)
    for s in stmts:
        c.execute(s)
    c.commit()
    c.close()


def _with_keys(env):
    """live gains an api_keys row and a second table with a column of the
    same name, which the list does not cover."""
    _sql(env["live"],
         "create table api_keys (id integer primary key, user_id integer, name text, "
         "last_used_at text, is_active integer)",
         "insert into api_keys values (2, 1, 'phone', '2026-09-16T15:30:24Z', 1)",
         "create table devices (id integer primary key, last_used_at text)",
         "insert into devices values (1, '2026-09-16T15:30:24Z')")


def _request(env):
    """What `verify_api_key` does on a request (382's id 2, M6)."""
    _sql(env["live"], "update api_keys set last_used_at = '2026-10-19T22:27:00Z' where id = 2")


def _verify(env, capsys) -> tuple[int, str]:
    code = D.verify_live(PHASE, db=env["live"], repo=env["repo"])
    return code, capsys.readouterr().out


def _ready(env):
    _with_keys(env)
    assert _dryrun(env) == 0
    _commit_diff(env)


class TestTheListedColumnIsSetAside:
    def test_a_request_between_the_dry_run_and_the_apply(self, env, capsys):
        _ready(env)
        _request(env)
        assert _apply(env) == 0
        live_diff = D.diff_path(env["repo"], PHASE, "live").read_text()
        assert "Equals the approved exact diff:** `yes`" in live_diff
        assert "api_keys 2 last_used_at" in live_diff

    def test_a_request_after_the_apply_passes_verify_live(self, env, capsys):
        """382's case: verify-live exited 3 on this row."""
        _ready(env)
        assert _apply(env) == 0
        _request(env)
        code, out = _verify(env, capsys)
        assert code == 0, out
        assert "set aside: 1 change(s)" in out and "api_keys 2 last_used_at" in out

    def test_a_row_with_another_change_keeps_it_without_the_listed_field(self):
        cols = ["id", "name", "last_used_at"]
        d = {"api_keys": {"cols": cols, "added": [], "removed": [], "changed": [2],
                          "a": {2: (2, 2, "phone", "t0")}, "b": {2: (2, 2, "tablet", "t1")}}}
        out, aside = D.server_masked(d, None)
        assert out["api_keys"]["changed"] == [2]
        assert out["api_keys"]["b"][2] == (2, 2, "tablet", "t0")
        assert aside == ["api_keys 2 last_used_at"]


class TestTheControlsStillFail:
    """A change outside the list refuses the apply and fails verify-live."""

    def test_another_column_of_the_row_before_the_apply(self, env, capsys):
        _ready(env)
        _request(env)
        _sql(env["live"], "update api_keys set name = 'renamed' where id = 2")
        assert "changed since the dry run" in _refusal(env, capsys)

    def test_an_added_api_keys_row_before_the_apply(self, env, capsys):
        """Beside a request, so the masked change and the added row share a table."""
        _ready(env)
        _request(env)
        _sql(env["live"], "insert into api_keys values (3, 1, 'new', null, 1)")
        assert "changed since the dry run" in _refusal(env, capsys)

    def test_the_same_column_name_in_another_table_before_the_apply(self, env, capsys):
        _ready(env)
        _sql(env["live"], "update devices set last_used_at = '2026-10-19T22:27:00Z'")
        assert "changed since the dry run" in _refusal(env, capsys)

    def test_another_column_after_the_apply(self, env, capsys):
        _ready(env)
        assert _apply(env) == 0
        _request(env)
        _sql(env["live"], "update api_keys set is_active = 0 where id = 2")
        code, out = _verify(env, capsys)
        assert code == 3, out

    def test_another_table_after_the_apply(self, env, capsys):
        _ready(env)
        assert _apply(env) == 0
        _sql(env["live"], "update devices set last_used_at = '2026-10-19T22:27:00Z'")
        code, out = _verify(env, capsys)
        assert code == 3, out


class TestAMigrationThatWritesTheColumn:
    """The dry run is not masked, and a field the approved diff names is
    compared exactly."""

    @staticmethod
    def _migrate(path) -> list[int]:
        _sql(path, "update api_keys set last_used_at = '2020-01-01T00:00:00Z' where id = 2",
             "insert into schema_version values (71)")
        return [71]

    def _scoped(self, env):
        _with_keys(env)
        scope = {"tables": {
            "api_keys": {"changed": [{"where": "id = ?", "params": [2],
                                      "fields": ["last_used_at"]}]},
            "schema_version": {"added": 1}}}
        D.scope_path(env["repo"], PHASE).write_text(json.dumps(scope, indent=1))
        _git(env["repo"], "commit", "-qam", "a scope naming the column")
        assert _dryrun(env, self._migrate) == 0
        _commit_diff(env)

    def test_the_dry_run_shows_it(self, env):
        self._scoped(env)
        approved = D._approved_exact(D.diff_path(env["repo"], PHASE).read_text())
        assert approved["rows"]["api_keys"]["changed"]["2"]["last_used_at"] == [
            "2026-09-16T15:30:24Z", "2020-01-01T00:00:00Z"]

    def test_a_later_request_on_that_field_fails_verify_live(self, env, capsys):
        self._scoped(env)
        assert D.apply_live(PHASE, db=env["live"], repo=env["repo"],
                            migrate=self._migrate) == 0
        _request(env)
        code, out = _verify(env, capsys)
        assert code == 3, out


def test_the_list_is_exactly_this():
    """A column joins the list by a phase that measured the API writing it."""
    assert D.SERVER_WRITES == {"api_keys": frozenset({"last_used_at"})}
    assert SCOPE["tables"].keys().isdisjoint(D.SERVER_WRITES)
