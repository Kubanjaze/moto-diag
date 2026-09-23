#!/usr/bin/env python3
"""acquire — put maker documents INTO the library, with the script's own provenance.

No model. Two ways in:

* `acquire.py fetch MAKE [--limit N]` — the census's machine names for one
  make, through that make's measured route (ROUTES; D7, phase log). At most
  CAP fetches a run, one a second, robots.txt honoured, TLS never bypassed,
  a 403 recorded and never retried. A spelling no route page matches is
  reported, not guessed.
* `acquire.py ingest` — what the operator downloaded by hand into
  `~/research/motodiag/inbox/` (the convention is in INBOX_README).

Every file lands in `~/research/motodiag/acquired/<Make>/` with a sidecar
`<file>.acquired.json` that this script writes: url, final_url,
http_status, content_type, bytes, sha256, fetched_at, supplied_by,
referrer (url, path, sha256 of the maker page that linked it, or null),
for_spellings. Each original gets a derived text (`<file>.txt`,
`entry_check.derive_text`) whose sidecar names its parent; E11 re-derives
it and compares. The sandbox denies every model stage writes here.

Usage:  acquire.py fetch MAKE [--limit N] | acquire.py ingest
"""
from __future__ import annotations

import datetime as dt
import hashlib
import http.cookiejar
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import census as C  # noqa: E402
import library_index  # noqa: E402
from d7_probe import UA, classify  # noqa: E402
from entry_check import _key, derive_text, weak_spelling  # noqa: E402

LIBRARY = library_index.LIBRARY
CAP = 30                     # fetches per run (operator, 2026-09-23)
RATE = 1.0                   # seconds between requests
TIMEOUT = 25
MAX_BYTES = 60 * 2**20
XHR = {"X-Requested-With": "XMLHttpRequest"}


class CapReached(RuntimeError):
    pass


class Fetcher:
    """One cookie jar, the cap, the rate, robots.txt. The only network door."""

    def __init__(self, cap: int = CAP, rate: float = RATE, transport=None):
        self.cap, self.rate, self.count, self._last = cap, rate, 0, 0.0
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.transport = transport       # tests: url, headers -> (status, body, error, final_url)
        self.robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self.log: list[dict] = []

    def _raw(self, url: str, headers: dict | None) -> tuple[int | None, bytes, str | None, str]:
        if self.count >= self.cap:
            raise CapReached(f"{self.cap} fetches")
        wait = self.rate - (time.monotonic() - self._last)
        if wait > 0 and self.transport is None:
            time.sleep(wait)
        self.count += 1
        self._last = time.monotonic()
        if self.transport:
            return self.transport(url, headers or {})
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", **(headers or {})})
        try:
            with self.opener.open(req, timeout=TIMEOUT) as r:
                return r.status, r.read(MAX_BYTES), None, r.geturl()
        except urllib.error.HTTPError as e:
            return e.code, e.read(MAX_BYTES) if e.fp else b"", None, e.geturl() or url
        except Exception as e:                   # DNS, TLS, timeout: recorded, never retried
            return None, b"", f"{type(e).__name__}: {e}"[:200], url

    def allowed(self, url: str) -> bool:
        parts = urllib.parse.urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self.robots:
            status, body, err, _ = self._raw(host + "/robots.txt", None)
            rp = None
            if status == 200 and body:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(body.decode("utf-8", "ignore").splitlines())
            self.robots[host] = rp               # no robots.txt: nothing disallowed
        rp = self.robots[host]
        return rp is None or rp.can_fetch(UA, url)

    def get(self, url: str, headers: dict | None = None) -> dict:
        if not self.allowed(url):
            row = {"url": url, "status": None, "method": "robots_disallowed", "body": b"", "final_url": url}
        else:
            status, body, err, final = self._raw(url, headers)
            method, _ = classify(status, body, err, final, None if body[:5] != b"%PDF-" else "")
            row = {"url": url, "status": status, "error": err, "final_url": final, "body": body, "method": method,
                   "fetched_at": dt.datetime.now().isoformat(timespec="seconds")}
        self.log.append({k: v for k, v in row.items() if k != "body"})
        return row


