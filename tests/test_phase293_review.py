"""Phase 293 — the person at Mekno who reviews every upload first (K119).

A reviewer is granted through ``grant_reviewer`` and sees the queue across
shops; no one else, whatever their role in any shop, opens a review route.
Each decision records who and when; approval waits for every page; a
rejection or a takedown needs a reason the shop sees. Temporary databases.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from support.phase293 import (  # noqa: F401
    key_for,
    make_shop,
    make_user,
    manuals_db,
    pdf_bytes,
    upload,
)

from motodiag.api import create_app
from motodiag.manuals import review
from motodiag.reference import manual_repo


@pytest.fixture
def world(manuals_db):
    a, b = make_shop(manuals_db, "alpha"), make_shop(manuals_db, "bravo")
    client = TestClient(create_app(db_path_override=manuals_db))
    rid = make_user(manuals_db, "mekno_reviewer", None)
    review.grant_reviewer(rid, db_path=manuals_db)
    ma = upload(client, a.id, a.keys["owner"], pdf_bytes(2)).json()["id"]
    mb = upload(client, b.id, b.keys["service_writer"], pdf_bytes(1)).json()["id"]
    return {"client": client, "a": a, "b": b, "ma": ma, "mb": mb, "rid": rid,
            "rh": {"X-API-Key": key_for(manuals_db, rid)}}


def _decide(w, mid, **body):
    return w["client"].post(f"/v1/review/manuals/{mid}/decision", json=body, headers=w["rh"])


def _page(w, mid, key):
    return w["client"].get(f"/v1/shop/{w['a'].id}/manuals/{mid}/pages/1",
                           headers={"X-API-Key": key})


def test_the_queue_shows_each_shops_pending_manual_oldest_first(manuals_db, world):
    r = world["client"].get("/v1/review/manuals", headers=world["rh"])
    assert r.status_code == 200
    q = r.json()
    assert [x["id"] for x in q] == [world["ma"], world["mb"]]
    assert [x["shop_name"] for x in q] == ["alpha", "bravo"]
    assert [x["uploader_username"] for x in q] == ["alpha_owner", "bravo_service_writer"]
    assert [x["rendered_pages"] for x in q] == [2, 1]
    assert [x["page_count"] for x in q] == [2, 1]


def test_no_one_else_opens_a_review_route(manuals_db, world):
    a, b, mid = world["a"], world["b"], world["ma"]
    solo = make_user(manuals_db, "solo_rider", "individual")
    keys = [a.keys["owner"], a.keys["service_writer"], b.keys["owner"],
            key_for(manuals_db, solo)]
    c = world["client"]
    for key in keys:
        h = {"X-API-Key": key}
        calls = [
            c.get("/v1/review/manuals", headers=h),
            c.get(f"/v1/review/manuals/{mid}", headers=h),
            c.get(f"/v1/review/manuals/{mid}/pages/1", headers=h),
            c.post(f"/v1/review/manuals/{mid}/decision", json={"decision": "approved"},
                   headers=h),
        ]
        assert [x.status_code for x in calls] == [403] * 4
    assert manual_repo.get_manual(mid, db_path=manuals_db)["status"] == "pending_review"


def test_the_reviewer_opens_a_pending_page(world):
    r = world["client"].get(f"/v1/review/manuals/{world['ma']}/pages/1", headers=world["rh"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    one = world["client"].get(f"/v1/review/manuals/{world['ma']}", headers=world["rh"])
    assert one.json()["status"] == "pending_review"


def test_approval_records_who_and_when_and_opens_the_pages(manuals_db, world):
    a, mid = world["a"], world["ma"]
    assert _page(world, mid, a.keys["tech"]).status_code == 404
    r = _decide(world, mid, decision="approved")
    assert r.status_code == 200
    row = manual_repo.get_manual(mid, db_path=manuals_db)
    assert row["status"] == "approved"
    assert row["reviewed_by_user_id"] == world["rid"]
    assert row["reviewed_at"].endswith("Z") or "+00:00" in row["reviewed_at"]
    assert _page(world, mid, a.keys["tech"]).status_code == 200
    hits = world["client"].get(f"/v1/shop/{a.id}/manuals/search", params={"q": "caliper"},
                               headers={"X-API-Key": a.keys["tech"]}).json()
    assert [h["manual_id"] for h in hits] == [mid]


def test_a_tag_fix_changes_the_row_before_approval(manuals_db, world):
    r = _decide(world, world["ma"], decision="approved", title="Honda CBR600F4i manual",
                year_start=2001, year_end=2006)
    assert r.status_code == 200
    row = manual_repo.get_manual(world["ma"], db_path=manuals_db)
    assert (row["title"], row["year_start"], row["year_end"], row["model"]) == (
        "Honda CBR600F4i manual", 2001, 2006, "CBR600RR")


def test_a_rejection_shows_its_reason_and_keeps_the_pages_closed(manuals_db, world):
    a, mid = world["a"], world["ma"]
    assert _decide(world, mid, decision="rejected", reason="a scan of a library book").status_code == 200
    listed = world["client"].get(f"/v1/shop/{a.id}/manuals",
                                 headers={"X-API-Key": a.keys["tech"]}).json()
    mine = next(x for x in listed if x["id"] == mid)
    assert (mine["status"], mine["review_reason"]) == ("rejected", "a scan of a library book")
    assert _page(world, mid, a.keys["tech"]).status_code == 404


@pytest.mark.parametrize("decision", ["rejected", "taken_down"])
def test_a_rejection_or_takedown_without_a_reason_is_422(manuals_db, world, decision):
    before = manual_repo.get_manual(world["ma"], db_path=manuals_db)
    for body in ({"decision": decision}, {"decision": decision, "reason": "   "}):
        r = _decide(world, world["ma"], **body)
        assert r.status_code == 422
        assert r.json()["type"].endswith("manual-reason-required")
    assert manual_repo.get_manual(world["ma"], db_path=manuals_db) == before


def test_approval_while_rendering_is_409(manuals_db, world):
    manual_repo.set_rendered(world["ma"], 1, None, db_path=manuals_db)
    r = _decide(world, world["ma"], decision="approved")
    assert r.status_code == 409
    assert "still rendering (1 of 2)" in r.json()["detail"]
    manual_repo.set_rendered(world["ma"], 2, "page 2: bad stream", db_path=manuals_db)
    r = _decide(world, world["ma"], decision="approved")
    assert r.status_code == 409 and "failed to render" in r.json()["detail"]
    assert manual_repo.get_manual(world["ma"], db_path=manuals_db)["status"] == "pending_review"


def test_a_takedown_closes_the_pages_at_once_and_a_later_approval_opens_them(manuals_db, world):
    a, mid = world["a"], world["ma"]
    _decide(world, mid, decision="approved")
    assert _page(world, mid, a.keys["tech"]).status_code == 200
    r = _decide(world, mid, decision="taken_down", reason="the publisher says it is theirs")
    assert r.status_code == 200
    assert _page(world, mid, a.keys["tech"]).status_code == 404
    assert _decide(world, mid, decision="approved").status_code == 200
    assert _page(world, mid, a.keys["tech"]).status_code == 200


def test_a_revoked_reviewer_is_403_on_the_next_call(manuals_db, world):
    assert world["client"].get("/v1/review/manuals", headers=world["rh"]).status_code == 200
    assert review.revoke_reviewer(world["rid"], db_path=manuals_db)
    assert not review.is_reviewer(world["rid"], db_path=manuals_db)
    assert world["client"].get("/v1/review/manuals", headers=world["rh"]).status_code == 403


def test_the_queue_by_status_and_an_unknown_manual(world):
    _decide(world, world["ma"], decision="rejected", reason="no")
    r = world["client"].get("/v1/review/manuals", params={"status": "rejected"},
                            headers=world["rh"])
    assert [x["id"] for x in r.json()] == [world["ma"]]
    assert world["client"].get("/v1/review/manuals/99999",
                               headers=world["rh"]).status_code == 404
    assert _decide(world, 99999, decision="approved").status_code == 404


def test_grant_twice_is_one_row_and_list_names_them(manuals_db, world):
    assert review.grant_reviewer(world["rid"], db_path=manuals_db) is False
    assert [r["username"] for r in review.list_reviewers(db_path=manuals_db)] == [
        "mekno_reviewer"]


def test_decide_and_flag_directly(manuals_db, world):
    stamp = "2026-11-22T12:00:00Z"
    row = review.decide(world["mb"], "approved", None, world["rid"],
                        clock=lambda: stamp, db_path=manuals_db)
    assert (row["status"], row["reviewed_at"]) == ("approved", stamp)
    row = review.flag(world["mb"], world["b"].users["tech"], 1, "blurry", db_path=manuals_db)
    assert row["status"] == "pending_review"
    assert row["reviewed_by_user_id"] is None and row["reviewed_at"] is None
    assert "page 1" in row["review_reason"]
