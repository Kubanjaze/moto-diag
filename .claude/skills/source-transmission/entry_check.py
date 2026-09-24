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
| E12 | a `manual` finding whose quote names no rider-operated clutch, foot-shift pattern or the word "manual" | a gear count is not a mechanism: a DCT is a constant-mesh six-speed too (Ninja 650, killed; the standard had drifted) |
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
import unicodedata
import urllib.parse

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


def _folded_words(s: str) -> list[str]:
    """Words after NFKD, so an accent is split off its letter: 'Ténéré' →
    ['te', 'ne', 're'], which _names joins back to 'tenere'."""
    return re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", s or "").lower())


def _names(text: str, aliases: list[str]) -> bool:
    """E4: does the text name one of these spellings as the maker prints it?

    A run of whole words whose letters and digits are the spelling's
    (bug fix #6): Yamaha prints 'YZFR6', 'YZFR7' and 'Ténéré 700' for the
    typed 'YZF-R6', 'YZF-R7' and 'Tenere 700'. Never part of a word:
    'YZFR1M' does not name the YZF-R1, nor 'MT03T' the MT-03."""
    words = _folded_words(text)
    for a in aliases:
        target = "".join(_folded_words(a))
        if not target:
            continue
        for i, w in enumerate(words):
            acc, j = w, i
            while len(acc) < len(target) and target.startswith(acc) and j + 1 < len(words):
                j += 1
                acc += words[j]
            if acc == target:
                return True
    return False


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


# Words that, right after a model's name, make it a different model — each
# seen in this phase: KTM '1290 Super Duke GT', BMW 'F 800 GS' / 'S 1000 XR',
# Triumph '765 RS', '1200 RR', Zero 'SR/S', 'SR/F', Honda 'SP', 'SE', Ducati
# 'V4 R', KTM '890 Adventure R Rally', '450 SX-F', '300 XC', 'RC 390', 'Evo'.
# ABS is equipment, not a model, and is deliberately absent.
VARIANT_TOKENS = {"gt", "r", "rr", "rs", "s", "sp", "se", "x", "xr", "gs", "sx", "xc", "f", "rc",
                  "rally", "evo", "carbon",
                  # Transmissions — the variants that CHANGE the answer: Honda
                  # 'Africa Twin DCT', Yamaha 'MT-09 Y-AMT' (y, amt), Honda
                  # 'CB650R E-Clutch' (e). A DCT page never sources the manual.
                  "dct", "y", "amt", "e"}


