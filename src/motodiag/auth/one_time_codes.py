"""One-time codes for an email link (Phase 329 prebuild).

Self-serve sign-up proves an email address, and a forgotten password is
reset, by a link that carries a one-time code (the 329 scope: "the check by
a link with a one-time code that expires", and "a password reset by email,
under the same one-time code rules"). This module is the code itself, with
no storage and no routes: 329's Step 0 decides the table and the routes.

The rules:

- a code is 32 random bytes, url-safe (43 characters); only its sha256 is
  kept, as an API key's is (``api_key_repo.hash_api_key``);
- a code is for one purpose and one subject (a user id or an email), and
  checking it for another is refused;
- it expires: 24 hours for an address check, 1 hour for a password reset;
- it works once; a used code is refused;
- a new code for the same purpose and subject makes the older ones void,
  which the caller does by keeping only the newest record;
- the check compares in constant time, and says why it refused, so the
  route can answer one message for every refusal and log the reason.

The clock is passed in (``now``, epoch seconds), so tests need no frozen
clock and the module has no private time helper.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, replace
from typing import Literal, get_args

Purpose = Literal["verify_email", "reset_password"]
PURPOSES: tuple[Purpose, ...] = get_args(Purpose)

Outcome = Literal["ok", "wrong_code", "wrong_purpose", "wrong_subject",
                  "expired", "used"]

CODE_NBYTES = 32
LIFETIME_S: dict[Purpose, int] = {
    "verify_email": 24 * 60 * 60,
    "reset_password": 60 * 60,
}


@dataclass(frozen=True)
class CodeRecord:
    """What is stored for a code: never the code itself."""

    purpose: Purpose
    subject: str
    code_hash: str
    issued_at: float
    expires_at: float
    used_at: float | None = None


@dataclass(frozen=True)
class IssuedCode:
    """The plaintext, shown once (it goes into the email's link), and the
    record to store."""

    code: str
    record: CodeRecord


#: Phase 329 bug fix #2: every code starts with this, so the server's log
#: filter and the crash reports' scrubber mask it wherever a link is logged
#: (``motodiag.cli.serve.SESSION_TOKEN_RE``).
CODE_PREFIX = "mdc_"


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def issue_code(purpose: Purpose, subject: str, *, now: float) -> IssuedCode:
    """A fresh code for ``purpose`` and ``subject``, valid from ``now``."""
    if purpose not in PURPOSES:
        raise ValueError(f"purpose must be one of {PURPOSES}, got {purpose!r}")
    if not subject:
        raise ValueError("a code needs a subject")
    code = CODE_PREFIX + secrets.token_urlsafe(CODE_NBYTES)
    return IssuedCode(code, CodeRecord(
        purpose=purpose, subject=subject, code_hash=hash_code(code),
        issued_at=now, expires_at=now + LIFETIME_S[purpose],
    ))


@dataclass(frozen=True)
class CodeCheck:
    outcome: Outcome
    #: The record to store after the check: marked used on "ok", else as it was.
    record: CodeRecord

    @property
    def ok(self) -> bool:
        return self.outcome == "ok"


def check_code(
    record: CodeRecord, code: str, *,
    purpose: Purpose, subject: str, now: float,
) -> CodeCheck:
    """Check ``code`` against ``record``. The code is compared first, so a
    wrong code says nothing about the record's purpose, subject or age."""
    if not hmac.compare_digest(hash_code(code or ""), record.code_hash):
        return CodeCheck("wrong_code", record)
    if record.purpose != purpose:
        return CodeCheck("wrong_purpose", record)
    if record.subject != subject:
        return CodeCheck("wrong_subject", record)
    if record.used_at is not None:
        return CodeCheck("used", record)
    if now >= record.expires_at:
        return CodeCheck("expired", record)
    return CodeCheck("ok", replace(record, used_at=now))
