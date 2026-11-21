"""Phase 408 — getmekno.com's source in `site/`, held without the network.

Each test reads `site/` and `docs/legal/` only. The first commit under
`site/` is the Direct Upload deployment 592d738e as it was, byte for byte
(`408_step0.md` S0-2); later commits move a pin only for a file they change.
"""

from __future__ import annotations

import hashlib
import importlib.util
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
LEGAL = ROOT / "docs" / "legal"

_spec = importlib.util.spec_from_file_location("site_build", ROOT / "scripts" / "site_build.py")
assert _spec and _spec.loader
site_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(site_build)

#: 408_step0.md S0-2: the zip and the live site, equal on 2026-11-21.
PINNED = {
    "_headers": "0db0814825652ec99c9879473fcd883495e10336a020a55be38175d13bd6bf2e",
    "index.html": "25d10976e91edb02362576cb1b99cdd58d97783b0f2ccf20953f4e6b8bf42ace",
    "404.html": "db6deb9f1a05b4f383ea87a5aa7f37506b4d7c847ba89ae51672d50f7462bd4a",
    "robots.txt": "39ebecbb8c9fce53c69912f2c47c83ca70e2358ed65ef900d96847d12f733423",
    "styles.css": "21ac74ea9b5b7dc29d327f90943d9d95f17d5607f82f2427d2a1e3adebe12b3a",
    "favicon.svg": "a3eda7afe1c7ddf2ac8a338010f919652d74f1ebd9507965befc016eba6d7da4",
    "support/index.html": "75b5656332f1b14534404b4ca99815db4509ef1ccd44355b99e4aa308b5028f1",
    "thanks/index.html": "8ba9ea9dc83207f77f043cbc6c904384bb27503b49466e4e64c6b37b1cbd9365",
}


#: Built from docs/legal/ by scripts/site_build.py (item 14).
BUILT = set(site_build.LEGAL_PAGES)
#: The served set (408_implementation.md, Logic 2).
SERVED = set(PINNED) | BUILT
ATTRIBUTION = ("Adapted from Basecamp's policies (https://github.com/basecamp/policies), "
               "used under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).")


def _served() -> set[str]:
    return {p.relative_to(SITE).as_posix() for p in SITE.rglob("*") if p.is_file()}


def _read(name: str) -> str:
    return (SITE / name).read_text(encoding="utf-8")


class _MainText(HTMLParser):
    """The words inside <main>, as a reader sees them."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "main" or self.depth:
            self.depth += 1 if tag not in {"br", "hr", "img", "meta", "link"} else 0

    def handle_endtag(self, tag):
        if self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.text.append(data)


def main_words(name: str) -> list[str]:
    parser = _MainText()
    parser.feed(_read(name))
    return "".join(parser.text).split()


def test_the_served_set_is_exactly_the_sites_files():
    assert _served() == SERVED


@pytest.mark.parametrize("name", sorted(PINNED))
def test_each_pinned_file_keeps_its_bytes(name):
    assert hashlib.sha256((SITE / name).read_bytes()).hexdigest() == PINNED[name], name


# ------------------------------------------------- item 14: terms and privacy 1.0
@pytest.mark.parametrize("page", sorted(BUILT))
def test_each_legal_page_is_the_builds_output(page):
    assert _read(page) == site_build.render_legal(page), f"run scripts/site_build.py legal ({page})"


@pytest.mark.parametrize("page", sorted(BUILT))
def test_each_legal_page_says_its_text_word_for_word(page):
    source = LEGAL / site_build.LEGAL_PAGES[page]["source"]
    assert main_words(page) == site_build.markdown_words(source.read_text(encoding="utf-8"))


@pytest.mark.parametrize("page", sorted(BUILT))
def test_each_legal_page_shows_its_version_and_the_attribution(page):
    text = " ".join(main_words(page))
    source = (LEGAL / site_build.LEGAL_PAGES[page]["source"]).read_text(encoding="utf-8")
    version = next(line for line in source.splitlines() if site_build.VERSION_LINE.match(line))
    assert f'<p class="updated">{version}</p>' in _read(page)
    assert ATTRIBUTION in text
    assert "November 9, 2026" not in _read(page)
    assert "Last updated" not in _read(page)


def test_the_legal_readme_names_site():
    assert "`site/`" in (LEGAL / "README.md").read_text(encoding="utf-8")
