#!/usr/bin/env python3
"""D7 probe — how each maker's documents can be fetched, measured, no model.

Replaces `~/.cache/motodiag/d7_subc.py`, an open-ended agent loop ("go
deeper: find the API the page's scripts call"). This is bounded: a FIXED
list of at most three URLs per maker, written here by hand — the maker's
manual portal, a spec page for a model in the census, and a document
endpoint where one is known — one GET each, no cookies, no JavaScript, no
retries, no following of discovered links. What it cannot reach is
recorded as such, never guessed past.

Every classification is a rule over the response, in this file:

| method | rule |
|---|---|
| `unreachable` | DNS / TLS / timeout, or a 5xx (the origin down) |
| `redirect_loop` | a 3xx urllib gave up following — a cookie wall |
| `blocked` | 401 / 403 / 429, or a bot wall or "Access Denied" body |
| `not_found` | 404 / 410, or a redirect to a 404 page |
| `document_endpoint` | the body is a PDF (%PDF) |
| `spec_page_html` | HTML whose text carries a transmission line (TRANSMISSION_LINE) |
| `document_links` | HTML with links to .pdf files, no transmission line |
| `needs_browser` | HTML with under MIN_TEXT characters of text: the content is built by script |
| `html_no_evidence` | readable HTML with neither |

Each response body is saved under OUT/<stamp>/ with its sha256, the URL,
the final URL and the fetch time — the script's record, not a model's.
These saves are measurements; nothing here writes into the library.

Usage:  d7_probe.py [--only MAKE ...]
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from entry_check import _extract_text  # noqa: E402

OUT = pathlib.Path.home() / ".cache" / "motodiag" / "d7"
TIMEOUT = 25
MAX_BYTES = 30 * 2**20
MIN_TEXT = 1500
# The same UA as Step 0's S0-2, so the two measurements compare.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
BOT_WALL = re.compile(r"just a moment|access denied|attention required|captcha|cf-chl|"
                      r"are you a robot|request unsuccessful|incapsula|perimeterx|akamai.{0,40}reference", re.I)
TRANSMISSION_LINE = re.compile(r"(transmission|gearbox)\W{0,20}.{0,40}"
                               r"(\d[ -]?speed|speeds?\b|manual|dct|dual clutch|cvt|automatic|direct drive|single speed)",
                               re.I)

# (maker, role, url). Roles: portal = the owner's-manual portal; spec = a
# spec page for a model in the census; doc = a known document endpoint.
TARGETS: list[tuple[str, str, str]] = [
    ("Triumph", "portal", "https://www.triumphmotorcycles.com/owners/manuals"),
    ("Triumph", "spec", "https://www.triumphmotorcycles.com/motorcycles/roadsters/speed-triple-1200-rs"),
    ("Ducati", "portal", "https://www.ducati.com/us/en/owners/owner-manuals"),
    ("Ducati", "spec", "https://www.ducati.com/us/en/bikes/panigale/panigale-v4"),
    ("KTM", "portal", "https://www.ktm.com/en-us/service/manuals.html"),
    ("KTM", "spec", "https://www.ktm.com/en-us/models/naked-bike/ktm-1290-super-duke-r-evo.html"),
    ("BMW", "portal", "https://manuals.bmw-motorrad.com/"),
    ("BMW", "spec", "https://www.bmwmotorcycles.com/en/models/sport/s1000rr.html"),
    ("Kawasaki", "portal", "https://www.kawasaki.com/en-us/owner-center"),
    ("Kawasaki", "spec", "https://www.kawasaki.com/en-us/motorcycle/ninja/supersport/ninja-zx-10r"),
    ("Yamaha", "portal", "https://library.ymcapps.net/"),
    ("Yamaha", "spec", "https://www.yamahamotorsports.com/sport/models/yzf-r1"),
    ("Suzuki", "portal", "https://suzukicycles.com/"),
    ("Suzuki", "spec", "https://suzukicycles.com/product-lines/motorcycles/products/gsx-r1000"),
    ("Honda", "portal", "https://powersports.honda.com/owners/owners-manuals"),
    ("Honda", "doc", "https://www.hondamotopub.com/"),
    ("Honda", "spec", "https://powersports.honda.com/motorcycle/sport/cbr600rr"),
    ("Aprilia", "portal", "https://www.aprilia.com/us_EN/owner-manuals/"),
    ("Aprilia", "spec", "https://www.aprilia.com/us_EN/models/rsv4/"),
    ("MV Agusta", "portal", "https://www.mvagusta.com/us/en/manuals"),
    ("MV Agusta", "spec", "https://www.mvagusta.com/us/en/motorcycles/brutale"),
    ("Piaggio", "portal", "https://www.piaggio.com/us_EN/owners-manuals/"),
    ("Piaggio", "spec", "https://www.piaggio.com/us_EN/models/beverly/"),
    ("Vespa", "portal", "https://www.vespa.com/us_EN/owners-manuals/"),
    ("Vespa", "spec", "https://www.vespa.com/us_EN/vespa-models/gts/"),
    ("Harley-Davidson", "portal", "https://www.harley-davidson.com/us/en/owners/manuals.html"),
    ("Harley-Davidson", "doc", "https://serviceinfo.harley-davidson.com/"),
    ("Harley-Davidson", "spec", "https://www.harley-davidson.com/us/en/motorcycles/road-king.html"),
    ("Zero", "portal", "https://www.zeromotorcycles.com/owner-resources"),
    ("Zero", "spec", "https://www.zeromotorcycles.com/model/zero-sr"),
    ("Moto Guzzi", "portal", "https://www.motoguzzi.com/us_EN/owner-manuals/"),
    ("Moto Guzzi", "spec", "https://www.motoguzzi.com/us_EN/models/v7/"),
    ("Energica", "portal", "https://www.energicamotor.com/user-manual/"),
    ("Energica", "spec", "https://www.energicamotor.com/energica-experia/"),
    ("Kymco", "portal", "https://kymcousa.com/owners-manuals/"),
    ("Kymco", "spec", "https://kymcousa.com/super-8-50x/"),
    ("LiveWire", "portal", "https://www.livewire.com/"),
    ("LiveWire", "spec", "https://www.livewire.com/s2-del-mar"),
    ("Genuine", "portal", "https://www.genuinescooters.com/pages/owners-manuals"),
    ("Genuine", "doc", "https://www.genuinescooters.com/cdn/shop/files/Buddy125-OwnersManual_567a2b1f-2367-4ef5-9fcd-a960a034bcb3.pdf"),
    ("SYM", "portal", "https://sym-usa.com/owners-manuals/"),
    ("SYM", "spec", "https://sym-usa.com/jet-14-200i/"),
    ("Damon", "portal", "https://www.damon.com/"),
]


def classify(status: int | None, body: bytes, error: str | None, final_url: str,
             text: str | None = None) -> tuple[str, dict]:
    if error is not None or (status is not None and status >= 500):
        return "unreachable", {}                 # DNS, TLS, timeout, or the origin down (Cloudflare 522)
    if status is not None and 300 <= status < 400:
        return "redirect_loop", {}               # urllib gave up redirecting: a cookie wall (Kawasaki, S0-2)
    head = body[:4096].decode("latin-1", "ignore")
    if status in (401, 403, 429) or (len(body) < 50_000 and BOT_WALL.search(head)):
        return "blocked", {}
    if status in (404, 410) or re.search(r"/404\b|not[-_]found", final_url, re.I):
        return "not_found", {}
    if body[:5] == b"%PDF-":
        return "document_endpoint", {}
    if text is None:
        tmp = OUT / ".probe.html"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(body)
        text = _extract_text(tmp) or ""
    text = " ".join(text.split())
    pdfs = sorted(set(re.findall(r"""href=["']([^"']+\.pdf[^"']*)""", body.decode("utf-8", "ignore"), re.I)))
    m = TRANSMISSION_LINE.search(text)
    info = {"text_chars": len(text), "pdf_links": len(pdfs), "pdf_link_sample": pdfs[:3],
            "transmission_line": m.group(0)[:120] if m else None}
    if m:
        return "spec_page_html", info
    if pdfs:
        return "document_links", info
    if len(text) < MIN_TEXT:
        return "needs_browser", info
    return "html_no_evidence", info


def fetch(url: str) -> tuple[int | None, bytes, str | None, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read(MAX_BYTES), None, r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.read(MAX_BYTES) if e.fp else b"", None, e.geturl() or url
    except Exception as e:                       # DNS, TLS, timeout: recorded, not retried
        return None, b"", f"{type(e).__name__}: {e}"[:200], url


def main(argv: list[str]) -> int:
    only = set(argv[argv.index("--only") + 1:]) if "--only" in argv else None
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run = OUT / stamp
    run.mkdir(parents=True)
    rows = []
    for i, (maker, role, url) in enumerate(TARGETS):
        if only and maker not in only:
            continue
        at = dt.datetime.now().isoformat(timespec="seconds")
        status, body, error, final = fetch(url)
        method, info = classify(status, body, error, final)
        sha = hashlib.sha256(body).hexdigest() if body else None
        if body:
            (run / f"{i:02d}_{re.sub(r'[^A-Za-z0-9]+', '_', maker)}_{role}.bin").write_bytes(body)
        row = {"maker": maker, "role": role, "url": url, "final_url": final, "status": status,
               "error": error, "bytes": len(body), "sha256": sha, "fetched_at": at, "method": method, **info}
        rows.append(row)
        print(f"{maker:16s} {role:6s} {str(status):4s} {method:18s} {len(body):9d}  "
              f"{(info.get('transmission_line') or '')[:60]}", flush=True)
    (run / "d7.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(run / "d7.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
