"""Phase 303 — sessions as rows of `api_keys`, and the password check
(Logic item 3; the operator's K56 requirements 2 and 4).

`created_at` is written here by SQLite's own `datetime('now', ...)`, the
shape `CURRENT_TIMESTAMP` stores, so the expiry is tested on the text the
live table really holds.
"""

from __future__ import annotations

import pytest

from motodiag.auth import passwords, sessions_repo
from motodiag.auth.api_key_repo import create_api_key, verify_api_key
from motodiag.auth.deps import resolve_credential
from motodiag.auth.sessions_repo import (
    DUMMY_HASH, SESSION_PREFIX, authenticate, create_session,
    list_user_sessions, revoke_session, revoke_user_sessions,
    session_expires_at, verify_session,
)
from motodiag.auth.users_repo import deactivate_user

from support.phase303 import (
    PASSWORD, api_keys_rows, auth, client, make_user, new_db, sql,
)


@pytest.fixture
def db(tmp_path, monkeypatch):
    return new_db(tmp_path, monkeypatch)


def _age(db, row_id, *modifiers):
    sql(db, "UPDATE api_keys SET created_at = datetime('now', "
            + ", ".join("?" for _ in modifiers) + ") WHERE id = ?",
        (*modifiers, row_id))


class TestCreate:
    def test_the_token_is_mds_and_stored_hashed(self, db):
        uid = make_user(db, "tess")
        row, token = create_session(uid, "phone", db_path=db)
        assert token.startswith(SESSION_PREFIX) and len(token) > 30
        assert row.key_prefix == token[:12] and row.kind == "session"
        assert row.name == "session:phone"
        stored = sql(db, "SELECT key_hash FROM api_keys WHERE id = ?", (row.id,))[0][0]
        assert token not in stored and len(stored) == 64

    def test_no_client_names_it_session(self, db):
        uid = make_user(db, "tess")
        assert create_session(uid, db_path=db)[0].name == "session"

    def test_a_key_is_kind_api_key(self, db):
        uid = make_user(db, "tess")
        assert create_api_key(uid, db_path=db)[0].kind == "api_key"


class TestVerify:
    def test_a_fresh_session_verifies_and_marks_last_used(self, db):
        uid = make_user(db, "tess")
        row, token = create_session(uid, db_path=db)
        got = verify_session(token, 30, db_path=db)
        assert got is not None and got.id == row.id
        assert sql(db, "SELECT last_used_at FROM api_keys WHERE id = ?", (row.id,))[0][0]

    def test_the_two_credentials_never_pass_for_each_other(self, db):
        uid = make_user(db, "tess")
        _, token = create_session(uid, db_path=db)
        _, key = create_api_key(uid, db_path=db)
        assert verify_api_key(token, db_path=db) is None
        assert verify_session(key, 30, db_path=db) is None
        assert verify_api_key(key, db_path=db) is not None

    def test_a_key_row_reached_by_a_session_prefix_is_refused(self, db):
        """A session token whose hash somehow matched a key row is refused
        by the row's own prefix, not only the token's."""
        uid = make_user(db, "tess")
        key_row, _ = create_api_key(uid, db_path=db)
        token = SESSION_PREFIX + "planted"
        sql(db, "UPDATE api_keys SET key_hash = ? WHERE id = ?",
            (sessions_repo.hash_api_key(token), key_row.id))
        assert verify_session(token, 30, db_path=db) is None

    def test_revoked_session_is_none(self, db):
        uid = make_user(db, "tess")
        row, token = create_session(uid, db_path=db)
        assert revoke_session(row.id, db_path=db)
        assert verify_session(token, 30, db_path=db) is None

    def test_a_deactivated_users_session_is_none(self, db):
        uid = make_user(db, "tess")
        _, token = create_session(uid, db_path=db)
        deactivate_user(uid, db_path=db)
        assert verify_session(token, 30, db_path=db) is None

    def test_garbage_is_none(self, db):
        assert verify_session("", 30, db_path=db) is None
        assert verify_session(None, 30, db_path=db) is None
        assert verify_session("mds_nope", 30, db_path=db) is None


