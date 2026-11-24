"""Phase 293 — rendering a manual's pages, and searching their text.

``render_manual`` on a three-page PDF made in the test writes three images
at 200 dpi, three thumbnails and three page rows; a second run writes
nothing; a page that fails records ``render_error`` and stops short;
``render_missing`` makes deleted images again and skips a failed render.
``search_pages`` reaches only this shop's approved manuals, and FTS5 syntax
in a query finds nothing rather than raising. Temporary databases only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from support.phase293 import make_shop, manuals_db, pdf_bytes  # noqa: F401

from motodiag.core.config import get_settings
from motodiag.manuals import render, storage
from motodiag.media.paths import resolve_media_path, stored_media_path
from motodiag.reference import manual_repo
from motodiag.reference.models import ManualReference, ManualSource


def _manual(db: str, shop_id: int, data: bytes, status: str = "approved", **tag) -> int:
    data_dir = get_settings().data_dir
    mid = manual_repo.add_manual(ManualReference(
        source=ManualSource.OTHER, title=tag.pop("title", "Service manual"), shop_id=shop_id,
        status=status, **tag), db_path=db)
    path = storage.manual_file_path(data_dir, shop_id, mid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(path))
    pages = len(doc)
    doc.close()
    manual_repo.set_file(mid, stored_media_path(path, data_dir), "sha", len(data), pages,
                         db_path=db)
    return mid


@pytest.fixture
def shop(manuals_db):
    return make_shop(manuals_db, "alpha")


def _images(shop_id: int, mid: int, n: int = 3) -> list[Path]:
    d = get_settings().data_dir
    return ([storage.page_image_path(d, shop_id, mid, i) for i in range(1, n + 1)]
            + [storage.thumb_path(d, shop_id, mid, i) for i in range(1, n + 1)])


def test_three_pages_three_images_three_thumbs_three_rows(manuals_db, shop):
    mid = _manual(manuals_db, shop.id, pdf_bytes(3))
    assert render.render_manual(mid, manuals_db) == 3
    row = manual_repo.get_manual(mid, db_path=manuals_db)
    assert (row["rendered_pages"], row["page_count"], row["render_error"]) == (3, 3, None)
    pages = manual_repo.list_pages(mid, db_path=manuals_db)
    assert [p["page_number"] for p in pages] == [1, 2, 3]
    assert all(p.exists() for p in _images(shop.id, mid))
    full = Image.open(resolve_media_path(pages[0]["image_path"], get_settings().data_dir))
    # reportlab's default page is A4 (595 x 842 points); at 200 dpi, 1653 x 2339.
    assert full.size == (round(595.2756 * 200 / 72), round(841.8898 * 200 / 72))
    thumb = Image.open(resolve_media_path(pages[0]["thumb_path"], get_settings().data_dir))
    assert max(thumb.size) == render.THUMB_EDGE
    assert not Path(pages[0]["image_path"]).is_absolute(), "stored relative (F205)"
    assert "caliper" in pages[0]["text"]


def test_a_second_run_writes_nothing(manuals_db, shop):
    mid = _manual(manuals_db, shop.id, pdf_bytes(3))
    render.render_manual(mid, manuals_db)
    before = {p: p.stat().st_mtime_ns for p in _images(shop.id, mid)}
    assert render.render_manual(mid, manuals_db) == 0
    assert {p: p.stat().st_mtime_ns for p in _images(shop.id, mid)} == before
    assert len(manual_repo.list_pages(mid, db_path=manuals_db)) == 3


def test_a_page_that_fails_records_the_error_and_stops(manuals_db, shop, monkeypatch):
    mid = _manual(manuals_db, shop.id, pdf_bytes(3))
    real = render._render_page

    def corrupt_page_two(doc, index, image, thumb):
        if index == 1:
            raise RuntimeError("bad page stream")
        return real(doc, index, image, thumb)

    monkeypatch.setattr(render, "_render_page", corrupt_page_two)
    assert render.render_manual(mid, manuals_db) == 1
    row = manual_repo.get_manual(mid, db_path=manuals_db)
    assert row["rendered_pages"] == 1
    assert "page 2" in row["render_error"]
    monkeypatch.setattr(render, "_render_page", real)
    assert render.render_missing(manuals_db) == {}, "a failed render is not retried by itself"


def test_render_missing_writes_deleted_images_again(manuals_db, shop):
    mid = _manual(manuals_db, shop.id, pdf_bytes(3))
    render.render_manual(mid, manuals_db)
    for p in _images(shop.id, mid):
        p.unlink()
    assert render.render_missing(manuals_db) == {mid: 3}
    assert all(p.exists() for p in _images(shop.id, mid))
    assert len(manual_repo.list_pages(mid, db_path=manuals_db)) == 3


def test_render_missing_finishes_a_render_cut_short(manuals_db, shop):
    mid = _manual(manuals_db, shop.id, pdf_bytes(3))
    assert render.render_missing(manuals_db) == {mid: 3}
    assert render.render_missing(manuals_db) == {}


def test_a_file_that_will_not_open_records_the_error(manuals_db, shop):
    mid = _manual(manuals_db, shop.id, pdf_bytes(1))
    storage.manual_file_path(get_settings().data_dir, shop.id, mid).write_bytes(b"%PDF-1.7 no")
    assert render.render_manual(mid, manuals_db) == 0
    assert manual_repo.get_manual(mid, db_path=manuals_db)["render_error"]


# ---------------------------------------------------------------- the search
@pytest.fixture
def two_shops(manuals_db):
    a, b = make_shop(manuals_db, "alpha"), make_shop(manuals_db, "bravo")
    ma = _manual(manuals_db, a.id, pdf_bytes(2), make="Honda", model="CBR600RR",
                 year_start=2003, year_end=2006)
    mb = _manual(manuals_db, b.id, pdf_bytes(1, ["Carburettor float height 14 mm"]))
    for m in (ma, mb):
        render.render_manual(m, manuals_db)
    return a, b, ma, mb


def test_the_search_finds_the_torque_line_with_a_snippet(manuals_db, two_shops):
    a, _, ma, _ = two_shops
    hits = manual_repo.search_pages(a.id, "caliper torque", db_path=manuals_db)
    assert [(h["manual_id"], h["page_number"]) for h in hits] == [(ma, 1)]
    assert "[caliper]" in hits[0]["snippet"] and "[torque]" in hits[0]["snippet"]


def test_the_search_filters_by_bike(manuals_db, two_shops):
    a = two_shops[0]
    assert manual_repo.search_pages(a.id, "caliper", make="Honda", target_year=2004,
                                    db_path=manuals_db)
    assert manual_repo.search_pages(a.id, "caliper", target_year=2010, db_path=manuals_db) == []
    assert manual_repo.search_pages(a.id, "caliper", model="CB750", db_path=manuals_db) == []


def test_another_shops_page_is_never_found(manuals_db, two_shops):
    a, b = two_shops[0], two_shops[1]
    assert manual_repo.search_pages(a.id, "carburettor", db_path=manuals_db) == []
    assert manual_repo.search_pages(b.id, "caliper", db_path=manuals_db) == []
    assert manual_repo.search_pages(b.id, "carburettor", db_path=manuals_db)


def test_a_pending_manual_is_never_found(manuals_db, two_shops):
    a, _, ma, _ = two_shops
    manual_repo.update_manual(ma, db_path=manuals_db, status="pending_review")
    assert manual_repo.search_pages(a.id, "caliper", db_path=manuals_db) == []


@pytest.mark.parametrize("q", ['caliper"', '"', "NEAR(caliper", "caliper OR", "*", "a:b"])
def test_fts_syntax_finds_nothing_instead_of_raising(manuals_db, two_shops, q):
    hits = manual_repo.search_pages(two_shops[0].id, q, db_path=manuals_db)
    assert isinstance(hits, list)
    assert all(h["page_number"] for h in hits)


def test_the_near_query_is_read_as_words(manuals_db, two_shops):
    assert manual_repo.search_pages(two_shops[0].id, "NEAR(", db_path=manuals_db) == []


def test_storage_used_counts_files_and_never_images(manuals_db, two_shops):
    a, _, ma, _ = two_shops
    size = manual_repo.get_manual(ma, db_path=manuals_db)["file_size_bytes"]
    assert manual_repo.list_pages(ma, db_path=manuals_db), "its images exist"
    assert manual_repo.storage_used_bytes(a.id, db_path=manuals_db) == size
