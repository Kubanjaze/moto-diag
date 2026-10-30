"""Phase 348, Logic item 6 — `GET /v1/shop/{shop_id}/audit`.

Shop A is Olga's (owner, shop subscription), with Tess a tech and Abe an
apprentice; Shop B is Bob's. Every status the plan names, the shop filter,
paging without a repeat or a gap, and no hash in the response. Scratch
databases only, as `tests/test_phase303_auth_api.py` makes them.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from motodiag.audit import AuditEvent, append_event
from motodiag.core.database import get_connection

from support.phase303 import (
    add_member, auth, client, login, make_key, make_shop, make_sub, make_user, new_db,
)


@pytest.fixture
def world(tmp_path, monkeypatch):
    db = new_db(tmp_path, monkeypatch)
    olga = make_user(db, "olga")
    make_sub(db, olga, "shop")
    a = make_shop(db, "Shop A", olga)
    bob = make_user(db, "bob")
    make_sub(db, bob, "shop")
    b = make_shop(db, "Shop B", bob)
    tess, abe = make_user(db, "tess"), make_user(db, "abe")
    add_member(db, a, tess, "tech")
    add_member(db, a, abe, "apprentice")
    for u in (tess, abe):
        make_sub(db, u, "shop")
    with get_connection(db) as conn:
        for i in range(1, 8):
            append_event(conn, AuditEvent(method="POST", path=f"/v1/shop/{a}/x/{i}",
                                          status=200, shop_id=a, actor_user_id=olga,
                                          actor_username="olga", credential_kind="api_key",
                                          request_id=f"a{i}", endpoint="ep"))
            append_event(conn, AuditEvent(method="POST", path=f"/v1/shop/{b}/x/{i}",
                                          status=200, shop_id=b, actor_user_id=bob,
                                          request_id=f"b{i}"))
    return SimpleNamespace(db=db, c=client(db), a=a, b=b, olga=olga, bob=bob,
                           tess=tess, abe=abe)


def _get(w, caller: int, shop: int, **params):
    return w.c.get(f"/v1/shop/{shop}/audit", params=params,
                   headers={"X-API-Key": make_key(w.db, caller)})


def _shop_paths(w, shop: int) -> int:
    with get_connection(w.db) as conn:
        return conn.execute("SELECT count(*) FROM audit_events WHERE shop_id = ?",
                            (shop,)).fetchone()[0]


class TestTheOwnerSeesTheirShop:
    def test_only_their_shop_newest_first(self, world):
        r = _get(world, world.olga, world.a)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) == _shop_paths(world, world.a)
        assert all(i["path"].startswith(f"/v1/shop/{world.a}/") for i in items)
        assert [i["id"] for i in items] == sorted((i["id"] for i in items), reverse=True)

    def test_an_item_carries_the_actor_and_no_hash(self, world):
        item = _get(world, world.olga, world.a, limit=1).json()["items"][0]
        assert set(item) == {"id", "occurred_at", "actor", "method", "path", "endpoint",
                             "status", "request_id"}
        assert item["actor"] == {"user_id": world.olga, "username": "olga",
                                 "credential_kind": "api_key"}
        body = _get(world, world.olga, world.a).text
        assert "row_hash" not in body and "prev_hash" not in body

    def test_the_user_filter(self, world):
        with get_connection(world.db) as conn:
            tid = append_event(conn, AuditEvent(method="DELETE", path=f"/v1/shop/{world.a}/y",
                                                status=204, shop_id=world.a,
                                                actor_user_id=world.tess))
        items = _get(world, world.olga, world.a, user_id=world.tess).json()["items"]
        assert [i["id"] for i in items] == [tid]
        assert len(_get(world, world.olga, world.a, user_id=world.olga).json()["items"]) == 7

    def test_paging_walks_the_whole_trail_without_a_repeat_or_a_gap(self, world):
        seen: list[int] = []
        before = None
        while True:
            params = {"limit": 3, **({"before_id": before} if before else {})}
            page = _get(world, world.olga, world.a, **params).json()
            seen += [i["id"] for i in page["items"]]
            before = page["next_before_id"]
            if before is None:
                break
        everything = [i["id"] for i in _get(world, world.olga, world.a, limit=500).json()["items"]]
        assert seen == everything
        assert len(set(seen)) == len(seen) == _shop_paths(world, world.a)

    @pytest.mark.parametrize("limit", [0, 501])
    def test_a_limit_outside_1_to_500_is_refused(self, world, limit):
        assert _get(world, world.olga, world.a, limit=limit).status_code == 422

    def test_a_session_caller_too(self, world):
        r = world.c.get(f"/v1/shop/{world.a}/audit", headers=auth(login(world.c, "olga")))
        assert r.status_code == 200


class TestEveryoneElseIsRefused:
    @pytest.mark.parametrize("who", ["tess", "abe"])
    def test_a_tech_and_an_apprentice_get_403(self, world, who):
        assert _get(world, getattr(world, who), world.a).status_code == 403

    def test_the_owner_of_another_shop_gets_403(self, world):
        assert _get(world, world.bob, world.a).status_code == 403

    def test_no_credential_gets_401(self, world):
        assert world.c.get(f"/v1/shop/{world.a}/audit").status_code == 401

    def test_no_shop_tier_gets_402(self, world):
        nora = make_user(world.db, "nora")
        n = make_shop(world.db, "Shop N", nora)
        assert _get(world, nora, n).status_code == 402
