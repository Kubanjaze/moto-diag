"""Build getmekno.com's generated files in `site/` (Phase 408).

    python scripts/site_build.py legal     # site/terms/ and site/privacy/ from docs/legal/
    python scripts/site_build.py sitemap   # site/sitemap.xml, each lastmod from git
    python scripts/site_build.py check     # exit 1 if a committed page is not the output

The terms and privacy pages are the texts in `docs/legal/`, word for word,
in the site's own header, footer and styles. The Markdown they use is a
small, fixed subset: `#` and `##` headings, the version line, paragraphs,
`- ` lists (continued by indented lines), `**bold**`, a `---` rule and bare
addresses. A getmekno.com address becomes a link to itself; any other
address stays plain text, so the pages link no outside host (the site's
no-outside-host rule, `tests/test_phase408_site.py`).

`tests/test_phase408_site.py` imports this file and holds the committed
pages to `render_legal`'s output, so a change to `docs/legal/` that is not
rebuilt fails the suite. It reads no network and writes nothing unless
asked to.
"""

from __future__ import annotations

import datetime as dt
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
LEGAL = ROOT / "docs" / "legal"
ORIGIN = "https://getmekno.com"

#: The four pages a search engine may index, in the sitemap's order.
INDEXABLE = ("index.html", "support/index.html", "terms/index.html", "privacy/index.html")

#: Each built page: its source, its address, its title and its description
#: (titles 30 to 60 characters, descriptions 110 to 160: the request, item 5).
LEGAL_PAGES = {
    "terms/index.html": {
        "source": "terms.md",
        "path": "/terms/",
        "title": "Terms of Service · Mekno, for motorcycle shops",
        "description": ("The terms for using the Mekno app and getmekno.com: your account, "
                        "who decides on a repair, the shop's data, paying and cancelling, "
                        "and our limits."),
    },
    "privacy/index.html": {
        "source": "privacy.md",
        "path": "/privacy/",
        "title": "Privacy policy · Mekno, for motorcycle shops",
        "description": ("What Mekno keeps, why, which services it goes to, how long it is kept, "
                        "and how a shop takes its data out or has it deleted. "
                        "The shop's data is the shop's."),
    },
}

VERSION_LINE = re.compile(r"^Version \d+\.\d+ — \d{4}-\d{2}-\d{2}$")
URL = re.compile(r"https?://[^\s()<>]+[^\s()<>.,;:]")
BOLD = re.compile(r"\*\*(.+?)\*\*")

BRAND = ('      <a class="brand" href="/" aria-label="Mekno home">\n'
         '        <svg viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" '
         'rx="16" fill="#e8590c"/><path d="M14 46V20l9 0 9 13 9-13 9 0v26h-8V31l-10 14-10-14v15z" '
         'fill="#fff"/></svg>\n'
         '        mekno\n'
         '      </a>\n')
FOOTER = ('  <footer class="site">\n'
          '    <div class="wrap">\n'
          '      <span>© 2026 Mekno</span>\n'
          '      <span><a href="/privacy/">Privacy</a><a href="/terms/">Terms</a>'
          '<a href="/support/">Support</a></span>\n'
          '    </div>\n'
          '  </footer>\n')


def attr(value: str) -> str:
    """A value for a double-quoted attribute."""
    return html.escape(value, quote=False).replace('"', "&quot;")


def head(*, title: str, description: str, path: str) -> str:
    """The `<head>` of an indexable page: canonical and Open Graph included."""
    url = ORIGIN + path
    return ("<head>\n"
            '  <meta charset="utf-8">\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"  <title>{html.escape(title, quote=False)}</title>\n"
            f'  <meta name="description" content="{attr(description)}">\n'
            f'  <link rel="canonical" href="{url}">\n'
            f'  <meta property="og:title" content="{attr(title)}">\n'
            f'  <meta property="og:description" content="{attr(description)}">\n'
            f'  <meta property="og:url" content="{url}">\n'
            '  <meta property="og:type" content="website">\n'
            '  <meta property="og:site_name" content="Mekno">\n'
            f'  <meta property="og:image" content="{ORIGIN}/og.png">\n'
            '  <link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
            '  <link rel="stylesheet" href="/styles.css">\n'
            "</head>\n")


def inline(text: str) -> str:
    """Escape a run of text, then mark up its bold and its getmekno.com addresses."""
    out: list[str] = []
    pos = 0
    for m in URL.finditer(text):
        out.append(html.escape(text[pos:m.start()], quote=False))
        url = m.group(0)
        shown = html.escape(url, quote=False)
        if url.startswith(ORIGIN + "/") or url == ORIGIN:
            out.append(f'<a href="{attr(url)}">{shown}</a>')
        else:
            out.append(shown)
        pos = m.end()
    out.append(html.escape(text[pos:], quote=False))
    return BOLD.sub(r"<strong>\1</strong>", "".join(out))


