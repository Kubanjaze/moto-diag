"""Where a shop's manuals and their page images live, and how much it may store.

The file is ``manuals/shop_<shop_id>/<manual_id>.pdf`` under the data
folder, inside the nightly backup (K121). The page images are
``manual_pages/shop_<shop_id>/<manual_id>/<n>.jpg`` and ``<n>_thumb.jpg``,
outside it on purpose: they are made again from the file after a restore.

The limit is the shop's plan's (``shop_plan``), not the uploader's own tier,
because the files are the shop's. It counts the files only, never the page
images (K123); a rejected or taken-down file counts until the shop deletes
it. GB here is 1024³ bytes, as the photo ceiling's MB is 1024².
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from motodiag.billing.subscription_repo import shop_plan
from motodiag.cli.subscription import TIER_LIMITS, SubscriptionTier

#: At most 300 MB a file (K119).
MANUAL_FILE_BYTES_CAP = 300 * 1024 * 1024


def manual_file_path(data_dir: str | Path, shop_id: int, manual_id: int) -> Path:
    return Path(data_dir) / "manuals" / f"shop_{shop_id}" / f"{manual_id}.pdf"


def _pages_dir(data_dir: str | Path, shop_id: int, manual_id: int) -> Path:
    return Path(data_dir) / "manual_pages" / f"shop_{shop_id}" / str(manual_id)


def page_image_path(data_dir: str | Path, shop_id: int, manual_id: int, n: int) -> Path:
    return _pages_dir(data_dir, shop_id, manual_id) / f"{n}.jpg"


def thumb_path(data_dir: str | Path, shop_id: int, manual_id: int, n: int) -> Path:
    return _pages_dir(data_dir, shop_id, manual_id) / f"{n}_thumb.jpg"


def tier_storage_bytes(tier: Optional[str]) -> Optional[int]:
    """A plan's manual storage, or None for no plan."""
    if tier is None:
        return None
    return TIER_LIMITS[SubscriptionTier(tier)].manual_storage_bytes


def storage_limit_bytes(shop_id: int, db_path: Optional[str] = None) -> Optional[int]:
    """The shop's plan's manual storage; None when the shop has no active plan."""
    return tier_storage_bytes(shop_plan(shop_id, db_path))


def remove_manual_files(data_dir: str | Path, shop_id: int, manual_id: int) -> None:
    """The file and every page image of one manual; nothing else."""
    manual_file_path(data_dir, shop_id, manual_id).unlink(missing_ok=True)
    shutil.rmtree(_pages_dir(data_dir, shop_id, manual_id), ignore_errors=True)