# --- saving ------------------------------------------------------------------
def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _slug(url: str) -> str:
    path = urllib.parse.unquote(urllib.parse.urlsplit(url).path).strip("/") or "index"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", path)[-120:]


def _suffix(row: dict) -> str:
    body = row["body"]
    if body[:5] == b"%PDF-":
        return ".pdf"
    if row["method"] == "json_endpoint":
        return ".json"
    return ".html"


def save(make: str, row: dict, *, referrer: dict | None, for_spellings: list[str],
         supplied_by: str = "acquire.py", library: pathlib.Path = LIBRARY) -> dict:
    """Write the original, its sidecar, its derived text and that sidecar.
    Returns {"path", "sha256"} relative to the library."""
    folder = library / "acquired" / make
    folder.mkdir(parents=True, exist_ok=True)
    name = _slug(row["final_url"] or row["url"])
    name = name if name.lower().endswith(_suffix(row)) else name + _suffix(row)
    path = folder / name
    path.write_bytes(row["body"])
    sha = _sha(row["body"])
    side = {"url": row["url"], "final_url": row["final_url"], "http_status": row.get("status"),
            "bytes": len(row["body"]), "sha256": sha, "fetched_at": row.get("fetched_at"),
            "supplied_by": supplied_by, "referrer": referrer, "for_spellings": sorted(for_spellings),
            "method": row["method"]}
    (folder / (name + ".acquired.json")).write_text(json.dumps(side, indent=1) + "\n", encoding="utf-8")
    rel = path.relative_to(library).as_posix()
    text = derive_text(path)
    if text is not None and path.suffix != ".txt":
        tpath = folder / (name + ".txt")
        tpath.write_text(text, encoding="utf-8")
        tside = {"url": row["url"], "sha256": _sha(text.encode("utf-8")), "supplied_by": supplied_by,
                 "derived_from": {"path": rel, "sha256": sha}, "for_spellings": sorted(for_spellings)}
        (folder / (tpath.name + ".acquired.json")).write_text(json.dumps(tside, indent=1) + "\n", encoding="utf-8")
    return {"url": row["final_url"] or row["url"], "path": rel, "sha256": sha}


# --- matching a spelling to a route's names ------------------------------------
def match(spelling: str, names: dict[str, str]) -> str | None:
    """The route name (and its URL) for a spelling, or None.

    A strong spelling matches a name that contains it word for word; the
    shortest wins ("Street Triple 765" over "Street Triple 765 RS"). A weak
    one ("Bolt", "CB", "Monster 821") needs the name to BE it — "CB" must
    not take the first CB it sees."""
    sk = _key(spelling)
    exact = [n for n in names if _key(n) == sk]
    if exact:
        return names[min(exact, key=len)]
    if weak_spelling(spelling):
        return None
    hits = [n for n in names if sk in _key(n)]
    return names[min(hits, key=len)] if hits else None


# UI badges a maker appends to a link's text, named where seen: Zero's
# listing reads "SR/S New", "DSR/X New".
BADGES = {"new"}


def _links(body: bytes, base: str, pattern: str) -> dict[str, str]:
    """{name: absolute URL} for links matching pattern. Each link is named
    three ways, because makers name their pages three ways: its visible text
    ("KTM 1290 SUPER ADVENTURE R" — the slug says "superadventurer"), its last
    path segment, and its last two ("brutale/800" — the last alone is "800")."""
    html = body.decode("utf-8", "ignore")
    out: dict[str, str] = {}
    for href, inner in re.findall(r"""<a\b[^>]*href\s*=\s*["']([^"'#]+)["'][^>]*>(.*?)</a>""", html, re.I | re.S):
        url = urllib.parse.urljoin(base, href.replace("&amp;", "&"))
        if not re.search(pattern, url):
            continue
        parts = [re.sub(r"^20\d\d-|\.html$", "", p).replace("-", " ")
                 for p in urllib.parse.unquote(urllib.parse.urlsplit(url).path).strip("/").split("/")]
        words = re.sub(r"<[^>]+>", " ", inner).replace("&amp;", "&").split()
        while words and words[-1].lower() in BADGES:
            words.pop()                          # "SR/S New" is the SR/S
        text = " ".join(words)
        for name in (text, parts[-1], " ".join(parts[-2:])):
            if name and len(name) <= 80:
                out.setdefault(name, url)
    return out


