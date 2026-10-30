"""Phase 348, Logic item 7 — `motodiag audit {list, verify, export}`.

Each subcommand under `CliRunner` against a scratch database: the empty case,
filters, `--json`, `verify`'s exit codes on an intact chain, a changed row, a
removed row and a dropped trigger, and `export`'s refusal to overwrite.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from motodiag.audit import AuditEvent, append_event
from motodiag.cli.main import cli
from motodiag.core.database import get_connection

from support.phase303 import client, login, make_key, make_shop, make_sub, make_user, new_db, sql


@pytest.fixture
def db(tmp_path, monkeypatch):
    return new_db(tmp_path, monkeypatch)


def run(*args):
    return CliRunner().invoke(cli, list(args))


def _fill(db: str, n: int = 3) -> None:
    with get_connection(db) as conn:
        for i in range(1, n + 1):
            append_event(conn, AuditEvent(
                method="POST", path=f"/v1/shop/{i % 2 + 1}/x", status=200,
                shop_id=i % 2 + 1, actor_user_id=10 + i % 2,
                actor_username=f"u{10 + i % 2}", credential_kind="session",
                occurred_at=f"2026-10-{10 + i:02d}T12:00:00.000+00:00"))


class TestList:
    def test_a_fresh_install_says_there_are_no_events(self, db):
        r = run("audit", "list")
        assert r.exit_code == 0, r.output
        assert "no events yet" in r.output

    def test_json_parses_newest_first_and_filters(self, db):
        _fill(db, 4)
        r = run("audit", "list", "--json")
        assert r.exit_code == 0, r.output
        assert [e["id"] for e in json.loads(r.output)] == [4, 3, 2, 1]

        def ids(*args):
            return [e["id"] for e in json.loads(run("audit", "list", "--json", *args).output)]
        assert ids("--shop", "1") == [4, 2]
        assert ids("--user", "11") == [3, 1]
        assert ids("--since", "2026-10-13T00:00:00+00:00") == [4, 3]
        assert ids("--until", "2026-10-12T13:00:00+00:00") == [2, 1]
        assert ids("--path", "/v1/shop/2") == [3, 1]
        assert ids("--limit", "1") == [4]

    def test_a_username_resolves_and_an_unknown_one_is_refused(self, db):
        uid = make_user(db, "olga")
        with get_connection(db) as conn:
            append_event(conn, AuditEvent(method="POST", path="/v1/a", status=200,
                                          actor_user_id=uid))
        assert [e["actor_user_id"] for e in json.loads(
            run("audit", "list", "--json", "--user", "olga").output)] == [uid]
        r = run("audit", "list", "--user", "nobody")
        assert r.exit_code != 0 and "no user matching" in r.output

    def test_a_bad_since_is_refused_cleanly(self, db):
        r = run("audit", "list", "--since", "whenever")
        assert r.exit_code == 1 and "since must be" in r.output

    def test_the_table_shows_who(self, db):
        _fill(db, 1)
        r = run("audit", "list")
        assert r.exit_code == 0 and "u11" in r.output

    def test_json_after_real_requests_carries_no_token_or_its_hash(self, db):
        uid = make_user(db, "olga")
        make_sub(db, uid, "shop")
        shop = make_shop(db, "Shop A", uid)
        c = client(db)
        token = login(c, "olga")
        key = make_key(db, uid)
        c.patch(f"/v1/shop/profile/{shop}", json={"phone": "1"}, headers={"X-API-Key": key})
        out = run("audit", "list", "--json").output
        events = json.loads(out)
        assert len(events) == 2
        hashes = [h for (h,) in sql(db, "SELECT key_hash FROM api_keys")]
        for secret in (token, key, *hashes):
            assert secret not in out


class TestVerify:
    def test_an_intact_chain_exits_0_with_the_count_and_head(self, db):
        _fill(db)
        r = run("audit", "verify")
        assert r.exit_code == 0, r.output
        head = sql(db, "SELECT row_hash FROM audit_events ORDER BY id DESC LIMIT 1")[0][0]
        assert "events: 3" in r.output and head in r.output and "chain intact" in r.output

    def test_a_changed_row_exits_nonzero_naming_it(self, db):
        _fill(db)
        sql(db, "DROP TRIGGER audit_events_no_update")
        sql(db, "UPDATE audit_events SET status = 500 WHERE id = 2")
        sql(db, "CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events "
                "BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END")
        r = run("audit", "verify")
        assert r.exit_code != 0 and "chain broken at event 2" in r.output

    def test_a_removed_row_exits_nonzero(self, db):
        _fill(db)
        sql(db, "DROP TRIGGER audit_events_no_delete")
        sql(db, "DELETE FROM audit_events WHERE id = 2")
        sql(db, "CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events "
                "BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END")
        r = run("audit", "verify")
        assert r.exit_code != 0 and "chain broken at event 3" in r.output

    def test_a_dropped_trigger_exits_nonzero_naming_it(self, db):
        _fill(db)
        sql(db, "DROP TRIGGER audit_events_no_delete")
        r = run("audit", "verify")
        assert r.exit_code != 0 and "missing trigger: audit_events_no_delete" in r.output


class TestExport:
    def test_it_writes_one_line_per_event(self, db, tmp_path):
        _fill(db)
        out = tmp_path / "trail.jsonl"
        r = run("audit", "export", str(out))
        assert r.exit_code == 0, r.output
        assert "wrote 3 events" in r.output
        assert [json.loads(x)["id"] for x in out.read_text().splitlines()] == [1, 2, 3]

    def test_it_refuses_to_overwrite(self, db, tmp_path):
        _fill(db)
        out = tmp_path / "trail.jsonl"
        out.write_text("keep\n")
        r = run("audit", "export", str(out))
        assert r.exit_code != 0 and "refusing to overwrite" in r.output
        assert out.read_text() == "keep\n"
