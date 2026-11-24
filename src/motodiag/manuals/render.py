"""Turning a manual's pages into images and searchable text (Phase 293).

``render_manual`` is the upload's background job and the ``manuals render``
command's worker. Each page in turn is rendered at 200 dpi (an A4 page about
1650 by 2340 pixels, so a torque value reads at full zoom), saved as a JPEG
at quality 85 with a thumbnail of 300 pixels on its long edge, and its text
read; the ``manual_pages`` row is written (the triggers fill the FTS index)
and ``rendered_pages`` advances. One page is in memory at a time. A page
whose row and both images exist is skipped, so the job is safe to run again;
an exception records ``render_error`` and stops.

``render_missing`` is the recovery path, after a restore (the page images
are not backed up, by K123's reading) or a render a restart cut short.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from motodiag.core.config import get_settings
from motodiag.manuals import storage
from motodiag.media.paths import resolve_media_path, stored_media_path
from motodiag.reference import manual_repo

RENDER_DPI = 200
JPEG_QUALITY = 85
THUMB_EDGE = 300


def _render_page(doc, index: int, image: Path, thumb: Path) -> str:
    """Write page ``index``'s image and thumbnail; return its text."""
    page = doc[index]
    try:
        pil = page.render(scale=RENDER_DPI / 72).to_pil().convert("RGB")
        image.parent.mkdir(parents=True, exist_ok=True)
        pil.save(image, "JPEG", quality=JPEG_QUALITY)
        pil.thumbnail((THUMB_EDGE, THUMB_EDGE))
        pil.save(thumb, "JPEG", quality=JPEG_QUALITY)
        return page.get_textpage().get_text_bounded()
    finally:
        page.close()


def render_manual(manual_id: int, db_path: Optional[str] = None,
                  data_dir: Optional[str | Path] = None) -> int:
    """Render every page not yet on disk; return how many were written."""
    import pypdfium2 as pdfium

    data_dir = data_dir or get_settings().data_dir
    manual = manual_repo.get_manual(manual_id, db_path=db_path)
    if manual is None or not manual.get("file_path"):
        return 0
    shop_id = int(manual["shop_id"])
    written = 0
    done = int(manual["rendered_pages"] or 0)
    try:
        doc = pdfium.PdfDocument(str(resolve_media_path(manual["file_path"], data_dir)))
    except pdfium.PdfiumError as exc:
        manual_repo.set_rendered(manual_id, done, f"the file could not be opened: {exc}",
                                 db_path=db_path)
        return 0
    try:
        for index in range(len(doc)):
            n = index + 1
            image = storage.page_image_path(data_dir, shop_id, manual_id, n)
            thumb = storage.thumb_path(data_dir, shop_id, manual_id, n)
            row = manual_repo.get_page(manual_id, n, db_path=db_path)
            if row is not None and image.exists() and thumb.exists():
                continue
            try:
                text = _render_page(doc, index, image, thumb)
            except Exception as exc:  # noqa: BLE001 — any failure is recorded on the row
                manual_repo.set_rendered(manual_id, done, f"page {n}: {exc}", db_path=db_path)
                return written
            if row is None:
                manual_repo.add_page(manual_id, n, stored_media_path(image, data_dir),
                                     stored_media_path(thumb, data_dir), text, db_path=db_path)
                done += 1
            written += 1
            manual_repo.set_rendered(manual_id, done, None, db_path=db_path)
    finally:
        doc.close()
    return written


def _needs_render(manual: dict, data_dir: str | Path, db_path: Optional[str]) -> bool:
    if (manual["rendered_pages"] or 0) < (manual["page_count"] or 0):
        return True
    return any(not resolve_media_path(p["image_path"], data_dir).exists()
               or not resolve_media_path(p["thumb_path"], data_dir).exists()
               for p in manual_repo.list_pages(manual["id"], db_path=db_path))


def render_missing(db_path: Optional[str] = None,
                   data_dir: Optional[str | Path] = None) -> dict[int, int]:
    """Render every uploaded manual with pages missing, in the database or on
    disk, whose render has not failed. {manual_id: pages written}."""
    data_dir = data_dir or get_settings().data_dir
    out: dict[int, int] = {}
    for manual in manual_repo.list_manuals(db_path=db_path):
        if manual.get("shop_id") is None or not manual.get("file_path"):
            continue
        if manual.get("render_error") is not None:
            continue
        if _needs_render(manual, data_dir, db_path):
            out[int(manual["id"])] = render_manual(int(manual["id"]), db_path, data_dir)
    return out
