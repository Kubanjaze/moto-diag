"""Phase 408's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/408_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 407's harness, with
two additions: an edit whose old text is None creates a file (removed after),
and an edit on bytes (an image) works on bytes. Exact strings, each must
occur once; every file is restored whatever happens. Exits 1 if any
mutation stays green. An argument runs only the mutations whose name starts
with it.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-p", "no:xdist", "-o", "addopts=", *args]


T = pytest("tests/test_phase408_site.py")

HOME = "site/index.html"
SUPPORT = "site/support/index.html"
CSP = "script-src 'none'"
HSTS = "  Strict-Transport-Security: max-age=31536000\n"
COMPANY = '<p class="price ask">More than one shop? Talk to us</p>'
SUPPORT_TITLE = "<title>Support · Mekno, diagnostics for motorcycle shops</title>"
LEDE_NOTE = "Mekno is in early access. We set up each early-access shop by hand."
CARD = "Record the bike on your phone. Mekno reads the symptoms out of your voice note and looks at the video with you."
QUOTE = '"We do not sell anyone\'s data, and we do not use it for advertising." (Privacy)'
PNG_END = b"\x00\x00\x00\x00IEND\xaeB`\x82"
#: The terms page's sitemap entry as committed (its date moves with the page).
_SITEMAP = (ROOT / "site" / "sitemap.xml").read_text(encoding="utf-8")
_AT = _SITEMAP.index("<loc>https://getmekno.com/terms/</loc>")
TERMS_LASTMOD = _SITEMAP[_AT:_SITEMAP.index("</lastmod>", _AT) + len("</lastmod>")]
TEXT_CHUNK = (b"\x00\x00\x00\x07tEXtA\x00hello" + b"\x00\x00\x00\x00")

MUTATIONS = [
    ("M1 a file that is not served sits in site/", [("site/notes.txt", None, "notes\n")], T),
    ("M2 the Stripe return page changes", [("site/thanks/index.html", "</html>", "</html> ")], T),
    ("M3 the CSP lets a script run", [("site/_headers", CSP, "script-src 'self'")], T),
    ("M4 HSTS covers every subdomain", [("site/_headers", HSTS,
     "  Strict-Transport-Security: max-age=31536000; includeSubDomains\n")], T),
    ("M5 a script that runs", [(HOME, "</body>", "<script>1</script></body>")], T),
    ("M6 a form", [(HOME, "</main>", '<form action="/x"></form></main>')], T),
    ("M7 an on* attribute", [(HOME, '<main>', '<main onclick="x">')], T),
    ("M8 a link to another host", [(SUPPORT, '<a href="/privacy/">privacy policy</a>',
     '<a href="https://example.com/">privacy policy</a>')], T),
    ("M9 the old name", [(SUPPORT, "<h1>Support</h1>", "<h1>MotoDiag support</h1>")], T),
    ("M10 a second email address", [(SUPPORT, "<h2>Email</h2>", "<h2>Email (or hello@getmekno.com)</h2>")], T),
    ("M11 a phone number", [(SUPPORT, "<h2>Email</h2>", "<h2>Email or call 617-555-0123</h2>")], T),
    ("M12 a price beside Company", [(HOME, COMPANY,
     '<p class="price ask">More than one shop? Talk to us, $299</p>')], T),
    ("M13 a title over 60 characters", [(SUPPORT, SUPPORT_TITLE,
     "<title>Support · Mekno, diagnostics for motorcycle shops and riders everywhere</title>")], T),
    ("M14 a description under 110 characters", [(SUPPORT,
     '<meta name="description" content="How to reach Mekno: email support@getmekno.com, and a person '
     'reads every message. Help with your plan, a payment to a shop, or the data we keep about you.">',
     '<meta name="description" content="How to reach Mekno.">')], T),
    ("M15 a canonical on www", [(SUPPORT, '<link rel="canonical" href="https://getmekno.com/support/">',
     '<link rel="canonical" href="https://www.getmekno.com/support/">')], T),
    ("M16 the 404 page may be indexed", [("site/404.html", '  <meta name="robots" content="noindex">\n', "")], T),
    ("M17 the sitemap lists /thanks/", [("site/sitemap.xml", "<loc>https://getmekno.com/privacy/</loc>",
     "<loc>https://getmekno.com/thanks/</loc>")], T),
    ("M18 robots.txt loses the sitemap", [("site/robots.txt",
     "Sitemap: https://getmekno.com/sitemap.xml\n", "")], T),
    ("M19 an internal link to nothing", [(HOME, '<a href="/support/">Support</a>\n      </nav>',
     '<a href="/pricing/">Support</a>\n      </nav>')], T),
    ("M20 a rating in the data", [(HOME, '"email": "support@getmekno.com"',
     '"email": "support@getmekno.com", "aggregateRating": {"ratingValue": "5"}')], T),
    ("M21 a plan's price drifts", [(HOME, '"price": "19.00",\n        "priceCurrency": "USD",\n        "priceSpecification"',
     '"price": "29.00",\n        "priceCurrency": "USD",\n        "priceSpecification"')], T),
    ("M22 the privacy text changes and the page is not rebuilt", [("docs/legal/privacy.md",
     "do not sell anyone's data, and we", "never sell anyone's data, and we")], T),
    ("M23 the build links an outside address", [("scripts/site_build.py",
     '        if url.startswith(ORIGIN + "/") or url == ORIGIN:\n', "        if True:\n"),
     ], T),
    ("M24 an image carries a text chunk", [("site/og.png", PNG_END, TEXT_CHUNK + PNG_END)], T),
    ("M25 the old card comes back", [(HOME, CARD,
     "Record a cold start, a rattle or a misfire on your phone. Mekno compares it with how that engine should sound.")], T),
    ("M26 a FAQ quote is not the policy's words", [(HOME, QUOTE,
     '"We never sell anyone\'s data, and we do not use it for advertising." (Privacy)')], T),
    ("M27 the old early-access line comes back", [(HOME, LEDE_NOTE,
     "Want to try it in your shop first?")], T),
    ("M28 a page links the thanks page", [(HOME, '<a href="#faq">FAQ</a>', '<a href="/thanks/">FAQ</a>')], T),
    ("M29 a lastmod that is not the page's", [("site/sitemap.xml", TERMS_LASTMOD,
     "<loc>https://getmekno.com/terms/</loc>\n    <lastmod>2001-01-01</lastmod>")], T),
    ("M31 the founder's photo carries Exif", [("site/founder.jpg", b"\xff\xd8\xff\xe0",
     b"\xff\xd8\xff\xe1\x00\x0eExif\x00\x00MM\x00*\xff\xe0")], T),
    ("M32 the founder block loses the name", [(HOME, ", founder</h3>", "</h3>")], T),
    ("M30 the legal README forgets site/", [("docs/legal/README.md", "is in this repository's `site/`",
     "is in this repository")], T),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests", ROOT / "scripts"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode


def apply(rel: str, old, new, originals: dict, created: list) -> None:
    path = ROOT / rel
    if old is None:
        assert not path.exists(), f"{rel} exists"
        path.write_text(new)
        created.append(path)
        return
    if isinstance(old, bytes):
        originals.setdefault(rel, path.read_bytes())
        current = path.read_bytes()
    else:
        originals.setdefault(rel, path.read_text(encoding="utf-8"))
        current = path.read_text(encoding="utf-8")
    assert current.count(old) == 1, f"the text occurs {current.count(old)} times in {rel}"
    changed = current.replace(old, new)
    if isinstance(changed, bytes):
        path.write_bytes(changed)
    else:
        path.write_text(changed, encoding="utf-8")


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    commands = []
    for m in chosen:
        if m[2] not in commands:
            commands.append(m[2])
    for command in commands:
        assert run(command) == 0, f"not green before mutating: {command}"
    survivors = []
    for name, edits, command in chosen:
        originals: dict = {}
        created: list = []
        try:
            for rel, old, new in edits:
                apply(rel, old, new, originals, created)
            code = run(command)
        finally:
            for rel, data in originals.items():
                path = ROOT / rel
                if isinstance(data, bytes):
                    path.write_bytes(data)
                else:
                    path.write_text(data, encoding="utf-8")
            for path in created:
                path.unlink()
        verdict = "red" if code != 0 else "GREEN (survived)"
        print(f"{name}: {verdict}", flush=True)
        if code == 0:
            survivors.append(name)
    for command in commands:
        assert run(command) == 0, f"not green after restoring: {command}"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
