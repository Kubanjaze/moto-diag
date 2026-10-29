"""Password hashing for staff logins (Phase 303).

The stored form is one string, ``scrypt$<n>$<r>$<p>$<salt>$<hash>``, with
the salt and the hash in hex. It comes from :func:`hashlib.scrypt` in the
standard library, so the server installs nothing for it, and it carries its
own parameters, so a later change to them still verifies the hashes stored
before it.

A stored value that is null, empty or not in this form verifies false. The
seeded system user and every user created before this phase have a null
``password_hash``, so none of them can log in until a password is set.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional

SCHEME = "scrypt"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
KEY_BYTES = 32
SALT_BYTES = 16
# 128 * r * n is 16 MiB at the parameters above; twice that leaves room
# for a later raise without letting a malformed row ask for gigabytes.
MAX_MEMORY = 64 * 1024 * 1024

MIN_PASSWORD_LENGTH = 8


class PasswordTooShort(ValueError):
    """Raised when a new password is shorter than MIN_PASSWORD_LENGTH."""

    def __init__(self, length: int) -> None:
        super().__init__(
            f"password must be at least {MIN_PASSWORD_LENGTH} characters "
            f"(got {length})"
        )
        self.length = length


def _derive(plain: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        plain.encode("utf-8"), salt=salt, n=n, r=r, p=p,
        maxmem=MAX_MEMORY, dklen=KEY_BYTES,
    )


def hash_password(plain: str) -> str:
    """Hash a new password with a fresh salt. Raises PasswordTooShort."""
    if len(plain) < MIN_PASSWORD_LENGTH:
        raise PasswordTooShort(len(plain))
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(plain, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return (
        f"{SCHEME}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}$"
        f"{salt.hex()}${digest.hex()}"
    )


def verify_password(plain: str, stored: Optional[str]) -> bool:
    """True only when ``stored`` is this module's form and ``plain`` matches."""
    if not stored:
        return False
    parts = stored.split("$")
    if len(parts) != 6 or parts[0] != SCHEME:
        return False
    try:
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt = bytes.fromhex(parts[4])
        expected = bytes.fromhex(parts[5])
        digest = _derive(plain, salt, n, r, p)
    except ValueError:
        return False
    return hmac.compare_digest(digest, expected)
