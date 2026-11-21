"""Phase 408 — getmekno.com's source in `site/`, held without the network.

Each test reads `site/` and `docs/legal/` only. The first commit under
`site/` is the Direct Upload deployment 592d738e as it was, byte for byte
(`408_step0.md` S0-2); later commits move a pin only for a file they change.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

#: 408_step0.md S0-2: the zip and the live site, equal on 2026-11-21.
PINNED = {
    "_headers": "0db0814825652ec99c9879473fcd883495e10336a020a55be38175d13bd6bf2e",
    "index.html": "25d10976e91edb02362576cb1b99cdd58d97783b0f2ccf20953f4e6b8bf42ace",
    "404.html": "db6deb9f1a05b4f383ea87a5aa7f37506b4d7c847ba89ae51672d50f7462bd4a",
    "robots.txt": "39ebecbb8c9fce53c69912f2c47c83ca70e2358ed65ef900d96847d12f733423",
    "styles.css": "21ac74ea9b5b7dc29d327f90943d9d95f17d5607f82f2427d2a1e3adebe12b3a",
    "favicon.svg": "a3eda7afe1c7ddf2ac8a338010f919652d74f1ebd9507965befc016eba6d7da4",
    "support/index.html": "75b5656332f1b14534404b4ca99815db4509ef1ccd44355b99e4aa308b5028f1",
    "terms/index.html": "6638f2599d02c2e665c7878648d630a87875cd5b4fceb7840ea4832b150fdde7",
    "privacy/index.html": "9ea862c181aadeec54cc803a433129f571d50f31d6c731f3d38627b52d2d0824",
    "thanks/index.html": "8ba9ea9dc83207f77f043cbc6c904384bb27503b49466e4e64c6b37b1cbd9365",
}


def _served() -> set[str]:
    return {p.relative_to(SITE).as_posix() for p in SITE.rglob("*") if p.is_file()}


def test_the_served_set_is_exactly_the_sites_files():
    assert _served() == set(PINNED)


@pytest.mark.parametrize("name", sorted(PINNED))
def test_each_pinned_file_keeps_its_bytes(name):
    assert hashlib.sha256((SITE / name).read_bytes()).hexdigest() == PINNED[name], name