# --- routes (measured in D7, phase log 2026-09-23) -----------------------------
def spec_route(listings: list[str], pattern: str, to_spec=lambda u: u, year_hop: bool = False):
    """Maker spec pages: listing page(s) → a model link → its spec page.
    `year_hop`: the model link is a family page whose spec lives one hop
    down, on its newest `/20xx-<family>` page (Kawasaki, measured)."""
    def run(f: Fetcher, make: str, spellings: list[str], library: pathlib.Path) -> dict:
        names: dict[str, str] = {}
        ref_for: dict[str, dict] = {}
        for lst in listings:
            row = f.get(lst)
            if row["method"] in ("blocked", "not_found", "unreachable", "robots_disallowed", "redirect_loop"):
                continue
            ref = save(make, row, referrer=None, for_spellings=[], library=library)
            for n, u in _links(row["body"], row["final_url"], pattern).items():
                names.setdefault(n, u)
                ref_for.setdefault(u, ref)
        return _fetch_matched(f, make, spellings, names, ref_for, to_spec, library, year_hop)
    return run


def _newest_year_page(f: Fetcher, make: str, family_url: str, library: pathlib.Path) -> tuple[str | None, dict | None]:
    """The family page's newest `<family>/20xx-<family slug>` link, and the
    saved family page as its referrer. Editions ('-krt-edition') are not the
    base model and are passed over."""
    row = f.get(family_url)
    if row["status"] != 200:
        return None, None
    slug = family_url.rstrip("/").rsplit("/", 1)[-1]
    years = {}
    for href in re.findall(r"""href\s*=\s*["']([^"'#]+)["']""", row["body"].decode("utf-8", "ignore")):
        m = re.search(rf"/{re.escape(slug)}/(20\d\d)-{re.escape(slug)}$", href)
        if m:
            years[int(m.group(1))] = urllib.parse.urljoin(row["final_url"], href)
    if not years:
        return None, None
    return years[max(years)], save(make, row, referrer=None, for_spellings=[], library=library)


def _fetch_matched(f, make, spellings, names, ref_for, to_spec, library, year_hop=False) -> dict:
    report: dict = {"matched": {}, "unmatched": [], "failed": {}}
    by_url: dict[str, list[str]] = {}
    for s in spellings:
        u = match(s, names)
        if u:
            by_url.setdefault(u, []).append(s)
        else:
            report["unmatched"].append(s)
    for u, ss in by_url.items():
        if year_hop:
            year_url, fam_ref = _newest_year_page(f, make, u, library)
            if not year_url:
                for s in ss:
                    report["failed"][s] = {"url": u, "method": "no_model_year_link"}
                continue
            u, ref_for = year_url, {**ref_for, year_url: fam_ref}
        row = f.get(to_spec(u))
        if row["method"] in ("spec_page_html", "spec_embedded_json", "document_endpoint", "html_no_evidence",
                             "document_links"):
            saved = save(make, row, referrer=ref_for.get(u), for_spellings=ss, library=library)
            for s in ss:
                report["matched"][s] = {"url": row["final_url"], "method": row["method"], "path": saved["path"]}
        else:
            for s in ss:
                report["failed"][s] = {"url": to_spec(u), "method": row["method"], "status": row["status"]}
    return report


def bmw_route(f: Fetcher, make: str, spellings: list[str], library: pathlib.Path) -> dict:
    """BMW Motorrad's own manuals app reads a static XML index (Nav.xml);
    the English rider's manual PDF for the newest model year of a match."""
    base = "https://manuals.bmw-motorrad.com/manuals/BA-Extern/IN/BA-INTERNET-COM"
    row = f.get(base + "/01/Nav.xml")
    if row["status"] != 200:
        return {"matched": {}, "unmatched": list(spellings), "failed": {"*": {"url": row["url"], "method": row["method"]}}}
    ref = save(make, row, referrer=None, for_spellings=[], library=library)
    xml = row["body"].decode("utf-8", "ignore")
    names: dict[str, str] = {}
    for m in re.finditer(r'<NAV-MODELL[^>]*T-BEZ="([^"]+)"[^>]*>(.*?)</NAV-MODELL', xml, re.S):
        pdfs = re.findall(r'LANGUAGE="01" FILENAME="([^"]+\.pdf)"', m.group(2))
        if pdfs:
            names.setdefault(m.group(1), f"{base}/PDF/{pdfs[-1]}")
    return _fetch_matched(f, make, spellings, names, {u: ref for u in names.values()}, lambda u: u, library)


