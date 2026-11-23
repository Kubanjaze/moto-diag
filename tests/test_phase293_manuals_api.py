"""Phase 293 — the shop's manual routes, on ``api_db``'s form.

Two shops, A and B, each with an owner (Shop plan), a service writer and a
tech (Individual subscriptions of their own); a stub virus scanner on PATH.
Privacy first, the main risk: nothing of A's is reachable from B, whatever
the manual's status. Then the upload's order of refusals, the plan's
storage limit (K119, K123), the reads, the flag, the delete, and that each
route is reachable with the fixed words declared before ``{manual_id}``.
Temporary databases only; no test reads live, ``git diff`` or a master ref.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from support.phase293 import (  # noqa: F401
    EICAR,
    bad_files,
    key_for,
    make_shop,
    make_user,
    manuals_db,
    padded,
    pdf_bytes,
    upload,
)

from motodiag.api import create_app
from motodiag.cli.subscription import TIER_LIMITS, SubscriptionTier
from motodiag.core.config import get_settings
from motodiag.core.database import get_connection
from motodiag.manuals import storage
from motodiag.reference import manual_repo
from motodiag.shop.rbac import add_shop_member

ROOT = Path(__file__).resolve().parent.parent
MB = 1024 * 1024
STATUSES = ["pending_review", "approved", "rejected", "taken_down"]


@pytest.fixture
def world(manuals_db):
    a, b = make_shop(manuals_db, "alpha"), make_shop(manuals_db, "bravo")
    client = TestClient(create_app(db_path_override=manuals_db))
    return client, a, b


def _h(key: str) -> dict:
    return {"X-API-Key": key}


def _uploaded(client, shop, role="owner", data=None, **meta) -> int:
    r = upload(client, shop.id, shop.keys[role], data or pdf_bytes(2), **meta)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _set(db, mid, status, reason=None):
    manual_repo.set_status(mid, status, None, reason, db_path=db)


def _rows(db) -> int:
    with get_connection(db) as conn:
        return conn.execute("SELECT count(*) FROM manual_references").fetchone()[0]


def _leftovers() -> list[str]:
    d = Path(get_settings().data_dir)
    return [p.name for p in d.glob(".manual_upload_*")] if d.exists() else []


# ---------------------------------------------------------------- privacy
@pytest.mark.parametrize("status", STATUSES)
def test_another_shop_reaches_nothing_of_a_manual(manuals_db, world, status):
    client, a, b = world
    mid = _uploaded(client, a)
    _set(manuals_db, mid, status, "a reason")
    base = f"/v1/shop/{a.id}/manuals"
    for role in ("owner", "service_writer", "tech"):
        h = _h(b.keys[role])
        calls = [
            client.get(base, headers=h),
            client.get(f"{base}/usage", headers=h),
            client.get(f"{base}/{mid}", headers=h),
            client.get(f"{base}/{mid}/pages/1", headers=h),
            client.get(f"{base}/search", params={"q": "caliper"}, headers=h),
            client.post(f"{base}/{mid}/flag", json={"page_number": 1, "reason": "x"}, headers=h),
            client.delete(f"{base}/{mid}", headers=h),
        ]
        assert [r.status_code for r in calls] == [403] * 7, (role, [r.text for r in calls])
    assert manual_repo.get_manual(mid, db_path=manuals_db)["status"] == status


def test_bs_search_never_finds_as_words(manuals_db, world):
    client, a, b = world
    _set(manuals_db, _uploaded(client, a), "approved")
    _set(manuals_db, _uploaded(client, b, data=pdf_bytes(1, ["Carburettor float height"])),
         "approved")
    r = client.get(f"/v1/shop/{b.id}/manuals/search", params={"q": "caliper"},
                   headers=_h(b.keys["owner"]))
    assert r.status_code == 200 and r.json() == []
    r = client.get(f"/v1/shop/{a.id}/manuals/search", params={"q": "caliper"},
                   headers=_h(a.keys["owner"]))
    assert len(r.json()) == 1


def test_as_id_under_bs_path(manuals_db, world):
    client, a, b = world
    mid = _uploaded(client, a)
    _set(manuals_db, mid, "approved")
    r = client.get(f"/v1/shop/{b.id}/manuals/{mid}", headers=_h(a.keys["owner"]))
    assert r.status_code == 403, "A's owner is not a member of B"
    both = make_user(manuals_db, "both", "shop")
    add_shop_member(a.id, both, "tech", db_path=manuals_db)
    add_shop_member(b.id, both, "tech", db_path=manuals_db)
    h = _h(key_for(manuals_db, both))
    for path in (f"/v1/shop/{b.id}/manuals/{mid}", f"/v1/shop/{b.id}/manuals/{mid}/pages/1"):
        assert client.get(path, headers=h).status_code == 404
    assert client.get(f"/v1/shop/{a.id}/manuals/{mid}/pages/1", headers=h).status_code == 200


# ---------------------------------------------------------------- the upload
@pytest.mark.parametrize("role", ["owner", "service_writer"])
def test_the_owner_and_the_service_writer_upload(manuals_db, world, role):
    client, a, _ = world
    data = pdf_bytes(2)
    r = upload(client, a.id, a.keys[role], data)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "pending_review"
    assert body["page_count"] == 2
    assert body["uploaded_by_user_id"] == a.users[role]
    assert "file_path" not in body and "file_sha256" not in body
    row = manual_repo.get_manual(body["id"], db_path=manuals_db)
    assert row["rendered_pages"] == 2, "the background render ran after the response"
    assert row["file_path"] == f"manuals/shop_{a.id}/{body['id']}.pdf"
    assert (Path(get_settings().data_dir) / row["file_path"]).read_bytes() == data
    assert _leftovers() == []


def test_the_tech_may_not_upload(manuals_db, world):
    client, a, _ = world
    assert upload(client, a.id, a.keys["tech"], pdf_bytes()).status_code == 403
    assert _rows(manuals_db) == 0


def test_no_subscription_is_402(manuals_db, world):
    client, a, _ = world
    uid = make_user(manuals_db, "nosub", None)
    add_shop_member(a.id, uid, "owner", db_path=manuals_db)
    r = upload(client, a.id, key_for(manuals_db, uid), pdf_bytes())
    assert r.status_code == 402
    assert r.json()["type"].endswith("subscription-required")


def test_a_shop_with_no_plan_is_402(manuals_db, world):
    client, a, _ = world
    with get_connection(manuals_db) as conn:
        conn.execute("UPDATE subscriptions SET status = 'canceled' WHERE user_id = ?",
                     (a.users["owner"],))
    r = upload(client, a.id, a.keys["service_writer"], pdf_bytes())
    assert r.status_code == 402
    assert "no active plan" in r.json()["detail"]
    assert _rows(manuals_db) == 0


@pytest.mark.parametrize("name", ["png", "javascript", "attachment", "launch", "locked"])
def test_the_five_bad_files_are_refused(manuals_db, world, name):
    client, a, _ = world
    data, reason = bad_files()[name]
    r = upload(client, a.id, a.keys["owner"], data)
    assert r.status_code == 422
    assert r.json()["type"].endswith("manual-refused")
    assert r.json()["detail"] == reason
    assert _rows(manuals_db) == 0 and _leftovers() == []


def test_the_cap_admits_a_file_exactly_at_it_and_refuses_one_byte_more(manuals_db, world,
                                                                        monkeypatch):
    client, a, _ = world
    monkeypatch.setattr(storage, "MANUAL_FILE_BYTES_CAP", MB)
    at_cap = padded(pdf_bytes(), MB)
    assert len(at_cap) == MB
    assert upload(client, a.id, a.keys["owner"], at_cap).status_code == 201
    r = upload(client, a.id, a.keys["owner"], at_cap + b"x")
    assert r.status_code == 413
    assert r.json()["type"].endswith("upload-too-large")
    assert _rows(manuals_db) == 1 and _leftovers() == []


def test_the_cap_is_300_mb():
    assert storage.MANUAL_FILE_BYTES_CAP == 300 * 1024 * 1024


def test_the_same_file_again_is_409_naming_the_first(manuals_db, world):
    client, a, _ = world
    data = pdf_bytes(2)
    mid = _uploaded(client, a, data=data)
    r = upload(client, a.id, a.keys["service_writer"], data)
    assert r.status_code == 409
    assert f"manual id={mid}" in r.json()["detail"]
    assert "pending_review" in r.json()["detail"]
    assert _rows(manuals_db) == 1


def test_another_shops_identical_file_is_stored_again(manuals_db, world):
    client, a, b = world
    data = pdf_bytes(2)
    first, second = _uploaded(client, a, data=data), _uploaded(client, b, data=data)
    assert first != second


def test_no_scanner_is_503_and_writes_nothing(manuals_db, world, tmp_path, monkeypatch):
    client, a, _ = world
    (tmp_path / "none").mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "none"))
    r = upload(client, a.id, a.keys["owner"], pdf_bytes())
    assert r.status_code == 503
    assert r.json()["type"].endswith("manual-scanner-unavailable")
    assert _rows(manuals_db) == 0 and _leftovers() == []
    assert not (Path(get_settings().data_dir) / "manuals").exists()


def test_an_infected_file_is_422_and_writes_nothing(manuals_db, world):
    client, a, _ = world
    r = upload(client, a.id, a.keys["owner"], pdf_bytes() + b"\n%" + EICAR.encode())
    assert r.status_code == 422
    assert r.json()["detail"] == "the file failed the virus scan"
    assert _rows(manuals_db) == 0 and _leftovers() == []
    assert not (Path(get_settings().data_dir) / "manuals").exists()


def test_bad_metadata_is_422(manuals_db, world):
    client, a, _ = world
    r = client.post(f"/v1/shop/{a.id}/manuals", headers=_h(a.keys["owner"]),
                    files={"file": ("m.pdf", pdf_bytes(), "application/pdf")},
                    data={"metadata": '{"kind": "service_manual"}'})
    assert r.status_code == 422
    assert upload(client, a.id, a.keys["owner"], pdf_bytes(), year_start=1960).status_code == 422


# ---------------------------------------------------------------- the limit
def test_the_plans_limits():
    assert TIER_LIMITS[SubscriptionTier.INDIVIDUAL].manual_storage_bytes == 2 * 1024**3
    assert TIER_LIMITS[SubscriptionTier.SHOP].manual_storage_bytes == 20 * 1024**3
    assert TIER_LIMITS[SubscriptionTier.COMPANY].manual_storage_bytes == 50 * 1024**3


def test_over_the_limit_is_402_until_a_manual_is_deleted(manuals_db, world, monkeypatch):
    client, a, _ = world
    monkeypatch.setattr(storage, "storage_limit_bytes", lambda shop_id, db_path=None: MB)
    first = padded(pdf_bytes(), 600 * 1024)
    second = padded(pdf_bytes(1, ["Clutch cable free play 10 mm"]), 600 * 1024)
    r1 = upload(client, a.id, a.keys["owner"], first)
    assert r1.status_code == 201
    r2 = upload(client, a.id, a.keys["owner"], second)
    assert r2.status_code == 402
    detail = r2.json()["detail"]
    assert r2.json()["type"].endswith("manual-storage-exceeded")
    assert f"stores {MB} bytes" in detail and f"{600 * 1024} bytes are used" in detail
    assert "shop plan" in detail
    assert "Delete a manual from the list to free space." in detail
    usage = client.get(f"/v1/shop/{a.id}/manuals/usage", headers=_h(a.keys["tech"])).json()
    assert (usage["used_bytes"], usage["limit_bytes"]) == (600 * 1024, MB)
    assert manual_repo.list_pages(r1.json()["id"], db_path=manuals_db), "its images exist"
    assert manual_repo.storage_used_bytes(a.id, db_path=manuals_db) == 600 * 1024
    d = client.delete(f"/v1/shop/{a.id}/manuals/{r1.json()['id']}", headers=_h(a.keys["owner"]))
    assert d.status_code == 204
    assert upload(client, a.id, a.keys["owner"], second).status_code == 201


def test_the_limit_is_the_shops_plan_not_the_uploaders(manuals_db, world):
    client, a, _ = world
    usage = client.get(f"/v1/shop/{a.id}/manuals/usage",
                       headers=_h(a.keys["service_writer"])).json()
    assert usage == {"plan": "shop", "used_bytes": 0, "limit_bytes": 20 * 1024**3,
                     "file_cap_bytes": 300 * MB}


# ---------------------------------------------------------------- the reads
def test_the_list_shows_every_status_with_its_reason_and_filters(manuals_db, world):
    client, a, _ = world
    ids = {}
    for i, status in enumerate(STATUSES):
        ids[status] = _uploaded(client, a, data=pdf_bytes(1, [f"text {i}"]),
                                title=f"m{i}", kind="parts_catalog" if i == 1 else "wiring",
                                model="CBR600RR" if i else "CB750")
        if status != "pending_review":
            _set(manuals_db, ids[status], status, f"because {status}")
    base, h = f"/v1/shop/{a.id}/manuals", _h(a.keys["tech"])
    rows = {r["id"]: r for r in client.get(base, headers=h).json()}
    assert {r["status"] for r in rows.values()} == set(STATUSES)
    assert rows[ids["rejected"]]["review_reason"] == "because rejected"
    assert rows[ids["taken_down"]]["review_reason"] == "because taken_down"

    def got(**params):
        return sorted(r["id"] for r in client.get(base, params=params, headers=h).json())

    assert got(status="approved") == [ids["approved"]]
    assert got(kind="parts_catalog") == [ids["approved"]]
    assert got(model="CB750") == [ids["pending_review"]]
    assert got(make="Honda", year=2004) == sorted(ids.values())
    assert got(year=2010) == []


def test_usage_is_never_read_as_an_id(manuals_db, world):
    client, a, _ = world
    r = client.get(f"/v1/shop/{a.id}/manuals/usage", headers=_h(a.keys["tech"]))
    assert r.status_code == 200
    assert r.json()["used_bytes"] == 0
    s = client.get(f"/v1/shop/{a.id}/manuals/search", params={"q": "x"},
                   headers=_h(a.keys["tech"]))
    assert s.status_code == 200 and s.json() == []


def test_a_page_opens_only_once_approved(manuals_db, world):
    client, a, _ = world
    mid = _uploaded(client, a)
    page = f"/v1/shop/{a.id}/manuals/{mid}/pages/1"
    h = _h(a.keys["tech"])
    assert client.get(page, headers=h).status_code == 404
    assert client.get(f"/v1/shop/{a.id}/manuals/search", params={"q": "caliper"},
                      headers=h).json() == []
    _set(manuals_db, mid, "approved")
    full = client.get(page, headers=h)
    assert full.status_code == 200 and full.headers["content-type"] == "image/jpeg"
    thumb = client.get(page, params={"size": "thumb"}, headers=h)
    assert thumb.status_code == 200 and len(thumb.content) < len(full.content)
    assert client.get(f"/v1/shop/{a.id}/manuals/{mid}/pages/9", headers=h).status_code == 404
    hits = client.get(f"/v1/shop/{a.id}/manuals/search", params={"q": "caliper torque"},
                      headers=h).json()
    assert [(x["manual_id"], x["page_number"]) for x in hits] == [(mid, 1)]
    assert "caliper" in hits[0]["snippet"].lower()


def test_one_manual_any_status(manuals_db, world):
    client, a, _ = world
    mid = _uploaded(client, a)
    r = client.get(f"/v1/shop/{a.id}/manuals/{mid}", headers=_h(a.keys["tech"]))
    assert r.status_code == 200 and r.json()["status"] == "pending_review"
    assert client.get(f"/v1/shop/{a.id}/manuals/99999",
                      headers=_h(a.keys["tech"])).status_code == 404


# ---------------------------------------------------------------- flag and delete
def test_a_members_flag_sends_it_back_to_review(manuals_db, world):
    client, a, _ = world
    mid = _uploaded(client, a)
    flag = f"/v1/shop/{a.id}/manuals/{mid}/flag"
    h = _h(a.keys["tech"])
    pending = client.post(flag, json={"page_number": 1, "reason": "wrong bike"}, headers=h)
    assert pending.status_code == 409
    _set(manuals_db, mid, "approved")
    assert client.get(f"/v1/shop/{a.id}/manuals/{mid}/pages/1", headers=h).status_code == 200
    r = client.post(flag, json={"page_number": 2, "reason": "the torque is wrong"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "pending_review"
    assert "page 2" in r.json()["review_reason"] and "the torque is wrong" in r.json()[
        "review_reason"]
    assert client.get(f"/v1/shop/{a.id}/manuals/{mid}/pages/1", headers=h).status_code == 404


def test_delete_removes_the_file_the_images_and_the_rows(manuals_db, world):
    client, a, _ = world
    mid = _uploaded(client, a)
    _set(manuals_db, mid, "approved")
    d = get_settings().data_dir
    pdf = storage.manual_file_path(d, a.id, mid)
    image = storage.page_image_path(d, a.id, mid, 1)
    assert pdf.exists() and image.exists()
    url, h = f"/v1/shop/{a.id}/manuals/{mid}", _h(a.keys["owner"])
    assert client.delete(url, headers=_h(a.keys["tech"])).status_code == 403
    assert client.delete(url, headers=h).status_code == 204
    assert not pdf.exists() and not image.exists()
    assert manual_repo.get_manual(mid, db_path=manuals_db) is None
    with get_connection(manuals_db) as conn:
        assert conn.execute("SELECT count(*) FROM manual_pages").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM manual_pages_fts WHERE manual_pages_fts "
                            "MATCH 'caliper'").fetchone()[0] == 0
    assert client.delete(url, headers=h).status_code == 204


def test_every_post_and_delete_is_in_the_activity_log(manuals_db, world):
    client, a, _ = world
    mid = _uploaded(client, a)
    client.delete(f"/v1/shop/{a.id}/manuals/{mid}", headers=_h(a.keys["owner"]))
    with get_connection(manuals_db) as conn:
        rows = conn.execute("SELECT method, path FROM audit_events "
                            "WHERE path LIKE '%/manuals%'").fetchall()
    assert {(r[0], r[1]) for r in rows} >= {
        ("POST", f"/v1/shop/{a.id}/manuals"), ("DELETE", f"/v1/shop/{a.id}/manuals/{mid}")}


# ---------------------------------------------------------------- reachability
EXPECTED = {
    ("POST", "/v1/shop/{shop_id}/manuals"),
    ("GET", "/v1/shop/{shop_id}/manuals"),
    ("GET", "/v1/shop/{shop_id}/manuals/usage"),
    ("GET", "/v1/shop/{shop_id}/manuals/search"),
    ("GET", "/v1/shop/{shop_id}/manuals/{manual_id}"),
    ("GET", "/v1/shop/{shop_id}/manuals/{manual_id}/pages/{n}"),
    ("POST", "/v1/shop/{shop_id}/manuals/{manual_id}/flag"),
    ("DELETE", "/v1/shop/{shop_id}/manuals/{manual_id}"),
    ("GET", "/v1/review/manuals"),
    ("GET", "/v1/review/manuals/{manual_id}"),
    ("GET", "/v1/review/manuals/{manual_id}/pages/{n}"),
    ("POST", "/v1/review/manuals/{manual_id}/decision"),
}


def test_every_route_is_reachable_and_the_fixed_words_come_first():
    routes = [r for r in create_app().routes if hasattr(r, "methods")]
    found = {(m, r.path) for r in routes for m in r.methods if "manuals" in r.path}
    assert found == EXPECTED
    order = [r.path for r in routes]
    by_id = order.index("/v1/shop/{shop_id}/manuals/{manual_id}")
    assert order.index("/v1/shop/{shop_id}/manuals/usage") < by_id
    assert order.index("/v1/shop/{shop_id}/manuals/search") < by_id


def test_the_app_imports_and_includes_both_routers():
    text = (ROOT / "src" / "motodiag" / "api" / "app.py").read_text()
    assert text.count("from motodiag.api.routes.manuals import router as manuals_router") == 1
    assert text.count("import review_router as manual_review_router") == 1
    assert text.count('app.include_router(manuals_router, prefix="/v1")') == 1
    assert text.count('app.include_router(manual_review_router, prefix="/v1")') == 1
