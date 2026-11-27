"""Self-serve sign-up's rows: the sign-ups and their one-time codes
(Phase 329 prebuild, migration 093).

A sign-up is written when the website's form arrives, with the owner's
password already hashed. Its email is checked by a one-time code
(:mod:`motodiag.auth.one_time_codes`). Only when Stripe's subscription is
paid does :func:`complete_signup` make the login and the terms acceptance,
and for a shop plan the shop and the owner's membership, so an unpaid
sign-up leaves no shop and no login (the 329 scope). An individual's
sign-up (K150) has no shop. It is safe to run again: each piece
it has made is recorded on the sign-up and not made twice.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal, Optional

from motodiag.auth.models import User
from motodiag.auth.one_time_codes import CodeRecord, Purpose, hash_code
from motodiag.auth.terms_acceptance import record_acceptance
from motodiag.auth.users_repo import create_user, get_user_by_username
from motodiag.core.database import get_connection
from motodiag.core.timestamps import utc_now

SignupStatus = Literal["pending_email", "email_verified", "completed"]
SignupTier = Literal["individual", "shop", "company"]
SIGNUP_TIERS: tuple[SignupTier, ...] = ("individual", "shop", "company")
#: The plans that make a shop. K141 opens them only after shop 10, K150
#: opens "individual" when 329 ships, so each has its own switch.
SHOP_TIERS: tuple[SignupTier, ...] = ("shop", "company")


class SignupError(Exception):
    """A sign-up that cannot be completed as it stands."""


# ---------------------------------------------------------------- the codes


def store_code(record: CodeRecord, db_path: Optional[str] = None) -> int:
    """Store a new code; any older unused code for the same purpose and
    subject is spent, so only the newest email's link works."""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE one_time_codes SET used_at = ? "
            "WHERE purpose = ? AND subject = ? AND used_at IS NULL",
            (record.issued_at, record.purpose, record.subject),
        )
        cur = conn.execute(
            "INSERT INTO one_time_codes "
            "(purpose, subject, code_hash, issued_at, expires_at, used_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (record.purpose, record.subject, record.code_hash,
             record.issued_at, record.expires_at, record.used_at),
        )
        return int(cur.lastrowid or 0)


def find_code(code: str, db_path: Optional[str] = None) -> Optional[CodeRecord]:
    """The record a plaintext code names, or None."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT purpose, subject, code_hash, issued_at, expires_at, used_at "
            "FROM one_time_codes WHERE code_hash = ?",
            (hash_code(code or ""),),
        ).fetchone()
    if row is None:
        return None
    purpose: Purpose = row["purpose"]
    return CodeRecord(purpose=purpose, subject=row["subject"],
                      code_hash=row["code_hash"], issued_at=row["issued_at"],
                      expires_at=row["expires_at"], used_at=row["used_at"])


def mark_code_used(record: CodeRecord, db_path: Optional[str] = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE one_time_codes SET used_at = ? WHERE code_hash = ?",
            (record.used_at, record.code_hash),
        )


# ---------------------------------------------------------------- the sign-ups


@dataclass(frozen=True)
class Signup:
    id: int
    email: str
    owner_name: str
    username: str
    password_hash: str
    shop_name: Optional[str]
    tier: SignupTier
    terms_version: str
    status: SignupStatus
    user_id: Optional[int]
    shop_id: Optional[int]


def _row(row: sqlite3.Row) -> Signup:
    return Signup(
        id=int(row["id"]), email=row["email"], owner_name=row["owner_name"],
        username=row["username"], password_hash=row["password_hash"],
        shop_name=row["shop_name"], tier=row["tier"],
        terms_version=row["terms_version"], status=row["status"],
        user_id=row["user_id"], shop_id=row["shop_id"],
    )


def username_taken(username: str, db_path: Optional[str] = None) -> bool:
    """A login has it, or a sign-up not yet completed asks for it."""
    if get_user_by_username(username, db_path=db_path) is not None:
        return True
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM signups WHERE lower(username) = lower(?) "
            "AND status != 'completed' LIMIT 1", (username,),
        ).fetchone()
    return row is not None


def create_signup(
    *, email: str, owner_name: str, username: str, password_hash: str,
    shop_name: Optional[str], tier: SignupTier, terms_version: str,
    db_path: Optional[str] = None,
) -> int:
    if tier not in SIGNUP_TIERS:
        raise SignupError(f"tier must be one of {SIGNUP_TIERS}")
    if (tier in SHOP_TIERS) != bool(shop_name):
        raise SignupError("a shop plan needs a shop name, and an individual has none")
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO signups (email, owner_name, username, password_hash, "
            "shop_name, tier, terms_version, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (email, owner_name, username, password_hash, shop_name, tier,
             terms_version, utc_now()),
        )
        return int(cur.lastrowid or 0)


def get_signup(signup_id: int, db_path: Optional[str] = None) -> Optional[Signup]:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM signups WHERE id = ?",
                           (signup_id,)).fetchone()
    return _row(row) if row else None


def mark_verified(signup_id: int, db_path: Optional[str] = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE signups SET status = 'email_verified', verified_at = ? "
            "WHERE id = ? AND status = 'pending_email'",
            (utc_now(), signup_id),
        )


def _set(signup_id: int, column: str, value, db_path: Optional[str]) -> None:
    assert column in {"user_id", "shop_id", "stripe_subscription_id"}
    with get_connection(db_path) as conn:
        conn.execute(f"UPDATE signups SET {column} = ? WHERE id = ?",
                     (value, signup_id))


def complete_signup(
    signup_id: int, stripe_subscription_id: str, db_path: Optional[str] = None,
) -> Signup:
    """Make the login and the terms acceptance, and for a shop plan the
    shop and the owner's membership, for a paid sign-up, and mark it
    completed. Returns the
    sign-up as it now stands."""
    from motodiag.shop import create_shop, seed_first_owner

    s = get_signup(signup_id, db_path)
    if s is None:
        raise SignupError(f"no sign-up {signup_id}")
    if s.status == "pending_email":
        raise SignupError(f"sign-up {signup_id} was paid before its email was checked")
    if s.status == "completed":
        return s
    user_id = s.user_id
    if user_id is None:
        if get_user_by_username(s.username, db_path=db_path) is not None:
            raise SignupError(
                f"sign-up {signup_id}: the username {s.username!r} was taken "
                "after the form; the operator picks another by hand")
        user_id = int(create_user(User(
            username=s.username, email=s.email, full_name=s.owner_name,
            password_hash=s.password_hash, tier=s.tier,
        ), db_path=db_path))
        _set(signup_id, "user_id", user_id, db_path)
    if s.tier in SHOP_TIERS:
        assert s.shop_name  # the table's CHECK holds it
        shop_id = s.shop_id
        if shop_id is None:
            shop_id = int(create_shop(s.shop_name, owner_user_id=user_id,
                                      email=s.email, db_path=db_path))
            _set(signup_id, "shop_id", shop_id, db_path)
        seed_first_owner(shop_id, user_id, db_path=db_path)
    record_acceptance(user_id, s.terms_version, db_path=db_path)
    _set(signup_id, "stripe_subscription_id", stripe_subscription_id, db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE signups SET status = 'completed', completed_at = ? WHERE id = ?",
            (utc_now(), signup_id),
        )
    done = get_signup(signup_id, db_path)
    assert done is not None
    return done