def honda_route(f: Fetcher, make: str, spellings: list[str], library: pathlib.Path) -> dict:
    """Honda motopub (American Honda): model names per displacement bucket
    (JSON, the page's own /ajax/ calls), the newest year, the owner's-manual
    page, its PDF on a hondamotopub.com subdomain."""
    site = "https://www.hondamotopub.com"
    f.get(site + "/AHM")                                     # the session cookie, as the page gets it
    hdr = {**XHR, "Referer": site + "/AHM"}
    names: dict[str, str] = {}
    for cc in ("-0", "1-125", "126-400", "401-750", "751-"):
        row = f.get(f"{site}/ajax/get_model_names/AHM/{cc}", hdr)
        if row["method"] == "json_endpoint":
            for n in json.loads(row["body"]):
                names.setdefault(n, n)
    report: dict = {"matched": {}, "unmatched": [], "failed": {}}
    for s in spellings:
        name = match(s, names)
        if not name:
            report["unmatched"].append(s)
            continue
        yrow = f.get(f"{site}/ajax/get_model_years/AHM/{urllib.parse.quote(name)}", hdr)
        years = json.loads(yrow["body"]) if yrow["method"] == "json_endpoint" else []
        if not years:
            report["failed"][s] = {"url": yrow["url"], "method": yrow["method"]}
            continue
        om = f.get(f"{site}/om/AHM/{urllib.parse.quote(name)}/{max(years)}")
        pdfs = re.findall(r"""["'](https://[a-z0-9.-]*hondamotopub\.com/[^"']+\.pdf)["']""",
                          om["body"].decode("utf-8", "ignore"))
        if not pdfs:
            report["failed"][s] = {"url": om["url"], "method": om["method"]}
            continue
        ref = save(make, om, referrer=None, for_spellings=[s], library=library)
        doc = f.get(pdfs[0])
        if doc["method"] != "document_endpoint":
            report["failed"][s] = {"url": pdfs[0], "method": doc["method"]}
            continue
        saved = save(make, doc, referrer=ref, for_spellings=[s], library=library)
        report["matched"][s] = {"url": doc["final_url"], "method": doc["method"], "path": saved["path"]}
    return report


def doc_links_route(listings: list[str], page_pattern: str, pdf_pattern: str):
    """A listing → product pages → the PDF each links (SYM, Genuine)."""
    def run(f: Fetcher, make: str, spellings: list[str], library: pathlib.Path) -> dict:
        names: dict[str, str] = {}
        for lst in listings:
            row = f.get(lst)
            if row["status"] == 200:
                names.update(_links(row["body"], row["final_url"], page_pattern))
        report: dict = {"matched": {}, "unmatched": [], "failed": {}}
        for s in spellings:
            u = match(s, names)
            if not u:
                report["unmatched"].append(s)
                continue
            page = f.get(u)
            pdfs = list(_links(page["body"], page["final_url"], pdf_pattern).values()) if page["status"] == 200 else []
            if not pdfs:
                report["failed"][s] = {"url": u, "method": page["method"]}
                continue
            ref = save(make, page, referrer=None, for_spellings=[s], library=library)
            doc = f.get(pdfs[0])
            if doc["method"] != "document_endpoint":
                report["failed"][s] = {"url": pdfs[0], "method": doc["method"]}
                continue
            saved = save(make, doc, referrer=ref, for_spellings=[s], library=library)
            report["matched"][s] = {"url": doc["final_url"], "method": doc["method"], "path": saved["path"]}
        return report
    return run


