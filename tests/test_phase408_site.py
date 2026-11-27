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

#: 408_step0.md S0-2: the zip and the live site, equal on 2026-11-21. The
#: files the phase did not change keep these bytes; /thanks/ never moves (the
#: Stripe return page, K74).
PINNED = {
    "404.html": "db6deb9f1a05b4f383ea87a5aa7f37506b4d7c847ba89ae51672d50f7462bd4a",
    "favicon.svg": "a3eda7afe1c7ddf2ac8a338010f919652d74f1ebd9507965befc016eba6d7da4",
    "thanks/index.html": "8ba9ea9dc83207f77f043cbc6c904384bb27503b49466e4e64c6b37b1cbd9365",
}


#: Built from docs/legal/ by scripts/site_build.py (item 14).
BUILT = set(site_build.LEGAL_PAGES)
#: The served set (408_implementation.md, Logic 2).
#: Written by hand in this phase, and by the two scripts.
CHANGED = {"_headers", "index.html", "robots.txt", "styles.css", "support/index.html",
           "sitemap.xml", "og.png", "logo.png"}
#: Phase 329 (K152, K150): the Individual plan's sign-up and the password
#: reset by email. The shops' form stays staged outside site/ (K141).
SIGNUP = {"forms.css", "signup/individual/index.html", "signup/check-email/index.html",
          "signup/paid/index.html", "signup/problem/index.html", "reset/index.html",
          "reset/sent/index.html", "reset/done/index.html", "reset/problem/index.html"}
SERVED = set(PINNED) | BUILT | CHANGED | SIGNUP
#: The founder's photo, once the operator gives it (K103, K110).
OPTIONAL = {"founder.jpg"}
#: 408_step0.md S0-2: the five headers the site sent on 2026-11-21, byte for byte.
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'none'; "
       "frame-ancestors 'none'; base-uri 'self'; form-action 'none'")
HEADERS = (
    "/*\n"
    f"  Content-Security-Policy: {CSP}\n"
    "  X-Content-Type-Options: nosniff\n"
    "  Referrer-Policy: strict-origin-when-cross-origin\n"
    "  Permissions-Policy: camera=(), microphone=(), geolocation=()\n"
    "  X-Frame-Options: DENY\n"
    # Item 2 and K114: a year, no includeSubDomains, no preload.
    "  Strict-Transport-Security: max-age=31536000\n"
)
#: Phase 329: only the sign-up's and the reset's pages may post, and only to
#: the API, whose answer is a redirect back to the site.
FORM_CSP = CSP.replace("form-action 'none'",
                       "form-action https://api.getmekno.com https://getmekno.com")
HEADERS_329 = HEADERS + "".join(
    f"\n{path}\n  ! Content-Security-Policy\n  Content-Security-Policy: {FORM_CSP}\n"
    for path in ("/signup/*", "/reset/*"))
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
    assert SERVED <= _served() <= SERVED | OPTIONAL, sorted(_served() ^ SERVED)


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


def test_the_legal_readmes_publishing_names_site():
    text = (LEGAL / "README.md").read_text(encoding="utf-8")
    publishing = " ".join(text[text.index("## Publishing"):].split())
    assert "is in this repository's `site/`" in publishing
    assert "lies outside this repository" not in text
    assert "`python scripts/site_build.py legal`" in publishing


# ------------------------------------------------------------- item 2: HSTS
def test_headers_are_the_five_of_today_and_hsts_alone():
    assert _read("_headers") == HEADERS_329


def test_the_shops_form_is_not_published():
    """K141: shops sign up through the support email until after shop 10."""
    assert not (SITE / "signup" / "index.html").exists()
    for name in sorted(SIGNUP):
        assert 'href="/signup/"' not in _read(name), name


def test_every_link_on_a_signup_page_reaches_a_published_page():
    pages = _served()
    for name in sorted(SIGNUP - {"forms.css"}):
        for href in __import__("re").findall(r'href="(/[^"#]*)"', _read(name)):
            target = href.lstrip("/")
            assert (target in pages or f"{target}index.html" in pages
                    or target == ""), (name, href)


# ----------------------------------------------------------- reading the pages
HTML_PAGES = sorted(p for p in SERVED | OPTIONAL if p.endswith(".html") and (SITE / p).exists())
#: Item 3: the four pages a search engine may index, and their canonicals.
CANONICAL = {page: site_build.page_url(page) for page in site_build.INDEXABLE}
ORIGIN = site_build.ORIGIN


