#!/usr/bin/env python3
"""Candidates — the library excerpts a source stage is allowed to read.

No model. For each spelling, find the on-disk library files that name it
and cut out only the matching passages: the hit line **±40 lines**, with
the file's absolute path and the page the hit sits on. A file whose own
NAME names the spelling (`Wolf_CR300i_Owners_Manual.pdf.txt`) is about
that machine throughout, so its gearbox lines are anchors too — an owner's
manual rarely repeats the model name on its gear-change page. Those
excerpts say `anchor: "file"`; the rest `anchor: "name"`. The source stage
then gets those excerpts and nothing else — one turn, no tools — so what
it costs is bounded by what this file hands it, not by how long a model
chooses to browse. The agent-loop source stage it replaces measured
~2.4M tokens per spelling; Kymco's one spelling measured 7.66M.

What is read: `*.txt` and HTML (HTML→text by `entry_check._extract_text`,
the same code E3 verifies quotes with). What is not: the project's own
artefacts that live in the library folder — phase notes (`250_*`), logs,
past refute output, virtualenvs. They are the project talking to itself,
not maker documents. Nor is anything over MAX_BYTES.

Pages come from the extract's own markers (`=== PAGE N ===`, `===PAGE N===`,
`===== PAGE N =====`, `<<<PAGE N>>>`) or form feeds; an HTML page or an
unmarked text has no page and is cited by its lines. Blank lines are
dropped and lines longer than LONG_LINE wrapped (HTML→text is mostly
blank lines, or one very long one), so ±40 lines is ±40 lines of text,
and line numbers refer to the extracted text, not the file.

Usage:  candidates.py SPELLING [SPELLING ...] [--make MAKE] [--library DIR] [--json]
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import textwrap

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from entry_check import _extract_text  # noqa: E402

LIBRARY = pathlib.Path.home() / "research" / "motodiag"
CONTEXT = 40                 # lines either side of a hit
MAX_EXCERPTS = 8             # per spelling
MAX_CHARS = 40_000           # per spelling, all excerpts together
LONG_LINE = 400
WRAP = 200
MAX_BYTES = 32 * 2**20       # larger is a database dump (NHTSA's flat recall
                             # file is 311 MB), not a maker document; the
                             # largest maker page on disk is 16 MB

SUFFIXES = {".txt", ".html", ".htm"}
SKIP_DIRS = {".git", ".venv", "venv", "site-packages", "__pycache__", "node_modules", "refute"}
# Phase artefacts (250_regression.txt, 257B_…) and fetch/crawl logs.
SKIP_NAME = re.compile(r"^\d{3}[A-Z]?_|(^|[_.-])log[_.-]|fetchlog", re.I)
# What a gearbox passage says. Narrower than entry_check's TRANSMISSION_TERMS,
# which also admits 'drive' and 'belt' — words every recall notice uses.
GEARBOX = re.compile(r"transmission|gearbox|gear ?shift|shift pedal|clutch|\d-speed|speeds?\b|"
                     r"v-?matic|cvt|variator|dct|dual clutch|centrifugal|constant mesh", re.I)
PAGE_MARK = re.compile(r"^\s*(?:=+|<<<)\s*PAGE\s+(\d+)\s*(?:=+|>>>)\s*$", re.I)


def _key(s: str) -> str:
    """Lower-case words, letters split from digits: 'CR300i' ~ 'CR 300i'."""
    s = re.sub(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])", " ", s.lower())
    return " " + " ".join(re.sub(r"[^a-z0-9]+", " ", s).split()) + " "


def documents(library: pathlib.Path) -> list[pathlib.Path]:
    out = []
    for p in library.rglob("*"):
        rel = p.relative_to(library)
        if (p.suffix.lower() in SUFFIXES and p.is_file()
                and not SKIP_DIRS.intersection(rel.parts[:-1])
                and not SKIP_NAME.search(p.name)
                and p.stat().st_size <= MAX_BYTES):
            out.append(p)
    return sorted(out)


def _lines(text: str) -> tuple[list[str], list[int | None]]:
    """Display lines and the page each one is on (None when unmarked)."""
    lines: list[str] = []
    pages: list[int | None] = []
    marked = bool(re.search(PAGE_MARK.pattern, text, re.I | re.M))
    page: int | None = 1 if ("\f" in text and not marked) else None
    for raw in text.split("\n"):
        m = PAGE_MARK.match(raw)
        if m:
            page = int(m.group(1))
        # A form feed ends a page: what follows it on the line is the next page.
        for n, seg in enumerate(raw.split("\f")):
            if n and not marked:
                page = (page or 1) + 1
            chunks = textwrap.wrap(" ".join(seg.split()), WRAP) if len(seg) > LONG_LINE else [seg]
            for c in chunks:
                if c.strip():
                    lines.append(c.rstrip("\r"))
                    pages.append(page)
    return lines, pages


def candidates(spellings: list[str], library: pathlib.Path = LIBRARY, *,
               make: str | None = None,
               aliases: dict[str, list[str]] | None = None) -> dict[str, list[dict]]:
    """{spelling: [excerpt]} — an empty list means no library file names it."""
    keys = {s: {_key(a) for a in [s, *((aliases or {}).get(s) or [])] if a.strip()}
            for s in spellings}
    hits: dict[str, list[tuple]] = {s: [] for s in spellings}
    make_key = _key(make) if make else None
    for doc in documents(library):
        text = _extract_text(doc)
        if not text:
            continue
        low = _key(text)
        wanted = [s for s in spellings if any(k in low for k in keys[s])]
        if not wanted:
            continue
        lines, pages = _lines(text)
        line_keys = [_key(x) for x in lines]
        names_make = bool(make_key and make_key in low)
        file_key = _key(doc.name)
        for s in wanted:
            about = any(k in file_key for k in keys[s])
            for i, lk in enumerate(line_keys):
                by_name = any(k in lk for k in keys[s])
                if by_name or (about and GEARBOX.search(lines[i])):
                    lo, hi = max(0, i - CONTEXT), min(len(lines), i + CONTEXT + 1)
                    window = "\n".join(lines[lo:hi])
                    # A file naming the make first, then the passage that says
                    # most about a gearbox: a spec table beats a model list.
                    terms = {t.lower() for t in GEARBOX.findall(window)}
                    dense = sum(bool(GEARBOX.search(x)) for x in lines[lo:hi])
                    rank = (not names_make, -len(terms), -dense, str(doc), i)
                    hits[s].append((rank, doc, i, lo, hi, window, pages[i],
                                    "name" if by_name else "file"))
    out: dict[str, list[dict]] = {}
    for s in spellings:
        taken: list[dict] = []
        spans: dict[pathlib.Path, list[tuple[int, int]]] = {}
        seen: set[str] = set()
        used = 0
        for rank, doc, i, lo, hi, window, page, anchor in sorted(hits[s], key=lambda h: h[0]):
            if len(taken) >= MAX_EXCERPTS:
                break
            if any(a <= i < b for a, b in spans.get(doc, [])):
                continue            # already inside a taken excerpt of this file
            if window in seen or used + len(window) > MAX_CHARS:
                continue            # a duplicate file's copy, or too big for what is left
            seen.add(window)
            spans.setdefault(doc, []).append((lo, hi))
            used += len(window)
            taken.append({"document": str(doc), "page": page, "lines": f"{lo + 1}-{hi}",
                          "hit_line": i + 1, "anchor": anchor, "text": window})
        out[s] = taken
    return out


def main(argv: list[str]) -> int:
    opts = {"--make": None, "--library": str(LIBRARY)}
    rest = []
    it = iter(argv)
    for a in it:
        if a in opts:
            opts[a] = next(it)
        elif a != "--json":
            rest.append(a)
    if not rest:
        print(__doc__.split("Usage:")[1].strip(), file=sys.stderr)
        return 2
    result = candidates(rest, pathlib.Path(opts["--library"]), make=opts["--make"])
    if "--json" in argv:
        print(json.dumps(result, indent=1))
    else:
        for s, ex in result.items():
            print(f"{s}: {len(ex)} excerpt(s), {sum(len(e['text']) for e in ex)} chars")
            for e in ex:
                print(f"  {e['document']}  page {e['page']}  lines {e['lines']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