ROUTES = {
    "KTM": spec_route(["https://www.ktm.com/en-us/service/manuals.html"],
                      r"ktm\.com/en-us/models/.+/20\d\d-ktm-[a-z0-9-]+\.html$"),
    "Suzuki": spec_route(["https://suzukicycles.com/"],
                         r"suzukicycles\.com/(?:sportbike|street|adventure|crossover|cruiser|dualsport|offroad)/20\d\d/[a-z0-9-]+$"),
    "MV Agusta": spec_route(["https://www.mvagusta.com/us/en/manuals"], r"mvagusta\.com/us/en/product/[a-z0-9-]+/[a-z0-9-]+$"),
    "Triumph": spec_route([f"https://www.triumphmotorcycles.com/motorcycles/{c}"
                           for c in ("roadsters", "adventure", "classic", "sport")],
                          r"triumphmotorcycles\.com/motorcycles/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+-20\d\d$"),
    "Yamaha": spec_route(["https://www.yamahamotorsports.com/"], r"yamahamotorsports\.com/models/[a-z0-9-]+$",
                         to_spec=lambda u: u.rstrip("/") + "/specs"),
    "Zero": spec_route(["https://www.zeromotorcycles.com/"], r"zeromotorcycles\.com/model/[a-z0-9-]+$"),
    "Kymco": spec_route(["https://kymcousa.com/scooters/"], r"kymcousa\.com/scooters/[a-z0-9-]+/?$"),
    "Kawasaki": spec_route(["https://www.kawasaki.com/en-us/owner-center"],
                           r"kawasaki\.com/en-us/motorcycle/[a-z-]+/[a-z-]+/[a-z0-9-]+$", year_hop=True),
    "BMW": bmw_route,
    "Honda": honda_route,
    "SYM": doc_links_route(["https://www.sym-global.com/"], r"sym-global\.com/[a-z0-9-]+$",
                           r"sym-global\.com/storage/.+\.pdf$"),
    "Genuine": doc_links_route(["https://www.genuinescooters.com/pages/owners-manual"],
                               r"genuinescooters\.com/cdn/shop/files/.+\.pdf", r"genuinescooters\.com/cdn/shop/files/.+\.pdf"),
}


def machine_names(make: str, db: pathlib.Path = C.REPO / "data" / "motodiag.db") -> list[str]:
    return [e["model"] for e in C.census(db, make).get(make, []) if not C.not_a_machine(make, e["model"])]


def already(make: str, library: pathlib.Path = LIBRARY) -> set[str]:
    out: set[str] = set()
    for side in (library / "acquired" / make).glob("*.acquired.json"):
        try:
            out.update(json.loads(side.read_text(encoding="utf-8")).get("for_spellings") or [])
        except ValueError:
            pass
    return out


def fetch(make: str, limit: int | None = None, *, fetcher: Fetcher | None = None,
          library: pathlib.Path = LIBRARY, spellings: list[str] | None = None) -> dict:
    if make not in ROUTES:
        return {"make": make, "error": "no measured route (D7)"}
    todo = [s for s in (spellings if spellings is not None else machine_names(make)) if s not in already(make, library)]
    todo = todo[:limit] if limit else todo
    if not todo:
        return {"make": make, "asked": [], "matched": {}, "unmatched": [], "failed": {}, "stopped": None,
                "fetches": 0, "log": []}
    f = fetcher or Fetcher()
    try:
        report = ROUTES[make](f, make, todo, library)
        report["stopped"] = None
    except CapReached as e:
        report = {"matched": {}, "unmatched": [], "failed": {}, "stopped": f"cap reached: {e}"}
    report.update({"make": make, "asked": todo, "fetches": f.count, "log": f.log})
    return report


