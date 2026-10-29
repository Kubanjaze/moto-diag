"""Phase 303 — password hashing (Logic item 2).

scrypt from the standard library, stored as one string that carries its
parameters. Everything that is not this module's form verifies false, so a
user with no password, including the seeded system user, can never log in.
"""

from __future__ import annotations

import hashlib

import pytest

from motodiag.auth import passwords
from motodiag.auth.passwords import (
    MIN_PASSWORD_LENGTH, PasswordTooShort, hash_password, verify_password,
)
from motodiag.auth.users_repo import get_system_user
from motodiag.core.database import init_db


def test_a_password_verifies_against_its_own_hash():
    stored = hash_password("correct horse")
    assert verify_password("correct horse", stored)


def test_a_wrong_password_fails():
    assert not verify_password("correct hors", hash_password("correct horse"))


def test_two_hashes_of_one_password_differ_by_salt():
    a, b = hash_password("correct horse"), hash_password("correct horse")
    assert a != b
    assert a.split("$")[4] != b.split("$")[4]
    assert verify_password("correct horse", a) and verify_password("correct horse", b)


def test_the_stored_form_carries_its_parameters():
    scheme, n, r, p, salt, digest = hash_password("correct horse").split("$")
    assert (scheme, int(n), int(r), int(p)) == ("scrypt", 2**14, 8, 1)
    assert len(bytes.fromhex(salt)) == 16 and len(bytes.fromhex(digest)) == 32


def test_old_parameters_still_verify():
    """A hash stored under other parameters is verified with its own."""
    salt = bytes(16)
    digest = hashlib.scrypt(b"correct horse", salt=salt, n=2**12, r=8, p=1, dklen=32)
    stored = f"scrypt${2**12}$8$1${salt.hex()}${digest.hex()}"
    assert verify_password("correct horse", stored)


@pytest.mark.parametrize("stored", [
    None, "", "plaintext", "scrypt$", "bcrypt$16384$8$1$00$00",
    "scrypt$x$8$1$00$00", "scrypt$16384$8$1$zz$00",
    "$2b$12$abcdefghijklmnopqrstuuK8tE0pYH5a5hD1c9B2v9o0p1q2r3s4",
])
def test_a_null_or_foreign_hash_fails_closed(stored):
    assert verify_password("correct horse", stored) is False


def test_a_hash_asking_for_huge_memory_fails_closed():
    stored = f"scrypt${2**24}$8$1${bytes(16).hex()}${bytes(32).hex()}"
    assert verify_password("x", stored) is False


def test_the_minimum_length():
    assert MIN_PASSWORD_LENGTH == 8
    hash_password("a" * 8)
    with pytest.raises(PasswordTooShort, match="at least 8"):
        hash_password("a" * 7)


def test_the_compare_is_constant_time(monkeypatch):
    calls = []
    real = passwords.hmac.compare_digest
    monkeypatch.setattr(passwords.hmac, "compare_digest",
                        lambda a, b: calls.append(1) or real(a, b))
    stored = hash_password("correct horse")
    assert verify_password("correct horse", stored)
    assert not verify_password("wrong horse", stored)
    assert len(calls) == 2


def test_the_system_user_never_verifies(tmp_path):
    db = str(tmp_path / "sys.db")
    init_db(db)
    system = get_system_user(db)
    assert system is not None and not system["password_hash"]
    for guess in ("", "system", "password", "correct horse"):
        assert not verify_password(guess, system["password_hash"])
