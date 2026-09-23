#!/usr/bin/env python3
"""Candidates — the library excerpts a source stage is allowed to read.

No model. For each spelling, find the on-disk library files that name it
and cut out only the matching passages: the hit line **±40 lines**, with
the file's absolute path and the page the hit sits on. A file whose own
NAME names the spelling (`Wolf_CR300i_Owners_Manual.pdf.txt`) is about
that machine throughout, so its gearbox lines are anchors too — an owner's
manual rarely repeats the model name on its gear-change page. Those
excerpts say `anchor: "file"`; the rest `anchor: "name"`. A manual that a
manual route (`acquire.MANUAL_ROUTES`) fetched for a spelling is tied to it
by its sidecar's `for_spellings`, named or not — Yamaha's Vino 125 manual
prints only "YJ125Y" — and cut around its mechanism lines anywhere in the
text, never a table-of-contents line: `anchor: "route"`. The source stage
then gets those excerpts and nothing else — one turn, no tools — so what
it costs is bounded by what this file hands it, not by how long a model
chooses to browse. The agent-loop source stage it replaces measured
~2.4M tokens per spelling; Kymco's one spelling measured 7.66M.

What is read: `*.txt` and HTML (HTML→text by `entry_check._extract_text`,
the same code E3 verifies quotes with) that `library_index` classes as a
maker document, and that **names the make** (`entry_check.MAKE_NAMES`).
The make is a filter, not a rank: matching a spelling as a word in any
file sent Yamaha "Bolt" to the Zuma 125 manual's fasteners, Harley "One"
to a dealer page and Ducati "1000" to SYM scooter manuals. What is never
read: third-party mirrors, crawl dumps, recalls, unindexed files, the
project's own artefacts (phase notes `250_*`, logs, `refute/`,
virtualenvs), and anything over MAX_BYTES. The make filter cannot stop
"Bolt" in Yamaha's own Zuma manual; for a weak spelling (an ordinary word
or bare number) a document is read only where it names the spelling as a
model — `entry_check.named_as_model`, E4's rule.

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

import library_index  # noqa: E402
from entry_check import (_extract_text, _key, acquired_provenance, is_mechanism,  # noqa: E402
                         manual_route_pdf, named_as_model, names_make, toc_line, weak_spelling)

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


# A spec-table row: the label alone or first on its line, its value on the
# same line or the next non-empty one ("Transmission / 6-speed, return shift",
# "Transmission  CVT Automatic", "Gearbox 6-Speed").
SPEC_LABEL = re.compile(r"^\s*(?:transmission|gearbox)\b\W*(.*)$", re.I)
SPEC_VALUE = re.compile(r"\d\s*-?\s*speed|\bspeeds?\b|\bcvt\b|automatic|\bmanual\b|\bdct\b|dual.clutch|"
                        r"direct drive|single.speed|constant.mesh", re.I)


def spec_lines(lines: list[str]) -> list[int]:
    """Indexes of spec-table rows naming the gearbox."""
    out = []
    for i, line in enumerate(lines):
        m = SPEC_LABEL.match(line)
        if m and (SPEC_VALUE.search(m.group(1)) or (i + 1 < len(lines) and not m.group(1).strip()
                                                    and SPEC_VALUE.search(lines[i + 1]))):
            out.append(i)
    return out


def documents(library: pathlib.Path, maker_only: bool = True) -> list[pathlib.Path]:
    out = []
    for p in library.rglob("*"):
        rel = p.relative_to(library)
        if (p.suffix.lower() in SUFFIXES and p.is_file()
                and not SKIP_DIRS.intersection(rel.parts[:-1])
                and not SKIP_NAME.search(p.name)
                and p.stat().st_size <= MAX_BYTES
                and (not maker_only or library_index.kind(p, library) in library_index.MAKER_KINDS)):
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
    for doc in documents(library):
        text = _extract_text(doc)
        if not text:
            continue
        low = _key(text)
        if make and not names_make(low, make):
            continue                # a document that never names the make is not about its machines
        if (library_index.kind(doc, library) == "acquired"
                and (doc.suffix != ".txt" or not make or acquired_provenance(doc, library, make, ""))):
            continue                # acquired: read only its derived text, and only with provenance for this make (E11)
        # A spelling that is an ordinary word or a bare number ("Bolt", "1000")
        # counts only where the document names it as a model — the same rule
        # as E4, applied before the model is paid to read the excerpt.
        wanted = [s for s in spellings if any(k in low for k in keys[s])
                  and not (make and weak_spelling(s) and not named_as_model(text, doc, make, s))]
        # A manual a manual route fetched for a spelling is about that machine
        # throughout, whether or not it prints the name (operator, 2026-09-23):
        # the Vino 125 manual says only "YJ125Y". Its sidecar's for_spellings
        # ties it; its anchors are its mechanism lines, never a contents line.
        route = manual_route_pdf(doc, library, make, e11_passed=True) if make else None
        fetched_for = [s for s in spellings if route and s in (route[1].get("for_spellings") or [])]
        wanted += [s for s in fetched_for if s not in wanted]
        if not wanted:
            continue
        lines, pages = _lines(text)
        line_keys = [_key(x) for x in lines]
        file_key = _key(doc.name)
        specs = spec_lines(lines)
        for s in wanted:
            about = any(k in file_key for k in keys[s])
            # A document about this machine (its file name or its title
            # names it) gives its own spec line first,
            # ahead of every ranked window: the 2026 ZX-10R page's "Transmission
            # / 6-speed, return shift" sat 97 lines from any mention of the name
            # and lost on rank. Not "names it anywhere": every Suzuki page's menu
            # says "Suzuki GSX-R750", and the V-Strom's spec row is not the GSX-R's.
            # Its title is its FIRST line (HTML → text puts <title> first), not
            # the first few: a menu one line down names every machine the maker sells.
            title = _key(next((x for x in lines if not PAGE_MARK.match(x)), ""))
            if s in fetched_for:
                for i, line in enumerate(lines):
                    if toc_line(line) or not is_mechanism(line):
                        continue
                    lo, hi = max(0, i - CONTEXT), min(len(lines), i + CONTEXT + 1)
                    window = "\n".join(lines[lo:hi])
                    terms = {t.lower() for t in GEARBOX.findall(window)}
                    dense = sum(bool(GEARBOX.search(x)) for x in lines[lo:hi])
                    hits[s].append(((0, -len(terms), -dense, str(doc), i), doc, i, lo, hi, window,
                                    pages[i], "route"))
            if about or any(k in title for k in keys[s]):
                for i in specs:
                    lo, hi = max(0, i - CONTEXT), min(len(lines), i + CONTEXT + 1)
                    hits[s].append(((0,), doc, i, lo, hi, "\n".join(lines[lo:hi]), pages[i], "spec"))
            for i, lk in enumerate(line_keys):
                by_name = any(k in lk for k in keys[s])
                if by_name or (about and GEARBOX.search(lines[i])):
                    lo, hi = max(0, i - CONTEXT), min(len(lines), i + CONTEXT + 1)
                    window = "\n".join(lines[lo:hi])
                    # The passage that says most about a gearbox first: a spec
                    # table beats a model list.
                    terms = {t.lower() for t in GEARBOX.findall(window)}
                    dense = sum(bool(GEARBOX.search(x)) for x in lines[lo:hi])
                    rank = (1, -len(terms), -dense, str(doc), i)
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
