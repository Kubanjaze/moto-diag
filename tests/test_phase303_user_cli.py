"""Phase 303 — `motodiag user` (Logic item 9) and the two `apikey` filters.

Each subcommand round-trips under `CliRunner` against a scratch database. A
password never reaches stdout, the log or `--json`.
"""

from __future__ import annotations

import json
import logging

import pytest
from click.testing import CliRunner

from motodiag.auth.api_key_repo import create_api_key, get_api_key_by_id
from motodiag.auth.sessions_repo import authenticate, create_session, list_user_sessions
from motodiag.cli.main import cli

from support.phase303 import PASSWORD, make_user, new_db, sql

NEW = "brand new horse"


@pytest.fixture
def db(tmp_path, monkeypatch):
    return new_db(tmp_path, monkeypatch)


def run(*args, input=None):
    return CliRunner().invoke(cli, list(args), input=input)


class TestCreate:
    def test_password_stdin(self, db, caplog):
        caplog.set_level(logging.DEBUG)
        r = run("user", "create", "--username", "tess", "--full-name", "Tess T",
                "--email", "t@ex.com", "--password-stdin", input=NEW + "\n")
        assert r.exit_code == 0, r.output
        uid = sql(db, "SELECT id FROM users WHERE username = 'tess'")[0][0]
        assert f"#{uid}" in r.output and "shop member add" in r.output
        assert NEW not in r.output and NEW not in caplog.text
        assert sql(db, "SELECT password_hash FROM users WHERE id = ?", (uid,))[0][0].startswith("scrypt$")
        assert authenticate("tess", NEW, db_path=db)["full_name"] == "Tess T"

    def test_hidden_prompt_twice(self, db):
        r = run("user", "create", "--username", "tess", "--full-name", "Tess",
                input=f"{NEW}\n{NEW}\n")
        assert r.exit_code == 0, r.output
        assert NEW not in r.output
        assert r.output.count("Password") >= 1
        assert authenticate("tess", NEW, db_path=db) is not None

    def test_a_seven_character_password_is_refused(self, db):
        r = run("user", "create", "--username", "tess", "--full-name", "Tess",
                "--password-stdin", input="1234567\n")
        assert r.exit_code != 0
        assert "at least 8" in r.output
        assert sql(db, "SELECT count(*) FROM users WHERE username = 'tess'")[0][0] == 0

    def test_a_taken_username_is_refused(self, db):
        make_user(db, "tess")
        r = run("user", "create", "--username", "tess", "--full-name", "Tess",
                "--password-stdin", input=NEW + "\n")
        assert r.exit_code != 0 and "already taken" in r.output


class TestList:
    def test_json_says_whether_a_password_is_set_never_the_hash(self, db):
        tess = make_user(db, "tess")
        make_user(db, "nopass", None)
        create_session(tess, db_path=db)
        r = run("user", "list", "--json")
        assert r.exit_code == 0, r.output
        rows = {u["username"]: u for u in json.loads(r.output)}
        assert rows["tess"]["password_set"] is True and rows["tess"]["open_sessions"] == 1
        assert rows["nopass"]["password_set"] is False
        assert "password_hash" not in r.output and "scrypt$" not in r.output

    def test_include_inactive(self, db):
        make_user(db, "gone")
        assert run("user", "deactivate", "gone").exit_code == 0
        assert "gone" not in run("user", "list", "--json").output
        assert "gone" in run("user", "list", "--include-inactive", "--json").output

    def test_the_table(self, db):
        make_user(db, "tess")
        r = run("user", "list")
        assert r.exit_code == 0 and "tess" in r.output


class TestSetPassword:
    @pytest.mark.parametrize("by", ["id", "username"])
    def test_sets_the_hash_and_ends_sessions(self, db, by):
        tess = make_user(db, "tess")
        create_session(tess, db_path=db)
        r = run("user", "set-password", str(tess) if by == "id" else "tess",
                "--password-stdin", input=NEW + "\n")
        assert r.exit_code == 0, r.output
        assert "1 session(s) ended" in r.output and NEW not in r.output
        assert list_user_sessions(tess, db_path=db) == []
        assert authenticate("tess", NEW, db_path=db) is not None
        assert authenticate("tess", PASSWORD, db_path=db) is None

    def test_an_unknown_user(self, db):
        r = run("user", "set-password", "nobody", "--password-stdin", input=NEW + "\n")
        assert r.exit_code != 0 and "no user" in r.output


class TestDeactivate:
    def test_deactivate_ends_sessions(self, db):
        tess = make_user(db, "tess")
        create_session(tess, db_path=db)
        r = run("user", "deactivate", "tess")
        assert r.exit_code == 0, r.output
        assert list_user_sessions(tess, db_path=db) == []
        assert authenticate("tess", PASSWORD, db_path=db) is None

    def test_the_system_user_is_refused(self, db):
        r = run("user", "deactivate", "1")
        assert r.exit_code != 0 and "system user" in r.output


class TestSessionsAndLogout:
    def test_sessions_lists_sessions_not_keys(self, db):
        tess = make_user(db, "tess")
        s, _ = create_session(tess, "phone", db_path=db)
        create_api_key(tess, db_path=db)
        r = run("user", "sessions", "tess", "--json")
        assert r.exit_code == 0, r.output
        items = json.loads(r.output)
        assert [(i["id"], i["client"]) for i in items] == [(s.id, "phone")]
        assert "mdk_" not in r.output
        assert "phone" in run("user", "sessions", "tess").output

    def test_logout_ends_every_session(self, db):
        tess = make_user(db, "tess")
        create_session(tess, db_path=db)
        create_session(tess, db_path=db)
        r = run("user", "logout", "tess")
        assert r.exit_code == 0 and "2 session(s) ended" in r.output
        assert "No open sessions" in run("user", "sessions", "tess").output


class TestApikeyFilters:
    def test_a_session_is_absent_from_apikey_list(self, db):
        tess = make_user(db, "tess")
        k, _ = create_api_key(tess, db_path=db)
        create_session(tess, db_path=db)
        r = run("apikey", "list", "--user", str(tess), "--json")
        assert [x["id"] for x in json.loads(r.output)] == [k.id]

    def test_apikey_show_does_not_show_a_session(self, db):
        tess = make_user(db, "tess")
        s, _ = create_session(tess, db_path=db)
        for ident in (str(s.id), s.key_prefix):
            r = run("apikey", "show", ident, "--json")
            assert r.exit_code != 0 and "no API key" in r.output

    def test_apikey_revoke_of_a_session_id_is_harmless(self, db):
        tess = make_user(db, "tess")
        k, _ = create_api_key(tess, db_path=db)
        s, _ = create_session(tess, db_path=db)
        r = run("apikey", "revoke", str(s.id))
        assert r.exit_code == 0, r.output
        assert list_user_sessions(tess, db_path=db) == []
        assert get_api_key_by_id(k.id, db_path=db).is_active
