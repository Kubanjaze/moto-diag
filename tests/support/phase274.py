"""Shared helpers for Phase 274's tests (Track O batch 1).

Every capability in the batch is reached through a `motodiag` command, so
each test drives the CLI against its own scratch database. The seeding
helpers write through the same repositories the product uses.
"""

from __future__ import annotations

import sqlite3

import pytest
from click.testing import CliRunner

from motodiag.cli.main import cli as main_cli
from motodiag.cli.theme import reset_console
from motodiag.core.config import reset_settings
from motodiag.core.database import get_connection, init_db

WIDE = 10000


def new_db(tmp_path, name: str = "phase274.db") -> str:
    path = str(tmp_path / name)
    init_db(path)
    return path


def cli(db_path: str, *args, answers=()):
    text = "".join(f"{a}\n" for a in answers)
    try:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("MOTODIAG_DB_PATH", db_path)
            mp.setenv("COLUMNS", str(WIDE))
            reset_settings()
            reset_console()
            return CliRunner().invoke(main_cli, [str(a) for a in args], input=text)
    finally:
        reset_settings()
        reset_console()


def ok(db_path: str, *args, answers=()):
    """Run a command that must succeed; return its output."""
    res = cli(db_path, *args, answers=answers)
    assert res.exit_code == 0, f"{args} exit {res.exit_code}:\n{res.output}\n{res.exception!r}"
    return res.output


def refused(db_path: str, *args, answers=()):
    """Run a command that must fail cleanly; return its output."""
    res = cli(db_path, *args, answers=answers)
    assert res.exit_code != 0, f"{args} unexpectedly passed:\n{res.output}"
    assert not isinstance(res.exception, (AssertionError, TypeError, KeyError,
                                          sqlite3.Error)), repr(res.exception)
    return res.output


def sql(db_path: str, query: str, params=()):
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(query, params).fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


def seed_shop(db_path: str, name: str = "Test Shop", state: str | None = None) -> int:
    from motodiag.shop.shop_repo import create_shop
    return create_shop(name, state=state, db_path=db_path)


def seed_user(db_path: str, username: str) -> int:
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO users (username) VALUES (?)", (username,),
        ).lastrowid


def seed_customer(db_path: str, shop_id: int, name: str, email: str | None = None) -> int:
    from motodiag.crm import customer_repo
    from motodiag.crm.models import Customer
    return customer_repo.create_customer(
        Customer(name=name, email=email, shop_id=shop_id), db_path=db_path,
    )


def seed_bike(db_path: str, make: str = "Honda", model: str = "CB500F",
              year: int = 2020, vin: str | None = None,
              mileage: int | None = None) -> int:
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO vehicles (make, model, year, vin, mileage, powertrain, "
            "engine_type) VALUES (?, ?, ?, ?, ?, 'ice', 'four_stroke')",
            (make, model, year, vin, mileage),
        ).lastrowid