class _Tags(HTMLParser):
    """Every start tag with its attributes, every script's body, and the title."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.scripts: list[tuple[dict[str, str], str]] = []
        self.title = ""
        self._in: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        self.tags.append((tag, a))
        if tag in {"script", "title"}:
            self._in, self._buf = tag, []
            self._attrs = a

    def handle_endtag(self, tag):
        if tag == self._in:
            text = "".join(self._buf)
            if tag == "script":
                self.scripts.append((self._attrs, text))
            else:
                self.title = text
            self._in = None

    def handle_data(self, data):
        if self._in:
            self._buf.append(data)


def tags(page: str) -> _Tags:
    parser = _Tags()
    parser.feed(_read(page))
    return parser


def meta(page: str, key: str, value: str) -> list[str]:
    return [a.get("content", "") for t, a in tags(page).tags if t == "meta" and a.get(key) == value]


def links(page: str) -> list[str]:
    found = []
    for _t, a in tags(page).tags:
        for k in ("href", "src", "content"):
            v = a.get(k, "")
            if k == "content" and not v.startswith(("http://", "https://", "/")):
                continue
            if v:
                found.append(v)
    return found


def jsonld(page: str) -> list[dict]:
    import json
    return [json.loads(body) for a, body in tags(page).scripts if a.get("type") == "application/ld+json"]


# ------------------------------------------------------------ what must not be
@pytest.mark.parametrize("page", HTML_PAGES)
def test_no_script_runs_and_nothing_is_collected(page):
    import re
    t = tags(page)
    for attrs, _body in t.scripts:
        assert attrs.get("type") == "application/ld+json", f"{page}: a script that runs"
        assert "src" not in attrs, page
    names = [tag for tag, _a in t.tags]
    assert "iframe" not in names, page
    # Phase 329 (K152): only the two sign-up and reset forms, each a plain
    # post to the API's address, which its path rule alone allows.
    forms = [a for tag, a in t.tags if tag == "form"]
    if page in {"signup/individual/index.html", "reset/index.html"}:
        assert len(forms) == 1 and forms[0].get("method") == "post", page
        assert forms[0].get("action", "").startswith("https://api.getmekno.com/v1/"), page
    else:
        assert forms == [], page
    for tag, a in t.tags:
        assert not [k for k in a if k.lower().startswith("on")], f"{page}: <{tag}> has an on* attribute"
    assert not re.search(r"javascript\s*:", _read(page), re.I), page
    assert "Set-Cookie" not in _read(page) and "document.cookie" not in _read(page)


def _host_ok(url: str) -> bool:
    from urllib.parse import urlsplit
    if url == "mailto:support@getmekno.com" or url.startswith(("/", "#")):
        return True
    parts = urlsplit(url)
    if parts.scheme == "https" and parts.netloc == "getmekno.com":
        return True
    # schema.org names the JSON-LD vocabulary; the sitemap's namespace is not a link.
    return False


@pytest.mark.parametrize("page", HTML_PAGES)
def test_no_link_or_asset_to_another_host(page):
    bad = [u for u in links(page) if not _host_ok(u)]
    assert not bad, f"{page}: {bad}"


@pytest.mark.parametrize("page", HTML_PAGES + ["robots.txt", "sitemap.xml", "styles.css"])
def test_the_words_the_site_must_not_say(page):
    import re
    text = _read(page)
    assert "motodiag" not in text.lower(), page
    emails = set(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text))
    assert emails <= {"support@getmekno.com"}, f"{page}: {emails}"
    assert not re.search(r"\+?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b|\+\d[\d\s-]{8,}", text), page
    assert "not for home garages" not in text.lower(), page
    assert "299" not in text, f"{page}: no price beside Company (K114)"
    for word in ("aggregateRating", "ratingValue", "reviewCount", "ratingCount", "testimonial"):
        assert word not in text, f"{page}: {word}"


def test_the_card_no_longer_promises_an_engine_sound_comparison():
    text = " ".join(main_words("index.html"))
    assert "how that engine should sound" not in text
    assert "Record the bike on your phone." in text


# ---------------------------------------------- items 3, 5, 6: each page's head
@pytest.mark.parametrize("page", sorted(CANONICAL))
def test_each_indexable_page_has_its_canonical_and_open_graph(page):
    t = tags(page)
    canon = [a["href"] for tag, a in t.tags if tag == "link" and a.get("rel") == "canonical"]
    assert canon == [CANONICAL[page]], page
    assert meta(page, "property", "og:url") == [CANONICAL[page]]
    assert meta(page, "property", "og:type") == ["website"]
    assert meta(page, "property", "og:site_name") == ["Mekno"]
    assert meta(page, "property", "og:image") == [f"{ORIGIN}/og.png"]
    assert meta(page, "property", "og:title") == [t.title]
    assert meta(page, "property", "og:description") == meta(page, "name", "description")


@pytest.mark.parametrize("page", sorted(CANONICAL))
def test_each_title_and_description_has_its_length(page):
    title = tags(page).title
    (description,) = meta(page, "name", "description")
    assert 30 <= len(title) <= 60, f"{page}: title {len(title)}"
    assert 110 <= len(description) <= 160, f"{page}: description {len(description)}"


@pytest.mark.parametrize("page", ["thanks/index.html", "404.html"])
def test_the_pages_not_to_index_say_so_and_have_no_canonical(page):
    assert meta(page, "name", "robots") == ["noindex"]
    assert not [a for tag, a in tags(page).tags if tag == "link" and a.get("rel") == "canonical"]


# ------------------------------------------------------- item 4: the sitemap
def _sitemap() -> list[tuple[str, str]]:
    import xml.etree.ElementTree as ET
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.fromstring(_read("sitemap.xml"))
    return [(u.findtext("s:loc", namespaces=ns), u.findtext("s:lastmod", namespaces=ns))
            for u in root.findall("s:url", ns)]


def test_the_sitemap_lists_the_four_canonicals():
    assert [loc for loc, _d in _sitemap()] == [CANONICAL[p] for p in site_build.INDEXABLE]
    assert "/thanks/" not in _read("sitemap.xml")


def test_each_lastmod_is_the_date_its_page_last_changed():
    import datetime as dt
    import subprocess
    dates = dict(zip(site_build.INDEXABLE, (d for _l, d in _sitemap()), strict=True))
    for page, date in dates.items():
        dt.date.fromisoformat(date)
    shallow = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"],
                             capture_output=True, text=True).stdout.strip()
    if shallow == "false":
        # In a full clone, the sitemap moves with the pages: run
        # `python scripts/site_build.py sitemap` and commit it with the page.
        for page, date in dates.items():
            assert date == site_build.last_changed(page), f"{page}: run scripts/site_build.py sitemap"


def test_robots_points_at_the_sitemap_and_keeps_thanks_out():
    lines = _read("robots.txt").splitlines()
    assert "Disallow: /thanks/" in lines
    assert f"Sitemap: {ORIGIN}/sitemap.xml" in lines


@pytest.mark.parametrize("page", HTML_PAGES)
def test_no_page_links_the_thanks_page(page):
    assert not [u for u in links(page) if "/thanks" in u], page


# -------------------------------------------------- every link lands on a file
def _target(url: str) -> str | None:
    from urllib.parse import urlsplit
    if url.startswith("mailto:") or url.startswith("#"):
        return None
    path = urlsplit(url).path
    if not path:
        return None
    path = path.lstrip("/")
    return path + "index.html" if path == "" or path.endswith("/") else path


@pytest.mark.parametrize("page", HTML_PAGES)
def test_every_internal_link_and_asset_is_a_file_in_site(page):
    missing = [u for u in links(page) if (t := _target(u)) is not None and not (SITE / t).is_file()]
    assert not missing, f"{page}: {missing}"


def test_every_in_page_anchor_exists():
    import re
    text = _read("index.html")
    ids = set(re.findall(r'\sid="([^"]+)"', text))
    for anchor in re.findall(r'href="#([^"]+)"', text):
        assert anchor in ids, anchor


# ----------------------------------------- items 7, 11, 12: the data and prices
def test_the_json_ld_parses_and_names_only_the_two_priced_plans():
    blocks = jsonld("index.html")
    kinds = sorted(b["@type"] for b in blocks)
    assert kinds == ["Organization", "SoftwareApplication"]
    org = next(b for b in blocks if b["@type"] == "Organization")
    assert org["email"] == "support@getmekno.com" and "sameAs" not in org
    assert org["logo"] == f"{ORIGIN}/logo.png" and org["url"] == f"{ORIGIN}/"
    app = next(b for b in blocks if b["@type"] == "SoftwareApplication")
    offers = {o["name"]: (o["price"], o["priceCurrency"], o["priceSpecification"]["unitCode"])
              for o in app["offers"]}
    assert offers == {"Individual": ("19.00", "USD", "MON"), "Shop": ("99.00", "USD", "MON")}
    for page in HTML_PAGES:
        for b in jsonld(page):
            keys = _keys(b)
            assert not {k for k in keys if k.lower().endswith(("rating", "review", "reviews", "ratingcount", "reviewcount"))}, page


def _keys(value) -> set[str]:
    """Every key, at every depth, of a JSON-LD block."""
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def test_the_prices_are_pr_62s_and_company_has_none():
    text = " ".join(main_words("index.html"))
    assert "Individual: for your own bikes $19 a month" in text
    assert "Shop $99 a month" in text
    assert "Company More than one shop? Talk to us" in text
    assert text.count("$") == 2


def test_the_early_access_line_replaces_the_old_one():
    text = " ".join(main_words("index.html"))
    assert "Want to try it in your shop first?" not in text
    assert "Mekno is in early access. We set up each early-access shop by hand." in text


def test_the_faq_quotes_terms_and_privacy_1_0_word_for_word():
    import re
    text = " ".join(main_words("index.html"))
    sources = " ".join(" ".join(site_build.markdown_words((LEGAL / name).read_text(encoding="utf-8")))
                       for name in ("terms.md", "privacy.md"))
    quotes = re.findall(r'"([^"]{20,})"', text)
    assert len(quotes) >= 5
    for quote in quotes:
        assert quote in sources, quote


# ------------------------------------------------- images carry no metadata
IMAGES = sorted(p for p in _served() if p.endswith((".png", ".jpg", ".jpeg")))
PNG_CHUNKS = {b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND"}


def _png_chunks(data: bytes) -> list[bytes]:
    import struct
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    found, pos = [], 8
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        found.append(data[pos + 4:pos + 8])
        pos += 12 + length
    return found


def _jpeg_markers(data: bytes) -> list[int]:
    assert data[:2] == b"\xff\xd8"
    found, pos = [], 2
    while pos < len(data):
        assert data[pos] == 0xFF, "a JPEG marker"
        marker = data[pos + 1]
        found.append(marker)
        if marker == 0xDA:  # the image data starts; no metadata after it
            break
        length = int.from_bytes(data[pos + 2:pos + 4], "big")
        pos += 2 + length
    return found


def png_size(data: bytes) -> tuple[int, int]:
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


@pytest.mark.parametrize("image", IMAGES)
def test_each_image_carries_no_metadata(image):
    data = (SITE / image).read_bytes()
    if image.endswith(".png"):
        assert set(_png_chunks(data)) <= PNG_CHUNKS, f"{image}: {_png_chunks(data)}"
    else:
        markers = _jpeg_markers(data)
        # APP0 (JFIF) is format only; APP1-APP15 hold Exif, XMP, ICC and the like; FE is a comment.
        assert not [m for m in markers if 0xE1 <= m <= 0xEF or m == 0xFE], f"{image}: {markers}"


def test_the_two_brand_images_have_their_sizes():
    assert png_size((SITE / "og.png").read_bytes()) == (1200, 630)
    assert png_size((SITE / "logo.png").read_bytes()) == (512, 512)


# ------------------------------------------- item 9: the founder block (K103, K110)
def test_the_founder_block_is_whole_or_absent():
    """Name, line and photo go in together, with `founder` in the data; or none of them."""
    import re
    text = _read("index.html")
    org = next(b for b in jsonld("index.html") if b["@type"] == "Organization")
    if "founder.jpg" not in _served():
        assert 'id="founder"' not in text and "founder" not in org
        return
    block = text[text.index('id="founder"'):]
    block = block[:block.index("</section>")]
    assert re.search(r'<img src="/founder\.jpg" alt="[^"]+"', block)
    name = re.search(r"<h3>([^<]+), founder</h3>", block)
    assert name, "the founder's name, then ', founder'"
    assert org["founder"] == {"@type": "Person", "name": name.group(1)}
    assert "@getmekno.com" not in block.replace("support@getmekno.com", "")
