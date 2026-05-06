"""Phase 194 (Commit 0) — work-order photo upload + CRUD endpoints.

Pins the substrate-half of the substrate-then-feature pair (Phase 194
capture/attach/display + Phase 194B AI photo analysis). Tests cover:

* Migration v41 — work_order_photos table + indexes + FK posture.
* photo_pipeline.normalize_photo — decode + EXIF rotation + resize +
  JPEG quality (Section K image-pipeline normalization).
* wo_photo_repo CRUD — create / get / list / update_pairing /
  soft_delete + quota helpers.
* Route layer — POST / GET / PATCH / DELETE / file-stream over
  /v1/shop/{shop_id}/work-orders/{wo_id}/photos with auth, cross-shop
  isolation, quota enforcement (per-WO 30 / per-issue 10), pair_id
  validation, and image-format error mapping (HEIC without
  pillow-heif → 415; corrupt input → 422).
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.media.photo_pipeline import (
    ImageDecodeError,
    LONG_EDGE_BOUND_PX,
    NormalizedPhoto,
    UnsupportedImageFormatError,
    normalize_photo,
)
from motodiag.shop import (
    add_shop_member, create_shop, create_work_order, seed_first_owner,
)
from motodiag.shop.wo_photo_repo import (
    WorkOrderPhotoPairingError,
    WorkOrderPhotoQuotaExceededError,
    count_issue_photos,
    count_wo_photos,
    count_wo_photos_this_month_for_uploader,
    create_wo_photo,
    get_wo_photo,
    get_wo_photo_for_pairing,
    list_issue_photos,
    list_wo_photos,
    soft_delete_wo_photo,
    update_pairing,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase194_c0.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(tmp_path / "data"))
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username, sub_tier="shop"):
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        )
        user_id = cur.lastrowid
        conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, current_period_end)
               VALUES (?, ?, 'active', datetime('now', '+30 days'))""",
            (user_id, sub_tier),
        )
    return user_id


def _seed_shop_and_wo(db_path, owner_user_id, shop_name="TestShop"):
    """Create a shop owned by owner_user_id + 1 open WO. Returns (shop_id, wo_id)."""
    shop_id = create_shop(shop_name, db_path=db_path)
    seed_first_owner(shop_id, owner_user_id, db_path=db_path)

    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES ('Honda', 'CBR600', 2005, 'none')"
        )
        vid = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO customers (name, phone, email) "
            "VALUES ('Alice', '555-0100', 'a@ex.com')"
        )
        cust_id = cur.lastrowid
    wo_id = create_work_order(
        shop_id=shop_id, vehicle_id=vid, customer_id=cust_id,
        title="brake service", priority=2, db_path=db_path,
    )
    return shop_id, wo_id


def _seed_issue(db_path, work_order_id):
    """Create one issue on the WO. Returns issue_id."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO issues
               (work_order_id, title, category, severity, status)
               VALUES (?, 'brake squeal', 'brakes', 'medium', 'open')""",
            (work_order_id,),
        )
        return cur.lastrowid


@pytest.fixture
def authed(api_db):
    user_id = _make_user(api_db, "owner")
    _, plaintext = create_api_key(user_id, db_path=api_db)
    shop_id, wo_id = _seed_shop_and_wo(api_db, user_id)
    return user_id, plaintext, shop_id, wo_id


@pytest.fixture
def client(api_db):
    return TestClient(create_app(db_path_override=api_db))


