"""Phase 392, F227, bug fix #1: `init_db` closes the connection it opens.

`with sqlite3.connect(path) as conn:` commits or rolls back on leaving the
block, and never closes the connection. Each `init_db` (every CLI command
runs one) left a connection, with its `.db`, `-wal` and `-shm` handles, for
the garbage collector. In the fleet's fence one xdist worker ended the
full suite holding 919 open files, almost all of them these (392's probe),
against the service's old limit of 1024. Every connection `init_db` makes
must be closed when it returns.
"""
from __future__ import annotations

import gc
import sqlite3
import weakref

import motodiag.core.database as database


def test_every_connection_init_db_makes_is_closed(tmp_path, monkeypatch):
    made: list[weakref.ref] = []
    real = sqlite3.connect

    class Tracked(sqlite3.Connection):
        pass

    def connect(*a, **k):
        k.setdefault("factory", Tracked)
        c = real(*a, **k)
        made.append(weakref.ref(c))
        return c

    monkeypatch.setattr(sqlite3, "connect", connect)
    gc.disable()                          # a leaked one must not be collected first
    try:
        database.init_db(str(tmp_path / "t.db"))
        alive = [r() for r in made if r() is not None]
        still_open = []
        for c in alive:
            try:
                c.execute("select 1")
                still_open.append(c)
            except sqlite3.ProgrammingError:
                pass                      # closed
    finally:
        gc.enable()
    assert made, "control: init_db made no connection through sqlite3.connect"
    assert still_open == [], f"{len(still_open)} of {len(made)} connections left open"
