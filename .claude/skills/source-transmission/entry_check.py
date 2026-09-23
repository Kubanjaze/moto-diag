#!/usr/bin/env python3
"""Reject bad evidence before it reaches refute. No model.

Each finding the source stage returns is checked against the DOCUMENT, not
against the model's account of it. A quote the document does not contain
is not evidence, however well it reads. And since Phase 257's Honda batch,
"the document" means the ORIGINAL a copy claims to come from: a file the
model saved under ./evidence/ is a copy it controls, and a check that
string-matches against the copy verifies nothing but the model's own
work (F141). Rejection classes, one per trap:

| id | rejects | why it exists |
|---|---|---|
| E1 | a `found` finding without quote, document, page, or kind | a claim with no citation |
| E2 | evidence that is not a maker document (marketing, forum, dealer, mirror); for a library file the kind is `library_index`'s, never the model's | the SOP's source ladder; a model's declared kind is its own account |
| E3 | a quote the ORIGINAL does not contain, whitespace-normalised | fabricated or garbled-OCR quotes, and doctored copies: a quote present in the saved copy but absent from its declared original |
| E4 | an original that never names the machine — and for a common word or bare number ("Bolt", "One", "1000"), never names it AS A MODEL: after the make, as a lookup alias, in the title, or in the file name | recycled headers; Yamaha "Bolt" matched the Zuma 125 manual's fasteners |
| E5 | a quote under four words, or with no transmission term | single table cells ("Manual") |
| E6 | a transmission value outside the six, or both a value and a candidate set | classification contract |
| E7 | a blocked / not-found outcome carrying a value, or without the URL tried | never guess past a block |
| E8 | OCR-sourced evidence not flagged for a page-image check | the Grom: OCR is not evidence |
| E9 | an evidence copy with no provenance: missing/invalid sidecar, unreadable original, a URL with no pinned fetch, or a sha256 that does not match | the saved copy is not the evidence; the original is (F141) |
| E10 | (when the excerpts handed to the source stage are given) a document that is not one of them, or a quote that is not inside them | the source stage reads only `candidates.py`'s excerpts; E9 alone accepted "originals" the model wrote itself (F141, reopened) |
| E11 | an acquired library file whose sidecar is missing, whose bytes changed, or that is neither on the make's own host nor linked from an unchanged maker-host page in the library | provenance is the script's record; makers host their own manuals elsewhere (SYM's Wolf 150 on Dropbox) |

A document under `evidence/` must carry a sibling `<file>.provenance.json`:

    {"original": "<absolute on-disk path, path relative to the sidecar, or URL>",
     "original_sha256": "<sha256 hex of the original bytes>",
     "fetched_as": "<sibling filename holding the bytes fetched from the URL>"}

E9 is weaker than it reads: the model writes the sidecar, so an
"original" can be a second file it wrote, and a URL's `fetched_as` is its
own bytes. Since the token redesign the batch source stage has no tools
and writes nothing; E10 is what binds its findings to documents it did
not author — the library files `candidates.py` excerpted.

`fetched_as` is required only for a URL original: entry_check is a no-model,
offline check and cannot re-fetch, so the fetch must be pinned by hash
next to the copy. The original's text is extracted HERE — HTML→text in
this file, `.txt` read raw, PDF via pypdf — and E3/E4 match against that,
never against the copy. Documents cited by absolute path outside
`evidence/` (the on-disk library) are originals already and are read
directly.

Usage:  entry_check.py FINDINGS.json [--docs-root DIR] [--excerpts CANDIDATES.json]
"""
from __future__ import annotations

import hashlib
import html as _html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library_index  # noqa: E402

SIX = {"manual", "cvt", "dct", "semi_auto_centrifugal", "semi_auto_actuated", "direct_drive"}
MAKER_KINDS = {"owners_manual", "service_manual", "workshop_manual", "spec_sheet", "maker_spec_page"}
TRANSMISSION_TERMS = re.compile(
    r"transmission|gearbox|gear ?shift|shift pedal|clutch|speed|v-?matic|cvt|variator|"
    r"dct|dual clutch|y-?amt|centrifugal|constant mesh|belt|drive", re.I)
OUTCOMES = {"found", "blocked", "not_found", "no_evidence"}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


# How a document names each make. A make's bare name where it is a safe
# word; otherwise its full name — "Genuine" alone is every manual's
# "genuine parts", "Zero" and "One" are ordinary words.
MAKE_NAMES: dict[str, tuple[str, ...]] = {
    "Harley-Davidson": ("harley davidson", "harley"),
    "MV Agusta": ("mv agusta",),
    "Moto Guzzi": ("moto guzzi", "guzzi"),
    "Genuine": ("genuine scooter", "genuine scooters", "genuinescooters", "genuine scooter co"),
    "Zero": ("zero motorcycles", "zero motorcycle", "zeromotorcycles"),
    "Damon": ("damon motorcycles", "damon motors", "damon"),
    "SYM": ("sym", "sanyang"),
    "Kymco": ("kymco", "kwang yang"),
    "LiveWire": ("livewire", "live wire"),
    "Vespa": ("vespa",),
    "Piaggio": ("piaggio",),
}


