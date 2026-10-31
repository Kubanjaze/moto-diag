"""Phase 385, F212 — the push token's own write is set aside, and only it.

The app's push registration (`POST /v1/push/register`, `push/registry.py`
`register_token`) refreshes `device_tokens.last_seen_at` on every
registration, with no user action, so 384's check 8 failed on one changed row
nothing deployed. The operator's K39: "add device_tokens.last_seen_at to the
list as its own phase", scoped to that one column. The controls, each seen
failing (`385_mutate.py`): another column of that row (the upsert's rebind of
`platform`), an added token row, and the same column name in another table.

Fixture databases through 358's deploy contract, and a fresh database at the
schema head through `support.phase303.new_db`; never live.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3

import pytest

from support.phase303 import make_user, new_db, sql
from test_phase358_deploy_contract import (  # noqa: F401  (env is a fixture)
    D, PHASE, _apply, _commit_diff, _dryrun, _git, _refusal, env,
)

TOKEN_SEEN = "2026-10-21T07:12:40.118000+00:00"
REGISTERED = "2026-10-31T09:00:00.000000+00:00"


def _sql(path, *stmts):
    c = sqlite3.connect(path)
    for s in stmts:
        c.execute(s)
    c.commit()
    c.close()


def _with_tokens(env):
    """live gains a device_tokens table of 044's six columns holding row 31,
    and a second table with a column of the same name, which the list does
    not cover."""
    _sql(env["live"],
         "create table device_tokens (id integer primary key, user_id integer, "
         "token text unique, platform text, created_at text, last_seen_at text)",
         f"insert into device_tokens values (31, 1, 'ExponentPushToken[a]', 'ios', "
         f"'2026-10-21T07:12:40Z', '{TOKEN_SEEN}')",
         "create table phones (id integer primary key, last_seen_at text)",
         f"insert into phones values (1, '{TOKEN_SEEN}')")


def _with_keys(env):
    """383's api_keys row beside it, for the run that writes both columns."""
    _sql(env["live"],
         "create table api_keys (id integer primary key, user_id integer, name text, "
         "last_used_at text, is_active integer)",
         "insert into api_keys values (2, 1, 'phone', '2026-09-16T15:30:24Z', 1)")


def _register(env):
    """What `register_token`'s upsert does when the same phone registers again."""
    _sql(env["live"], f"update device_tokens set last_seen_at = '{REGISTERED}' where id = 31")


def _request(env):
    """What `verify_api_key` does on a request (383's case)."""
    _sql(env["live"], "update api_keys set last_used_at = '2026-10-19T22:27:00Z' where id = 2")


#: The three controls: a change K39 does not cover, made beside a registration.
CONTROLS = {
    "rebind": "update device_tokens set platform = 'android' where id = 31",
    "added_row": "insert into device_tokens values (32, 1, 'ExponentPushToken[b]', 'ios', "
                 f"'{REGISTERED}', '{REGISTERED}')",
    "other_table": f"update phones set last_seen_at = '{REGISTERED}' where id = 1",
}


def _verify(env, capsys) -> tuple[int, str]:
    code = D.verify_live(PHASE, db=env["live"], repo=env["repo"])
    return code, capsys.readouterr().out


def _ready(env):
    _with_tokens(env)
    assert _dryrun(env) == 0
    _commit_diff(env)


class TestTheTokenColumnIsSetAside:
    def test_a_registration_between_the_dry_run_and_the_apply(self, env, capsys):
        _ready(env)
        _register(env)
        assert _apply(env) == 0
        live_diff = D.diff_path(env["repo"], PHASE, "live").read_text()
        assert "Equals the approved exact diff:** `yes`" in live_diff
        assert "device_tokens 31 last_seen_at" in live_diff

    def test_a_registration_after_the_apply_passes_verify_live(self, env, capsys):
        """384's case: check 8 failed on this row (F212)."""
        _ready(env)
        assert _apply(env) == 0
        _register(env)
        code, out = _verify(env, capsys)
        assert code == 0, out
        assert "set aside: 1 change(s)" in out and "device_tokens 31 last_seen_at" in out

    def test_both_listed_columns_in_one_run(self, env, capsys):
        """As 384's live showed on 2026-10-21: a request and a registration."""
        _with_keys(env)
        _ready(env)
        assert _apply(env) == 0
        _request(env)
        _register(env)
        code, out = _verify(env, capsys)
        assert code == 0, out
        assert "set aside: 2 change(s)" in out
        assert "api_keys 2 last_used_at" in out and "device_tokens 31 last_seen_at" in out