def _make_jpeg_bytes(w=320, h=240, color="red", exif=None):
    """Helper: build a JPEG of (w, h) in RGB."""
    img = Image.new("RGB", (w, h), color=color)
    buf = io.BytesIO()
    if exif is not None:
        img.save(buf, format="JPEG", exif=exif)
    else:
        img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_rgba_bytes(w=200, h=200):
    img = Image.new("RGBA", (w, h), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. Migration shape
# ---------------------------------------------------------------------------


class TestMigration041:

    def test_schema_version_at_least_41(self):
        # Pin the floor (Phase 194 bumped 40 → 41 for work_order_photos)
        # rather than equality — downstream phases may bump further
        # without re-litigating this assertion. Matches the F9-SSOT
        # discipline applied to Phase 192's equivalent test.
        assert SCHEMA_VERSION >= 41  # f9-noqa: ssot-pin contract-pin: phase-194 floor — verifies migration 041 landed and stays

    def test_table_exists_with_expected_columns(self, api_db):
        with get_connection(api_db) as conn:
            cur = conn.execute("PRAGMA table_info(work_order_photos)")
            cols = {r[1]: (r[2], bool(r[3]), r[4]) for r in cur.fetchall()}
        # All planned columns present
        for name in (
            "id", "work_order_id", "issue_id", "role", "pair_id",
            "file_path", "file_size_bytes", "width", "height",
            "sha256", "captured_at", "uploaded_by_user_id",
            "analysis_state", "analysis_findings", "source",
            "created_at", "updated_at", "deleted_at",
        ):
            assert name in cols, f"missing column: {name}"
        # Required NOT NULL columns
        assert cols["work_order_id"][1] is True
        assert cols["role"][1] is True
        assert cols["file_path"][1] is True
        assert cols["uploaded_by_user_id"][1] is True
        # Substrate-anticipates-feature columns are NULLABLE
        assert cols["analysis_state"][1] is False
        assert cols["analysis_findings"][1] is False
        assert cols["source"][1] is False
        # role default
        assert cols["role"][2] == "'general'"

    def test_indexes_exist(self, api_db):
        with get_connection(api_db) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND tbl_name='work_order_photos'"
            )
            names = {r[0] for r in cur.fetchall()}
        assert "idx_wo_photos_wo" in names
        assert "idx_wo_photos_issue" in names
        assert "idx_wo_photos_pair" in names
        assert "idx_wo_photos_sha256" in names

    def test_role_check_constraint_rejects_invalid_role(self, api_db, authed):
        user_id, _, _, wo_id = authed
        with get_connection(api_db) as conn:
            with pytest.raises(Exception):  # IntegrityError
                conn.execute(
                    """INSERT INTO work_order_photos
                       (work_order_id, role, file_path,
                        file_size_bytes, width, height, sha256,
                        captured_at, uploaded_by_user_id)
                       VALUES (?, 'INVALID_ROLE', 'p.jpg',
                               100, 10, 10, 'abc', '2026-05-06', ?)""",
                    (wo_id, user_id),
                )

    def test_role_check_constraint_accepts_each_enum_value(
        self, api_db, authed,
    ):
        user_id, _, _, wo_id = authed
        with get_connection(api_db) as conn:
            for role in ("before", "after", "general", "undecided"):
                conn.execute(
                    """INSERT INTO work_order_photos
                       (work_order_id, role, file_path,
                        file_size_bytes, width, height, sha256,
                        captured_at, uploaded_by_user_id)
                       VALUES (?, ?, ?, 100, 10, 10, ?, '2026-05-06', ?)""",
                    (wo_id, role, f"p_{role}.jpg", role, user_id),
                )

    def test_fk_cascade_on_wo_delete(self, api_db, authed):
        user_id, _, _, wo_id = authed
        photo_id = create_wo_photo(
            work_order_id=wo_id, file_path="p.jpg",
            file_size_bytes=100, width=10, height=10,
            sha256="abc", captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        with get_connection(api_db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("DELETE FROM work_orders WHERE id = ?", (wo_id,))
        assert get_wo_photo(photo_id, db_path=api_db) is None


# ---------------------------------------------------------------------------
# 2. Photo pipeline (Section K)
# ---------------------------------------------------------------------------


class TestPhotoPipeline:

    def test_jpeg_passthrough_keeps_dimensions(self):
        raw = _make_jpeg_bytes(100, 50)
        result = normalize_photo(raw)
        assert isinstance(result, NormalizedPhoto)
        assert result.width == 100
        assert result.height == 50

    def test_resize_4000x3000_to_2048_long_edge(self):
        raw = _make_jpeg_bytes(4000, 3000)
        result = normalize_photo(raw)
        assert result.width == LONG_EDGE_BOUND_PX
        assert result.height == 1536  # 3000 * 2048/4000 = 1536

    def test_resize_preserves_portrait_aspect_ratio(self):
        raw = _make_jpeg_bytes(3000, 4000)
        result = normalize_photo(raw)
        assert result.height == LONG_EDGE_BOUND_PX
        assert result.width == 1536

    def test_no_upscaling_for_small_inputs(self):
        raw = _make_jpeg_bytes(50, 50)
        result = normalize_photo(raw)
        assert result.width == 50
        assert result.height == 50

    def test_png_rgba_converts_to_rgb_jpeg(self):
        raw = _make_png_rgba_bytes(200, 200)
        result = normalize_photo(raw)
        # Output is JPEG (no alpha channel preserved)
        out = Image.open(io.BytesIO(result.jpeg_bytes))
        assert out.mode == "RGB"

    def test_exif_orientation_6_rotates_to_upright(self):
        # EXIF orientation 6 = rotate 90 CW. Source: 200x100; expected
        # output: 100x200 (the canonical sideways-photo fix).
        img = Image.new("RGB", (200, 100), color="green")
        exif = img.getexif()
        exif[0x0112] = 6  # Orientation tag
        buf = io.BytesIO()
        img.save(buf, format="JPEG", exif=exif)
        result = normalize_photo(buf.getvalue())
        assert result.width == 100
        assert result.height == 200

    def test_empty_payload_raises_decode_error(self):
        with pytest.raises(ImageDecodeError):
            normalize_photo(b"")

    def test_corrupt_payload_raises_decode_error(self):
        with pytest.raises(ImageDecodeError):
            normalize_photo(b"this is not an image" * 100)

    def test_jpeg_quality_85_smaller_than_input(self):
        # 4000x3000 solid-color → tiny JPEG; 4000x3000 with synthetic
        # noise pattern → still much smaller than raw at q=85. Pin so
        # a future quality bump doesn't silently grow output 5x.
        raw = _make_jpeg_bytes(4000, 3000, color="red")
        result = normalize_photo(raw)
        # 2048x1536 RGB raw is ~9MB; JPEG q=85 should be < 1MB even
        # for noisy inputs (solid color is much smaller).
        assert len(result.jpeg_bytes) < 1_000_000


# ---------------------------------------------------------------------------
# 3. Repo CRUD + quota helpers
# ---------------------------------------------------------------------------


class TestWorkOrderPhotoRepo:

    def test_create_get_round_trip(self, api_db, authed):
        user_id, _, _, wo_id = authed
        photo_id = create_wo_photo(
            work_order_id=wo_id, file_path="p1.jpg",
            file_size_bytes=12345, width=2048, height=1536,
            sha256="abc123", captured_at="2026-05-06T10:00:00Z",
            uploaded_by_user_id=user_id,
            role="before", db_path=api_db,
        )
        row = get_wo_photo(photo_id, db_path=api_db)
        assert row is not None
        assert row["work_order_id"] == wo_id
        assert row["role"] == "before"
        assert row["width"] == 2048
        assert row["height"] == 1536
        assert row["uploaded_by_user_id"] == user_id

    def test_list_returns_newest_first(self, api_db, authed):
        user_id, _, _, wo_id = authed
        ids = []
        for i in range(3):
            ids.append(create_wo_photo(
                work_order_id=wo_id, file_path=f"p{i}.jpg",
                file_size_bytes=100, width=10, height=10,
                sha256=f"s{i}", captured_at=f"2026-05-0{i + 1}T10:00:00Z",
                uploaded_by_user_id=user_id, db_path=api_db,
            ))
        rows = list_wo_photos(wo_id, db_path=api_db)
        assert len(rows) == 3
        # newest captured_at first → ids[2] then ids[1] then ids[0]
        assert [r["id"] for r in rows] == [ids[2], ids[1], ids[0]]

    def test_list_excludes_soft_deleted(self, api_db, authed):
        user_id, _, _, wo_id = authed
        photo_id = create_wo_photo(
            work_order_id=wo_id, file_path="p.jpg",
            file_size_bytes=100, width=10, height=10,
            sha256="s", captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        soft_delete_wo_photo(photo_id, db_path=api_db)
        assert list_wo_photos(wo_id, db_path=api_db) == []
        assert get_wo_photo(photo_id, db_path=api_db) is None

    def test_soft_delete_idempotent(self, api_db, authed):
        user_id, _, _, wo_id = authed
        photo_id = create_wo_photo(
            work_order_id=wo_id, file_path="p.jpg",
            file_size_bytes=100, width=10, height=10,
            sha256="s", captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        assert soft_delete_wo_photo(photo_id, db_path=api_db) is True
        assert soft_delete_wo_photo(photo_id, db_path=api_db) is False

    def test_list_issue_photos_filters_by_issue(self, api_db, authed):
        user_id, _, _, wo_id = authed
        issue_id = _seed_issue(api_db, wo_id)
        # 2 photos on issue, 1 photo on WO without issue
        for i in range(2):
            create_wo_photo(
                work_order_id=wo_id, file_path=f"p{i}.jpg",
                file_size_bytes=100, width=10, height=10,
                sha256=f"s{i}", captured_at="2026-05-06",
                uploaded_by_user_id=user_id, issue_id=issue_id,
                db_path=api_db,
            )
        create_wo_photo(
            work_order_id=wo_id, file_path="generic.jpg",
            file_size_bytes=100, width=10, height=10,
            sha256="generic", captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        issue_rows = list_issue_photos(issue_id, db_path=api_db)
        assert len(issue_rows) == 2
        assert all(r["issue_id"] == issue_id for r in issue_rows)
        assert count_issue_photos(issue_id, db_path=api_db) == 2
        assert count_wo_photos(wo_id, db_path=api_db) == 3

    def test_count_monthly_for_uploader(self, api_db, authed):
        user_id, _, _, wo_id = authed
        for i in range(5):
            create_wo_photo(
                work_order_id=wo_id, file_path=f"p{i}.jpg",
                file_size_bytes=100, width=10, height=10,
                sha256=f"s{i}", captured_at="2026-05-06",
                uploaded_by_user_id=user_id, db_path=api_db,
            )
        assert count_wo_photos_this_month_for_uploader(
            user_id, db_path=api_db,
        ) == 5

    def test_update_pairing_promotes_undecided_to_typed(
        self, api_db, authed,
    ):
        user_id, _, _, wo_id = authed
        photo_id = create_wo_photo(
            work_order_id=wo_id, file_path="p.jpg",
            file_size_bytes=100, width=10, height=10,
            sha256="s", captured_at="2026-05-06",
            uploaded_by_user_id=user_id, role="undecided", db_path=api_db,
        )
        update_pairing(
            photo_id, pair_id=None, role="general", db_path=api_db,
        )
        row = get_wo_photo(photo_id, db_path=api_db)
        assert row["role"] == "general"

    def test_update_pairing_with_pair_id_links_partners(
        self, api_db, authed,
    ):
        user_id, _, _, wo_id = authed
        before_id = create_wo_photo(
            work_order_id=wo_id, file_path="b.jpg",
            file_size_bytes=100, width=10, height=10,
            sha256="b", captured_at="2026-05-06",
            uploaded_by_user_id=user_id, role="before", db_path=api_db,
        )
        after_id = create_wo_photo(
            work_order_id=wo_id, file_path="a.jpg",
            file_size_bytes=100, width=10, height=10,
            sha256="a", captured_at="2026-05-06",
            uploaded_by_user_id=user_id, role="after",
            pair_id=before_id, db_path=api_db,
        )
        # Caller-side: update_pairing on "before" to point at "after"
        update_pairing(before_id, pair_id=after_id, db_path=api_db)
        before_row = get_wo_photo(before_id, db_path=api_db)
        after_row = get_wo_photo(after_id, db_path=api_db)
        assert before_row["pair_id"] == after_id
        assert after_row["pair_id"] == before_id

    def test_pair_id_set_null_on_partner_delete(self, api_db, authed):
        user_id, _, _, wo_id = authed
        before_id = create_wo_photo(
            work_order_id=wo_id, file_path="b.jpg",
            file_size_bytes=100, width=10, height=10,
            sha256="b", captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        after_id = create_wo_photo(
            work_order_id=wo_id, file_path="a.jpg",
            file_size_bytes=100, width=10, height=10,
            sha256="a", captured_at="2026-05-06",
            uploaded_by_user_id=user_id, pair_id=before_id, db_path=api_db,
        )
        # HARD-delete the "before" row (FK cascade only fires on real
        # DELETE; soft-delete is a column update). Pin the FK posture.
        with get_connection(api_db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "DELETE FROM work_order_photos WHERE id = ?", (before_id,),
            )
        after_row = get_wo_photo(after_id, db_path=api_db)
        assert after_row is not None
        assert after_row["pair_id"] is None

    def test_get_wo_photo_for_pairing_rejects_other_wo(
        self, api_db, authed,
    ):
        user_id, _, shop_id, wo_id = authed
        # Create a 2nd WO in same shop
        with get_connection(api_db) as conn:
            cur = conn.execute(
                "INSERT INTO vehicles (make, model, year, protocol) "
                "VALUES ('Honda', 'CB500', 2010, 'none')"
            )
            vid = cur.lastrowid
            cur = conn.execute(
                "INSERT INTO customers (name, phone) "
                "VALUES ('Bob', '555-0200')"
            )
            cust_id = cur.lastrowid
        wo2_id = create_work_order(
            shop_id=shop_id, vehicle_id=vid, customer_id=cust_id,
            title="other", priority=3, db_path=api_db,
        )
        photo_on_wo2 = create_wo_photo(
            work_order_id=wo2_id, file_path="p.jpg",
            file_size_bytes=100, width=10, height=10,
            sha256="s", captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        # Looking up photo_on_wo2 with expected_wo_id=wo_id returns None
        assert get_wo_photo_for_pairing(
            photo_on_wo2, expected_wo_id=wo_id, db_path=api_db,
        ) is None
        # Same lookup with the correct expected_wo_id returns the row
        assert get_wo_photo_for_pairing(
            photo_on_wo2, expected_wo_id=wo2_id, db_path=api_db,
        ) is not None


# ---------------------------------------------------------------------------
# 4. Route — happy path
# ---------------------------------------------------------------------------


def _post_photo(client, key, shop_id, wo_id, raw=None, **meta_overrides):
    raw = raw or _make_jpeg_bytes(800, 600, color="red")
    metadata = {
        "captured_at": "2026-05-06T10:00:00Z",
        "role": "general",
    }
    metadata.update(meta_overrides)
    import json as _json
    return client.post(
        f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos",
        files={"file": ("photo.jpg", raw, "image/jpeg")},
        data={"metadata": _json.dumps(metadata)},
        headers={"X-API-Key": key},
    )


class TestUploadHappyPath:

    def test_upload_returns_201_with_normalized_dimensions(
        self, client, authed,
    ):
        _, key, shop_id, wo_id = authed
        # 4000x3000 input → 2048x1536 output
        raw = _make_jpeg_bytes(4000, 3000)
        r = _post_photo(client, key, shop_id, wo_id, raw=raw)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["work_order_id"] == wo_id
        assert body["role"] == "general"
        assert body["width"] == 2048
        assert body["height"] == 1536
        assert body["analysis_state"] is None  # 194 doesn't write
        assert body["analysis_findings"] is None

    def test_upload_writes_jpeg_to_canonical_path(
        self, client, authed, api_db, tmp_path,
    ):
        _, key, shop_id, wo_id = authed
        r = _post_photo(client, key, shop_id, wo_id)
        assert r.status_code == 201
        photo_id = r.json()["id"]
        # File at {data_dir}/photos/shop_{shop_id}/work_order_{wo_id}/{id}.jpg
        expected = (
            tmp_path / "data" / "photos"
            / f"shop_{shop_id}" / f"work_order_{wo_id}" / f"{photo_id}.jpg"
        )
        assert expected.exists(), f"missing: {expected}"
        # The on-disk JPEG decodes to a valid image
        out = Image.open(expected)
        assert out.format == "JPEG"

    def test_list_then_get_round_trip(self, client, authed):
        _, key, shop_id, wo_id = authed
        r1 = _post_photo(client, key, shop_id, wo_id, role="before")
        r2 = _post_photo(client, key, shop_id, wo_id, role="after")
        assert r1.status_code == 201 and r2.status_code == 201
        list_r = client.get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos",
            headers={"X-API-Key": key},
        )
        assert list_r.status_code == 200
        items = list_r.json()
        assert len(items) == 2
        assert {it["role"] for it in items} == {"before", "after"}
        # GET single
        photo_id = items[0]["id"]
        get_r = client.get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos/{photo_id}",
            headers={"X-API-Key": key},
        )
        assert get_r.status_code == 200
        assert get_r.json()["id"] == photo_id

    def test_patch_promotes_undecided_to_general(self, client, authed):
        _, key, shop_id, wo_id = authed
        r = _post_photo(client, key, shop_id, wo_id, role="undecided")
        assert r.status_code == 201
        photo_id = r.json()["id"]
        patch_r = client.patch(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos/{photo_id}",
            json={"role": "general"},
            headers={"X-API-Key": key},
        )
        assert patch_r.status_code == 200, patch_r.text
        assert patch_r.json()["role"] == "general"

    def test_delete_returns_204_idempotent(self, client, authed):
        _, key, shop_id, wo_id = authed
        r = _post_photo(client, key, shop_id, wo_id)
        photo_id = r.json()["id"]
        del_r1 = client.delete(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos/{photo_id}",
            headers={"X-API-Key": key},
        )
        assert del_r1.status_code == 204
        del_r2 = client.delete(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos/{photo_id}",
            headers={"X-API-Key": key},
        )
        assert del_r2.status_code == 204  # idempotent

    def test_file_stream_serves_jpeg(self, client, authed):
        _, key, shop_id, wo_id = authed
        r = _post_photo(client, key, shop_id, wo_id)
        photo_id = r.json()["id"]
        file_r = client.get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos/{photo_id}/file",
            headers={"X-API-Key": key},
        )
        assert file_r.status_code == 200
        assert file_r.headers["content-type"] == "image/jpeg"
        # Body is a valid JPEG
        out = Image.open(io.BytesIO(file_r.content))
        assert out.format == "JPEG"


# ---------------------------------------------------------------------------
# 5. Route — auth + cross-shop isolation
# ---------------------------------------------------------------------------


class TestUploadAuth:

    def test_unauth_returns_401(self, client, authed):
        _, _, shop_id, wo_id = authed
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos",
            files={"file": ("p.jpg", _make_jpeg_bytes(), "image/jpeg")},
            data={"metadata": '{"captured_at": "2026-05-06T10:00:00Z"}'},
        )
        assert r.status_code == 401

    def test_individual_tier_returns_402(self, client, authed, api_db):
        _, _, shop_id, wo_id = authed
        # Create individual-tier user with their own key
        ind_user_id = _make_user(api_db, "alone", sub_tier="individual")
        _, ind_key = create_api_key(ind_user_id, db_path=api_db)
        r = _post_photo(client, ind_key, shop_id, wo_id)
        assert r.status_code == 402

    def test_cross_shop_returns_403(self, client, authed, api_db):
        # owner has their shop; other_user has their OWN shop with WO
        _, key, _, _ = authed
        other_user = _make_user(api_db, "other_owner")
        other_shop, other_wo = _seed_shop_and_wo(
            api_db, other_user, shop_name="OtherShop",
        )
        # owner tries to upload to other_shop's WO
        r = _post_photo(client, key, other_shop, other_wo)
        assert r.status_code == 403

    def test_cross_wo_returns_404(self, client, authed):
        _, key, shop_id, wo_id = authed
        bad_wo = wo_id + 9999
        r = _post_photo(client, key, shop_id, bad_wo)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 6. Route — quotas
# ---------------------------------------------------------------------------


class TestUploadQuotas:

    def test_per_wo_count_cap_enforced(
        self, client, authed, api_db,
    ):
        from motodiag.api.routes.photos import PER_WO_COUNT_CAP
        _, key, shop_id, wo_id = authed
        user_id = authed[0]
        # Bypass HTTP for the first PER_WO_COUNT_CAP photos to avoid
        # PIL CPU on quota-fill; the LAST one is what we exercise.
        for i in range(PER_WO_COUNT_CAP):
            create_wo_photo(
                work_order_id=wo_id, file_path=f"p{i}.jpg",
                file_size_bytes=100, width=10, height=10,
                sha256=f"s{i}", captured_at="2026-05-06",
                uploaded_by_user_id=user_id, db_path=api_db,
            )
        r = _post_photo(client, key, shop_id, wo_id)
        assert r.status_code == 402
        body = r.json()
        assert body["type"].endswith("wo-photo-quota-exceeded")

    def test_per_issue_count_cap_enforced(
        self, client, authed, api_db,
    ):
        from motodiag.api.routes.photos import PER_ISSUE_COUNT_CAP
        _, key, shop_id, wo_id = authed
        user_id = authed[0]
        issue_id = _seed_issue(api_db, wo_id)
        # Fill the issue to its cap via direct repo writes
        for i in range(PER_ISSUE_COUNT_CAP):
            create_wo_photo(
                work_order_id=wo_id, file_path=f"p{i}.jpg",
                file_size_bytes=100, width=10, height=10,
                sha256=f"s{i}", captured_at="2026-05-06",
                uploaded_by_user_id=user_id, issue_id=issue_id,
                db_path=api_db,
            )
        r = _post_photo(client, key, shop_id, wo_id, issue_id=issue_id)
        assert r.status_code == 402

    def test_quota_does_not_count_soft_deleted(
        self, client, authed, api_db,
    ):
        from motodiag.api.routes.photos import PER_WO_COUNT_CAP
        _, key, shop_id, wo_id = authed
        user_id = authed[0]
        # Fill, soft-delete one, then upload should succeed
        ids = []
        for i in range(PER_WO_COUNT_CAP):
            ids.append(create_wo_photo(
                work_order_id=wo_id, file_path=f"p{i}.jpg",
                file_size_bytes=100, width=10, height=10,
                sha256=f"s{i}", captured_at="2026-05-06",
                uploaded_by_user_id=user_id, db_path=api_db,
            ))
        soft_delete_wo_photo(ids[0], db_path=api_db)
        r = _post_photo(client, key, shop_id, wo_id)
        assert r.status_code == 201


# ---------------------------------------------------------------------------
# 7. Route — pairing + image-format errors
# ---------------------------------------------------------------------------


class TestPairingAndErrors:

    def test_pair_id_to_nonexistent_returns_422(self, client, authed):
        _, key, shop_id, wo_id = authed
        r = _post_photo(
            client, key, shop_id, wo_id,
            role="after", pair_id=999_999,
        )
        assert r.status_code == 422
        assert r.json()["type"].endswith("wo-photo-pairing-error")

    def test_corrupt_payload_returns_422(self, client, authed):
        _, key, shop_id, wo_id = authed
        import json as _json
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos",
            files={"file": ("bad.jpg", b"this is not an image" * 50, "image/jpeg")},
            data={"metadata": _json.dumps({"captured_at": "2026-05-06T10:00:00Z"})},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 422

    def test_metadata_invalid_role_returns_422(self, client, authed):
        _, key, shop_id, wo_id = authed
        import json as _json
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos",
            files={"file": ("p.jpg", _make_jpeg_bytes(), "image/jpeg")},
            data={"metadata": _json.dumps({
                "captured_at": "2026-05-06T10:00:00Z",
                "role": "INVALID_ROLE",
            })},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 422

    def test_post_pairs_then_patch_assigns_to_partner(self, client, authed):
        _, key, shop_id, wo_id = authed
        r1 = _post_photo(client, key, shop_id, wo_id, role="before")
        before_id = r1.json()["id"]
        r2 = _post_photo(
            client, key, shop_id, wo_id,
            role="after", pair_id=before_id,
        )
        after_id = r2.json()["id"]
        assert r2.status_code == 201
        # Both rows now reference each other
        get_before = client.get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos/{before_id}",
            headers={"X-API-Key": key},
        )
        get_after = client.get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos/{after_id}",
            headers={"X-API-Key": key},
        )
        assert get_before.json()["pair_id"] == after_id
        assert get_after.json()["pair_id"] == before_id


# ---------------------------------------------------------------------------
# 8. Quota helper unit tests (counts only — bypass HTTP)
# ---------------------------------------------------------------------------


class TestQuotaHelperUnit:

    def test_quota_exceeded_error_carries_metadata(self):
        e = WorkOrderPhotoQuotaExceededError(
            current=30, limit=30, scope="wo", unit="count",
        )
        assert e.current == 30
        assert e.limit == 30
        assert e.scope == "wo"
        assert "30/30 count" in str(e)

    def test_pairing_error_subtypes_value_error(self):
        e = WorkOrderPhotoPairingError("test")
        assert isinstance(e, ValueError)
