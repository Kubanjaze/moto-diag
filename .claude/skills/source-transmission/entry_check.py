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
| E2 | evidence that is not a maker document (marketing, forum, dealer, mirror) | the SOP's source ladder |
| E3 | a quote the ORIGINAL does not contain, whitespace-normalised | fabricated or garbled-OCR quotes, and doctored copies: a quote present in the saved copy but absent from its declared original |
| E4 | an original that never names the machine | recycled headers: another model's manual, or a template page |
| E5 | a quote under four words, or with no transmission term | single table cells ("Manual") |
| E6 | a transmission value outside the six, or both a value and a candidate set | classification contract |
| E7 | a blocked / not-found outcome carrying a value, or without the URL tried | never guess past a block |
| E8 | OCR-sourced evidence not flagged for a page-image check | the Grom: OCR is not evidence |
| E9 | an evidence copy with no provenance: missing/invalid sidecar, unreadable original, a URL with no pinned fetch, or a sha256 that does not match | the saved copy is not the evidence; the original is (F141) |

A document under `evidence/` must carry a sibling `<file>.provenance.json`:

    {"original": "<absolute on-disk path, path relative to the sidecar, or URL>",
     "original_sha256": "<sha256 hex of the original bytes>",
     "fetched_as": "<sibling filename holding the bytes fetched from the URL>"}

`fetched_as` is required only for a URL original: entry_check is a no-model,
offline check and cannot re-fetch, so the fetch must be pinned by hash
next to the copy. The original's text is extracted HERE — HTML→text in
this file, `.txt` read raw, PDF via pypdf — and E3/E4 match against that,
never against the copy. Documents cited by absolute path outside
`evidence/` (the on-disk library) are originals already and are read
directly.

Usage:  entry_check.py FINDINGS.json [--docs-root DIR]
"""
from __future__ import annotations

import hashlib
import html as _html
import json
import pathlib
import re
import sys

SIX = {"manual", "cvt", "dct", "semi_auto_centrifugal", "semi_auto_actuated", "direct_drive"}
MAKER_KINDS = {"owners_manual", "service_manual", "workshop_manual", "spec_sheet", "maker_spec_page"}
TRANSMISSION_TERMS = re.compile(
    r"transmission|gearbox|gear ?shift|shift pedal|clutch|speed|v-?matic|cvt|variator|"
    r"dct|dual clutch|y-?amt|centrifugal|constant mesh|belt|drive", re.I)
OUTCOMES = {"found", "blocked", "not_found", "no_evidence"}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


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


def check_one(f: dict, docs_root: pathlib.Path) -> list[str]:
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
    if f["evidence_kind"] not in MAKER_KINDS:
        fails.append(f"E2 {tag}: evidence kind {f['evidence_kind']!r} is not a maker document")

    value, cands = f.get("transmission"), f.get("candidates") or []
    if bool(value) == bool(cands):
        fails.append(f"E6 {tag}: exactly one of transmission / candidates")
    elif value and value not in SIX or any(c not in SIX for c in cands):
        fails.append(f"E6 {tag}: value outside the six")

    quote = f["quote"]
    if len(quote.split()) < 4 or not TRANSMISSION_TERMS.search(quote):
        fails.append(f"E5 {tag}: quote is a fragment, not a statement: {quote!r}")

    doc = pathlib.Path(f["document"])
    doc = doc if doc.is_absolute() else docs_root / doc
    if _is_evidence_copy(doc, docs_root):
        # F141: a copy the model saved is not the evidence. The quote is
        # matched against the ORIGINAL the copy's sidecar declares.
        text = _original_text(doc, tag, fails)
    elif doc.is_file():
        text = doc.read_text(encoding="utf-8", errors="ignore")
    else:
        text = None
        fails.append(f"E3 {tag}: document not readable at {doc}")
    if text is not None:
        if _norm(quote) not in _norm(text):
            fails.append(f"E3 {tag}: the document does not contain the quote")
        if not _names(text, [f.get("spelling", "")] + list(f.get("aliases") or [])):
            fails.append(f"E4 {tag}: the document never names the machine")
    if f.get("ocr") and not f.get("needs_page_image"):
        fails.append(f"E8 {tag}: OCR-sourced evidence not flagged for a page-image check")
    return fails


def check(findings: list[dict], docs_root: pathlib.Path) -> list[str]:
    return [x for f in findings for x in check_one(f, docs_root)]


REJECTION_IDS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.split("Usage:")[1].strip(), file=sys.stderr)
        return 2
    path = pathlib.Path(argv[0])
    root = pathlib.Path(argv[argv.index("--docs-root") + 1]) if "--docs-root" in argv else path.parent
    fails = check(json.loads(path.read_text(encoding="utf-8")), root)
    for x in fails:
        print(x)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