@pytest.mark.parametrize("beside", [True, False], ids=["beside", "alone"])
@pytest.mark.parametrize("control", sorted(CONTROLS))
class TestTheControlsStillFail:
    """Each control refuses the apply and fails verify-live: beside a
    registration, so the set-aside change and the control share a table, and
    alone, so a widened entry cannot hide behind the registration's own drift
    (an added row under a `WHOLE_TABLE` entry)."""

    def test_before_the_apply(self, env, capsys, control, beside):
        _ready(env)
        if beside:
            _register(env)
        _sql(env["live"], CONTROLS[control])
        assert "changed since the dry run" in _refusal(env, capsys)

    def test_after_the_apply(self, env, capsys, control, beside):
        _ready(env)
        assert _apply(env) == 0
        if beside:
            _register(env)
        _sql(env["live"], CONTROLS[control])
        code, out = _verify(env, capsys)
        assert code == 3, out


class TestAMigrationThatWritesTheColumn:
    """The dry run is not masked, and a field the approved diff names is
    compared exactly."""

    @staticmethod
    def _migrate(path) -> list[int]:
        _sql(path, "update device_tokens set last_seen_at = '2020-01-01T00:00:00Z' where id = 31",
             "insert into schema_version values (71)")
        return [71]

    def _scoped(self, env):
        _with_tokens(env)
        scope = {"tables": {
            "device_tokens": {"changed": [{"where": "id = ?", "params": [31],
                                           "fields": ["last_seen_at"]}]},
            "schema_version": {"added": 1}}}
        D.scope_path(env["repo"], PHASE).write_text(json.dumps(scope, indent=1))
        _git(env["repo"], "commit", "-qam", "a scope naming the column")
        assert _dryrun(env, self._migrate) == 0
        _commit_diff(env)

    def test_the_dry_run_shows_it(self, env):
        self._scoped(env)
        approved = D._approved_exact(D.diff_path(env["repo"], PHASE).read_text())
        assert approved["rows"]["device_tokens"]["changed"]["31"]["last_seen_at"] == [
            TOKEN_SEEN, "2020-01-01T00:00:00Z"]

    def test_a_later_registration_on_that_field_fails_verify_live(self, env, capsys):
        self._scoped(env)
        assert D.apply_live(PHASE, db=env["live"], repo=env["repo"],
                            migrate=self._migrate) == 0
        _register(env)
        code, out = _verify(env, capsys)
        assert code == 3, out


class TestTheRealRegistration:
    """On a fresh database at the schema head (never live): the real
    `register_token`, a backup taken between two registrations."""

    @pytest.fixture
    def live(self, tmp_path, monkeypatch):
        from motodiag.push import registry

        db = new_db(tmp_path, monkeypatch)
        tess = make_user(db, "tess")
        olga = make_user(db, "olga")
        registry.register_token(tess, "ExponentPushToken[t]", "ios", db_path=db)
        backup = pathlib.Path(tmp_path / "backup.db")
        D.backup(pathlib.Path(db), backup)
        monkeypatch.setattr(registry, "_now", lambda: REGISTERED)
        return db, backup, (tess, olga), registry

    @staticmethod
    def _masked(db: str, backup: pathlib.Path):
        return D.server_masked(D.diff(D.dump(backup), D.dump(pathlib.Path(db))), None)

    def test_the_same_user_registering_again_is_set_aside(self, live):
        db, backup, (tess, _), registry = live
        registry.register_token(tess,"ExponentPushToken[t]", "ios", db_path=db)
        out, aside = self._masked(db, backup)
        (row,) = sql(db, "SELECT id FROM device_tokens")
        assert out == {}
        assert aside == [f"device_tokens {row[0]} last_seen_at"]

    def test_control_another_user_registering_the_token_stays(self, live):
        """The upsert's rebind of `user_id`: not on the list (F210)."""
        db, backup, (_, olga), registry = live
        registry.register_token(olga, "ExponentPushToken[t]", "ios", db_path=db)
        out, _ = self._masked(db, backup)
        assert set(out) == {"device_tokens"}
        assert len(out["device_tokens"]["changed"]) == 1
