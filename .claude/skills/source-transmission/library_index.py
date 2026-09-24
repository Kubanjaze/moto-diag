#!/usr/bin/env python3
"""Library index — what KIND of document each on-disk library file is.

No model. E2 used to trust the `evidence_kind` the source stage declared; a
model that called a crawl dump an owner's manual passed it. For a library
file the kind now comes from here: an ordered table of path rules, written
by hand after reading the files, first match wins. **A file no rule
matches is `unindexed`**, and unindexed is not a maker document: E2
rejects it and `candidates.py` never reads it. Adding a document to the
library therefore means adding (or checking) its rule — which is the point.

Kinds that are maker evidence: `maker_manual`, `maker_spec_page` (a
maker's own model/spec web page), `maker_site_page` (other pages crawled
from a maker's own site). Kinds that are not: `third_party` (mirrors,
cyclepedia, manualslib), `crawl_artefact` (the project's own lists, dumps,
error pages), `recall` (NHTSA), `regulation`.

Usage:  library_index.py [--library DIR]   (prints the count per kind, and every unindexed file)
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

LIBRARY = pathlib.Path.home() / "research" / "motodiag"
MAKER_KINDS = {"maker_manual", "maker_spec_page", "maker_site_page", "acquired"}

# (regex over the path relative to the library, kind, why). Order matters:
# the not-evidence rules come first, so a mirror named like a manual is
# still a mirror.
# Each make's own web hosts (a host matches itself and its subdomains). An
# acquired document from any other host counts only through a referrer: a
# page on one of these hosts, itself acquired, that links to it (E11) — the
# Wolf 150 manual is a Dropbox file linked from SYM USA's own page.
MAKER_HOSTS: dict[str, tuple[str, ...]] = {
    "SYM": ("sym-usa.com", "sym-global.com"), "Kymco": ("kymcousa.com", "kymco.com"),
    "Genuine": ("genuinescooters.com",), "Honda": ("honda.com", "hondamotopub.com"),
    "Kawasaki": ("kawasaki.com",),
    # library.ymcapps.net served the Vino 125 owner's manual PDF (5YR-F8199-15, 2026-09-23). Linked as
    # Yamaha's Owner's Manual Library from acquired/Yamaha/models_*_specs.html (yamahamotorsports.com).
    "Yamaha": ("yamahamotorsports.com", "yamaha-motor.com", "library.ymcapps.net"),
    "Suzuki": ("suzukicycles.com",),
    # Not KTM's Azure CDN host (azwecdnepstoragewebsiteuploads.azureedge.net): a generic address that
    # may carry other brands. Its manuals pass as a referrer's link — ktm.com's own
    # bikemanuals.manuals.json names each PDF by exact URL (operator, 2026-09-23).
    "KTM": ("ktm.com",),
    "Triumph": ("triumphmotorcycles.com",),
    "MV Agusta": ("mvagusta.com",), "Zero": ("zeromotorcycles.com",),
    "BMW": ("bmw-motorrad.com", "bmwmotorcycles.com"), "LiveWire": ("livewire.com",),
    "Harley-Davidson": ("harley-davidson.com",), "Ducati": ("ducati.com",), "Aprilia": ("aprilia.com",),
    "Piaggio": ("piaggio.com",), "Vespa": ("vespa.com",), "Moto Guzzi": ("motoguzzi.com",),
    "Energica": ("energicamotor.com",), "Damon": ("damon.com",),
}


def maker_host(url: str, make: str) -> bool:
    host = re.sub(r"^[a-z]+://([^/:?#]+).*$", r"\1", (url or "").strip().lower())
    return any(host == h or host.endswith("." + h) for h in MAKER_HOSTS.get(make, ()))


RULES: list[tuple[str, str, str]] = [
    # --- acquired by acquire.py: provenance in the sidecar, checked by E11 ---
    (r"^acquired/", "acquired", "fetched by acquire.py; its kind is its sidecar's, gated by E11"),
    # --- not evidence -------------------------------------------------------
    (r"(^|/)cyclepedia_", "third_party", "Cyclepedia: a third-party manual publisher"),
    (r"(^|/)txt_vespa_lx50_633416\.txt$", "third_party", "its own page 1 reads 'Downloaded from www.Manualslib.com'"),
    (r"_mirror\.", "third_party", "saved from a mirror site, by its own name"),
    (r"(^|/)v2/pdf/dealer_", "third_party", "a dealer's file, not the maker's"),
    (r"(^|/)(makes_raw|models_raw|makes_models|yam_models|vespa_models|lance_models|catalog|catalog_uniq"
     r"|scooter_hits|probe2|idx2015|om_pdfs|manual_links|urls\d*|kymco_urls|symglobal_urls|sym_sitemap_urls"
     r"|allcamp|campaigns)\.txt$", "crawl_artefact", "the project's own model lists, URL lists and API dumps"),
    (r"^(cp|kb|kc|kcs|kg|ki|pc|hv|ml1|t|mv|rc|rc_[0-9a-f]+|ffdd|vespa_manuals|sgsitemap|sgtech-talk)\.html$",
     "crawl_artefact", "crawl pages: dealer/aggregator pages, bot walls ('Just a moment'), 'Access Denied', 404s"),
    (r"^[0-9a-f]{32}\.html$", "crawl_artefact", "hash-named crawl saves of 'About us' pages"),
    (r"(^|/)(mi300|mi500)\.txt$", "crawl_artefact", "one-paragraph notes, not a document"),
    (r"(^|/)(ct110|c70)\.(txt|html)$", "crawl_artefact", "a web page saved under a manual's name (the text is HTML)"),
    (r"(^|/)hpe_workshop\.txt$", "crawl_artefact", "a broken extraction ('Ignoring wrong pointing object'); txt_c2_hpe_workshop.txt is the readable copy"),
    (r"^nhtsa/|(^|/)(p573_|RCL|24V825)", "recall", "NHTSA recall records: about a defect, not the maker's specification"),
    (r"(^|/)eu(168|3_2014)\.txt$", "regulation", "EU type-approval regulations"),
    (r"(^|/)txt_c[56]_", "crawl_artefact", "Piaggio technical communications: bulletins, not a machine's specification"),
    # --- maker manuals --------------------------------------------------------
    (r"^(p250|txt)/p\d+\.txt$", "maker_manual", "page-split Kymco service manuals (People S 250; Agility 50)"),
    (r"^manuals/ocr_cache/", "maker_manual", "OCR of maker user's manuals (Lance, Roketa, Genuine)"),
    (r"^(v2/)?(pdf|pdfs|sympdf)/", "maker_manual", "maker PDFs fetched from maker portals, text extracted"),
    (r"^pcx/\d{4}\.txt$", "maker_manual", "Honda PCX owner's manuals by year"),
    (r"^honda/(chf50_sm_p1_140|metro_\d{4}|ruckus_\d{4}|service)\.txt$", "maker_manual", "Honda owner's/service manual extracts"),
    (r"(^|/)(txt_|om_|pc_)?[^/]*(owners?[_ -]?manual|_om|_sm|_wsm|_user|_shop|_ssm|workshop|service)[^/]*\.txt$",
     "maker_manual", "named as an owner's, service or workshop manual"),
    (r"^(txt_)?(buddy\w*|rattler50|roughhouse50|symba|gts310|s50_2t|elettrica_ws|2025_pcx|txt_\d{4}_\w+"
     r"|txt_c[1278]_\w+|txt_honda_\w+|txt_kymco_\w+|txt_yamaha_\w+|txt_yz125_2009|txt_pgo_\w+|txt_sym_\w+|txt_gen_\w+"
     r"|mp3_400lt_user|om_c125_\w+|pc_c125|pc_ct125|530_spec|530_user|buddy125_sm|ct110_clean|txt_vespa_lx)\.txt$",
     "maker_manual", "maker manuals extracted to text at the library root (each read before listing)"),
    # --- maker web pages --------------------------------------------------------
    (r"^honda/(grom|monkey|trail|cub|metro|minimoto)[^/]*\.html$", "maker_spec_page", "Honda's own model specification pages"),
    (r"^html/(pcx\w*|zuma-125|vino-classic|adv160)\.html$|^adv160\.html$", "maker_spec_page", "maker model pages"),
    (r"^v2/(super850[rx]|peoples)_prod\.(html|txt)$", "maker_spec_page", "Kymco product pages"),
    (r"^v2/(kymcocom|symusa|symglobal)/", "maker_site_page", "crawls of kymco.com, sym-usa.com, sym-global.com"),
    (r"^v2/(kymcousa|kymco_uk|sym_global|symusa|symba_site)[\w-]*\.(html|txt)$", "maker_site_page", "maker site pages"),
    (r"^(sym_mg|sgdownload|sgfaq|pgo|pgo_en|about|faqs|manuals|om|techres|warranty|abw2?)\.html$",
     "maker_site_page", "maker portal pages (SYM, PGO, Genuine)"),
    (r"^honda/[^/]+\.(html|txt)$|^html/[^/]+\.html$|^manuals/[^/]+\.html$|^yam/", "maker_site_page",
     "other pages saved from maker sites"),
]
_COMPILED = [(re.compile(rx, re.I), kind, why) for rx, kind, why in RULES]


def kind(path: pathlib.Path | str, library: pathlib.Path = LIBRARY) -> str:
    """The kind of a library file, or `unindexed`; `not_library` outside it."""
    try:
        rel = pathlib.Path(path).resolve().relative_to(pathlib.Path(library).resolve()).as_posix()
    except ValueError:
        return "not_library"
    for rx, k, _ in _COMPILED:
        if rx.search(rel):
            return k
    return "unindexed"


def main(argv: list[str]) -> int:
    lib = pathlib.Path(argv[argv.index("--library") + 1]) if "--library" in argv else LIBRARY
    import candidates
    counts: collections.Counter = collections.Counter()
    unindexed = []
    for p in candidates.documents(lib, maker_only=False):
        k = kind(p, lib)
        counts[k] += 1
        if k == "unindexed":
            unindexed.append(p.relative_to(lib).as_posix())
    for k, n in counts.most_common():
        print(f"{k:18s} {n:5d}")
    for u in unindexed:
        print("  unindexed:", u)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    raise SystemExit(main(sys.argv[1:]))
