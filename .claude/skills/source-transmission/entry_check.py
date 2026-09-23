#!/usr/bin/env python3
"""Reject bad evidence before it reaches refute. No model.

Each finding the source stage returns is checked against the DOCUMENT, not
against the model's account of it. A quote the document does not contain
is not evidence, however well it reads. Rejection classes, one per trap:

| id | rejects | why it exists |
|---|---|---|
| E1 | a `found` finding without quote, document, page, or kind | a claim with no citation |
| E2 | evidence that is not a maker document (marketing, forum, dealer, mirror) | the SOP's source ladder |
| E3 | a quote the document does not contain, whitespace-normalised | fabricated or garbled-OCR quotes |
| E4 | a document that never names the machine | recycled headers: another model's manual, or a template page |
| E5 | a quote under four words, or with no transmission term | single table cells ("Manual") |
| E6 | a transmission value outside the six, or both a value and a candidate set | classification contract |
| E7 | a blocked / not-found outcome carrying a value, or without the URL tried | never guess past a block |
| E8 | OCR-sourced evidence not flagged for a page-image check | the Grom: OCR is not evidence |

Usage:  entry_check.py FINDINGS.json [--docs-root DIR]
"""
from __future__ import annotations

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


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def _names(text: str, aliases: list[str]) -> bool:
    t = " " + re.sub(r"[^a-z0-9]+", " ", text.lower()) + " "
    return any(" " + re.sub(r"[^a-z0-9]+", " ", a.lower()).strip() + " " in t for a in aliases if a.strip())


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
    text = doc.read_text(encoding="utf-8", errors="ignore") if doc.is_file() else None
    if text is None:
        fails.append(f"E3 {tag}: document not readable at {doc}")
    else:
        if _norm(quote) not in _norm(text):
            fails.append(f"E3 {tag}: the document does not contain the quote")
        if not _names(text, [f.get("spelling", "")] + list(f.get("aliases") or [])):
            fails.append(f"E4 {tag}: the document never names the machine")
    if f.get("ocr") and not f.get("needs_page_image"):
        fails.append(f"E8 {tag}: OCR-sourced evidence not flagged for a page-image check")
    return fails


def check(findings: list[dict], docs_root: pathlib.Path) -> list[str]:
    return [x for f in findings for x in check_one(f, docs_root)]


REJECTION_IDS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8")


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