def blocks(markdown: str) -> list[tuple[str, str]]:
    """The Markdown as (kind, text) blocks: h1, version, h2, p, li, hr."""
    found: list[tuple[str, str]] = []
    para: list[str] = []
    item: list[str] | None = None

    def flush() -> None:
        nonlocal item
        if para:
            found.append(("p", " ".join(para)))
            para.clear()
        if item is not None:
            found.append(("li", " ".join(item)))
            item = None

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line:
            flush()
        elif line.startswith("## "):
            flush()
            found.append(("h2", line[3:].strip()))
        elif line.startswith("# "):
            flush()
            found.append(("h1", line[2:].strip()))
        elif line == "---":
            flush()
            found.append(("hr", ""))
        elif VERSION_LINE.match(line):
            flush()
            found.append(("version", line))
        elif line.startswith("- "):
            flush()
            item = [line[2:].strip()]
        elif item is not None and raw.startswith("  "):
            item.append(line.strip())
        else:
            if item is not None:
                flush()
            para.append(line.strip())
    flush()
    return found


def body(markdown: str) -> str:
    """The page's main column, from the Markdown's blocks."""
    lines: list[str] = []
    in_list = False
    for kind, text in blocks(markdown):
        if kind == "li" and not in_list:
            lines.append("      <ul>")
            in_list = True
        elif kind != "li" and in_list:
            lines.append("      </ul>")
            in_list = False
        if kind == "h1":
            lines.append(f"      <h1>{inline(text)}</h1>")
        elif kind == "version":
            lines.append(f'      <p class="updated">{inline(text)}</p>')
        elif kind == "h2":
            lines.append("")
            lines.append(f"      <h2>{inline(text)}</h2>")
        elif kind == "li":
            lines.append(f"        <li>{inline(text)}</li>")
        elif kind == "hr":
            lines.append("")
            lines.append("      <hr>")
        else:
            lines.append(f"      <p>{inline(text)}</p>")
    if in_list:
        lines.append("      </ul>")
    return "\n".join(lines) + "\n"


def render_legal(page: str) -> str:
    """One built page, as `site/<page>` must hold it."""
    spec = LEGAL_PAGES[page]
    markdown = (LEGAL / spec["source"]).read_text(encoding="utf-8")
    return ("<!doctype html>\n"
            '<html lang="en">\n'
            + head(title=spec["title"], description=spec["description"], path=spec["path"])
            + "<body>\n"
            '  <header class="site">\n'
            '    <div class="wrap">\n'
            + BRAND
            + "    </div>\n"
            "  </header>\n"
            '  <main class="page">\n'
            '    <div class="wrap prose">\n'
            + body(markdown)
            + "    </div>\n"
            "  </main>\n"
            + FOOTER
            + "</body>\n"
            "</html>\n")


def markdown_words(markdown: str) -> list[str]:
    """The words a reader sees in the Markdown: its syntax taken off."""
    words: list[str] = []
    for _kind, text in blocks(markdown):
        words.extend(BOLD.sub(r"\1", text).split())
    return words


def page_url(page: str) -> str:
    return ORIGIN + "/" + page.removesuffix("index.html")


def last_changed(page: str, *, root: Path = ROOT) -> str:
    """The date `site/<page>` last changed in git; today if it is changed now."""
    rel = f"site/{page}"
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", rel],
                           capture_output=True, text=True, check=True).stdout.strip()
    if dirty:
        return dt.datetime.now(dt.timezone.utc).date().isoformat()
    return subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%cs", "--", rel],
                          capture_output=True, text=True, check=True).stdout.strip()


def render_sitemap(dates: dict[str, str]) -> str:
    rows = "".join(f"  <url>\n    <loc>{page_url(p)}</loc>\n    <lastmod>{dates[p]}</lastmod>\n"
                   "  </url>\n" for p in INDEXABLE)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{rows}</urlset>\n")


def stale() -> list[str]:
    """The built pages whose committed bytes are not the build's output."""
    return [p for p in LEGAL_PAGES
            if (SITE / p).read_text(encoding="utf-8") != render_legal(p)]


def main(argv: list[str]) -> int:
    if argv == ["legal"]:
        for page in LEGAL_PAGES:
            (SITE / page).write_text(render_legal(page), encoding="utf-8")
            print(f"wrote site/{page}")
        return 0
    if argv == ["sitemap"]:
        (SITE / "sitemap.xml").write_text(
            render_sitemap({p: last_changed(p) for p in INDEXABLE}), encoding="utf-8")
        print("wrote site/sitemap.xml")
        return 0
    if argv == ["check"]:
        bad = stale()
        for page in bad:
            print(f"site/{page} is not the build's output: run scripts/site_build.py legal")
        return 1 if bad else 0
    print("\n".join(__doc__.strip().splitlines()[2:5]), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