class TestExpiryK56:
    """K56 requirement 4: real UTC times, never date text."""

    def test_30_days_plus_a_minute_is_expired(self, db):
        uid = make_user(db, "tess")
        row, token = create_session(uid, db_path=db)
        _age(db, row.id, "-30 days", "-1 minutes")
        assert verify_session(token, 30, db_path=db) is None

    def test_30_days_minus_a_minute_is_valid(self, db):
        uid = make_user(db, "tess")
        row, token = create_session(uid, db_path=db)
        _age(db, row.id, "-30 days", "+1 minutes")
        got = verify_session(token, 30, db_path=db)
        assert got is not None and got.id == row.id

    def test_created_at_is_sqlites_shape(self, db):
        uid = make_user(db, "tess")
        row, _ = create_session(uid, db_path=db)
        assert len(row.created_at) == 19 and row.created_at[10] == " "

    def test_expires_at_is_created_plus_the_lifetime_in_utc(self, db):
        uid = make_user(db, "tess")
        row, _ = create_session(uid, db_path=db)
        sql(db, "UPDATE api_keys SET created_at = '2026-10-01 23:30:00' WHERE id = ?", (row.id,))
        row = sessions_repo.get_session(row.id, db_path=db)
        assert session_expires_at(row, 30) == "2026-10-31T23:30:00+00:00"
        assert session_expires_at(row, 1) == "2026-10-02T23:30:00+00:00"

    def test_a_one_day_setting_expires_after_a_day(self, db, monkeypatch):
        """Logic item 10: the setting reads from the environment."""
        from motodiag.core.config import get_settings, reset_settings

        uid = make_user(db, "tess")
        row, token = create_session(uid, db_path=db)
        _age(db, row.id, "-1 days", "-1 minutes")
        assert resolve_credential(token, db_path=db) is not None  # 30 days
        monkeypatch.setenv("MOTODIAG_SESSION_LIFETIME_DAYS", "1")
        reset_settings()
        assert get_settings().session_lifetime_days == 1
        assert resolve_credential(token, db_path=db) is None
        reset_settings()


class TestRevokeAndList:
    def test_revoke_all_but_one_and_keys_untouched(self, db):
        uid = make_user(db, "tess")
        keep, keep_t = create_session(uid, db_path=db)
        _, other_t = create_session(uid, db_path=db)
        _, key = create_api_key(uid, db_path=db)
        assert revoke_user_sessions(uid, keep_session_id=keep.id, db_path=db) == 1
        assert verify_session(keep_t, 30, db_path=db) is not None
        assert verify_session(other_t, 30, db_path=db) is None
        assert verify_api_key(key, db_path=db) is not None

    def test_revoke_all(self, db):
        uid = make_user(db, "tess")
        create_session(uid, db_path=db)
        create_session(uid, db_path=db)
        assert revoke_user_sessions(uid, db_path=db) == 2
        assert list_user_sessions(uid, db_path=db) == []

    def test_list_is_confined_to_sessions(self, db):
        uid = make_user(db, "tess")
        s, _ = create_session(uid, db_path=db)
        create_api_key(uid, db_path=db)
        assert [r.id for r in list_user_sessions(uid, db_path=db)] == [s.id]

    def test_list_include_revoked(self, db):
        uid = make_user(db, "tess")
        s, _ = create_session(uid, db_path=db)
        revoke_session(s.id, db_path=db)
        assert list_user_sessions(uid, db_path=db) == []
        assert [r.id for r in list_user_sessions(uid, include_revoked=True, db_path=db)] == [s.id]

    def test_revoke_session_never_revokes_a_key(self, db):
        uid = make_user(db, "tess")
        k, key = create_api_key(uid, db_path=db)
        assert revoke_session(k.id, db_path=db) is False
        assert verify_api_key(key, db_path=db) is not None

    def test_an_underscore_in_a_key_prefix_is_not_a_session(self, db):
        """'mds_' is matched literally: in LIKE, '_' would match any byte."""
        uid = make_user(db, "tess")
        k, _ = create_api_key(uid, db_path=db)
        sql(db, "UPDATE api_keys SET key_prefix = 'mdsXlive_AbC' WHERE id = ?", (k.id,))
        assert list_user_sessions(uid, db_path=db) == []
        assert revoke_user_sessions(uid, db_path=db) == 0