# --- the operator inbox -----------------------------------------------------------
INBOX_README = """# inbox — maker documents downloaded by hand

For makers whose sites refuse a script (HTTP 403: Ducati, Aprilia, Piaggio,
Vespa, Moto Guzzi). `acquire.py ingest` copies each document into
`acquired/<Make>/` with a sidecar it writes itself; nothing here is edited
or deleted.

For EACH document, three files in `inbox/<Make>/` — the folder named exactly
as the make is spelled in the census (`Ducati`, `Aprilia`, `Piaggio`,
`Vespa`, `Moto Guzzi`):

1. the document itself, any name, e.g. `panigale-v4-om-2024.pdf`
2. `<that name>.url` — a plain text file of two lines:

       document: <the URL the file downloaded from — right-click the link, Copy Link>
       page: <the URL of the maker's own page you clicked it on>

3. `<that name>.page.html` — that maker page, saved from the browser with
   "Save Page As… → Web Page, HTML Only" while you are on it.

What ingest (and E11) require, so nothing is rejected on format:

* the `page:` URL is on the make's own site (ducati.com, aprilia.com,
  piaggio.com, vespa.com, motoguzzi.com, or a subdomain of one);
* the saved page links to the `document:` URL — relative links are fine,
  they are resolved against `page:` as a browser would;
* the `document:` URL may be on another host (a CDN) — the page vouches for it;
* one document per `.url`; names without the three files are left alone
  and reported.
"""


def ingest(library: pathlib.Path = LIBRARY) -> dict:
    inbox = library / "inbox"
    report: dict = {"ingested": [], "rejected": {}}
    for mdir in sorted(p for p in inbox.iterdir() if p.is_dir()) if inbox.is_dir() else []:
        make = mdir.name
        for doc in sorted(mdir.iterdir()):
            if doc.name.endswith((".url", ".page.html")) or doc.name.startswith(".") or not doc.is_file():
                continue
            why = _ingest_one(make, doc, library)
            if why:
                report["rejected"][f"{make}/{doc.name}"] = why
            else:
                report["ingested"].append(f"{make}/{doc.name}")
    return report


def _ingest_one(make: str, doc: pathlib.Path, library: pathlib.Path) -> str | None:
    from entry_check import links_to
    if make not in library_index.MAKER_HOSTS:
        return f"folder {make!r} is not a make in MAKER_HOSTS"
    urlf, pagef = doc.with_name(doc.name + ".url"), doc.with_name(doc.name + ".page.html")
    if not urlf.is_file() or not pagef.is_file():
        return f"needs {urlf.name} and {pagef.name}"
    fields = dict(re.findall(r"^\s*(document|page)\s*:\s*(\S.*?)\s*$", urlf.read_text(encoding="utf-8"), re.M))
    if set(fields) != {"document", "page"}:
        return f"{urlf.name} needs a 'document:' line and a 'page:' line"
    if not library_index.maker_host(fields["page"], make):
        return f"page {fields['page']} is not on a {make} host"
    page_bytes = pagef.read_bytes()
    if not links_to(page_bytes, fields["page"], fields["document"]):
        return f"{pagef.name} does not link to {fields['document']}"
    at = dt.datetime.fromtimestamp(doc.stat().st_mtime).isoformat(timespec="seconds")
    page_row = {"url": fields["page"], "final_url": fields["page"], "status": None, "body": page_bytes,
                "method": "operator_saved_page", "fetched_at": at}
    ref = save(make, page_row, referrer=None, for_spellings=[], supplied_by="operator", library=library)
    body = doc.read_bytes()
    doc_row = {"url": fields["document"], "final_url": fields["document"], "status": None, "body": body,
               "method": "document_endpoint" if body[:5] == b"%PDF-" else "operator_file", "fetched_at": at}
    save(make, doc_row, referrer=ref, for_spellings=[], supplied_by="operator", library=library)
    return None


def main(argv: list[str]) -> int:
    if argv[:1] == ["ingest"]:
        print(json.dumps(ingest(), indent=1))
        return 0
    if len(argv) >= 2 and argv[0] == "fetch":
        limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
        r = fetch(argv[1], limit)
        out = LIBRARY / "acquired" / f"_run_{argv[1].replace(' ', '_')}_{dt.datetime.now():%Y%m%d_%H%M%S}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")
        print(json.dumps({k: r.get(k) for k in ("make", "fetches", "stopped", "unmatched", "failed")}, indent=1))
        print(f"matched: {sorted(r.get('matched', {}))}\nrun record: {out}")
        return 0
    print(__doc__.split("Usage:")[1].strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
