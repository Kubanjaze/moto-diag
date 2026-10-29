"""Shared helpers for Phase 303's tests (staff logins).

A scratch database per test, as `tests/test_phase180_shop_api.py` makes it:
`init_db` on a temp path, `MOTODIAG_DB_PATH` pointed at it, the rate limits
raised so no test trips them by accident, and `create_app(db_path_override=)`
under `TestClient`. No test reads the live database.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.auth.models import User
from motodiag.auth.passwords import hash_password
from motodiag.auth.users_repo import create_user
from motodiag.core.database import get_connection, init_db
from motodiag.shop import add_shop_member, create_shop, seed_first_owner

__all__ = ["new_db", "make_user", "make_sub", "make_shop", "add_member",
           "make_key", "client", "login", "auth", "api_keys_rows", "sql"]

PASSWORD = "correct horse"


def new_db(tmp_path, monkeypatch, *, rate_limit: str = "9999") -> str:
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase303.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("MOTODIAG_LIVE_PROVIDER", "fake")
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", rate_limit)
    reset_settings()
    return path


def sql(db_path: str, query: str, params: tuple = ()) -> list:
    with get_connection(db_path) as conn:
        return [tuple(r) for r in conn.execute(query, params).fetchall()]


def make_user(db_path: str, username: str, password: str | None = PASSWORD,
              *, full_name: str | None = None) -> int:
    return int(create_user(User(
        username=username, email=f"{username}@ex.com",
        full_name=full_name or username.title(),
        password_hash=hash_password(password) if password else None,
    ), db_path=db_path))


def make_sub(db_path: str, user_id: int, tier: str = "shop") -> None:
    sql(db_path, "INSERT INTO subscriptions (user_id, tier, status, current_period_end) "
                 "VALUES (?, ?, 'active', datetime('now', '+30 days'))", (user_id, tier))


def make_shop(db_path: str, name: str, owner_id: int) -> int:
    shop_id = create_shop(name, owner_user_id=owner_id, db_path=db_path)
    seed_first_owner(shop_id, owner_id, db_path=db_path)
    return shop_id


def add_member(db_path: str, shop_id: int, user_id: int, role: str = "tech") -> None:
    add_shop_member(shop_id, user_id, role, db_path=db_path)


def make_key(db_path: str, user_id: int) -> str:
    return create_api_key(user_id, db_path=db_path)[1]


def client(db_path: str) -> TestClient:
    return TestClient(create_app(db_path_override=db_path), raise_server_exceptions=False)


def login(c: TestClient, username: str, password: str = PASSWORD, **extra) -> str:
    r = c.post("/v1/auth/login", json={"username": username, "password": password, **extra})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def api_keys_rows(db_path: str) -> list:
    return sql(db_path, "SELECT * FROM api_keys ORDER BY id")