class TestAuthenticate:
    def test_a_match_returns_the_user(self, db):
        uid = make_user(db, "tess")
        assert authenticate("tess", PASSWORD, db_path=db)["id"] == uid

    @pytest.mark.parametrize("case", ["unknown", "wrong", "no-password", "inactive"])
    def test_every_failure_is_the_same_none(self, db, case):
        uid = make_user(db, "tess", None if case == "no-password" else PASSWORD)
        if case == "inactive":
            deactivate_user(uid, db_path=db)
        name = "nobody" if case == "unknown" else "tess"
        password = "wrong horse" if case == "wrong" else PASSWORD
        assert authenticate(name, password, db_path=db) is None

    @pytest.fixture
    def spy(self, monkeypatch):
        calls = []
        real = sessions_repo.verify_password
        monkeypatch.setattr(sessions_repo, "verify_password",
                            lambda plain, stored: calls.append(stored) or real(plain, stored))
        return calls

    def test_k55_an_unknown_name_runs_the_check_against_the_dummy(self, db, spy):
        assert authenticate("nobody", PASSWORD, db_path=db) is None
        assert spy == [DUMMY_HASH]

    def test_k55_a_passwordless_user_runs_the_check_against_the_dummy(self, db, spy):
        make_user(db, "tess", None)
        assert authenticate("tess", PASSWORD, db_path=db) is None
        assert spy == [DUMMY_HASH]

    def test_a_wrong_password_runs_the_check_against_the_users_hash(self, db, spy):
        uid = make_user(db, "tess")
        stored = sql(db, "SELECT password_hash FROM users WHERE id = ?", (uid,))[0][0]
        assert authenticate("tess", "wrong horse", db_path=db) is None
        assert spy == [stored] and stored != DUMMY_HASH

    def test_the_control_the_dummy_runs_the_full_derivation(self, monkeypatch):
        """The dummy is well formed, so the check does not return early."""
        parts = DUMMY_HASH.split("$")
        assert parts[0] == "scrypt" and len(parts) == 6
        assert (int(parts[1]), int(parts[2]), int(parts[3])) == (
            passwords.SCRYPT_N, passwords.SCRYPT_R, passwords.SCRYPT_P)
        derived = []
        real = passwords._derive
        monkeypatch.setattr(passwords, "_derive",
                            lambda *a: derived.append(a[2:]) or real(*a))
        assert passwords.verify_password(PASSWORD, DUMMY_HASH) is False
        assert derived == [(passwords.SCRYPT_N, passwords.SCRYPT_R, passwords.SCRYPT_P)]


class TestRowForRow:
    """A request changes `last_used_at` of its own row and no other byte."""

    @staticmethod
    def _changed(db, before, after):
        cols = [r[1] for r in sql(db, "PRAGMA table_info(api_keys)")]
        return [(b[0], cols[i]) for b, a in zip(before, after)
                for i, (x, y) in enumerate(zip(b, a)) if x != y]

    def test_a_session_request_touches_only_its_own_last_used_at(self, db):
        uid = make_user(db, "tess")
        other = make_user(db, "owen")
        create_api_key(uid, db_path=db)
        create_api_key(other, db_path=db)
        mine, token = create_session(uid, db_path=db)
        create_session(uid, db_path=db)
        create_session(other, db_path=db)
        before = api_keys_rows(db)
        assert client(db).get("/v1/auth/me", headers=auth(token)).status_code == 200
        after = api_keys_rows(db)
        assert len(before) == len(after) == 5
        assert self._changed(db, before, after) == [(mine.id, "last_used_at")]

    def test_the_control_a_key_request_touches_only_the_keys_row(self, db):
        uid = make_user(db, "tess")
        krow, key = create_api_key(uid, db_path=db)
        create_session(uid, db_path=db)
        before = api_keys_rows(db)
        assert client(db).get("/v1/auth/me", headers={"X-API-Key": key}).status_code == 200
        assert self._changed(db, before, api_keys_rows(db)) == [(krow.id, "last_used_at")]
