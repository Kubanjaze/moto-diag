"""Phase 293 — the uploaded manuals join the nightly backup; their page
images do not, and are made again after a restore (K121, K123).

In 345's fixtures' form: a live-shaped folder holding one manual's PDF and
its rendered page, an in-memory store, the cheap cipher. The manifest lists
the PDF and not the image; the second snapshot sends nothing again; a
restore brings the PDF back byte for byte and no image; ``render_missing``
on the restored folder writes the image, and the page route serves it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from support.phase293 import key_for, make_shop, pdf_bytes
from support.phase345 import FAKE_VALUES, MemoryStore, cheap_crypto, clock_at, make_live

from motodiag.api import create_app
from motodiag.backup import snapshot as snap
from motodiag.backup.restore import list_snapshots, restore
from motodiag.backup.settings import BackupSettings
from motodiag.backup.snapshot import take_snapshot
from motodiag.manuals import render, storage
from motodiag.media.paths import stored_media_path
from motodiag.reference import manual_repo
from motodiag.reference.models import ManualReference, ManualSource

T1 = "2026-11-22T03:00:00.000+00:00"
T2 = "2026-11-23T03:00:00.000+00:00"


@pytest.fixture(autouse=True)
def _cheap(monkeypatch):
    cheap_crypto(monkeypatch)


@pytest.fixture
def settings(tmp_path):
    return BackupSettings(tmp_path / "backup.env", *list(FAKE_VALUES.values()))


@pytest.fixture
def live(tmp_path):
    db, data = make_live(tmp_path, media={})
    shop = make_shop(str(db), "alpha")
    mid = manual_repo.add_manual(ManualReference(
        source=ManualSource.OTHER, title="Service manual", shop_id=shop.id,
        status="approved"), db_path=str(db))
    pdf = storage.manual_file_path(data, shop.id, mid)
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(pdf_bytes(1))
    manual_repo.set_file(mid, stored_media_path(pdf, data), "sha", pdf.stat().st_size, 1,
                         db_path=str(db))
    assert render.render_manual(mid, str(db), data) == 1
    return db, data, shop, mid


def _rels(shop, mid):
    return (f"manuals/shop_{shop.id}/{mid}.pdf", f"manual_pages/shop_{shop.id}/{mid}/1.jpg")


def test_the_folders_are_the_four(tmp_path):
    assert snap.MEDIA_DIRS == ("videos", "photos", "audio", "manuals")


def test_the_manifest_lists_the_pdf_and_not_the_image(live, settings, tmp_path):
    db, data, shop, mid = live
    pdf_rel, image_rel = _rels(shop, mid)
    assert (data / image_rel).exists()
    work = tmp_path / "work"
    work.mkdir()
    store = MemoryStore()
    first = take_snapshot(db, data, settings, store, work, clock_at(T1))
    paths = [e.path for e in first.manifest.media]
    assert paths == [pdf_rel]
    assert (first.media_uploaded, first.media_skipped) == (1, 0)
    second = take_snapshot(db, data, settings, store, work, clock_at(T2))
    assert (second.media_uploaded, second.media_skipped) == (0, 1)


def test_a_restore_brings_the_pdf_back_and_the_render_makes_the_image(
        live, settings, tmp_path, monkeypatch):
    db, data, shop, mid = live
    pdf_rel, image_rel = _rels(shop, mid)
    work = tmp_path / "work"
    work.mkdir()
    store = MemoryStore()
    take_snapshot(db, data, settings, store, work, clock_at(T1))
    to = tmp_path / "restored"
    restore(list_snapshots(store)[0], store, settings, to)
    assert (to / pdf_rel).read_bytes() == (data / pdf_rel).read_bytes()
    assert not (to / "manual_pages").exists()

    restored_db = str(to / "motodiag.db")
    assert render.render_missing(restored_db, to) == {mid: 1}
    assert (to / image_rel).exists()

    from motodiag.core.config import reset_settings
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(to))
    monkeypatch.setenv("MOTODIAG_DB_PATH", restored_db)
    reset_settings()
    try:
        client = TestClient(create_app(db_path_override=restored_db))
        r = client.get(f"/v1/shop/{shop.id}/manuals/{mid}/pages/1",
                       headers={"X-API-Key": key_for(restored_db, shop.users["tech"])})
        assert r.status_code == 200 and r.content == (to / image_rel).read_bytes()
    finally:
        reset_settings()