def _key(s: str) -> str:
    """Lower-case words, letters split from digits: 'CR300i' ~ 'CR 300i'."""
    s = re.sub(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])", " ", (s or "").lower())
    return " " + " ".join(re.sub(r"[^a-z0-9]+", " ", s).split()) + " "


def make_names(make: str) -> list[str]:
    """The make's names as _key strings."""
    return [_key(n) for n in MAKE_NAMES.get(make, (make,))]


def names_make(text_key: str, make: str) -> bool:
    """Does text (already through _key) name the make as a word?"""
    return any(n in text_key for n in make_names(make))


def weak_spelling(spelling: str) -> bool:
    """A spelling that can be an ordinary word or a bare number.

    Strong: a token mixing letters and digits (ZX-10R, CR300i) or two real
    words (Speed Triple). Weak: everything else — Bolt, One, 1000, RS,
    Monster 821, Tiger 900, K-Pipe.
    """
    toks = re.findall(r"[A-Za-z0-9]+", spelling or "")
    mixed = any(re.search(r"[A-Za-z]", t) and re.search(r"\d", t) for t in toks)
    words = [t for t in toks if t.isalpha() and len(t) >= 3]
    return not mixed and len(words) < 2


TITLE_LINES = 3                     # a document's title is its first lines, not its first page


def _lookup_aliases(make: str, spelling: str) -> list[str]:
    """Strong aliases of a lookup entry this spelling already belongs to."""
    try:
        sys.path.insert(0, str(HERE.parents[2] / "src"))
        from motodiag.knowledge.transmission import TRANSMISSION_LOOKUP
    except Exception:
        return []
    sk = _key(spelling)
    out = []
    for e in TRANSMISSION_LOOKUP:
        names = [e.canonical, *e.aliases]
        if e.make == make and any(_key(n) == sk for n in names):
            out += [n for n in names if not weak_spelling(n)]
    return out


def named_as_model(text: str, doc: pathlib.Path, make: str, spelling: str) -> bool:
    """The document names this spelling as a model of this make, not as a word."""
    sk = _key(spelling)
    tk = _key(text)
    if any(n[:-1] + sk in tk for n in make_names(make)):
        return True                                             # "Yamaha Bolt"
    if any(_key(a) in tk for a in _lookup_aliases(make, spelling)):
        return True                                             # a model code the lookup holds
    title = [x for x in text.splitlines()
             if x.strip() and not re.match(r"^\W*(PDF)?PAGE\W*\d+\W*$", x.strip(), re.I)][:TITLE_LINES]
    return sk in _key(" ".join(title)) or sk in _key(doc.name)  # the document's own title or name


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def _names(text: str, aliases: list[str]) -> bool:
    t = " " + re.sub(r"[^a-z0-9]+", " ", text.lower()) + " "
    return any(" " + re.sub(r"[^a-z0-9]+", " ", a.lower()).strip() + " " in t for a in aliases if a.strip())


def _extract_text(path: pathlib.Path) -> str | None:
    """Text of the ORIGINAL bytes. HTML→text is done here, not by the model.

    Returns None for anything entry_check cannot read honestly — an
    unsupported type, or a PDF with no pypdf to open it. None is a
    rejection (E9), never a silent pass.
    """
    suffix = path.suffix.lower()
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if suffix in (".html", ".htm", ".xhtml"):
        src = raw.decode("utf-8", errors="ignore")
        src = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", src)
        src = re.sub(r"(?s)<[^>]*>", " ", src)
        return _html.unescape(src)
    if suffix in (".txt", ".text"):
        return raw.decode("utf-8", errors="ignore")
    if suffix == ".pdf":
        try:
            import pypdf
        except ImportError:
            return None
        try:
            return "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(path).pages)
        except Exception:
            return None
    return None


def _is_evidence_copy(doc: pathlib.Path, docs_root: pathlib.Path) -> bool:
    """True when the cited document is a copy the model saved under evidence/.

    Relative-to-clone paths starting at `evidence/`, and absolute paths
    inside the clone's evidence/ dir, are copies. An absolute path
    elsewhere (the on-disk library) is an original already.
    """
    try:
        rel = doc.resolve().relative_to(docs_root.resolve())
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] == "evidence"


