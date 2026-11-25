"""``motodiag launch check``: whether one paying shop can start on live (Phase 210).

Eight conditions, in the order of 210's written scope, each a function that
returns a :class:`Condition`. The check reads the server's settings and the
database and writes nothing: the database is opened read-only
(``mode=ro``) and never through ``init_db``, which loads the bulletins into
an empty table (F292). The feed's condition calls the rules of
``payments feed status`` as that command calls them, through the feed's own
readers, which do not call ``init_db`` either.

No detail carries a value from the settings: only words (``set``, ``live``,
``on``), counts, times and versions. The one connection the check makes is
to the server on this machine's loopback address.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from motodiag.auth import terms_acceptance
from motodiag.backup.settings import BackupConfigError, work_dir
from motodiag.backup.snapshot import RUNS_LOG
from motodiag.cli.payments import _status_problems
from motodiag.core.config import Environment, Settings
from motodiag.core.database import SCHEMA_VERSION
from motodiag.payments import event_feed, stripe_api

#: Phase 390's free-space floor in GB, the same on both of the home desktop's
#: disks (``SPACE_FLOOR_GB`` in ``.claude/skills/fleet/dispatcher.py``; a test
#: holds the two equal).
DISK_FLOOR_GB = 50
#: The nightly backup's timer fires at 03:00: one day, plus one hour of slack.
BACKUP_MAX_AGE_H = 25
#: The terms version launch needs: 293's terms 1.1.
LAUNCH_TERMS_VERSION = "1.1"
#: Where ``motodiag-api.service`` serves (``--host 127.0.0.1 --port 8000``).
SERVER_URL = "http://127.0.0.1:8000"
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
#: Windows' C: as WSL mounts it on the home desktop.
WINDOWS_DISK = Path("/mnt/c")
#: ``list_reviewers``'s own query (``motodiag.manuals.review``), run here
#: on the read-only connection.
_REVIEWERS_SQL = ("SELECT r.user_id, u.username, r.granted_at, r.granted_by_user_id "
                  "FROM manual_reviewers r LEFT JOIN users u ON u.id = r.user_id "
                  "ORDER BY r.granted_at, r.user_id")


class NotLoopback(Exception):
    """The check was asked to read a server that is not on this machine."""


@dataclass(frozen=True)
class Condition:
    name: str
    ready: bool
    detail: str

    def line(self) -> str:
        if self.ready:
            return f"ready: {self.name} ({self.detail})"
        return f"NOT READY: {self.name}: {self.detail}"


def open_read_only(db_path: str) -> sqlite3.Connection:
    """The database, read-only; ``sqlite3.Error`` when it cannot be opened."""
    path = Path(db_path).expanduser()
    if not path.is_file():
        raise sqlite3.OperationalError(f"there is no database file at {path}")
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except sqlite3.Error:
        conn.close()
        raise
    return conn


# ---------------------------------------------------------------- 1. schema
def schema_condition(conn: sqlite3.Connection) -> Condition:
    name = "the database's schema is at the code's version"
    try:
        found = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    except sqlite3.Error:
        return Condition(name, False, "the database has no schema_version table")
    if found != SCHEMA_VERSION:
        return Condition(name, False, f"the database is at {found} and the code at "
                                      f"{SCHEMA_VERSION}")
    return Condition(name, True, f"database {found}, code {SCHEMA_VERSION}")


# ---------------------------------------------------------------- 2. stripe
def stripe_condition(settings: Settings) -> Condition:
    name = "the server is in prod, with Stripe live and the real prices"
    ks = stripe_api.key_status(settings)
    if not ks.api_key_set:
        key = "not set"
    else:
        key = "test" if ks.test_mode else "live"
    words = [
        ("env", settings.env.value, settings.env == Environment.PROD),
        ("provider", "stripe" if ks.provider == "stripe" else "not stripe",
         ks.provider == "stripe"),
        ("key", key, key == "live"),
        ("prices", str(ks.prices_set), ks.prices_set == 3),
        ("placeholders", "yes" if ks.prices_are_placeholders else "no",
         not ks.prices_are_placeholders),
        ("share links", "on" if settings.share_links_enabled else "off",
         not settings.share_links_enabled),
    ]
    wrong = [f"{label}={word}" for label, word, ok in words if not ok]
    if wrong:
        return Condition(name, False, "wrong: " + ", ".join(wrong))
    return Condition(name, True, ", ".join(f"{label}={word}" for label, word, _ in words))


# ---------------------------------------------------------------- 3. the feed
def feed_condition(settings: Settings, db_path: str, now: float) -> Condition:
    """``payments feed status``'s rules, then the check's own: at launch the
    alarm must be on, where the command prints it as off and no problem."""
    name = "the payments feed and Sentry's alarm are checking in"
    try:
        problems = _status_problems(settings, db_path, event_feed.cursor_rows(db_path), now)
    except sqlite3.Error:
        return Condition(name, False, "the feed's tables cannot be read")
    if event_feed.alarm_dsn(settings) is None:
        problems.append("the alarm is off: no Sentry DSN")
    if problems:
        return Condition(name, False, "; ".join(problems))
    return Condition(name, True, "every account asked within two intervals, "
                                 "and the alarm's check-ins accepted")


# ---------------------------------------------------------------- 4. backup
def backup_condition(now: float) -> Condition:
    name = "last night's backup"
    try:
        log = work_dir() / RUNS_LOG
    except BackupConfigError:
        return Condition(name, False, "the backup's working folder cannot be used")
    lines = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
    lines = [line for line in lines if line.strip()]
    if not lines:
        return Condition(name, False, "no backup has run: runs.log has no line")
    try:
        entry = json.loads(lines[-1])
        taken = datetime.fromisoformat(entry["time"])
    except (ValueError, KeyError, TypeError):
        return Condition(name, False, "the last line of runs.log cannot be read")
    age_h = (now - taken.timestamp()) / 3600
    when = f"taken {entry['time']}, {age_h:.1f} hours ago"
    if entry.get("outcome") != "ok":
        return Condition(name, False, f"the last backup failed ({when})")
    if age_h > BACKUP_MAX_AGE_H:
        return Condition(name, False, f"the last backup is more than {BACKUP_MAX_AGE_H} "
                                      f"hours old ({when})")
    return Condition(name, True, when)


# ---------------------------------------------------------------- 5. terms
def loopback_json(url: str, timeout: float = 5.0) -> dict:
    """GET ``url`` from the server on this machine, never through a proxy."""
    host = urlsplit(url).hostname
    if host not in LOOPBACK_HOSTS:
        raise NotLoopback(f"the launch check reads only this machine's server, not {host}")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def terms_condition(settings: Settings, server_url: Optional[str] = None) -> Condition:
    name = f"the terms switch is on, at version {LAUNCH_TERMS_VERSION}"
    server_url = server_url or SERVER_URL
    version = terms_acceptance.TERMS_VERSION
    if not settings.terms_required:
        return Condition(name, False, "the switch is off (MOTODIAG_TERMS_REQUIRED is not true)")
    if version != LAUNCH_TERMS_VERSION:
        return Condition(name, False, f"the code's terms are version {version}, "
                                      f"not {LAUNCH_TERMS_VERSION}")
    try:
        health = loopback_json(f"{server_url}/healthz")
        served = loopback_json(f"{server_url}/v1/terms")
    except (OSError, ValueError):
        return Condition(name, False, "the server did not answer on loopback")
    if health.get("status") != "ok":
        return Condition(name, False, "the server answered on loopback but is not healthy")
    if served.get("version") != LAUNCH_TERMS_VERSION:
        return Condition(name, False, f"the running server serves version "
                                      f"{served.get('version')}, not {LAUNCH_TERMS_VERSION}")
    return Condition(name, True, f"switch=on, version={version}, "
                                 f"server={served['version']}, healthy")


# ---------------------------------------------------------------- 6. reviewer
def reviewer_condition(conn: sqlite3.Connection) -> Condition:
    name = "a manual reviewer is set"
    try:
        count = len(conn.execute(_REVIEWERS_SQL).fetchall())
    except sqlite3.Error:
        return Condition(name, False, "the manual_reviewers table cannot be read")
    if count == 0:
        return Condition(name, False, "no one is a manual reviewer")
    return Condition(name, True, f"{count} reviewer{'s' if count != 1 else ''}")


# ---------------------------------------------------------------- 7. test shop
def smoke_shop_condition(conn: sqlite3.Connection) -> Condition:
    name = "the test shop is inactive"
    try:
        row = conn.execute("SELECT is_active FROM shops WHERE id = 1").fetchone()
    except sqlite3.Error:
        return Condition(name, False, "the shops table cannot be read")
    if row is None:
        return Condition(name, False, "there is no shop 1: this is not live's database")
    if row[0]:
        return Condition(name, False, "the test shop (id 1) is still active")
    return Condition(name, True, "shop 1 is inactive")


# ---------------------------------------------------------------- 8. disk
def disk_condition(db_path: str) -> Condition:
    name = f"the free disk is above the {DISK_FLOOR_GB} GB floor"
    disks = [("the database's disk", Path(db_path).expanduser().resolve().parent)]
    if os.path.ismount(WINDOWS_DISK):
        disks.append(("C:", WINDOWS_DISK))
    free = [(label, round(shutil.disk_usage(path).free / 1e9, 1)) for label, path in disks]
    words = ", ".join(f"{label} {gb:.1f} GB free" for label, gb in free)
    if any(gb < DISK_FLOOR_GB for _, gb in free):
        return Condition(name, False, f"under the floor: {words}")
    return Condition(name, True, words)


# ---------------------------------------------------------------- the check
def run_conditions(settings: Settings, db_path: str, conn: sqlite3.Connection, *,
                   now: Optional[float] = None) -> list[Condition]:
    """The eight conditions, in the scope's order."""
    at = time.time() if now is None else now
    return [
        schema_condition(conn),
        stripe_condition(settings),
        feed_condition(settings, db_path, at),
        backup_condition(at),
        terms_condition(settings),
        reviewer_condition(conn),
        smoke_shop_condition(conn),
        disk_condition(db_path),
    ]
