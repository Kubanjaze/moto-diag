"""Phase 348, Logic item 8 — the rows the real middleware writes are what K59
sets aside.

K59 (the operator): "audit_events joins SERVER_WRITES as a whole table: it is
append-only and only the server writes it", built by #39 on master. Here, on a
fresh database migrated to 088 (never live): a copy is taken as the backup,
write requests whose only persistent effect is their audit row go through
`create_app(db_path_override=...)`, and `deploy.server_masked(deploy.diff(...))`
between the two is empty, with one set-aside line per event. The keyed request
also moves its key's `last_used_at`, which 383's entry already sets aside. The
control: an UPDATE of an existing `users` row stays in the diff; and with
`audit_events` taken out of a patched `SERVER_WRITES` the rows stay too.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

from support.phase303 import (
    add_member, client, make_key, make_shop, make_sub, make_user, new_db, sql,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "deploy"))

import deploy as D  # noqa: E402


@pytest.fixture
def live(tmp_path, monkeypatch):
    """A fresh database at 088 with a shop, its backup, and the requests made."""
    db = new_db(tmp_path, monkeypatch)
    olga = make_user(db, "olga")
    make_sub(db, olga, "shop")
    shop = make_shop(db, "Shop A", olga)
    tess = make_user(db, "tess")
    make_sub(db, tess, "shop")
    add_member(db, shop, tess, "tech")
    key = make_key(db, tess)
    backup = pathlib.Path(tmp_path / "backup.db")
    D.backup(pathlib.Path(db), backup)

    c = client(db)
    statuses = [
        c.post(f"/v1/shop/{shop}/customers", json={"name": "x"}).status_code,
        c.delete("/v1/no-such-route/1").status_code,
        c.patch(f"/v1/shop/profile/{shop}", json={"phone": "1"},
                headers={"X-API-Key": key}).status_code,
    ]
    assert statuses == [401, 404, 403]
    return db, backup, olga


def _masked(db: str, backup: pathlib.Path):
    return D.server_masked(D.diff(D.dump(backup), D.dump(pathlib.Path(db))), None)


def test_the_entry_is_k59s_whole_table():
    assert D.SERVER_WRITES["audit_events"] == D.WHOLE_TABLE


def test_the_audit_rows_are_set_aside_one_line_per_event(live):
    db, backup, _ = live
    out, aside = _masked(db, backup)
    assert out == {}
    ids = [r[0] for r in sql(db, "SELECT id FROM audit_events ORDER BY id")]
    assert len(ids) == 3
    assert [a for a in aside if a.startswith("audit_events ")] == \
        [f"audit_events {i} added" for i in ids]
    assert all(a.startswith("api_keys ") and a.endswith(" last_used_at")
               for a in aside if not a.startswith("audit_events "))


def test_control_a_users_row_changed_beside_them_stays_in_the_diff(live):
    db, backup, olga = live
    sql(db, "UPDATE users SET full_name = 'Changed' WHERE id = ?", (olga,))
    out, aside = _masked(db, backup)
    assert set(out) == {"users"}
    assert len([a for a in aside if a.startswith("audit_events ")]) == 3


def test_without_the_entry_the_audit_rows_stay(live, monkeypatch):
    db, backup, _ = live
    patched = {t: v for t, v in D.SERVER_WRITES.items() if t != "audit_events"}
    monkeypatch.setattr(D, "SERVER_WRITES", patched)
    out, _ = _masked(db, backup)
    assert set(out) == {"audit_events"}
    assert len(out["audit_events"]["added"]) == 3