def _original_text(doc: pathlib.Path, tag: str, fails: list[str]) -> str | None:
    """Text of the declared original behind a copy, or None with E9 fails.

    The copy itself is never read: it exists for humans and refute, not
    for this check.
    """
    side = doc.with_name(doc.name + ".provenance.json")
    try:
        prov = json.loads(side.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        prov = None
    if not isinstance(prov, dict):
        fails.append(f"E9 {tag}: evidence copy {doc.name} has no readable "
                     f"{doc.name}.provenance.json declaring its original and its sha256")
        return None
    original = str(prov.get("original") or "").strip()
    sha = str(prov.get("original_sha256") or "").strip().lower()
    if not original or not SHA_RE.match(sha):
        fails.append(f"E9 {tag}: the provenance sidecar needs an 'original' and "
                     "a 64-hex 'original_sha256'")
        return None
    if original.startswith(("http://", "https://")):
        fetched = str(prov.get("fetched_as") or "").strip()
        if not fetched:
            fails.append(f"E9 {tag}: a URL original needs 'fetched_as' — the saved "
                         "fetch this check can hash and read offline")
            return None
        src = pathlib.Path(fetched)
        src = src if src.is_absolute() else doc.parent / src
    else:
        src = pathlib.Path(original)
        src = src if src.is_absolute() else doc.parent / src
    if not src.is_file():
        fails.append(f"E9 {tag}: the declared original is not readable at {src}")
        return None
    actual = hashlib.sha256(src.read_bytes()).hexdigest()
    if actual != sha:
        fails.append(f"E9 {tag}: sha256 of {src.name} is {actual}, the sidecar "
                     f"declares {sha} — the original changed, or the pin is wrong")
        return None
    text = _extract_text(src)
    if text is None:
        fails.append(f"E9 {tag}: cannot extract text from the original {src.name} "
                     "(unsupported type, or no pypdf for a PDF)")
        return None
    return text


def _in_excerpts(f: dict, doc: pathlib.Path, excerpts: dict, tag: str) -> list[str]:
    """E10: the document is one the source stage was handed, and so is the quote."""
    mine = [e for e in excerpts.get(f.get("spelling"), [])
            if pathlib.Path(e["document"]).resolve() == doc.resolve()]
    if not mine:
        return [f"E10 {tag}: {doc} is not one of the excerpts supplied for this spelling"]
    if not any(_norm(f["quote"]) in _norm(e["text"]) for e in mine):
        return [f"E10 {tag}: the quote is not inside the excerpts supplied from {doc.name}"]
    return []


def _sha256(path: pathlib.Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def acquired_provenance(doc: pathlib.Path, library: pathlib.Path, make: str, tag: str) -> list[str]:
    """E11: an acquired file's provenance, as acquire.py recorded it.

    The sidecar `<file>.acquired.json` carries `url`, `final_url`, `sha256`,
    `fetched_at` and `referrer` (`url`, `path` in the library, `sha256`, or
    null). The file must still hash to `sha256`. It counts as the make's
    document when `final_url` is on one of the make's own hosts, or — for a
    file hosted elsewhere, like SYM's Dropbox-hosted Wolf 150 manual — when
    its referrer is a page on a maker host, itself in the library, unchanged
    since it was saved, and linking to `url`. No network: everything is on
    disk.
    """
    side = doc.with_name(doc.name + ".acquired.json")
    try:
        prov = json.loads(side.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [f"E11 {tag}: {doc.name} has no readable {side.name}"]
    if not isinstance(prov, dict) or not prov.get("url") or not SHA_RE.match(str(prov.get("sha256", ""))):
        return [f"E11 {tag}: {side.name} needs 'url' and a 64-hex 'sha256'"]
    if _sha256(doc) != prov["sha256"]:
        return [f"E11 {tag}: {doc.name} no longer hashes to the sha256 recorded when it was fetched"]
    if library_index.maker_host(prov.get("final_url") or prov["url"], make):
        return []
    ref = prov.get("referrer")
    if not isinstance(ref, dict) or not ref.get("url"):
        return [f"E11 {tag}: {doc.name} is not on a {make} host and has no referrer on one"]
    if not library_index.maker_host(ref["url"], make):
        return [f"E11 {tag}: the referrer {ref['url']} is not on a {make} host"]
    page = library / str(ref.get("path", ""))
    if not ref.get("path") or not page.is_file():
        return [f"E11 {tag}: the referrer page is not in the library at {ref.get('path')!r}"]
    if _sha256(page) != ref.get("sha256"):
        return [f"E11 {tag}: the referrer page {page.name} has changed since it was recorded"]
    src = _html.unescape(page.read_bytes().decode("utf-8", errors="ignore"))
    url = prov["url"]
    if url not in src and url.replace(" ", "%20") not in src:
        return [f"E11 {tag}: the referrer page {page.name} does not link to {url}"]
    return []


def check_one(f: dict, docs_root: pathlib.Path, excerpts: dict | None = None,
              library: pathlib.Path = library_index.LIBRARY) -> list[str]:
    fails: list[str] = []
    tag = f"{f.get('make')} | {f.get('spelling')}"
    outcome = f.get("outcome")
    if outcome not in OUTCOMES:
        return [f"E6 {tag}: outcome {outcome!r} is not one of {sorted(OUTCOMES)}"]

    if outcome in ("blocked", "not_found"):
        if f.get("transmission") or f.get("candidates"):
            fails.append(f"E7 {tag}: a {outcome} finding carries a classification")
        if not str(f.get("url_tried", "")).startswith("http") and not f.get("document"):
            fails.append(f"E7 {tag}: a {outcome} finding does not name what was tried")
        return fails
    if outcome == "no_evidence":
        if f.get("transmission") or f.get("candidates"):
            fails.append(f"E6 {tag}: no_evidence must stay NULL")
        return fails

    # outcome == "found"
    missing = [k for k in ("quote", "document", "page", "evidence_kind") if not f.get(k)]
    if missing:
        return [f"E1 {tag}: missing {missing}"]
    doc = pathlib.Path(f["document"])
    doc = doc if doc.is_absolute() else docs_root / doc
    indexed = library_index.kind(doc, library)
    if indexed != "not_library":
        # A library file's kind is the index's; what the model declared is not consulted.
        if indexed not in library_index.MAKER_KINDS:
            fails.append(f"E2 {tag}: the library index classes {doc.name} as {indexed}, not a maker document")
        elif indexed == "acquired":
            fails += acquired_provenance(doc, library, f.get("make", ""), tag)
    elif f["evidence_kind"] not in MAKER_KINDS:
        fails.append(f"E2 {tag}: evidence kind {f['evidence_kind']!r} is not a maker document")

    value, cands = f.get("transmission"), f.get("candidates") or []
    if bool(value) == bool(cands):
        fails.append(f"E6 {tag}: exactly one of transmission / candidates")
    elif value and value not in SIX or any(c not in SIX for c in cands):
        fails.append(f"E6 {tag}: value outside the six")

    quote = f["quote"]
    if len(quote.split()) < 4 or not TRANSMISSION_TERMS.search(quote):
        fails.append(f"E5 {tag}: quote is a fragment, not a statement: {quote!r}")

    if excerpts is not None:
        fails += _in_excerpts(f, doc, excerpts, tag)
    if _is_evidence_copy(doc, docs_root):
        # F141: a copy the model saved is not the evidence. The quote is
        # matched against the ORIGINAL the copy's sidecar declares.
        text = _original_text(doc, tag, fails)
    elif doc.is_file():
        # A library original: HTML is matched as text, as candidates.py showed it.
        text = _extract_text(doc)
        if text is None:
            fails.append(f"E3 {tag}: cannot extract text from {doc}")
    else:
        text = None
        fails.append(f"E3 {tag}: document not readable at {doc}")
    if text is not None:
        if _norm(quote) not in _norm(text):
            fails.append(f"E3 {tag}: the document does not contain the quote")
        if not _names(text, [f.get("spelling", "")] + list(f.get("aliases") or [])):
            fails.append(f"E4 {tag}: the document never names the machine")
        elif weak_spelling(f.get("spelling", "")) and not named_as_model(
                text, doc, f.get("make", ""), f.get("spelling", "")):
            fails.append(f"E4 {tag}: {f.get('spelling')!r} is a common word or bare number and the "
                         f"document never names it as a {f.get('make')} model (after the make, as a "
                         "lookup alias, in its title or its file name)")
    if f.get("ocr") and not f.get("needs_page_image"):
        fails.append(f"E8 {tag}: OCR-sourced evidence not flagged for a page-image check")
    return fails


def check(findings: list[dict], docs_root: pathlib.Path, excerpts: dict | None = None,
          library: pathlib.Path = library_index.LIBRARY) -> list[str]:
    return [x for f in findings for x in check_one(f, docs_root, excerpts, library)]


REJECTION_IDS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10", "E11")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.split("Usage:")[1].strip(), file=sys.stderr)
        return 2
    path = pathlib.Path(argv[0])
    root = pathlib.Path(argv[argv.index("--docs-root") + 1]) if "--docs-root" in argv else path.parent
    excerpts = (json.loads(pathlib.Path(argv[argv.index("--excerpts") + 1]).read_text(encoding="utf-8"))
                if "--excerpts" in argv else None)
    fails = check(json.loads(path.read_text(encoding="utf-8")), root, excerpts)
    for x in fails:
        print(x)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
