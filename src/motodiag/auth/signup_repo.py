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
from datetime import datetime, timezone
from typing import Literal, Optional

from motodiag.auth.models import User
from motodiag.auth.one_time_codes import CodeRecord, Purpose, hash_code
from motodiag.auth.terms_acceptance import record_acceptance
from motodiag.auth.users_repo import create_user
from motodiag.core.database import get_connection
from motodiag.core.timestamps import utc_now

SignupStatus = Literal["pending_email", "email_verified", "completed"]
SignupTier = Literal["individual", "shop", "company"]
SIGNUP_TIERS: tuple[SignupTier, ...] = ("individual", "shop", "company")
#: The plans that make a shop. K141 opens them only after shop 10, K150
#: opens "individual" when 329 ships, so each has its own switch.
SHOP_TIERS: tuple[SignupTier, ...] = ("shop", "company")
#: The plans the website's form takes (Phase 329): the site says "talk to
#: us" for Company, so the form refuses it; the table keeps it for later.
FORM_TIERS: tuple[SignupTier, ...] = ("individual", "shop")
#: Privacy 1.3: "A sign-up not paid within 30 days is deleted."
UNPAID_KEEP_S = 30 * 86400
#: A spent or expired code is kept this long past its expiry, then deleted.
CODE_KEEP_S = 86400


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
    #: Bug fix #4: the paid or unpaid state of a sign-up's payment is
    #: Stripe's; these two say a payment was started or made.
    stripe_subscription_id: Optional[str] = None
    stripe_checkout_session_id: Optional[str] = None


def _row(row: sqlite3.Row) -> Signup:
    return Signup(
        id=int(row["id"]), email=row["email"], owner_name=row["owner_name"],
        username=row["username"], password_hash=row["password_hash"],
        shop_name=row["shop_name"], tier=row["tier"],
        terms_version=row["terms_version"], status=row["status"],
        user_id=row["user_id"], shop_id=row["shop_id"],
        stripe_subscription_id=row["stripe_subscription_id"],
        stripe_checkout_session_id=row["stripe_checkout_session_id"],
    )


def _login_has(username: str, db_path: Optional[str]) -> bool:
    """A login has this name in any case (Phase 329 bug fix #3: sign-in
    matches a name exactly, so "olga" beside an existing "Olga" would be
    two people who cannot tell their logins apart)."""
    with get_connection(db_path) as conn:
        return conn.execute("SELECT 1 FROM users WHERE lower(username) = lower(?) LIMIT 1",
                            (username,)).fetchone() is not None


def username_taken(username: str, db_path: Optional[str] = None) -> bool:
    """A login has it (in any case), or a sign-up not yet completed asks
    for it."""
    if _login_has(username, db_path):
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
    assert column in {"user_id", "shop_id", "stripe_subscription_id",
                      "stripe_checkout_session_id"}
    with get_connection(db_path) as conn:
        conn.execute(f"UPDATE signups SET {column} = ? WHERE id = ?",
                     (value, signup_id))


def discard_signup(signup_id: int, db_path: Optional[str] = None) -> None:
    """A sign-up whose address check could not be sent (bug fix #6): the
    row and its code go, so the username is free for the retry."""
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM one_time_codes WHERE subject = ?", (f"signup:{signup_id}",))
        conn.execute("DELETE FROM signups WHERE id = ? AND status = 'pending_email'",
                     (signup_id,))


def set_checkout_session(signup_id: int, session_id: str,
                         db_path: Optional[str] = None) -> None:
    """The newest Stripe checkout opened for this sign-up (bug fix #4)."""
    _set(signup_id, "stripe_checkout_session_id", session_id, db_path)


def mark_paid(signup_id: int, stripe_subscription_id: str,
              db_path: Optional[str] = None) -> None:
    """Record the subscription on a sign-up that could not be completed, so
    the 30-day purge keeps it for the operator."""
    _set(signup_id, "stripe_subscription_id", stripe_subscription_id, db_path)


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
        if _login_has(s.username, db_path):
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
    forget_form(signup_id, db_path=db_path)
    # The caller gets what the form said once more (the welcome email); the
    # row itself keeps it no longer.
    return done


def forget_form(signup_id: int, db_path: Optional[str] = None) -> None:
    """Privacy 1.3: what the form asked for is kept "until the plan is
    paid". Once the login exists (it holds its own copy, and a later reset
    changes only the login's), the sign-up keeps only its username, plan
    and the ids it made (bug fix #5)."""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE signups SET email = '', owner_name = '', password_hash = '' "
            "WHERE id = ? AND status = 'completed'", (signup_id,),
        )


# ---------------------------------------------------------------- limits and keeping


#: Domains whose mailbox ignores dots in the local part (Gmail's rule).
DOTLESS_DOMAINS = ("gmail.com", "googlemail.com")


def mailbox_key(email: str) -> str:
    """The mailbox an address reaches, for the per-address cap: lower case,
    a ``+tag`` dropped, and for Gmail the dots dropped and googlemail.com
    read as gmail.com. ``Olga.K+a@GMail.com`` and ``olgak@gmail.com`` are
    one mailbox, so they share one cap (Phase 329 bug fix #8)."""
    local, at, domain = email.strip().lower().rpartition("@")
    if not at:
        return email.strip().lower()
    local = local.split("+", 1)[0]
    if domain in DOTLESS_DOMAINS:
        local = local.replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"


def emails_sent_to(email: str, since: float, db_path: Optional[str] = None) -> int:
    """How many sign-up and reset links this address's mailbox was sent
    since ``since`` (epoch seconds): one code per email, so the codes count
    them. Every spelling of one mailbox (``mailbox_key``) counts together."""
    key = mailbox_key(email)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT c.subject, s.email AS s_email, u.email AS u_email "
            "FROM one_time_codes c "
            "LEFT JOIN signups s ON c.purpose = 'verify_email' "
            "  AND c.subject = 'signup:' || s.id "
            "LEFT JOIN users u ON c.purpose = 'reset_password' "
            "  AND c.subject = 'user:' || u.id "
            "WHERE c.issued_at >= ? "
            "AND c.purpose IN ('verify_email', 'reset_password')",
            (since,),
        ).fetchall()
    return sum(
        1 for r in rows
        if (r["s_email"] or r["u_email"])
        and mailbox_key(r["s_email"] or r["u_email"]) == key
    )


def purge_stale(now: float, db_path: Optional[str] = None) -> tuple[int, int]:
    """Delete unpaid sign-ups older than 30 days, and codes a day past their
    expiry. A sign-up with a subscription or a login is never deleted: a paid
    one that could not finish waits for the operator. Returns (sign-ups,
    codes) deleted."""
    cutoff = datetime.fromtimestamp(now - UNPAID_KEEP_S, timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S")
    with get_connection(db_path) as conn:
        gone = conn.execute(
            "SELECT id FROM signups WHERE status != 'completed' "
            "AND stripe_subscription_id IS NULL AND user_id IS NULL "
            "AND datetime(created_at) < ?", (cutoff,),
        ).fetchall()
        subjects = [f"signup:{r['id']}" for r in gone]
        conn.executemany("DELETE FROM one_time_codes WHERE subject = ?",
                         [(x,) for x in subjects])
        conn.executemany("DELETE FROM signups WHERE id = ?",
                         [(r["id"],) for r in gone])
        codes = conn.execute("DELETE FROM one_time_codes WHERE expires_at < ?",
                             (now - CODE_KEEP_S,)).rowcount
    return len(gone), int(codes)