def _words_of(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def names_model(text: str, spelling: str) -> bool:
    """Does text name THIS model — its words in a run, as the document
    spells them ('CR 300i' names 'CR300i'), not followed by a variant word?

    The 4609 over-claim, as a rule: 'F800' is not named by 'F 800 GS', nor
    '1290 Super Duke' by '1290 Super Duke GT', nor 'SR' by 'SR/S'. A page
    that only names a sibling or the family is family evidence."""
    target = "".join(_words_of(spelling))
    if not target:
        return False
    toks = _words_of(text)
    for i, t in enumerate(toks):
        if not target.startswith(t):
            continue
        acc, j = t, i
        while len(acc) < len(target) and j + 1 < len(toks) and target.startswith(acc + toks[j + 1]):
            j += 1
            acc += toks[j]
        if acc == target and (j + 1 >= len(toks) or toks[j + 1] not in VARIANT_TOKENS):
            return True
    return False


def abs_edition(text: str, spelling: str) -> bool:
    """Does text name '<exact model> ABS'? The operator's one named
    exception (2026-09-23): ABS is braking equipment, so an ABS-edition page
    sources its base model and the entry records that it did. Exactly the
    model's words, then 'ABS' — 'Z900 SE ABS', 'Ninja H2 Carbon ABS' and
    'SV650X ABS' are other machines and do not qualify."""
    target = "".join(_words_of(spelling))
    toks = _words_of(text)
    for i, t in enumerate(toks):
        if not target.startswith(t):
            continue
        acc, j = t, i
        while len(acc) < len(target) and j + 1 < len(toks) and target.startswith(acc + toks[j + 1]):
            j += 1
            acc += toks[j]
        if acc == target and j + 1 < len(toks) and toks[j + 1] == "abs":
            return True
    return False


# E12 (operator, 2026-09-23): what makes a quote evidence of a MANUAL gearbox.
# A rider-operated clutch, a foot-shift pattern, or the word "manual". A gear
# count, "constant mesh" or "close-ratio" is not: a DCT or Y-AMT is a
# constant-mesh six-speed too (Ninja 650 was killed on "6-speed" alone).
RIDER_CLUTCH = re.compile(
    r"clutch lever|clutch cable|cable[- ]operated clutch|cable[- ]actuated clutch|"
    r"hydraulic(?:ally)?(?:[- ](?:operated|actuated))? clutch|manual clutch|"
    r"(?:pull|squeeze|pulling|squeezing)\W+(?:\w+\W+){0,3}clutch|clutch\W+(?:\w+\W+){0,2}pull", re.I)
FOOT_SHIFT = re.compile(r"return shift|shift pedal|change pedal|gear ?shift pedal|foot[- ]shift|"
                        r"foot[- ]operated (?:return )?shift", re.I)
MANUAL_WORD = re.compile(r"\bmanual\b", re.I)
# The word "manual" counts only within MANUAL_REACH words of a gearbox term
# (operator, 2026-09-23): "Manual transmission", "6-speed manual gearbox",
# "Transmission Manual; 5 speeds" — not "manual choke", "manual fuel valve"
# or Triumph's "manual adjustment of compression and rebound damping".
GEARBOX_TERM = re.compile(r"\b(?:transmission|gearbox|gear ?shift|"
                          r"(?:\d|two|three|four|five|six|seven)[- ]?speeds?)\b", re.I)
MANUAL_REACH = 3
DOCUMENT_MANUAL = re.compile(r"(?:owner'?s?|owners|service|workshop|shop|repair|rider'?s?|user'?s?)\s+manual", re.I)
# The clutch pull, widened to one sentence (operator, 2026-09-23): "clutch"
# and a NOUN pull — "a light (lever) pull", "the pull of the clutch" — not
# the engine's "pulls hard" or a machine that "pulls away".
CLUTCH_PULL = re.compile(r"\b(?:lever|light|lighter|easy|easier|smooth|clutch)[- ]pull\b|"
                         r"\bpull (?:on|of) the clutch\b", re.I)
# A sentence carrying any of these is not manual evidence, whatever else it
# says: Yamaha's "Automated Manual Transmission" (Y-AMT), a DCT's "manual
# mode", "clutchless" (operator, 2026-09-23 — Yamaha and Honda are next).
AUTOMATED = re.compile(r"\bdct\b|dual[- ]clutch|\by-?amt\b|\bautomated\b|\bautomatic\b|\bclutchless\b|"
                       r"\bmanual (?:shift )?mode\b|\bpaddle", re.I)
# A negation governing the clutch/shift term: "eliminates the clutch lever",
# "without a clutch lever", "no clutch lever to pull", "no need to".
NEGATION = re.compile(r"\b(?:no|not|without|eliminates?|eliminated|eliminating|never|nor|free of|cannot)\b"
                      r"|n't\b", re.I)
NEGATION_REACH = 5                      # words before the term
NEGATION_AFTER = 4                      # and after it: "the clutch lever is not required" (bug fix #5)


def _sentences(q: str) -> list[str]:
    """Sentences — split at . ! ?, never at ';' (a spec row reads
    'Transmission Manual; 5 speeds', and a DCT sentence may continue past one)."""
    return [s for s in re.split(r"(?<=[.!?])\s+", q) if s.strip()]


def _unnegated(pattern: re.Pattern, sentence: str, near: re.Pattern | None = None) -> bool:
    """A match of `pattern` with no negation governing it — and, given
    `near`, with a match of `near` within MANUAL_REACH words of it."""
    for m in pattern.finditer(sentence):
        before = re.findall(r"[\w'-]+", sentence[:m.start()])[-NEGATION_REACH:]
        after = re.findall(r"[\w'-]+", sentence[m.end():])[:NEGATION_AFTER]
        if any(NEGATION.search(" ".join(w)) for w in (before, after)) or NEGATION.search(m.group(0)):
            continue
        if near is not None:
            close = (re.findall(r"[\w'-]+", sentence[:m.start()])[-MANUAL_REACH:],
                     re.findall(r"[\w'-]+", sentence[m.end():])[:MANUAL_REACH])
            if not any(near.search(" ".join(w)) for w in close):
                continue
        return True
    return False


def manual_evidence(quote: str) -> bool:
    """Does the quote itself show a manual gearbox's mechanism? One of its
    sentences must name a rider-operated clutch (a lever, cable, hydraulic
    clutch, or a clutch pull — a noun pull, anywhere in the sentence), a
    foot-shift pattern, or the word "manual" within three words of a gearbox
    term — with no automated-transmission
    marker in that sentence and no negation governing the term."""
    # Typographic apostrophes read as plain ones (bug fix #5): BMW prints
    # "Rider’s Manual", Honda "don’t" — the rules below were written for "'".
    q = " ".join((quote or "").replace("’", "'").replace("‘", "'").split())
    for s in _sentences(q):
        if AUTOMATED.search(s):
            continue
        if _unnegated(RIDER_CLUTCH, s) or _unnegated(FOOT_SHIFT, s):
            return True
        if re.search(r"\bclutch", s, re.I) and _unnegated(CLUTCH_PULL, s):
            return True
        if _unnegated(MANUAL_WORD, DOCUMENT_MANUAL.sub(" ", s), near=GEARBOX_TERM):
            return True
    return False


def passing_sentences(excerpts: list[dict]) -> list[str]:
    """The sentences in a spelling's excerpts that pass E12, deduplicated.
    Measures the reader, not the rule (operator C, 2026-09-23): when E12
    rejects a finding, were there lines it could have quoted instead?"""
    seen: dict[str, None] = {}
    for e in excerpts or []:
        for s in _sentences(" ".join(str(e.get("text", "")).split())):
            if manual_evidence(s):
                seen.setdefault(s, None)
    return list(seen)


# The non-manual mechanisms in the maker's own words (operator, 2026-09-23):
# a sentence naming one is something the source stage could classify from.
# V-matic is Honda's CVT; Y-AMT is Yamaha's automated manual. A miss here
# drops a spelling silently; a false alarm costs one source call — so the
# list leans wide (automatic, V-belt, variator, single-speed; operator).
MECHANISM = re.compile(r"\bv-?matic\b|\bcvt\b|\bdct\b|\by-amt\b|\bamt\b|\bcentrifugal\b|\bdirect[- ]drive\b|"
                       r"\bv-belt\b|\bvariator\b|\bsingle[- ]speed\b", re.I)
# "automatic" counts only within three words of a drive term (operator,
# 2026-09-23), the shape of the "manual" rule: "V-belt automatic", not
# Triumph's "automatic warnings if tyres fall", BMW's "Automatic Stability
# Control" or Honda's "automatic reset mode".
AUTOMATIC_WORD = re.compile(r"\bautomatic\b", re.I)
DRIVE_TERM = re.compile(r"\b(?:transmission|gearbox|belt|clutch|drive)\b", re.I)   # "belt" matches V-belt


def _beside(pattern: re.Pattern, sentence: str, near: re.Pattern) -> bool:
    """A match of `pattern` with a match of `near` within MANUAL_REACH words."""
    for m in pattern.finditer(sentence):
        close = (re.findall(r"[\w'-]+", sentence[:m.start()])[-MANUAL_REACH:],
                 re.findall(r"[\w'-]+", sentence[m.end():])[:MANUAL_REACH])
        if any(near.search(" ".join(w)) for w in close):
            return True
    return False


# A table-of-contents line (operator, 2026-09-23): a dot leader, or a trailing
# page reference — "6-16 Clutch lever ......", "Clutch lever......... 4-9",
# "Shift pedal (page 5-29)". It names a page, not a mechanism: Yamaha's MT-09,
# MT-07, XT250 and MT-10 were sent on such lines and nothing else.
TOC_LINE = re.compile(r"(?:\.\s?){4,}|…{2,}|[A-Za-z)]\s*\(?(?:page\s+)?\d{1,2}-\d{1,3}\)?\s*$", re.I)
# A trailing "N-N" after one of these is a range in a wrapped sentence, not a
# page: KTM's "Press and / hold the SET / button for 3-5 / seconds."; after
# "see page" it is a sentence's cross-reference, Yamaha's "or equipment
# damage. See page 5-1" (bug fix #7). A callout's "Shift pedal (page 6-31)"
# is still a contents line.
RANGE_WORD = re.compile(r"\b(?:for|to|from|between|within|of|in|at|by|about|approx\.?|approximately|every|after|"
                        r"and|or|than|see\s+page)\s+\d{1,2}-\d{1,3}\s*$", re.I)


def toc_line(line: str) -> bool:
    return bool(TOC_LINE.search(line)) and not RANGE_WORD.search(line)


def is_mechanism(sentence: str) -> bool:
    """Passes E12, or names a non-manual mechanism in the maker's words."""
    return bool(manual_evidence(sentence) or MECHANISM.search(sentence)
                or _beside(AUTOMATIC_WORD, sentence, DRIVE_TERM))


def mechanism_lines(excerpts: list[dict]) -> list[str]:
    """The dry run before the source call: the sentences in a spelling's
    excerpts that pass E12 or name a non-manual mechanism, deduplicated.
    None → nothing for the source stage to quote, and the spelling is not
    sent (Yamaha and Triumph: spec pages whose gearbox is a table cell).
    Table-of-contents lines are dropped before the text is read as
    sentences: they are not evidence."""
    seen: dict[str, None] = {}
    for e in excerpts or []:
        kept = [x for x in str(e.get("text", "")).split("\n") if not toc_line(x)]
        for s in _sentences(" ".join(" ".join(kept).split())):
            if is_mechanism(s):
                seen.setdefault(s, None)
    return list(seen)


def reader_note(excerpts: list[dict], scope: str = "model") -> str:
    """A miss counts only when the finding's document names its own model
    (operator, 2026-09-23): R1100's passing line is in the R 1100 S's
    manual, which could never have written the R1100."""
    if scope != "model":
        return "not a reader miss: its document names only a sibling or the family"
    n = len(passing_sentences(excerpts))
    return f"reader miss: {n} passing line{'s' if n != 1 else ''}" if n else "no passing line in its excerpts"


def document_text(f: dict, docs_root: pathlib.Path) -> str | None:
    """The text a finding's claims are checked against: the original behind
    an evidence copy, else the document itself (HTML as text)."""
    doc = pathlib.Path(f.get("document") or "")
    doc = doc if doc.is_absolute() else docs_root / doc
    if _is_evidence_copy(doc, docs_root):
        return _original_text(doc, "", [])
    return _extract_text(doc) if doc.is_file() else None


def model_edition(f: dict, docs_root: pathlib.Path) -> str | None:
    """'ABS' when the cited document names '<model> ABS' — recorded on the
    finding so the written entry says it came from the ABS edition."""
    text = document_text(f, docs_root)
    return "ABS" if text is not None and abs_edition(text, f.get("spelling", "")) else None


def model_scope(f: dict, docs_root: pathlib.Path, library: pathlib.Path = library_index.LIBRARY) -> str:
    """'model' when the cited document names the finding's own model;
    'family' when it names only a sibling or the family. Family evidence is
    recorded and cannot write an entry unless refute shows the page names
    the model (orchestrate.batch). A manual-route PDF whose pinned list
    record names the model exactly (`list_identity`) is 'model' too: the
    maker's own catalogue gives its model line (operator, 2026-09-23)."""
    text = document_text(f, docs_root)
    if text is not None and names_model(text, f.get("spelling", "")):
        return "model"
    doc = pathlib.Path(f.get("document") or "")
    doc = doc if doc.is_absolute() else docs_root / doc
    if list_identity(doc, library, f.get("make", ""), f.get("spelling", "")):
        return "model"
    return "family"


SPEC_LABEL = re.compile(r"transmission|gearbox|clutch|drive|gear|speed", re.I)


def embedded_spec_pairs(raw: str) -> list[tuple[str, str]]:
    """Label/value pairs from spec data a page embeds as JSON (Zero's
    `"entry_label":"Transmission" … "model_type_option_1_value":"Clutchless
    direct drive"`), gearbox labels only, in page order."""
    s = raw.replace('\\"', '"')
    pat = re.compile(r'"(?:entry_label|label|name)"\s*:\s*"([^"]{1,60})"(.{0,400}?)'
                     r'"[a-z0-9_]*value[a-z0-9_]*"\s*:\s*"([^"]{1,200})"', re.S)
    out: list[tuple[str, str]] = []
    for m in pat.finditer(s):
        if SPEC_LABEL.search(m.group(1)) and (m.group(1), m.group(3)) not in out:
            out.append((m.group(1), m.group(3)))
    return out


def derive_text(path: pathlib.Path) -> str | None:
    """The text candidates.py reads for an acquired original — a pure
    function of its bytes, so E11 can re-derive it and compare. PDF: pypdf
    per page under `=== PAGE n ===`; HTML: its text, then any embedded spec
    pairs; JSON: sorted and indented."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pypdf
            pages = pypdf.PdfReader(path).pages
            return "\n".join(f"=== PAGE {i} ===\n{p.extract_text() or ''}" for i, p in enumerate(pages, 1))
        except Exception:
            return None
    if suffix in (".html", ".htm"):
        text = _extract_text(path)
        if text is None:
            return None
        pairs = embedded_spec_pairs(path.read_bytes().decode("utf-8", errors="ignore"))
        if pairs:
            text += "\n=== EMBEDDED SPEC DATA ===\n" + "\n".join(f"{a}: {b}" for a, b in pairs) + "\n"
        return text
    if suffix == ".json":
        try:
            return json.dumps(json.loads(path.read_bytes()), indent=1, sort_keys=True, ensure_ascii=False) + "\n"
        except ValueError:
            return None
    return None


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
    parent = prov.get("derived_from")
    if parent:
        # Derived text: its parent must pass E11, and re-deriving it must give these bytes.
        src = library / str(parent.get("path", ""))
        if not parent.get("path") or not src.is_file():
            return [f"E11 {tag}: {doc.name} is derived from {parent.get('path')!r}, not in the library"]
        fails = acquired_provenance(src, library, make, tag)
        if fails:
            return fails
        text = derive_text(src)
        if text is None or hashlib.sha256(text.encode("utf-8")).hexdigest() != prov["sha256"]:
            return [f"E11 {tag}: {doc.name} is not what {src.name} derives to"]
        return []
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
    if not links_to(page.read_bytes(), ref["url"], prov["url"]):
        return [f"E11 {tag}: the referrer page {page.name} does not link to {prov['url']}"]
    return []


def _same_url(a: str, b: str) -> bool:
    n = lambda u: urllib.parse.unquote(u.strip()).rstrip("/")  # noqa: E731
    return n(a) == n(b)


def _json_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, list):
        return [s for v in value for s in _json_strings(v)]
    return []


def links_to(page_bytes: bytes, page_url: str, url: str) -> bool:
    """Does this page link to url? Every href/src, resolved against the
    page's own URL as a browser would — a page saved with 'Save Page As'
    keeps its links relative ('/content/…/manual.pdf').

    A JSON referrer — a maker's own data endpoint, like ktm.com's
    bikemanuals.manuals.json — links by a string value equal to url, exact
    and never resolved (operator, 2026-09-23)."""
    try:
        data = json.loads(page_bytes)
    except ValueError:
        data = None
    if isinstance(data, (dict, list)):
        return any(_same_url(s, url) for s in _json_strings(data))
    src = page_bytes.decode("utf-8", errors="ignore")
    for ref in re.findall(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", src, re.I):
        if _same_url(urllib.parse.urljoin(page_url, _html.unescape(ref)), url):
            return True
    return False


def manual_route_pdf(doc: pathlib.Path, library: pathlib.Path, make: str,
                     e11_passed: bool = False) -> tuple[pathlib.Path, dict] | None:
    """(pdf, its sidecar) when doc is an owner's manual a manual route
    fetched (acquire.MANUAL_ROUTES), or that PDF's derived text, and it
    passes E11 (`e11_passed`: the caller has just checked). Else None."""
    from acquire import MANUAL_ROUTES
    if make not in MANUAL_ROUTES or library_index.kind(doc, library) != "acquired":
        return None
    if not e11_passed and acquired_provenance(doc, library, make, ""):
        return None
    try:
        prov = json.loads(doc.with_name(doc.name + ".acquired.json").read_text(encoding="utf-8"))
        pdf = library / prov["derived_from"]["path"] if prov.get("derived_from") else doc
        side = json.loads(pdf.with_name(pdf.name + ".acquired.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return (pdf, side) if pdf.suffix.lower() == ".pdf" else None


def list_identity(doc: pathlib.Path, library: pathlib.Path, make: str, spelling: str) -> dict | None:
    """The maker's own list record naming this manual's model (operator,
    2026-09-23). Yamaha's Vino 125 manual prints only "YJ125Y"; the saved
    model_list response the route fetched it from reads
    "dispModelName": "VINO 125 - YJ125Y" beside this PDF's pdffileURL.

    Holds only when: doc is a manual-route PDF (or its text) passing E11,
    fetched for this spelling (for_spellings); its referrer record is in
    the library and still hashes to the sha256 its sidecar pinned; one of
    the record's entries has a pdffileURL equal to the PDF's url
    (protocol-relative completed as https); and that entry's name — the
    dispModelName before " - <code>" — IS the spelling (exact, by _key;
    "Bonneville T100" is not "T100"). Returns the model line, the code
    (an alias) and the record's path and sha256."""
    got = manual_route_pdf(doc, library, make)
    if got is None:
        return None
    pdf, side = got
    ref = side.get("referrer") or {}
    if spelling not in (side.get("for_spellings") or []) or not ref.get("path"):
        return None
    record = library / str(ref["path"])
    if not record.is_file() or _sha256(record) != ref.get("sha256"):
        return None
    try:
        rows = json.loads(record.read_bytes()).get("modelDataCollection") or []
    except (ValueError, AttributeError):
        return None
    for row in rows:
        url = str(row.get("pdffileURL") or "")
        url = "https:" + url if url.startswith("//") else url
        name, sep, code = str(row.get("dispModelName") or "").rpartition(" - ")
        if not sep:
            name, code = code, ""
        if url and _same_url(url, side.get("url", "")) and name and _key(name) == _key(spelling):
            return {"record": str(ref["path"]), "sha256": ref["sha256"], "model_line": row["dispModelName"],
                    "code": code.strip(), "publication": row.get("publicationNo")}
    return None


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
    if value == "manual" and not manual_evidence(quote):
        fails.append(f"E12 {tag}: a manual classification needs a quote naming a rider-operated clutch, "
                     f"a foot-shift pattern or the word 'manual' — a gear count, 'constant mesh' or "
                     f"'close-ratio' alone is not mechanism evidence: {quote!r}")

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
                text, doc, f.get("make", ""), f.get("spelling", "")) and not list_identity(
                doc, library, f.get("make", ""), f.get("spelling", "")):
            # The maker's own pinned list record naming this manual's model
            # exactly names it as a model (operator, 2026-09-23): "VINO 125".
            fails.append(f"E4 {tag}: {f.get('spelling')!r} is a common word or bare number and the "
                         f"document never names it as a {f.get('make')} model (after the make, as a "
                         "lookup alias, in its title or its file name)")
    if f.get("ocr") and not f.get("needs_page_image"):
        fails.append(f"E8 {tag}: OCR-sourced evidence not flagged for a page-image check")
    return fails


def check(findings: list[dict], docs_root: pathlib.Path, excerpts: dict | None = None,
          library: pathlib.Path = library_index.LIBRARY) -> list[str]:
    return [x for f in findings for x in check_one(f, docs_root, excerpts, library)]


REJECTION_IDS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10", "E11", "E12")


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
