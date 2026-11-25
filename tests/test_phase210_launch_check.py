"""Phase 210: ``motodiag launch check``, against stand-ins only.

Every case builds its own stand-in: a database made with ``init_db`` on a
temporary path, the server's settings in the environment, a backup log
written by ``take_snapshot`` itself, and a server on a loopback port that
answers ``/healthz`` and ``/v1/terms``. No test reads the live database
(244H), and the check is a command that is run, never a test of live.

The passing stand-in prints eight ``ready:`` lines and ALL GOOD; each case
breaks one condition and holds the other seven ready.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import socket
import sqlite3
import threading
import time
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from click.testing import CliRunner
from support.phase345 import FAKE_VALUES, MemoryStore, cheap_crypto, write_env
from support.phase371 import DSN_TEXT, PLANTED_DSN_KEY
from support.stripe_fixtures import LIVE_KEY_PLANTED, TEST_KEY, TEST_SECRET

from motodiag.backup.settings import BackupSettings
from motodiag.backup.snapshot import take_snapshot
from motodiag.cli.main import cli
from motodiag.cli.payments import _status_problems
from motodiag.core.config import get_settings, reset_settings
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.core.timestamps import utc_at
from motodiag.launch import check
from motodiag.manuals.review import grant_reviewer
from motodiag.payments import event_feed
from motodiag.shop import create_shop
from motodiag.shop.shop_repo import deactivate_shop

REPO = Path(__file__).resolve().parent.parent
DISPATCHER = REPO / ".claude" / "skills" / "fleet" / "dispatcher.py"
PASSPHRASE_PLANTED = FAKE_VALUES["MOTODIAG_BACKUP_PASSPHRASE"]

NAMES = (
    "the database's schema is at the code's version",
    "the server is in prod, with Stripe live and the real prices",
    "the payments feed and Sentry's alarm are checking in",
    "last night's backup",
    "the terms switch is on, at version 1.1",
    "a manual reviewer is set",
    "the test shop is inactive",
    "the free disk is above the 50 GB floor",
)

Usage = namedtuple("Usage", "total used free")


# ---------------------------------------------------------------- the server
class _Answers(BaseHTTPRequestHandler):
    version = "1.1"

    def do_GET(self):  # noqa: N802 (the stdlib's name)
        body = {"/healthz": {"status": "ok", "schema_version": SCHEMA_VERSION},
                "/v1/terms": {"version": self.version, "date": "2026-11-23"}}.get(self.path)
        data = json.dumps(body or {}).encode()
        self.send_response(200 if body else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Answers)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _closed_port() -> str:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return f"http://127.0.0.1:{port}"


# ---------------------------------------------------------------- the stand-in
def _iso(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


class _Refusing(MemoryStore):
    def put(self, key, path, sha256):
        raise OSError("the store refused the upload")


def _snapshot(world, hours_ago: float, *, fail: bool = False) -> None:
    settings = BackupSettings(world.backup_env, *FAKE_VALUES.values())
    store = _Refusing() if fail else MemoryStore()
    try:
        take_snapshot(Path(world.db), world.data, settings, store, world.work,
                      lambda: _iso(hours_ago), label="nightly")
    except OSError:
        assert fail


@pytest.fixture(scope="module")
def template(tmp_path_factory) -> Path:
    """The stand-in's rows that do not depend on the clock, made once: the
    schema, an empty bulletins table (F292's control), shop 1 inactive, and
    one reviewer. Each case copies it."""
    path = tmp_path_factory.mktemp("phase210_template") / "standin.db"
    init_db(str(path))
    with get_connection(str(path)) as conn:
        conn.execute("DELETE FROM technical_service_bulletins")
        uid = conn.execute("INSERT INTO users (username) VALUES ('operator')").lastrowid
    assert create_shop("Mekno smoke test", db_path=str(path)) == 1
    deactivate_shop(1, db_path=str(path))
    grant_reviewer(int(uid), db_path=str(path))
    return path


class World:
    def __init__(self, tmp_path: Path, monkeypatch, server_url: str, template: Path) -> None:
        self.tmp, self.mp = tmp_path, monkeypatch
        self.db = str(tmp_path / "standin.db")
        shutil.copyfile(template, self.db)
        self.data = tmp_path / "data"
        self.data.mkdir()
        self.work = tmp_path / "work"
        self.work.mkdir(mode=0o700)
        self.backup_env = write_env(tmp_path / "backup.env")
        now = time.time()
        event_feed.write_cursor(self.db, "platform", last_created=int(now),
                                last_event_id=None, polled_at=utc_at(now),
                                last_error=None, livemode=1)
        self.checkin(ok=1)
        cheap_crypto(monkeypatch)
        _snapshot(self, 4)
        self.env = {
            "MOTODIAG_DB_PATH": self.db,
            "MOTODIAG_ENV": "prod",
            "MOTODIAG_BILLING_PROVIDER": "stripe",
            "MOTODIAG_STRIPE_API_KEY": LIVE_KEY_PLANTED,
            "MOTODIAG_STRIPE_WEBHOOK_SECRET": TEST_SECRET,
            "MOTODIAG_STRIPE_PRICE_INDIVIDUAL": "price_live_individual",
            "MOTODIAG_STRIPE_PRICE_SHOP": "price_live_shop",
            "MOTODIAG_STRIPE_PRICE_COMPANY": "price_live_company",
            "MOTODIAG_STRIPE_PRICES_ARE_PLACEHOLDERS": "false",
            "MOTODIAG_SHARE_LINKS_ENABLED": "false",
            "MOTODIAG_TERMS_REQUIRED": "true",
            "MOTODIAG_SENTRY_DSN": DSN_TEXT,
            "MOTODIAG_BACKUP_WORK_DIR": str(self.work),
            "MOTODIAG_BACKUP_ENV": str(self.backup_env),
        }
        self.free_gb = {"db": 120.0, "c": 80.0}
        monkeypatch.setattr(check, "SERVER_URL", server_url)
        monkeypatch.setattr(check.shutil, "disk_usage", self._usage)
        real_ismount = os.path.ismount
        monkeypatch.setattr(check.os.path, "ismount",
                            lambda p: True if Path(p) == check.WINDOWS_DISK else real_ismount(p))

    def _usage(self, path):
        gb = self.free_gb["c" if Path(path) == check.WINDOWS_DISK else "db"]
        return Usage(1000 * 10**9, 0, int(gb * 10**9))

    def sql(self, query: str, params: tuple = ()):
        with get_connection(self.db) as conn:
            cur = conn.execute(query, params)
            return cur.lastrowid if query.lstrip().upper().startswith("INSERT") else cur.fetchall()

    def checkin(self, ok: int) -> None:
        self.sql("INSERT INTO stripe_feed_checkins (sent_at, ok, answer, slug) "
                 "VALUES (?, ?, ?, 'motodiag-payments-feed')",
                 (utc_at(time.time()), ok, "accepted" if ok else "rate limited"))

    def run(self, *args: str):
        with pytest.MonkeyPatch.context() as mp:
            for k, v in self.env.items():
                mp.setenv(k, v)
            reset_settings()
            try:
                return CliRunner().invoke(cli, ["launch", "check", *args])
            finally:
                self.read_settings = get_settings()
                reset_settings()


@pytest.fixture
def world(tmp_path, monkeypatch, server, template):
    for k in list(os.environ):
        if k.startswith("MOTODIAG_") and k not in ("MOTODIAG_DB_PATH", "MOTODIAG_TEST_DEFAULT_DB"):
            monkeypatch.delenv(k, raising=False)
    w = World(tmp_path, monkeypatch, server, template)
    yield w
    reset_settings()


def _lines(out) -> list[str]:
    return out.output.splitlines()


# ---------------------------------------------------------------- the passing stand-in
def test_the_ready_stand_in_prints_eight_ready_lines_and_all_good(world):
    out = world.run()
    assert out.exit_code == 0, out.output
    lines = _lines(out)
    assert [line.split(" (")[0] for line in lines[:8]] == [f"ready: {n}" for n in NAMES]
    assert lines[8:] == ["ALL GOOD"]
    assert ("ready: the server is in prod, with Stripe live and the real prices "
            "(env=prod, provider=stripe, key=live, prices=3, placeholders=no, "
            "share links=off)") in lines
    assert "ready: the terms switch is on, at version 1.1 (switch=on, version=1.1, " \
           "server=1.1, healthy)" in lines
    assert "ready: a manual reviewer is set (1 reviewer)" in lines
    assert re.search(r"database's disk 120\.0 GB free, C: 80\.0 GB free", out.output)
    assert re.search(r"last night's backup \(taken \S+, 4\.0 hours ago\)", out.output)


def test_the_backup_line_is_read_as_take_snapshot_writes_it(world, monkeypatch):
    last = json.loads((world.work / "runs.log").read_text().splitlines()[-1])
    assert last["outcome"] == "ok" and last["label"] == "nightly"
    monkeypatch.setenv("MOTODIAG_BACKUP_WORK_DIR", str(world.work))
    assert check.backup_condition(time.time()).ready


# ---------------------------------------------------------------- each broken alone
def _schema_behind(w):
    w.sql("DELETE FROM schema_version WHERE version = ?", (SCHEMA_VERSION,))


def _env(**changes):
    def apply(w):
        w.env.update(changes)
    return apply


def _no_cursor(w):
    w.sql("DELETE FROM stripe_event_cursors")


def _refused_checkin(w):
    w.checkin(ok=0)


def _no_runs_line(w):
    (w.work / "runs.log").write_text("")


def _failed_backup(w):
    _snapshot(w, 1, fail=True)


def _old_backup(w):
    _snapshot(w, 26)


def _terms_1_0(w):
    w.mp.setattr(check.terms_acceptance, "TERMS_VERSION", "1.0")


def _server_down(w):
    w.mp.setattr(check, "SERVER_URL", _closed_port())


def _no_reviewer(w):
    w.sql("DELETE FROM manual_reviewers")


def _shop_active(w):
    w.sql("UPDATE shops SET is_active = 1 WHERE id = 1")


def _no_shop_1(w):
    w.sql("DELETE FROM shops WHERE id = 1")


def _low_disk(w):
    w.free_gb["c"] = 49.9


BREAKS = {
    "schema one behind": (_schema_behind, 0, f"the database is at {SCHEMA_VERSION - 1} "
                                             f"and the code at {SCHEMA_VERSION}"),
    "env dev": (_env(MOTODIAG_ENV="dev"), 1, "wrong: env=dev"),
    "provider fake": (_env(MOTODIAG_BILLING_PROVIDER="fake"), 1, "wrong: provider=not stripe"),
    "a test key": (_env(MOTODIAG_STRIPE_API_KEY=TEST_KEY), 1, "wrong: key=test"),
    "two prices": (_env(MOTODIAG_STRIPE_PRICE_COMPANY=""), 1, "wrong: prices=2"),
    "placeholders": (_env(MOTODIAG_STRIPE_PRICES_ARE_PLACEHOLDERS="true"), 1,
                     "wrong: placeholders=yes"),
    "share links on": (_env(MOTODIAG_SHARE_LINKS_ENABLED="true"), 1, "wrong: share links=on"),
    "the feed never asked": (_no_cursor, 2, "platform has never been asked"),
    "the last check-in refused": (_refused_checkin, 2,
                                  "the last check-in was refused: rate limited"),
    "no DSN": (_env(MOTODIAG_SENTRY_DSN=""), 2, "the alarm is off: no Sentry DSN"),
    "no runs.log line": (_no_runs_line, 3, "no backup has run: runs.log has no line"),
    "a failed last line": (_failed_backup, 3, "the last backup failed"),
    "a line 26 hours old": (_old_backup, 3, "the last backup is more than 25 hours old"),
    "the switch off": (_env(MOTODIAG_TERMS_REQUIRED="false"), 4,
                       "the switch is off (MOTODIAG_TERMS_REQUIRED is not true)"),
    "terms 1.0": (_terms_1_0, 4, "the code's terms are version 1.0, not 1.1"),
    "the server down": (_server_down, 4, "the server did not answer on loopback"),
    "no reviewer": (_no_reviewer, 5, "no one is a manual reviewer"),
    "shop 1 active": (_shop_active, 6, "the test shop (id 1) is still active"),
    "no shop 1": (_no_shop_1, 6, "there is no shop 1: this is not live's database"),
    "under 50 GB": (_low_disk, 7, "under the floor: the database's disk 120.0 GB free, "
                                  "C: 49.9 GB free"),
}


@pytest.mark.parametrize("case", list(BREAKS), ids=[k.replace(" ", "_") for k in BREAKS])
def test_each_condition_broken_alone_is_the_one_not_ready(world, case):
    breaks, index, reason = BREAKS[case]
    breaks(world)
    out = world.run()
    assert out.exit_code == 1, out.output
    lines = _lines(out)
    assert lines[-1] == "SOMETHING IS OFF"
    assert lines[index].startswith(f"NOT READY: {NAMES[index]}: "), lines[index]
    assert reason in lines[index], lines[index]
    others = [line for i, line in enumerate(lines[:8]) if i != index]
    assert all(line.startswith("ready: ") for line in others), out.output


def test_no_dsn_is_the_checks_own_refusal_not_the_commands(world):
    """The control: on the same stand-in with no DSN, ``payments feed
    status``'s rules find nothing; the launch check's own test refuses."""
    world.env["MOTODIAG_SENTRY_DSN"] = ""
    settings = get_settings().model_copy(update={"sentry_dsn": "", "stripe_api_key":
                                                 LIVE_KEY_PLANTED})
    assert _status_problems(settings, world.db, event_feed.cursor_rows(world.db),
                            time.time()) == []
    assert not check.feed_condition(settings, world.db, time.time()).ready


# ---------------------------------------------------------------- what it never does
def test_it_never_calls_init_db(world, monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("the launch check called init_db")

    import motodiag.cli.payments as cli_payments
    import motodiag.core.database as database
    monkeypatch.setattr(database, "init_db", refuse)
    monkeypatch.setattr(cli_payments, "init_db", refuse)
    out = world.run()
    assert out.exit_code == 0, out.output


def test_the_empty_bulletins_table_stays_empty(world):
    """F292's control: ``init_db`` would load the bulletins into it."""
    assert world.sql("SELECT COUNT(*) FROM technical_service_bulletins")[0][0] == 0
    assert world.run().exit_code == 0
    assert world.sql("SELECT COUNT(*) FROM technical_service_bulletins")[0][0] == 0


def test_it_writes_nothing_to_the_database(world):
    watcher = sqlite3.connect(f"file:{world.db}?mode=ro", uri=True)
    try:
        before = (watcher.execute("PRAGMA data_version").fetchone()[0],
                  Path(world.db).read_bytes())
        assert world.run().exit_code == 0
        after = (watcher.execute("PRAGMA data_version").fetchone()[0],
                 Path(world.db).read_bytes())
    finally:
        watcher.close()
    assert before == after


def test_no_planted_key_dsn_or_passphrase_in_the_output(world):
    out = world.run()
    assert out.exit_code == 0, out.output
    assert world.read_settings.stripe_api_key == LIVE_KEY_PLANTED  # the control
    assert world.read_settings.sentry_dsn == DSN_TEXT
    assert PASSPHRASE_PLANTED in world.backup_env.read_text()
    for planted in (LIVE_KEY_PLANTED, PLANTED_DSN_KEY, DSN_TEXT, PASSPHRASE_PLANTED,
                    TEST_SECRET, "sk_live_"):
        assert planted not in out.output


def test_it_reads_only_a_loopback_server():
    with pytest.raises(check.NotLoopback):
        check.loopback_json("http://203.0.113.7/healthz")
    with pytest.raises(check.NotLoopback):
        check.terms_condition(get_settings().model_copy(update={"terms_required": True}),
                              "http://example.com")


def test_a_database_that_cannot_be_opened_is_exit_2(world, tmp_path):
    out = world.run("--db", str(tmp_path / "missing.db"))
    assert out.exit_code == 2, out.output
    assert "The database cannot be opened" in out.output
    assert _lines(out)[-1] == "SOMETHING IS OFF"
    assert not (tmp_path / "missing.db").exists()


def test_db_option_reads_the_named_database(world, tmp_path):
    other = tmp_path / "other.db"
    init_db(str(other))
    out = world.run("--db", str(other))
    assert out.exit_code == 1
    assert "there is no shop 1: this is not live's database" in out.output


# ---------------------------------------------------------------- the pins
def test_the_disk_floor_is_390s_floor():
    text = DISPATCHER.read_text(encoding="utf-8")
    match = re.search(r"^SPACE_FLOOR_GB = (\{.*\})$", text, re.M)
    assert match, "SPACE_FLOOR_GB not found in the dispatcher"
    floors = ast.literal_eval(match.group(1))
    assert set(floors.values()) == {check.DISK_FLOOR_GB}
    assert check.DISK_FLOOR_GB == 50


def test_the_backup_age_bound_is_25_hours():
    assert check.BACKUP_MAX_AGE_H == 25
